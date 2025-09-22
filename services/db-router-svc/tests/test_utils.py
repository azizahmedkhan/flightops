"""
Tests for db-router-svc utility functions.
"""

import pytest
from datetime import datetime, timedelta
import pytz

from ..util import (
    normalize_city_to_iata, normalize_flight_number, normalize_time_phrase,
    format_datetime_for_display, validate_iata_code, get_city_name,
    mask_pii_data, extract_date_from_text
)


class TestCityToIATAMapping:
    """Test city name to IATA code mapping."""
    
    def test_direct_iata_codes(self):
        """Test direct IATA code mapping."""
        assert normalize_city_to_iata("AKL") == "AKL"
        assert normalize_city_to_iata("WLG") == "WLG"
        assert normalize_city_to_iata("CHC") == "CHC"
    
    def test_city_name_mapping(self):
        """Test city name to IATA mapping."""
        assert normalize_city_to_iata("Auckland") == "AKL"
        assert normalize_city_to_iata("Wellington") == "WLG"
        assert normalize_city_to_iata("Christchurch") == "CHC"
        assert normalize_city_to_iata("Dunedin") == "DUD"
        assert normalize_city_to_iata("Queenstown") == "ZQN"
        assert normalize_city_to_iata("Napier") == "NPE"
    
    def test_city_variations(self):
        """Test city name variations."""
        assert normalize_city_to_iata("akl") == "AKL"
        assert normalize_city_to_iata("wellington city") == "WLG"
        assert normalize_city_to_iata("christchurch airport") == "CHC"
        assert normalize_city_to_iata("hawke's bay") == "NPE"
        assert normalize_city_to_iata("palmy") == "PMR"
    
    def test_unknown_city(self):
        """Test unknown city names."""
        assert normalize_city_to_iata("Unknown City") is None
        assert normalize_city_to_iata("") is None
        assert normalize_city_to_iata(None) is None


class TestFlightNumberNormalization:
    """Test flight number extraction and normalization."""
    
    def test_valid_flight_numbers(self):
        """Test valid flight number extraction."""
        assert normalize_flight_number("NZ278") == "NZ278"
        assert normalize_flight_number("NZ 278") == "NZ278"
        assert normalize_flight_number("What's the status of NZ278?") == "NZ278"
        assert normalize_flight_number("Flight NZ 1234 is delayed") == "NZ1234"
    
    def test_invalid_flight_numbers(self):
        """Test invalid flight number patterns."""
        assert normalize_flight_number("") is None
        assert normalize_flight_number("AA123") is None  # Not NZ
        assert normalize_flight_number("NZ1") is None  # Too short
        assert normalize_flight_number("NZ12345") is None  # Too long
        assert normalize_flight_number("No flight number here") is None


class TestTimeNormalization:
    """Test time phrase normalization."""
    
    def test_relative_time_phrases(self):
        """Test relative time phrase conversion."""
        # Test "now"
        now_dt = normalize_time_phrase("now")
        assert isinstance(now_dt, datetime)
        
        # Test "today"
        today_dt = normalize_time_phrase("today")
        assert isinstance(today_dt, datetime)
        
        # Test "tomorrow"
        tomorrow_dt = normalize_time_phrase("tomorrow")
        assert isinstance(tomorrow_dt, datetime)
        assert tomorrow_dt > today_dt
        
        # Test "next week"
        next_week_dt = normalize_time_phrase("next week")
        assert isinstance(next_week_dt, datetime)
    
    def test_timezone_handling(self):
        """Test timezone conversion to UTC."""
        dt = normalize_time_phrase("now")
        assert dt.tzinfo is not None
        assert dt.tzinfo.utcoffset(dt).total_seconds() == 0  # Should be UTC


class TestDateTimeFormatting:
    """Test datetime formatting for display."""
    
    def test_format_datetime_for_display(self):
        """Test datetime formatting in NZ timezone."""
        # Create a UTC datetime
        utc_dt = datetime(2024, 1, 15, 10, 30, 0, tzinfo=pytz.UTC)
        
        formatted = format_datetime_for_display(utc_dt)
        assert "2024-01-15" in formatted
        assert "NZDT" in formatted or "NZST" in formatted  # NZ timezone
    
    def test_format_datetime_no_timezone(self):
        """Test formatting datetime without timezone info."""
        dt = datetime(2024, 1, 15, 10, 30, 0)
        formatted = format_datetime_for_display(dt)
        assert "2024-01-15" in formatted


