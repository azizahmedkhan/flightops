import json
import random
from contextlib import asynccontextmanager
from datetime import datetime, date, timedelta
from typing import List, Dict, Any, Optional

import psycopg
from fastapi import HTTPException, Request
from pydantic import BaseModel
from psycopg_pool import ConnectionPool

from services.shared.base_service import BaseService, LATENCY, log_startup
from services.shared.prompt_manager import PromptManager
from services.shared.llm_client import create_llm_client

# Initialize base service
service = BaseService("predictive-svc", "1.0.0")
app = service.get_app()

# Get environment variables
DB_HOST = service.get_env_var("DB_HOST", "localhost")
DB_PORT = service.get_env_int("DB_PORT", 5432)
DB_NAME = service.get_env_var("DB_NAME", "flightops")
DB_USER = service.get_env_var("DB_USER", "postgres")
DB_PASS = service.get_env_var("DB_PASS", "postgres")

# Initialize LLM client
llm_client = create_llm_client("predictive-svc")

# Create database connection pool
DB_CONN_STRING = f"host={DB_HOST} port={DB_PORT} dbname={DB_NAME} user={DB_USER} password={DB_PASS}"
db_pool = None

class PredictionRequest(BaseModel):
    flight_no: Optional[str] = None
    date: Optional[str] = None
    hours_ahead: int = 4
    include_weather: bool = True
    include_crew: bool = True
    include_aircraft: bool = True

class DisruptionPrediction(BaseModel):
    flight_no: str
    date: str
    risk_level: str  # low, medium, high, critical
    risk_score: float  # 0.0 to 1.0
    predicted_disruption_type: str
    confidence: float
    factors: List[str]
    recommendations: List[str]
    time_to_disruption: Optional[str] = None

@asynccontextmanager
async def lifespan(app):
    global db_pool
    log_startup("predictive-svc")
    
    # Initialize connection pool
    db_pool = ConnectionPool(DB_CONN_STRING, min_size=2, max_size=10)
    
    yield
    
    # Close connection pool on shutdown
    if db_pool:
        db_pool.close()

# Set lifespan for the app
app.router.lifespan_context = lifespan


def _parse_date(value: Optional[str]) -> Optional[date]:
    if value in (None, ""):
        return None

    if isinstance(value, date):
        return value

    value = value.strip()
    for fmt in ("%Y-%m-%d", "%Y/%m/%d"):
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue

    try:
        return datetime.fromisoformat(value).date()
    except ValueError as exc:
        raise ValueError(f"Invalid date value: {value}") from exc


def get_weather_data(airport: str, date: str) -> Dict[str, Any]:
    """Mock weather data - in production, integrate with weather API"""
    # Simulate weather patterns that could cause delays
    weather_conditions = {
        "AKL": {"wind_speed": 25, "visibility": 8, "precipitation": 0.1, "conditions": "windy"},
        "WLG": {"wind_speed": 35, "visibility": 6, "precipitation": 0.3, "conditions": "stormy"},
        "CHC": {"wind_speed": 15, "visibility": 10, "precipitation": 0.0, "conditions": "clear"},
        "SYD": {"wind_speed": 20, "visibility": 9, "precipitation": 0.1, "conditions": "windy"},
        "LAX": {"wind_speed": 18, "visibility": 7, "precipitation": 0.2, "conditions": "cloudy"}
    }
    
    base_weather = weather_conditions.get(airport, {"wind_speed": 15, "visibility": 10, "precipitation": 0.0, "conditions": "clear"})
    
    # Add some randomness to simulate changing conditions
    base_weather["wind_speed"] += random.randint(-5, 10)
    base_weather["visibility"] += random.randint(-2, 2)
    base_weather["precipitation"] += random.uniform(-0.1, 0.2)
    
    return base_weather

