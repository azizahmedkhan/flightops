"""
Main FastAPI application for db-router-svc.

This service provides natural language to database query routing
with safe, parameterized SQL execution.
"""

import os
import asyncio
from datetime import datetime
from contextlib import asynccontextmanager
from typing import Dict, Any, List, Tuple
from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from loguru import logger
import uvicorn
import httpx

from models import (
    RouteRequest, RouteResponse, SmartQueryRequest, SmartQueryResponse,
    HealthResponse, Intent
)
from router import QueryRouter
from execute import (
    initialize_database, close_database, execute_intent_query,
    get_database_health, validate_intent_args
)
from util import format_datetime_for_display, get_city_name
from services.shared.llm_client import LLMClient
from services.shared.base_service import BaseService


# Global instances
llm_client: LLMClient = None
query_router: QueryRouter = None
base_service: BaseService = None

RETRIEVAL_SVC_URL = os.getenv("RETRIEVAL_SVC_URL", "http://knowledge-engine:8081")
try:
    DEFAULT_KB_TOP_K = int(os.getenv("KB_TOP_K", "5"))
except ValueError:
    DEFAULT_KB_TOP_K = 5


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    global llm_client, query_router, base_service
    
    # Startup
    logger.info("Starting db-router-svc")
    
    try:
        # Initialize base service
        base_service = BaseService("db-router-svc")

        # Initialize LLM client
        llm_client = LLMClient("db-router-svc")

        # Initialize query router
        query_router = QueryRouter(llm_client)

        # Configure retrieval service for knowledge base lookups
        global RETRIEVAL_SVC_URL, DEFAULT_KB_TOP_K
        RETRIEVAL_SVC_URL = base_service.get_env_var("RETRIEVAL_SVC_URL", RETRIEVAL_SVC_URL)
        try:
            DEFAULT_KB_TOP_K = int(base_service.get_env_var("KB_TOP_K", str(DEFAULT_KB_TOP_K)))
        except ValueError:
            DEFAULT_KB_TOP_K = 5
        logger.info(
            f"Knowledge base retrieval configured: url={RETRIEVAL_SVC_URL}, default_top_k={DEFAULT_KB_TOP_K}"
        )

        # Initialize database
        database_url = os.getenv("DATABASE_URL", "postgresql://user:password@localhost:5432/flightops")
        await initialize_database(database_url)
        
        logger.info("db-router-svc startup complete")
        
    except Exception as e:
        logger.error(f"Failed to start db-router-svc: {e}")
        raise
    
    yield
    
    # Shutdown
    logger.info("Shutting down db-router-svc")
    
    try:
        await close_database()
        if base_service:
            await base_service.close()
        logger.info("db-router-svc shutdown complete")
    except Exception as e:
        logger.error(f"Error during shutdown: {e}")


# Create FastAPI app
app = FastAPI(
    title="Database Router Service",
    description="Natural language to database query routing service",
    version="1.0.0",
    lifespan=lifespan
)

# Add middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["*"]  # Configure appropriately for production
)


def get_llm_client() -> LLMClient:
    """Get LLM client instance."""
    if not llm_client:
        raise HTTPException(status_code=503, detail="LLM client not initialized")
    return llm_client


def get_query_router() -> QueryRouter:
    """Get query router instance."""
    if not query_router:
        raise HTTPException(status_code=503, detail="Query router not initialized")
    return query_router


async def query_knowledge_base(query: str, top_k: int = DEFAULT_KB_TOP_K) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """Call retrieval service to fetch knowledge base snippets."""
    sanitized_query = (query or "").strip()
    if not sanitized_query:
        return [], {"mode": "empty", "embeddings_available": False}

    try:
        bounded_top_k = max(1, min(int(top_k), 20))
    except (TypeError, ValueError):
        bounded_top_k = DEFAULT_KB_TOP_K

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                f"{RETRIEVAL_SVC_URL}/kb/search",
                json={"q": sanitized_query, "k": bounded_top_k}
            )
            response.raise_for_status()
            data = response.json()
    except httpx.HTTPError as exc:
        logger.error(f"Knowledge base search HTTP error: {exc}")
        return [], {"mode": "error", "error": str(exc)}
    except Exception as exc:
        logger.error(f"Knowledge base search failed: {exc}")
        return [], {"mode": "error", "error": str(exc)}

    results = data.get("results", []) if isinstance(data, dict) else []
    metadata = {
        "mode": data.get("mode") if isinstance(data, dict) else None,
        "embeddings_available": data.get("embeddings_available") if isinstance(data, dict) else None,
        "total_documents": data.get("total_documents") if isinstance(data, dict) else None,
        "category_counts": data.get("category_counts") if isinstance(data, dict) else None
    }
    return results, metadata


