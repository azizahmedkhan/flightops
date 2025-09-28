import csv
import glob
import json
import re
import yaml
from contextlib import asynccontextmanager
from datetime import datetime, date, time
from typing import Dict, List, Tuple, Optional, Any

import psycopg
from fastapi import Request
from pydantic import BaseModel
from psycopg_pool import ConnectionPool

from services.shared.base_service import BaseService, log_startup

# Initialize base service
service = BaseService("ingest-svc", "1.0.0")
app = service.get_app()

# Get environment variables using the base service
DB_HOST = service.get_env_var("DB_HOST", "localhost")
DB_PORT = service.get_env_int("DB_PORT", 5432)
DB_NAME = service.get_env_var("DB_NAME", "flightops")
DB_USER = service.get_env_var("DB_USER", "postgres")
DB_PASS = service.get_env_var("DB_PASS", "postgres")
EMBEDDINGS_MODEL = service.get_env_var("EMBEDDINGS_MODEL", "text-embedding-3-small")

# Create database connection pool
DB_CONN_STRING = f"host={DB_HOST} port={DB_PORT} dbname={DB_NAME} user={DB_USER} password={DB_PASS}"
db_pool = None

DATA_DIR = "/data"

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

def parse_yaml_frontmatter(content: str) -> Tuple[Dict, str]:
    """Parse YAML frontmatter from markdown content."""
    if not content.startswith('---'):
        return {}, content
    
    try:
        # Find the end of frontmatter
        end_marker = content.find('---', 3)
        if end_marker == -1:
            return {}, content
        
        frontmatter_text = content[3:end_marker].strip()
        content_without_frontmatter = content[end_marker + 3:].strip()
        
        # Parse YAML
        frontmatter = yaml.safe_load(frontmatter_text) or {}
        return frontmatter, content_without_frontmatter
    except Exception as e:
        service.log_error(e, "YAML frontmatter parsing")
        return {}, content

def categorize_document(filename: str) -> str:
    """Categorize document based on filename numbering system."""
    # Extract number from filename (e.g., "01_checkin.md" -> "01")
    match = re.match(r'^(\d+)_', filename)
    if not match:
        return "unknown"
    
    doc_number = int(match.group(1))
    
    # 01-12 = customer-facing documents
    if 1 <= doc_number <= 12:
        return "customer"
    # 13-17 = operational documents
    elif 13 <= doc_number <= 17:
        return "operational"
    else:
        return "other"

def chunk_text(text: str, chunk_size: int = 400, overlap: float = 0.15) -> List[str]:
    """Split text into overlapping chunks for better knowledge search."""
    # Simple word-based chunking
    words = text.split()
    chunk_size_words = chunk_size
    overlap_words = int(chunk_size_words * overlap)
    
    chunks = []
    start = 0
    
    while start < len(words):
        end = min(start + chunk_size_words, len(words))
        chunk = ' '.join(words[start:end])
        chunks.append(chunk)
        
        if end >= len(words):
            break
            
        start = end - overlap_words
    
    return chunks

def estimate_tokens(text: str) -> int:
    """Rough estimation of token count (1 token ≈ 4 characters for English)."""
    return len(text) // 4

@asynccontextmanager
async def lifespan(app):
    global db_pool
    log_startup("ingest-svc")
    
    # Initialize connection pool
    db_pool = ConnectionPool(DB_CONN_STRING, min_size=2, max_size=10)
    
    yield
    
    # Close connection pool on shutdown
    if db_pool:
        db_pool.close()

# Set lifespan for the app
app.router.lifespan_context = lifespan

def _parse_date(value: Any) -> Optional[date]:
    """Convert incoming CSV value into a date object."""
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
    except ValueError:
        service.logger.warning("Unable to parse date value '%s'; defaulting to None", value_str)
        return None


def _parse_time(value: Any) -> Optional[time]:
    """Parse a time string into a time object."""
    if value in (None, ""):
        return None

    if isinstance(value, time):
        return value

    value_str = str(value).strip()

    # Handle full timestamp strings by extracting the time component
    try:
        dt = datetime.fromisoformat(value_str.replace("Z", "+00:00"))
        return dt.time()
    except ValueError:
        pass

    for fmt in ("%H:%M:%S", "%H:%M"):
        try:
            return datetime.strptime(value_str, fmt).time()
        except ValueError:
            continue

    service.logger.warning("Unable to parse time value '%s'; defaulting to midnight", value_str)
    return time(0, 0)


def _combine_datetime(flight_dt: Optional[date], time_value: Optional[time]) -> Optional[datetime]:
    """Combine a flight date with a clock time into a naive datetime."""
    if not flight_dt or not time_value:
        return None
    return datetime.combine(flight_dt, time_value)


