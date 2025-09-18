import sys
import os
import json
from contextlib import asynccontextmanager
from typing import List, Dict, Any, Optional

import httpx
import psycopg
from fastapi import HTTPException, Request
from pydantic import BaseModel
from psycopg_pool import ConnectionPool

sys.path.append(os.path.join(os.path.dirname(__file__), 'shared'))

from base_service import BaseService
from prompt_manager import PromptManager
from llm_tracker import LLMTracker
from utils import LATENCY, log_startup

# Initialize base service
service = BaseService("agent-svc", "1.0.0")
app = service.get_app()

# Get environment variables using the base service
DB_HOST = service.get_env_var("DB_HOST")
DB_PORT = service.get_env_int("DB_PORT", 5432)
DB_NAME = service.get_env_var("DB_NAME")
DB_USER = service.get_env_var("DB_USER")
DB_PASS = service.get_env_var("DB_PASS")
RETRIEVAL_URL = service.get_env_var("RETRIEVAL_URL")
COMMS_URL = service.get_env_var("COMMS_URL")
OPENAI_API_KEY = service.get_env_var("OPENAI_API_KEY")
CHAT_MODEL = service.get_env_var("CHAT_MODEL")
ALLOW_UNGROUNDED = service.get_env_bool("ALLOW_UNGROUNDED_ANSWERS", False)

# Create database connection pool
DB_CONN_STRING = f"host={DB_HOST} port={DB_PORT} dbname={DB_NAME} user={DB_USER} password={DB_PASS}"
db_pool = None

@asynccontextmanager
async def lifespan(app):
    global db_pool
    log_startup("agent-svc")
    
    # Initialize connection pool
    db_pool = ConnectionPool(DB_CONN_STRING, min_size=2, max_size=10)
    
    yield
    
    # Close connection pool on shutdown
    if db_pool:
        db_pool.close()

# Set lifespan for the app
app.router.lifespan_context = lifespan

class Ask(BaseModel):
    question: str
    flight_no: str
    date: str

def pii_scrub(text: str) -> str:
    import re
    text = re.sub(r"[A-Z0-9]{6}(?=\b)", "[PNR]", text)
    text = re.sub(r"[\w\.-]+@[\w\.-]+", "[EMAIL]", text)
    text = re.sub(r"\+?\d[\d\s-]{6,}", "[PHONE]", text)
    return text

def tool_flight_lookup(flight_no: str, date: str) -> Dict[str, Any]:
    with db_pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT flight_no, origin, destination, sched_dep_time, sched_arr_time, status, tail_number
                FROM flights
                WHERE flight_no=%s AND flight_date=%s
            """, (flight_no, date))
            row = cur.fetchone()
            if not row:
                return {}
            return {"flight_no":row[0], "origin":row[1], "destination":row[2],
                    "sched_dep":row[3], "sched_arr":row[4], "status":row[5], "tail_number":row[6]}

def tool_impact_assessor(flight_no: str, date: str) -> Dict[str, Any]:
    with db_pool.connection() as conn:
        with conn.cursor() as cur:
            # Get passenger count and connection details
            cur.execute("""
                SELECT COUNT(*), COUNT(CASE WHEN has_connection = 'TRUE' THEN 1 END)
                FROM bookings
                WHERE flight_no=%s AND flight_date=%s
            """, (flight_no, date))
            pax_data = cur.fetchone()
            pax = pax_data[0]
            connecting_pax = pax_data[1]
            
            # Get crew count and roles
            cur.execute("""
                SELECT COUNT(*), STRING_AGG(DISTINCT crew_role, ', ')
                FROM crew_roster
                WHERE flight_no=%s AND flight_date=%s
            """, (flight_no, date))
            crew_data = cur.fetchone()
            crew = crew_data[0]
            crew_roles = crew_data[1] or "Unknown"
            
            # Get aircraft status
            cur.execute("""
                SELECT f.tail_number, a.status, a.current_location
                FROM flights f
                LEFT JOIN aircraft_status a ON f.tail_number = a.tail_number
                WHERE f.flight_no=%s AND f.flight_date=%s
            """, (flight_no, date))
            aircraft_data = cur.fetchone()
            aircraft_status = aircraft_data[1] if aircraft_data else "Unknown"
            aircraft_location = aircraft_data[2] if aircraft_data else "Unknown"
            
    return {
        "passengers": pax, 
        "connecting_passengers": connecting_pax,
        "crew": crew, 
        "crew_roles": crew_roles,
        "aircraft_status": aircraft_status,
        "aircraft_location": aircraft_location,
        "summary": f"{pax} passengers ({connecting_pax} with connections) and {crew} crew affected. Aircraft status: {aircraft_status} at {aircraft_location}."
    }

def tool_crew_details(flight_no: str, date: str) -> List[Dict[str, Any]]:
    """Get detailed crew information for a flight."""
    with db_pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT cr.crew_id, cr.crew_role, cd.crew_name, cd.duty_start_time, cd.max_duty_hours
                FROM crew_roster cr
                LEFT JOIN crew_details cd ON cr.crew_id = cd.crew_id
                WHERE cr.flight_no=%s AND cr.flight_date=%s
                ORDER BY cr.crew_role
            """, (flight_no, date))
            crew_members = []
            for row in cur.fetchall():
                crew_members.append({
                    "crew_id": row[0],
                    "role": row[1],
                    "name": row[2] or "Unknown",
                    "duty_start": row[3] or "Unknown",
                    "max_hours": row[4] or 0
                })
    return crew_members

