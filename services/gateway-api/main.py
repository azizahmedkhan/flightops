from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse, PlainTextResponse
from fastapi.middleware.cors import CORSMiddleware
import os, httpx
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST

AGENT_URL=os.getenv("AGENT_URL","http://agent-svc:8082")
RETRIEVAL_URL=os.getenv("RETRIEVAL_URL","http://retrieval-svc:8081")
COMMS_URL=os.getenv("COMMS_URL","http://comms-svc:8083")
INGEST_URL=os.getenv("INGEST_URL","http://ingest-svc:8084")

app = FastAPI(title="gateway-api")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def root():
    return RedirectResponse("/docs")

@app.get("/metrics")
def metrics(): return PlainTextResponse(generate_latest(), media_type=CONTENT_TYPE_LATEST)

@app.get("/demo/seed")
async def seed():
    async with httpx.AsyncClient() as client:
        r = await client.post(f"{INGEST_URL}/ingest/seed", timeout=90.0)
        return r.json()

@app.post("/ask")
async def ask(payload: dict):
    async with httpx.AsyncClient() as client:
        r = await client.post(f"{AGENT_URL}/ask", json=payload, timeout=60.0)
        return r.json()

@app.post("/draft_comms")
async def draft_comms(payload: dict):
    async with httpx.AsyncClient() as client:
        r = await client.post(f"{AGENT_URL}/draft_comms", json=payload, timeout=60.0)
        return r.json()

@app.post("/search")
async def search(payload: dict):
    async with httpx.AsyncClient() as client:
        r = await client.post(f"{RETRIEVAL_URL}/search", json=payload, timeout=30.0)
        return r.json()
