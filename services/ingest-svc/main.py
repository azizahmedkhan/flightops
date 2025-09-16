import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'shared'))

from base_service import BaseService
from fastapi import Request
from pydantic import BaseModel
import json, csv, glob
import psycopg
from utils import log_startup

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

def embed(text: str):
    if OPENAI_API_KEY:
        try:
            from openai import OpenAI
            client = OpenAI(api_key=OPENAI_API_KEY)
            resp = client.embeddings.create(input=[text], model=EMBEDDINGS_MODEL)
            return resp.data[0].embedding
        except Exception as e:
            service.log_error(e, "embedding generation")
            pass
    # fallback: deterministic fake vector
    import random, hashlib
    random.seed(int(hashlib.md5(text.encode()).hexdigest(), 16))
    return [random.random() for _ in range(1536)]

@app.post("/ingest/seed")
def ingest_seed(request: Request):
    try:
        with psycopg.connect(host=DB_HOST,port=DB_PORT,dbname=DB_NAME,user=DB_USER,password=DB_PASS,autocommit=True) as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS flights(
                      flight_no TEXT,
                      flight_date TEXT,
                      origin TEXT,
                      destination TEXT,
                      sched_dep TEXT,
                      sched_arr TEXT,
                      status TEXT
                    );
                    CREATE TABLE IF NOT EXISTS bookings(
                      flight_no TEXT,
                      flight_date TEXT,
                      pnr TEXT
                    );
                    CREATE TABLE IF NOT EXISTS crew_roster(
                      flight_no TEXT,
                      flight_date TEXT,
                      crew_id TEXT
                    );
                """)
                # load CSVs
                for name in ["flights","bookings","crew_roster"]:
                    path = f"{DATA_DIR}/csv/{name}.csv"
                    with open(path, newline='') as f:
                        reader = csv.DictReader(f)
                        rows = [tuple(d.values()) for d in reader]
                    cur.execute(f"DELETE FROM {name}")
                    placeholders = ",".join(["(" + ",".join(["%s"]*len(rows[0])) + ")"]*len(rows)) if rows else ""
                    if rows:
                        flat = [x for row in rows for x in row]
                        cur.execute(f"INSERT INTO {name} VALUES {placeholders}", flat)

                # docs
                cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")
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
                # clear and reinsert
                cur.execute("DELETE FROM doc_embeddings")
                cur.execute("DELETE FROM docs")
                for md in glob.glob(f"{DATA_DIR}/docs/*.md"):
                    title = os.path.basename(md).replace(".md","").replace("_"," ").title()
                    with open(md) as f:
                        content = f.read()
                    cur.execute("INSERT INTO docs(title,content,meta) VALUES (%s,%s,%s) RETURNING id", (title, content, json.dumps({"source": os.path.basename(md)})))
                    doc_id = cur.fetchone()[0]
                    vec = embed(content[:5000])
                    cur.execute("INSERT INTO doc_embeddings(doc_id,embedding) VALUES (%s,%s)", (doc_id, vec))

        result = {"ok": True, "message": "Seeded CSVs and embedded docs."}
        service.log_request(request, {"status": "success"})
        return result
    except Exception as e:
        service.log_error(e, "ingest_seed endpoint")
        raise