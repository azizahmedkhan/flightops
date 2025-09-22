"""
Pytest configuration and fixtures for db-router-svc tests.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock
import os
import sys

# Add the parent directory to the path so we can import the service modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def mock_database_url():
    """Mock database URL for testing."""
    return "postgresql://test:test@localhost:5432/test"


@pytest.fixture
def mock_llm_response():
    """Mock LLM response for testing."""
    return {
        "function_call": {
            "name": "route_query",
            "arguments": '{"intent": "flight_status", "args": {"flight_no": "NZ278", "date": null}, "confidence": 0.95}'
        }
    }


@pytest.fixture
def mock_database_rows():
    """Mock database rows for testing."""
    return [
        {
            "flight_no": "NZ278",
            "flight_date": "2024-01-15",
            "origin": "AKL",
            "destination": "WLG",
            "sched_dep_time": "2024-01-15 14:30:00",
            "sched_arr_time": "2024-01-15 15:45:00",
            "status": "on_time",
            "tail_number": "ZK-NZQ"
        },
        {
            "flight_no": "NZ280",
            "flight_date": "2024-01-15",
            "origin": "AKL",
            "destination": "CHC",
            "sched_dep_time": "2024-01-15 18:45:00",
            "sched_arr_time": "2024-01-15 20:00:00",
            "status": "delayed",
            "tail_number": "ZK-NZR"
        }
    ]


@pytest.fixture
def mock_booking_rows():
    """Mock booking rows for testing."""
    return [
        {
            "pnr": "ABC123",
            "passenger_name": "John Smith",
            "flight_no": "NZ278",
            "flight_date": "2024-01-15",
            "has_connection": False,
            "connecting_flight_no": None
        },
        {
            "pnr": "DEF456",
            "passenger_name": "Jane Doe",
            "flight_no": "NZ280",
            "flight_date": "2024-01-15",
            "has_connection": True,
            "connecting_flight_no": "NZ282"
        }
    ]


@pytest.fixture
def mock_crew_rows():
    """Mock crew rows for testing."""
    return [
        {
            "crew_id": "C001",
            "crew_name": "Captain Smith",
            "flight_no": "NZ278",
            "flight_date": "2024-01-15",
            "crew_role": "captain"
        },
        {
            "crew_id": "C002",
            "crew_name": "First Officer Jones",
            "flight_no": "NZ278",
            "flight_date": "2024-01-15",
            "crew_role": "first_officer"
        }
    ]


@pytest.fixture
def mock_aircraft_rows():
    """Mock aircraft status rows for testing."""
    return [
        {
            "tail_number": "ZK-NZQ",
            "current_location": "AKL",
            "status": "in_service"
        },
        {
            "tail_number": "ZK-NZR",
            "current_location": "WLG",
            "status": "maintenance"
        }
    ]


@pytest.fixture
def sample_queries():
    """Sample queries for testing."""
    return {
        "flight_status": [
            "What's the status of NZ278?",
            "Is flight NZ 278 on time?",
            "NZ278 status"
        ],
        "next_flight": [
            "When is the next flight to Wellington?",
            "Next flight to WLG from Auckland",
            "Show me flights to Christchurch tomorrow"
        ],
        "flights_from": [
            "Show me flights from Auckland",
            "What flights depart from AKL today?",
            "Flights from Auckland to anywhere"
        ],
        "flights_to": [
            "Show me flights to Wellington",
            "What flights arrive at WLG?",
            "Flights to Christchurch from anywhere"
        ],
        "booking_lookup": [
            "Look up booking ABC123",
            "Find reservation DEF456",
            "Booking details for PNR GHI789"
        ],
        "crew_for_flight": [
            "Who is crewed on NZ278?",
            "Show me crew for flight NZ 280 on 2024-01-15",
            "Crew assignment for NZ278"
        ],
        "aircraft_status": [
            "What's the status of aircraft ZK-NZQ?",
            "Show me aircraft ZK-NZR status",
            "Aircraft ZK-NZQ information"
        ],
        "passenger_count": [
            "How many passengers on NZ278?",
            "Passenger count for flight NZ 280",
            "Number of passengers on NZ278 today"
        ],
        "crew_availability": [
            "Who is available for duty tomorrow?",
            "Available pilots for 2024-01-15",
            "Show me available crew next week"
        ],
        "aircraft_by_location": [
            "What aircraft are at Auckland?",
            "Show me aircraft at AKL",
            "Aircraft currently at Wellington airport"
        ]
    }


@pytest.fixture
def mock_environment():
    """Mock environment variables for testing."""
    return {
        "DATABASE_URL": "postgresql://test:test@localhost:5432/test",
        "OPENAI_API_KEY": "test-api-key",
        "CHAT_MODEL": "gpt-4o-mini"
    }


@pytest.fixture(autouse=True)
def setup_test_environment(mock_environment):
    """Set up test environment variables."""
    for key, value in mock_environment.items():
        os.environ[key] = value
    yield
    # Clean up after test
    for key in mock_environment.keys():
        if key in os.environ:
            del os.environ[key]


@pytest.fixture
def mock_asyncpg_pool():
    """Mock asyncpg connection pool."""
    pool = AsyncMock()
    connection = AsyncMock()
    
    # Mock connection methods
    connection.fetch.return_value = []
    connection.fetchval.return_value = 1
    connection.execute.return_value = "OK"
    
    # Mock pool context manager
    pool.acquire.return_value.__aenter__.return_value = connection
    pool.acquire.return_value.__aexit__.return_value = None
    pool.close.return_value = None
    pool.get_size.return_value = 5
    
    return pool


@pytest.fixture
def mock_llm_client():
    """Mock LLM client for testing."""
    client = AsyncMock()
    client.call_function.return_value = {
        "function_call": {
            "name": "route_query",
            "arguments": '{"intent": "flight_status", "args": {"flight_no": "NZ278", "date": null}, "confidence": 0.95}'
        }
    }
    client.generate_response.return_value = "Flight NZ278 is on time"
    return client


@pytest.fixture
def mock_query_router():
    """Mock query router for testing."""
    router = AsyncMock()
    router.route_query.return_value = {
        "intent": "flight_status",
        "args": {"flight_no": "NZ278", "date": None},
        "confidence": 0.95
    }
    return router


@pytest.fixture
def mock_database_executor():
    """Mock database executor for testing."""
    executor = AsyncMock()
    executor.execute_query.return_value = ([{"test": "data"}], 1)
    executor.test_connection.return_value = True
    executor.pool = AsyncMock()
    executor.pool.get_size.return_value = 5
    executor.max_connections = 10
    return executor


# Pytest configuration
def pytest_configure(config):
    """Configure pytest."""
    config.addinivalue_line(
        "markers", "asyncio: mark test as async"
    )
    config.addinivalue_line(
        "markers", "unit: mark test as unit test"
    )
    config.addinivalue_line(
        "markers", "integration: mark test as integration test"
    )


def pytest_collection_modifyitems(config, items):
    """Modify test collection to add markers."""
    for item in items:
        # Add unit marker to all tests by default
        if not any(marker.name == "unit" or marker.name == "integration" for marker in item.iter_markers()):
            item.add_marker(pytest.mark.unit)
        
        # Add asyncio marker to async tests
        if asyncio.iscoroutinefunction(item.function):
            item.add_marker(pytest.mark.asyncio)
