import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'shared'))

from base_service import BaseService
from fastapi import Request
from pydantic import BaseModel
from typing import Dict, Any
from utils import REQUEST_COUNT, LATENCY, log_startup

# Initialize base service
service = BaseService("comms-svc", "1.0.0")
app = service.get_app()

# Get environment variables using the base service
CHAT_MODEL = service.get_env_var("CHAT_MODEL", "gpt-4o-mini")
OPENAI_API_KEY = service.get_env_var("OPENAI_API_KEY", "")

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
        except Exception as e:
            service.log_error(e, "llm_chat")
            pass
    # fallback mock
    return f"[MOCK DRAFT]\n{prompt[:500]}..."

@app.post("/draft")
def draft(req: DraftReq, request: Request):
    with LATENCY.labels("comms-svc","/draft","POST").time():
        try:
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
            result = {"draft": text}
            service.log_request(request, {"status": "success"})
            return result
        except Exception as e:
            service.log_error(e, "draft endpoint")
            raise