import json
import struct
from contextlib import asynccontextmanager
from datetime import datetime, date, time
from typing import List, Dict, Any, Optional

import httpx
import psycopg
from fastapi import Request, HTTPException
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from psycopg.errors import UndefinedTable
from psycopg_pool import ConnectionPool

from services.shared.base_service import BaseService
from services.shared.llm_tracker import LLMTracker

# Initialize base service
service = BaseService("gateway-api", "1.0.0")
app = service.get_app()

# Database connection is initialized at module load time

# Get environment variables using the base service
AGENT_URL = service.get_env_var("AGENT_URL", "http://agent-svc:8082")
RETRIEVAL_URL = service.get_env_var("RETRIEVAL_URL", "http://knowledge-engine:8081")
COMMS_URL = service.get_env_var("COMMS_URL", "http://comms-svc:8083")
INGEST_URL = service.get_env_var("INGEST_URL", "http://ingest-svc:8084")
CUSTOMER_CHAT_URL = service.get_env_var("CUSTOMER_CHAT_URL", "http://customer-chat-svc:8085")
PREDICTIVE_URL = service.get_env_var("PREDICTIVE_URL", "http://predictive-svc:8085")
CREW_URL = service.get_env_var("CREW_URL", "http://crew-svc:8086")
DB_ROUTER_URL = service.get_env_var("DB_ROUTER_URL", "http://db-router-svc:8000")

# Database configuration
DB_HOST = service.get_env_var("DB_HOST", "db")
DB_PORT = service.get_env_int("DB_PORT", 5432)
DB_NAME = service.get_env_var("DB_NAME", "flightops")
DB_USER = service.get_env_var("DB_USER", "postgres")
DB_PASS = service.get_env_var("DB_PASS", "postgres")

# Embedding configuration
EMBEDDINGS_MODEL = service.get_env_var("EMBEDDINGS_MODEL", "text-embedding-3-small")

# Create database connection pool
DB_CONN_STRING = f"host={DB_HOST} port={DB_PORT} dbname={DB_NAME} user={DB_USER} password={DB_PASS}"

# Initialize connection pool immediately
try:
    db_pool = ConnectionPool(DB_CONN_STRING, min_size=2, max_size=10)
    service.logger.info("Database connection pool initialized successfully")
except Exception as init_error:
    service.logger.warning(f"Failed to initialize database connection: {init_error}")
    db_pool = None

# Initialize database tables after connection pool is ready
if db_pool:
    try:
        ensure_tables_exist()
        service.logger.info("Database tables initialized successfully")
    except Exception as init_error:
        service.logger.warning(f"Failed to initialize database tables: {init_error}")

# Global LLM message store (in production, use Redis or database)
llm_messages = []

def embed(text: str) -> List[float]:
    """Generate embeddings using OpenAI API."""
    try:
        from openai import OpenAI
        client = OpenAI()  # Uses OPENAI_API_KEY from environment
        resp = client.embeddings.create(input=[text], model=EMBEDDINGS_MODEL)
        return resp.data[0].embedding
    except Exception as e:
        service.log_error(e, "embedding generation")
        raise e

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

# Database connection is initialized at module load time

# Database helper functions
def get_db_connection():
    if db_pool is not None:
        return db_pool.connection()
    else:
        # Fallback to direct connection if pool is not available
        import psycopg
        return psycopg.connect(DB_CONN_STRING)

def _execute_with_recovery(operation):
    try:
        return operation()
    except UndefinedTable:
        ensure_tables_exist()
        return operation()


def execute_query(query: str, params: tuple = None) -> List[Dict[str, Any]]:
    def run():
        with get_db_connection() as conn:
            conn.autocommit = True
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
            conn.autocommit = True
            with conn.cursor() as cur:
                cur.execute(query, params)
                return cur.rowcount

    return _execute_with_recovery(run)


