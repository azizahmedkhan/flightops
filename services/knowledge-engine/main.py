import re
import json
from contextlib import asynccontextmanager
from datetime import datetime, date
from typing import Any, Dict, List, Optional, Tuple

import psycopg
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger
from openai import OpenAI
from pydantic import BaseModel, Field
from psycopg_pool import ConnectionPool

from services.shared.base_service import BaseService, LATENCY, log_startup

# ---------------------------------------------------------------------------
# Service bootstrap
# ---------------------------------------------------------------------------

service = BaseService("knowledge-engine", "1.0.0")
app = service.get_app()

# Basic middleware – allow internal service-to-service calls
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Environment / configuration
DB_HOST = service.get_env_var("DB_HOST")
DB_PORT = service.get_env_int("DB_PORT")
DB_NAME = service.get_env_var("DB_NAME")
DB_USER = service.get_env_var("DB_USER")
DB_PASS = service.get_env_var("DB_PASS")
OPENAI_API_KEY = service.get_env_var("OPENAI_API_KEY")
EMBEDDINGS_MODEL = service.get_env_var("EMBEDDINGS_MODEL")

DB_CONN_STRING = (
    f"host={DB_HOST} port={DB_PORT} dbname={DB_NAME} "
    f"user={DB_USER} password={DB_PASS}"
)

db_pool: Optional[ConnectionPool] = None

# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------


class SearchRequest(BaseModel):
    query: str = Field(..., description="Natural language query")
    k: int = Field(5, ge=1, le=20, description="Number of results to return")
    category: Optional[str] = Field(None, description="Optional document category filter")


class SearchResponse(BaseModel):
    mode: str
    results: List[Dict[str, Any]]
    embeddings_available: bool
    category_counts: Optional[Dict[str, int]] = None
    total_documents: Optional[int] = None


class FlightLookupRequest(BaseModel):
    flight_no: str
    date: str


class FlightLookupResponse(BaseModel):
    flight_no: str
    origin: str
    destination: str
    sched_dep: Optional[str]
    sched_arr: Optional[str]
    status: Optional[str]
    tail_number: Optional[str]


class ImpactAssessmentResponse(BaseModel):
    passengers: int
    connecting_passengers: int
    crew: int
    crew_roles: str
    aircraft_status: str
    aircraft_location: str
    summary: str


class CrewDetailsResponse(BaseModel):
    crew_id: str
    role: str
    name: str
    duty_start: Optional[str]
    max_hours: Optional[int]


class PassengerProfileRecord(BaseModel):
    pnr: str
    passenger_name: str
    has_connection: bool
    connecting_flight_no: Optional[str] = None


# ---------------------------------------------------------------------------
# Utility helpers
# ---------------------------------------------------------------------------


def _parse_date(value: str) -> date:
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
    except ValueError as exc:  # pragma: no cover - defensive
        raise HTTPException(status_code=400, detail=f"Invalid date value: {value}") from exc


def _iso_or_none(value: Optional[Any]) -> Optional[str]:
    if isinstance(value, datetime):
        return value.isoformat()
    return value


def _get_connection():
    if not db_pool:
        raise HTTPException(status_code=503, detail="Database connection unavailable")
    return db_pool.connection()


def embed(text: str) -> List[float]:
    try:
        client = OpenAI(api_key=OPENAI_API_KEY)
        resp = client.embeddings.create(input=[text], model=EMBEDDINGS_MODEL)
        return resp.data[0].embedding
    except Exception as exc:  # pragma: no cover - relies on external API
        service.log_error(exc, "embedding generation")
        raise HTTPException(status_code=500, detail="Embedding generation failed") from exc


def tokenize(text: str) -> List[str]:
    return re.findall(r"\\b\\w+\\b", text.lower())


def get_bm25_scores(query: str, documents: List[Dict[str, Any]]) -> List[Tuple[int, float]]:
    if not documents:
        return []

    from rank_bm25 import BM25Okapi

    tokenized_docs: List[Tuple[Dict[str, Any], List[str]]] = []
    for doc in documents:
        content = doc.get("content") or ""
        tokens = tokenize(content)
        if tokens:
            tokenized_docs.append((doc, tokens))

    if not tokenized_docs:
        service.logger.warning("BM25 skipped: no tokenized documents available")
        return []

    query_tokens = tokenize(query)
    if not query_tokens:
        service.logger.info("BM25 skipped: empty query tokens")
        return []

    doc_tokens = [tokens for _, tokens in tokenized_docs]
    filtered_docs = [doc for doc, _ in tokenized_docs]

    bm25 = BM25Okapi(doc_tokens)
    scores = bm25.get_scores(query_tokens)
    return [(doc["doc_id"], float(score)) for doc, score in zip(filtered_docs, scores)]


