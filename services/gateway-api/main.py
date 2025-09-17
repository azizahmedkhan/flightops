import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'shared'))

from base_service import BaseService
from fastapi import Request, HTTPException
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from psycopg.errors import UndefinedTable
import httpx
import psycopg
import json

# Initialize base service
service = BaseService("gateway-api", "1.0.0")
app = service.get_app()

# Get environment variables using the base service
AGENT_URL = service.get_env_var("AGENT_URL", "http://agent-svc:8082")
RETRIEVAL_URL = service.get_env_var("RETRIEVAL_URL", "http://retrieval-svc:8081")
COMMS_URL = service.get_env_var("COMMS_URL", "http://comms-svc:8083")
INGEST_URL = service.get_env_var("INGEST_URL", "http://ingest-svc:8084")
CUSTOMER_CHAT_URL = service.get_env_var("CUSTOMER_CHAT_URL", "http://customer-chat-svc:8085")
PREDICTIVE_URL = service.get_env_var("PREDICTIVE_URL", "http://predictive-svc:8085")
CREW_URL = service.get_env_var("CREW_URL", "http://crew-svc:8086")

# Database configuration
DB_HOST = service.get_env_var("DB_HOST", "db")
DB_PORT = service.get_env_int("DB_PORT", 5432)
DB_NAME = service.get_env_var("DB_NAME", "flightops")
DB_USER = service.get_env_var("DB_USER", "postgres")
DB_PASS = service.get_env_var("DB_PASS", "postgres")

# Embedding configuration
OPENAI_API_KEY = service.get_env_var("OPENAI_API_KEY", "")
EMBEDDINGS_MODEL = service.get_env_var("EMBEDDINGS_MODEL", "text-embedding-3-small")

def embed(text: str) -> List[float]:
    """Generate embeddings if API key is available, otherwise return deterministic fake vectors."""
    if OPENAI_API_KEY:
        try:
            from openai import OpenAI
            client = OpenAI(api_key=OPENAI_API_KEY)
            resp = client.embeddings.create(input=[text], model=EMBEDDINGS_MODEL)
            return resp.data[0].embedding
        except Exception as e:
            service.log_error(e, "embedding generation")
            # Fall through to fake vectors
    # fallback: deterministic fake vector
    import random, hashlib
    random.seed(int(hashlib.md5(text.encode()).hexdigest(), 16))
    return [random.random() for _ in range(1536)]

# Pydantic models for data operations
class Flight(BaseModel):
    flight_no: str
    flight_date: str
    origin: str
    destination: str
    sched_dep_time: str
    sched_arr_time: str
    status: str
    tail_number: str

class Booking(BaseModel):
    flight_no: str
    flight_date: str
    pnr: str
    passenger_name: str
    has_connection: str
    connecting_flight_no: str

class CrewRoster(BaseModel):
    flight_no: str
    flight_date: str
    crew_id: str
    crew_role: str

class CrewDetail(BaseModel):
    crew_id: str
    crew_name: str
    duty_start_time: str
    max_duty_hours: int

class AircraftStatus(BaseModel):
    tail_number: str
    current_location: str
    status: str

class Policy(BaseModel):
    id: Optional[int] = None
    title: str
    content: str
    meta: Dict[str, Any]
    embedding: Optional[List[float]] = None

# Database helper functions
def get_db_connection():
    return psycopg.connect(
        host=DB_HOST, 
        port=DB_PORT, 
        dbname=DB_NAME, 
        user=DB_USER, 
        password=DB_PASS, 
        autocommit=True
    )

def _execute_with_recovery(operation):
    try:
        return operation()
    except UndefinedTable:
        ensure_tables_exist()
        return operation()


def execute_query(query: str, params: tuple = None) -> List[Dict[str, Any]]:
    def run():
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, params)
                if cur.description:
                    columns = [desc[0] for desc in cur.description]
                    return [dict(zip(columns, row)) for row in cur.fetchall()]
                return []

    return _execute_with_recovery(run)


def execute_insert(query: str, params: tuple) -> int:
    def run():
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, params)
                return cur.rowcount

    return _execute_with_recovery(run)


def execute_update(query: str, params: tuple) -> int:
    def run():
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, params)
                return cur.rowcount

    return _execute_with_recovery(run)


def execute_delete(query: str, params: tuple) -> int:
    def run():
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, params)
                return cur.rowcount

    return _execute_with_recovery(run)