def format_knowledge_base_answer(rows: List[Dict[str, Any]]) -> str:
    """Create a grounded response from knowledge base snippets."""
    if not rows:
        return (
            "I couldn't find any matching policy information in the knowledge base right now.\n"
            "Please contact our support team if you need more detailed guidance."
        )

    bullets = []
    citations = []
    for index, row in enumerate(rows, start=1):
        snippet = (row.get("snippet") or row.get("content") or "").strip()
        if snippet:
            bullets.append(f"- {snippet}")
        else:
            bullets.append("- Reference policy found, but no summary snippet available.")

        title = (row.get("title") or row.get("source") or "Policy reference").strip()
        category = (row.get("category") or "general").strip()
        citations.append(f"[{index}] {title} ({category})")

    response_parts = ["\n".join(bullets)]
    if citations:
        response_parts.append("")
        response_parts.append("Sources:")
        response_parts.extend(citations)

    return "\n".join(part for part in response_parts if part).strip()


async def format_query_answer(
    intent: Intent,
    args: Dict[str, Any],
    rows: List[Dict[str, Any]],
    llm_client: LLMClient
) -> str:
    """
    Format database results into a natural language answer.
    
    Args:
        intent: Query intent
        args: Query arguments
        rows: Database results
        llm_client: LLM client for formatting
        
    Returns:
        Formatted answer string
    """
    if intent == Intent.KNOWLEDGE_BASE:
        return format_knowledge_base_answer(rows)

    if not rows:
        return "No results found for your query."
    
    # Create context for LLM formatting
    context = {
        "intent": intent.value,
        "args": args,
        "row_count": len(rows),
        "results": rows[:10]  # Limit to first 10 rows for context
    }
    
    # Create formatting prompt
    system_prompt = """You are a helpful airline assistant. Format database query results into a clear, 
    concise answer for the user. Use the following guidelines:
    
    1. Use 2-4 bullet points maximum
    2. No promises or guarantees unless explicitly stated in the data
    3. Show times in Pacific/Auckland timezone for user display
    4. Be factual and direct
    5. If no results, clearly state that
    6. Don't make up information not in the data
    
    Database results are provided as ground truth - use them exactly as shown."""
    
    user_prompt = f"""Please format these database results into a helpful answer:
    
    Query Intent: {context['intent']}
    Query Arguments: {context['args']}
    Number of Results: {context['row_count']}
    
    Results:
    {context['results']}
    
    Format this into a clear, helpful response for the user."""
    
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ]

    try:
        response = await asyncio.to_thread(
            llm_client.chat_completion,
            messages=messages,
            temperature=0.2,
            max_tokens=500,
            function_name="format_query_answer",
            metadata={
                "intent": intent.value,
                "row_count": len(rows)
            }
        )

        if isinstance(response, dict):
            content = response.get("content", "")
        else:
            content = str(response)

        content = content.strip()
        if content:
            return content

        raise ValueError("LLM returned empty content")

    except Exception as e:
        logger.error(f"Failed to format answer: {e}")
        # Fallback to simple formatting
        return (
            f"Found {len(rows)} result(s) for your query. "
            "Please check the detailed results below."
        )


