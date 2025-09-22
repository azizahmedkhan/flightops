"""
Utility functions for db-router-svc.

This module provides IATA code mapping, time normalization,
and other utility functions for the database router service.
"""

import re
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import pytz
from loguru import logger


# IATA code mapping for New Zealand airports
IATA_MAP = {
    "AKL": "Auckland",
    "WLG": "Wellington", 
    "CHC": "Christchurch",
    "DUD": "Dunedin",
    "ZQN": "Queenstown",
    "NPE": "Napier",
    "ROT": "Rotorua",
    "NPL": "New Plymouth",
    "PMR": "Palmerston North",
    "GIS": "Gisborne",
    "IVC": "Invercargill",
    "NSN": "Nelson",
    "BHE": "Blenheim",
    "WAG": "Wanganui",
    "TRG": "Tauranga",
    "KKE": "Kerikeri",
    "WHK": "Whakatane",
    "TUO": "Taupo",
    "MRO": "Masterton",
    "WRE": "Whangarei"
}

# Reverse mapping for city names to IATA codes
CITY_TO_IATA = {v.lower(): k for k, v in IATA_MAP.items()}

# Common city name variations
CITY_VARIATIONS = {
    "auckland": ["akl", "auckland city", "auckland airport"],
    "wellington": ["wlg", "wellington city", "wellington airport", "wgtn"],
    "christchurch": ["chc", "christchurch city", "christchurch airport", "chch"],
    "dunedin": ["dud", "dunedin city", "dunedin airport"],
    "queenstown": ["zqn", "queenstown airport", "queenstown city"],
    "napier": ["npe", "napier city", "napier airport", "hawke's bay"],
    "rotorua": ["rot", "rotorua city", "rotorua airport"],
    "new plymouth": ["npl", "new plymouth city", "new plymouth airport"],
    "palmerston north": ["pmr", "palmerston north city", "palmerston north airport", "palmy"],
    "gisborne": ["gis", "gisborne city", "gisborne airport"],
    "invercargill": ["ivc", "invercargill city", "invercargill airport"],
    "nelson": ["nsn", "nelson city", "nelson airport"],
    "blenheim": ["bhe", "blenheim city", "blenheim airport"],
    "wanganui": ["wag", "wanganui city", "wanganui airport", "whanganui"],
    "tauranga": ["trg", "tauranga city", "tauranga airport"],
    "kerikeri": ["kke", "kerikeri city", "kerikeri airport"],
    "whakatane": ["whk", "whakatane city", "whakatane airport"],
    "taupo": ["tuo", "taupo city", "taupo airport"],
    "masterton": ["mro", "masterton city", "masterton airport"],
    "whangarei": ["wre", "whangarei city", "whangarei airport"]
}

# New Zealand timezone
NZ_TZ = pytz.timezone('Pacific/Auckland')


def normalize_city_to_iata(city_name: str) -> Optional[str]:
    """
    Convert city name to IATA code.
    
    Args:
        city_name: City name or variation
        
    Returns:
        IATA code if found, None otherwise
    """
    if not city_name:
        return None
        
    city_lower = city_name.lower().strip()
    
    # Direct IATA code check
    if city_lower in IATA_MAP:
        return city_lower.upper()
    
    # Check city variations
    for iata, variations in CITY_VARIATIONS.items():
        if city_lower in variations or city_lower == iata:
            return CITY_TO_IATA[iata]
    
    # Check if it's already a valid IATA code
    if city_lower.upper() in IATA_MAP:
        return city_lower.upper()
    
    logger.warning(f"Could not map city name '{city_name}' to IATA code")
    return None


def normalize_flight_number(text: str) -> Optional[str]:
    """
    Extract and normalize flight number from text.
    
    Args:
        text: Text containing flight number
        
    Returns:
        Normalized flight number (e.g., "NZ278") or None
    """
    if not text:
        return None
    
    # Pattern to match NZ flight numbers
    pattern = r'\bNZ\s?\d{2,4}\b'
    match = re.search(pattern, text.upper())
    
    if match:
        flight_no = match.group(0).replace(' ', '')
        logger.debug(f"Extracted flight number: {flight_no}")
        return flight_no
    
    return None


