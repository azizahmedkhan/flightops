"""
Pydantic models for db-router-svc.

This module defines the request/response models and intent enums
for the database router service.
"""

from enum import Enum
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field, validator
from datetime import datetime
import re


class Intent(str, Enum):
    """Available database query intents."""
    FLIGHT_STATUS = "flight_status"
    NEXT_FLIGHT = "next_flight"
    FLIGHTS_FROM = "flights_from"
    FLIGHTS_TO = "flights_to"
    BOOKING_LOOKUP = "booking_lookup"
    CREW_FOR_FLIGHT = "crew_for_flight"
    AIRCRAFT_STATUS = "aircraft_status"
    PASSENGER_COUNT = "passenger_count"
    CREW_AVAILABILITY = "crew_availability"
    AIRCRAFT_BY_LOCATION = "aircraft_by_location"


class RouteRequest(BaseModel):
    """Request model for /route endpoint."""
    text: str = Field(..., min_length=1, max_length=500, description="Natural language query text")


class RouteResponse(BaseModel):
    """Response model for /route endpoint."""
    intent: Intent = Field(..., description="Detected intent for the query")
    args: Dict[str, Any] = Field(..., description="Extracted arguments for the intent")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score for the routing")


class SmartQueryRequest(BaseModel):
    """Request model for /smart-query endpoint."""
    text: str = Field(..., min_length=1, max_length=500, description="Natural language query text")
    auth: Dict[str, str] = Field(
        default_factory=lambda: {"role": "public"}, 
        description="Authentication context with role information"
    )

    @validator('auth')
    def validate_auth_role(cls, v):
        """Validate that role is one of the allowed values."""
        allowed_roles = {"public", "agent", "admin"}
        if v.get("role") not in allowed_roles:
            raise ValueError(f"Role must be one of {allowed_roles}")
        return v


class SmartQueryResponse(BaseModel):
    """Response model for /smart-query endpoint."""
    answer: str = Field(..., description="Formatted answer based on query results")
    rows: List[Dict[str, Any]] = Field(..., description="Raw database results")
    intent: Intent = Field(..., description="Detected intent for the query")
    args: Dict[str, Any] = Field(..., description="Extracted arguments for the intent")
    metadata: Dict[str, Any] = Field(..., description="Additional metadata about the query")


class HealthResponse(BaseModel):
    """Response model for health check endpoint."""
    status: str = Field(..., description="Service health status")
    timestamp: datetime = Field(..., description="Current timestamp")


class IntentArgs(BaseModel):
    """Base model for intent arguments with common validators."""
    pass


class FlightStatusArgs(IntentArgs):
    """Arguments for flight_status intent."""
    flight_no: str = Field(..., description="Flight number (e.g., NZ278)")
    date: Optional[str] = Field(None, description="Flight date (YYYY-MM-DD format)")
    
    @validator('flight_no', pre=True, always=True)
    def normalize_flight_no(cls, v):
        """Normalize flight number format."""
        if v is None:
            return v
        # Remove spaces and ensure NZ prefix
        v = str(v).strip().upper()
        if re.match(r'^NZ\s?\d{2,4}$', v):
            return v.replace(' ', '')
        return v
    
    @validator('date', pre=True, always=True)
    def normalize_date(cls, v):
        """Normalize date format."""
        if v is None or v == "":
            return None
        return str(v).strip()


class NextFlightArgs(IntentArgs):
    """Arguments for next_flight intent."""
    destination: str = Field(..., description="Destination IATA code")
    origin: Optional[str] = Field(None, description="Origin IATA code")
    after_time: str = Field("now", description="Time after which to search")
    
    @validator('origin', 'destination', pre=True, always=True)
    def normalize_iata_code(cls, v):
        """Normalize IATA codes to uppercase."""
        if v is None:
            return v
        return str(v).strip().upper()
    
    @validator('after_time', pre=True, always=True)
    def normalize_after_time(cls, v):
        """Normalize after_time parameter."""
        if v is None or v == "":
            return "now"
        return str(v).strip().lower()