def ensure_tables_exist() -> None:
    """Ensure core data tables exist so read endpoints do not 500 on fresh databases."""
    create_statements = [
        """
        CREATE TABLE IF NOT EXISTS flights (
            flight_no TEXT,
            flight_date TEXT,
            origin TEXT,
            destination TEXT,
            sched_dep_time TEXT,
            sched_arr_time TEXT,
            status TEXT,
            tail_number TEXT
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS bookings (
            flight_no TEXT,
            flight_date TEXT,
            pnr TEXT,
            passenger_name TEXT,
            has_connection TEXT,
            connecting_flight_no TEXT
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS crew_roster (
            flight_no TEXT,
            flight_date TEXT,
            crew_id TEXT,
            crew_role TEXT
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS crew_details (
            crew_id TEXT PRIMARY KEY,
            crew_name TEXT,
            duty_start_time TEXT,
            max_duty_hours INTEGER
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS aircraft_status (
            tail_number TEXT PRIMARY KEY,
            current_location TEXT,
            status TEXT
        )
        """,
        "CREATE EXTENSION IF NOT EXISTS vector",
        """
        CREATE TABLE IF NOT EXISTS docs (
            id SERIAL PRIMARY KEY,
            title TEXT,
            content TEXT,
            meta JSONB
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS doc_embeddings (
            doc_id INT PRIMARY KEY REFERENCES docs(id) ON DELETE CASCADE,
            embedding vector(1536)
        )
        """,
    ]

    with get_db_connection() as conn:
        with conn.cursor() as cur:
            for statement in create_statements:
                cur.execute(statement)


# Prime the database schema when the service starts.
try:
    ensure_tables_exist()
except Exception as init_error:
    service.logger.warning(f"Failed to initialize database tables at startup: {init_error}")

# Override the root endpoint to redirect to docs
@app.get("/")
def root():
    return RedirectResponse("/docs")

@app.get("/demo/seed")
async def seed(request: Request):
    try:
        async with httpx.AsyncClient() as client:
            r = await client.post(f"{INGEST_URL}/ingest/seed", timeout=90.0)
            result = r.json()
            service.log_request(request, {"status": "success"})
            return result
    except Exception as e:
        service.log_error(e, "seed endpoint")
        raise

@app.post("/ask")
async def ask(payload: dict, request: Request):
    try:
        async with httpx.AsyncClient() as client:
            r = await client.post(f"{AGENT_URL}/ask", json=payload, timeout=60.0)
            result = r.json()
            service.log_request(request, {"status": "success"})
            return result
    except Exception as e:
        service.log_error(e, "ask endpoint")
        raise

@app.post("/draft_comms")
async def draft_comms(payload: dict, request: Request):
    try:
        async with httpx.AsyncClient() as client:
            r = await client.post(f"{AGENT_URL}/draft_comms", json=payload, timeout=60.0)
            result = r.json()
            service.log_request(request, {"status": "success"})
            return result
    except Exception as e:
        service.log_error(e, "draft_comms endpoint")
        raise

@app.post("/search")
async def search(payload: dict, request: Request):
    try:
        async with httpx.AsyncClient() as client:
            r = await client.post(f"{RETRIEVAL_URL}/search", json=payload, timeout=30.0)
            result = r.json()
            service.log_request(request, {"status": "success"})
            return result
    except Exception as e:
        service.log_error(e, "search endpoint")
        raise

# Customer Chat Service Proxies
@app.post("/customer-chat/session")
async def create_chat_session(payload: dict, request: Request):
    try:
        service.logger.info(f"Creating chat session with payload: {payload}")
        async with httpx.AsyncClient() as client:
            r = await client.post(f"{CUSTOMER_CHAT_URL}/chat/session", json=payload, timeout=30.0)
            service.logger.info(f"Customer chat service response: {r.status_code}")
            if r.status_code != 200:
                service.logger.error(f"Customer chat service error: {r.text}")
                raise HTTPException(status_code=r.status_code, detail=f"Customer chat service error: {r.text}")
            result = r.json()
            service.log_request(request, {"status": "success"})
            return result
    except HTTPException:
        raise
    except Exception as e:
        service.log_error(e, "create_chat_session endpoint")
        raise HTTPException(status_code=500, detail=f"Failed to create chat session: {str(e)}")

@app.post("/customer-chat/message")
async def send_chat_message(payload: dict, request: Request):
    try:
        async with httpx.AsyncClient() as client:
            r = await client.post(f"{CUSTOMER_CHAT_URL}/chat/message", json=payload, timeout=30.0)
            result = r.json()
            service.log_request(request, {"status": "success"})
            return result
    except Exception as e:
        service.log_error(e, "send_chat_message endpoint")
        raise

@app.get("/customer-chat/session/{session_id}")
async def get_chat_session(session_id: str, request: Request):
    try:
        async with httpx.AsyncClient() as client:
            r = await client.get(f"{CUSTOMER_CHAT_URL}/chat/session/{session_id}", timeout=30.0)
            result = r.json()
            service.log_request(request, {"status": "success"})
            return result
    except Exception as e:
        service.log_error(e, "get_chat_session endpoint")
        raise

