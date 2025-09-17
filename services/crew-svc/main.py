import sys
import os
import json
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

import httpx
import psycopg
from fastapi import HTTPException, Request
from pydantic import BaseModel
from psycopg_pool import ConnectionPool

sys.path.append(os.path.join(os.path.dirname(__file__), 'shared'))

from base_service import BaseService
from prompt_manager import PromptManager
from utils import LATENCY, log_startup

# Initialize base service
service = BaseService("crew-svc", "1.0.0")
app = service.get_app()

# Get environment variables
DB_HOST = service.get_env_var("DB_HOST", "localhost")
DB_PORT = service.get_env_int("DB_PORT", 5432)
DB_NAME = service.get_env_var("DB_NAME", "flightops")
DB_USER = service.get_env_var("DB_USER", "postgres")
DB_PASS = service.get_env_var("DB_PASS", "postgres")
OPENAI_API_KEY = service.get_env_var("OPENAI_API_KEY", "")
CHAT_MODEL = service.get_env_var("CHAT_MODEL", "gpt-4o-mini")

# Create database connection pool
DB_CONN_STRING = f"host={DB_HOST} port={DB_PORT} dbname={DB_NAME} user={DB_USER} password={DB_PASS}"
db_pool = None

class CrewOptimizationRequest(BaseModel):
    flight_no: str
    date: str
    disruption_type: Optional[str] = None
    time_constraint: Optional[int] = None  # hours

class CrewSwapRequest(BaseModel):
    flight_no: str
    date: str
    unavailable_crew_id: str
    reason: str

class CrewMember(BaseModel):
    crew_id: str
    name: str
    role: str
    qualifications: List[str]
    current_location: str
    duty_hours: float
    max_duty_hours: float
    rest_required: float
    availability_status: str
    last_flight: Optional[str] = None

@asynccontextmanager
async def lifespan(app):
    global db_pool
    log_startup("crew-svc")
    
    # Initialize connection pool
    db_pool = ConnectionPool(DB_CONN_STRING, min_size=2, max_size=10)
    
    yield
    
    # Close connection pool on shutdown
    if db_pool:
        db_pool.close()

# Set lifespan for the app
app.router.lifespan_context = lifespan

class CrewSwap(BaseModel):
    original_crew: CrewMember
    replacement_crew: CrewMember
    swap_reason: str
    legality_check: bool
    cost_impact: float
    implementation_time: str

def get_crew_qualifications(crew_id: str) -> List[str]:
    """Get crew member qualifications and certifications"""
    # Mock qualifications - in production, integrate with crew management system
    qualifications_map = {
        "CAP001": ["B777", "B787", "A320", "Captain"],
        "FO001": ["B777", "B787", "First Officer"],
        "CC001": ["Cabin Crew", "Safety", "Service"],
        "CC002": ["Cabin Crew", "Safety", "Service", "Senior"],
        "CC003": ["Cabin Crew", "Safety", "Service", "Purser"]
    }
    return qualifications_map.get(crew_id, ["Basic"])

def calculate_duty_hours(crew_id: str, date: str) -> Dict[str, Any]:
    """Calculate current duty hours and rest requirements"""
    with db_pool.connection() as conn:
        with conn.cursor() as cur:
            # Get crew's flights for the day
            cur.execute("""
                SELECT f.sched_dep_time, f.sched_arr_time, f.origin, f.destination
                FROM crew_roster cr
                JOIN flights f ON cr.flight_no = f.flight_no AND cr.flight_date = f.flight_date
                WHERE cr.crew_id = %s AND cr.flight_date = %s
                ORDER BY f.sched_dep_time
            """, (crew_id, date))
            flights = cur.fetchall()
            
            # Calculate duty hours (simplified)
            total_duty_hours = 0
            for flight in flights:
                dep_time, arr_time, origin, destination = flight
                # Mock calculation - in production, use actual time calculations
                flight_duration = 2.5  # hours
                duty_hours = flight_duration + 1.0  # include pre/post flight duties
                total_duty_hours += duty_hours
            
            # Get max duty hours from crew details
            cur.execute("""
                SELECT max_duty_hours, duty_start_time
                FROM crew_details
                WHERE crew_id = %s
            """, (crew_id,))
            result = cur.fetchone()
            max_duty_hours = result[0] if result and result[0] else 8
            duty_start_time = result[1] if result and result[1] else "06:00"
            
            # Calculate rest required
            rest_required = max(0, 12 - (max_duty_hours - total_duty_hours)) if total_duty_hours > 0 else 0
            
            return {
                "duty_hours": total_duty_hours,
                "max_duty_hours": max_duty_hours,
                "rest_required": rest_required,
                "duty_start_time": duty_start_time,
                "flights_today": len(flights)
            }