def analyze_crew_fatigue(crew_details: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Analyze crew fatigue and duty time constraints"""
    total_crew = len(crew_details)
    at_risk_crew = 0
    factors = []
    
    for crew in crew_details:
        duty_hours = crew.get("duty_hours", 0)
        max_hours = crew.get("max_duty_hours", 8)
        
        if duty_hours >= max_hours * 0.9:  # 90% of max duty time
            at_risk_crew += 1
            factors.append(f"Crew {crew.get('crew_id', 'Unknown')} approaching duty limit")
    
    risk_level = "low"
    if at_risk_crew > total_crew * 0.5:
        risk_level = "high"
    elif at_risk_crew > total_crew * 0.3:
        risk_level = "medium"
    
    return {
        "total_crew": total_crew,
        "at_risk_crew": at_risk_crew,
        "risk_level": risk_level,
        "factors": factors
    }

def analyze_aircraft_status(tail_number: str) -> Dict[str, Any]:
    """Analyze aircraft maintenance and availability"""
    with db_pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT status, current_location
                FROM aircraft_status
                WHERE tail_number = %s
            """, (tail_number,))
            result = cur.fetchone()
            
            if not result:
                return {"status": "unknown", "risk_level": "medium", "factors": ["Aircraft status unknown"]}
            
            status, location = result
            factors = []
            risk_level = "low"
            
            if status == "Maintenance":
                risk_level = "high"
                factors.append("Aircraft currently in maintenance")
            elif status == "Delayed":
                risk_level = "medium"
                factors.append("Aircraft already delayed")
            
            return {
                "status": status,
                "location": location,
                "risk_level": risk_level,
                "factors": factors
            }

def get_historical_patterns(flight_no: str, days_back: int = 30) -> Dict[str, Any]:
    """Analyze historical delay patterns for a flight"""
    with db_pool.connection() as conn:
        with conn.cursor() as cur:
            # Get historical data (mock - in production, use actual historical data)
            cur.execute("""
                SELECT status, COUNT(*) as count
                FROM flights
                WHERE flight_no = %s
                GROUP BY status
            """, (flight_no,))
            results = cur.fetchall()
            
            total_flights = sum(row[1] for row in results)
            delay_count = sum(row[1] for row in results if row[0] in ["Delayed", "Cancelled"])
            
            delay_rate = delay_count / total_flights if total_flights > 0 else 0.1
            
            return {
                "total_flights": total_flights,
                "delay_count": delay_count,
                "delay_rate": delay_rate,
                "patterns": ["Peak delay times: 6-8 AM, 2-4 PM"] if delay_rate > 0.2 else []
            }

def generate_llm_insights(flight_data: Dict[str, Any], weather_data: Dict[str, Any], 
                         crew_analysis: Dict[str, Any], aircraft_analysis: Dict[str, Any],
                         historical_data: Dict[str, Any]) -> Dict[str, Any]:
    """Use LLM to generate insights and recommendations"""
    
    try:
        prompt = PromptManager.get_disruption_prediction_prompt(
            flight_data, weather_data, crew_analysis, aircraft_analysis, historical_data
        )
        
        result = llm_client.json_completion(
            prompt=prompt,
            temperature=0.3,
            function_name="generate_llm_insights",
            metadata={
                "flight_no": flight_data.get("flight_no"),
                "date": flight_data.get("date")
            },
            fallback_value=generate_rule_based_insights(flight_data, weather_data, crew_analysis, aircraft_analysis, historical_data)
        )
        
        return result
            
    except Exception as e:
        service.log_error(e, "LLM insights generation")
        return generate_rule_based_insights(flight_data, weather_data, crew_analysis, aircraft_analysis, historical_data)

