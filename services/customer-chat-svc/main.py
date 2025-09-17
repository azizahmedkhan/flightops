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
RETRIEVAL_URL = service.get_env_var("RETRIEVAL_URL", "http://retrieval-svc:8081")

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
    """Send a message in a chat session with sentiment analysis"""
    try:
        if message.session_id not in chat_sessions:
            raise HTTPException(status_code=404, detail="Chat session not found")
        
        # Analyze sentiment of customer message
        sentiment_analysis = analyze_customer_sentiment(message.message, message.session_id)
        
        # Store customer message with sentiment data
        customer_msg = {
            "id": str(uuid.uuid4()),
            "type": "customer",
            "message": message.message,
            "timestamp": datetime.now().isoformat(),
            "customer_name": message.customer_name,
            "customer_email": message.customer_email,
            "customer_phone": message.customer_phone,
            "sentiment": sentiment_analysis
        }
        
        message_history[message.session_id].append(customer_msg)
        
        # Get flight context for AI response
        session = chat_sessions[message.session_id]
        
        # Adjust response based on sentiment
        response_tone = sentiment_analysis.get("recommended_tone", "empathetic")
        
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
                
                # Enhance response with sentiment-aware communication
                enhanced_response = enhance_response_with_sentiment(
                    agent_data, sentiment_analysis, session
                )
                
                ai_response = {
                    "id": str(uuid.uuid4()),
                    "type": "agent",
                    "message": enhanced_response.get("message", "I'm here to help with your flight inquiry."),
                    "timestamp": datetime.now().isoformat(),
                    "flight_info": agent_data.get("tools_payload", {}).get("flight", {}),
                    "impact": agent_data.get("tools_payload", {}).get("impact", {}),
                    "options": agent_data.get("tools_payload", {}).get("options", []),
                    "citations": agent_data.get("answer", {}).get("citations", []),
                    "sentiment_aware": True,
                    "response_tone": response_tone,
                    "escalation_recommended": sentiment_analysis.get("urgency_level") == "high"
                }
            else:
                ai_response = {
                    "id": str(uuid.uuid4()),
                    "type": "agent",
                    "message": "I apologize, but I'm having trouble accessing flight information right now. Please try again later or contact our support team.",
                    "timestamp": datetime.now().isoformat(),
                    "sentiment_aware": False
                }
        except Exception as e:
            service.log_error(e, "agent_call")
            ai_response = {
                "id": str(uuid.uuid4()),
                "type": "agent",
                "message": "I'm sorry, I'm experiencing technical difficulties. Please try again or contact our support team.",
                "timestamp": datetime.now().isoformat(),
                "sentiment_aware": False
            }
        
        message_history[message.session_id].append(ai_response)
        chat_sessions[message.session_id]["last_activity"] = datetime.now().isoformat()
        
        # Update session with sentiment insights
        if "sentiment_insights" not in chat_sessions[message.session_id]:
            chat_sessions[message.session_id]["sentiment_insights"] = []
        chat_sessions[message.session_id]["sentiment_insights"].append({
            "timestamp": datetime.now().isoformat(),
            "sentiment": sentiment_analysis.get("sentiment"),
            "urgency": sentiment_analysis.get("urgency_level"),
            "escalation_needed": sentiment_analysis.get("urgency_level") == "high"
        })
        
        service.log_request(req, {"status": "success", "session_id": message.session_id, "sentiment": sentiment_analysis.get("sentiment")})
        return {
            "session_id": message.session_id,
            "customer_message": customer_msg,
            "ai_response": ai_response,
            "message_count": len(message_history[message.session_id]),
            "sentiment_analysis": sentiment_analysis
        }
        
    except HTTPException:
        raise
    except Exception as e:
        service.log_error(e, "send_chat_message")
        raise HTTPException(status_code=500, detail="Failed to send message")

def analyze_customer_sentiment(message: str, session_id: str) -> Dict[str, Any]:
    """Analyze customer sentiment using comms service"""
    try:
        # Get session context
        session = chat_sessions.get(session_id, {})
        context = {
            "flight_no": session.get("flight_no", "Unknown"),
            "customer_name": session.get("customer_name", "Customer"),
            "issue": "Customer inquiry"
        }
        
        # Call comms service for sentiment analysis
        sentiment_response = httpx.post(
            f"{COMMS_URL}/analyze_sentiment",
            json={
                "text": message,
                "context": context
            },
            timeout=15.0
        )
        
        if sentiment_response.status_code == 200:
            return sentiment_response.json()
        else:
            return analyze_sentiment_fallback(message)
            
    except Exception as e:
        service.log_error(e, "sentiment_analysis")
        return analyze_sentiment_fallback(message)