def tool_advanced_rebooking_optimizer(flight_no: str, date: str) -> List[Dict[str, Any]]:
    """Advanced rebooking optimization with LLM-powered analysis."""
    # Get passenger count and connection details
    impact = tool_impact_assessor(flight_no, date)
    pax_count = impact.get("passengers", 0)
    connecting_pax = impact.get("connecting_passengers", 0)
    
    # Get flight details to determine route type
    flight = tool_flight_lookup(flight_no, date)
    origin = flight.get("origin", "")
    destination = flight.get("destination", "")
    
    # Get passenger preferences and loyalty data (mock)
    passenger_profiles = get_passenger_profiles(flight_no, date)
    
    # Determine if domestic or international
    is_domestic = origin in ["AKL", "WLG", "CHC"] and destination in ["AKL", "WLG", "CHC"]
    
    # Generate base options
    options = generate_base_rebooking_options(flight_no, date, pax_count, connecting_pax, is_domestic)
    
    # Use LLM to optimize and rank options
    optimized_options = optimize_rebooking_with_llm(options, passenger_profiles, flight, impact)
    
    return optimized_options[:5]  # Return top 5 options

def get_passenger_profiles(flight_no: str, date: str) -> List[Dict[str, Any]]:
    """Get passenger profiles and preferences (mock data)"""
    with db_pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT pnr, passenger_name, has_connection, connecting_flight_no
                FROM bookings
                WHERE flight_no = %s AND flight_date = %s
            """, (flight_no, date))
            bookings = cur.fetchall()
    
    profiles = []
    for pnr, name, has_connection, connecting_flight in bookings:
        # Mock passenger profile data
        profiles.append({
            "pnr": pnr,
            "name": name,
            "has_connection": has_connection == "TRUE",
            "connecting_flight": connecting_flight,
            "loyalty_tier": "Gold" if "VIP" in name else "Silver" if "Premium" in name else "Bronze",
            "preferences": ["window_seat", "early_departure"] if "Early" in name else ["aisle_seat"],
            "special_needs": ["wheelchair"] if "Access" in name else [],
            "travel_purpose": "business" if "Corp" in name else "leisure"
        })
    
    return profiles

def generate_base_rebooking_options(flight_no: str, date: str, pax_count: int, connecting_pax: int, is_domestic: bool) -> List[Dict[str, Any]]:
    """Generate base rebooking options"""
    options = []
    
    # Option 1: Next available flight
    if is_domestic:
        base_plan = "Rebook on next available NZ domestic service + meal voucher"
        if connecting_pax > 0:
            base_plan += f" (priority for {connecting_pax} connecting passengers)"
        options.append({
            "plan": base_plan,
            "cx_score": 0.85,
            "cost_estimate": 80 * pax_count,
            "notes": "Minimizes missed connections, domestic route",
            "passenger_impact": "Low",
            "implementation_time": "30 minutes",
            "success_probability": 0.9
        })
    else:
        base_plan = "Rebook on next available NZ international service + meal voucher"
        if connecting_pax > 0:
            base_plan += f" (priority for {connecting_pax} connecting passengers)"
        options.append({
            "plan": base_plan,
            "cx_score": 0.82,
            "cost_estimate": 120 * pax_count,
            "notes": "International route, higher cost but better service",
            "passenger_impact": "Low",
            "implementation_time": "45 minutes",
            "success_probability": 0.85
        })
    
    # Option 2: Split across carriers (for high passenger count)
    if pax_count >= 50:
        options.append({
            "plan": f"Split {pax_count} passengers across NZ + partner airline",
            "cx_score": 0.75,
            "cost_estimate": 60 * pax_count,
            "notes": "High passenger count, cost-effective but more complex",
            "passenger_impact": "Medium",
            "implementation_time": "2 hours",
            "success_probability": 0.7
        })
    else:
        # Direct rebooking for low passenger count
        options.append({
            "plan": "Direct rebooking on next NZ service + compensation",
            "cx_score": 0.88,
            "cost_estimate": 100 * pax_count,
            "notes": "Low passenger count, premium service",
            "passenger_impact": "Low",
            "implementation_time": "20 minutes",
            "success_probability": 0.95
        })
    
    # Option 3: Flexible rebooking
    if connecting_pax > 0:
        options.append({
            "plan": f"Flexible rebooking within 48h + connection protection for {connecting_pax} passengers + accommodation if needed",
            "cx_score": 0.80,
            "cost_estimate": 90 * pax_count + 50 * connecting_pax,
            "notes": "Balanced approach with connection protection",
            "passenger_impact": "Low",
            "implementation_time": "1 hour",
            "success_probability": 0.8
        })
    else:
        options.append({
            "plan": "Flexible rebooking within 48h + accommodation if needed",
            "cx_score": 0.80,
            "cost_estimate": 90 * pax_count,
            "notes": "Balanced approach, good for mixed passenger needs",
            "passenger_impact": "Low",
            "implementation_time": "45 minutes",
            "success_probability": 0.85
        })
    
    # Option 4: Premium rebooking (for high-value passengers)
    vip_passengers = len([p for p in get_passenger_profiles(flight_no, date) if p["loyalty_tier"] in ["Gold", "Platinum"]])
    if vip_passengers > 0:
        options.append({
            "plan": f"Premium rebooking for {vip_passengers} VIP passengers + standard rebooking for others",
            "cx_score": 0.92,
            "cost_estimate": 150 * vip_passengers + 80 * (pax_count - vip_passengers),
            "notes": "VIP passengers get priority treatment and premium options",
            "passenger_impact": "Very Low",
            "implementation_time": "1.5 hours",
            "success_probability": 0.9
        })
    
    # Option 5: Alternative routing
    # Get flight details to determine origin and destination
    try:
        flight_details = tool_flight_lookup(flight_no, date)
        origin = flight_details.get("origin", "AKL")
        destination = flight_details.get("destination", "SYD")
    except:
        # Fallback to default values if flight details not available
        origin = "AKL"
        destination = "SYD"
    
    options.append({
        "plan": f"Alternative routing via {get_alternative_hub(origin, destination)} + ground transport",
        "cx_score": 0.70,
        "cost_estimate": 70 * pax_count,
        "notes": "Alternative routing may require ground transport",
        "passenger_impact": "Medium",
        "implementation_time": "3 hours",
        "success_probability": 0.6
    })
    
    return options

def get_alternative_hub(origin: str, destination: str) -> str:
    """Get alternative hub for routing (mock)"""
    hubs = {
        "AKL": "SYD",
        "WLG": "AKL", 
        "CHC": "AKL",
        "SYD": "AKL",
        "LAX": "SFO"
    }
    return hubs.get(origin, "AKL")

def optimize_rebooking_with_llm(options: List[Dict[str, Any]], passenger_profiles: List[Dict[str, Any]], 
                               flight: Dict[str, Any], impact: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Use LLM to optimize rebooking options"""
    import time
    start_time = time.time()
    
    print(f"DEBUG: optimize_rebooking_with_llm called with OPENAI_API_KEY: {'SET' if OPENAI_API_KEY else 'NOT SET'}")
    print(f"DEBUG: OPENAI_API_KEY length: {len(OPENAI_API_KEY) if OPENAI_API_KEY else 0}")
    print(f"DEBUG: OPENAI_API_KEY starts with 'sk-': {OPENAI_API_KEY.startswith('sk-') if OPENAI_API_KEY else False}")
    print(f"DEBUG: CHAT_MODEL: {CHAT_MODEL}")
    
    if not OPENAI_API_KEY or not OPENAI_API_KEY.startswith('sk-'):
        print(f"DEBUG: No valid OpenAI API key, falling back to rule-based")
        return optimize_rebooking_rule_based(options, passenger_profiles, flight, impact)
    
    try:
        from openai import OpenAI
        client = OpenAI(api_key=OPENAI_API_KEY)
        
        prompt = PromptManager.get_rebooking_optimization_prompt(flight, impact, passenger_profiles, options)
        print(f"DEBUG: Generated prompt length: {len(prompt)}")
        print(f"DEBUG: Prompt preview: {prompt[:200]}...")
        print(f"DEBUG: Sending prompt to LLM model {CHAT_MODEL}")
        
        response = client.chat.completions.create(
            model=CHAT_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3
        )
        print(f"DEBUG: LLM response received")
        
        content = response.choices[0].message.content
        print(f"DEBUG: LLM response length: {len(content)}")
        print(f"DEBUG: LLM response preview: {content[:200]}...")
        duration_ms = (time.time() - start_time) * 1000
        
        # Track the LLM message
        llm_message = LLMTracker.track_llm_call(
            service_name="agent-svc",
            prompt=prompt,
            response=content,
            model=CHAT_MODEL,
            tokens_used=response.usage.total_tokens if response.usage else None,
            duration_ms=duration_ms,
            metadata={
                "function": "optimize_rebooking_with_llm",
                "flight_no": flight.get("flight_no"),
                "passenger_count": len(passenger_profiles)
            }
        )
        
        try:
            optimized = json.loads(content)
            # Ensure we have the required fields
            for option in optimized:
                if "cx_score" not in option:
                    option["cx_score"] = 0.8
                if "cost_estimate" not in option:
                    option["cost_estimate"] = 100
                if "success_probability" not in option:
                    option["success_probability"] = 0.8
            
            # Add LLM message to the result
            optimized.append({"llm_message": llm_message})
            return optimized
        except json.JSONDecodeError:
            print(f"DEBUG: JSON decode error, falling back to rule-based")
            return optimize_rebooking_rule_based(options, passenger_profiles, flight, impact)
            
    except Exception as e:
        print(f"DEBUG: LLM call failed with error: {e}")
        service.log_error(e, "LLM rebooking optimization")
        
        # Create a test LLM message to show in UI even when API fails
        import time
        test_message = {
            "id": "test-message-" + str(int(time.time())),
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
            "service": "agent-svc",
            "prompt": prompt[:200] + "..." if len(prompt) > 200 else prompt,
            "response": f"LLM call failed: {str(e)[:200]}...",
            "model": CHAT_MODEL,
            "tokens_used": 0,
            "duration_ms": (time.time() - start_time) * 1000,
            "metadata": {
                "function": "optimize_rebooking_with_llm",
                "error": True,
                "error_type": type(e).__name__
            }
        }
        
        # Add the test message to the first option
        if options:
            options[0]["llm_message"] = test_message
        
        return optimize_rebooking_rule_based(options, passenger_profiles, flight, impact)