def generate_rule_based_insights(flight_data: Dict[str, Any], weather_data: Dict[str, Any],
                                crew_analysis: Dict[str, Any], aircraft_analysis: Dict[str, Any],
                                historical_data: Dict[str, Any]) -> Dict[str, Any]:
    """Fallback rule-based analysis when LLM is not available"""
    risk_factors = []
    risk_score = 0.0
    
    # Weather analysis
    if weather_data.get("wind_speed", 0) > 30:
        risk_factors.append("High wind conditions")
        risk_score += 0.3
    if weather_data.get("visibility", 10) < 5:
        risk_factors.append("Low visibility")
        risk_score += 0.2
    if weather_data.get("precipitation", 0) > 0.5:
        risk_factors.append("Heavy precipitation")
        risk_score += 0.2
    
    # Crew analysis
    if crew_analysis.get("risk_level") == "high":
        risk_factors.append("Crew fatigue concerns")
        risk_score += 0.3
    elif crew_analysis.get("risk_level") == "medium":
        risk_factors.append("Crew approaching duty limits")
        risk_score += 0.1
    
    # Aircraft analysis
    if aircraft_analysis.get("risk_level") == "high":
        risk_factors.append("Aircraft maintenance issues")
        risk_score += 0.4
    elif aircraft_analysis.get("risk_level") == "medium":
        risk_factors.append("Aircraft operational concerns")
        risk_score += 0.2
    
    # Historical analysis
    if historical_data.get("delay_rate", 0) > 0.3:
        risk_factors.append("High historical delay rate")
        risk_score += 0.2
    
    # Determine risk level
    if risk_score >= 0.7:
        risk_level = "critical"
    elif risk_score >= 0.5:
        risk_level = "high"
    elif risk_score >= 0.3:
        risk_level = "medium"
    else:
        risk_level = "low"
    
    # Generate recommendations
    recommendations = []
    if "High wind conditions" in risk_factors:
        recommendations.append("Consider earlier departure or delay")
    if "Crew fatigue concerns" in risk_factors:
        recommendations.append("Arrange crew replacement")
    if "Aircraft maintenance issues" in risk_factors:
        recommendations.append("Check aircraft availability and arrange backup")
    if "Low visibility" in risk_factors:
        recommendations.append("Monitor weather conditions closely")
    
    return {
        "risk_level": risk_level,
        "risk_score": min(risk_score, 1.0),
        "predicted_disruption_type": "Weather delay" if "weather" in str(risk_factors).lower() else "Operational delay",
        "confidence": 0.7 if risk_score > 0.5 else 0.5,
        "factors": risk_factors,
        "recommendations": recommendations
    }