def analyze_sentiment_fallback(message: str) -> Dict[str, Any]:
    """Fallback sentiment analysis when comms service is unavailable"""
    text_lower = message.lower()
    
    # Simple keyword-based analysis
    positive_words = ["thank", "appreciate", "good", "excellent", "happy", "satisfied"]
    negative_words = ["angry", "frustrated", "disappointed", "terrible", "awful", "hate", "complaint"]
    urgent_words = ["urgent", "immediately", "asap", "emergency", "critical", "now"]
    
    positive_count = sum(1 for word in positive_words if word in text_lower)
    negative_count = sum(1 for word in negative_words if word in text_lower)
    urgent_count = sum(1 for word in urgent_words if word in text_lower)
    
    if negative_count > positive_count:
        sentiment = "negative"
        sentiment_score = -0.5 - (negative_count * 0.1)
    elif positive_count > negative_count:
        sentiment = "positive"
        sentiment_score = 0.5 + (positive_count * 0.1)
    else:
        sentiment = "neutral"
        sentiment_score = 0.0
    
    urgency = "high" if urgent_count > 0 else "medium" if negative_count > 2 else "low"
    response_tone = "urgent" if sentiment == "negative" and urgency == "high" else "empathetic" if sentiment == "negative" else "professional"
    
    return {
        "sentiment": sentiment,
        "sentiment_score": max(-1.0, min(1.0, sentiment_score)),
        "urgency_level": urgency,
        "recommended_tone": response_tone,
        "analysis_method": "fallback"
    }

def enhance_response_with_sentiment(agent_data: Dict[str, Any], sentiment_analysis: Dict[str, Any], 
                                  session: Dict[str, Any]) -> Dict[str, Any]:
    """Enhance AI response based on customer sentiment"""
    base_message = agent_data.get("answer", {}).get("issue", "I'm here to help with your flight inquiry.")
    sentiment = sentiment_analysis.get("sentiment", "neutral")
    urgency = sentiment_analysis.get("urgency_level", "low")
    
    # Enhance message based on sentiment
    if sentiment == "negative" and urgency == "high":
        enhanced_message = f"I understand your frustration and I'm here to help resolve this immediately. {base_message}"
    elif sentiment == "negative":
        enhanced_message = f"I sincerely apologize for the inconvenience. {base_message}"
    elif sentiment == "positive":
        enhanced_message = f"Thank you for your patience. {base_message}"
    else:
        enhanced_message = base_message
    
    # Add escalation recommendation if needed
    if urgency == "high":
        enhanced_message += "\n\nI'm escalating this to our senior support team for immediate attention."
    
    return {
        "message": enhanced_message,
        "original_message": base_message,
        "enhancement_applied": True
    }

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

@app.get("/message")
def get_message(flight_no: str, date: str, req: Request):
    """Get latest generated email/SMS for a specific flight and date"""
    try:
        # Call agent service to get grounded context
        try:
            agent_response = httpx.post(
                f"{AGENT_URL}/draft_comms",
                json={
                    "question": "Draft email + SMS for affected passengers",
                    "flight_no": flight_no,
                    "date": date
                },
                timeout=30.0
            )
            
            if agent_response.status_code == 200:
                agent_data = agent_response.json()
                context = agent_data.get("context", {})
                draft = agent_data.get("draft", {})
                
                # Generate both email and SMS versions
                email_response = httpx.post(
                    f"{COMMS_URL}/draft",
                    json={
                        "context": context,
                        "tone": "empathetic",
                        "channel": "email"
                    },
                    timeout=30.0
                )
                
                sms_response = httpx.post(
                    f"{COMMS_URL}/draft",
                    json={
                        "context": context,
                        "tone": "empathetic",
                        "channel": "sms"
                    },
                    timeout=30.0
                )
                
                result = {
                    "flight_no": flight_no,
                    "date": date,
                    "email": email_response.json().get("draft", "Email not available") if email_response.status_code == 200 else "Email generation failed",
                    "sms": sms_response.json().get("draft", "SMS not available") if sms_response.status_code == 200 else "SMS generation failed",
                    "context": context,
                    "generated_at": datetime.now().isoformat()
                }
            else:
                result = {
                    "flight_no": flight_no,
                    "date": date,
                    "email": "Unable to generate email - flight data not available",
                    "sms": "Unable to generate SMS - flight data not available",
                    "error": "Flight data not found",
                    "generated_at": datetime.now().isoformat()
                }
        except Exception as e:
            service.log_error(e, "get_message")
            result = {
                "flight_no": flight_no,
                "date": date,
                "email": "Service temporarily unavailable",
                "sms": "Service temporarily unavailable",
                "error": "Service error",
                "generated_at": datetime.now().isoformat()
            }
        
        service.log_request(req, {"status": "success", "flight_no": flight_no, "date": date})
        return result
        
    except Exception as e:
        service.log_error(e, "get_message")
        raise HTTPException(status_code=500, detail="Failed to get message")