@app.get("/healthz", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    try:
        db_health = await get_database_health()
        
        if db_health["status"] == "healthy":
            return HealthResponse(
                status="healthy",
                timestamp=datetime.now()
            )
        else:
            return HealthResponse(
                status="unhealthy",
                timestamp=datetime.now()
            )
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return HealthResponse(
            status="unhealthy",
            timestamp=datetime.now()
        )


@app.post("/route", response_model=RouteResponse)
async def route_query(
    request: RouteRequest,
    router: QueryRouter = Depends(get_query_router)
):
    """
    Route a natural language query to the appropriate database intent.
    
    This endpoint uses LLM function calling to determine the intent and extract arguments.
    """
    try:
        logger.info(f"Routing query: {request.text[:100]}...")
        
        response = await router.route_query(request.text)
        
        logger.info(f"Routed to {response.intent} with confidence {response.confidence}")
        return response
        
    except Exception as e:
        logger.error(f"Query routing failed: {e}")
        raise HTTPException(status_code=500, detail=f"Query routing failed: {str(e)}")


@app.post("/smart-query", response_model=SmartQueryResponse)
async def smart_query(
    request: SmartQueryRequest,
    router: QueryRouter = Depends(get_query_router),
    llm_client: LLMClient = Depends(get_llm_client)
):
    """
    Execute a smart query: route -> execute -> format.
    
    This is the main endpoint that combines routing, execution, and formatting.
    """
    try:
        logger.info(f"Processing smart query: {request.text[:100]}...")
        
        # Step 1: Route the query
        route_response = await router.route_query(request.text)

        # Knowledge base queries bypass SQL execution and use embeddings search
        if route_response.intent == Intent.KNOWLEDGE_BASE:
            kb_args = dict(route_response.args)
            query_text = kb_args.get("query") or request.text

            try:
                parsed_top_k = int(kb_args.get("k", DEFAULT_KB_TOP_K))
            except (TypeError, ValueError):
                parsed_top_k = DEFAULT_KB_TOP_K

            bounded_top_k = max(1, min(parsed_top_k, 20))

            kb_rows, retrieval_meta = await query_knowledge_base(query_text, bounded_top_k)
            kb_args.setdefault("query", query_text)
            kb_args["k"] = bounded_top_k

            answer = await format_query_answer(
                route_response.intent,
                kb_args,
                kb_rows,
                llm_client
            )

            metadata = {
                "row_count": len(kb_rows),
                "confidence": route_response.confidence,
                "intent": route_response.intent.value,
                "args": kb_args,
                "retrieval": retrieval_meta,
                "role": request.auth.get("role", "public")
            }

            logger.info(
                f"Knowledge base query completed: {len(kb_rows)} results, "
                f"confidence {route_response.confidence}"
            )

            return SmartQueryResponse(
                answer=answer,
                rows=kb_rows,
                intent=route_response.intent,
                args=kb_args,
                metadata=metadata
            )

        # Step 2: Validate arguments
        if not validate_intent_args(route_response.intent, route_response.args):
            raise HTTPException(
                status_code=400, 
                detail=f"Invalid arguments for intent {route_response.intent}"
            )
        
        # Step 3: Execute database query
        rows, row_count = await execute_intent_query(
            route_response.intent,
            route_response.args,
            request.auth.get("role", "public")
        )
        
        # Step 4: Format answer
        answer = await format_query_answer(
            route_response.intent,
            route_response.args,
            rows,
            llm_client
        )
        
        # Step 5: Prepare metadata
        metadata = {
            "row_count": row_count,
            "confidence": route_response.confidence,
            "intent": route_response.intent.value,
            "args": route_response.args,
            "execution_time_ms": 0,  # Could add timing if needed
            "role": request.auth.get("role", "public")
        }
        
        logger.info(f"Smart query completed: {row_count} rows, confidence {route_response.confidence}")
        
        return SmartQueryResponse(
            answer=answer,
            rows=rows,
            intent=route_response.intent,
            args=route_response.args,
            metadata=metadata
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Smart query failed: {e}")
        raise HTTPException(status_code=500, detail=f"Smart query failed: {str(e)}")


@app.get("/intents")
async def list_intents():
    """List all supported intents."""
    return {
        "intents": [intent.value for intent in Intent],
        "count": len(Intent)
    }


@app.get("/database/health")
async def database_health():
    """Get database health status."""
    try:
        health = await get_database_health()
        return health
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return {"status": "unhealthy", "error": str(e)}


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler."""
    logger.error(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"}
    )


if __name__ == "__main__":
    # Configure logging
    logger.remove()
    logger.add(
        "logs/db-router-svc.log",
        rotation="1 day",
        retention="7 days",
        level="INFO",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {name}:{function}:{line} - {message}"
    )
    logger.add(
        lambda msg: print(msg, end=""),
        level="INFO",
        format="<green>{time:HH:mm:ss}</green> | <level>{level}</level> | <cyan>{name}</cyan> - {message}"
    )
    
    # Run the application
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