def get_vector_scores(query: str, k: int, category: Optional[str] = None) -> List[Tuple[int, float]]:
    try:
        vec = embed(query)
    except HTTPException:
        return []

    with _get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM doc_embeddings")
            cnt = cur.fetchone()[0]
            if cnt == 0:
                return []

            cur.execute("CREATE TEMP TABLE IF NOT EXISTS tmp_query(q vector(1536))")
            cur.execute("TRUNCATE tmp_query")
            cur.execute("INSERT INTO tmp_query VALUES (%s)", (vec,))

            if category:
                cur.execute(
                    """
                    SELECT d.id,
                           CASE WHEN de.embedding <#> t.q IS NOT NULL
                                THEN 1 - (de.embedding <#> t.q)
                                ELSE 0.0
                           END AS score
                    FROM doc_embeddings de
                    JOIN docs d ON d.id = de.doc_id
                    JOIN tmp_query t ON TRUE
                    WHERE d.meta->>'category' = %s
                    ORDER BY de.embedding <-> t.q
                    LIMIT %s
                    """,
                    (category, k),
                )
            else:
                cur.execute(
                    """
                    SELECT d.id,
                           CASE WHEN de.embedding <#> t.q IS NOT NULL
                                THEN 1 - (de.embedding <#> t.q)
                                ELSE 0.0
                           END AS score
                    FROM doc_embeddings de
                    JOIN docs d ON d.id = de.doc_id
                    JOIN tmp_query t ON TRUE
                    ORDER BY de.embedding <-> t.q
                    LIMIT %s
                    """,
                    (k,),
                )

            results: List[Tuple[int, float]] = []
            for doc_id, score in cur.fetchall():
                try:
                    results.append((int(doc_id), float(score or 0.0)))
                except (TypeError, ValueError):
                    results.append((int(doc_id), 0.0))
            return results


def hybrid_search(query: str, k: int = 5, category: Optional[str] = None) -> List[Dict[str, Any]]:
    with _get_connection() as conn:
        with conn.cursor() as cur:
            if category:
                cur.execute(
                    "SELECT id, title, content, meta FROM docs WHERE meta->>'category' = %s",
                    (category,),
                )
            else:
                cur.execute("SELECT id, title, content, meta FROM docs")

            docs = [
                {
                    "doc_id": row[0],
                    "title": row[1],
                    "content": row[2],
                    "meta": row[3] or {},
                }
                for row in cur.fetchall()
            ]

    if not docs:
        return []

    bm25_scores = get_bm25_scores(query, docs)
    vector_scores = get_vector_scores(query, k * 2, category)

    def normalize(scores: List[Tuple[int, float]]) -> Dict[int, float]:
        if not scores:
            return {}
        min_score = min(score for _, score in scores)
        max_score = max(score for _, score in scores)
        if max_score == min_score:
            return {doc_id: 1.0 for doc_id, _ in scores}
        return {
            doc_id: (score - min_score) / (max_score - min_score)
            for doc_id, score in scores
        }

    bm25_norm = normalize(bm25_scores)
    vector_norm = normalize(vector_scores)

    combined: Dict[int, float] = {}
    for doc_id in set(bm25_norm) | set(vector_norm):
        combined[doc_id] = 0.5 * bm25_norm.get(doc_id, 0.0) + 0.5 * vector_norm.get(doc_id, 0.0)

    ranked = sorted(combined.items(), key=lambda item: item[1], reverse=True)[:k]
    doc_lookup = {doc["doc_id"]: doc for doc in docs}

    results: List[Dict[str, Any]] = []
    for doc_id, score in ranked:
        doc = doc_lookup.get(doc_id)
        if not doc:
            continue
        content = doc["content"]
        snippet = content[:300] + "..." if len(content) > 300 else content
        meta = doc["meta"] or {}
        results.append(
            {
                "doc_id": doc_id,
                "title": doc["title"],
                "snippet": snippet,
                "score": score,
                "source": meta.get("source", "unknown"),
                "category": meta.get("category", "unknown"),
                "chunk_index": meta.get("chunk_index"),
                "total_chunks": meta.get("total_chunks"),
            }
        )
    return results


