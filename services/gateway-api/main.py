import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'shared'))

from base_service import BaseService
from fastapi import Request, HTTPException
from fastapi.responses import RedirectResponse
import httpx

# Initialize base service
service = BaseService("gateway-api", "1.0.0")
app = service.get_app()

# Get environment variables using the base service
AGENT_URL = service.get_env_var("AGENT_URL", "http://agent-svc:8082")
RETRIEVAL_URL = service.get_env_var("RETRIEVAL_URL", "http://retrieval-svc:8081")
COMMS_URL = service.get_env_var("COMMS_URL", "http://comms-svc:8083")
INGEST_URL = service.get_env_var("INGEST_URL", "http://ingest-svc:8084")
CUSTOMER_CHAT_URL = service.get_env_var("CUSTOMER_CHAT_URL", "http://customer-chat-svc:8085")

# Override the root endpoint to redirect to docs
@app.get("/")
def root():
    return RedirectResponse("/docs")

@app.get("/demo/seed")
async def seed(request: Request):
    try:
        async with httpx.AsyncClient() as client:
            r = await client.post(f"{INGEST_URL}/ingest/seed", timeout=90.0)
            result = r.json()
            service.log_request(request, {"status": "success"})
            return result
    except Exception as e:
        service.log_error(e, "seed endpoint")
        raise

@app.post("/ask")
async def ask(payload: dict, request: Request):
    try:
        async with httpx.AsyncClient() as client:
            r = await client.post(f"{AGENT_URL}/ask", json=payload, timeout=60.0)
            result = r.json()
            service.log_request(request, {"status": "success"})
            return result
    except Exception as e:
        service.log_error(e, "ask endpoint")
        raise

@app.post("/draft_comms")
async def draft_comms(payload: dict, request: Request):
    try:
        async with httpx.AsyncClient() as client:
            r = await client.post(f"{AGENT_URL}/draft_comms", json=payload, timeout=60.0)
            result = r.json()
            service.log_request(request, {"status": "success"})
            return result
    except Exception as e:
        service.log_error(e, "draft_comms endpoint")
        raise

@app.post("/search")
async def search(payload: dict, request: Request):
    try:
        async with httpx.AsyncClient() as client:
            r = await client.post(f"{RETRIEVAL_URL}/search", json=payload, timeout=30.0)
            result = r.json()
            service.log_request(request, {"status": "success"})
            return result
    except Exception as e:
        service.log_error(e, "search endpoint")
        raise

# Customer Chat Service Proxies
@app.post("/customer-chat/session")
async def create_chat_session(payload: dict, request: Request):
    try:
        service.logger.info(f"Creating chat session with payload: {payload}")
        async with httpx.AsyncClient() as client:
            r = await client.post(f"{CUSTOMER_CHAT_URL}/chat/session", json=payload, timeout=30.0)
            service.logger.info(f"Customer chat service response: {r.status_code}")
            if r.status_code != 200:
                service.logger.error(f"Customer chat service error: {r.text}")
                raise HTTPException(status_code=r.status_code, detail=f"Customer chat service error: {r.text}")
            result = r.json()
            service.log_request(request, {"status": "success"})
            return result
    except HTTPException:
        raise
    except Exception as e:
        service.log_error(e, "create_chat_session endpoint")
        raise HTTPException(status_code=500, detail=f"Failed to create chat session: {str(e)}")

@app.post("/customer-chat/message")
async def send_chat_message(payload: dict, request: Request):
    try:
        async with httpx.AsyncClient() as client:
            r = await client.post(f"{CUSTOMER_CHAT_URL}/chat/message", json=payload, timeout=30.0)
            result = r.json()
            service.log_request(request, {"status": "success"})
            return result
    except Exception as e:
        service.log_error(e, "send_chat_message endpoint")
        raise

@app.get("/customer-chat/session/{session_id}")
async def get_chat_session(session_id: str, request: Request):
    try:
        async with httpx.AsyncClient() as client:
            r = await client.get(f"{CUSTOMER_CHAT_URL}/chat/session/{session_id}", timeout=30.0)
            result = r.json()
            service.log_request(request, {"status": "success"})
            return result
    except Exception as e:
        service.log_error(e, "get_chat_session endpoint")
        raise

@app.post("/customer-chat/communication/send")
async def send_communication(payload: dict, request: Request):
    try:
        async with httpx.AsyncClient() as client:
            r = await client.post(f"{CUSTOMER_CHAT_URL}/communication/send", json=payload, timeout=30.0)
            result = r.json()
            service.log_request(request, {"status": "success"})
            return result
    except Exception as e:
        service.log_error(e, "send_communication endpoint")
        raise

@app.get("/customer-chat/communication/history")
async def get_communication_history(request: Request):
    try:
        async with httpx.AsyncClient() as client:
            r = await client.get(f"{CUSTOMER_CHAT_URL}/communication/history", timeout=30.0)
            result = r.json()
            service.log_request(request, {"status": "success"})
            return result
    except Exception as e:
        service.log_error(e, "get_communication_history endpoint")
        raise

@app.get("/customer-chat/test")
async def test_customer_chat(request: Request):
    try:
        async with httpx.AsyncClient() as client:
            r = await client.get(f"{CUSTOMER_CHAT_URL}/test", timeout=30.0)
            result = r.json()
            service.log_request(request, {"status": "success"})
            return result
    except Exception as e:
        service.log_error(e, "test_customer_chat endpoint")
        raise HTTPException(status_code=500, detail=f"Customer chat service not available: {str(e)}")