@app.post("/customer-chat/communication/send")
async def send_communication(payload: dict, request: Request):
    try:
        async with httpx.AsyncClient() as client:
            r = await client.post(f"{CUSTOMER_CHAT_URL}/communication/send", json=payload, timeout=30.0)
            result = r.json()
            service.log_request(request, {"status": "success"})
            return result
    except Exception as e:
        service.log_error(e, "send_communication endpoint")
        raise

@app.get("/customer-chat/communication/history")
async def get_communication_history(request: Request):
    try:
        async with httpx.AsyncClient() as client:
            r = await client.get(f"{CUSTOMER_CHAT_URL}/communication/history", timeout=30.0)
            result = r.json()
            service.log_request(request, {"status": "success"})
            return result
    except Exception as e:
        service.log_error(e, "get_communication_history endpoint")
        raise

@app.get("/customer-chat/test")
async def test_customer_chat(request: Request):
    try:
        async with httpx.AsyncClient() as client:
            r = await client.get(f"{CUSTOMER_CHAT_URL}/test", timeout=30.0)
            result = r.json()
            service.log_request(request, {"status": "success"})
            return result
    except Exception as e:
        service.log_error(e, "test_customer_chat endpoint")
        raise HTTPException(status_code=500, detail=f"Customer chat service not available: {str(e)}")

# Data Management Endpoints

# Flights CRUD
@app.get("/data/flights")
async def get_flights(request: Request):
    try:
        flights = execute_query("SELECT * FROM flights ORDER BY flight_date, flight_no")
        service.log_request(request, {"status": "success", "count": len(flights)})
        return flights
    except Exception as e:
        service.log_error(e, "get_flights endpoint")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/data/flights")
async def create_flight(flight: Flight, request: Request):
    try:
        query = """
            INSERT INTO flights (flight_no, flight_date, origin, destination, sched_dep_time, sched_arr_time, status, tail_number)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """
        params = (flight.flight_no, flight.flight_date, flight.origin, flight.destination, 
                 flight.sched_dep_time, flight.sched_arr_time, flight.status, flight.tail_number)
        execute_insert(query, params)
        service.log_request(request, {"status": "success"})
        return {"message": "Flight created successfully"}
    except Exception as e:
        service.log_error(e, "create_flight endpoint")
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/data/flights/{flight_no}")
async def update_flight(flight_no: str, flight: Flight, request: Request):
    try:
        query = """
            UPDATE flights SET flight_date=%s, origin=%s, destination=%s, sched_dep_time=%s, 
                   sched_arr_time=%s, status=%s, tail_number=%s WHERE flight_no=%s
        """
        params = (flight.flight_date, flight.origin, flight.destination, flight.sched_dep_time,
                 flight.sched_arr_time, flight.status, flight.tail_number, flight_no)
        rows_affected = execute_update(query, params)
        if rows_affected == 0:
            raise HTTPException(status_code=404, detail="Flight not found")
        service.log_request(request, {"status": "success"})
        return {"message": "Flight updated successfully"}
    except HTTPException:
        raise
    except Exception as e:
        service.log_error(e, "update_flight endpoint")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/data/flights/{flight_no}")