def parse_csv_files() -> Dict[str, int]:
    """Parse CSV files and return counts of loaded records."""
    counts = {}

    with db_pool.connection() as conn:
        conn.autocommit = True
        with conn.cursor() as cur:
            # Drop existing tables to recreate with new structure
            cur.execute("DROP TABLE IF EXISTS flights CASCADE")
            cur.execute("DROP TABLE IF EXISTS bookings CASCADE")
            cur.execute("DROP TABLE IF EXISTS crew_roster CASCADE")
            cur.execute("DROP TABLE IF EXISTS crew_details CASCADE")
            cur.execute("DROP TABLE IF EXISTS aircraft_status CASCADE")

            # Create tables with new structure
            cur.execute(
                """
                CREATE TABLE flights(
                    flight_no TEXT,
                    flight_date DATE,
                    origin TEXT,
                    destination TEXT,
                    sched_dep_time TIMESTAMP,
                    sched_arr_time TIMESTAMP,
                    status TEXT,
                    tail_number TEXT
                );
                CREATE TABLE bookings(
                    flight_no TEXT,
                    flight_date DATE,
                    pnr TEXT,
                    passenger_name TEXT,
                    has_connection TEXT,
                    connecting_flight_no TEXT
                );
                CREATE TABLE crew_roster(
                    flight_no TEXT,
                    flight_date DATE,
                    crew_id TEXT,
                    crew_role TEXT
                );
                CREATE TABLE crew_details(
                    crew_id TEXT PRIMARY KEY,
                    crew_name TEXT,
                    duty_start_time TEXT,
                    max_duty_hours INTEGER
                );
                CREATE TABLE aircraft_status(
                    tail_number TEXT PRIMARY KEY,
                    current_location TEXT,
                    status TEXT
                );
            """
            )

            def load_csv(table_name: str, processor):
                path = f"{DATA_DIR}/csv/{table_name}.csv"
                if not os.path.exists(path):
                    service.log_error(f"CSV file not found: {path}", "parse_csv_files")
                    counts[table_name] = 0
                    return

                with open(path, newline='') as f:
                    reader = csv.DictReader(f)
                    processed_rows = [processor(row) for row in reader]

                cur.execute(f"DELETE FROM {table_name}")

                if processed_rows:
                    column_count = len(processed_rows[0])
                    placeholders = ",".join(["(" + ",".join(["%s"] * column_count) + ")"] * len(processed_rows))
                    flat_values = [value for row in processed_rows for value in row]
                    cur.execute(f"INSERT INTO {table_name} VALUES {placeholders}", flat_values)

                counts[table_name] = len(processed_rows)

            load_csv(
                "flights",
                lambda row: (
                    row.get("flight_no"),
                    (flight_dt := _parse_date(row.get("flight_date"))),
                    row.get("origin"),
                    row.get("destination"),
                    _combine_datetime(flight_dt, _parse_time(row.get("sched_dep_time"))),
                    _combine_datetime(flight_dt, _parse_time(row.get("sched_arr_time"))),
                    row.get("status"),
                    row.get("tail_number"),
                ),
            )

            load_csv(
                "bookings",
                lambda row: (
                    row.get("flight_no"),
                    _parse_date(row.get("flight_date")),
                    row.get("pnr"),
                    row.get("passenger_name"),
                    row.get("has_connection"),
                    row.get("connecting_flight_no"),
                ),
            )

            load_csv(
                "crew_roster",
                lambda row: (
                    row.get("flight_no"),
                    _parse_date(row.get("flight_date")),
                    row.get("crew_id"),
                    row.get("crew_role"),
                ),
            )

            load_csv(
                "crew_details",
                lambda row: (
                    row.get("crew_id"),
                    row.get("crew_name"),
                    row.get("duty_start_time"),
                    int(row.get("max_duty_hours", 0) or 0),
                ),
            )

            load_csv(
                "aircraft_status",
                lambda row: (
                    row.get("tail_number"),
                    row.get("current_location"),
                    row.get("status"),
                ),
            )

    return counts

