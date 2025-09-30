"""
Tests for db-router-svc main FastAPI application.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient
from fastapi import HTTPException

from ..main import app
from ..models import Intent, RouteResponse


class TestMainApp:
    """Test main FastAPI application."""
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)
    
    @pytest.fixture
    def mock_llm_client(self):
        """Create mock LLM client."""
        client = AsyncMock()
        return client
    
    @pytest.fixture
    def mock_query_router(self):
        """Create mock query router."""
        router = AsyncMock()
        return router
    
    @pytest.fixture
    def mock_database_executor(self):
        """Create mock database executor."""
        executor = AsyncMock()
        executor.execute_query = AsyncMock(return_value=([{"test": "data"}], 1))
        executor.test_connection = AsyncMock(return_value=True)
        return executor


class TestHealthEndpoints:
    """Test health check endpoints."""
    
    def test_healthz_endpoint(self, client):
        """Test /healthz endpoint."""
        with patch('services.db_router_svc.main.get_database_health') as mock_health:
            mock_health.return_value = {"status": "healthy"}
            
            response = client.get("/healthz")
            
            assert response.status_code == 200
            data = response.json()
            assert "status" in data
            assert "timestamp" in data
    
    def test_healthz_unhealthy(self, client):
        """Test /healthz endpoint when unhealthy."""
        with patch('services.db_router_svc.main.get_database_health') as mock_health:
            mock_health.return_value = {"status": "unhealthy"}
            
            response = client.get("/healthz")
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "unhealthy"
    
    def test_database_health_endpoint(self, client):
        """Test /database/health endpoint."""
        with patch('services.db_router_svc.main.get_database_health') as mock_health:
            mock_health.return_value = {
                "status": "healthy",
                "pool_size": 5,
                "max_connections": 10
            }
            
            response = client.get("/database/health")
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "healthy"
            assert data["pool_size"] == 5
            assert data["max_connections"] == 10


class TestRouteEndpoint:
    """Test /route endpoint."""
    
    def test_route_endpoint_success(self, client):
        """Test successful routing."""
        with patch('services.db_router_svc.main.get_query_router') as mock_get_router:
            mock_router = AsyncMock()
            mock_router.route_query.return_value = RouteResponse(
                intent=Intent.FLIGHT_STATUS,
                args={"flight_no": "NZ278", "date": None},
                confidence=0.95
            )
            mock_get_router.return_value = mock_router
            
            response = client.post("/route", json={"text": "What's the status of NZ278?"})
            
            assert response.status_code == 200
            data = response.json()
            assert data["intent"] == "flight_status"
            assert data["args"]["flight_no"] == "NZ278"
            assert data["confidence"] == 0.95
    
    def test_route_endpoint_router_failure(self, client):
        """Test routing when router fails."""
        with patch('services.db_router_svc.main.get_query_router') as mock_get_router:
            mock_router = AsyncMock()
            mock_router.route_query.side_effect = Exception("Router error")
            mock_get_router.return_value = mock_router
            
            response = client.post("/route", json={"text": "Test query"})
            
            assert response.status_code == 500
            data = response.json()
            assert "Query routing failed" in data["detail"]


class TestSmartQueryEndpoint:
    """Test /smart-query endpoint."""
    
    def test_smart_query_success(self, client):
        """Test successful smart query."""
        with patch('services.db_router_svc.main.get_query_router') as mock_get_router, \
             patch('services.db_router_svc.main.get_llm_client') as mock_get_llm, \
             patch('services.db_router_svc.main.execute_intent_query') as mock_execute, \
            patch('services.db_router_svc.main.format_query_answer') as mock_format:
            
            # Mock dependencies
            mock_router = AsyncMock()
            mock_router.route_query.return_value = RouteResponse(
                intent=Intent.FLIGHT_STATUS,
                args={"flight_no": "NZ278", "date": None},
                confidence=0.95
            )
            mock_get_router.return_value = mock_router
            
            mock_llm = AsyncMock()
            mock_get_llm.return_value = mock_llm
            
            mock_execute.return_value = ([{"flight_no": "NZ278", "status": "on_time"}], 1)
            mock_format.return_value = "Flight NZ278 is on time"
            
            response = client.post("/smart-query", json={
                "text": "What's the status of NZ278?",
                "auth": {"role": "public"}
            })
            
            assert response.status_code == 200
            data = response.json()
            assert data["answer"] == "Flight NZ278 is on time"
            assert data["intent"] == "flight_status"
            assert len(data["rows"]) == 1
            assert data["rows"][0]["flight_no"] == "NZ278"

    def test_smart_query_knowledge_base(self, client):
        """Test smart query routing to knowledge base search."""
        with patch('services.db_router_svc.main.get_query_router') as mock_get_router, \
             patch('services.db_router_svc.main.get_llm_client') as mock_get_llm, \
             patch('services.db_router_svc.main.query_knowledge_base', new_callable=AsyncMock) as mock_kb_search:

            mock_router = AsyncMock()
            mock_router.route_query.return_value = RouteResponse(
                intent=Intent.KNOWLEDGE_BASE,
                args={"query": "What is the refund policy?", "k": 5},
                confidence=0.9
            )
            mock_get_router.return_value = mock_router

            mock_llm = AsyncMock()
            mock_get_llm.return_value = mock_llm

            mock_kb_search.return_value = (
                [{
                    "title": "Refund Policy",
                    "snippet": "Refunds are available within 24 hours of purchase.",
                    "category": "policy"
                }],
                {"mode": "hybrid", "embeddings_available": True}
            )

            response = client.post("/smart-query", json={
                "text": "What is the refund policy?"
            })

            assert response.status_code == 200
            data = response.json()
            assert data["intent"] == "knowledge_base"
            assert data["rows"][0]["title"] == "Refund Policy"
            assert data["metadata"]["knowledge_service"]["mode"] == "hybrid"
            assert "refund" in data["answer"].lower()

    def test_smart_query_invalid_args(self, client):
        """Test smart query with invalid arguments."""
        with patch('services.db_router_svc.main.get_query_router') as mock_get_router, \
             patch('services.db_router_svc.main.validate_intent_args') as mock_validate:
            
            mock_router = AsyncMock()
            mock_router.route_query.return_value = RouteResponse(
                intent=Intent.FLIGHT_STATUS,
                args={"flight_no": "NZ278"},
                confidence=0.95
            )
            mock_get_router.return_value = mock_router
            
            mock_validate.return_value = False  # Invalid args
            
            response = client.post("/smart-query", json={
                "text": "Test query",
                "auth": {"role": "public"}
            })
            
            assert response.status_code == 400
            data = response.json()
            assert "Invalid arguments" in data["detail"]
    
    def test_smart_query_execution_failure(self, client):
        """Test smart query when execution fails."""
        with patch('services.db_router_svc.main.get_query_router') as mock_get_router, \
             patch('services.db_router_svc.main.validate_intent_args') as mock_validate, \
             patch('services.db_router_svc.main.execute_intent_query') as mock_execute:
            
            mock_router = AsyncMock()
            mock_router.route_query.return_value = RouteResponse(
                intent=Intent.FLIGHT_STATUS,
                args={"flight_no": "NZ278"},
                confidence=0.95
            )
            mock_get_router.return_value = mock_router
            
            mock_validate.return_value = True
            mock_execute.side_effect = Exception("Database error")
            
            response = client.post("/smart-query", json={
                "text": "Test query",
                "auth": {"role": "public"}
            })
            
            assert response.status_code == 500
            data = response.json()
            assert "Smart query failed" in data["detail"]
    
    def test_smart_query_default_auth(self, client):
        """Test smart query with default auth role."""
        with patch('services.db_router_svc.main.get_query_router') as mock_get_router, \
             patch('services.db_router_svc.main.validate_intent_args') as mock_validate, \
             patch('services.db_router_svc.main.execute_intent_query') as mock_execute, \
             patch('services.db_router_svc.main.get_llm_client') as mock_get_llm, \
             patch('services.db_router_svc.main.format_query_answer') as mock_format:
            
            # Mock dependencies
            mock_router = AsyncMock()
            mock_router.route_query.return_value = RouteResponse(
                intent=Intent.FLIGHT_STATUS,
                args={"flight_no": "NZ278"},
                confidence=0.95
            )
            mock_get_router.return_value = mock_router
            
            mock_llm = AsyncMock()
            mock_get_llm.return_value = mock_llm
            
            mock_validate.return_value = True
            mock_execute.return_value = ([{"test": "data"}], 1)
            mock_format.return_value = "Test answer"
            
            # Request without auth field
            response = client.post("/smart-query", json={"text": "Test query"})
            
            assert response.status_code == 200
            # Verify that execute_intent_query was called with "public" role
            mock_execute.assert_called_once()
            call_args = mock_execute.call_args
            assert call_args[0][2] == "public"  # role parameter


class TestListIntentsEndpoint:
    """Test /intents endpoint."""
    
    def test_list_intents(self, client):
        """Test listing all supported intents."""
        response = client.get("/intents")
        
        assert response.status_code == 200
        data = response.json()
        assert "intents" in data
        assert "count" in data
        assert len(data["intents"]) == len(Intent)
        assert "flight_status" in data["intents"]
        assert "next_flight" in data["intents"]
        assert "knowledge_base" in data["intents"]


class TestAnswerFormatting:
    """Test answer formatting functionality."""
    
    @pytest.mark.asyncio
    async def test_format_query_answer_success(self):
        """Test successful answer formatting."""
        from ..main import format_query_answer
        
        class DummyLLM:
            def __init__(self):
                self.calls = 0

            async def chat_completion_async(self, **kwargs):
                self.calls += 1
                return {"content": "Flight NZ278 is on time"}

        mock_llm_client = DummyLLM()
        
        result = await format_query_answer(
            Intent.FLIGHT_STATUS,
            {"flight_no": "NZ278"},
            [{"flight_no": "NZ278", "status": "on_time"}],
            mock_llm_client
        )
        
        assert result == "Flight NZ278 is on time"
        assert mock_llm_client.calls == 1
    
    @pytest.mark.asyncio
    async def test_format_query_answer_no_results(self):
        """Test answer formatting with no results."""
        from ..main import format_query_answer
        
        class DummyLLM:
            def __init__(self):
                self.calls = 0

            async def chat_completion_async(self, **kwargs):
                self.calls += 1
                return {"content": "Should not be called"}

        mock_llm_client = DummyLLM()
        
        result = await format_query_answer(
            Intent.FLIGHT_STATUS,
            {"flight_no": "NZ278"},
            [],
            mock_llm_client
        )
        
        assert result == "No results found for your query."
        assert mock_llm_client.calls == 0
    
    @pytest.mark.asyncio
    async def test_format_query_answer_llm_failure(self):
        """Test answer formatting when LLM fails."""
        from ..main import format_query_answer
        
        class DummyLLM:
            def __init__(self):
                self.calls = 0

            async def chat_completion_async(self, **kwargs):
                self.calls += 1
                raise Exception("LLM error")

        mock_llm_client = DummyLLM()
        
        result = await format_query_answer(
            Intent.FLIGHT_STATUS,
            {"flight_no": "NZ278"},
            [{"flight_no": "NZ278", "status": "on_time"}],
            mock_llm_client
        )
        
        assert "Found 1 result(s)" in result
        assert "Please check the detailed results below" in result


class TestDependencyInjection:
    """Test dependency injection."""
    
    def test_get_llm_client_not_initialized(self, client):
        """Test LLM client dependency when not initialized."""
        with patch('services.db_router_svc.main.llm_client', None):
            response = client.post("/route", json={"text": "Test"})
            
            assert response.status_code == 503
            data = response.json()
            assert "LLM client not initialized" in data["detail"]
    
    def test_get_query_router_not_initialized(self, client):
        """Test query router dependency when not initialized."""
        with patch('services.db_router_svc.main.query_router', None):
            response = client.post("/route", json={"text": "Test"})
            
            assert response.status_code == 503
            data = response.json()
            assert "Query router not initialized" in data["detail"]


class TestErrorHandling:
    """Test error handling."""
    
    def test_global_exception_handler(self, client):
        """Test global exception handler."""
        with patch('services.db_router_svc.main.get_query_router') as mock_get_router:
            mock_router = AsyncMock()
            mock_router.route_query.side_effect = Exception("Unexpected error")
            mock_get_router.return_value = mock_router
            
            response = client.post("/route", json={"text": "Test"})
            
            assert response.status_code == 500
            data = response.json()
            assert data["detail"] == "Internal server error"
