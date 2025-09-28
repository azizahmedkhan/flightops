"""
Comprehensive test suite for the scalable chatbot service
"""

import asyncio
import json
import pytest
import httpx
import websockets
from datetime import datetime
from unittest.mock import Mock, patch, AsyncMock
import sys
import os

# Add the parent directory to the path so we can import the main module
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from main import app, manager, redis_manager, rate_limiter, llm_client
from chatbot_toolkit import (
    fetch_flight_context, 
    fetch_policy_context, 
    calculate_query_hash,
    sanitize_message,
    extract_entities,
    calculate_similarity_score,
    fetch_kb_context,
    route_query,
    format_kb_response
)


class TestChatbotService:
    """Test suite for the chatbot service"""
    
    @pytest.fixture
    async def client(self):
        """Create test client"""
        async with httpx.AsyncClient(app=app, base_url="http://test") as ac:
            yield ac
    
    @pytest.fixture
    async def mock_redis(self):
        """Mock Redis manager"""
        mock_redis = AsyncMock()
        mock_redis.get_session_context.return_value = {}
        mock_redis.set_session_context.return_value = None
        mock_redis.cache_response.return_value = None
        mock_redis.get_cached_response.return_value = None
        return mock_redis
    
    @pytest.fixture
    async def mock_llm_client(self):
        """Mock LLM client"""
        mock_llm = Mock()
        mock_llm.chat_completion.return_value = {
            "content": "Test response from ChatGPT",
            "tokens_used": 50,
            "duration_ms": 1000
        }
        return mock_llm


class TestWebSocketConnections(TestChatbotService):
    """Test WebSocket functionality"""
    
    @pytest.mark.asyncio
    async def test_websocket_connection(self):
        """Test basic WebSocket connection"""
        session_id = "test-session-123"
        client_id = "test-client-456"
        
        # This would require a WebSocket test client
        # For now, we'll test the connection manager directly
        mock_websocket = AsyncMock()
        mock_websocket.accept = AsyncMock()
        
        await manager.connect(mock_websocket, session_id, client_id)
        
        assert client_id in manager.active_connections
        assert session_id in manager.session_connections
        assert client_id in manager.session_connections[session_id]
        
        # Test disconnection
        manager.disconnect(client_id)
        assert client_id not in manager.active_connections
        assert client_id not in manager.session_connections[session_id]
    
    @pytest.mark.asyncio
    async def test_multiple_connections_per_session(self):
        """Test multiple clients connecting to same session"""
        session_id = "multi-session-123"
        client_ids = ["client-1", "client-2", "client-3"]
        
        for client_id in client_ids:
            mock_websocket = AsyncMock()
            mock_websocket.accept = AsyncMock()
            await manager.connect(mock_websocket, session_id, client_id)
        
        assert len(manager.session_connections[session_id]) == 3
        assert all(client_id in manager.active_connections for client_id in client_ids)
    
    @pytest.mark.asyncio
    async def test_connection_metadata(self):
        """Test connection metadata tracking"""
        session_id = "metadata-session-123"
        client_id = "metadata-client-456"
        
        mock_websocket = AsyncMock()
        mock_websocket.accept = AsyncMock()
        
        await manager.connect(mock_websocket, session_id, client_id)
        
        metadata = manager.connection_metadata[client_id]
        assert metadata["session_id"] == session_id
        assert "connected_at" in metadata
        assert "last_activity" in metadata


class TestSessionManagement(TestChatbotService):
    """Test session management functionality"""
    
    @pytest.mark.asyncio
    async def test_create_session(self, client):
        """Test session creation"""
        session_data = {
            "customer_name": "John Doe",
            "customer_email": "john@example.com",
            "flight_no": "NZ123",
            "date": "2025-01-17"
        }
        
        response = await client.post("/chat/session", json=session_data)
        assert response.status_code == 200
        
        data = response.json()
        assert "session_id" in data
        assert data["status"] == "created"
        assert data["context"]["customer_name"] == "John Doe"
    
    @pytest.mark.asyncio
    async def test_get_session(self, client):
        """Test getting session information"""
        # First create a session
        session_data = {
            "customer_name": "Jane Smith",
            "customer_email": "jane@example.com"
        }
        
        create_response = await client.post("/chat/session", json=session_data)
        session_id = create_response.json()["session_id"]
        
        # Then get the session
        response = await client.get(f"/chat/session/{session_id}")
        assert response.status_code == 200
        
        data = response.json()
        assert data["session_id"] == session_id
        assert data["context"]["customer_name"] == "Jane Smith"
    
    @pytest.mark.asyncio
    async def test_session_not_found(self, client):
        """Test getting non-existent session"""
        response = await client.get("/chat/session/non-existent-session")
        assert response.status_code == 404