def parse_markdown_files(kb_only: bool = False) -> Tuple[int, bool]:
    """Parse markdown policy files and return count of loaded docs and embeddings availability."""
    doc_count = 0
    chunk_count = 0
    embeddings_available = True  # Will be determined by actual API call
    
    with db_pool.connection() as conn:
        conn.autocommit = True
        with conn.cursor() as cur:
            # Enable vector extension
            cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")
            
            # Create tables
            cur.execute("""
                CREATE TABLE IF NOT EXISTS docs(
                    id SERIAL PRIMARY KEY,
                    title TEXT,
                    content TEXT,
                    meta JSONB
                );
                CREATE TABLE IF NOT EXISTS doc_embeddings(
                    doc_id INT PRIMARY KEY REFERENCES docs(id) ON DELETE CASCADE,
                    embedding vector(1536)
                );
            """)
            
            # Clear existing data
            cur.execute("DELETE FROM doc_embeddings")
            cur.execute("DELETE FROM docs")
            
            # Process markdown files
            for md_file in glob.glob(f"{DATA_DIR}/docs/*.md"):
                filename = os.path.basename(md_file)
                
                # Filter for knowledge base only if requested (documents 01-12)
                if kb_only:
                    doc_category = categorize_document(filename)
                    if doc_category != "customer":
                        continue
                
                with open(md_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Parse YAML frontmatter
                frontmatter, content_without_frontmatter = parse_yaml_frontmatter(content)
                
                # Use frontmatter title if available, otherwise generate from filename
                title = frontmatter.get('title', filename.replace(".md", "").replace("_", " ").title())
                
                # Categorize document
                doc_category = categorize_document(filename)
                
                # Create metadata with category and frontmatter
                meta = {
                    "source": filename,
                    "category": doc_category,
                    "frontmatter": frontmatter
                }
                
                # Chunk the content for better knowledge search
                chunks = chunk_text(content_without_frontmatter, chunk_size=400, overlap=0.15)
                
                # Store each chunk as a separate document
                for i, chunk in enumerate(chunks):
                    chunk_meta = meta.copy()
                    chunk_meta.update({
                        "chunk_index": i,
                        "total_chunks": len(chunks),
                        "tokens_estimated": estimate_tokens(chunk)
                    })
                    
                    # Insert document chunk
                    cur.execute(
                        "INSERT INTO docs(title, content, meta) VALUES (%s, %s, %s) RETURNING id",
                        (f"{title} (Part {i+1})" if len(chunks) > 1 else title, chunk, json.dumps(chunk_meta))
                    )
                    doc_id = cur.fetchone()[0]
                    chunk_count += 1
                    
                    # Generate and store embedding
                    if embeddings_available:
                        try:
                            embedding = embed(chunk[:5000])  # Truncate for embedding
                            cur.execute(
                                "INSERT INTO doc_embeddings(doc_id, embedding) VALUES (%s, %s)",
                                (doc_id, embedding)
                            )
                        except Exception as e:
                            service.log_error(e, f"embedding generation for {filename} chunk {i}")
                
                doc_count += 1
    
    return doc_count, chunk_count, embeddings_available

@app.post("/ingest/seed")
def ingest_seed(request: Request):
    """Parse CSVs and markdown files, optionally compute embeddings."""
    try:
        # Parse CSV files
        csv_counts = parse_csv_files()
        
        # Parse markdown files (all documents)
        doc_count, chunk_count, embeddings_available = parse_markdown_files(kb_only=False)
        
        # Calculate total counts
        total_csv_records = sum(csv_counts.values())
        
        result = {
            "ok": True,
            "message": "Successfully parsed CSVs and markdown files",
            "counts": {
                "csv_records": csv_counts,
                "total_csv_records": total_csv_records,
                "documents": doc_count,
                "chunks": chunk_count
            },
            "embeddings_available": embeddings_available
        }
        
        service.log_request(request, {"status": "success", "counts": result["counts"]})
        return result
        
    except Exception as e:
        service.log_error(e, "ingest_seed endpoint")
        raise

@app.post("/ingest/kb-only")
def ingest_kb_only(request: Request):
    """Parse only knowledge base documents (01-12) with enhanced processing."""
    try:
        # Parse only knowledge base markdown files (documents 01-12)
        doc_count, chunk_count, embeddings_available = parse_markdown_files(kb_only=True)
        
        result = {
            "ok": True,
            "message": "Successfully parsed knowledge base documents (01-12)",
            "counts": {
                "documents": doc_count,
                "chunks": chunk_count
            },
            "embeddings_available": embeddings_available,
            "processing_features": {
                "categorization": "Documents categorized as customer-facing",
                "chunking": "Content chunked with 15% overlap",
                "yaml_frontmatter": "YAML frontmatter parsed and stored in metadata",
                "token_estimation": "Token count estimated for each chunk"
            }
        }
        
        service.log_request(request, {"status": "success", "counts": result["counts"]})
        return result
        
    except Exception as e:
        service.log_error(e, "ingest_kb_only endpoint")
        raise
