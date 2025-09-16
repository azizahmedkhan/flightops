import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'shared'))

from base_service import BaseService
from fastapi import Request
from pydantic import BaseModel
import json, csv, glob
import psycopg
from utils import log_startup
from typing import Dict, List, Tuple, Optional

# Initialize base service
service = BaseService("ingest-svc", "1.0.0")
app = service.get_app()

# Get environment variables using the base service
DB_HOST = service.get_env_var("DB_HOST", "localhost")
DB_PORT = service.get_env_int("DB_PORT", 5432)
DB_NAME = service.get_env_var("DB_NAME", "flightops")
DB_USER = service.get_env_var("DB_USER", "postgres")
DB_PASS = service.get_env_var("DB_PASS", "postgres")
OPENAI_API_KEY = service.get_env_var("OPENAI_API_KEY", "")
EMBEDDINGS_MODEL = service.get_env_var("EMBEDDINGS_MODEL", "text-embedding-3-small")

DATA_DIR = "/data"

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

def parse_csv_files() -> Dict[str, int]:
    """Parse CSV files and return counts of loaded records."""
    counts = {}
    
    with psycopg.connect(host=DB_HOST, port=DB_PORT, dbname=DB_NAME, user=DB_USER, password=DB_PASS, autocommit=True) as conn:
        with conn.cursor() as cur:
            # Drop existing tables to recreate with new structure
            cur.execute("DROP TABLE IF EXISTS flights CASCADE")
            cur.execute("DROP TABLE IF EXISTS bookings CASCADE")
            cur.execute("DROP TABLE IF EXISTS crew_roster CASCADE")
            cur.execute("DROP TABLE IF EXISTS crew_details CASCADE")
            cur.execute("DROP TABLE IF EXISTS aircraft_status CASCADE")
            
            # Create tables with new structure
            cur.execute("""
                CREATE TABLE flights(
                    flight_no TEXT,
                    flight_date TEXT,
                    origin TEXT,
                    destination TEXT,
                    sched_dep_time TEXT,
                    sched_arr_time TEXT,
                    status TEXT,
                    tail_number TEXT
                );
                CREATE TABLE bookings(
                    flight_no TEXT,
                    flight_date TEXT,
                    pnr TEXT,
                    passenger_name TEXT,
                    has_connection TEXT,
                    connecting_flight_no TEXT
                );
                CREATE TABLE crew_roster(
                    flight_no TEXT,
                    flight_date TEXT,
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
            """)
            
            # Load each CSV
            for table_name in ["flights", "bookings", "crew_roster", "crew_details", "aircraft_status"]:
                path = f"{DATA_DIR}/csv/{table_name}.csv"
                if os.path.exists(path):
                    with open(path, newline='') as f:
                        reader = csv.DictReader(f)
                        rows = [tuple(d.values()) for d in reader]
                    
                    # Clear existing data
                    cur.execute(f"DELETE FROM {table_name}")
                    
                    # Insert new data
                    if rows:
                        placeholders = ",".join(["(" + ",".join(["%s"]*len(rows[0])) + ")"]*len(rows))
                        flat = [x for row in rows for x in row]
                        cur.execute(f"INSERT INTO {table_name} VALUES {placeholders}", flat)
                        counts[table_name] = len(rows)
                    else:
                        counts[table_name] = 0
                else:
                    service.log_error(f"CSV file not found: {path}", "parse_csv_files")
                    counts[table_name] = 0
    
    return counts

def parse_markdown_files() -> Tuple[int, bool]:
    """Parse markdown policy files and return count of loaded docs and embeddings availability."""
    doc_count = 0
    embeddings_available = bool(OPENAI_API_KEY)
    
    with psycopg.connect(host=DB_HOST, port=DB_PORT, dbname=DB_NAME, user=DB_USER, password=DB_PASS, autocommit=True) as conn:
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
                    doc_id INT REFERENCES docs(id) ON DELETE CASCADE,
                    embedding vector(1536)
                );
            """)
            
            # Clear existing data
            cur.execute("DELETE FROM doc_embeddings")
            cur.execute("DELETE FROM docs")
            
            # Process markdown files
            for md_file in glob.glob(f"{DATA_DIR}/docs/*.md"):
                title = os.path.basename(md_file).replace(".md", "").replace("_", " ").title()
                with open(md_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Insert document
                cur.execute(
                    "INSERT INTO docs(title, content, meta) VALUES (%s, %s, %s) RETURNING id",
                    (title, content, json.dumps({"source": os.path.basename(md_file)}))
                )
                doc_id = cur.fetchone()[0]
                doc_count += 1
                
                # Generate and store embedding
                embedding = embed(content[:5000])  # Truncate for embedding
                cur.execute(
                    "INSERT INTO doc_embeddings(doc_id, embedding) VALUES (%s, %s)",
                    (doc_id, embedding)
                )
    
    return doc_count, embeddings_available

@app.post("/ingest/seed")
def ingest_seed(request: Request):
    """Parse CSVs and markdown files, optionally compute embeddings."""
    try:
        # Parse CSV files
        csv_counts = parse_csv_files()
        
        # Parse markdown files
        doc_count, embeddings_available = parse_markdown_files()
        
        # Calculate total counts
        total_csv_records = sum(csv_counts.values())
        
        result = {
            "ok": True,
            "message": "Successfully parsed CSVs and markdown files",
            "counts": {
                "csv_records": csv_counts,
                "total_csv_records": total_csv_records,
                "documents": doc_count
            },
            "embeddings_available": embeddings_available
        }
        
        service.log_request(request, {"status": "success", "counts": result["counts"]})
        return result
        
    except Exception as e:
        service.log_error(e, "ingest_seed endpoint")
        raise