def normalize_time_phrase(time_phrase: str) -> datetime:
    """
    Convert time phrases to UTC datetime.
    
    Args:
        time_phrase: Time phrase like "now", "today", "tomorrow", "next week"
        
    Returns:
        UTC datetime object
    """
    now_nz = datetime.now(NZ_TZ)
    time_lower = time_phrase.lower().strip()
    
    if time_lower in ["now", "current", "immediately"]:
        return now_nz.astimezone(pytz.UTC)
    
    elif time_lower in ["today", "this morning", "this afternoon", "this evening"]:
        # Start of today in NZ timezone, then convert to UTC
        today_start = now_nz.replace(hour=0, minute=0, second=0, microsecond=0)
        return today_start.astimezone(pytz.UTC)
    
    elif time_lower in ["tomorrow", "tomorrow morning", "tomorrow afternoon", "tomorrow evening"]:
        # Start of tomorrow in NZ timezone, then convert to UTC
        tomorrow_start = (now_nz + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        return tomorrow_start.astimezone(pytz.UTC)
    
    elif time_lower in ["next week", "next week's"]:
        # Start of next week (Monday) in NZ timezone, then convert to UTC
        days_ahead = 7 - now_nz.weekday()  # Monday is 0
        if days_ahead == 0:  # If today is Monday, get next Monday
            days_ahead = 7
        next_monday = now_nz + timedelta(days=days_ahead)
        next_monday_start = next_monday.replace(hour=0, minute=0, second=0, microsecond=0)
        return next_monday_start.astimezone(pytz.UTC)
    
    elif time_lower in ["next month", "next month's"]:
        # Start of next month in NZ timezone, then convert to UTC
        if now_nz.month == 12:
            next_month = now_nz.replace(year=now_nz.year + 1, month=1, day=1)
        else:
            next_month = now_nz.replace(month=now_nz.month + 1, day=1)
        next_month_start = next_month.replace(hour=0, minute=0, second=0, microsecond=0)
        return next_month_start.astimezone(pytz.UTC)
    
    else:
        # Try to parse as datetime string
        try:
            # Try common formats
            for fmt in ["%Y-%m-%d", "%Y-%m-%d %H:%M", "%d/%m/%Y", "%d-%m-%Y"]:
                try:
                    parsed = datetime.strptime(time_phrase, fmt)
                    # Assume NZ timezone if no timezone info
                    if parsed.tzinfo is None:
                        parsed = NZ_TZ.localize(parsed)
                    return parsed.astimezone(pytz.UTC)
                except ValueError:
                    continue
        except Exception as e:
            logger.warning(f"Could not parse time phrase '{time_phrase}': {e}")
        
        # Default to now if we can't parse
        logger.warning(f"Unknown time phrase '{time_phrase}', defaulting to now")
        return now_nz.astimezone(pytz.UTC)


def format_datetime_for_display(dt: datetime) -> str:
    """
    Format datetime for user display in NZ timezone.
    
    Args:
        dt: UTC datetime object
        
    Returns:
        Formatted string in NZ timezone
    """
    if dt.tzinfo is None:
        # Assume UTC if no timezone info
        dt = pytz.UTC.localize(dt)
    
    nz_dt = dt.astimezone(NZ_TZ)
    return nz_dt.strftime("%Y-%m-%d %H:%M %Z")


def validate_iata_code(code: str) -> bool:
    """
    Validate if a string is a valid IATA code.
    
    Args:
        code: String to validate
        
    Returns:
        True if valid IATA code, False otherwise
    """
    if not code or len(code) != 3:
        return False
    
    return code.upper() in IATA_MAP


def get_city_name(iata_code: str) -> Optional[str]:
    """
    Get city name from IATA code.
    
    Args:
        iata_code: IATA code
        
    Returns:
        City name if found, None otherwise
    """
    return IATA_MAP.get(iata_code.upper())


def mask_pii_data(data: Dict[str, Any], role: str) -> Dict[str, Any]:
    """
    Mask PII data based on user role.
    
    Args:
        data: Dictionary containing potentially sensitive data
        role: User role ("public", "agent", "admin")
        
    Returns:
        Dictionary with PII masked if role is not "agent" or "admin"
    """
    if role in ["agent", "admin"]:
        return data
    
    # Mask passenger names
    if "passenger_name" in data:
        name = data["passenger_name"]
        if name and len(name) > 2:
            # Show first letter and last letter, mask middle
            masked = f"{name[0]}***{name[-1]}"
            data["passenger_name"] = masked
    
    return data


def extract_date_from_text(text: str) -> Optional[str]:
    """
    Extract date from text in various formats.
    
    Args:
        text: Text containing date information
        
    Returns:
        Date string in YYYY-MM-DD format or None
    """
    if not text:
        return None
    
    text_lower = text.lower().strip()
    
    # Handle relative dates
    if text_lower in ["today"]:
        return datetime.now(NZ_TZ).strftime("%Y-%m-%d")
    elif text_lower in ["tomorrow"]:
        return (datetime.now(NZ_TZ) + timedelta(days=1)).strftime("%Y-%m-%d")
    elif text_lower in ["yesterday"]:
        return (datetime.now(NZ_TZ) - timedelta(days=1)).strftime("%Y-%m-%d")
    
    # Try to parse various date formats
    date_patterns = [
        r'\b(\d{4})-(\d{1,2})-(\d{1,2})\b',  # YYYY-MM-DD
        r'\b(\d{1,2})/(\d{1,2})/(\d{4})\b',  # DD/MM/YYYY
        r'\b(\d{1,2})-(\d{1,2})-(\d{4})\b',  # DD-MM-YYYY
        r'\b(\d{1,2})\s+(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\s+(\d{4})\b',  # DD MMM YYYY
    ]
    
    month_names = {
        'jan': '01', 'feb': '02', 'mar': '03', 'apr': '04',
        'may': '05', 'jun': '06', 'jul': '07', 'aug': '08',
        'sep': '09', 'oct': '10', 'nov': '11', 'dec': '12'
    }
    
    for pattern in date_patterns:
        match = re.search(pattern, text_lower)
        if match:
            groups = match.groups()
            if len(groups) == 3:
                if pattern == date_patterns[0]:  # YYYY-MM-DD
                    year, month, day = groups
                elif pattern in [date_patterns[1], date_patterns[2]]:  # DD/MM/YYYY or DD-MM-YYYY
                    day, month, year = groups
                elif pattern == date_patterns[3]:  # DD MMM YYYY
                    day, month, year = groups
                    month = month_names.get(month, month)
                
                try:
                    # Validate the date
                    datetime.strptime(f"{year}-{month.zfill(2)}-{day.zfill(2)}", "%Y-%m-%d")
                    return f"{year}-{month.zfill(2)}-{day.zfill(2)}"
                except ValueError:
                    continue
    
    return None
