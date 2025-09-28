"""
Scalable Chatbot Service for FlightOps
Handles up to 1000 concurrent chat sessions with efficient ChatGPT integration
"""

import asyncio
import json
import uuid
from contextlib import asynccontextmanager, suppress
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

import httpx
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import uvicorn

from services.shared.base_service import BaseService
from services.shared.llm_client import LLMClient
from services.shared.prompt_manager import PromptManager
from connection_manager import ConnectionManager
from redis_manager import RedisManager
from rate_limiter import RateLimiter
import os
import debugpy

if os.environ.get("DEBUGPY"):
    debugpy.listen(("0.0.0.0", 5678))
    print("🐛 Debugpy is listening on port 5678")


# Initialize services
service = BaseService("scalable-chatbot-svc", "1.0.0")
app = service.get_app()
logger = service.logger

# Add CORS middleware for WebSocket connections
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global instances
manager = ConnectionManager()
redis_manager = RedisManager()
rate_limiter = RateLimiter(redis_manager)
llm_client = LLMClient("scalable-chatbot-svc", model="gpt-4o-mini")

@asynccontextmanager
async def lifespan(_app: FastAPI):
    """Manage service startup and shutdown without deprecated events."""
    logger.info("startup_event begin")
    await redis_manager.connect()
    cleanup_task_handle = asyncio.create_task(cleanup_task())
    logger.info("startup_event complete - scalable-chatbot-svc ready")

    try:
        yield
    finally:
        logger.info("shutdown_event begin")
        cleanup_task_handle.cancel()
        with suppress(asyncio.CancelledError):
            await cleanup_task_handle
        await redis_manager.disconnect()
        logger.info("shutdown_event complete")

app.router.lifespan_context = lifespan

# Environment variables for service URLs
KNOWLEDGE_SERVICE_URL = os.getenv("KNOWLEDGE_SERVICE_URL", "http://knowledge-engine:8081")
DB_ROUTER_URL = os.getenv("DB_ROUTER_URL", "http://db-router-svc:8000")

# Pydantic models
class ChatMessage(BaseModel):
    session_id: str
    message: str
    client_id: Optional[str] = None

class SessionCreate(BaseModel):
    session_id: Optional[str] = None
    customer_name: str
    customer_email: str
    flight_no: Optional[str] = None
    date: Optional[str] = None

class StreamingResponse(BaseModel):
    type: str  # "chunk", "complete", "error"
    content: str
    session_id: str
    timestamp: str
    metadata: Optional[Dict[str, Any]] = None


async def cleanup_task():
    """Background task to clean up stale connections"""
    while True:
        try:
            await asyncio.sleep(300)  # Run every 5 minutes
            await manager.cleanup_stale_connections(timeout_minutes=10)
        except asyncio.CancelledError:
            logger.info("cleanup_task cancelled")
            break
        except Exception as e:
            logger.error("cleanup_task error: %s", e, exc_info=True)