def execute_update(query: str, params: tuple) -> int:
    def run():
        with get_db_connection() as conn:
            conn.autocommit = True
            with conn.cursor() as cur:
                cur.execute(query, params)
                return cur.rowcount

    return _execute_with_recovery(run)


def execute_delete(query: str, params: tuple) -> int:
    def run():
        with get_db_connection() as conn:
            conn.autocommit = True
            with conn.cursor() as cur:
                cur.execute(query, params)
                return cur.rowcount

    return _execute_with_recovery(run)


def _coerce_date(value: Any) -> Optional[date]:
    """Convert incoming values to date objects."""
    if value in (None, ""):
        return None

    if isinstance(value, date):
        return value

    value_str = str(value).strip()
    for fmt in ("%Y-%m-%d", "%Y/%m/%d"):
        try:
            return datetime.strptime(value_str, fmt).date()
        except ValueError:
            continue

    try:
        return datetime.fromisoformat(value_str).date()
    except ValueError as exc:
        raise ValueError(f"Invalid date value: {value_str}") from exc


def _coerce_time(value: Any) -> Optional[time]:
    """Convert various time representations into a time object."""
    if value in (None, ""):
        return None

    if isinstance(value, time):
        return value

    value_str = str(value).strip()

    try:
        parsed_dt = datetime.fromisoformat(value_str.replace("Z", "+00:00"))
        return parsed_dt.time()
    except ValueError:
        pass

    for fmt in ("%H:%M:%S", "%H:%M"):
        try:
            return datetime.strptime(value_str, fmt).time()
        except ValueError:
            continue

    raise ValueError(f"Invalid time value: {value_str}")


def _coerce_timestamp(value: Any, fallback_date: Optional[date] = None) -> Optional[datetime]:
    """Normalize timestamp values, allowing pure times when a date is supplied."""
    if value in (None, ""):
        return None

    if isinstance(value, datetime):
        return value

    value_str = str(value).strip()

    try:
        return datetime.fromisoformat(value_str.replace("Z", "+00:00"))
    except ValueError:
        pass

    time_value = _coerce_time(value_str)
    if fallback_date:
        return datetime.combine(fallback_date, time_value)

    raise ValueError(f"Invalid timestamp value: {value_str}")


def _serialize_temporal_fields(row: Dict[str, Any]) -> Dict[str, Any]:
    """Convert date and datetime objects to ISO strings for JSON responses."""
    serialized = dict(row)
    for field in ("flight_date", "duty_start_time"):
        value = serialized.get(field)
        if isinstance(value, (date, datetime)):
            serialized[field] = value.isoformat()

    for field in ("sched_dep_time", "sched_arr_time"):
        value = serialized.get(field)
        if isinstance(value, datetime):
            serialized[field] = value.isoformat()

    return serialized


