import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'shared'))

from base_service import BaseService
from fastapi import Request, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, List, Optional
import httpx
import json
from datetime import datetime
import uuid

# Initialize base service
service = BaseService("customer-chat-svc", "1.0.0")
app = service.get_app()

# Get environment variables using the base service
COMMS_URL = service.get_env_var("COMMS_URL", "http://comms-svc:8083")
AGENT_URL = service.get_env_var("AGENT_URL", "http://agent-svc:8082")

# In-memory storage for demo purposes (in production, use Redis or database)
chat_sessions = {}
message_history = {}

class ChatMessage(BaseModel):
    session_id: str
    message: str
    customer_name: Optional[str] = None
    customer_email: Optional[str] = None
    customer_phone: Optional[str] = None

class CommunicationRequest(BaseModel):
    flight_no: str
    date: str
    customer_name: str
    customer_email: str
    customer_phone: Optional[str] = None
    communication_type: str  # "email", "sms", "both"
    tone: str = "empathetic"

class ChatSessionCreate(BaseModel):
    customer_name: str
    customer_email: str
    customer_phone: Optional[str] = None
    flight_no: str
    date: str

class ChatSession(BaseModel):
    session_id: str
    customer_name: str
    customer_email: str
    customer_phone: Optional[str] = None
    flight_no: str
    date: str
    created_at: str
    last_activity: str

@app.post("/chat/session")
def create_chat_session(request: ChatSessionCreate, req: Request):
    """Create a new chat session for a customer"""
    try:
        session_id = str(uuid.uuid4())
        session = {
            "session_id": session_id,
            "customer_name": request.customer_name,
            "customer_email": request.customer_email,
            "customer_phone": request.customer_phone,
            "flight_no": request.flight_no,
            "date": request.date,
            "created_at": datetime.now().isoformat(),
            "last_activity": datetime.now().isoformat()
        }
        
        chat_sessions[session_id] = session
        message_history[session_id] = []
        
        service.log_request(req, {"status": "success", "session_id": session_id})
        return {"session_id": session_id, "status": "created", "session": session}
    except Exception as e:
        service.log_error(e, "create_chat_session")
        raise HTTPException(status_code=500, detail="Failed to create chat session")

@app.post("/chat/message")
def send_chat_message(message: ChatMessage, req: Request):
    """Send a message in a chat session"""
    try:
        if message.session_id not in chat_sessions:
            raise HTTPException(status_code=404, detail="Chat session not found")
        
        # Store customer message
        customer_msg = {
            "id": str(uuid.uuid4()),
            "type": "customer",
            "message": message.message,
            "timestamp": datetime.now().isoformat(),
            "customer_name": message.customer_name,
            "customer_email": message.customer_email,
            "customer_phone": message.customer_phone
        }
        
        message_history[message.session_id].append(customer_msg)
        
        # Get flight context for AI response
        session = chat_sessions[message.session_id]
        
        # Call agent service for AI response
        try:
            agent_response = httpx.post(
                f"{AGENT_URL}/ask",
                json={
                    "question": message.message,
                    "flight_no": session["flight_no"],
                    "date": session["date"]
                },
                timeout=30.0
            )
            
            if agent_response.status_code == 200:
                agent_data = agent_response.json()
                ai_response = {
                    "id": str(uuid.uuid4()),
                    "type": "agent",
                    "message": agent_data.get("answer", {}).get("issue", "I'm here to help with your flight inquiry."),
                    "timestamp": datetime.now().isoformat(),
                    "flight_info": agent_data.get("tools_payload", {}).get("flight", {}),
                    "impact": agent_data.get("tools_payload", {}).get("impact", {}),
                    "options": agent_data.get("tools_payload", {}).get("options", []),
                    "citations": agent_data.get("answer", {}).get("citations", [])
                }
            else:
                ai_response = {
                    "id": str(uuid.uuid4()),
                    "type": "agent",
                    "message": "I apologize, but I'm having trouble accessing flight information right now. Please try again later or contact our support team.",
                    "timestamp": datetime.now().isoformat()
                }
        except Exception as e:
            service.log_error(e, "agent_call")
            ai_response = {
                "id": str(uuid.uuid4()),
                "type": "agent",
                "message": "I'm sorry, I'm experiencing technical difficulties. Please try again or contact our support team.",
                "timestamp": datetime.now().isoformat()
            }
        
        message_history[message.session_id].append(ai_response)
        chat_sessions[message.session_id]["last_activity"] = datetime.now().isoformat()
        
        service.log_request(req, {"status": "success", "session_id": message.session_id})
        return {
            "session_id": message.session_id,
            "customer_message": customer_msg,
            "ai_response": ai_response,
            "message_count": len(message_history[message.session_id])
        }
        
    except HTTPException:
        raise
    except Exception as e:
        service.log_error(e, "send_chat_message")
        raise HTTPException(status_code=500, detail="Failed to send message")

