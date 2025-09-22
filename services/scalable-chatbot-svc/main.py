"""
Scalable Chatbot Service for FlightOps
Handles up to 1000 concurrent chat sessions with efficient ChatGPT integration
"""

import asyncio
import json
import uuid
import time
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Set
from contextlib import asynccontextmanager

import redis.asyncio as redis
import httpx
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import uvicorn

from shared.base_service import BaseService
from shared.llm_client import LLMClient
from shared.prompt_manager import PromptManager
import os
import debugpy

if os.environ.get("DEBUGPY"):
    debugpy.listen(("0.0.0.0", 5678))
    print("🐛 Debugpy is listening on port 5678")


# Global variables for connection management
class ConnectionManager:
    """Manages WebSocket connections for scalable chat sessions"""
    
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.session_connections: Dict[str, Set[str]] = {}
        self.connection_metadata: Dict[str, Dict[str, Any]] = {}
        
    async def connect(self, websocket: WebSocket, session_id: str, client_id: str):
        """Accept a new WebSocket connection"""
        await websocket.accept()
        self.active_connections[client_id] = websocket
        
        if session_id not in self.session_connections:
            self.session_connections[session_id] = set()
        self.session_connections[session_id].add(client_id)
        
        self.connection_metadata[client_id] = {
            "session_id": session_id,
            "connected_at": datetime.now(),
            "last_activity": datetime.now()
        }
        
    def disconnect(self, client_id: str):
        """Remove a WebSocket connection"""
        if client_id in self.active_connections:
            del self.active_connections[client_id]
            
        # Remove from session tracking
        for session_id, connections in list(self.session_connections.items()):
            connections.discard(client_id)
            if not connections:
                del self.session_connections[session_id]
                
        if client_id in self.connection_metadata:
            del self.connection_metadata[client_id]
            
    async def send_personal_message(self, message: str, client_id: str):
        """Send message to specific client"""
        if client_id in self.active_connections:
            try:
                await self.active_connections[client_id].send_text(message)
            except:
                self.disconnect(client_id)
                
    async def send_to_session(self, message: str, session_id: str):
        """Send message to all clients in a session"""
        if session_id in self.session_connections:
            for client_id in list(self.session_connections[session_id]):
                await self.send_personal_message(message, client_id)
                
    async def broadcast(self, message: str):
        """Broadcast message to all active connections"""
        for client_id in list(self.active_connections.keys()):
            await self.send_personal_message(message, client_id)


class RedisManager:
    """Redis-based session and context management"""
    
    def __init__(self, redis_url: str = "redis://redis:6379"):
        self.redis_url = redis_url
        self.redis_client = None
        
    async def connect(self):
        """Initialize Redis connection"""
        self.redis_client = redis.from_url(self.redis_url, decode_responses=True)
        
    async def disconnect(self):
        """Close Redis connection"""
        if self.redis_client:
            await self.redis_client.close()
            
    async def get_session_context(self, session_id: str) -> Dict[str, Any]:
        """Get session context from Redis"""
        if not self.redis_client:
            return {}
            
        try:
            context_data = await self.redis_client.hgetall(f"session:{session_id}")
            if context_data:
                # Parse JSON fields
                for key in ['flight_data', 'policy_data', 'sentiment_history']:
                    if key in context_data:
                        try:
                            context_data[key] = json.loads(context_data[key])
                        except:
                            context_data[key] = {}
                
                # Convert numeric fields back to their proper types
                if 'message_count' in context_data:
                    try:
                        context_data['message_count'] = int(context_data['message_count'])
                    except (ValueError, TypeError):
                        context_data['message_count'] = 0
                        
            return context_data
        except Exception as e:
            print(f"Redis get error: {e}")
            return {}
            
    async def set_session_context(self, session_id: str, context: Dict[str, Any], ttl: int = 3600):
        """Store session context in Redis with TTL"""
        if not self.redis_client:
            return
            
        try:
            # Serialize complex fields
            serialized_context = {}
            for key, value in context.items():
                if isinstance(value, (dict, list)):
                    serialized_context[key] = json.dumps(value)
                else:
                    serialized_context[key] = str(value)
                    
            await self.redis_client.hset(f"session:{session_id}", mapping=serialized_context)
            await self.redis_client.expire(f"session:{session_id}", ttl)
        except Exception as e:
            print(f"Redis set error: {e}")
            
    async def cache_response(self, query_hash: str, response: str, ttl: int = 1800):
        """Cache ChatGPT response to avoid duplicate API calls"""
        if not self.redis_client:
            return
            
        try:
            await self.redis_client.setex(f"response:{query_hash}", ttl, response)
        except Exception as e:
            print(f"Redis cache error: {e}")
            
    async def get_cached_response(self, query_hash: str) -> Optional[str]:
        """Get cached ChatGPT response"""
        if not self.redis_client:
            return None
            
        try:
            return await self.redis_client.get(f"response:{query_hash}")
        except Exception as e:
            print(f"Redis get cache error: {e}")
            return None


