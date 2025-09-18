import sys
import os
import re
from typing import Dict, Any, List, Optional

from fastapi import Request
from jinja2 import Template
from pydantic import BaseModel

sys.path.append(os.path.join(os.path.dirname(__file__), 'shared'))

from base_service import BaseService
from prompt_manager import PromptManager
from llm_tracker import LLMTracker
from llm_client import create_llm_client
from utils import REQUEST_COUNT, LATENCY, log_startup

# Initialize base service
service = BaseService("comms-svc", "1.0.0")
app = service.get_app()

# Get environment variables using the base service
CHAT_MODEL = service.get_env_var("CHAT_MODEL", "gpt-4o-mini")
OPENAI_API_KEY = service.get_env_var("OPENAI_API_KEY", "")

# Initialize LLM client
llm_client = create_llm_client("comms-svc", CHAT_MODEL)

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
    
    import time
    start_time = time.time()
    
    try:
        prompt = PromptManager.get_tone_rewrite_prompt(template_text, tone)
        
        content = llm_client.simple_completion(
            prompt=prompt,
            function_name="llm_rewrite_for_tone",
            metadata={
                "tone": tone
            }
        )
        
        return content
    except Exception as e:
        service.log_error(e, "llm_rewrite_for_tone")
        return template_text

def translate_communication(text: str, target_language: str, context: Dict[str, Any]) -> str:
    """Translate communication to target language with cultural adaptation"""
    if not OPENAI_API_KEY:
        return text  # Fallback to original text
    
    import time
    start_time = time.time()
    
    try:
        # Get cultural context for the language
        cultural_context = get_cultural_context(target_language)
        
        prompt = PromptManager.get_translation_prompt(text, target_language, context, cultural_context)
        
        content = llm_client.simple_completion(
            prompt=prompt,
            temperature=0.3,
            function_name="translate_communication",
            metadata={
                "target_language": target_language,
                "flight_no": context.get("flight_no")
            }
        )
        
        return content
    except Exception as e:
        service.log_error(e, "translate_communication")
        return text

def get_cultural_context(language: str) -> str:
    """Get cultural context for different languages"""
    contexts = {
        "Spanish": "Use formal 'usted' form, be warm but respectful, emphasize family considerations",
        "French": "Use formal language, be polite and elegant, mention service excellence",
        "German": "Be direct and efficient, emphasize punctuality and reliability",
        "Japanese": "Use very polite language, apologize profusely, emphasize customer service",
        "Chinese": "Be respectful and formal, emphasize harmony and understanding",
        "Korean": "Use honorific language, be very polite, emphasize respect for customers",
        "Portuguese": "Be warm and friendly, use informal but respectful tone",
        "Italian": "Be expressive and warm, emphasize passion for service",
        "Dutch": "Be direct but friendly, emphasize efficiency and honesty",
        "Arabic": "Use formal language, be respectful and hospitable"
    }
    return contexts.get(language, "Maintain professional tone and cultural sensitivity")

def generate_multilingual_comms(context: Dict[str, Any], target_languages: List[str], 
                              tone: str = "empathetic", channel: str = "email") -> Dict[str, Any]:
    """Generate communications in multiple languages"""
    # Generate base communication
    base_text = render_template(context, channel)
    
    # Apply tone refinement
    if OPENAI_API_KEY and tone != "standard":
        base_text = llm_rewrite_for_tone(base_text, tone)
    
    # Apply PII scrubbing
    base_text = pii_scrub(base_text)
    
    # Translate to target languages
    translations = {}
    for language in target_languages:
        try:
            translated = translate_communication(base_text, language, context)
            translations[language] = {
                "text": translated,
                "language": language,
                "confidence": 0.9  # Mock confidence score
            }
        except Exception as e:
            service.log_error(e, f"translation to {language}")
            translations[language] = {
                "text": base_text,  # Fallback to original
                "language": language,
                "confidence": 0.0,
                "error": "Translation failed"
            }
    
    return {
        "original": {
            "text": base_text,
            "language": "English",
            "confidence": 1.0
        },
        "translations": translations,
        "supported_languages": list(translations.keys())
    }

