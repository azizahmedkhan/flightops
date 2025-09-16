import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'shared'))

from base_service import BaseService
from fastapi import Request
from pydantic import BaseModel
import json, math
from typing import List, Dict, Any
import psycopg
import httpx
from utils import REQUEST_COUNT, LATENCY, log_startup
from contextlib import asynccontextmanager

# Initialize base service
service = BaseService("retrieval-svc", "1.0.0")

# Get environment variables using the base service
DB_HOST = service.get_env_var("DB_HOST", "localhost")
DB_PORT = service.get_env_int("DB_PORT", 5432)
DB_NAME = service.get_env_var("DB_NAME", "flightops")
DB_USER = service.get_env_var("DB_USER", "postgres")
DB_PASS = service.get_env_var("DB_PASS", "postgres")
EMBEDDINGS_MODEL = service.get_env_var("EMBEDDINGS_MODEL", "text-embedding-3-small")
OPENAI_API_KEY = service.get_env_var("OPENAI_API_KEY", "")

@asynccontextmanager
async def lifespan(app):
    log_startup("retrieval-svc")
    # init tables
    with psycopg.connect(host=DB_HOST,port=DB_PORT,dbname=DB_NAME,user=DB_USER,password=DB_PASS,autocommit=True) as conn:
        with conn.cursor() as cur:
            cur.execute("""
            CREATE TABLE IF NOT EXISTS docs(
              id SERIAL PRIMARY KEY,
              title TEXT,
              content TEXT,
              meta JSONB
            );
            CREATE EXTENSION IF NOT EXISTS vector;
            CREATE TABLE IF NOT EXISTS doc_embeddings(
              doc_id INT REFERENCES docs(id) ON DELETE CASCADE,
              embedding vector(1536)
            );
            """)
    yield

# Create app with lifespan
app = service.get_app()
app.router.lifespan_context = lifespan

class Query(BaseModel):
    q: str
    k: int = 5

def embed(text: str):
    # try OpenAI embeddings first; fallback to naive hash vector
    if OPENAI_API_KEY:
        try:
            from openai import OpenAI
            client = OpenAI(api_key=OPENAI_API_KEY)
            resp = client.embeddings.create(input=[text], model=EMBEDDINGS_MODEL)
            return resp.data[0].embedding
        except Exception as e:
            service.log_error(e, "embedding generation")
            pass
    # fallback: simple hashed vector of 1536 dims
    import random, hashlib
    random.seed(int(hashlib.md5(text.encode()).hexdigest(), 16))
    return [random.random() for _ in range(1536)]

@app.post("/search")
def search(q: Query, request: Request):
    from time import time as now
    with LATENCY.labels("retrieval-svc","/search","POST").time():
        try:
            vec = embed(q.q)
            with psycopg.connect(host=DB_HOST,port=DB_PORT,dbname=DB_NAME,user=DB_USER,password=DB_PASS) as conn:
                with conn.cursor() as cur:
                    # If vector table empty, fallback to keyword
                    cur.execute("SELECT COUNT(*) FROM doc_embeddings")
                    cnt = cur.fetchone()[0]
                    if cnt == 0:
                        cur.execute("""
                        SELECT id,title,content,meta
                        FROM docs
                        WHERE content ILIKE %s OR title ILIKE %s
                        LIMIT %s
                        """, (f"%{q.q}%", f"%{q.q}%", q.k))
                        rows = cur.fetchall()
                        results = []
                        for id_, title, content, meta in rows:
                            results.append({"doc_id": id_, "title": title, "snippet": content[:300], "meta": meta or {}})
                        result = {"mode":"keyword","results":results}
                    else:
                        # vector search
                        # upsert temp query embedding
                        cur.execute("CREATE TEMP TABLE tmp(q vector(1536));")
                        cur.execute("INSERT INTO tmp VALUES (%s)", (vec,))
                        cur.execute("""
                            SELECT d.id, d.title, d.content, d.meta,
                                   1 - (de.embedding <#> t.q) AS score
                            FROM doc_embeddings de, docs d, tmp t
                            WHERE d.id = de.doc_id
                            ORDER BY de.embedding <-> t.q
                            LIMIT %s
                        """, (q.k,))
                        rows = cur.fetchall()
                        results = [{"doc_id": r[0], "title": r[1], "snippet": r[2][:300], "meta": r[3] or {}, "score": float(r[4])} for r in rows]
                        result = {"mode":"vector","results":results}
            
            service.log_request(request, {"status": "success"})
            return result
        except Exception as e:
            service.log_error(e, "search endpoint")
            raise