def check_crew_legality(crew_id: str, flight_no: str, date: str) -> Dict[str, Any]:
    """Check if crew member is legally allowed to operate the flight"""
    duty_info = calculate_duty_hours(crew_id, date)
    
    # Basic legality checks
    violations = []
    is_legal = True
    
    # Duty time check
    if duty_info["duty_hours"] >= duty_info["max_duty_hours"]:
        violations.append("Exceeded maximum duty hours")
        is_legal = False
    
    # Rest requirement check
    if duty_info["rest_required"] > 0:
        violations.append(f"Requires {duty_info['rest_required']} hours rest")
        is_legal = False
    
    # Flight duty period check (simplified)
    if duty_info["flights_today"] >= 4:
        violations.append("Exceeded maximum flights per day")
        is_legal = False
    
    return {
        "is_legal": is_legal,
        "violations": violations,
        "duty_info": duty_info
    }

def find_replacement_crew(unavailable_crew_id: str, flight_no: str, date: str, 
                         required_role: str, required_qualifications: List[str]) -> List[CrewMember]:
    """Find suitable replacement crew members"""
    with db_pool.connection() as conn:
        with conn.cursor() as cur:
            # Get all crew members with the required role
            cur.execute("""
                SELECT cd.crew_id, cd.crew_name, cr.crew_role, cd.max_duty_hours
                FROM crew_details cd
                JOIN crew_roster cr ON cd.crew_id = cr.crew_id
                WHERE cr.crew_role = %s AND cr.crew_id != %s
                ORDER BY cd.crew_name
            """, (required_role, unavailable_crew_id))
            crew_candidates = cur.fetchall()
    
    replacements = []
    for crew_id, name, role, max_hours in crew_candidates:
        # Check legality
        legality = check_crew_legality(crew_id, flight_no, date)
        
        if legality["is_legal"]:
            # Get qualifications
            qualifications = get_crew_qualifications(crew_id)
            
            # Check if qualified for the aircraft type
            aircraft_type = "B777"  # Mock - in production, get from flight data
            is_qualified = aircraft_type in qualifications or "Captain" in qualifications or "First Officer" in qualifications
            
            if is_qualified:
                duty_info = legality["duty_info"]
                replacements.append(CrewMember(
                    crew_id=crew_id,
                    name=name,
                    role=role,
                    qualifications=qualifications,
                    current_location="AKL",  # Mock
                    duty_hours=duty_info["duty_hours"],
                    max_duty_hours=duty_info["max_duty_hours"],
                    rest_required=duty_info["rest_required"],
                    availability_status="Available",
                    last_flight="NZ456"  # Mock
                ))
    
    # Sort by suitability (fewer duty hours, more qualifications)
    replacements.sort(key=lambda x: (x.duty_hours, -len(x.qualifications)))
    return replacements[:5]  # Return top 5 candidates

def generate_llm_crew_analysis(crew_data: Dict[str, Any], disruption_context: str) -> Dict[str, Any]:
    """Use LLM to analyze crew situation and provide recommendations"""
    if not OPENAI_API_KEY:
        return generate_rule_based_crew_analysis(crew_data, disruption_context)
    
    try:
        from openai import OpenAI
        client = OpenAI(api_key=OPENAI_API_KEY)
        
        prompt = PromptManager.get_crew_analysis_prompt(crew_data, disruption_context)
        
        response = client.chat.completions.create(
            model=CHAT_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3
        )
        
        content = response.choices[0].message.content
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            return generate_rule_based_crew_analysis(crew_data, disruption_context)
            
    except Exception as e:
        service.log_error(e, "LLM crew analysis")
        return generate_rule_based_crew_analysis(crew_data, disruption_context)

def generate_rule_based_crew_analysis(crew_data: Dict[str, Any], disruption_context: str) -> Dict[str, Any]:
    """Fallback rule-based crew analysis"""
    concerns = []
    risk_level = "low"
    
    # Analyze crew legality
    for crew in crew_data.get("crew_members", []):
        if not crew.get("is_legal", True):
            concerns.append(f"Crew {crew.get('crew_id')} has legality issues")
            risk_level = "high"
        elif crew.get("duty_hours", 0) > crew.get("max_duty_hours", 8) * 0.8:
            concerns.append(f"Crew {crew.get('crew_id')} approaching duty limits")
            risk_level = "medium" if risk_level != "high" else "high"
    
    # Generate recommendations
    recommendations = []
    if risk_level == "high":
        recommendations.append("Immediate crew replacement required")
    elif risk_level == "medium":
        recommendations.append("Monitor crew duty hours closely")
    
    if "fatigue" in disruption_context.lower():
        recommendations.append("Consider additional rest periods")
    
    return {
        "risk_level": risk_level,
        "concerns": concerns,
        "recommendations": recommendations,
        "priority": 5 if risk_level == "high" else 3,
        "estimated_resolution_time": "2-4 hours" if risk_level == "high" else "1-2 hours"
    }