class TestIATACodeValidation:
    """Test IATA code validation."""
    
    def test_valid_iata_codes(self):
        """Test valid IATA codes."""
        assert validate_iata_code("AKL") is True
        assert validate_iata_code("WLG") is True
        assert validate_iata_code("CHC") is True
    
    def test_invalid_iata_codes(self):
        """Test invalid IATA codes."""
        assert validate_iata_code("") is False
        assert validate_iata_code("A") is False  # Too short
        assert validate_iata_code("ABCD") is False  # Too long
        assert validate_iata_code("XYZ") is False  # Not in our map
        assert validate_iata_code(None) is False


class TestCityNameRetrieval:
    """Test city name retrieval from IATA codes."""
    
    def test_get_city_name(self):
        """Test getting city name from IATA code."""
        assert get_city_name("AKL") == "Auckland"
        assert get_city_name("WLG") == "Wellington"
        assert get_city_name("CHC") == "Christchurch"
    
    def test_get_city_name_unknown(self):
        """Test getting city name for unknown IATA code."""
        assert get_city_name("XYZ") is None
        assert get_city_name("") is None


class TestPIIDataMasking:
    """Test PII data masking based on user role."""
    
    def test_mask_pii_public_role(self):
        """Test PII masking for public role."""
        data = {
            "passenger_name": "John Smith",
            "flight_no": "NZ278",
            "status": "on_time"
        }
        
        masked_data = mask_pii_data(data, "public")
        assert masked_data["passenger_name"] == "J***h"  # First and last letter
        assert masked_data["flight_no"] == "NZ278"  # Not PII
        assert masked_data["status"] == "on_time"  # Not PII
    
    def test_mask_pii_agent_role(self):
        """Test no masking for agent role."""
        data = {
            "passenger_name": "John Smith",
            "flight_no": "NZ278"
        }
        
        masked_data = mask_pii_data(data, "agent")
        assert masked_data["passenger_name"] == "John Smith"  # No masking
        assert masked_data["flight_no"] == "NZ278"
    
    def test_mask_pii_admin_role(self):
        """Test no masking for admin role."""
        data = {
            "passenger_name": "John Smith",
            "flight_no": "NZ278"
        }
        
        masked_data = mask_pii_data(data, "admin")
        assert masked_data["passenger_name"] == "John Smith"  # No masking
        assert masked_data["flight_no"] == "NZ278"
    
    def test_mask_pii_short_name(self):
        """Test masking for very short names."""
        data = {"passenger_name": "Jo"}
        masked_data = mask_pii_data(data, "public")
        assert masked_data["passenger_name"] == "Jo"  # Too short to mask


class TestDateExtraction:
    """Test date extraction from text."""
    
    def test_relative_dates(self):
        """Test relative date extraction."""
        assert extract_date_from_text("today") == datetime.now(pytz.timezone('Pacific/Auckland')).strftime("%Y-%m-%d")
        assert extract_date_from_text("tomorrow") == (datetime.now(pytz.timezone('Pacific/Auckland')) + timedelta(days=1)).strftime("%Y-%m-%d")
        assert extract_date_from_text("yesterday") == (datetime.now(pytz.timezone('Pacific/Auckland')) - timedelta(days=1)).strftime("%Y-%m-%d")
    
    def test_iso_date_formats(self):
        """Test ISO date format extraction."""
        assert extract_date_from_text("2024-01-15") == "2024-01-15"
        assert extract_date_from_text("Flight on 2024-01-15") == "2024-01-15"
    
    def test_other_date_formats(self):
        """Test other date format extraction."""
        assert extract_date_from_text("15/01/2024") == "2024-01-15"
        assert extract_date_from_text("15-01-2024") == "2024-01-15"
        assert extract_date_from_text("15 Jan 2024") == "2024-01-15"
    
    def test_no_date_in_text(self):
        """Test text with no date."""
        assert extract_date_from_text("No date here") is None
        assert extract_date_from_text("") is None
        assert extract_date_from_text(None) is None