def _normalize_embedding(raw_embedding: Any, expected_dims: Optional[Any]) -> Optional[List[float]]:
    """Coerce embeddings from Postgres/pgvector into JSON-safe float lists."""
    if raw_embedding is None:
        return None

    dims: Optional[int] = None
    if expected_dims is not None:
        try:
            dims = int(expected_dims)
        except (TypeError, ValueError):  # defensive: unexpected db result
            service.logger.warning(f"Unable to coerce embedding dims '{expected_dims}' to int")

    try:
        values: Optional[List[float]] = None

        if hasattr(raw_embedding, "tolist"):
            values = [float(x) for x in raw_embedding.tolist()]
        elif isinstance(raw_embedding, (list, tuple)):
            values = [float(x) for x in raw_embedding]
        elif isinstance(raw_embedding, memoryview):
            buffer = raw_embedding.tobytes()
            if len(buffer) % 4 != 0:
                service.logger.warning(
                    "Embedding buffer length is not divisible by 4; cannot decode vector"
                )
                return None
            values = [value for (value,) in struct.iter_unpack("!f", buffer)]
        elif isinstance(raw_embedding, (bytes, bytearray)):
            buffer = bytes(raw_embedding)
            if len(buffer) % 4 != 0:
                service.logger.warning(
                    "Embedding byte payload length is not divisible by 4; cannot decode vector"
                )
                return None
            values = [value for (value,) in struct.iter_unpack("!f", buffer)]
        elif isinstance(raw_embedding, str):
            cleaned = raw_embedding.strip()
            if cleaned:
                try:
                    values_json = json.loads(cleaned)
                except json.JSONDecodeError:
                    if cleaned.startswith("[") and cleaned.endswith("]"):
                        body = cleaned[1:-1]
                        parts = [part.strip() for part in body.split(",") if part.strip()]
                        values = [float(part) for part in parts]
                    else:
                        service.logger.warning(
                            "Unsupported embedding string format; expected JSON array representation"
                        )
                        return None
                else:
                    if isinstance(values_json, list):
                        values = [float(x) for x in values_json]
                    else:
                        service.logger.warning(
                            "Embedding string decoded to non-list JSON value; dropping embedding"
                        )
                        return None
            else:
                return None
        else:
            cleaned = str(raw_embedding).strip()
            if cleaned.startswith("[") and cleaned.endswith("]"):
                try:
                    value_list = json.loads(cleaned)
                except json.JSONDecodeError:
                    body = cleaned[1:-1]
                    parts = [part.strip() for part in body.split(",") if part.strip()]
                    value_list = [float(part) for part in parts]
                values = [float(x) for x in value_list]
            else:
                service.logger.warning(
                    f"Unsupported embedding type {type(raw_embedding)}; returning None"
                )
                return None

        if not values:
            return None

        if dims is not None and len(values) != dims:
            service.logger.warning(
                f"Embedding length {len(values)} does not match expected dimensions {dims}"
            )

        return values
    except Exception as exc:  # pragma: no cover - defensive against malformed data
        service.logger.error(f"Failed to normalize embedding: {exc}")
        return None