def render_template(context: Dict[str, Any], channel: str) -> str:
    """Render the appropriate template based on channel."""
    # Prepare context - all values should come from the request
    template_context = {
        "flight_no": context.get("flight_no"),
        "date": context.get("date"),
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

class MultilingualDraftReq(BaseModel):
    context: Dict[str, Any]
    target_languages: List[str]
    tone: str = "empathetic"
    channel: str = "email"

@app.post("/draft_multilingual")
def draft_multilingual(req: MultilingualDraftReq, request: Request):
    """Generate communications in multiple languages with cultural adaptation."""
    with LATENCY.labels("comms-svc", "/draft_multilingual", "POST").time():
        try:
            result = generate_multilingual_comms(
                req.context, 
                req.target_languages, 
                req.tone, 
                req.channel
            )
            
            service.log_request(request, {
                "status": "success", 
                "languages": len(req.target_languages),
                "channel": req.channel,
                "tone": req.tone
            })
            return result
            
        except Exception as e:
            service.log_error(e, "draft_multilingual endpoint")
            raise

class SentimentAnalysisReq(BaseModel):
    text: str
    context: Optional[Dict[str, Any]] = None

@app.post("/analyze_sentiment")
def analyze_sentiment(req: SentimentAnalysisReq, request: Request):
    """Analyze sentiment of customer communication."""
    with LATENCY.labels("comms-svc", "/analyze_sentiment", "POST").time():
        try:
            if not OPENAI_API_KEY:
                # Fallback to rule-based sentiment analysis
                sentiment_result = analyze_sentiment_rule_based(req.text)
            else:
                sentiment_result = analyze_sentiment_with_llm(req.text, req.context)
            
            service.log_request(request, {"status": "success", "sentiment": sentiment_result.get("sentiment")})
            return sentiment_result
            
        except Exception as e:
            service.log_error(e, "analyze_sentiment endpoint")
            raise

def analyze_sentiment_with_llm(text: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Use LLM to analyze sentiment of customer communication"""
    import time
    start_time = time.time()
    
    try:
        context_str = ""
        if context:
            context_str = f"Context: Flight {context.get('flight_no', 'Unknown')}, Issue: {context.get('issue', 'Unknown')}"
        
        prompt = PromptManager.get_sentiment_analysis_prompt(text, context)
        
        result = llm_client.json_completion(
            prompt=prompt,
            temperature=0.3,
            function_name="analyze_sentiment_with_llm",
            metadata={
                "flight_no": context.get("flight_no") if context else None,
                "text_length": len(text)
            },
            fallback_value=analyze_sentiment_rule_based(text)
        )
        
        return result
            
    except Exception as e:
        service.log_error(e, "LLM sentiment analysis")
        return analyze_sentiment_rule_based(text)

def analyze_sentiment_rule_based(text: str) -> Dict[str, Any]:
    """Fallback rule-based sentiment analysis"""
    text_lower = text.lower()
    
    # Simple keyword-based sentiment analysis
    positive_words = ["thank", "appreciate", "good", "excellent", "happy", "satisfied", "pleased"]
    negative_words = ["angry", "frustrated", "disappointed", "terrible", "awful", "hate", "complaint"]
    urgent_words = ["urgent", "immediately", "asap", "emergency", "critical", "now"]
    
    positive_count = sum(1 for word in positive_words if word in text_lower)
    negative_count = sum(1 for word in negative_words if word in text_lower)
    urgent_count = sum(1 for word in urgent_words if word in text_lower)
    
    # Determine sentiment
    if negative_count > positive_count:
        sentiment = "negative"
        sentiment_score = -0.5 - (negative_count * 0.1)
    elif positive_count > negative_count:
        sentiment = "positive"
        sentiment_score = 0.5 + (positive_count * 0.1)
    else:
        sentiment = "neutral"
        sentiment_score = 0.0
    
    # Determine urgency
    if urgent_count > 0:
        urgency = "high"
    elif negative_count > 2:
        urgency = "medium"
    else:
        urgency = "low"
    
    # Determine response tone
    if sentiment == "negative" and urgency == "high":
        response_tone = "urgent"
    elif sentiment == "negative":
        response_tone = "empathetic"
    else:
        response_tone = "professional"
    
    return {
        "sentiment": sentiment,
        "sentiment_score": max(-1.0, min(1.0, sentiment_score)),
        "emotions": ["frustration", "anger"] if sentiment == "negative" else ["satisfaction", "happiness"] if sentiment == "positive" else ["neutral"],
        "urgency_level": urgency,
        "recommended_tone": response_tone,
        "key_concerns": ["delays", "service"] if sentiment == "negative" else [],
        "analysis_method": "rule_based"
    }