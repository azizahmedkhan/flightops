"""
Utility functions for the scalable chatbot service
"""

import hashlib
import json
import time
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
import httpx
import asyncio


async def fetch_flight_context(flight_no: str, date: str, agent_url: str) -> Optional[Dict[str, Any]]:
    """Fetch flight context from agent service"""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                f"{agent_url}/get_flight_context",
                json={"flight_no": flight_no, "date": date}
            )
            if response.status_code == 200:
                return response.json()
    except Exception as e:
        print(f"Error fetching flight context: {e}")
    return None


async def fetch_policy_context(query: str, knowledge_service_url: str) -> Optional[List[Dict[str, Any]]]:
    """Fetch policy context from knowledge service"""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                f"{knowledge_service_url}/search",
                json={"q": query, "k": 3}
            )
            if response.status_code == 200:
                data = response.json()
                return data.get("results", [])
    except Exception as e:
        print(f"Error fetching policy context: {e}")
    return None


async def fetch_database_context(query: str, db_router_url: str) -> Optional[Dict[str, Any]]:
    """Fetch database context from db-router-svc"""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                f"{db_router_url}/smart-query",
                json={
                    "text": query,
                    "auth": {"role": "public"}
                }
            )
            if response.status_code == 200:
                data = response.json()
                return data
    except Exception as e:
        print(f"Error fetching database context: {e}")
    return None


def calculate_query_hash(session_id: str, message: str, context: Dict[str, Any]) -> str:
    """Calculate hash for caching queries"""
    # Create a deterministic string from the inputs
    query_string = f"{session_id}:{message}:{json.dumps(context, sort_keys=True)}"
    return hashlib.md5(query_string.encode()).hexdigest()


def sanitize_message(message: str) -> str:
    """Sanitize user message for processing"""
    # Remove potential harmful characters and limit length
    sanitized = message.strip()[:1000]  # Limit to 1000 characters
    
    # Remove common injection patterns
    dangerous_patterns = ["<script", "javascript:", "data:", "vbscript:"]
    for pattern in dangerous_patterns:
        sanitized = sanitized.replace(pattern, "")
    
    return sanitized