class QARequest(BaseModel):
    question: str
    flight_no: str
    date: str

@app.post("/qa")
def qa(request: QARequest, req: Request):
    """Narrow Q&A endpoint with retrieval-only answers (no state changes)"""
    try:
        # Rate limiting check (simple in-memory for demo)
        client_ip = req.client.host if hasattr(req, 'client') else "unknown"
        rate_limit_key = f"{client_ip}:{request.flight_no}:{request.date}"
        
        # Simple rate limiting: max 10 requests per minute per flight
        current_time = datetime.now()
        if not hasattr(qa, 'rate_limit'):
            qa.rate_limit = {}
        
        if rate_limit_key in qa.rate_limit:
            last_request = qa.rate_limit[rate_limit_key]
            if (current_time - last_request).seconds < 60:
                # Check if we've exceeded 10 requests in the last minute
                if not hasattr(qa, 'request_counts'):
                    qa.request_counts = {}
                if rate_limit_key not in qa.request_counts:
                    qa.request_counts[rate_limit_key] = []
                
                # Clean old requests
                qa.request_counts[rate_limit_key] = [
                    t for t in qa.request_counts[rate_limit_key] 
                    if (current_time - t).seconds < 60
                ]
                
                if len(qa.request_counts[rate_limit_key]) >= 10:
                    raise HTTPException(status_code=429, detail="Rate limit exceeded. Please try again later.")
                
                qa.request_counts[rate_limit_key].append(current_time)
        else:
            qa.rate_limit[rate_limit_key] = current_time
            qa.request_counts = getattr(qa, 'request_counts', {})
            qa.request_counts[rate_limit_key] = [current_time]
        
        # PII scrubbing
        def pii_scrub(text: str) -> str:
            import re
            text = re.sub(r"[A-Z0-9]{6}(?=\b)", "[PNR]", text)
            text = re.sub(r"[\w\.-]+@[\w\.-]+", "[EMAIL]", text)
            text = re.sub(r"\+?\d[\d\s-]{6,}", "[PHONE]", text)
            return text
        
        scrubbed_question = pii_scrub(request.question)
        
        # Use retrieval service for policy grounding
        try:
            retrieval_response = httpx.post(
                f"{RETRIEVAL_URL}/search",
                json={
                    "q": scrubbed_question + " policy compensation rebooking",
                    "k": 3
                },
                timeout=15.0
            )
            
            if retrieval_response.status_code == 200:
                retrieval_data = retrieval_response.json()
                citations = retrieval_data.get("results", [])
                
                # Generate safe, limited response based on citations
                if citations:
                    # Extract key information from citations
                    policy_info = []
                    for citation in citations[:2]:  # Limit to top 2 citations
                        policy_info.append(f"{citation.get('title', 'Policy')}: {citation.get('snippet', '')[:200]}")
                    
                    answer = f"Based on our policies: {' '.join(policy_info[:1])}"
                    if len(policy_info) > 1:
                        answer += f" Additional information: {policy_info[1]}"
                else:
                    answer = "I can help with general questions about your flight status, rebooking options, and compensation policies. Please contact our support team for specific assistance."
                
                result = {
                    "question": scrubbed_question,
                    "answer": answer,
                    "flight_no": request.flight_no,
                    "date": request.date,
                    "citations": citations,
                    "answered_at": current_time.isoformat(),
                    "source": "retrieval_only"
                }
            else:
                result = {
                    "question": scrubbed_question,
                    "answer": "I'm having trouble accessing policy information right now. Please contact our support team for assistance.",
                    "flight_no": request.flight_no,
                    "date": request.date,
                    "citations": [],
                    "answered_at": current_time.isoformat(),
                    "source": "fallback"
                }
        except Exception as e:
            service.log_error(e, "qa_retrieval")
            result = {
                "question": scrubbed_question,
                "answer": "I'm experiencing technical difficulties. Please contact our support team for assistance.",
                "flight_no": request.flight_no,
                "date": request.date,
                "citations": [],
                "answered_at": current_time.isoformat(),
                "source": "error"
            }
        
        service.log_request(req, {"status": "success", "flight_no": request.flight_no, "date": request.date})
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        service.log_error(e, "qa")
        raise HTTPException(status_code=500, detail="Failed to process Q&A request")

@app.get("/test")
def test_endpoint(req: Request):
    """Test endpoint to verify service is working"""
    return {"status": "ok", "service": "customer-chat-svc", "message": "Service is running"}