class RateLimiter:
    """Rate limiting for ChatGPT API calls"""
    
    def __init__(self, redis_manager: RedisManager):
        self.redis_manager = redis_manager
        self.local_limits: Dict[str, List[float]] = {}
        
    async def is_rate_limited(self, key: str, limit: int = 60, window: int = 60) -> bool:
        """Check if rate limit is exceeded"""
        current_time = time.time()
        
        # Clean old entries
        if key in self.local_limits:
            self.local_limits[key] = [
                t for t in self.local_limits[key] 
                if current_time - t < window
            ]
        else:
            self.local_limits[key] = []
            
        # Check limit
        if len(self.local_limits[key]) >= limit:
            return True
            
        self.local_limits[key].append(current_time)
        return False


# Initialize services
service = BaseService("scalable-chatbot-svc", "1.0.0")
app = service.get_app()

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

# Environment variables for KB service URLs
RETRIEVAL_SVC_URL = os.getenv("RETRIEVAL_SVC_URL", "http://retrieval-svc:8086")
AGENT_SVC_URL = os.getenv("AGENT_SVC_URL", "http://agent-svc:8081")

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


@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    await redis_manager.connect()
    print("🚀 Scalable Chatbot Service started - ready for 1000+ concurrent sessions")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    await redis_manager.disconnect()


@app.websocket("/ws/{session_id}/{client_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str, client_id: str):
    """WebSocket endpoint for real-time chat"""
    await manager.connect(websocket, session_id, client_id)
    
    try:
        while True:
            # Receive message from client
            data = await websocket.receive_text()
            message_data = json.loads(data)
            
            # Update connection metadata
            if client_id in manager.connection_metadata:
                manager.connection_metadata[client_id]["last_activity"] = datetime.now()
            
            # Process message asynchronously
            asyncio.create_task(process_chat_message(session_id, message_data, client_id))
            
    except WebSocketDisconnect:
        manager.disconnect(client_id)
        print(f"Client {client_id} disconnected from session {session_id}")


async def process_chat_message(session_id: str, message_data: Dict[str, Any], client_id: str):
    """Process chat message asynchronously"""
    try:
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
            return
        
        # Generate new response using ChatGPT
        await generate_streaming_response(session_id, user_message, session_context, client_id)
        
    except Exception as e:
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
        # Import the new utility functions
        from utils import (fetch_kb_context, route_query, format_kb_response, 
                          create_air_nz_system_prompt, format_air_nz_response, 
                          add_heads_up_warning, get_safe_fallback_response)
        
        # Route the query to determine if it needs KB or flight status
        query_type = route_query(user_message)
        
        # Initialize response metadata
        response_metadata = {
            "query_type": query_type,
            "sources": [],
            "kb_context": []
        }
        
        # Fetch KB context if needed
        kb_chunks = []
        kb_response = None
        if query_type == "kb":
            kb_chunks = await fetch_kb_context(user_message, RETRIEVAL_SVC_URL)
            if kb_chunks:
                response_metadata["kb_context"] = kb_chunks
                # Format KB response with Air New Zealand style citations
                kb_response = format_kb_response(kb_chunks, response_metadata["sources"])
            else:
                # Use safe fallback for unknown KB queries
                kb_response = get_safe_fallback_response("kb")
        elif query_type == "flight":
            # For flight status queries, check if we have flight context
            if not session_context.get("flight_data"):
                kb_response = get_safe_fallback_response("flight")
        else:
            # Unknown query type - use general fallback
            kb_response = get_safe_fallback_response("general")
        
        # Build context-aware prompt
        context_str = build_context_string(session_context)
        
        # Create Air New Zealand system prompt
        system_content = create_air_nz_system_prompt(
            context_str=context_str,
            kb_response=kb_response,
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
        
    except Exception as e:
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