@app.post("/predict_disruptions")
def predict_disruptions(req: PredictionRequest, request: Request):
    """Predict potential disruptions for flights"""
    with LATENCY.labels("predictive-svc", "/predict_disruptions", "POST").time():
        try:
            flight_no = req.flight_no
            date = req.date
            flight_dt = _parse_date(date) if date else None

            if not flight_no or not flight_dt:
                raise HTTPException(status_code=400, detail="flight_no and date are required")
            
            # Get flight data
            with db_pool.connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        SELECT flight_no, origin, destination, sched_dep_time, sched_arr_time, status, tail_number
                        FROM flights
                        WHERE flight_no = %s AND flight_date = %s
                    """, (flight_no, flight_dt))
                    flight_row = cur.fetchone()
                    
                    if not flight_row:
                        raise HTTPException(status_code=404, detail="Flight not found")
                    
                    flight_data = {
                        "flight_no": flight_row[0],
                        "origin": flight_row[1],
                        "destination": flight_row[2],
                        "sched_dep_time": flight_row[3],
                        "sched_arr_time": flight_row[4],
                        "status": flight_row[5],
                        "tail_number": flight_row[6],
                        "date": flight_dt.isoformat()
                    }

            # Gather analysis data
            weather_data = get_weather_data(flight_data["origin"], flight_data["date"]) if req.include_weather else {}
            
            crew_analysis = {"risk_level": "low", "factors": [], "total_crew": 0, "at_risk_crew": 0}
            if req.include_crew:
                # Get crew details
                with db_pool.connection() as conn:
                    with conn.cursor() as cur:
                        cur.execute("""
                            SELECT cr.crew_id, cr.crew_role, cd.crew_name, cd.duty_start_time, cd.max_duty_hours
                            FROM crew_roster cr
                            LEFT JOIN crew_details cd ON cr.crew_id = cd.crew_id
                            WHERE cr.flight_no = %s AND cr.flight_date = %s
                        """, (flight_no, flight_dt))
                        crew_details = []
                        for row in cur.fetchall():
                            crew_details.append({
                                "crew_id": row[0],
                                "role": row[1],
                                "name": row[2] or "Unknown",
                                "duty_start": row[3] or "Unknown",
                                "max_duty_hours": row[4] or 8,
                                "duty_hours": 6  # Mock current duty hours
                            })
                        crew_analysis = analyze_crew_fatigue(crew_details)
            
            aircraft_analysis = {"status": "ready", "risk_level": "low", "factors": []}
            if req.include_aircraft and flight_data.get("tail_number"):
                aircraft_analysis = analyze_aircraft_status(flight_data["tail_number"])
            
            historical_data = get_historical_patterns(flight_no)
            
            # Generate insights using LLM or rule-based analysis
            insights = generate_llm_insights(flight_data, weather_data, crew_analysis, aircraft_analysis, historical_data)
            
            # Create prediction response
            prediction = DisruptionPrediction(
                flight_no=flight_no,
                date=flight_dt.isoformat(),
                risk_level=insights.get("risk_level", "low"),
                risk_score=insights.get("risk_score", 0.0),
                predicted_disruption_type=insights.get("predicted_disruption_type", "No disruption expected"),
                confidence=insights.get("confidence", 0.5),
                factors=insights.get("factors", []),
                recommendations=insights.get("recommendations", []),
                time_to_disruption=f"{req.hours_ahead} hours" if insights.get("risk_score", 0) > 0.5 else None
            )
            
            service.log_request(request, {"status": "success", "risk_level": prediction.risk_level})
            return {"prediction": prediction, "analysis_data": {
                "weather": weather_data,
                "crew": crew_analysis,
                "aircraft": aircraft_analysis,
                "historical": historical_data
            }}
            
        except Exception as e:
            service.log_error(e, "predict_disruptions endpoint")
            raise

@app.post("/bulk_predict")
def bulk_predict_disruptions(request: Request):
    """Predict disruptions for all flights in the next 24 hours"""
    with LATENCY.labels("predictive-svc", "/bulk_predict", "POST").time():
        try:
            tomorrow_date = (datetime.now() + timedelta(days=1)).date()

            # Get all flights for tomorrow
            with db_pool.connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        SELECT flight_no, origin, destination, sched_dep_time, status, tail_number
                        FROM flights
                        WHERE flight_date = %s
                        ORDER BY sched_dep_time
                    """, (tomorrow_date,))
                    flights = cur.fetchall()

            predictions = []
            for flight in flights:
                flight_no, origin, destination, sched_dep_time, status, tail_number = flight
                
                # Quick risk assessment for bulk prediction
                risk_score = 0.0
                factors = []
                
                # Check if already delayed
                if status in ["Delayed", "Cancelled"]:
                    risk_score = 0.8
                    factors.append("Already disrupted")
                
                # Check weather at origin
                weather = get_weather_data(origin, tomorrow_date.isoformat())
                if weather.get("wind_speed", 0) > 25:
                    risk_score += 0.3
                    factors.append("High wind at origin")
                
                # Determine risk level
                if risk_score >= 0.7:
                    risk_level = "high"
                elif risk_score >= 0.4:
                    risk_level = "medium"
                else:
                    risk_level = "low"
                
                predictions.append({
                    "flight_no": flight_no,
                    "route": f"{origin} → {destination}",
                    "departure_time": sched_dep_time,
                    "risk_level": risk_level,
                    "risk_score": min(risk_score, 1.0),
                    "factors": factors
                })
            
            # Sort by risk score
            predictions.sort(key=lambda x: x["risk_score"], reverse=True)
            
            service.log_request(request, {"status": "success", "predictions_count": len(predictions)})
            return {"predictions": predictions, "date": tomorrow_date.isoformat()}
            
        except Exception as e:
            service.log_error(e, "bulk_predict endpoint")
            raise

@app.get("/health")
def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "predictive-svc"}

if __name__ == "__main__":
    log_startup("predictive-svc")
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8085)