@app.post("/optimize_crew")
def optimize_crew_assignments(req: CrewOptimizationRequest, request: Request):
    """Optimize crew assignments for a flight"""
    with LATENCY.labels("crew-svc", "/optimize_crew", "POST").time():
        try:
            # Get current crew for the flight
            with db_pool.connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        SELECT cr.crew_id, cr.crew_role, cd.crew_name, cd.max_duty_hours
                        FROM crew_roster cr
                        LEFT JOIN crew_details cd ON cr.crew_id = cd.crew_id
                        WHERE cr.flight_no = %s AND cr.flight_date = %s
                        ORDER BY cr.crew_role
                    """, (req.flight_no, req.date))
                    crew_rows = cur.fetchall()
            
            # Analyze each crew member
            crew_members = []
            for crew_id, role, name, max_hours in crew_rows:
                legality = check_crew_legality(crew_id, req.flight_no, req.date)
                duty_info = legality["duty_info"]
                qualifications = get_crew_qualifications(crew_id)
                
                crew_members.append({
                    "crew_id": crew_id,
                    "name": name or "Unknown",
                    "role": role,
                    "qualifications": qualifications,
                    "duty_hours": duty_info["duty_hours"],
                    "max_duty_hours": duty_info["max_duty_hours"],
                    "rest_required": duty_info["rest_required"],
                    "is_legal": legality["is_legal"],
                    "violations": legality["violations"]
                })
            
            # Generate analysis
            crew_data = {
                "flight_no": req.flight_no,
                "date": req.date,
                "crew_members": crew_members,
                "disruption_type": req.disruption_type
            }
            
            analysis = generate_llm_crew_analysis(crew_data, req.disruption_type or "Normal operations")
            
            # Generate optimization recommendations
            recommendations = []
            if analysis["risk_level"] == "high":
                recommendations.append("Replace crew members with legality violations")
            if analysis["risk_level"] == "medium":
                recommendations.append("Monitor duty hours and consider early relief")
            
            # Add specific crew recommendations
            for crew in crew_members:
                if not crew["is_legal"]:
                    replacements = find_replacement_crew(
                        crew["crew_id"], req.flight_no, req.date, 
                        crew["role"], crew["qualifications"]
                    )
                    if replacements:
                        recommendations.append(f"Replace {crew['crew_id']} with {replacements[0].crew_id}")
            
            service.log_request(request, {"status": "success", "crew_count": len(crew_members)})
            return {
                "flight_no": req.flight_no,
                "date": req.date,
                "crew_analysis": analysis,
                "crew_members": crew_members,
                "recommendations": recommendations,
                "optimization_status": "Complete" if analysis["risk_level"] != "high" else "Requires action"
            }
            
        except Exception as e:
            service.log_error(e, "optimize_crew endpoint")
            raise

@app.post("/suggest_crew_swap")
def suggest_crew_swap(req: CrewSwapRequest, request: Request):
    """Suggest crew replacement for unavailable crew member"""
    with LATENCY.labels("crew-svc", "/suggest_crew_swap", "POST").time():
        try:
            # Get unavailable crew details
            with db_pool.connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        SELECT cr.crew_role, cd.crew_name, cd.max_duty_hours
                        FROM crew_roster cr
                        LEFT JOIN crew_details cd ON cr.crew_id = cd.crew_id
                        WHERE cr.crew_id = %s AND cr.flight_no = %s AND cr.flight_date = %s
                    """, (req.unavailable_crew_id, req.flight_no, req.date))
                    result = cur.fetchone()
                    
                    if not result:
                        raise HTTPException(status_code=404, detail="Crew member not found on this flight")
                    
                    role, name, max_hours = result
            
            # Find replacement crew
            qualifications = get_crew_qualifications(req.unavailable_crew_id)
            replacements = find_replacement_crew(
                req.unavailable_crew_id, req.flight_no, req.date, role, qualifications
            )
            
            if not replacements:
                return {
                    "status": "No suitable replacements found",
                    "reason": "No available crew with required qualifications and legal status",
                    "recommendations": ["Consider delaying flight", "Check standby crew", "Contact crew scheduling"]
                }
            
            # Create crew swap suggestions
            swaps = []
            for replacement in replacements[:3]:  # Top 3 options
                # Calculate cost impact (mock)
                cost_impact = 0.0
                if replacement.duty_hours > 6:
                    cost_impact += 50  # Overtime
                if replacement.current_location != "AKL":
                    cost_impact += 100  # Relocation
                
                # Check legality
                legality = check_crew_legality(replacement.crew_id, req.flight_no, req.date)
                
                swaps.append(CrewSwap(
                    original_crew=CrewMember(
                        crew_id=req.unavailable_crew_id,
                        name=name or "Unknown",
                        role=role,
                        qualifications=qualifications,
                        current_location="AKL",
                        duty_hours=0,
                        max_duty_hours=max_hours or 8,
                        rest_required=0,
                        availability_status="Unavailable",
                        last_flight=req.flight_no
                    ),
                    replacement_crew=replacement,
                    swap_reason=req.reason,
                    legality_check=legality["is_legal"],
                    cost_impact=cost_impact,
                    implementation_time="30-60 minutes"
                ))
            
            service.log_request(request, {"status": "success", "replacements_found": len(swaps)})
            return {
                "flight_no": req.flight_no,
                "date": req.date,
                "unavailable_crew": req.unavailable_crew_id,
                "swap_suggestions": [swap.dict() for swap in swaps],
                "recommended_swap": swaps[0].dict() if swaps else None
            }
            
        except Exception as e:
            service.log_error(e, "suggest_crew_swap endpoint")
            raise