def _column_type(conn, table: str, column: str) -> Optional[str]:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT data_type
            FROM information_schema.columns
            WHERE table_name = %s AND column_name = %s
            """,
            (table, column),
        )
        result = cur.fetchone()
        return result[0] if result else None


def _alter_column(conn, table: str, column: str, target_type: str, expression: str) -> None:
    with conn.cursor() as cur:
        cur.execute(
            f"ALTER TABLE {table} ALTER COLUMN {column} TYPE {target_type} USING {expression}"
        )


def _migrate_legacy_columns(conn) -> None:
    """Upgrade legacy TEXT-based schedule columns to DATE/TIMESTAMP."""
    migrations = [
        (
            "flights",
            "flight_date",
            "date",
            "NULLIF(flight_date, '')::date",
        ),
        (
            "bookings",
            "flight_date",
            "date",
            "NULLIF(flight_date, '')::date",
        ),
        (
            "crew_roster",
            "flight_date",
            "date",
            "NULLIF(flight_date, '')::date",
        ),
        (
            "flights",
            "sched_dep_time",
            "timestamp without time zone",
            "CASE "
            "WHEN sched_dep_time IS NULL OR sched_dep_time = '' THEN NULL "
            "WHEN sched_dep_time ~ '^\\d{2}:\\d{2}(:\\d{2})?$' AND flight_date IS NOT NULL "
            "THEN (flight_date::text || ' ' || sched_dep_time)::timestamp "
            "ELSE NULLIF(sched_dep_time, '')::timestamp "
            "END",
        ),
        (
            "flights",
            "sched_arr_time",
            "timestamp without time zone",
            "CASE "
            "WHEN sched_arr_time IS NULL OR sched_arr_time = '' THEN NULL "
            "WHEN sched_arr_time ~ '^\\d{2}:\\d{2}(:\\d{2})?$' AND flight_date IS NOT NULL "
            "THEN (flight_date::text || ' ' || sched_arr_time)::timestamp "
            "ELSE NULLIF(sched_arr_time, '')::timestamp "
            "END",
        ),
    ]

    for table, column, target_type, expression in migrations:
        current = _column_type(conn, table, column)
        if current is None or current == target_type:
            continue

        try:
            _alter_column(conn, table, column, target_type, expression)
            service.logger.info(
                "Migrated %s.%s from %s to %s", table, column, current, target_type
            )
        except Exception as exc:
            service.logger.warning(
                "Failed to migrate %s.%s to %s: %s", table, column, target_type, exc
            )
            conn.rollback()
        else:
            conn.commit()


def ensure_tables_exist() -> None:
    """Ensure core data tables exist so read endpoints do not 500 on fresh databases."""
    create_statements = [
        """
        CREATE TABLE IF NOT EXISTS flights (
            flight_no TEXT,
            flight_date DATE,
            origin TEXT,
            destination TEXT,
            sched_dep_time TIMESTAMP,
            sched_arr_time TIMESTAMP,
            status TEXT,
            tail_number TEXT
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS bookings (
            flight_no TEXT,
            flight_date DATE,
            pnr TEXT,
            passenger_name TEXT,
            has_connection TEXT,
            connecting_flight_no TEXT
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS crew_roster (
            flight_no TEXT,
            flight_date DATE,
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
        conn.autocommit = False
        with conn.cursor() as cur:
            for statement in create_statements:
                cur.execute(statement)
        conn.commit()
        _migrate_legacy_columns(conn)


# Database schema will be initialized in the lifespan function after connection pool is ready

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
            r = await client.post(f"{AGENT_URL}/analyze-disruption", json=payload, timeout=60.0)
            result = r.json()
            
            # Track LLM message if present in response
            if 'llm_message' in result:
                llm_messages.append(result['llm_message'])
                # Keep only last 1000 messages
                if len(llm_messages) > 1000:
                    llm_messages[:] = llm_messages[-1000:]
            
            service.log_request(request, {"status": "success"})
            return result
    except Exception as e:
        service.log_error(e, "ask endpoint")
        raise

@app.post("/test_llm")
async def test_llm(request: Request):
    try:
        import time
        timestamp = time.time()
        print(f"DEBUG: test_llm endpoint called in gateway with request: {request} at {timestamp}...")
        print(f"DEBUG: Request headers: {dict(request.headers)}")
        print(f"DEBUG: Request method: {request.method}")
        print(f"DEBUG: Request URL: {request.url}")

        async with httpx.AsyncClient() as client:
            r = await client.post(f"{AGENT_URL}/test_llm", timeout=60.0)
            result = r.json()
            
            # Track LLM message if present in response
            if 'llm_message' in result:
                llm_messages.append(result['llm_message'])
                # Keep only last 1000 messages
                if len(llm_messages) > 1000:
                    llm_messages[:] = llm_messages[-1000:]
            
            service.log_request(request, {"status": "success"})
            return result
    except Exception as e:
        service.log_error(e, "test_llm endpoint")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/draft_comms")
async def draft_comms(payload: dict, request: Request):
    try:
        print(f"DEBUG: Gateway received draft_comms request: {payload}")
        print(f"DEBUG: AGENT_URL: {AGENT_URL}")
        async with httpx.AsyncClient() as client:
            r = await client.post(f"{AGENT_URL}/draft_comms", json=payload, timeout=60.0)
            print(f"DEBUG: Agent service response status: {r.status_code}")
            result = r.json()
            print(f"DEBUG: Agent service response: {result}")
            
            # Track LLM message if present in response
            if 'llm_message' in result:
                llm_messages.append(result['llm_message'])
                # Keep only last 1000 messages
                if len(llm_messages) > 1000:
                    llm_messages[:] = llm_messages[-1000:]
            
            service.log_request(request, {"status": "success"})
            return result
    except Exception as e:
        print(f"DEBUG: Gateway error: {e}")
        service.log_error(e, "draft_comms endpoint")
        raise

@app.post("/search")
async def search(payload: dict, request: Request):
    try:
        async with httpx.AsyncClient() as client:
            r = await client.post(f"{RETRIEVAL_URL}/search", json=payload, timeout=30.0)
            if r.status_code >= 400:
                message = None
                try:
                    error_body = r.json()
                    message = error_body if isinstance(error_body, str) else error_body.get("detail")
                except ValueError:
                    message = r.text

                service.log_request(
                    request,
                    {"status": "error", "upstream_status": r.status_code, "upstream_detail": message},
                )
                raise HTTPException(status_code=r.status_code, detail=message or "Search failed")

            result = r.json()
            service.log_request(request, {"status": "success"})
            return result
    except Exception as e:
        service.log_error(e, "search endpoint")
        raise

@app.post("/smart-ask")
async def smart_ask(payload: dict, request: Request):
    """
    Smart query endpoint that routes natural language queries to the database router service.
    This endpoint combines routing, execution, and formatting for database queries.
    """
    try:
        service.logger.info(f"Processing smart-ask request: {payload}")
        
        # Validate required fields
        if "text" not in payload:
            raise HTTPException(status_code=400, detail="Missing required field: text")
        
        # Set default auth role if not provided
        if "auth" not in payload:
            payload["auth"] = {"role": "public"}
        
        async with httpx.AsyncClient() as client:
            r = await client.post(f"{DB_ROUTER_URL}/smart-query", json=payload, timeout=30.0)
            
            if r.status_code != 200:
                service.logger.error(f"DB router service error: {r.status_code} - {r.text}")
                raise HTTPException(status_code=r.status_code, detail=f"Database router error: {r.text}")
            
            result = r.json()
            service.log_request(request, {"status": "success", "intent": result.get("intent")})
            return result
            
    except HTTPException:
        raise
    except Exception as e:
        service.log_error(e, "smart-ask endpoint")
        raise HTTPException(status_code=500, detail=f"Smart query failed: {str(e)}")

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
        rows = execute_query("SELECT * FROM flights ORDER BY flight_date, flight_no")
        flights = [_serialize_temporal_fields(row) for row in rows]
        service.log_request(request, {"status": "success", "count": len(flights)})
        return flights
    except Exception as e:
        service.log_error(e, "get_flights endpoint")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/data/flights")
async def create_flight(flight: Flight, request: Request):
    try:
        try:
            flight_date = _coerce_date(flight.flight_date)
            sched_dep_time = _coerce_timestamp(flight.sched_dep_time, flight_date)
            sched_arr_time = _coerce_timestamp(flight.sched_arr_time, flight_date)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

        query = """
            INSERT INTO flights (flight_no, flight_date, origin, destination, sched_dep_time, sched_arr_time, status, tail_number)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """
        params = (
            flight.flight_no,
            flight_date,
            flight.origin,
            flight.destination,
            sched_dep_time,
            sched_arr_time,
            flight.status,
            flight.tail_number,
        )
        execute_insert(query, params)
        service.log_request(request, {"status": "success"})
        return {"message": "Flight created successfully"}
    except HTTPException:
        raise
    except Exception as e:
        service.log_error(e, "create_flight endpoint")
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/data/flights/{flight_no}")
async def update_flight(flight_no: str, flight: Flight, request: Request):
    try:
        try:
            flight_date = _coerce_date(flight.flight_date)
            sched_dep_time = _coerce_timestamp(flight.sched_dep_time, flight_date)
            sched_arr_time = _coerce_timestamp(flight.sched_arr_time, flight_date)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

        query = """
            UPDATE flights SET flight_date=%s, origin=%s, destination=%s, sched_dep_time=%s, 
                   sched_arr_time=%s, status=%s, tail_number=%s WHERE flight_no=%s
        """
        params = (
            flight_date,
            flight.origin,
            flight.destination,
            sched_dep_time,
            sched_arr_time,
            flight.status,
            flight.tail_number,
            flight_no,
        )
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
        rows = execute_query("SELECT * FROM bookings ORDER BY flight_date, flight_no")
        bookings = [_serialize_temporal_fields(row) for row in rows]
        service.log_request(request, {"status": "success", "count": len(bookings)})
        return bookings
    except Exception as e:
        service.log_error(e, "get_bookings endpoint")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/data/bookings")
async def create_booking(booking: Booking, request: Request):
    try:
        try:
            flight_date = _coerce_date(booking.flight_date)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

        query = """
            INSERT INTO bookings (flight_no, flight_date, pnr, passenger_name, has_connection, connecting_flight_no)
            VALUES (%s, %s, %s, %s, %s, %s)
        """
        params = (
            booking.flight_no,
            flight_date,
            booking.pnr,
            booking.passenger_name,
            booking.has_connection,
            booking.connecting_flight_no,
        )
        execute_insert(query, params)
        service.log_request(request, {"status": "success"})
        return {"message": "Booking created successfully"}
    except HTTPException:
        raise
    except Exception as e:
        service.log_error(e, "create_booking endpoint")
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/data/bookings/{pnr}")
async def update_booking(pnr: str, booking: Booking, request: Request):
    try:
        try:
            flight_date = _coerce_date(booking.flight_date)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

        query = """
            UPDATE bookings SET flight_no=%s, flight_date=%s, passenger_name=%s, 
                   has_connection=%s, connecting_flight_no=%s WHERE pnr=%s
        """
        params = (
            booking.flight_no,
            flight_date,
            booking.passenger_name,
            booking.has_connection,
            booking.connecting_flight_no,
            pnr,
        )
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
        rows = execute_query("SELECT * FROM crew_roster ORDER BY flight_date, flight_no")
        roster = [_serialize_temporal_fields(row) for row in rows]
        service.log_request(request, {"status": "success", "count": len(roster)})
        return roster
    except Exception as e:
        service.log_error(e, "get_crew_roster endpoint")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/data/crew_roster")
async def create_crew_roster(roster: CrewRoster, request: Request):
    try:
        try:
            flight_date = _coerce_date(roster.flight_date)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

        query = """
            INSERT INTO crew_roster (flight_no, flight_date, crew_id, crew_role)
            VALUES (%s, %s, %s, %s)
        """
        params = (roster.flight_no, flight_date, roster.crew_id, roster.crew_role)
        execute_insert(query, params)
        service.log_request(request, {"status": "success"})
        return {"message": "Crew roster entry created successfully"}
    except HTTPException:
        raise
    except Exception as e:
        service.log_error(e, "create_crew_roster endpoint")
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/data/crew_roster/{flight_no}/{crew_id}")
async def update_crew_roster(flight_no: str, crew_id: str, roster: CrewRoster, request: Request):
    try:
        try:
            flight_date = _coerce_date(roster.flight_date)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

        query = """
            UPDATE crew_roster SET flight_date=%s, crew_role=%s WHERE flight_no=%s AND crew_id=%s
        """
        params = (flight_date, roster.crew_role, flight_no, crew_id)
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
        
        service.logger.info(f"Retrieved {len(policies)} policies from database")

        for policy in policies:
            raw_embedding = policy.get('embedding')
            embedding_dims = policy.pop('embedding_dims', None)
            normalized_embedding = _normalize_embedding(raw_embedding, embedding_dims)

            if normalized_embedding is None and raw_embedding is not None:
                service.logger.warning(
                    f"Failed to normalize embedding for policy {policy.get('id')} (type={type(raw_embedding)})"
                )
            elif normalized_embedding is not None and embedding_dims is not None:
                preview = ", ".join(f"{value:.4f}" for value in normalized_embedding[:3])
                service.logger.debug(
                    "Embedding normalized for policy {} ({} dims expected {}, preview [{}{}])",
                    policy.get('id'),
                    len(normalized_embedding),
                    embedding_dims,
                    preview,
                    "..." if len(normalized_embedding) > 3 else "",
                )

            policy['embedding'] = normalized_embedding

            meta = policy.get('meta')
            if isinstance(meta, str):
                try:
                    policy['meta'] = json.loads(meta)
                except json.JSONDecodeError:
                    service.logger.warning(
                        f"Policy {policy.get('id')} meta column is not valid JSON string; leaving as-is"
                    )
        
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
        
        for policy in policies:
            raw_embedding = policy.get('embedding')
            embedding_dims = policy.pop('embedding_dims', None)
            policy['embedding'] = _normalize_embedding(raw_embedding, embedding_dims)

            meta = policy.get('meta')
            if isinstance(meta, str):
                try:
                    policy['meta'] = json.loads(meta)
                except json.JSONDecodeError:
                    service.logger.warning(
                        f"Policy {policy.get('id')} meta column is not valid JSON string; leaving as-is"
                    )
        
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

# Flight Number Autocomplete Endpoint
@app.get("/flights/autocomplete")
async def get_flight_autocomplete(q: str = "", limit: int = 10, request: Request = None):
    """Get flight numbers for autocomplete suggestions"""
    try:
        if not q or len(q) < 1:
            # Return recent flights if no query
            flights = execute_query("""
                SELECT DISTINCT flight_no, flight_date, origin, destination, status
                FROM flights 
                ORDER BY flight_date DESC, flight_no 
                LIMIT %s
            """, (limit,))
        else:
            # Search for flights matching the query
            flights = execute_query("""
                SELECT DISTINCT 
                    flight_no, 
                    flight_date, 
                    origin, 
                    destination, 
                    status,
                    CASE 
                        WHEN flight_no ILIKE %s THEN 1
                        WHEN flight_no ILIKE %s THEN 2
                        ELSE 3
                    END as priority
                FROM flights 
                WHERE flight_no ILIKE %s
                ORDER BY priority, flight_date DESC, flight_no
                LIMIT %s
            """, (f"{q}%", f"%{q}%", f"%{q}%", limit))
        
        # Format the response
        suggestions = []
        for flight in flights:
            suggestions.append({
                "flight_no": flight["flight_no"],
                "flight_date": flight["flight_date"],
                "route": f"{flight['origin']} → {flight['destination']}",
                "status": flight["status"],
                "display": f"{flight['flight_no']} ({flight['origin']} → {flight['destination']}) - {flight['status']}"
            })
        
        service.log_request(request, {"status": "success", "count": len(suggestions)})
        return {"suggestions": suggestions}
    except Exception as e:
        service.log_error(e, "get_flight_autocomplete endpoint")
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

# LLM Message Tracking Endpoints
@app.post("/llm/track")
async def track_llm_message(request: Request):
    """Track an LLM message from a service"""
    try:
        message_data = await request.json()
        llm_messages.append(message_data)
        # Keep only last 1000 messages
        if len(llm_messages) > 1000:
            llm_messages[:] = llm_messages[-1000:]
        return {"status": "success", "message_id": message_data.get("id")}
    except Exception as e:
        service.log_error(e, "track_llm_message endpoint")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/llm/messages")
async def get_llm_messages(limit: int = 50, service: Optional[str] = None):
    """Get recent LLM messages"""
    try:
        messages = llm_messages.copy()
        
        # Filter by service if specified
        if service:
            messages = [msg for msg in messages if msg.get("service") == service]
        
        # Sort by timestamp (newest first) and limit
        messages.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
        messages = messages[:limit]
        
        return {"messages": messages, "total": len(messages)}
    except Exception as e:
        service.log_error(e, "get_llm_messages endpoint")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/llm/messages")
async def clear_llm_messages():
    """Clear all LLM messages"""
    try:
        llm_messages.clear()
        return {"status": "success", "message": "All LLM messages cleared"}
    except Exception as e:
        service.log_error(e, "clear_llm_messages endpoint")
        raise HTTPException(status_code=500, detail=str(e))
