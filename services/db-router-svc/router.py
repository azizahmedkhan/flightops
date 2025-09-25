"""
LLM routing module for db-router-svc.

This module handles natural language to intent routing using LLM function calling.
"""

import re
import time
from typing import Dict, Any, Optional, Tuple
from loguru import logger
import json

from models import Intent, RouteResponse
from util import normalize_city_to_iata, normalize_flight_number, normalize_time_phrase, extract_date_from_text
from services.shared.llm_client import LLMClient


class QueryRouter:
    """Handles natural language query routing to database intents."""
    
    def __init__(self, llm_client: LLMClient):
        """
        Initialize query router.
        
        Args:
            llm_client: LLM client for function calling
        """
        self.llm_client = llm_client
        self.function_schema = self._create_function_schema()
    
    def _create_function_schema(self) -> Dict[str, Any]:
        """Create the function calling schema for LLM."""
        return {
            "name": "route_query",
            "description": "Route a natural language query to the appropriate database intent",
            "parameters": {
                "type": "object",
                "properties": {
                    "intent": {
                        "type": "string",
                        "enum": [
                            "flight_status", "next_flight", "flights_from", "flights_to",
                            "booking_lookup", "crew_for_flight", "aircraft_status",
                            "passenger_count", "crew_availability", "aircraft_by_location",
                            "knowledge_base"
                        ],
                        "description": "The database intent that best matches the query"
                    },
                    "args": {
                        "type": "object",
                        "properties": {
                            "flight_no": {
                                "type": "string",
                                "description": "Flight number (e.g., NZ278)"
                            },
                            "date": {
                                "type": "string",
                                "description": "Date in YYYY-MM-DD format"
                            },
                            "origin": {
                                "type": "string",
                                "description": "Origin IATA code (e.g., AKL)"
                            },
                            "destination": {
                                "type": "string",
                                "description": "Destination IATA code (e.g., WLG)"
                            },
                            "after_time": {
                                "type": "string",
                                "description": "Time after which to search (e.g., 'now', 'tomorrow')"
                            },
                            "pnr": {
                                "type": "string",
                                "description": "Passenger Name Record"
                            },
                            "tail_number": {
                                "type": "string",
                                "description": "Aircraft tail number"
                            },
                            "role": {
                                "type": "string",
                                "description": "Crew role filter"
                            },
                            "location": {
                                "type": "string",
                                "description": "Location IATA code"
                            },
                            "query": {
                                "type": "string",
                                "description": "Knowledge base query text"
                            },
                            "k": {
                                "type": "integer",
                                "minimum": 1,
                                "maximum": 20,
                                "description": "Number of knowledge base results to retrieve"
                            }
                        }
                    },
                    "confidence": {
                        "type": "number",
                        "minimum": 0,
                        "maximum": 1,
                        "description": "Confidence score for the routing decision"
                    }
                },
                "required": ["intent", "args", "confidence"]
            }
        }
    
    def _extract_flight_number(self, text: str) -> Optional[str]:
        """Extract flight number from text using regex."""
        return normalize_flight_number(text)

    def _has_crew_context(self, text: str) -> bool:
        """Detect if the text is specifically asking about crew details."""
        crew_keywords = [
            "crew",
            "pilot",
            "captain",
            "first officer",
            "flight attendant",
            "attendant",
            "cabin crew",
            "staffing",
        ]
        lowered = text.lower()
        return any(keyword in lowered for keyword in crew_keywords)

    def _has_knowledge_base_context(self, text: str) -> bool:
        """Detect if the query should be answered via the knowledge base."""
        lowered = text.lower()

        kb_keywords = [
            "policy", "policies", "refund", "refunds", "allowance", "allowances",
            "baggage", "luggage", "credit", "credits", "compensation", "fare",
            "fares", "sop", "procedure", "procedures", "template", "templates",
            "communication", "communications", "comm", "dangerous goods",
            "special assistance", "wheelchair", "koru", "airpoints", "loyalty",
            "voucher", "vouchers", "pet", "pets", "animal", "animals", "contact",
            "contacts", "channel", "channels", "advisory", "advisories", "check-in",
            "checkin", "cutoff", "cut-off", "disruption", "delay policy"
        ]

        db_keywords = [
            "flight", "status", "departure", "arrival", "boarding", "gate",
            "terminal", "crew", "pnr", "booking", "reservation", "passenger",
            "tail", "aircraft", "roster", "schedule"
        ]

        kb_score = sum(1 for keyword in kb_keywords if keyword in lowered)
        db_score = sum(1 for keyword in db_keywords if keyword in lowered)

        return kb_score > 0 and kb_score >= db_score
    
    def _normalize_city_names(self, text: str) -> str:
        """Normalize city names to IATA codes in text."""
        # Common city name patterns
        city_patterns = [
            (r'\b(auckland|akl)\b', 'AKL'),
            (r'\b(wellington|wlg|wgtn)\b', 'WLG'),
            (r'\b(christchurch|chc|chch)\b', 'CHC'),
            (r'\b(dunedin|dud)\b', 'DUD'),
            (r'\b(queenstown|zqn)\b', 'ZQN'),
            (r'\b(napier|npe|hawke\'s bay)\b', 'NPE'),
            (r'\b(rotorua|rot)\b', 'ROT'),
            (r'\b(new plymouth|npl)\b', 'NPL'),
            (r'\b(palmerston north|pmr|palmy)\b', 'PMR'),
            (r'\b(gisborne|gis)\b', 'GIS'),
            (r'\b(invercargill|ivc)\b', 'IVC'),
            (r'\b(nelson|nsn)\b', 'NSN'),
            (r'\b(blenheim|bhe)\b', 'BHE'),
            (r'\b(wanganui|wag|whanganui)\b', 'WAG'),
            (r'\b(tauranga|trg)\b', 'TRG'),
            (r'\b(kerikeri|kke)\b', 'KKE'),
            (r'\b(whakatane|whk)\b', 'WHK'),
            (r'\b(taupo|tuo)\b', 'TUO'),
            (r'\b(masterton|mro)\b', 'MRO'),
            (r'\b(whangarei|wre)\b', 'WRE')
        ]
        
        normalized_text = text
        for pattern, iata_code in city_patterns:
            normalized_text = re.sub(pattern, iata_code, normalized_text, flags=re.IGNORECASE)
        
        return normalized_text
    
    def _extract_date_from_text(self, text: str) -> Optional[str]:
        """Extract date from text."""
        return extract_date_from_text(text)
    
    async def route_query(self, text: str) -> RouteResponse:
        """
        Route a natural language query to the appropriate database intent.
        
        Args:
            text: Natural language query text
            
        Returns:
            RouteResponse with intent, args, and confidence
        """
        if not text or not text.strip():
            raise ValueError("Query text cannot be empty")
        
        # Pre-process the text
        processed_text = text.strip()
        logger.info("route_query begin query='{}'", processed_text[:200])
        start_time = time.time()

        # Route knowledge base queries directly to embeddings search
        if self._has_knowledge_base_context(processed_text):
            logger.debug("Detected knowledge base query pattern")
            response = RouteResponse(
                intent=Intent.KNOWLEDGE_BASE,
                args={"query": processed_text, "k": 5},
                confidence=0.85
            )
            duration_ms = (time.time() - start_time) * 1000
            logger.info(
                "route_query exit intent={} confidence={} reason=knowledge_base_pattern duration_ms={:.2f}",
                response.intent,
                response.confidence,
                duration_ms
            )
            return response

        # Check for flight number pattern first (fast path)
        flight_no = self._extract_flight_number(processed_text)
        if flight_no and not self._has_crew_context(processed_text):
            logger.debug(f"Detected flight number pattern: {flight_no}")
            response = RouteResponse(
                intent=Intent.FLIGHT_STATUS,
                args={"flight_no": flight_no, "date": None},
                confidence=0.95
            )
            duration_ms = (time.time() - start_time) * 1000
            logger.info(
                "route_query exit intent={} confidence={} reason=flight_number_pattern duration_ms={:.2f}",
                response.intent,
                response.confidence,
                duration_ms
            )
            return response
        elif flight_no:
            logger.debug(
                "Detected flight number pattern but crew context present; deferring to LLM routing"
            )

        
        # Normalize city names to IATA codes
        processed_text = self._normalize_city_names(processed_text)
        
        # Extract date if present
        extracted_date = self._extract_date_from_text(processed_text)
        
        # Create system prompt for LLM
        system_prompt = """You are a database query router for an airline system. 
        Your job is to analyze natural language queries and route them to the appropriate database intent.
        
        Available intents:
        - flight_status: Get status of a specific flight (requires flight_no)
        - next_flight: Find next flights to a destination (requires destination, optional origin, after_time)
        - flights_from: List flights from an origin (requires origin, optional date)
        - flights_to: List flights to a destination (requires destination, optional date)
        - booking_lookup: Look up booking by PNR (requires pnr)
        - crew_for_flight: Get crew assigned to a flight (requires flight_no, date)
        - aircraft_status: Get aircraft status (requires tail_number)
        - passenger_count: Get passenger count for a flight (requires flight_no, date)
        - crew_availability: Find available crew (requires date, optional role)
        - aircraft_by_location: Find aircraft at a location (requires location)
        - knowledge_base: Answer general policy, procedure, or customer questions (requires query text)
        
        IATA codes for New Zealand airports:
        AKL=Auckland, WLG=Wellington, CHC=Christchurch, DUD=Dunedin, ZQN=Queenstown, NPE=Napier,
        ROT=Rotorua, NPL=New Plymouth, PMR=Palmerston North, GIS=Gisborne, IVC=Invercargill,
        NSN=Nelson, BHE=Blenheim, WAG=Wanganui, TRG=Tauranga, KKE=Kerikeri, WHK=Whakatane,
        TUO=Taupo, MRO=Masterton, WRE=Whangarei
        
        Rules:
        1. Use IATA codes for all airport references
        2. Extract dates in YYYY-MM-DD format
        3. For time references, use "now" for current time
        4. Be conservative with confidence scores
        5. If unsure, choose the most likely intent with lower confidence
        """
        
        try:
            # Use LLM function calling to route the query
            response = await self.llm_client.call_function(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": processed_text}
                ],
                function_schema=self.function_schema
            )
            
            if not response or "function_call" not in response:
                logger.warning("LLM did not return a function call")
                return self._fallback_route(processed_text)
            
            function_call = response["function_call"]
            if function_call.name != "route_query":
                logger.warning(f"Unexpected function call: {function_call.name}")
                return self._fallback_route(processed_text)
            
            # Parse function arguments
            try:
                args = json.loads(function_call.arguments)
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse function arguments: {e}")
                return self._fallback_route(processed_text)
            
            intent_str = args.get("intent")
            intent_args = args.get("args", {})
            confidence = args.get("confidence", 0.5)
            
            # Validate intent
            try:
                intent = Intent(intent_str)
            except ValueError:
                logger.warning(f"Invalid intent: {intent_str}")
                return self._fallback_route(processed_text)
            
            # Add extracted date if present and not already in args
            if extracted_date and "date" not in intent_args:
                intent_args["date"] = extracted_date
            
            # Normalize IATA codes in args
            for key in ["origin", "destination", "location"]:
                if key in intent_args and intent_args[key]:
                    normalized = normalize_city_to_iata(intent_args[key])
                    if normalized:
                        intent_args[key] = normalized
            
            # Normalize time references
            if "after_time" in intent_args and intent_args["after_time"]:
                if intent_args["after_time"].lower() in ["now", "current", "immediately"]:
                    intent_args["after_time"] = "now"
                elif intent_args["after_time"].lower() in ["today", "tomorrow", "next week"]:
                    # Convert to timestamp
                    try:
                        dt = normalize_time_phrase(intent_args["after_time"])
                        intent_args["after_time"] = dt.isoformat()
                    except Exception as e:
                        logger.warning(f"Failed to normalize time: {e}")
                        intent_args["after_time"] = "now"
            
            response = RouteResponse(
                intent=intent,
                args=intent_args,
                confidence=float(confidence)
            )
            duration_ms = (time.time() - start_time) * 1000
            logger.info(
                "route_query exit intent={} confidence={} duration_ms={:.2f}",
                response.intent,
                response.confidence,
                duration_ms
            )
            return response
            
        except Exception as e:
            logger.error(f"LLM routing failed: {e}")
            return self._fallback_route(processed_text)

    def _fallback_route(self, text: str) -> RouteResponse:
        """
        Fallback routing when LLM fails.
        
        Args:
            text: Query text
            
        Returns:
            RouteResponse with best guess
        """
        logger.warning("Using fallback routing")
        
        # Simple keyword-based fallback
        text_lower = text.lower()
        
        if any(word in text_lower for word in ["status", "flight", "nz"]):
            response = RouteResponse(
                intent=Intent.FLIGHT_STATUS,
                args={"flight_no": "UNKNOWN", "date": None},
                confidence=0.3
            )
            logger.info(
                "route_query exit intent={} confidence={} reason=fallback_flight_status",
                response.intent,
                response.confidence
            )
            return response
        elif any(word in text_lower for word in ["next", "flight", "to"]):
            response = RouteResponse(
                intent=Intent.NEXT_FLIGHT,
                args={"destination": "WLG", "origin": None, "after_time": "now"},
                confidence=0.3
            )
            logger.info(
                "route_query exit intent={} confidence={} reason=fallback_next_flight",
                response.intent,
                response.confidence
            )
            return response
        elif any(word in text_lower for word in ["booking", "pnr", "reservation"]):
            response = RouteResponse(
                intent=Intent.BOOKING_LOOKUP,
                args={"pnr": "UNKNOWN"},
                confidence=0.3
            )
            logger.info(
                "route_query exit intent={} confidence={} reason=fallback_booking_lookup",
                response.intent,
                response.confidence
            )
            return response
        else:
            response = RouteResponse(
                intent=Intent.FLIGHT_STATUS,
                args={"flight_no": "UNKNOWN", "date": None},
                confidence=0.1
            )
            logger.info(
                "route_query exit intent={} confidence={} reason=fallback_default",
                response.intent,
                response.confidence
            )
            return response
