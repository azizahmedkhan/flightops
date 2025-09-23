"""
Main FastAPI application for db-router-svc.

This service provides natural language to database query routing
with safe, parameterized SQL execution.
"""

import os
import asyncio
from datetime import datetime
from contextlib import asynccontextmanager
from typing import Dict, Any, List
from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from loguru import logger
import uvicorn

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
from shared.llm_client import LLMClient
from shared.base_service import BaseService


# Global instances
llm_client: LLMClient = None
query_router: QueryRouter = None
base_service: BaseService = None


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