async def delete_flight(flight_no: str, request: Request):
    try:
        query = "DELETE FROM flights WHERE flight_no=%s"
        rows_affected = execute_delete(query, (flight_no,))
        if rows_affected == 0:
            raise HTTPException(status_code=404, detail="Flight not found")
        service.log_request(request, {"status": "success"})
        return {"message": "Flight deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        service.log_error(e, "delete_flight endpoint")
        raise HTTPException(status_code=500, detail=str(e))

# Bookings CRUD
@app.get("/data/bookings")
async def get_bookings(request: Request):
    try:
        bookings = execute_query("SELECT * FROM bookings ORDER BY flight_date, flight_no")
        service.log_request(request, {"status": "success", "count": len(bookings)})
        return bookings
    except Exception as e:
        service.log_error(e, "get_bookings endpoint")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/data/bookings")
async def create_booking(booking: Booking, request: Request):
    try:
        query = """
            INSERT INTO bookings (flight_no, flight_date, pnr, passenger_name, has_connection, connecting_flight_no)
            VALUES (%s, %s, %s, %s, %s, %s)
        """
        params = (booking.flight_no, booking.flight_date, booking.pnr, booking.passenger_name,
                 booking.has_connection, booking.connecting_flight_no)
        execute_insert(query, params)
        service.log_request(request, {"status": "success"})
        return {"message": "Booking created successfully"}
    except Exception as e:
        service.log_error(e, "create_booking endpoint")
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/data/bookings/{pnr}")
async def update_booking(pnr: str, booking: Booking, request: Request):
    try:
        query = """
            UPDATE bookings SET flight_no=%s, flight_date=%s, passenger_name=%s, 
                   has_connection=%s, connecting_flight_no=%s WHERE pnr=%s
        """
        params = (booking.flight_no, booking.flight_date, booking.passenger_name,
                 booking.has_connection, booking.connecting_flight_no, pnr)
        rows_affected = execute_update(query, params)
        if rows_affected == 0:
            raise HTTPException(status_code=404, detail="Booking not found")
        service.log_request(request, {"status": "success"})
        return {"message": "Booking updated successfully"}
    except HTTPException:
        raise
    except Exception as e:
        service.log_error(e, "update_booking endpoint")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/data/bookings/{pnr}")
async def delete_booking(pnr: str, request: Request):
    try:
        query = "DELETE FROM bookings WHERE pnr=%s"
        rows_affected = execute_delete(query, (pnr,))
        if rows_affected == 0:
            raise HTTPException(status_code=404, detail="Booking not found")
        service.log_request(request, {"status": "success"})
        return {"message": "Booking deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        service.log_error(e, "delete_booking endpoint")
        raise HTTPException(status_code=500, detail=str(e))

# Crew Roster CRUD
@app.get("/data/crew_roster")
async def get_crew_roster(request: Request):
    try:
        roster = execute_query("SELECT * FROM crew_roster ORDER BY flight_date, flight_no")
        service.log_request(request, {"status": "success", "count": len(roster)})
        return roster
    except Exception as e:
        service.log_error(e, "get_crew_roster endpoint")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/data/crew_roster")
async def create_crew_roster(roster: CrewRoster, request: Request):
    try:
        query = """
            INSERT INTO crew_roster (flight_no, flight_date, crew_id, crew_role)
            VALUES (%s, %s, %s, %s)
        """
        params = (roster.flight_no, roster.flight_date, roster.crew_id, roster.crew_role)
        execute_insert(query, params)
        service.log_request(request, {"status": "success"})
        return {"message": "Crew roster entry created successfully"}
    except Exception as e:
        service.log_error(e, "create_crew_roster endpoint")
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/data/crew_roster/{flight_no}/{crew_id}")
async def update_crew_roster(flight_no: str, crew_id: str, roster: CrewRoster, request: Request):
    try:
        query = """
            UPDATE crew_roster SET flight_date=%s, crew_role=%s WHERE flight_no=%s AND crew_id=%s
        """
        params = (roster.flight_date, roster.crew_role, flight_no, crew_id)
        rows_affected = execute_update(query, params)
        if rows_affected == 0:
            raise HTTPException(status_code=404, detail="Crew roster entry not found")
        service.log_request(request, {"status": "success"})
        return {"message": "Crew roster entry updated successfully"}
    except HTTPException:
        raise
    except Exception as e:
        service.log_error(e, "update_crew_roster endpoint")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/data/crew_roster/{flight_no}/{crew_id}")
async def delete_crew_roster(flight_no: str, crew_id: str, request: Request):
    try:
        query = "DELETE FROM crew_roster WHERE flight_no=%s AND crew_id=%s"
        rows_affected = execute_delete(query, (flight_no, crew_id))
        if rows_affected == 0:
            raise HTTPException(status_code=404, detail="Crew roster entry not found")
        service.log_request(request, {"status": "success"})
        return {"message": "Crew roster entry deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        service.log_error(e, "delete_crew_roster endpoint")
        raise HTTPException(status_code=500, detail=str(e))

# Crew Details CRUD
@app.get("/data/crew_details")
async def get_crew_details(request: Request):
    try:
        details = execute_query("SELECT * FROM crew_details ORDER BY crew_id")
        service.log_request(request, {"status": "success", "count": len(details)})
        return details
    except Exception as e:
        service.log_error(e, "get_crew_details endpoint")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/data/crew_details")
async def create_crew_detail(detail: CrewDetail, request: Request):
    try:
        query = """
            INSERT INTO crew_details (crew_id, crew_name, duty_start_time, max_duty_hours)
            VALUES (%s, %s, %s, %s)
        """
        params = (detail.crew_id, detail.crew_name, detail.duty_start_time, detail.max_duty_hours)
        execute_insert(query, params)
        service.log_request(request, {"status": "success"})
        return {"message": "Crew detail created successfully"}
    except Exception as e:
        service.log_error(e, "create_crew_detail endpoint")
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/data/crew_details/{crew_id}")
async def update_crew_detail(crew_id: str, detail: CrewDetail, request: Request):
    try:
        query = """
            UPDATE crew_details SET crew_name=%s, duty_start_time=%s, max_duty_hours=%s WHERE crew_id=%s
        """
        params = (detail.crew_name, detail.duty_start_time, detail.max_duty_hours, crew_id)
        rows_affected = execute_update(query, params)
        if rows_affected == 0:
            raise HTTPException(status_code=404, detail="Crew detail not found")
        service.log_request(request, {"status": "success"})
        return {"message": "Crew detail updated successfully"}
    except HTTPException:
        raise
    except Exception as e:
        service.log_error(e, "update_crew_detail endpoint")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/data/crew_details/{crew_id}")
async def delete_crew_detail(crew_id: str, request: Request):
    try:
        query = "DELETE FROM crew_details WHERE crew_id=%s"
        rows_affected = execute_delete(query, (crew_id,))
        if rows_affected == 0:
            raise HTTPException(status_code=404, detail="Crew detail not found")
        service.log_request(request, {"status": "success"})
        return {"message": "Crew detail deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        service.log_error(e, "delete_crew_detail endpoint")
        raise HTTPException(status_code=500, detail=str(e))

# Aircraft Status CRUD
@app.get("/data/aircraft_status")
async def get_aircraft_status(request: Request):
    try:
        status = execute_query("SELECT * FROM aircraft_status ORDER BY tail_number")
        service.log_request(request, {"status": "success", "count": len(status)})
        return status
    except Exception as e:
        service.log_error(e, "get_aircraft_status endpoint")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/data/aircraft_status")
async def create_aircraft_status(status: AircraftStatus, request: Request):
    try:
        query = """
            INSERT INTO aircraft_status (tail_number, current_location, status)
            VALUES (%s, %s, %s)
        """
        params = (status.tail_number, status.current_location, status.status)
        execute_insert(query, params)
        service.log_request(request, {"status": "success"})
        return {"message": "Aircraft status created successfully"}
    except Exception as e:
        service.log_error(e, "create_aircraft_status endpoint")
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/data/aircraft_status/{tail_number}")
async def update_aircraft_status(tail_number: str, status: AircraftStatus, request: Request):
    try:
        query = """
            UPDATE aircraft_status SET current_location=%s, status=%s WHERE tail_number=%s
        """
        params = (status.current_location, status.status, tail_number)
        rows_affected = execute_update(query, params)
        if rows_affected == 0:
            raise HTTPException(status_code=404, detail="Aircraft status not found")
        service.log_request(request, {"status": "success"})
        return {"message": "Aircraft status updated successfully"}
    except HTTPException:
        raise
    except Exception as e:
        service.log_error(e, "update_aircraft_status endpoint")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/data/aircraft_status/{tail_number}")
async def delete_aircraft_status(tail_number: str, request: Request):
    try:
        query = "DELETE FROM aircraft_status WHERE tail_number=%s"
        rows_affected = execute_delete(query, (tail_number,))
        if rows_affected == 0:
            raise HTTPException(status_code=404, detail="Aircraft status not found")
        service.log_request(request, {"status": "success"})
        return {"message": "Aircraft status deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        service.log_error(e, "delete_aircraft_status endpoint")
        raise HTTPException(status_code=500, detail=str(e))

# Policies CRUD
@app.get("/data/policies")
async def get_policies(request: Request):
    try:
        policies = execute_query("""
            SELECT d.id, d.title, d.content, d.meta, de.embedding, vector_dims(de.embedding) as embedding_dims
            FROM docs d
            LEFT JOIN doc_embeddings de ON d.id = de.doc_id
            ORDER BY d.id
        """)
        
        # Debug logging
        service.logger.info(f"Retrieved {len(policies)} policies from database")
        for i, policy in enumerate(policies):
            service.logger.info(f"Policy {i}: id={policy.get('id')}, title={policy.get('title')}, embedding_type={type(policy.get('embedding'))}, embedding_value={policy.get('embedding')}")
        
        # Convert vector embeddings to arrays for JSON serialization
        for policy in policies:
            embedding = policy.get('embedding')
            embedding_dims = policy.get('embedding_dims')
            
            # Remove the embedding_dims field as it's not part of the Policy model
            if 'embedding_dims' in policy:
                del policy['embedding_dims']
            
            if embedding is not None and embedding_dims is not None:
                try:
                    # Handle pgvector data - it might be a string representation or a special object
                    if isinstance(embedding, str):
                        # If it's a string, try to parse it as a vector representation
                        # pgvector often returns strings like "[0.1, 0.2, 0.3]" or similar
                        if embedding.startswith('[') and embedding.endswith(']'):
                            # Remove brackets and split by comma
                            vector_str = embedding[1:-1]
                            if vector_str.strip():
                                policy['embedding'] = [float(x.strip()) for x in vector_str.split(',')]
                                service.logger.info(f"Parsed string embedding for policy {policy.get('id')}: {len(policy['embedding'])} dimensions (expected: {embedding_dims})")
                            else:
                                policy['embedding'] = None
                        else:
                            policy['embedding'] = None
                    elif hasattr(embedding, '__iter__') and not isinstance(embedding, str):
                        # If it's already iterable (list, tuple, etc.)
                        policy['embedding'] = list(embedding)
                        service.logger.info(f"Converted iterable embedding for policy {policy.get('id')}: {len(policy['embedding'])} dimensions (expected: {embedding_dims})")
                    else:
                        # Try to convert to string first, then parse
                        embedding_str = str(embedding)
                        if embedding_str.startswith('[') and embedding_str.endswith(']'):
                            vector_str = embedding_str[1:-1]
                            if vector_str.strip():
                                policy['embedding'] = [float(x.strip()) for x in vector_str.split(',')]
                                service.logger.info(f"Converted string representation for policy {policy.get('id')}: {len(policy['embedding'])} dimensions (expected: {embedding_dims})")
                            else:
                                policy['embedding'] = None
                        else:
                            service.logger.info(f"Unknown embedding format for policy {policy.get('id')}: {type(embedding)} - {embedding} (expected dims: {embedding_dims})")
                            policy['embedding'] = None
                except Exception as e:
                    service.logger.error(f"Error converting embedding for policy {policy.get('id')}: {e} (expected dims: {embedding_dims})")
                    policy['embedding'] = None
            else:
                service.logger.info(f"No embedding found for policy {policy.get('id')} (dims: {embedding_dims})")
        
        service.log_request(request, {"status": "success", "count": len(policies)})
        return policies
    except Exception as e:
        service.log_error(e, "get_policies endpoint")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/data/policies")
async def create_policy(policy: Policy, request: Request):
    try:
        # Insert document
        doc_query = "INSERT INTO docs (title, content, meta) VALUES (%s, %s, %s) RETURNING id"
        doc_params = (policy.title, policy.content, json.dumps(policy.meta))
        
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(doc_query, doc_params)
                doc_id = cur.fetchone()[0]
                
                # Generate and insert embedding
                embedding = embed(policy.content[:5000])  # Truncate for embedding
                embed_query = "INSERT INTO doc_embeddings (doc_id, embedding) VALUES (%s, %s)"
                embed_params = (doc_id, embedding)
                cur.execute(embed_query, embed_params)
        
        service.log_request(request, {"status": "success"})
        return {"message": "Policy created successfully", "id": doc_id}
    except Exception as e:
        service.log_error(e, "create_policy endpoint")
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/data/policies/{policy_id}")
async def update_policy(policy_id: int, policy: Policy, request: Request):
    try:
        # Update document
        doc_query = "UPDATE docs SET title=%s, content=%s, meta=%s WHERE id=%s"
        doc_params = (policy.title, policy.content, json.dumps(policy.meta), policy_id)
        rows_affected = execute_update(doc_query, doc_params)
        
        if rows_affected == 0:
            raise HTTPException(status_code=404, detail="Policy not found")
        
        # Generate and update embedding
        embedding = embed(policy.content[:5000])  # Truncate for embedding
        embed_query = """
            INSERT INTO doc_embeddings (doc_id, embedding) VALUES (%s, %s)
            ON CONFLICT (doc_id) DO UPDATE SET embedding = EXCLUDED.embedding
        """
        embed_params = (policy_id, embedding)
        execute_insert(embed_query, embed_params)
        
        service.log_request(request, {"status": "success"})
        return {"message": "Policy updated successfully"}
    except HTTPException:
        raise
    except Exception as e:
        service.log_error(e, "update_policy endpoint")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/data/policies/{policy_id}")
async def delete_policy(policy_id: int, request: Request):
    try:
        query = "DELETE FROM docs WHERE id=%s"
        rows_affected = execute_delete(query, (policy_id,))
        if rows_affected == 0:
            raise HTTPException(status_code=404, detail="Policy not found")
        service.log_request(request, {"status": "success"})
        return {"message": "Policy deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        service.log_error(e, "delete_policy endpoint")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/data/policies/search")
async def search_policies(query: dict, request: Request):
    try:
        search_term = query.get("query", "")
        if not search_term:
            return []
        
        # Simple text search for now - could be enhanced with vector search
        policies = execute_query("""
            SELECT d.id, d.title, d.content, d.meta, de.embedding, vector_dims(de.embedding) as embedding_dims
            FROM docs d
            LEFT JOIN doc_embeddings de ON d.id = de.doc_id
            WHERE d.title ILIKE %s OR d.content ILIKE %s
            ORDER BY d.id
        """, (f"%{search_term}%", f"%{search_term}%"))
        
        # Convert vector embeddings to arrays for JSON serialization
        for policy in policies:
            embedding = policy.get('embedding')
            embedding_dims = policy.get('embedding_dims')
            
            # Remove the embedding_dims field as it's not part of the Policy model
            if 'embedding_dims' in policy:
                del policy['embedding_dims']
            
            if embedding is not None and embedding_dims is not None:
                try:
                    # Handle pgvector data - it might be a string representation or a special object
                    if isinstance(embedding, str):
                        # If it's a string, try to parse it as a vector representation
                        if embedding.startswith('[') and embedding.endswith(']'):
                            vector_str = embedding[1:-1]
                            if vector_str.strip():
                                policy['embedding'] = [float(x.strip()) for x in vector_str.split(',')]
                            else:
                                policy['embedding'] = None
                        else:
                            policy['embedding'] = None
                    elif hasattr(embedding, '__iter__') and not isinstance(embedding, str):
                        policy['embedding'] = list(embedding)
                    else:
                        embedding_str = str(embedding)
                        if embedding_str.startswith('[') and embedding_str.endswith(']'):
                            vector_str = embedding_str[1:-1]
                            if vector_str.strip():
                                policy['embedding'] = [float(x.strip()) for x in vector_str.split(',')]
                            else:
                                policy['embedding'] = None
                        else:
                            policy['embedding'] = None
                except Exception as e:
                    policy['embedding'] = None
        
        service.log_request(request, {"status": "success", "count": len(policies)})
        return policies
    except Exception as e:
        service.log_error(e, "search_policies endpoint")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/data/policies/debug")
async def debug_policies(request: Request):
    """Debug endpoint to check the current state of policies and embeddings."""
    try:
        all_docs = execute_query("SELECT id, title, content FROM docs ORDER BY id")
        all_embeddings = execute_query("SELECT doc_id, vector_dims(embedding) as dims FROM doc_embeddings ORDER BY doc_id")
        
        # Check which docs have embeddings
        docs_with_embeddings = set(row['doc_id'] for row in all_embeddings)
        docs_without_embeddings = [doc for doc in all_docs if doc['id'] not in docs_with_embeddings]
        
        return {
            "total_docs": len(all_docs),
            "total_embeddings": len(all_embeddings),
            "docs_without_embeddings": len(docs_without_embeddings),
            "docs_without_embeddings_list": docs_without_embeddings,
            "embedding_dimensions": [row['dims'] for row in all_embeddings] if all_embeddings else []
        }
    except Exception as e:
        service.log_error(e, "debug_policies endpoint")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/data/policies/regenerate-embeddings")
async def regenerate_embeddings(request: Request):
    """Regenerate embeddings for all policies that don't have them."""
    try:
        # First, let's check what's in the database
        all_docs = execute_query("SELECT id, title FROM docs ORDER BY id")
        all_embeddings = execute_query("SELECT doc_id FROM doc_embeddings ORDER BY doc_id")
        
        service.logger.info(f"Total docs: {len(all_docs)}, Total embeddings: {len(all_embeddings)}")
        
        # Get all policies without embeddings - use NOT EXISTS for better reliability
        policies_without_embeddings = execute_query("""
            SELECT d.id, d.title, d.content
            FROM docs d
            WHERE NOT EXISTS (
                SELECT 1 FROM doc_embeddings de 
                WHERE de.doc_id = d.id
            )
        """)
        
        service.logger.info(f"Policies without embeddings: {len(policies_without_embeddings)}")
        
        updated_count = 0
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                for policy in policies_without_embeddings:
                    # Generate embedding
                    embedding = embed(policy['content'][:5000])
                    
                    # Insert embedding
                    embed_query = "INSERT INTO doc_embeddings (doc_id, embedding) VALUES (%s, %s)"
                    embed_params = (policy['id'], embedding)
                    cur.execute(embed_query, embed_params)
                    updated_count += 1
        
        service.log_request(request, {"status": "success", "updated_count": updated_count})
        return {
            "ok": True,
            "message": f"Regenerated embeddings for {updated_count} policies",
            "updated_count": updated_count
        }
    except Exception as e:
        service.log_error(e, "regenerate_embeddings endpoint")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/data/policies/force-regenerate-embeddings")
async def force_regenerate_embeddings(request: Request):
    """Force regenerate embeddings for ALL policies (delete existing and recreate)."""
    try:
        # Get all policies
        all_docs = execute_query("SELECT id, title, content FROM docs ORDER BY id")
        
        service.logger.info(f"Force regenerating embeddings for {len(all_docs)} policies")
        
        updated_count = 0
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                # Clear all existing embeddings
                cur.execute("DELETE FROM doc_embeddings")
                
                for policy in all_docs:
                    # Generate embedding
                    embedding = embed(policy['content'][:5000])
                    
                    # Insert embedding
                    embed_query = "INSERT INTO doc_embeddings (doc_id, embedding) VALUES (%s, %s)"
                    embed_params = (policy['id'], embedding)
                    cur.execute(embed_query, embed_params)
                    updated_count += 1
        
        service.log_request(request, {"status": "success", "updated_count": updated_count})
        return {
            "ok": True,
            "message": f"Force regenerated embeddings for {updated_count} policies",
            "updated_count": updated_count
        }
    except Exception as e:
        service.log_error(e, "force_regenerate_embeddings endpoint")
        raise HTTPException(status_code=500, detail=str(e))

# Clear all data endpoint
@app.delete("/data/clear")
async def clear_all_data(request: Request):
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                # Clear all data from tables (in order to respect foreign key constraints)
                cur.execute("DELETE FROM doc_embeddings")
                cur.execute("DELETE FROM docs")
                cur.execute("DELETE FROM crew_roster")
                cur.execute("DELETE FROM bookings")
                cur.execute("DELETE FROM flights")
                cur.execute("DELETE FROM crew_details")
                cur.execute("DELETE FROM aircraft_status")
                
                # Get counts of deleted records
                counts = {
                    "flights": cur.rowcount if 'flights' in locals() else 0,
                    "bookings": cur.rowcount if 'bookings' in locals() else 0,
                    "crew_roster": cur.rowcount if 'crew_roster' in locals() else 0,
                    "crew_details": cur.rowcount if 'crew_details' in locals() else 0,
                    "aircraft_status": cur.rowcount if 'aircraft_status' in locals() else 0,
                    "policies": cur.rowcount if 'docs' in locals() else 0
                }
        
        service.log_request(request, {"status": "success", "counts": counts})
        return {
            "ok": True,
            "message": "All data cleared successfully",
            "counts": counts
        }
    except Exception as e:
        service.log_error(e, "clear_all_data endpoint")
        raise HTTPException(status_code=500, detail=str(e))

# Predictive Analytics Endpoints
@app.post("/predict/disruptions")
async def predict_disruptions(request: Request):
    """Predict potential disruptions for flights"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(f"{PREDICTIVE_URL}/predict_disruptions", json=await request.json())
            return response.json()
    except Exception as e:
        service.log_error(e, "predict_disruptions endpoint")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/predict/bulk")
async def bulk_predict_disruptions(request: Request):
    """Predict disruptions for all flights in the next 24 hours"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(f"{PREDICTIVE_URL}/bulk_predict")
            return response.json()
    except Exception as e:
        service.log_error(e, "bulk_predict_disruptions endpoint")
        raise HTTPException(status_code=500, detail=str(e))

# Crew Management Endpoints
@app.post("/crew/optimize")
async def optimize_crew_assignments(request: Request):
    """Optimize crew assignments for a flight"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(f"{CREW_URL}/optimize_crew", json=await request.json())
            return response.json()
    except Exception as e:
        service.log_error(e, "optimize_crew_assignments endpoint")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/crew/suggest_swap")
async def suggest_crew_swap(request: Request):
    """Suggest crew replacement for unavailable crew member"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(f"{CREW_URL}/suggest_crew_swap", json=await request.json())
            return response.json()
    except Exception as e:
        service.log_error(e, "suggest_crew_swap endpoint")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/crew/legality/{crew_id}")
async def check_crew_legality(crew_id: str, flight_no: str, date: str, request: Request):
    """Check legality of a specific crew member for a flight"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{CREW_URL}/crew_legality/{crew_id}?flight_no={flight_no}&date={date}")
            return response.json()
    except Exception as e:
        service.log_error(e, "check_crew_legality endpoint")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/crew/availability")
async def get_crew_availability(date: str, role: Optional[str] = None, request: Request = None):
    """Get available crew members for a specific date and role"""
    try:
        params = {"date": date}
        if role:
            params["role"] = role
        
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{CREW_URL}/crew_availability", params=params)
            return response.json()
    except Exception as e:
        service.log_error(e, "get_crew_availability endpoint")
        raise HTTPException(status_code=500, detail=str(e))

# Enhanced Communication Endpoints
@app.post("/comms/multilingual")
async def draft_multilingual_communication(request: Request):
    """Generate communications in multiple languages"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(f"{COMMS_URL}/draft_multilingual", json=await request.json())
            return response.json()
    except Exception as e:
        service.log_error(e, "draft_multilingual_communication endpoint")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/comms/analyze_sentiment")
async def analyze_communication_sentiment(request: Request):
    """Analyze sentiment of customer communication"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(f"{COMMS_URL}/analyze_sentiment", json=await request.json())
            return response.json()
    except Exception as e:
        service.log_error(e, "analyze_communication_sentiment endpoint")
        raise HTTPException(status_code=500, detail=str(e))
