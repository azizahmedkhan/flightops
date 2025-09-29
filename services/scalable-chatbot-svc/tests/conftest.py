"""
Pytest configuration and fixtures for chatbot tests
"""

import pytest
import asyncio
import httpx
from unittest.mock import AsyncMock, Mock
import os
import sys

# Add the parent directory to the path
sys.path.append(os.path.dirname(os.path.dirname(__file__)))


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
async def mock_redis():
    """Mock Redis client for testing"""
    mock_redis = AsyncMock()
    mock_redis.hgetall.return_value = {}
    mock_redis.hset.return_value = None
    mock_redis.setex.return_value = None
    mock_redis.get.return_value = None
    mock_redis.ping.return_value = True
    return mock_redis


@pytest.fixture
async def mock_llm_client():
    """Mock LLM client for testing"""
    mock_llm = Mock()
    mock_llm.chat_completion.return_value = {
        "content": '{"response_to_customer": "Hello! How can I help you today?", "analysis": {"sentiment": "neutral", "sentiment_score": 0.0, "urgency_level": "low"}}',
        "tokens_used": 50,
        "duration_ms": 1000
    }
    return mock_llm


@pytest.fixture
async def mock_httpx_client():
    """Mock HTTPX client for testing"""
    mock_client = AsyncMock()
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"status": "success"}
    mock_client.post.return_value = mock_response
    mock_client.get.return_value = mock_response
    return mock_client


@pytest.fixture
def sample_session_data():
    """Sample session data for testing"""
    return {
        "customer_name": "Test Customer",
        "customer_email": "test@example.com",
        "flight_no": "NZ123",
        "date": "2025-01-17"
    }


@pytest.fixture
def sample_message_data():
    """Sample message data for testing"""
    return {
        "session_id": "test-session-123",
        "message": "Hello, I need help with my flight",
        "client_id": "test-client-456"
    }


@pytest.fixture
def sample_chatgpt_response():
    """Sample ChatGPT response for testing"""
    return {
        "response_to_customer": "Hello! I'd be happy to help you with your flight. Let me check the details for you.",
        "analysis": {
            "sentiment": "neutral",
            "sentiment_score": 0.2,
            "key_emotions_detected": ["curiosity"],
            "urgency_level": "low",
            "recommended_response_tone": "empathetic",
            "key_concerns": ["flight assistance"]
        }
    }


@pytest.fixture
async def test_app():
    """Test FastAPI app instance"""
    from main import app
    return app


@pytest.fixture
async def test_client(test_app):
    """Test HTTP client"""
    async with httpx.AsyncClient(app=test_app, base_url="http://test") as client:
        yield client


@pytest.fixture
def mock_websocket():
    """Mock WebSocket for testing"""
    mock_ws = AsyncMock()
    mock_ws.accept = AsyncMock()
    mock_ws.send_text = AsyncMock()
    mock_ws.receive_text = AsyncMock(return_value='{"message": "test message"}')
    return mock_ws


@pytest.fixture
def mock_connection_manager():
    """Mock connection manager for testing"""
    mock_manager = AsyncMock()
    mock_manager.active_connections = {}
    mock_manager.session_connections = {}
    mock_manager.connection_metadata = {}
    mock_manager.connect = AsyncMock()
    mock_manager.disconnect = Mock()
    mock_manager.send_personal_message = AsyncMock()
    mock_manager.send_to_session = AsyncMock()
    mock_manager.broadcast = AsyncMock()
    return mock_manager


# Performance testing fixtures
@pytest.fixture
def load_test_config():
    """Configuration for load testing"""
    return {
        "small_load": {"users": 10, "duration": 30},
        "medium_load": {"users": 100, "duration": 60},
        "high_load": {"users": 500, "duration": 120},
        "extreme_load": {"users": 1000, "duration": 180}
    }


@pytest.fixture
def performance_thresholds():
    """Performance thresholds for testing"""
    return {
        "small_load": {
            "min_success_rate": 90,
            "max_avg_response_time": 5.0,
            "min_requests_per_second": 1.0
        },
        "medium_load": {
            "min_success_rate": 80,
            "max_avg_response_time": 10.0,
            "max_p95_response_time": 15.0
        },
        "high_load": {
            "min_success_rate": 70,
            "max_avg_response_time": 20.0,
            "max_p95_response_time": 30.0
        },
        "extreme_load": {
            "min_success_rate": 60,
            "max_avg_response_time": 30.0,
            "max_p99_response_time": 60.0
        }
    }


# Database fixtures (for future use)
@pytest.fixture
async def mock_database():
    """Mock database for testing"""
    mock_db = AsyncMock()
    mock_db.fetch_one.return_value = None
    mock_db.fetch_all.return_value = []
    mock_db.execute.return_value = None
    return mock_db


# Cache fixtures
@pytest.fixture
async def mock_cache():
    """Mock cache for testing"""
    mock_cache = AsyncMock()
    mock_cache.get.return_value = None
    mock_cache.set.return_value = None
    mock_cache.delete.return_value = None
    mock_cache.exists.return_value = False
    return mock_cache


# Rate limiting fixtures
@pytest.fixture
def mock_rate_limiter():
    """Mock rate limiter for testing"""
    mock_limiter = AsyncMock()
    mock_limiter.is_rate_limited.return_value = False
    return mock_limiter


# Environment fixtures
@pytest.fixture
def test_environment():
    """Test environment variables"""
    return {
        "OPENAI_API_KEY": "test-api-key",
        "REDIS_URL": "redis://localhost:6379",
        "CHAT_MODEL": "gpt-4o-mini",
        "LOG_LEVEL": "DEBUG"
    }


# Utility fixtures
@pytest.fixture
def sample_entities():
    """Sample extracted entities for testing"""
    return {
        "flight_numbers": ["NZ123", "AA456"],
        "dates": ["2025-01-17", "01/17/2025"],
        "emails": ["test@example.com", "user@test.org"],
        "phone_numbers": ["555-123-4567", "(555) 987-6543"]
    }


@pytest.fixture
def sample_context():
    """Sample session context for testing"""
    return {
        "session_id": "test-session-123",
        "customer_name": "Test Customer",
        "customer_email": "test@example.com",
        "flight_no": "NZ123",
        "date": "2025-01-17",
        "created_at": "2025-01-16T10:00:00Z",
        "last_activity": "2025-01-16T10:30:00Z",
        "message_count": 5,
        "flight_data": {
            "flight_no": "NZ123",
            "status": "on time",
            "departure": "14:30",
            "arrival": "16:45"
        },
        "policy_data": [
            {
                "title": "Refund Policy",
                "snippet": "Customers can get refunds within 24 hours..."
            }
        ]
    }


# Cleanup fixtures
@pytest.fixture(autouse=True)
async def cleanup_test_data():
    """Cleanup test data after each test"""
    yield
    # Add cleanup logic here if needed
    pass


# Markers for different test types
def pytest_configure(config):
    """Configure pytest markers"""
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )
    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests"
    )
    config.addinivalue_line(
        "markers", "load: marks tests as load tests"
    )
    config.addinivalue_line(
        "markers", "websocket: marks tests as WebSocket tests"
    )
