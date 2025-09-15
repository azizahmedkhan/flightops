from fastapi import FastAPI
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel
from typing import Dict, Any
import os
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
from utils import REQUEST_COUNT, LATENCY, log_startup

SERVICE="comms-svc"

CHAT_MODEL=os.getenv("CHAT_MODEL","gpt-4o-mini")
OPENAI_API_KEY=os.getenv("OPENAI_API_KEY","")

app = FastAPI(title="comms-svc")

class DraftReq(BaseModel):
    context: Dict[str, Any]
    tone: str = "empathetic"
    channel: str = "email"

def llm_chat(prompt: str) -> str:
    if OPENAI_API_KEY:
        try:
            from openai import OpenAI
            client = OpenAI(api_key=OPENAI_API_KEY)
            resp = client.chat.completions.create(model=CHAT_MODEL, messages=[{"role":"user","content":prompt}])
            return resp.choices[0].message.content
        except Exception:
            pass
    # fallback mock
    return f"[MOCK DRAFT]\n{prompt[:500]}..."

@app.get("/health")
def health(): return {"ok": True}

@app.get("/metrics")
def metrics(): return PlainTextResponse(generate_latest(), media_type=CONTENT_TYPE_LATEST)

@app.post("/draft")
def draft(req: DraftReq):
    with LATENCY.labels(SERVICE,"/draft","POST").time():
        c = req.context
        policy_bits = "\n".join([f"- {p}" for p in c.get("policy_citations", [])])
        prompt = f"""You are an airline customer-communications assistant.
Channel: {req.channel}
Tone: {req.tone}
Task: Draft a clear, concise, and compliant message for affected passengers of flight {c.get('flight_no')} on {c.get('date')}.
Include compensation or care per policy. Cite grounded policy snippets at the end.

Context:
- Issue: {c.get('issue')}
- Impact: {c.get('impact_summary')}
- Rebooking options: {c.get('options_summary')}

Policy citations:
{policy_bits}

Draft now:
"""
        text = llm_chat(prompt)
        return {"draft": text}
