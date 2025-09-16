import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'shared'))

from base_service import BaseService
from fastapi import Request
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