def optimize_rebooking_rule_based(options: List[Dict[str, Any]], passenger_profiles: List[Dict[str, Any]], 
                                 flight: Dict[str, Any], impact: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Rule-based rebooking optimization fallback"""
    print(f"DEBUG: Using rule-based rebooking optimization (no LLM call)")
    
    vip_count = len([p for p in passenger_profiles if p["loyalty_tier"] in ["Gold", "Platinum"]])
    connecting_count = len([p for p in passenger_profiles if p["has_connection"]])
    
    # Adjust scores based on passenger mix
    for option in options:
        # Boost VIP options
        if "VIP" in option["plan"] or "premium" in option["plan"].lower():
            option["cx_score"] += 0.05 * vip_count
        
        # Boost connection protection
        if "connection" in option["plan"].lower():
            option["cx_score"] += 0.03 * connecting_count
        
        # Adjust cost based on passenger count
        base_cost = option["cost_estimate"]
        if len(passenger_profiles) > 100:
            option["cost_estimate"] = base_cost * 0.9  # Volume discount
        elif len(passenger_profiles) < 20:
            option["cost_estimate"] = base_cost * 1.1  # Small group premium
    
    # Sort by value (CX score / cost ratio)
    for option in options:
        if option["cost_estimate"] > 0:
            option["value_score"] = option["cx_score"] / (option["cost_estimate"] / 100)
        else:
            option["value_score"] = option["cx_score"]
    
    options.sort(key=lambda x: x["value_score"], reverse=True)
    return options

def tool_policy_grounder(question: str, k:int=3) -> Dict[str, Any]:
    try:
        r = httpx.post(f"{RETRIEVAL_URL}/search", json={"q":question, "k":k})
        results = r.json().get("results", [])
        cits = [f"{x.get('title')}: {x.get('snippet')}" for x in results]
        return {"citations": cits}
    except Exception as e:
        service.log_error(e, "policy_grounder")
        return {"citations": []}

def ensure_grounded(citations: List[str]) -> bool:
    if ALLOW_UNGROUNDED: return True
    return len(citations) > 0

@app.post("/ask")
def ask(body: Ask, request: Request):
    with LATENCY.labels("agent-svc","/ask","POST").time():
        try:
            print(f"DEBUG: /ask endpoint called with question: {body.question}")
            q = pii_scrub(body.question)
            fno = body.flight_no
            date = body.date

            flight = tool_flight_lookup(fno, date)
            impact = tool_impact_assessor(fno, date)
            crew_details = tool_crew_details(fno, date)
            print(f"DEBUG: About to call tool_advanced_rebooking_optimizer")
            options = tool_advanced_rebooking_optimizer(fno, date)
            print(f"DEBUG: tool_advanced_rebooking_optimizer returned {len(options)} options")
            policy = tool_policy_grounder(q + " policy rebooking compensation customer communication")

            if not ensure_grounded(policy.get("citations", [])):
                raise HTTPException(status_code=400, detail="Unable to verify policy grounding for this question.")

            options_summary = "; ".join([f"{o['plan']} (cx={o['cx_score']:.2f}, cost≈${o['cost_estimate']})" for o in options])
            payload = {
                "flight": flight,
                "impact": impact,
                "crew_details": crew_details,
                "options": options,
                "policy_citations": policy.get("citations", []),
            }
            result = {"answer": {
                        "issue": f"Delay/disruption for {fno} on {date}",
                        "impact_summary": impact["summary"],
                        "options_summary": options_summary,
                        "citations": policy.get("citations", [])
                    },
                    "tools_payload": payload}
            
            # Extract LLM message from options if present
            print(f"DEBUG: Checking {len(options)} options for LLM message")
            for i, option in enumerate(options):
                if isinstance(option, dict) and "llm_message" in option:
                    print(f"DEBUG: Found LLM message in option {i}")
                    result["llm_message"] = option["llm_message"]
                    break
            print(f"DEBUG: Final result has llm_message: {'llm_message' in result}")
            
            service.log_request(request, {"status": "success"})
            return result
        except Exception as e:
            service.log_error(e, "ask endpoint")
            raise

@app.post("/test_llm")
def test_llm(request: Request):
    """Test endpoint for general LLM calls using prompt manager."""
    try:
        import time
        start_time = time.time()
        
        # Get the test prompt from prompt manager
        prompt = PromptManager.get_test_joke_fact_prompt()
        
        print(f"DEBUG: test_llm endpoint called with prompt: {prompt[:100]}...")
        
        try:
            from openai import OpenAI
            client = OpenAI(api_key=OPENAI_API_KEY)
            
            response = client.chat.completions.create(
                model=CHAT_MODEL,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.8,
                max_tokens=200
            )
            
            content = response.choices[0].message.content
            duration_ms = (time.time() - start_time) * 1000
            
            # Track the LLM message
            llm_message = LLMTracker.track_llm_call(
                service_name="agent-svc",
                prompt=prompt,
                response=content,
                model=CHAT_MODEL,
                tokens_used=response.usage.total_tokens if response.usage else None,
                duration_ms=duration_ms,
                metadata={
                    "function": "test_llm",
                    "endpoint": "test_llm"
                }
            )
            
            result = {
                "answer": content,
                "llm_message": llm_message
            }
            
            service.log_request(request, {"status": "success"})
            return result
            
        except Exception as e:
            print(f"DEBUG: LLM call failed with error: {e}")
            service.log_error(e, "test_llm LLM call")
            
            # Create a test LLM message to show in UI even when API fails
            test_message = {
                "id": "test-message-" + str(int(time.time())),
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
                "service": "agent-svc",
                "prompt": prompt[:200] + "..." if len(prompt) > 200 else prompt,
                "response": f"LLM call failed: {str(e)[:200]}...",
                "model": CHAT_MODEL,
                "tokens_used": 0,
                "duration_ms": (time.time() - start_time) * 1000,
                "metadata": {
                    "function": "test_llm",
                    "error": True,
                    "error_type": type(e).__name__
                }
            }
            
            result = {
                "answer": f"LLM call failed: {str(e)}",
                "llm_message": test_message
            }
            
            service.log_request(request, {"status": "error"})
            return result
            
    except Exception as e:
        service.log_error(e, "test_llm endpoint")
        raise

@app.post("/draft_comms")
def draft_comms(body: Ask, request: Request):
    try:
        # Compose with comms-svc using grounded context
        q = body.question or "Draft email + SMS for affected passengers"
        fno = body.flight_no
        date = body.date
        impact = tool_impact_assessor(fno, date)
        crew_details = tool_crew_details(fno, date)
        options = tool_advanced_rebooking_optimizer(fno, date)
        policy = tool_policy_grounder(q)
        if not ensure_grounded(policy.get("citations", [])):
            raise HTTPException(status_code=400, detail="Policy grounding required.")

        context = {
            "flight_no": fno, "date": date,
            "issue":"Weather-related delay",
            "impact_summary": impact["summary"],
            "crew_summary": f"{len(crew_details)} crew members affected: {', '.join([c['role'] + ' (' + c['name'] + ')' for c in crew_details[:3]])}",
            "options_summary": "; ".join([o["plan"] for o in options]),
            "policy_citations": policy.get("citations", [])
        }
        r = httpx.post(f"{COMMS_URL}/draft", json={"context": context, "tone":"empathetic", "channel":"email"}, timeout=60.0)
        result = {"context": context, "draft": r.json().get("draft")}
        
        service.log_request(request, {"status": "success"})
        return result
    except Exception as e:
        service.log_error(e, "draft_comms endpoint")
        raise