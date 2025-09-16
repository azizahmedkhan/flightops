import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'shared'))

from base_service import BaseService
from fastapi import Request
from pydantic import BaseModel
from typing import Dict, Any, List
from utils import REQUEST_COUNT, LATENCY, log_startup
from jinja2 import Template
import re

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

# Email template
EMAIL_TEMPLATE = Template("""
Subject: Update on your flight {{ flight_no }} - {{ date }}

Dear Valued Customer,

We sincerely apologize for the inconvenience caused by the delay to your flight {{ flight_no }} on {{ date }}.

**Current Status:**
{{ issue }}

**Impact:**
{{ impact_summary }}

**What we're doing:**
{{ options_summary }}

**Next Steps:**
- Please check your email for rebooking details
- Contact our customer service team if you have questions
- We'll provide regular updates on the situation

**Expected Resolution Time:**
Most passengers will be rebooked within 2 hours of the original departure time.

Thank you for your patience and understanding.

Best regards,
Air New Zealand Customer Service Team

---
**Policy References:**
{% for citation in policy_citations[:3] %}
- {{ citation }}
{% endfor %}
""")

# SMS template
SMS_TEMPLATE = Template("""
Air NZ: Flight {{ flight_no }} on {{ date }} is delayed due to {{ issue }}. 

Impact: {{ impact_summary }}

We're working to rebook you. Check email for details. ETA: 2h.

Questions? Call us.

Ref: {{ policy_citations[0] if policy_citations else "Standard policy" }}
""")

def pii_scrub(text: str) -> str:
    """Remove PII from text."""
    text = re.sub(r"[A-Z0-9]{6}(?=\b)", "[PNR]", text)
    text = re.sub(r"[\w\.-]+@[\w\.-]+", "[EMAIL]", text)
    text = re.sub(r"\+?\d[\d\s-]{6,}", "[PHONE]", text)
    return text

def llm_rewrite_for_tone(template_text: str, tone: str) -> str:
    """Optional AI-powered tone refinement."""
    if not OPENAI_API_KEY:
        return template_text
    
    try:
        from openai import OpenAI
        client = OpenAI(api_key=OPENAI_API_KEY)
        
        prompt = f"""Rewrite this airline communication to be more {tone} while keeping all factual information intact:

{template_text}

Make it sound more {tone} but keep the same structure and all details."""
        
        resp = client.chat.completions.create(
            model=CHAT_MODEL, 
            messages=[{"role":"user","content":prompt}]
        )
        return resp.choices[0].message.content
    except Exception as e:
        service.log_error(e, "llm_rewrite_for_tone")
        return template_text

def render_template(context: Dict[str, Any], channel: str) -> str:
    """Render the appropriate template based on channel."""
    # Prepare context with defaults
    template_context = {
        "flight_no": context.get("flight_no", "NZ123"),
        "date": context.get("date", "2025-09-17"),
        "issue": context.get("issue", "operational delay"),
        "impact_summary": context.get("impact_summary", "Passengers affected"),
        "options_summary": context.get("options_summary", "Rebooking in progress"),
        "policy_citations": context.get("policy_citations", [])
    }
    
    if channel.lower() == "sms":
        template = SMS_TEMPLATE
    else:
        template = EMAIL_TEMPLATE
    
    return template.render(**template_context)

@app.post("/draft")
def draft(req: DraftReq, request: Request):
    """Generate communication using templates with optional AI tone refinement."""
    with LATENCY.labels("comms-svc","/draft","POST").time():
        try:
            # Render template first
            template_text = render_template(req.context, req.channel)
            
            # Apply PII scrubbing
            scrubbed_text = pii_scrub(template_text)
            
            # Optional AI tone refinement
            if OPENAI_API_KEY and req.tone != "standard":
                final_text = llm_rewrite_for_tone(scrubbed_text, req.tone)
            else:
                final_text = scrubbed_text
            
            result = {
                "draft": final_text,
                "template_used": req.channel,
                "tone_applied": req.tone,
                "ai_enhanced": bool(OPENAI_API_KEY and req.tone != "standard")
            }
            
            service.log_request(request, {"status": "success", "channel": req.channel, "tone": req.tone})
            return result
            
        except Exception as e:
            service.log_error(e, "draft endpoint")
            raise