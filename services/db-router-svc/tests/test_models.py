"""
Tests for db-router-svc models.
"""

import pytest
from datetime import datetime
from pydantic import ValidationError

from ..models import (
    Intent, RouteRequest, RouteResponse, SmartQueryRequest, SmartQueryResponse,
    HealthResponse, FlightStatusArgs, NextFlightArgs, FlightsFromArgs,
    FlightsToArgs, BookingLookupArgs, CrewForFlightArgs, AircraftStatusArgs,
    PassengerCountArgs, CrewAvailabilityArgs, AircraftByLocationArgs
)


class TestIntent:
    """Test Intent enum."""
    
    def test_intent_values(self):
        """Test that all expected intents are present."""
        expected_intents = [
            "flight_status", "next_flight", "flights_from", "flights_to",
            "booking_lookup", "crew_for_flight", "aircraft_status",
            "passenger_count", "crew_availability", "aircraft_by_location"
        ]
        
        for intent in expected_intents:
            assert hasattr(Intent, intent.upper())
            assert getattr(Intent, intent.upper()).value == intent


class TestRouteRequest:
    """Test RouteRequest model."""
    
    def test_valid_request(self):
        """Test valid route request."""
        request = RouteRequest(text="What's the status of NZ278?")
        assert request.text == "What's the status of NZ278?"
    
    def test_empty_text_validation(self):
        """Test that empty text is rejected."""
        with pytest.raises(ValidationError):
            RouteRequest(text="")
    
    def test_text_too_long_validation(self):
        """Test that text over 500 characters is rejected."""
        with pytest.raises(ValidationError):
            RouteRequest(text="x" * 501)


class TestRouteResponse:
    """Test RouteResponse model."""
    
    def test_valid_response(self):
        """Test valid route response."""
        response = RouteResponse(
            intent=Intent.FLIGHT_STATUS,
            args={"flight_no": "NZ278", "date": None},
            confidence=0.95
        )
        assert response.intent == Intent.FLIGHT_STATUS
        assert response.args == {"flight_no": "NZ278", "date": None}
        assert response.confidence == 0.95
    
    def test_confidence_validation(self):
        """Test confidence score validation."""
        # Valid confidence scores
        RouteResponse(intent=Intent.FLIGHT_STATUS, args={}, confidence=0.0)
        RouteResponse(intent=Intent.FLIGHT_STATUS, args={}, confidence=0.5)
        RouteResponse(intent=Intent.FLIGHT_STATUS, args={}, confidence=1.0)
        
        # Invalid confidence scores
        with pytest.raises(ValidationError):
            RouteResponse(intent=Intent.FLIGHT_STATUS, args={}, confidence=-0.1)
        
        with pytest.raises(ValidationError):
            RouteResponse(intent=Intent.FLIGHT_STATUS, args={}, confidence=1.1)


class TestSmartQueryRequest:
    """Test SmartQueryRequest model."""
    
    def test_valid_request(self):
        """Test valid smart query request."""
        request = SmartQueryRequest(
            text="When is the next flight to Wellington?",
            auth={"role": "agent"}
        )
        assert request.text == "When is the next flight to Wellington?"
        assert request.auth == {"role": "agent"}
    
    def test_default_auth(self):
        """Test default auth role."""
        request = SmartQueryRequest(text="Test query")
        assert request.auth == {"role": "public"}
    
    def test_invalid_auth_role(self):
        """Test invalid auth role validation."""
        with pytest.raises(ValidationError):
            SmartQueryRequest(
                text="Test query",
                auth={"role": "invalid_role"}
            )


class TestSmartQueryResponse:
    """Test SmartQueryResponse model."""
    
    def test_valid_response(self):
        """Test valid smart query response."""
        response = SmartQueryResponse(
            answer="Flight NZ278 is on time",
            rows=[{"flight_no": "NZ278", "status": "on_time"}],
            intent=Intent.FLIGHT_STATUS,
            args={"flight_no": "NZ278"},
            metadata={"row_count": 1}
        )
        assert response.answer == "Flight NZ278 is on time"
        assert len(response.rows) == 1
        assert response.intent == Intent.FLIGHT_STATUS


class TestIntentArgs:
    """Test intent argument models."""
    
    def test_flight_status_args(self):
        """Test FlightStatusArgs validation."""
        # Valid args
        args = FlightStatusArgs(flight_no="NZ278", date="2024-01-15")
        assert args.flight_no == "NZ278"
        assert args.date == "2024-01-15"
        
        # Test flight number normalization
        args = FlightStatusArgs(flight_no="NZ 278", date=None)
        assert args.flight_no == "NZ278"
    
    def test_next_flight_args(self):
        """Test NextFlightArgs validation."""
        args = NextFlightArgs(
            destination="WLG",
            origin="AKL",
            after_time="now"
        )
        assert args.destination == "WLG"
        assert args.origin == "AKL"
        assert args.after_time == "now"
    
    def test_flights_from_args(self):
        """Test FlightsFromArgs validation."""
        args = FlightsFromArgs(origin="AKL", date="2024-01-15")
        assert args.origin == "AKL"
        assert args.date == "2024-01-15"
    
    def test_flights_to_args(self):
        """Test FlightsToArgs validation."""
        args = FlightsToArgs(destination="WLG", date="2024-01-15")
        assert args.destination == "WLG"
        assert args.date == "2024-01-15"
    
    def test_booking_lookup_args(self):
        """Test BookingLookupArgs validation."""
        args = BookingLookupArgs(pnr="ABC123")
        assert args.pnr == "ABC123"
    
    def test_crew_for_flight_args(self):
        """Test CrewForFlightArgs validation."""
        args = CrewForFlightArgs(flight_no="NZ278", date="2024-01-15")
        assert args.flight_no == "NZ278"
        assert args.date == "2024-01-15"
    
    def test_aircraft_status_args(self):
        """Test AircraftStatusArgs validation."""
        args = AircraftStatusArgs(tail_number="ZK-NZQ")
        assert args.tail_number == "ZK-NZQ"
    
    def test_passenger_count_args(self):
        """Test PassengerCountArgs validation."""
        args = PassengerCountArgs(flight_no="NZ278", date="2024-01-15")
        assert args.flight_no == "NZ278"
        assert args.date == "2024-01-15"
    
    def test_crew_availability_args(self):
        """Test CrewAvailabilityArgs validation."""
        args = CrewAvailabilityArgs(date="2024-01-15", role="pilot")
        assert args.date == "2024-01-15"
        assert args.role == "pilot"
    
    def test_aircraft_by_location_args(self):
        """Test AircraftByLocationArgs validation."""
        args = AircraftByLocationArgs(location="AKL")
        assert args.location == "AKL"


class TestHealthResponse:
    """Test HealthResponse model."""
    
    def test_valid_response(self):
        """Test valid health response."""
        now = datetime.now()
        response = HealthResponse(status="healthy", timestamp=now)
        assert response.status == "healthy"
        assert response.timestamp == now
