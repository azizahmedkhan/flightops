from fastapi import FastAPI, HTTPException
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import os, psycopg, httpx, json
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
from utils import LATENCY, log_startup

SERVICE="agent-svc"

DB_HOST=os.getenv("DB_HOST","localhost")
DB_PORT=int(os.getenv("DB_PORT","5432"))
DB_NAME=os.getenv("DB_NAME","flightops")
DB_USER=os.getenv("DB_USER","postgres")
DB_PASS=os.getenv("DB_PASS","postgres")
RETRIEVAL_URL=os.getenv("RETRIEVAL_URL","http://localhost:8081")
COMMS_URL=os.getenv("COMMS_URL","http://localhost:8083")
ALLOW_UNGROUNDED=os.getenv("ALLOW_UNGROUNDED_ANSWERS","false").lower() == "true"

app = FastAPI(title="agent-svc")

class Ask(BaseModel):
    question: str
    flight_no: Optional[str] = None
    date: Optional[str] = None

def pii_scrub(text: str) -> str:
    import re
    text = re.sub(r"[A-Z0-9]{6}(?=\b)", "[PNR]", text)
    text = re.sub(r"[\w\.-]+@[\w\.-]+", "[EMAIL]", text)
    text = re.sub(r"\+?\d[\d\s-]{6,}", "[PHONE]", text)
    return text

def tool_flight_lookup(flight_no: str, date: str) -> Dict[str, Any]:
    with psycopg.connect(host=DB_HOST,port=DB_PORT,dbname=DB_NAME,user=DB_USER,password=DB_PASS) as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT flight_no, origin, destination, sched_dep, sched_arr, status
                FROM flights
                WHERE flight_no=%s AND flight_date=%s
            """, (flight_no, date))
            row = cur.fetchone()
            if not row:
                return {}
            return {"flight_no":row[0], "origin":row[1], "destination":row[2],
                    "sched_dep":row[3], "sched_arr":row[4], "status":row[5]}

def tool_impact_assessor(flight_no: str, date: str) -> Dict[str, Any]:
    with psycopg.connect(host=DB_HOST,port=DB_PORT,dbname=DB_NAME,user=DB_USER,password=DB_PASS) as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT COUNT(*)
                FROM bookings
                WHERE flight_no=%s AND flight_date=%s
            """, (flight_no, date))
            pax = cur.fetchone()[0]
            cur.execute("""
                SELECT COUNT(*)
                FROM crew_roster
                WHERE flight_no=%s AND flight_date=%s
            """, (flight_no, date))
            crew = cur.fetchone()[0]
    return {"passengers": pax, "crew": crew, "summary": f"{pax} passengers and {crew} crew affected."}

def tool_rebooking_optimizer(flight_no: str, date: str) -> List[Dict[str, Any]]:
    # heuristic: create two fake options with simple trade-offs
    return [
        {"plan":"Rebook on next NZ service + meal voucher", "cx_score":0.82, "cost_estimate": 120 * 50, "notes":"Minimizes missed connections"},
        {"plan":"Split pax across NZ + partner airline", "cx_score":0.77, "cost_estimate": 90 * 50, "notes":"Lower cost, more complexity"},
    ]

def tool_policy_grounder(question: str, k:int=3) -> Dict[str, Any]:
    try:
        r = httpx.post(f"{RETRIEVAL_URL}/search", json={"q":question, "k":k})
        results = r.json().get("results", [])
        cits = [f"{x.get('title')}: {x.get('snippet')}" for x in results]
        return {"citations": cits}
    except Exception:
        return {"citations": []}

def ensure_grounded(citations: List[str]) -> bool:
    if ALLOW_UNGROUNDED: return True
    return len(citations) > 0

@app.get("/health")
def health(): return {"ok": True}

@app.get("/metrics")
def metrics(): return PlainTextResponse(generate_latest(), media_type=CONTENT_TYPE_LATEST)

@app.post("/ask")
def ask(body: Ask):
    with LATENCY.labels(SERVICE,"/ask","POST").time():
        q = pii_scrub(body.question)
        fno = body.flight_no or "NZ123"
        date = body.date or "2025-09-17"

        flight = tool_flight_lookup(fno, date)
        impact = tool_impact_assessor(fno, date)
        options = tool_rebooking_optimizer(fno, date)
        policy = tool_policy_grounder(q + " policy rebooking compensation customer communication")

        if not ensure_grounded(policy.get("citations", [])):
            raise HTTPException(status_code=400, detail="Unable to verify policy grounding for this question.")

        options_summary = "; ".join([f"{o['plan']} (cx={o['cx_score']:.2f}, cost≈${o['cost_estimate']})" for o in options])
        payload = {
            "flight": flight,
            "impact": impact,
            "options": options,
            "policy_citations": policy.get("citations", []),
        }
        return {"answer": {
                    "issue": f"Delay/disruption for {fno} on {date}",
                    "impact_summary": impact["summary"],
                    "options_summary": options_summary,
                    "citations": policy.get("citations", [])
                },
                "tools_payload": payload}

@app.post("/draft_comms")
def draft_comms(body: Ask):
    # Compose with comms-svc using grounded context
    q = body.question or "Draft email + SMS for affected passengers"
    fno = body.flight_no or "NZ123"
    date = body.date or "2025-09-17"
    impact = tool_impact_assessor(fno, date)
    options = tool_rebooking_optimizer(fno, date)
    policy = tool_policy_grounder(q)
    if not ensure_grounded(policy.get("citations", [])):
        raise HTTPException(status_code=400, detail="Policy grounding required.")

    context = {
        "flight_no": fno, "date": date,
        "issue":"Weather-related delay",
        "impact_summary": impact["summary"],
        "options_summary": "; ".join([o["plan"] for o in options]),
        "policy_citations": policy.get("citations", [])
    }
    r = httpx.post(f"{COMMS_URL}/draft", json={"context": context, "tone":"empathetic", "channel":"email"}, timeout=60.0)
    return {"context": context, "draft": r.json().get("draft")}
