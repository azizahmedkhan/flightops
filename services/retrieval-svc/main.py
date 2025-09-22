import sys
import os
import json
import math
import re
from contextlib import asynccontextmanager
from typing import List, Dict, Any, Tuple

import httpx
import psycopg
from fastapi import Request
from pydantic import BaseModel
from psycopg_pool import ConnectionPool
from rank_bm25 import BM25Okapi

sys.path.append(os.path.join(os.path.dirname(__file__), 'shared'))

from base_service import BaseService
from utils import REQUEST_COUNT, LATENCY, log_startup

# Initialize base service
service = BaseService("retrieval-svc", "1.0.0")

# Get environment variables using the base service
DB_HOST = service.get_env_var("DB_HOST", "db")
DB_PORT = service.get_env_int("DB_PORT", 5432)
DB_NAME = service.get_env_var("DB_NAME", "flightops")
DB_USER = service.get_env_var("DB_USER", "postgres")
DB_PASS = service.get_env_var("DB_PASS", "postgres")
EMBEDDINGS_MODEL = service.get_env_var("EMBEDDINGS_MODEL", "text-embedding-3-small")
OPENAI_API_KEY = service.get_env_var("OPENAI_API_KEY", "")

# Create database connection pool
DB_CONN_STRING = f"host={DB_HOST} port={DB_PORT} dbname={DB_NAME} user={DB_USER} password={DB_PASS}"
db_pool = None

@asynccontextmanager
async def lifespan(app):
    global db_pool
    log_startup("retrieval-svc")
    
    # Initialize connection pool
    db_pool = ConnectionPool(DB_CONN_STRING, min_size=2, max_size=10)
    
    # init tables
    with db_pool.connection() as conn:
        conn.autocommit = True
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
    
    # Close connection pool on shutdown
    if db_pool:
        db_pool.close()

# Create app with lifespan
app = service.get_app()
app.router.lifespan_context = lifespan

class Query(BaseModel):
    q: str
    k: int = 5

def embed(text: str) -> List[float]:
    """Generate embeddings using OpenAI API."""
    try:
        from openai import OpenAI
        client = OpenAI(api_key=OPENAI_API_KEY)
        resp = client.embeddings.create(input=[text], model=EMBEDDINGS_MODEL)
        return resp.data[0].embedding
    except Exception as e:
        service.log_error(e, "embedding generation")
        raise e

def tokenize(text: str) -> List[str]:
    """Simple tokenization for BM25."""
    return re.findall(r'\b\w+\b', text.lower())

def get_bm25_scores(query: str, documents: List[Dict[str, Any]]) -> List[Tuple[int, float]]:
    """Get BM25 scores for documents given a query."""
    if not documents:
        return []
    
    # Tokenize documents and query
    doc_tokens = [tokenize(doc['content']) for doc in documents]
    query_tokens = tokenize(query)
    
    # Create BM25 index
    bm25 = BM25Okapi(doc_tokens)
    
    # Get scores
    scores = bm25.get_scores(query_tokens)
    
    # Return (doc_id, score) pairs
    return [(doc['doc_id'], float(score)) for doc, score in zip(documents, scores)]

def get_vector_scores(query: str, k: int, category: str = None) -> List[Tuple[int, float]]:
    """Get vector similarity scores using pgvector with optional category filtering."""
    try:
        vec = embed(query)
        
        with db_pool.connection() as conn:
            with conn.cursor() as cur:
                # Check if embeddings are available
                cur.execute("SELECT COUNT(*) FROM doc_embeddings")
                cnt = cur.fetchone()[0]
                
                if cnt == 0:
                    return []
                
                # Create temp table for query vector
                try:
                    cur.execute("CREATE TEMP TABLE tmp_query(q vector(1536));")
                    cur.execute("INSERT INTO tmp_query VALUES (%s)", (vec,))
                except Exception as e:
                    service.log_error(e, "pgvector extension not available")
                    return []
                
                # Build query with optional category filtering
                if category:
                    cur.execute("""
                        SELECT d.id, 
                               CASE 
                                   WHEN de.embedding <#> t.q IS NOT NULL 
                                   THEN 1 - (de.embedding <#> t.q)
                                   ELSE 0.0
                               END AS score
                        FROM doc_embeddings de, docs d, tmp_query t
                        WHERE d.id = de.doc_id AND d.meta->>'category' = %s
                        ORDER BY de.embedding <-> t.q
                        LIMIT %s
                    """, (category, k))
                else:
                    cur.execute("""
                        SELECT d.id, 
                               CASE 
                                   WHEN de.embedding <#> t.q IS NOT NULL 
                                   THEN 1 - (de.embedding <#> t.q)
                                   ELSE 0.0
                               END AS score
                        FROM doc_embeddings de, docs d, tmp_query t
                        WHERE d.id = de.doc_id
                        ORDER BY de.embedding <-> t.q
                        LIMIT %s
                    """, (k,))
                
                results = []
                for row in cur.fetchall():
                    doc_id = row[0]
                    score = row[1] if row[1] is not None else 0.0
                    try:
                        results.append((doc_id, float(score)))
                    except (ValueError, TypeError):
                        results.append((doc_id, 0.0))
                
                return results
                
    except Exception as e:
        service.log_error(e, "vector_scores")
        return []