@app.get("/chat/session/{session_id}")
def get_chat_session(session_id: str, req: Request):
    """Get chat session details and message history"""
    try:
        if session_id not in chat_sessions:
            raise HTTPException(status_code=404, detail="Chat session not found")
        
        session = chat_sessions[session_id]
        messages = message_history.get(session_id, [])
        
        service.log_request(req, {"status": "success", "session_id": session_id})
        return {
            "session": session,
            "messages": messages,
            "message_count": len(messages)
        }
    except HTTPException:
        raise
    except Exception as e:
        service.log_error(e, "get_chat_session")
        raise HTTPException(status_code=500, detail="Failed to get chat session")

@app.post("/communication/send")
def send_communication(request: CommunicationRequest, req: Request):
    """Send email or SMS communication to customer"""
    try:
        # Call comms service to draft the communication
        comms_response = httpx.post(
            f"{COMMS_URL}/draft",
            json={
                "context": {
                    "flight_no": request.flight_no,
                    "date": request.date,
                    "issue": "Flight disruption",
                    "impact_summary": "Your flight has been affected",
                    "options_summary": "We have rebooking options available",
                    "policy_citations": ["Customer compensation policy", "Rebooking procedures"]
                },
                "tone": request.tone,
                "channel": request.communication_type
            },
            timeout=30.0
        )
        
        if comms_response.status_code != 200:
            raise HTTPException(status_code=500, detail="Failed to generate communication")
        
        comms_data = comms_response.json()
        draft_content = comms_data.get("draft", "Communication content not available")
        
        # Format the content based on communication type
        if request.communication_type == "email":
            formatted_content = f"""Subject: Important Update for Your Flight {request.flight_no}

Dear {request.customer_name},

{draft_content}

Best regards,
FlightOps Customer Service Team

---
Flight: {request.flight_no}
Date: {request.date}
Reference: {str(uuid.uuid4())[:8].upper()}"""
        elif request.communication_type == "sms":
            # SMS should be concise
            sms_content = draft_content.replace('\n', ' ').strip()
            if len(sms_content) > 160:
                sms_content = sms_content[:157] + "..."
            formatted_content = f"FlightOps: {sms_content} - Flight {request.flight_no} on {request.date}"
        else:  # both
            sms_content = draft_content.replace('\n', ' ').strip()
            formatted_content = f"""EMAIL:
Subject: Important Update for Your Flight {request.flight_no}

Dear {request.customer_name},

{draft_content}

Best regards,
FlightOps Customer Service Team

---
SMS:
FlightOps: {sms_content[:100]}... - Flight {request.flight_no} on {request.date}"""
        
        # Simulate sending (in production, integrate with actual email/SMS services)
        communication_id = str(uuid.uuid4())
        
        result = {
            "communication_id": communication_id,
            "type": request.communication_type,
            "customer_name": request.customer_name,
            "customer_email": request.customer_email,
            "customer_phone": request.customer_phone,
            "flight_no": request.flight_no,
            "date": request.date,
            "content": formatted_content,
            "status": "sent",
            "sent_at": datetime.now().isoformat(),
            "tone": request.tone
        }
        
        service.log_request(req, {"status": "success", "communication_id": communication_id})
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        service.log_error(e, "send_communication")
        raise HTTPException(status_code=500, detail="Failed to send communication")

@app.get("/communication/history")
def get_communication_history(req: Request):
    """Get communication history (demo data)"""
    try:
        # In production, this would query a database
        demo_history = [
            {
                "communication_id": "demo-1",
                "type": "email",
                "customer_name": "John Doe",
                "customer_email": "john.doe@example.com",
                "flight_no": "NZ123",
                "date": "2025-09-17",
                "status": "sent",
                "sent_at": "2025-09-16T10:30:00Z",
                "tone": "empathetic"
            },
            {
                "communication_id": "demo-2",
                "type": "sms",
                "customer_name": "Jane Smith",
                "customer_phone": "+1234567890",
                "flight_no": "NZ456",
                "date": "2025-09-17",
                "status": "sent",
                "sent_at": "2025-09-16T11:15:00Z",
                "tone": "urgent"
            }
        ]
        
        service.log_request(req, {"status": "success"})
        return {"communications": demo_history}
        
    except Exception as e:
        service.log_error(e, "get_communication_history")
        raise HTTPException(status_code=500, detail="Failed to get communication history")

@app.get("/chat/sessions")
def list_chat_sessions(req: Request):
    """List all active chat sessions"""
    try:
        sessions = list(chat_sessions.values())
        service.log_request(req, {"status": "success", "count": len(sessions)})
        return {"sessions": sessions, "count": len(sessions)}
    except Exception as e:
        service.log_error(e, "list_chat_sessions")
        raise HTTPException(status_code=500, detail="Failed to list chat sessions")

@app.get("/test")
def test_endpoint(req: Request):
    """Test endpoint to verify service is working"""
    return {"status": "ok", "service": "customer-chat-svc", "message": "Service is running"}