@app.websocket("/ws/{session_id}/{client_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str, client_id: str):
    """WebSocket endpoint for real-time chat"""
    logger.info("websocket_endpoint begin session_id=%s client_id=%s", session_id, client_id)
    await manager.connect(websocket, session_id, client_id)
    
    try:
        while True:
            # Receive message from client
            data = await websocket.receive_text()
            message_data = json.loads(data)
            
            # Update connection metadata
            if client_id in manager.connection_metadata:
                manager.connection_metadata[client_id]["last_activity"] = datetime.now()
            
            # Handle ping messages for heartbeat
            if message_data.get("type") == "ping":
                pong_response = {
                    "type": "pong",
                    "timestamp": datetime.now().isoformat()
                }
                await manager.send_personal_message(json.dumps(pong_response), client_id)
                continue
            
            # Process chat message asynchronously
            asyncio.create_task(process_chat_message(session_id, message_data, client_id))
            
    except WebSocketDisconnect:
        manager.disconnect(client_id)
        logger.info(
            "websocket_endpoint disconnect session_id=%s client_id=%s",
            session_id,
            client_id
        )


async def process_chat_message(session_id: str, message_data: Dict[str, Any], client_id: str):
    """Process chat message asynchronously"""
    try:
        logger.info(
            "process_chat_message begin session_id=%s client_id=%s",
            session_id,
            client_id
        )
        user_message = message_data.get("message", "")
        
        # Get session context
        session_context = await redis_manager.get_session_context(session_id)
        
        # Check rate limiting for ChatGPT calls
        rate_limit_key = f"chatgpt:{session_id}"
        if await rate_limiter.is_rate_limited(rate_limit_key, limit=30, window=60):
            error_response = {
                "type": "error",
                "content": "Rate limit exceeded. Please wait a moment before sending another message.",
                "session_id": session_id,
                "timestamp": datetime.now().isoformat()
            }
            await manager.send_personal_message(json.dumps(error_response), client_id)
            logger.info(
                "process_chat_message exit session_id=%s client_id=%s reason=rate_limited",
                session_id,
                client_id
            )
            return
        
        # Check for cached response
        query_hash = f"{session_id}:{hash(user_message)}"
        cached_response = await redis_manager.get_cached_response(query_hash)
        
        if cached_response:
            # Send cached response immediately
            cached_data = json.loads(cached_response)
            cached_data["type"] = "complete"
            cached_data["from_cache"] = True
            await manager.send_personal_message(json.dumps(cached_data), client_id)
            logger.info(
                "process_chat_message exit session_id=%s client_id=%s reason=cached_response",
                session_id,
                client_id
            )
            return
        
        # Generate new response using ChatGPT
        await generate_streaming_response(session_id, user_message, session_context, client_id)
        logger.info(
            "process_chat_message exit session_id=%s client_id=%s reason=generated_response",
            session_id,
            client_id
        )
        
    except Exception as e:
        logger.exception(
            "process_chat_message error session_id=%s client_id=%s",
            session_id,
            client_id
        )
        error_response = {
            "type": "error",
            "content": f"Error processing message: {str(e)}",
            "session_id": session_id,
            "timestamp": datetime.now().isoformat()
        }
        await manager.send_personal_message(json.dumps(error_response), client_id)


async def generate_streaming_response(session_id: str, user_message: str, session_context: Dict[str, Any], client_id: str):
    """Generate streaming response from ChatGPT"""
    try:
        logger.info(
            "generate_streaming_response begin session_id=%s client_id=%s",
            session_id,
            client_id
        )
        # Import the new utility functions
        from chatbot_toolkit import (fetch_kb_context, fetch_database_context, route_query, format_kb_response, 
                                     format_database_response, create_air_nz_system_prompt, format_air_nz_response, 
                                     add_heads_up_warning, get_safe_fallback_response)
        
        # Route the query to determine if it needs KB or flight status
        query_type = route_query(user_message)
        
        # Initialize response metadata
        response_metadata = {
            "query_type": query_type,
            "sources": [],
            "kb_context": []
        }
        
        # Fetch context based on query type
        kb_chunks = []
        kb_response = None
        db_response = None
        
        if query_type == "kb":
            kb_chunks = await fetch_kb_context(user_message, KNOWLEDGE_SERVICE_URL)
            if kb_chunks:
                response_metadata["kb_context"] = kb_chunks
                # Format KB response with Air New Zealand style citations
                kb_response = format_kb_response(kb_chunks, response_metadata["sources"])
            else:
                # Use safe fallback for unknown KB queries
                kb_response = get_safe_fallback_response("kb")
        elif query_type == "database":
            # For database queries, use the db-router-svc
            db_data = await fetch_database_context(user_message, DB_ROUTER_URL)
            if db_data:
                response_metadata["database_context"] = db_data
                # Format database response with Air New Zealand style citations
                db_response = format_database_response(db_data, response_metadata["sources"])
            else:
                # Use safe fallback for database queries
                db_response = get_safe_fallback_response("database")
        elif query_type == "flight":
            # For flight status queries, prefer live context; otherwise fall back to database lookup
            if session_context.get("flight_data"):
                pass  # existing flight context in session is already part of the prompt
            else:
                db_data = await fetch_database_context(user_message, DB_ROUTER_URL)
                if db_data:
                    response_metadata["database_context"] = db_data
                    db_response = format_database_response(db_data, response_metadata["sources"])
                else:
                    kb_response = get_safe_fallback_response("flight")
        else:
            # Unknown query type - use general fallback
            kb_response = get_safe_fallback_response("general")

        # Build context-aware prompt
        context_str = build_context_string(session_context)

        # Create Air New Zealand system prompt
        system_content = create_air_nz_system_prompt(
            context_str=context_str,
            grounding_info=kb_response or db_response,
            query_type=query_type
        )
        
        # Create messages for ChatGPT
        messages = [
            {"role": "system", "content": system_content},
            {"role": "user", "content": user_message}
        ]
        
        # Send initial "thinking" message
        thinking_response = {
            "type": "chunk",
            "content": "🤔 Thinking...",
            "session_id": session_id,
            "timestamp": datetime.now().isoformat()
        }
        await manager.send_personal_message(json.dumps(thinking_response), client_id)
        
        # Get response from ChatGPT
        response = llm_client.chat_completion(
            messages=messages,
            temperature=0.3,
            max_tokens=500,
            function_name="generate_streaming_response",
            metadata={"session_id": session_id, "client_id": client_id}
        )
        
        # Parse the response
        chatgpt_response = response["content"]
        
        # Try to extract JSON if it's a sentiment analysis response
        try:
            response_data = json.loads(chatgpt_response)
            final_response = response_data.get("response_to_customer", chatgpt_response)
            sentiment_analysis = response_data.get("analysis", {})
        except:
            final_response = chatgpt_response
            sentiment_analysis = {}
        
        # Format response according to Air New Zealand guidelines
        final_response = format_air_nz_response(final_response, response_metadata["sources"])
        
        # Simulate streaming by sending chunks
        words = final_response.split()
        chunk_size = 3  # Send 3 words at a time
        
        for i in range(0, len(words), chunk_size):
            chunk = " ".join(words[i:i + chunk_size])
            if i + chunk_size < len(words):
                chunk += " "
                
            chunk_response = {
                "type": "chunk",
                "content": chunk,
                "session_id": session_id,
                "timestamp": datetime.now().isoformat()
            }
            
            await manager.send_personal_message(json.dumps(chunk_response), client_id)
            await asyncio.sleep(0.05)  # Small delay for streaming effect
        
        # Send completion message
        complete_response = {
            "type": "complete",
            "content": final_response,
            "session_id": session_id,
            "timestamp": datetime.now().isoformat(),
            "metadata": {
                "sentiment_analysis": sentiment_analysis,
                "tokens_used": response.get("tokens_used"),
                "response_time_ms": response.get("duration_ms"),
                "query_type": response_metadata["query_type"],
                "sources": response_metadata["sources"],
                "kb_context": response_metadata["kb_context"]
            }
        }
        
        await manager.send_personal_message(json.dumps(complete_response), client_id)
        
        # Cache the response
        query_hash = f"{session_id}:{hash(user_message)}"
        await redis_manager.cache_response(query_hash, json.dumps(complete_response))
        
        # Update session context
        updated_context = session_context.copy()
        updated_context["last_message"] = user_message
        updated_context["last_response"] = final_response
        updated_context["last_activity"] = datetime.now().isoformat()
        
        if "message_count" not in updated_context:
            updated_context["message_count"] = 0
            updated_context["message_count"] += 1
        
        await redis_manager.set_session_context(session_id, updated_context)
        logger.info(
            "generate_streaming_response complete session_id=%s client_id=%s query_type=%s tokens=%s duration_ms=%s",
            session_id,
            client_id,
            response_metadata.get("query_type"),
            response.get("tokens_used"),
            response.get("duration_ms")
        )
        
    except Exception as e:
        logger.exception(
            "generate_streaming_response error session_id=%s client_id=%s",
            session_id,
            client_id
        )
        error_response = {
            "type": "error",
            "content": f"Error generating response: {str(e)}",
            "session_id": session_id,
            "timestamp": datetime.now().isoformat()
        }
        await manager.send_personal_message(json.dumps(error_response), client_id)


def build_context_string(session_context: Dict[str, Any]) -> str:
    """Build context string from session data"""
    context_parts = []
    
    if session_context.get("customer_name"):
        context_parts.append(f"Customer: {session_context['customer_name']}")
    
    if session_context.get("flight_no"):
        context_parts.append(f"Flight: {session_context['flight_no']}")
        
    if session_context.get("date"):
        context_parts.append(f"Date: {session_context['date']}")
    
    if session_context.get("flight_data"):
        flight_data = session_context["flight_data"]
        context_parts.append(f"Flight Status: {flight_data.get('status', 'Unknown')}")
    
    if session_context.get("policy_data"):
        policy_data = session_context["policy_data"]
        if isinstance(policy_data, list) and policy_data:
            context_parts.append(f"Relevant Policies: {len(policy_data)} policies available")
    
    return "\n".join(context_parts) if context_parts else "No specific context available"


# REST API endpoints
@app.post("/chat/session")
async def create_session(request: SessionCreate, req: Request):
    """Create a new chat session"""
    try:
        session_id = request.session_id or str(uuid.uuid4())
        
        session_context = {
            "session_id": session_id,
            "customer_name": request.customer_name,
            "customer_email": request.customer_email,
            "flight_no": request.flight_no,
            "date": request.date,
            "created_at": datetime.now().isoformat(),
            "last_activity": datetime.now().isoformat(),
            "message_count": 0
        }
        
        await redis_manager.set_session_context(session_id, session_context)
        
        service.log_request(req, {"status": "success", "session_id": session_id})
        return {"session_id": session_id, "status": "created", "context": session_context}
        
    except Exception as e:
        service.log_error(e, "create_session")
        raise HTTPException(status_code=500, detail="Failed to create session")


@app.get("/chat/session/{session_id}")
async def get_session(session_id: str, req: Request):
    """Get session information"""
    try:
        context = await redis_manager.get_session_context(session_id)
        if not context:
            raise HTTPException(status_code=404, detail="Session not found")
            
        service.log_request(req, {"status": "success", "session_id": session_id})
        return {"session_id": session_id, "context": context}
        
    except HTTPException:
        raise
    except Exception as e:
        service.log_error(e, "get_session")
        raise HTTPException(status_code=500, detail="Failed to get session")


@app.post("/chat/message")
async def send_message(message: ChatMessage, req: Request):
    """Send a message via REST API (fallback for WebSocket)"""
    try:
        session_context = await redis_manager.get_session_context(message.session_id)
        if not session_context:
            raise HTTPException(status_code=404, detail="Session not found")
        
        # Process message synchronously for REST API
        await process_chat_message(message.session_id, {"message": message.message}, message.client_id or "rest")
        
        service.log_request(req, {"status": "success", "session_id": message.session_id})
        return {"status": "message_sent", "session_id": message.session_id}
        
    except HTTPException:
        raise
    except Exception as e:
        service.log_error(e, "send_message")
        raise HTTPException(status_code=500, detail="Failed to send message")


@app.get("/health")
async def health_check(req: Request):
    """Health check endpoint"""
    try:
        # Check Redis connection
        redis_status = "connected" if redis_manager.redis_client else "disconnected"
        
        # Get connection stats
        active_connections = len(manager.active_connections)
        active_sessions = len(manager.session_connections)
        
        health_data = {
            "status": "healthy",
            "service": "scalable-chatbot-svc",
            "timestamp": datetime.now().isoformat(),
            "redis_status": redis_status,
            "active_connections": active_connections,
            "active_sessions": active_sessions,
            "uptime": "running"
        }
        
        service.log_request(req, health_data)
        return health_data
        
    except Exception as e:
        service.log_error(e, "health_check")
        raise HTTPException(status_code=500, detail="Health check failed")


@app.get("/stats")
async def get_stats(req: Request):
    """Get service metrics"""
    try:
        metrics = {
            "active_connections": len(manager.active_connections),
            "active_sessions": len(manager.session_connections),
            "connection_metadata": manager.connection_metadata,
            "timestamp": datetime.now().isoformat()
        }
        
        service.log_request(req, {"status": "success"})
        return metrics
        
    except Exception as e:
        service.log_error(e, "get_metrics")
        raise HTTPException(status_code=500, detail="Failed to get metrics")


@app.get("/test")
def test_endpoint(req: Request):
    """Test endpoint"""
    return {"status": "ok", "service": "scalable-chatbot-svc", "message": "Service is running"}


if __name__ == "__main__":
    if os.environ.get("DEBUGPY"):
        print("⏳ Waiting for debugger to attach...")
        debugpy.wait_for_client()
        print("✅ Debugger attached!")
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8088,
        reload=True,
        workers=1,  # Single worker for WebSocket support
        loop="asyncio"
    )