class TestMessageProcessing(TestChatbotService):
    """Test message processing functionality"""
    
    @pytest.mark.asyncio
    async def test_send_message_rest(self, client):
        """Test sending message via REST API"""
        # Create a session first
        session_data = {
            "customer_name": "Test User",
            "customer_email": "test@example.com"
        }
        create_response = await client.post("/chat/session", json=session_data)
        session_id = create_response.json()["session_id"]
        
        # Send a message
        message_data = {
            "session_id": session_id,
            "message": "Hello, I need help with my flight",
            "client_id": "test-client"
        }
        
        response = await client.post("/chat/message", json=message_data)
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "message_sent"
        assert data["session_id"] == session_id
    
    @pytest.mark.asyncio
    async def test_message_sanitization(self):
        """Test message sanitization"""
        malicious_message = "<script>alert('xss')</script>Hello world"
        sanitized = sanitize_message(malicious_message)
        
        assert "<script>" not in sanitized
        assert "Hello world" in sanitized
        
        # Test length limiting
        long_message = "a" * 2000
        sanitized_long = sanitize_message(long_message)
        assert len(sanitized_long) <= 1000
    
    @pytest.mark.asyncio
    async def test_entity_extraction(self):
        """Test entity extraction from messages"""
        message = "My flight NZ123 is on 2025-01-17. Contact me at john@example.com or 555-123-4567"
        
        entities = extract_entities(message)
        
        assert "NZ123" in entities["flight_numbers"]
        assert "2025-01-17" in entities["dates"]
        assert "john@example.com" in entities["emails"]
        assert "555-123-4567" in entities["phone_numbers"]


class TestCachingAndRateLimiting(TestChatbotService):
    """Test caching and rate limiting functionality"""
    
    @pytest.mark.asyncio
    async def test_query_hash_calculation(self):
        """Test query hash calculation for caching"""
        session_id = "test-session"
        message = "Hello world"
        context = {"flight_no": "NZ123"}
        
        hash1 = calculate_query_hash(session_id, message, context)
        hash2 = calculate_query_hash(session_id, message, context)
        hash3 = calculate_query_hash(session_id, "Different message", context)
        
        assert hash1 == hash2  # Same inputs should produce same hash
        assert hash1 != hash3  # Different inputs should produce different hash
    
    @pytest.mark.asyncio
    async def test_rate_limiting(self):
        """Test rate limiting functionality"""
        key = "test-rate-limit-key"
        
        # Should not be rate limited initially
        assert not await rate_limiter.is_rate_limited(key, limit=5, window=60)
        
        # Make 5 requests (should hit the limit)
        for i in range(4):  # 4 more (total 5)
            assert not await rate_limiter.is_rate_limited(key, limit=5, window=60)
        
        # This should be rate limited
        assert await rate_limiter.is_rate_limited(key, limit=5, window=60)


class TestContextManagement(TestChatbotService):
    """Test context management functionality"""
    
    @pytest.mark.asyncio
    async def test_flight_context_fetching(self):
        """Test fetching flight context"""
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "flight_no": "NZ123",
                "status": "on time",
                "departure": "14:30"
            }
            
            mock_client.return_value.__aenter__.return_value.post.return_value = mock_response
            
            context = await fetch_flight_context("NZ123", "2025-01-17", "http://test-agent")
            
            assert context is not None
            assert context["flight_no"] == "NZ123"
    
    @pytest.mark.asyncio
    async def test_policy_context_fetching(self):
        """Test fetching policy context"""
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "results": [
                    {"title": "Refund Policy", "snippet": "Customers can get refunds..."}
                ]
            }
            
            mock_client.return_value.__aenter__.return_value.post.return_value = mock_response
            
            policies = await fetch_policy_context("refund policy", "http://test-knowledge-service")
            
            assert policies is not None
            assert len(policies) == 1
            assert policies[0]["title"] == "Refund Policy"