class FlightsFromArgs(IntentArgs):
    """Arguments for flights_from intent."""
    origin: str = Field(..., description="Origin IATA code")
    date: Optional[str] = Field(None, description="Flight date (YYYY-MM-DD format)")
    
    @validator('origin', pre=True, always=True)
    def normalize_iata_code(cls, v):
        """Normalize IATA codes to uppercase."""
        if v is None:
            return v
        return str(v).strip().upper()
    
    @validator('date', pre=True, always=True)
    def normalize_date(cls, v):
        """Normalize date format."""
        if v is None or v == "":
            return None
        return str(v).strip()


class FlightsToArgs(IntentArgs):
    """Arguments for flights_to intent."""
    destination: str = Field(..., description="Destination IATA code")
    date: Optional[str] = Field(None, description="Flight date (YYYY-MM-DD format)")
    
    @validator('destination', pre=True, always=True)
    def normalize_iata_code(cls, v):
        """Normalize IATA codes to uppercase."""
        if v is None:
            return v
        return str(v).strip().upper()
    
    @validator('date', pre=True, always=True)
    def normalize_date(cls, v):
        """Normalize date format."""
        if v is None or v == "":
            return None
        return str(v).strip()


class BookingLookupArgs(IntentArgs):
    """Arguments for booking_lookup intent."""
    pnr: str = Field(..., description="Passenger Name Record")


class CrewForFlightArgs(IntentArgs):
    """Arguments for crew_for_flight intent."""
    flight_no: str = Field(..., description="Flight number")
    date: str = Field(..., description="Flight date (YYYY-MM-DD format)")
    
    @validator('flight_no', pre=True, always=True)
    def normalize_flight_no(cls, v):
        """Normalize flight number format."""
        if v is None:
            return v
        # Remove spaces and ensure NZ prefix
        v = str(v).strip().upper()
        if re.match(r'^NZ\s?\d{2,4}$', v):
            return v.replace(' ', '')
        return v
    
    @validator('date', pre=True, always=True)
    def normalize_date(cls, v):
        """Normalize date format."""
        if v is None or v == "":
            return None
        return str(v).strip()


class AircraftStatusArgs(IntentArgs):
    """Arguments for aircraft_status intent."""
    tail_number: str = Field(..., description="Aircraft tail number")


class PassengerCountArgs(IntentArgs):
    """Arguments for passenger_count intent."""
    flight_no: str = Field(..., description="Flight number")
    date: str = Field(..., description="Flight date (YYYY-MM-DD format)")
    
    @validator('flight_no', pre=True, always=True)
    def normalize_flight_no(cls, v):
        """Normalize flight number format."""
        if v is None:
            return v
        # Remove spaces and ensure NZ prefix
        v = str(v).strip().upper()
        if re.match(r'^NZ\s?\d{2,4}$', v):
            return v.replace(' ', '')
        return v
    
    @validator('date', pre=True, always=True)
    def normalize_date(cls, v):
        """Normalize date format."""
        if v is None or v == "":
            return None
        return str(v).strip()


class CrewAvailabilityArgs(IntentArgs):
    """Arguments for crew_availability intent."""
    date: str = Field(..., description="Date for availability check")
    role: Optional[str] = Field(None, description="Crew role filter")
    
    @validator('date', pre=True, always=True)
    def normalize_date(cls, v):
        """Normalize date format."""
        if v is None or v == "":
            return None
        return str(v).strip()


class AircraftByLocationArgs(IntentArgs):
    """Arguments for aircraft_by_location intent."""
    location: str = Field(..., description="Location IATA code")
    
    @validator('location', pre=True, always=True)
    def normalize_iata_code(cls, v):
        """Normalize IATA codes to uppercase."""
        if v is None:
            return v
        return str(v).strip().upper()


# Intent to args mapping for validation
INTENT_ARGS_MAP = {
    Intent.FLIGHT_STATUS: FlightStatusArgs,
    Intent.NEXT_FLIGHT: NextFlightArgs,
    Intent.FLIGHTS_FROM: FlightsFromArgs,
    Intent.FLIGHTS_TO: FlightsToArgs,
    Intent.BOOKING_LOOKUP: BookingLookupArgs,
    Intent.CREW_FOR_FLIGHT: CrewForFlightArgs,
    Intent.AIRCRAFT_STATUS: AircraftStatusArgs,
    Intent.PASSENGER_COUNT: PassengerCountArgs,
    Intent.CREW_AVAILABILITY: CrewAvailabilityArgs,
    Intent.AIRCRAFT_BY_LOCATION: AircraftByLocationArgs,
}
