"""
Tests for db-router-svc router functionality.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import json

from ..router import QueryRouter
from ..models import Intent, RouteResponse


class TestQueryRouter:
    """Test QueryRouter class."""
    
    @pytest.fixture
    def mock_llm_client(self):
        """Create a mock LLM client."""
        client = AsyncMock()
        return client
    
    @pytest.fixture
    def query_router(self, mock_llm_client):
        """Create a QueryRouter instance with mock LLM client."""
        return QueryRouter(mock_llm_client)
    
    def test_function_schema_creation(self, query_router):
        """Test that function schema is created correctly."""
        schema = query_router.function_schema
        
        assert schema["name"] == "route_query"
        assert "description" in schema
        assert "parameters" in schema
        
        # Check that all intents are in the enum
        intent_enum = schema["parameters"]["properties"]["intent"]["enum"]
        expected_intents = [intent.value for intent in Intent]
        for intent in expected_intents:
            assert intent in intent_enum
    
    def test_extract_flight_number(self, query_router):
        """Test flight number extraction."""
        # Valid flight numbers
        assert query_router._extract_flight_number("NZ278") == "NZ278"
        assert query_router._extract_flight_number("NZ 278") == "NZ278"
        assert query_router._extract_flight_number("What's the status of NZ278?") == "NZ278"
        
        # Invalid flight numbers
        assert query_router._extract_flight_number("AA123") is None
        assert query_router._extract_flight_number("No flight here") is None
        assert query_router._extract_flight_number("") is None
    
    def test_normalize_city_names(self, query_router):
        """Test city name normalization."""
        # Test various city name patterns
        assert "AKL" in query_router._normalize_city_names("auckland")
        assert "WLG" in query_router._normalize_city_names("wellington")
        assert "CHC" in query_router._normalize_city_names("christchurch")
        assert "ZQN" in query_router._normalize_city_names("queenstown")
        
        # Test case insensitive
        assert "AKL" in query_router._normalize_city_names("AUCKLAND")
        assert "WLG" in query_router._normalize_city_names("Wellington")
    
    def test_extract_date_from_text(self, query_router):
        """Test date extraction from text."""
        # Test various date formats
        assert query_router._extract_date_from_text("2024-01-15") == "2024-01-15"
        assert query_router._extract_date_from_text("15/01/2024") == "2024-01-15"
        assert query_router._extract_date_from_text("15 Jan 2024") == "2024-01-15"
        
        # Test no date
        assert query_router._extract_date_from_text("No date here") is None
    
    @pytest.mark.asyncio
    async def test_route_query_flight_number_detection(self, query_router):
        """Test that flight numbers are detected and routed correctly."""
        response = await query_router.route_query("What's the status of NZ278?")
        
        assert response.intent == Intent.FLIGHT_STATUS
        assert response.args["flight_no"] == "NZ278"
        assert response.confidence == 0.95
    
    @pytest.mark.asyncio
    async def test_route_query_llm_routing(self, query_router, mock_llm_client):
        """Test LLM-based query routing."""
        # Mock LLM response
        mock_llm_client.call_function.return_value = {
            "function_call": {
                "name": "route_query",
                "arguments": json.dumps({
                    "intent": "next_flight",
                    "args": {
                        "destination": "WLG",
                        "origin": "AKL",
                        "after_time": "now"
                    },
                    "confidence": 0.85
                })
            }
        }
        
        response = await query_router.route_query("When is the next flight to Wellington?")
        
        assert response.intent == Intent.NEXT_FLIGHT
        assert response.args["destination"] == "WLG"
        assert response.args["origin"] == "AKL"
        assert response.confidence == 0.85
        
        # Verify LLM was called
        mock_llm_client.call_function.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_route_query_llm_failure_fallback(self, query_router, mock_llm_client):
        """Test fallback routing when LLM fails."""
        # Mock LLM failure
        mock_llm_client.call_function.side_effect = Exception("LLM error")
        
        response = await query_router.route_query("Some query")
        
        # Should fallback to a default response
        assert isinstance(response, RouteResponse)
        assert response.intent in Intent
        assert 0.0 <= response.confidence <= 1.0
    
    @pytest.mark.asyncio
    async def test_route_query_invalid_intent_fallback(self, query_router, mock_llm_client):
        """Test fallback when LLM returns invalid intent."""
        # Mock LLM response with invalid intent
        mock_llm_client.call_function.return_value = {
            "function_call": {
                "name": "route_query",
                "arguments": json.dumps({
                    "intent": "invalid_intent",
                    "args": {},
                    "confidence": 0.5
                })
            }
        }
        
        response = await query_router.route_query("Some query")
        
        # Should fallback to default response
        assert isinstance(response, RouteResponse)
        assert response.intent in Intent
    
    @pytest.mark.asyncio
    async def test_route_query_malformed_arguments(self, query_router, mock_llm_client):
        """Test handling of malformed LLM arguments."""
        # Mock LLM response with malformed JSON
        mock_llm_client.call_function.return_value = {
            "function_call": {
                "name": "route_query",
                "arguments": "invalid json"
            }
        }
        
        response = await query_router.route_query("Some query")
        
        # Should fallback to default response
        assert isinstance(response, RouteResponse)
        assert response.intent in Intent
    
    @pytest.mark.asyncio
    async def test_route_query_city_name_normalization(self, query_router, mock_llm_client):
        """Test that city names are normalized in the query."""
        # Mock LLM response
        mock_llm_client.call_function.return_value = {
            "function_call": {
                "name": "route_query",
                "arguments": json.dumps({
                    "intent": "flights_from",
                    "args": {
                        "origin": "Auckland",  # Should be normalized to AKL
                        "date": None
                    },
                    "confidence": 0.8
                })
            }
        }
        
        response = await query_router.route_query("Show me flights from Auckland")
        
        assert response.intent == Intent.FLIGHTS_FROM
        assert response.args["origin"] == "AKL"  # Should be normalized
    
    @pytest.mark.asyncio
    async def test_route_query_date_extraction(self, query_router, mock_llm_client):
        """Test that dates are extracted and added to args."""
        # Mock LLM response
        mock_llm_client.call_function.return_value = {
            "function_call": {
                "name": "route_query",
                "arguments": json.dumps({
                    "intent": "flights_from",
                    "args": {
                        "origin": "AKL",
                        "date": None  # Should be filled from text
                    },
                    "confidence": 0.8
                })
            }
        }
        
        response = await query_router.route_query("Show me flights from Auckland on 2024-01-15")
        
        assert response.intent == Intent.FLIGHTS_FROM
        assert response.args["origin"] == "AKL"
        assert response.args["date"] == "2024-01-15"  # Should be extracted
    
    @pytest.mark.asyncio
    async def test_route_query_time_normalization(self, query_router, mock_llm_client):
        """Test that time references are normalized."""
        # Mock LLM response
        mock_llm_client.call_function.return_value = {
            "function_call": {
                "name": "route_query",
                "arguments": json.dumps({
                    "intent": "next_flight",
                    "args": {
                        "destination": "WLG",
                        "origin": "AKL",
                        "after_time": "tomorrow"  # Should be normalized
                    },
                    "confidence": 0.8
                })
            }
        }
        
        response = await query_router.route_query("Next flight to Wellington tomorrow")
        
        assert response.intent == Intent.NEXT_FLIGHT
        assert response.args["destination"] == "WLG"
        assert response.args["after_time"] != "tomorrow"  # Should be normalized to timestamp
    
    def test_fallback_route_keywords(self, query_router):
        """Test fallback routing based on keywords."""
        # Test status keyword
        response = query_router._fallback_route("What's the status?")
        assert response.intent == Intent.FLIGHT_STATUS
        assert response.confidence == 0.3
        
        # Test next flight keyword
        response = query_router._fallback_route("Next flight to somewhere")
        assert response.intent == Intent.NEXT_FLIGHT
        assert response.confidence == 0.3
        
        # Test booking keyword
        response = query_router._fallback_route("Booking information")
        assert response.intent == Intent.BOOKING_LOOKUP
        assert response.confidence == 0.3
        
        # Test default fallback
        response = query_router._fallback_route("Random query")
        assert response.intent == Intent.FLIGHT_STATUS
        assert response.confidence == 0.1
    
    @pytest.mark.asyncio
    async def test_route_query_empty_text(self, query_router):
        """Test handling of empty query text."""
        with pytest.raises(ValueError):
            await query_router.route_query("")
        
        with pytest.raises(ValueError):
            await query_router.route_query(None)
    
    @pytest.mark.asyncio
    async def test_route_query_whitespace_text(self, query_router):
        """Test handling of whitespace-only query text."""
        with pytest.raises(ValueError):
            await query_router.route_query("   ")
        
        with pytest.raises(ValueError):
            await query_router.route_query("\t\n")