class TestUtilityFunctions(TestChatbotService):
    """Test utility functions"""
    
    def test_similarity_calculation(self):
        """Test text similarity calculation"""
        text1 = "Hello world"
        text2 = "Hello world"
        text3 = "Goodbye world"
        text4 = "Completely different"
        
        similarity1 = calculate_similarity_score(text1, text2)
        similarity2 = calculate_similarity_score(text1, text3)
        similarity3 = calculate_similarity_score(text1, text4)
        
        assert similarity1 == 1.0  # Identical
        assert similarity2 > similarity3  # Some overlap vs no overlap
        assert similarity3 == 0.0  # No overlap


class TestKnowledgeBaseIntegration(TestChatbotService):
    """Test knowledge base integration functionality"""
    
    @pytest.mark.asyncio
    async def test_fetch_kb_context(self):
        """Test fetching knowledge base context"""
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "results": [
                    {
                        "doc_id": 1,
                        "title": "Baggage Allowance Policy",
                        "snippet": "Passengers are allowed one carry-on bag...",
                        "source": "01_baggage_allowance.md",
                        "category": "customer",
                        "score": 0.95
                    }
                ]
            }
            
            mock_client.return_value.__aenter__.return_value.post.return_value = mock_response
            
            kb_chunks = await fetch_kb_context("baggage allowance", "http://test-knowledge-service")
            
            assert kb_chunks is not None
            assert len(kb_chunks) == 1
            assert kb_chunks[0]["title"] == "Baggage Allowance Policy"
            assert kb_chunks[0]["category"] == "customer"
    
    def test_route_query(self):
        """Test query routing logic"""
        # Test KB queries
        assert route_query("What is the baggage allowance policy?") == "kb"
        assert route_query("Tell me about check-in rules") == "kb"
        assert route_query("What are the refund policies?") == "kb"
        assert route_query("How do I get travel credits?") == "kb"
        
        # Test flight status queries
        assert route_query("Is my flight on time?") == "flight"
        assert route_query("What gate is my flight departing from?") == "flight"
        assert route_query("Has flight NZ123 departed?") == "flight"
        
        # Test mixed queries (should prefer KB)
        assert route_query("What is the policy for delayed flights?") == "kb"
        
        # Test general queries (default to KB)
        assert route_query("Hello, I need help") == "kb"
    
    def test_format_kb_response(self):
        """Test KB response formatting with citations"""
        chunks = [
            {
                "snippet": "Passengers are allowed one carry-on bag weighing up to 7kg.",
                "source": "01_baggage_allowance.md",
                "category": "customer"
            },
            {
                "snippet": "Excess baggage fees apply for additional items.",
                "source": "03_excess_fees.md", 
                "category": "customer"
            }
        ]
        
        sources = []
        response = format_kb_response(chunks, sources)
        
        # Check that response contains the snippets
        assert "Passengers are allowed one carry-on bag" in response
        assert "Excess baggage fees apply" in response
        
        # Check that sources are properly formatted
        assert len(sources) == 2
        assert "[1] 01_baggage_allowance.md (customer)" in sources
        assert "[2] 03_excess_fees.md (customer)" in sources
        
        # Check that sources are included in response
        assert "Sources:" in response
        assert "[1] 01_baggage_allowance.md (customer)" in response
    
    def test_format_kb_response_empty(self):
        """Test KB response formatting with empty chunks"""
        sources = []
        response = format_kb_response([], sources)
        
        assert "I don't have specific information" in response
        assert "contact our support team" in response
        assert len(sources) == 0
    
    @pytest.mark.asyncio
    async def test_kb_integration_flow(self, client):
        """Test complete KB integration flow"""
        with patch('httpx.AsyncClient') as mock_client:
            # Mock KB response
            mock_kb_response = Mock()
            mock_kb_response.status_code = 200
            mock_kb_response.json.return_value = {
                "results": [
                    {
                        "doc_id": 1,
                        "title": "Refund Policy",
                        "snippet": "Refunds are available within 24 hours of booking...",
                        "source": "15_policy_refunds_care.md",
                        "category": "customer",
                        "score": 0.92
                    }
                ]
            }
            
            # Mock LLM response
            mock_llm_response = Mock()
            mock_llm_response.status_code = 200
            mock_llm_response.json.return_value = {
                "content": "Based on our refund policy, you can get a refund within 24 hours of booking.",
                "tokens_used": 25,
                "duration_ms": 500
            }
            
            # Configure mock client to return different responses for different URLs
            async def mock_post(url, **kwargs):
                if "knowledge-engine" in url:
                    return mock_kb_response
                else:
                    return mock_llm_response
            
            mock_client.return_value.__aenter__.return_value.post = mock_post
            
            # Create a session
            session_data = {
                "customer_name": "KB Test User",
                "customer_email": "kb@test.com"
            }
            
            create_response = await client.post("/chat/session", json=session_data)
            session_id = create_response.json()["session_id"]
            
            # Send a KB query
            message_data = {
                "session_id": session_id,
                "message": "What is your refund policy?",
                "client_id": "kb-test-client"
            }
            
            response = await client.post("/chat/message", json=message_data)
            assert response.status_code == 200
            
            # Verify that the KB service was called
            assert mock_client.called