def hybrid_search(query: str, k: int = 5, category: str = None) -> List[Dict[str, Any]]:
    """Perform hybrid search combining BM25 and vector search with optional category filtering."""
    with db_pool.connection() as conn:
        with conn.cursor() as cur:
            # Build query with optional category filtering
            if category:
                cur.execute("SELECT id, title, content, meta FROM docs WHERE meta->>'category' = %s", (category,))
            else:
                cur.execute("SELECT id, title, content, meta FROM docs")
            
            docs = []
            for row in cur.fetchall():
                docs.append({
                    'doc_id': row[0],
                    'title': row[1],
                    'content': row[2],
                    'meta': row[3] or {}
                })
            
            if not docs:
                return []
            
            # Get BM25 scores
            bm25_scores = get_bm25_scores(query, docs)
            
            # Get vector scores with category filtering
            vector_scores = get_vector_scores(query, k * 2, category)  # Get more for better merging
            
            # Normalize scores (simple min-max normalization)
            def normalize_scores(scores):
                if not scores:
                    return {}
                min_score = min(score for _, score in scores)
                max_score = max(score for _, score in scores)
                if max_score == min_score:
                    return {doc_id: 1.0 for doc_id, _ in scores}
                return {doc_id: (score - min_score) / (max_score - min_score) 
                       for doc_id, score in scores}
            
            bm25_normalized = normalize_scores(bm25_scores)
            vector_normalized = normalize_scores(vector_scores)
            
            # Combine scores (equal weight for now)
            combined_scores = {}
            all_doc_ids = set(bm25_normalized.keys()) | set(vector_normalized.keys())
            
            for doc_id in all_doc_ids:
                bm25_score = bm25_normalized.get(doc_id, 0.0)
                vector_score = vector_normalized.get(doc_id, 0.0)
                combined_scores[doc_id] = 0.5 * bm25_score + 0.5 * vector_score
            
            # Sort by combined score and get top k
            sorted_docs = sorted(combined_scores.items(), key=lambda x: x[1], reverse=True)[:k]
            
            # Build results
            results = []
            doc_lookup = {doc['doc_id']: doc for doc in docs}
            
            for doc_id, score in sorted_docs:
                doc = doc_lookup[doc_id]
                results.append({
                    'doc_id': doc_id,
                    'title': doc['title'],
                    'snippet': doc['content'][:300] + '...' if len(doc['content']) > 300 else doc['content'],
                    'score': score,
                    'source': doc['meta'].get('source', 'unknown'),
                    'category': doc['meta'].get('category', 'unknown'),
                    'chunk_index': doc['meta'].get('chunk_index'),
                    'total_chunks': doc['meta'].get('total_chunks')
                })
            
            return results

@app.post("/search")
def search(q: Query, request: Request):
    """Hybrid search endpoint combining BM25 and vector search."""
    with LATENCY.labels("retrieval-svc","/search","POST").time():
        try:
            # Perform hybrid search
            results = hybrid_search(q.q, q.k)
            
            # Determine search mode based on available data
            with db_pool.connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT COUNT(*) FROM doc_embeddings")
                    embeddings_count = cur.fetchone()[0]
                    cur.execute("SELECT COUNT(*) FROM docs")
                    docs_count = cur.fetchone()[0]
            
            if embeddings_count > 0:
                mode = "hybrid"
            elif docs_count > 0:
                mode = "bm25_only"
            else:
                mode = "no_data"
            
            result = {
                "mode": mode,
                "results": results,
                "embeddings_available": embeddings_count > 0
            }
            
            service.log_request(request, {"status": "success", "mode": mode, "result_count": len(results)})
            return result
            
        except Exception as e:
            service.log_error(e, "search endpoint")
            raise