def _search_category_counts() -> Tuple[int, Dict[str, int]]:
    with _get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM docs")
            total = cur.fetchone()[0]
            cur.execute("SELECT meta->>'category', COUNT(*) FROM docs GROUP BY meta->>'category'")
            counts = {row[0] or "unknown": row[1] for row in cur.fetchall()}
            return total, counts


def _embedding_count() -> int:
    with _get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM doc_embeddings")
            return cur.fetchone()[0]


def _flight_lookup(flight_no: str, flight_date: date) -> Optional[FlightLookupResponse]:
    with _get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT flight_no, origin, destination, sched_dep_time, sched_arr_time, status, tail_number
                FROM flights
                WHERE flight_no = %s AND flight_date = %s
                """,
                (flight_no, flight_date),
            )
            row = cur.fetchone()
            if not row:
                return None
            return FlightLookupResponse(
                flight_no=row[0],
                origin=row[1],
                destination=row[2],
                sched_dep=_iso_or_none(row[3]),
                sched_arr=_iso_or_none(row[4]),
                status=row[5],
                tail_number=row[6],
            )


def _impact_assessment(flight_no: str, flight_date: date) -> ImpactAssessmentResponse:
    with _get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT COUNT(*) AS pax,
                       COUNT(CASE WHEN has_connection = 'TRUE' THEN 1 END) AS connecting
                FROM bookings
                WHERE flight_no = %s AND flight_date = %s
                """,
                (flight_no, flight_date),
            )
            pax_row = cur.fetchone() or (0, 0)
            passengers = pax_row[0] or 0
            connecting = pax_row[1] or 0

            cur.execute(
                """
                SELECT COUNT(*) AS crew,
                       COALESCE(STRING_AGG(DISTINCT crew_role, ', '), 'Unknown')
                FROM crew_roster
                WHERE flight_no = %s AND flight_date = %s
                """,
                (flight_no, flight_date),
            )
            crew_row = cur.fetchone() or (0, "Unknown")
            crew = crew_row[0] or 0
            crew_roles = crew_row[1] or "Unknown"

            cur.execute(
                """
                SELECT f.tail_number, a.status, a.current_location
                FROM flights f
                LEFT JOIN aircraft_status a ON f.tail_number = a.tail_number
                WHERE f.flight_no = %s AND f.flight_date = %s
                """,
                (flight_no, flight_date),
            )
            aircraft_row = cur.fetchone() or (None, "Unknown", "Unknown")
            aircraft_status = aircraft_row[1] or "Unknown"
            aircraft_location = aircraft_row[2] or "Unknown"

    summary = (
        f"{passengers} passengers ({connecting} with connections) and {crew} crew affected. "
        f"Aircraft status: {aircraft_status} at {aircraft_location}."
    )

    return ImpactAssessmentResponse(
        passengers=passengers,
        connecting_passengers=connecting,
        crew=crew,
        crew_roles=crew_roles,
        aircraft_status=aircraft_status,
        aircraft_location=aircraft_location,
        summary=summary,
    )


def _crew_details(flight_no: str, flight_date: date) -> List[CrewDetailsResponse]:
    with _get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT cr.crew_id, cr.crew_role, cd.crew_name, cd.duty_start_time, cd.max_duty_hours
                FROM crew_roster cr
                LEFT JOIN crew_details cd ON cr.crew_id = cd.crew_id
                WHERE cr.flight_no = %s AND cr.flight_date = %s
                ORDER BY cr.crew_role
                """,
                (flight_no, flight_date),
            )
            rows = cur.fetchall()

    details: List[CrewDetailsResponse] = []
    for row in rows:
        details.append(
            CrewDetailsResponse(
                crew_id=row[0],
                role=row[1],
                name=row[2] or "Unknown",
                duty_start=_iso_or_none(row[3]) if isinstance(row[3], datetime) else row[3],
                max_hours=row[4],
            )
        )
    return details


def _passenger_profiles(flight_no: str, flight_date: date) -> List[PassengerProfileRecord]:
    with _get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT pnr, passenger_name, has_connection, connecting_flight_no
                FROM bookings
                WHERE flight_no = %s AND flight_date = %s
                ORDER BY passenger_name
                """,
                (flight_no, flight_date),
            )
            rows = cur.fetchall()

    profiles: List[PassengerProfileRecord] = []
    for row in rows:
        has_connection = row[2]
        if isinstance(has_connection, str):
            has_connection = has_connection.upper() == "TRUE"
        profiles.append(
            PassengerProfileRecord(
                pnr=row[0],
                passenger_name=row[1],
                has_connection=bool(has_connection),
                connecting_flight_no=row[3],
            )
        )
    return profiles