def format_response_chunk(chunk_type: str, content: str, session_id: str, 
                         metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Format a response chunk for WebSocket transmission"""
    return {
        "type": chunk_type,
        "content": content,
        "session_id": session_id,
        "timestamp": datetime.now().isoformat(),
        "metadata": metadata or {}
    }


async def batch_process_messages(messages: List[Dict[str, Any]], 
                               process_func, 
                               batch_size: int = 10) -> List[Any]:
    """Process messages in batches for better performance"""
    results = []
    
    for i in range(0, len(messages), batch_size):
        batch = messages[i:i + batch_size]
        batch_tasks = [process_func(msg) for msg in batch]
        batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)
        results.extend(batch_results)
        
        # Small delay between batches to prevent overwhelming the system
        if i + batch_size < len(messages):
            await asyncio.sleep(0.1)
    
    return results


def extract_entities(message: str) -> Dict[str, List[str]]:
    """Extract entities from user message"""
    entities = {
        "flight_numbers": [],
        "dates": [],
        "emails": [],
        "phone_numbers": []
    }
    
    import re
    
    # Flight numbers (basic pattern)
    flight_pattern = r'\b[A-Z]{2,3}\d{3,4}\b'
    entities["flight_numbers"] = re.findall(flight_pattern, message.upper())
    
    # Dates (basic patterns)
    date_patterns = [
        r'\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b',  # MM/DD/YYYY or MM-DD-YYYY
        r'\b\d{4}[/-]\d{1,2}[/-]\d{1,2}\b',    # YYYY/MM/DD or YYYY-MM-DD
        r'\b(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\w*\s+\d{1,2},?\s+\d{4}\b',  # Month DD, YYYY
    ]
    
    for pattern in date_patterns:
        entities["dates"].extend(re.findall(pattern, message.lower()))
    
    # Email addresses
    email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    entities["emails"] = re.findall(email_pattern, message)
    
    # Phone numbers (basic pattern)
    phone_pattern = r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b'
    entities["phone_numbers"] = re.findall(phone_pattern, message)
    
    return entities


def calculate_similarity_score(text1: str, text2: str) -> float:
    """Calculate simple similarity score between two texts"""
    # Simple word-based similarity
    words1 = set(text1.lower().split())
    words2 = set(text2.lower().split())
    
    if not words1 or not words2:
        return 0.0
    
    intersection = words1.intersection(words2)
    union = words1.union(words2)
    
    return len(intersection) / len(union) if union else 0.0


async def cleanup_expired_sessions(redis_manager, max_age_hours: int = 24):
    """Clean up expired sessions from Redis"""
    try:
        # This would need to be implemented based on your Redis key pattern
        # For now, this is a placeholder
        print(f"Cleaning up sessions older than {max_age_hours} hours")
    except Exception as e:
        print(f"Error cleaning up sessions: {e}")


def generate_session_stats(session_context: Dict[str, Any]) -> Dict[str, Any]:
    """Generate statistics for a session"""
    stats = {
        "message_count": session_context.get("message_count", 0),
        "created_at": session_context.get("created_at"),
        "last_activity": session_context.get("last_activity"),
        "has_flight_context": bool(session_context.get("flight_data")),
        "has_policy_context": bool(session_context.get("policy_data")),
        "customer_name": session_context.get("customer_name"),
        "flight_no": session_context.get("flight_no")
    }
    
    # Calculate session duration
    if stats["created_at"] and stats["last_activity"]:
        try:
            created = datetime.fromisoformat(stats["created_at"].replace('Z', '+00:00'))
            last_activity = datetime.fromisoformat(stats["last_activity"].replace('Z', '+00:00'))
            duration = last_activity - created
            stats["session_duration_minutes"] = duration.total_seconds() / 60
        except:
            stats["session_duration_minutes"] = None
    
    return stats


def validate_session_data(session_data: Dict[str, Any]) -> Dict[str, List[str]]:
    """Validate session data and return any errors"""
    errors = []
    
    required_fields = ["customer_name", "customer_email"]
    for field in required_fields:
        if not session_data.get(field):
            errors.append(f"Missing required field: {field}")
    
    # Validate email format
    email = session_data.get("customer_email", "")
    if email and "@" not in email:
        errors.append("Invalid email format")
    
    # Validate flight number format (if provided)
    flight_no = session_data.get("flight_no", "")
    if flight_no and len(flight_no) < 3:
        errors.append("Flight number appears to be too short")
    
    return {"errors": errors, "valid": len(errors) == 0}


def create_response_template(response_type: str, session_id: str) -> Dict[str, Any]:
    """Create a standardized response template"""
    base_template = {
        "session_id": session_id,
        "timestamp": datetime.now().isoformat(),
        "type": response_type
    }
    
    if response_type == "error":
        base_template.update({
            "error_code": "UNKNOWN_ERROR",
            "message": "An unexpected error occurred"
        })
    elif response_type == "success":
        base_template.update({
            "status": "success",
            "data": {}
        })
    elif response_type == "streaming":
        base_template.update({
            "content": "",
            "is_complete": False
        })
    
    return base_template


async def fetch_kb_context(query: str, knowledge_service_url: str) -> Optional[List[Dict[str, Any]]]:
    """Search knowledge base via knowledge-engine"""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                f"{knowledge_service_url}/kb/search",
                json={"query": query, "k": 3}
            )
            if response.status_code == 200:
                data = response.json()
                return data.get("results", [])
    except Exception as e:
        print(f"Error fetching KB context: {e}")
    return None


def route_query(message: str) -> str:
    """Determine if query needs KB, database, or flight status for Air New Zealand"""
    message_lower = message.lower()
    
    # Keywords that suggest knowledge base queries (Air New Zealand specific)
    kb_keywords = [
        "policy", "policies", "rule", "rules", "allowance", "baggage", "check-in", 
        "checkin", "excess", "fee", "fees", "dangerous", "goods", "fare", "rebooking", 
        "delay", "credit", "credits", "assistance", "pet", "pets", "loyalty", 
        "cutoff", "cut-off", "compensation", "refund", "refunds", "contact", 
        "channel", "channels", "question", "questions", "sop", "template", "comm",
        "airpoints", "koru", "lounge", "seat", "meal", "special", "medical",
        "wheelchair", "mobility", "unaccompanied", "minor", "infant", "child"
    ]
    
    # Keywords that suggest database queries (flight data, bookings, crew, etc.)
    database_keywords = [
        "flight", "status", "departure", "arrival", "gate", "terminal", "delay", 
        "cancelled", "cancelled", "on-time", "boarding", "departed", "landed",
        "nz", "air new zealand", "akl", "wlg", "chc", "dud", "zqn", "npe",
        "next flight", "flights from", "flights to", "booking", "pnr", "reservation",
        "crew", "pilot", "flight attendant", "aircraft", "tail number", "passenger",
        "passengers", "count", "available", "duty", "roster", "schedule"
    ]
    
    # Check for KB keywords
    kb_score = sum(1 for keyword in kb_keywords if keyword in message_lower)
    
    # Check for database keywords
    database_score = sum(1 for keyword in database_keywords if keyword in message_lower)
    
    # If KB keywords are present and more than database keywords, route to KB
    if kb_score > 0 and kb_score >= database_score:
        return "kb"
    elif database_score > 0:
        return "database"
    else:
        # Default to KB for general queries
        return "kb"


def get_safe_fallback_response(query_type: str) -> str:
    """Get safe fallback response for unknown queries"""
    if query_type == "database":
        return """• I can't confirm from current info about that specific flight or booking
• Please check our website or mobile app for real-time updates
• Contact our call center for immediate assistance

Heads up: Flight information changes frequently, so always verify before traveling."""
    elif query_type == "flight":
        return """• I can't confirm from current info about your flight status
• Please check our website or mobile app for real-time updates
• Contact our call center for immediate assistance

Heads up: Flight information changes frequently, so always verify before traveling."""
    else:
        return """• I can't confirm from current info about that specific question
• Please contact our support team for detailed assistance
• You can also check our website for general information

Heads up: Our support team has access to the most up-to-date information and can provide personalized assistance."""


def format_kb_response(chunks: List[Dict[str, Any]], sources: List[str]) -> str:
    """Format KB responses with Air New Zealand style formatting"""
    if not chunks:
        return "I can't confirm from current info. Please contact our support team for assistance."
    
    response_parts = []
    source_citations = []
    
    # Process each chunk and create bullet points
    for i, chunk in enumerate(chunks, 1):
        snippet = chunk.get("snippet", "")
        source = chunk.get("source", "unknown")
        category = chunk.get("category", "unknown")
        
        # Add source citation
        citation = f"[{i}]"
        source_citations.append(f"{citation} {source} ({category})")
        
        # Format as bullet point
        bullet_point = f"• {snippet}"
        response_parts.append(bullet_point)
    
    # Combine response with sources
    response = "\n".join(response_parts)
    
    # Add source footnotes
    if source_citations:
        response += f"\n\nSources:\n" + "\n".join(source_citations)
    
    return response


def format_database_response(db_data: Dict[str, Any], sources: List[str]) -> str:
    """Format database responses with Air New Zealand style formatting"""
    if not db_data:
        return "I can't confirm from current info. Please contact our support team for assistance."

    answer = (db_data.get("answer") or "").strip()
    rows = db_data.get("rows", []) or []
    args = db_data.get("args", {}) or {}

    source_index = len(sources) + 1
    source_label = f"[source {source_index}]"
    sources.append("Air New Zealand operational database (historical schedule)")

    if not rows:
        destination = args.get("destination")
        origin = args.get("origin")
        if destination:
            destination = destination.upper()
        if origin:
            origin = origin.upper()
        if origin and destination:
            route_phrase = f" from {origin} to {destination}"
        elif destination:
            route_phrase = f" to {destination}"
        elif origin:
            route_phrase = f" from {origin}"
        else:
            route_phrase = " for the requested route"

        return (
            f"• There are no flights{route_phrase} scheduled for the coming days in the current operations dataset. {source_label}"
            "\n"
            f"• Our records only include historical flights right now, so please check official channels for future schedules. {source_label}" 
        )

    if answer.startswith("•"):
        return answer

    return f"{answer}\n\n{source_label}"


def create_air_nz_system_prompt(context_str: str, grounding_info: str = None, query_type: str = "general") -> str:
    """Create Air New Zealand system prompt with enterprise-ready restrictions"""

    base_prompt = """You are an Air New Zealand customer service agent. You must follow these strict guidelines:

RESPONSE RESTRICTIONS:
- ONLY use information provided in the context below
- NEVER make up or assume information not explicitly provided
- ALWAYS cite sources for all claims using [source] footnotes
- Use high-level, non-committal language for uncertain information
- If you don't have specific information, say "I can't confirm from current info"

RESPONSE FORMAT:
- Start with 2-4 bullet points (•)
- Add "Heads up:" for any exceptions or important notes
- Include [source] footnotes for each claim
- Use "I can't confirm from current info" for uncertainty

QUERY ROUTING:
- Flight status queries → use flight_status tool
- Policy questions → use kb_search results
- Unknown queries → provide safe fallback response

Session Context:
{context_str}"""

    if grounding_info:
        if query_type == "kb":
            base_prompt += f"""

Knowledge Base Information:
{grounding_info}

IMPORTANT: You must ONLY use information from the provided knowledge base and session context. 
Do not make up or assume any information not explicitly provided. 
Always cite sources when referencing policy information.
If you don't have specific information, direct customers to contact support for detailed assistance."""
        elif query_type in {"database", "flight"}:
            base_prompt += f"""

Database Information:
{grounding_info}

IMPORTANT: You must ONLY use the database facts provided above. 
If the data shows no availability, communicate that clearly without speculation. 
Never invent future schedules—direct customers to official channels for live updates."""

    base_prompt += """

Always be professional, helpful, and empathetic. If you don't have specific information, 
direct customers to contact support for detailed assistance."""

    return base_prompt.format(context_str=context_str)

def format_air_nz_response(response: str, sources: List[str] = None) -> str:
    """Format response according to Air New Zealand guidelines"""
    
    # If response is already formatted with bullet points, return as-is
    if response.startswith("•"):
        return response
    
    # Split response into sentences for bullet point formatting
    sentences = [s.strip() for s in response.split('.') if s.strip()]
    
    # Take first 2-4 sentences for bullet points
    bullet_sentences = sentences[:min(4, len(sentences))]
    
    # Format as bullet points
    formatted_response = "\n".join([f"• {sentence}." for sentence in bullet_sentences])
    
    # Add remaining sentences if any
    if len(sentences) > 4:
        remaining = ". ".join(sentences[4:])
        formatted_response += f"\n\n{remaining}."
    
    # Add source citations if provided
    if sources:
        formatted_response += f"\n\nSources:\n" + "\n".join(sources)
    
    return formatted_response


def add_heads_up_warning(response: str, warning: str) -> str:
    """Add a 'Heads up' warning to the response"""
    if not warning:
        return response
    
    # Insert heads up after first bullet point
    lines = response.split('\n')
    if len(lines) > 1 and lines[0].startswith('•'):
        lines.insert(1, f"Heads up: {warning}")
        return '\n'.join(lines)
    else:
        return f"Heads up: {warning}\n\n{response}"


async def monitor_system_health(redis_manager, connection_manager) -> Dict[str, Any]:
    """Monitor system health and performance"""
    health_status = {
        "timestamp": datetime.now().isoformat(),
        "redis_connected": bool(redis_manager.redis_client),
        "active_connections": len(connection_manager.active_connections),
        "active_sessions": len(connection_manager.session_connections),
        "memory_usage_mb": 0,  # Would need psutil or similar
        "cpu_usage_percent": 0  # Would need psutil or similar
    }
    
    # Check Redis connectivity
    try:
        if redis_manager.redis_client:
            await redis_manager.redis_client.ping()
            health_status["redis_ping"] = True
        else:
            health_status["redis_ping"] = False
    except:
        health_status["redis_ping"] = False
    
    # Calculate average connection duration
    if connection_manager.connection_metadata:
        current_time = datetime.now()
        durations = []
        for metadata in connection_manager.connection_metadata.values():
            try:
                connected_at = metadata["connected_at"]
                duration = (current_time - connected_at).total_seconds()
                durations.append(duration)
            except:
                pass
        
        if durations:
            health_status["avg_connection_duration_seconds"] = sum(durations) / len(durations)
            health_status["max_connection_duration_seconds"] = max(durations)
    
    return health_status