@app.post("/kb/search")
def kb_search(q: Query, request: Request):
    """Knowledge base search endpoint - searches all documents."""
    with LATENCY.labels("retrieval-svc","/kb/search","POST").time():
        try:
            # Perform hybrid search across all documents
            results = hybrid_search(q.q, q.k)
            
            # Get counts by category
            with db_pool.connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT COUNT(*) FROM doc_embeddings")
                    embeddings_count = cur.fetchone()[0]
                    cur.execute("SELECT COUNT(*) FROM docs")
                    docs_count = cur.fetchone()[0]
                    cur.execute("SELECT meta->>'category' as category, COUNT(*) FROM docs GROUP BY meta->>'category'")
                    category_counts = {row[0] or 'unknown': row[1] for row in cur.fetchall()}
            
            if embeddings_count > 0:
                mode = "hybrid"
            elif docs_count > 0:
                mode = "bm25_only"
            else:
                mode = "no_data"
            
            result = {
                "mode": mode,
                "results": results,
                "embeddings_available": embeddings_count > 0,
                "category_counts": category_counts,
                "total_documents": docs_count
            }
            
            service.log_request(request, {"status": "success", "mode": mode, "result_count": len(results)})
            return result
            
        except Exception as e:
            service.log_error(e, "kb_search endpoint")
            raise

@app.post("/kb/search/customer")
def kb_search_customer(q: Query, request: Request):
    """Knowledge base search endpoint - searches only customer-facing documents (01-12)."""
    with LATENCY.labels("retrieval-svc","/kb/search/customer","POST").time():
        try:
            # Perform hybrid search on customer-facing documents only
            results = hybrid_search(q.q, q.k, category="customer")
            
            # Get counts for customer documents
            with db_pool.connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT COUNT(*) FROM doc_embeddings de, docs d WHERE d.id = de.doc_id AND d.meta->>'category' = 'customer'")
                    embeddings_count = cur.fetchone()[0]
                    cur.execute("SELECT COUNT(*) FROM docs WHERE meta->>'category' = 'customer'")
                    docs_count = cur.fetchone()[0]
            
            if embeddings_count > 0:
                mode = "hybrid"
            elif docs_count > 0:
                mode = "bm25_only"
            else:
                mode = "no_data"
            
            result = {
                "mode": mode,
                "results": results,
                "embeddings_available": embeddings_count > 0,
                "category": "customer",
                "total_documents": docs_count
            }
            
            service.log_request(request, {"status": "success", "mode": mode, "result_count": len(results)})
            return result
            
        except Exception as e:
            service.log_error(e, "kb_search_customer endpoint")
            raise

@app.post("/kb/search/operational")
def kb_search_operational(q: Query, request: Request):
    """Knowledge base search endpoint - searches only operational documents (13-17)."""
    with LATENCY.labels("retrieval-svc","/kb/search/operational","POST").time():
        try:
            # Perform hybrid search on operational documents only
            results = hybrid_search(q.q, q.k, category="operational")
            
            # Get counts for operational documents
            with db_pool.connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT COUNT(*) FROM doc_embeddings de, docs d WHERE d.id = de.doc_id AND d.meta->>'category' = 'operational'")
                    embeddings_count = cur.fetchone()[0]
                    cur.execute("SELECT COUNT(*) FROM docs WHERE meta->>'category' = 'operational'")
                    docs_count = cur.fetchone()[0]
            
            if embeddings_count > 0:
                mode = "hybrid"
            elif docs_count > 0:
                mode = "bm25_only"
            else:
                mode = "no_data"
            
            result = {
                "mode": mode,
                "results": results,
                "embeddings_available": embeddings_count > 0,
                "category": "operational",
                "total_documents": docs_count
            }
            
            service.log_request(request, {"status": "success", "mode": mode, "result_count": len(results)})
            return result
            
        except Exception as e:
            service.log_error(e, "kb_search_operational endpoint")
            raise