# ---------------------------------------------------------------------------
# Lifespan
# ---------------------------------------------------------------------------


@asynccontextmanager
async def lifespan(app: FastAPI):
    global db_pool

    log_startup("knowledge-engine")
    db_pool = ConnectionPool(DB_CONN_STRING, min_size=2, max_size=10)

    yield

    if db_pool:
        db_pool.close()


app.router.lifespan_context = lifespan

# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@app.get("/healthz")
def health_check():
    if not db_pool:
        raise HTTPException(status_code=503, detail="Database pool not initialised")
    return {"status": "ok", "service": "knowledge-engine"}


@app.post("/search", response_model=SearchResponse)
def search_endpoint(payload: SearchRequest, request: Request):
    with LATENCY.labels("knowledge-engine", "/search", "POST").time():
        results = hybrid_search(payload.query, payload.k, payload.category)
        embeddings_available = _embedding_count() > 0
        total_docs, counts = _search_category_counts()

        mode = "hybrid" if embeddings_available else ("bm25_only" if total_docs else "no_data")
        response = SearchResponse(
            mode=mode,
            results=results,
            embeddings_available=embeddings_available,
            category_counts=counts,
            total_documents=total_docs,
        )
        service.log_request(request, {"status": "success", "mode": mode, "result_count": len(results)})
        return response


@app.post("/tools/search_policies", response_model=SearchResponse)
def search_policies(payload: SearchRequest, request: Request):
    return search_endpoint(payload, request)


@app.post("/tools/lookup_flight", response_model=FlightLookupResponse)
def lookup_flight(payload: FlightLookupRequest, request: Request):
    with LATENCY.labels("knowledge-engine", "/tools/lookup_flight", "POST").time():
        flight_date = _parse_date(payload.date)
        flight = _flight_lookup(payload.flight_no, flight_date)
        if not flight:
            raise HTTPException(status_code=404, detail="Flight not found")
        service.log_request(request, {"status": "success", "flight_no": payload.flight_no})
        return flight


@app.post("/tools/impact_assessment", response_model=ImpactAssessmentResponse)
def impact_assessment(payload: FlightLookupRequest, request: Request):
    with LATENCY.labels("knowledge-engine", "/tools/impact_assessment", "POST").time():
        flight_date = _parse_date(payload.date)
        response = _impact_assessment(payload.flight_no, flight_date)
        service.log_request(
            request,
            {"status": "success", "flight_no": payload.flight_no, "date": flight_date.isoformat()},
        )
        return response


@app.post("/tools/crew_details", response_model=List[CrewDetailsResponse])
def crew_details(payload: FlightLookupRequest, request: Request):
    with LATENCY.labels("knowledge-engine", "/tools/crew_details", "POST").time():
        flight_date = _parse_date(payload.date)
        response = _crew_details(payload.flight_no, flight_date)
        service.log_request(
            request,
            {
                "status": "success",
                "flight_no": payload.flight_no,
                "crew_count": len(response),
            },
        )
        return response


@app.post("/tools/passenger_profiles", response_model=List[PassengerProfileRecord])
def passenger_profiles(payload: FlightLookupRequest, request: Request):
    with LATENCY.labels("knowledge-engine", "/tools/passenger_profiles", "POST").time():
        flight_date = _parse_date(payload.date)
        response = _passenger_profiles(payload.flight_no, flight_date)
        service.log_request(
            request,
            {
                "status": "success",
                "flight_no": payload.flight_no,
                "profile_count": len(response),
            },
        )
        return response


# Compatibility alias for legacy knowledge service clients
@app.post("/kb/search", response_model=SearchResponse)
def kb_search(payload: SearchRequest, request: Request):
    return search_endpoint(payload, request)


@app.post("/kb/search/customer", response_model=SearchResponse)
def kb_search_customer(payload: SearchRequest, request: Request):
    payload.category = "customer"
    return search_endpoint(payload, request)


@app.post("/kb/search/operational", response_model=SearchResponse)
def kb_search_operational(payload: SearchRequest, request: Request):
    payload.category = "operational"
    return search_endpoint(payload, request)


# ---------------------------------------------------------------------------
# Admin helpers (minimal for now)
# ---------------------------------------------------------------------------


@app.get("/documents")
def list_documents():
    with _get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, title, meta->>'category' as category, meta->>'source' as source FROM docs ORDER BY id"
            )
            rows = cur.fetchall()
            return [
                {"id": row[0], "title": row[1], "category": row[2], "source": row[3]}
                for row in rows
            ]
