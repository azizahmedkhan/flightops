"""
Tests for db-router-svc SQL execution functionality.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import asyncio

from ..execute import (
    DatabaseExecutor, initialize_database, close_database, 
    execute_intent_query, get_database_health, validate_intent_args,
    get_supported_intents
)
from ..models import Intent


class TestDatabaseExecutor:
    """Test DatabaseExecutor class."""
    
    @pytest.fixture
    def mock_pool(self):
        """Create a mock database pool."""
        pool = AsyncMock()
        pool.acquire.return_value.__aenter__.return_value = AsyncMock()
        pool.get_size.return_value = 5
        return pool
    
    @pytest.fixture
    def executor(self, mock_pool):
        """Create a DatabaseExecutor with mock pool."""
        executor = DatabaseExecutor("postgresql://test:test@localhost:5432/test")
        executor.pool = mock_pool
        return executor
    
    def test_initialization(self):
        """Test executor initialization."""
        executor = DatabaseExecutor("postgresql://test:test@localhost:5432/test")
        assert executor.database_url == "postgresql://test:test@localhost:5432/test"
        assert executor.max_connections == 10
        assert executor.pool is None
    
    def test_initialization_custom_max_connections(self):
        """Test executor initialization with custom max connections."""
        executor = DatabaseExecutor("postgresql://test:test@localhost:5432/test", max_connections=20)
        assert executor.max_connections == 20
    
    @pytest.mark.asyncio
    async def test_initialize(self, executor):
        """Test database pool initialization."""
        with patch('asyncpg.create_pool') as mock_create_pool:
            mock_pool = AsyncMock()
            mock_create_pool.return_value = mock_pool
            
            await executor.initialize()
            
            assert executor.pool == mock_pool
            mock_create_pool.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_close(self, executor):
        """Test database pool closure."""
        mock_pool = AsyncMock()
        executor.pool = mock_pool
        
        await executor.close()
        
        mock_pool.close.assert_called_once()
        assert executor.pool is None
    
    @pytest.mark.asyncio
    async def test_execute_query_success(self, executor):
        """Test successful query execution."""
        # Mock database response
        mock_rows = [
            {"flight_no": "NZ278", "status": "on_time"},
            {"flight_no": "NZ280", "status": "delayed"}
        ]
        mock_conn = AsyncMock()
        mock_conn.fetch.return_value = mock_rows
        executor.pool.acquire.return_value.__aenter__.return_value = mock_conn
        
        rows, count = await executor.execute_query(
            Intent.FLIGHT_STATUS,
            {"flight_no": "NZ278", "date": None},
            "public"
        )
        
        assert len(rows) == 2
        assert count == 2
        assert rows[0]["flight_no"] == "NZ278"
        assert rows[1]["flight_no"] == "NZ280"
    
    @pytest.mark.asyncio
    async def test_execute_query_pii_masking(self, executor):
        """Test PII masking based on role."""
        # Mock database response with PII
        mock_rows = [
            {"passenger_name": "John Smith", "pnr": "ABC123"},
            {"passenger_name": "Jane Doe", "pnr": "DEF456"}
        ]
        mock_conn = AsyncMock()
        mock_conn.fetch.return_value = mock_rows
        executor.pool.acquire.return_value.__aenter__.return_value = mock_conn
        
        # Test with public role (should mask PII)
        rows, count = await executor.execute_query(
            Intent.BOOKING_LOOKUP,
            {"pnr": "ABC123"},
            "public"
        )
        
        assert len(rows) == 2
        assert rows[0]["passenger_name"] == "J***h"  # Masked
        assert rows[1]["passenger_name"] == "J***e"  # Masked
        
        # Test with agent role (should not mask PII)
        rows, count = await executor.execute_query(
            Intent.BOOKING_LOOKUP,
            {"pnr": "ABC123"},
            "agent"
        )
        
        assert len(rows) == 2
        assert rows[0]["passenger_name"] == "John Smith"  # Not masked
        assert rows[1]["passenger_name"] == "Jane Doe"  # Not masked
    
    @pytest.mark.asyncio
    async def test_execute_query_timeout(self, executor):
        """Test query timeout handling."""
        mock_conn = AsyncMock()
        mock_conn.fetch.side_effect = asyncio.TimeoutError()
        executor.pool.acquire.return_value.__aenter__.return_value = mock_conn
        
        with pytest.raises(RuntimeError, match="Query execution timeout"):
            await executor.execute_query(
                Intent.FLIGHT_STATUS,
                {"flight_no": "NZ278"},
                "public"
            )
    
    @pytest.mark.asyncio
    async def test_execute_query_database_error(self, executor):
        """Test database error handling."""
        mock_conn = AsyncMock()
        mock_conn.fetch.side_effect = Exception("Database error")
        executor.pool.acquire.return_value.__aenter__.return_value = mock_conn
        
        with pytest.raises(Exception, match="Database error"):
            await executor.execute_query(
                Intent.FLIGHT_STATUS,
                {"flight_no": "NZ278"},
                "public"
            )
    
    @pytest.mark.asyncio
    async def test_execute_query_invalid_intent(self, executor):
        """Test handling of invalid intent."""
        with pytest.raises(ValueError, match="Unknown intent"):
            await executor.execute_query(
                "invalid_intent",
                {"flight_no": "NZ278"},
                "public"
            )
    
    @pytest.mark.asyncio
    async def test_execute_query_pool_not_initialized(self, executor):
        """Test error when pool is not initialized."""
        executor.pool = None
        
        with pytest.raises(RuntimeError, match="Database pool not initialized"):
            await executor.execute_query(
                Intent.FLIGHT_STATUS,
                {"flight_no": "NZ278"},
                "public"
            )
    
    @pytest.mark.asyncio
    async def test_test_connection_success(self, executor):
        """Test successful connection test."""
        mock_conn = AsyncMock()
        mock_conn.fetchval.return_value = 1
        executor.pool.acquire.return_value.__aenter__.return_value = mock_conn
        
        result = await executor.test_connection()
        assert result is True
    
    @pytest.mark.asyncio
    async def test_test_connection_failure(self, executor):
        """Test connection test failure."""
        mock_conn = AsyncMock()
        mock_conn.fetchval.side_effect = Exception("Connection failed")
        executor.pool.acquire.return_value.__aenter__.return_value = mock_conn
        
        result = await executor.test_connection()
        assert result is False
    
    @pytest.mark.asyncio
    async def test_test_connection_no_pool(self, executor):
        """Test connection test when pool is not initialized."""
        executor.pool = None
        
        result = await executor.test_connection()
        assert result is False


class TestGlobalFunctions:
    """Test global database functions."""
    
    @pytest.mark.asyncio
    async def test_initialize_database(self):
        """Test global database initialization."""
        with patch('services.db_router_svc.execute.DatabaseExecutor') as mock_executor_class:
            mock_executor = AsyncMock()
            mock_executor_class.return_value = mock_executor
            
            await initialize_database("postgresql://test:test@localhost:5432/test")
            
            mock_executor_class.assert_called_once_with("postgresql://test:test@localhost:5432/test")
            mock_executor.initialize.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_close_database(self):
        """Test global database closure."""
        with patch('services.db_router_svc.execute._executor') as mock_executor:
            mock_executor.close = AsyncMock()
            
            await close_database()
            
            mock_executor.close.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_execute_intent_query(self):
        """Test global intent query execution."""
        with patch('services.db_router_svc.execute._executor') as mock_executor:
            mock_executor.execute_query = AsyncMock(return_value=([{"test": "data"}], 1))
            
            rows, count = await execute_intent_query(
                Intent.FLIGHT_STATUS,
                {"flight_no": "NZ278"},
                "public"
            )
            
            assert len(rows) == 1
            assert count == 1
            assert rows[0]["test"] == "data"
            mock_executor.execute_query.assert_called_once_with(
                Intent.FLIGHT_STATUS,
                {"flight_no": "NZ278"},
                "public"
            )
    
    @pytest.mark.asyncio
    async def test_execute_intent_query_no_executor(self):
        """Test intent query execution when executor is not initialized."""
        with patch('services.db_router_svc.execute._executor', None):
            with pytest.raises(RuntimeError, match="Database not initialized"):
                await execute_intent_query(
                    Intent.FLIGHT_STATUS,
                    {"flight_no": "NZ278"},
                    "public"
                )
    
    @pytest.mark.asyncio
    async def test_get_database_health_healthy(self):
        """Test database health check when healthy."""
        with patch('services.db_router_svc.execute._executor') as mock_executor:
            mock_executor.test_connection = AsyncMock(return_value=True)
            mock_executor.pool.get_size.return_value = 5
            mock_executor.max_connections = 10
            
            health = await get_database_health()
            
            assert health["status"] == "healthy"
            assert health["pool_size"] == 5
            assert health["max_connections"] == 10
    
    @pytest.mark.asyncio
    async def test_get_database_health_unhealthy(self):
        """Test database health check when unhealthy."""
        with patch('services.db_router_svc.execute._executor') as mock_executor:
            mock_executor.test_connection = AsyncMock(return_value=False)
            mock_executor.pool.get_size.return_value = 0
            mock_executor.max_connections = 10
            
            health = await get_database_health()
            
            assert health["status"] == "unhealthy"
            assert health["pool_size"] == 0
            assert health["max_connections"] == 10
    
    @pytest.mark.asyncio
    async def test_get_database_health_no_executor(self):
        """Test database health check when executor is not initialized."""
        with patch('services.db_router_svc.execute._executor', None):
            health = await get_database_health()
            
            assert health["status"] == "unavailable"
            assert "error" in health
    
    @pytest.mark.asyncio
    async def test_get_database_health_exception(self):
        """Test database health check when exception occurs."""
        with patch('services.db_router_svc.execute._executor') as mock_executor:
            mock_executor.test_connection = AsyncMock(side_effect=Exception("Test error"))
            
            health = await get_database_health()
            
            assert health["status"] == "unhealthy"
            assert "error" in health
    
    def test_get_supported_intents(self):
        """Test getting supported intents."""
        intents = get_supported_intents()
        
        assert len(intents) == 10
        assert Intent.FLIGHT_STATUS in intents
        assert Intent.NEXT_FLIGHT in intents
        assert Intent.BOOKING_LOOKUP in intents
    
    def test_validate_intent_args_valid(self):
        """Test validation of valid intent arguments."""
        # Test valid args for flight_status
        assert validate_intent_args(Intent.FLIGHT_STATUS, {
            "flight_no": "NZ278",
            "date": "2024-01-15"
        }) is True
        
        # Test valid args for next_flight
        assert validate_intent_args(Intent.NEXT_FLIGHT, {
            "destination": "WLG",
            "origin": "AKL",
            "after_time": "now"
        }) is True
    
    def test_validate_intent_args_invalid_intent(self):
        """Test validation with invalid intent."""
        assert validate_intent_args("invalid_intent", {}) is False
    
    def test_validate_intent_args_missing_required(self):
        """Test validation with missing required arguments."""
        # Missing required flight_no for flight_status
        assert validate_intent_args(Intent.FLIGHT_STATUS, {
            "date": "2024-01-15"
        }) is False
        
        # Missing required destination for next_flight
        assert validate_intent_args(Intent.NEXT_FLIGHT, {
            "origin": "AKL",
            "after_time": "now"
        }) is False


class TestSQLTemplates:
    """Test SQL template definitions."""
    
    def test_all_intents_have_sql_templates(self):
        """Test that all intents have corresponding SQL templates."""
        from ..execute import INTENT_SQL
        
        for intent in Intent:
            assert intent in INTENT_SQL
            sql_template, param_names = INTENT_SQL[intent]
            assert isinstance(sql_template, str)
            assert isinstance(param_names, list)
            assert len(param_names) > 0
    
    def test_sql_templates_use_parameterized_queries(self):
        """Test that SQL templates use parameterized queries."""
        from ..execute import INTENT_SQL
        
        for intent, (sql_template, param_names) in INTENT_SQL.items():
            # Check that template uses $1, $2, etc. parameters
            assert "$1" in sql_template
            # Check that we don't have string interpolation
            assert "%s" not in sql_template
            assert "{}" not in sql_template
            assert f"{param_names[0]}" not in sql_template
    
    def test_sql_templates_have_limits(self):
        """Test that SQL templates have appropriate LIMIT clauses."""
        from ..execute import INTENT_SQL
        
        for intent, (sql_template, _) in INTENT_SQL.items():
            # Most queries should have LIMIT clauses for safety
            if intent not in [Intent.PASSENGER_COUNT]:  # Some queries might not need limits
                assert "LIMIT" in sql_template.upper()