class TestHealthAndMetrics(TestChatbotService):
    """Test health check and metrics endpoints"""
    
    @pytest.mark.asyncio
    async def test_health_check(self, client):
        """Test health check endpoint"""
        response = await client.get("/health")
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "scalable-chatbot-svc"
        assert "timestamp" in data
        assert "active_connections" in data
    
    @pytest.mark.asyncio
    async def test_metrics_endpoint(self, client):
        """Test metrics endpoint"""
        response = await client.get("/metrics")
        assert response.status_code == 200
        
        data = response.json()
        assert "active_connections" in data
        assert "active_sessions" in data
        assert "timestamp" in data
    
    @pytest.mark.asyncio
    async def test_test_endpoint(self, client):
        """Test test endpoint"""
        response = await client.get("/test")
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "ok"
        assert data["service"] == "scalable-chatbot-svc"


# Integration Tests
class TestIntegration(TestChatbotService):
    """Integration tests for the full chatbot flow"""
    
    @pytest.mark.asyncio
    async def test_full_chat_flow(self, client, mock_redis, mock_llm_client):
        """Test complete chat flow from session creation to message processing"""
        with patch('main.redis_manager', mock_redis), \
             patch('main.llm_client', mock_llm_client):
            
            # 1. Create session
            session_data = {
                "customer_name": "Integration Test User",
                "customer_email": "integration@test.com",
                "flight_no": "NZ456",
                "date": "2025-01-17"
            }
            
            create_response = await client.post("/chat/session", json=session_data)
            assert create_response.status_code == 200
            
            session_id = create_response.json()["session_id"]
            
            # 2. Send message
            message_data = {
                "session_id": session_id,
                "message": "Is my flight on time?",
                "client_id": "integration-client"
            }
            
            send_response = await client.post("/chat/message", json=message_data)
            assert send_response.status_code == 200
            
            # 3. Verify session context was updated
            assert mock_redis.set_session_context.called
            
            # 4. Verify LLM was called
            assert mock_llm_client.chat_completion.called


# Performance Tests
class TestPerformance(TestChatbotService):
    """Performance and load testing"""
    
    @pytest.mark.asyncio
    async def test_concurrent_sessions(self, client):
        """Test creating multiple sessions concurrently"""
        session_data_list = [
            {
                "customer_name": f"User {i}",
                "customer_email": f"user{i}@test.com",
                "flight_no": f"NZ{i:03d}"
            }
            for i in range(10)
        ]
        
        # Create sessions concurrently
        tasks = [
            client.post("/chat/session", json=session_data)
            for session_data in session_data_list
        ]
        
        responses = await asyncio.gather(*tasks)
        
        # All should succeed
        for response in responses:
            assert response.status_code == 200
            assert "session_id" in response.json()
    
    @pytest.mark.asyncio
    async def test_message_processing_performance(self):
        """Test message processing performance"""
        start_time = asyncio.get_event_loop().time()
        
        # Simulate processing multiple messages
        messages = [f"Test message {i}" for i in range(100)]
        
        sanitized_messages = [sanitize_message(msg) for msg in messages]
        
        end_time = asyncio.get_event_loop().time()
        processing_time = end_time - start_time
        
        # Should process 100 messages in less than 1 second
        assert processing_time < 1.0
        assert len(sanitized_messages) == 100


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
