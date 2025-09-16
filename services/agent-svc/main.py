import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'shared'))

from base_service import BaseService
from fastapi import HTTPException, Request
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import psycopg, httpx, json
from utils import LATENCY, log_startup

# Initialize base service
service = BaseService("agent-svc", "1.0.0")
app = service.get_app()

# Get environment variables using the base service
DB_HOST = service.get_env_var("DB_HOST", "localhost")
DB_PORT = service.get_env_int("DB_PORT", 5432)
DB_NAME = service.get_env_var("DB_NAME", "flightops")
DB_USER = service.get_env_var("DB_USER", "postgres")
DB_PASS = service.get_env_var("DB_PASS", "postgres")
RETRIEVAL_URL = service.get_env_var("RETRIEVAL_URL", "http://localhost:8081")
COMMS_URL = service.get_env_var("COMMS_URL", "http://localhost:8083")
ALLOW_UNGROUNDED = service.get_env_bool("ALLOW_UNGROUNDED_ANSWERS", False)

class Ask(BaseModel):
    question: str
    flight_no: Optional[str] = None
    date: Optional[str] = None

def pii_scrub(text: str) -> str:
    import re
    text = re.sub(r"[A-Z0-9]{6}(?=\b)", "[PNR]", text)
    text = re.sub(r"[\w\.-]+@[\w\.-]+", "[EMAIL]", text)
    text = re.sub(r"\+?\d[\d\s-]{6,}", "[PHONE]", text)
    return text

def tool_flight_lookup(flight_no: str, date: str) -> Dict[str, Any]:
    with psycopg.connect(host=DB_HOST,port=DB_PORT,dbname=DB_NAME,user=DB_USER,password=DB_PASS) as conn:
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
    with psycopg.connect(host=DB_HOST,port=DB_PORT,dbname=DB_NAME,user=DB_USER,password=DB_PASS) as conn:
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
    with psycopg.connect(host=DB_HOST,port=DB_PORT,dbname=DB_NAME,user=DB_USER,password=DB_PASS) as conn:
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

def tool_rebooking_options(flight_no: str, date: str) -> List[Dict[str, Any]]:
    """Generate rebooking options based on passenger count and route type."""
    # Get passenger count and connection details
    impact = tool_impact_assessor(flight_no, date)
    pax_count = impact.get("passengers", 0)
    connecting_pax = impact.get("connecting_passengers", 0)
    
    # Get flight details to determine route type
    flight = tool_flight_lookup(flight_no, date)
    origin = flight.get("origin", "")
    destination = flight.get("destination", "")
    
    # Determine if domestic or international
    is_domestic = origin in ["AKL", "WLG", "CHC"] and destination in ["AKL", "WLG", "CHC"]
    
    options = []
    
    # Base option: Next available flight
    if is_domestic:
        base_plan = "Rebook on next available NZ domestic service + meal voucher"
        if connecting_pax > 0:
            base_plan += f" (priority for {connecting_pax} connecting passengers)"
        options.append({
            "plan": base_plan,
            "cx_score": 0.85,
            "cost_estimate": 80 * pax_count,
            "notes": "Minimizes missed connections, domestic route"
        })
    else:
        base_plan = "Rebook on next available NZ international service + meal voucher"
        if connecting_pax > 0:
            base_plan += f" (priority for {connecting_pax} connecting passengers)"
        options.append({
            "plan": base_plan,
            "cx_score": 0.82,
            "cost_estimate": 120 * pax_count,
            "notes": "International route, higher cost but better service"
        })
    
    # High passenger count option: Split across carriers
    if pax_count >= 50:
        options.append({
            "plan": f"Split {pax_count} passengers across NZ + partner airline",
            "cx_score": 0.75,
            "cost_estimate": 60 * pax_count,
            "notes": "High passenger count, cost-effective but more complex"
        })
    else:
        # Low passenger count option: Direct rebooking
        options.append({
            "plan": "Direct rebooking on next NZ service + compensation",
            "cx_score": 0.88,
            "cost_estimate": 100 * pax_count,
            "notes": "Low passenger count, premium service"
        })
    
    # Third option: Flexible rebooking with connection protection
    if connecting_pax > 0:
        options.append({
            "plan": f"Flexible rebooking within 48h + connection protection for {connecting_pax} passengers + accommodation if needed",
            "cx_score": 0.80,
            "cost_estimate": 90 * pax_count + 50 * connecting_pax,
            "notes": "Balanced approach with connection protection"
        })
    else:
        options.append({
            "plan": "Flexible rebooking within 48h + accommodation if needed",
            "cx_score": 0.80,
            "cost_estimate": 90 * pax_count,
            "notes": "Balanced approach, good for mixed passenger needs"
        })
    
    return options[:3]  # Return top 3 options

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
            q = pii_scrub(body.question)
            fno = body.flight_no or "NZ123"
            date = body.date or "2025-09-17"

            flight = tool_flight_lookup(fno, date)
            impact = tool_impact_assessor(fno, date)
            crew_details = tool_crew_details(fno, date)
            options = tool_rebooking_options(fno, date)
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
            
            service.log_request(request, {"status": "success"})
            return result
        except Exception as e:
            service.log_error(e, "ask endpoint")
            raise

@app.post("/draft_comms")
def draft_comms(body: Ask, request: Request):
    try:
        # Compose with comms-svc using grounded context
        q = body.question or "Draft email + SMS for affected passengers"
        fno = body.flight_no or "NZ123"
        date = body.date or "2025-09-17"
        impact = tool_impact_assessor(fno, date)
        crew_details = tool_crew_details(fno, date)
        options = tool_rebooking_options(fno, date)
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