@app.get("/crew_legality/{crew_id}")
def check_crew_legality_endpoint(crew_id: str, flight_no: str, date: str, request: Request):
    """Check legality of a specific crew member for a flight"""
    with LATENCY.labels("crew-svc", "/crew_legality", "GET").time():
        try:
            legality = check_crew_legality(crew_id, flight_no, date)
            duty_info = calculate_duty_hours(crew_id, date)
            
            service.log_request(request, {"status": "success", "crew_id": crew_id})
            return {
                "crew_id": crew_id,
                "flight_no": flight_no,
                "date": date,
                "legality_check": legality,
                "duty_hours": duty_info
            }
            
        except Exception as e:
            service.log_error(e, "crew_legality endpoint")
            raise

@app.get("/crew_availability")
def get_crew_availability(date: str, role: Optional[str] = None, request: Request = None):
    """Get available crew members for a specific date and role"""
    with LATENCY.labels("crew-svc", "/crew_availability", "GET").time():
        try:
            with db_pool.connection() as conn:
                with conn.cursor() as cur:
                    if role:
                        cur.execute("""
                            SELECT cd.crew_id, cd.crew_name, cr.crew_role, cd.max_duty_hours
                            FROM crew_details cd
                            JOIN crew_roster cr ON cd.crew_id = cr.crew_id
                            WHERE cr.crew_role = %s
                            ORDER BY cd.crew_name
                        """, (role,))
                    else:
                        cur.execute("""
                            SELECT cd.crew_id, cd.crew_name, cr.crew_role, cd.max_duty_hours
                            FROM crew_details cd
                            JOIN crew_roster cr ON cd.crew_id = cr.crew_id
                            ORDER BY cd.crew_name
                        """)
                    
                    crew_rows = cur.fetchall()
            
            available_crew = []
            for crew_id, name, role, max_hours in crew_rows:
                duty_info = calculate_duty_hours(crew_id, date)
                qualifications = get_crew_qualifications(crew_id)
                
                # Check if available (simplified)
                is_available = duty_info["duty_hours"] < max_hours * 0.9
                
                available_crew.append({
                    "crew_id": crew_id,
                    "name": name or "Unknown",
                    "role": role,
                    "qualifications": qualifications,
                    "duty_hours": duty_info["duty_hours"],
                    "max_duty_hours": max_hours,
                    "is_available": is_available,
                    "rest_required": duty_info["rest_required"]
                })
            
            service.log_request(request, {"status": "success", "crew_count": len(available_crew)})
            return {
                "date": date,
                "role_filter": role,
                "available_crew": available_crew,
                "total_available": len([c for c in available_crew if c["is_available"]])
            }
            
        except Exception as e:
            service.log_error(e, "crew_availability endpoint")
            raise

@app.get("/health")
def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "crew-svc"}

if __name__ == "__main__":
    log_startup("crew-svc")
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8086)
