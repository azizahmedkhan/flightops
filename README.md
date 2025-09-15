# FlightOps Copilot — Business Functionality

**FlightOps Copilot** is an AI-powered assistant designed to help airlines manage **irregular operations (IRROPs)** such as delays, cancellations, and weather disruptions.  
It combines **retrieval-augmented generation (RAG)**, **tool-using agents**, and **enterprise guardrails** to support both operations staff and customer service teams.

### Key Business Use Cases
- **Operational Decision Support**  
  - Assess passenger and crew impact when a flight is delayed.  
  - Generate rebooking options with estimated costs and customer experience scores.  
  - Ground recommendations in official airline policies and safety SOPs.

- **Customer Communication**  
  - Draft empathetic and policy-compliant emails or SMS updates.  
  - Ensure communications cite official policies and follow approved templates.  
  - Redact sensitive data (PNRs, phone numbers, emails) before sending.

- **Governance & Compliance**  
  - Enforce “grounded answers only” — no advice without supporting policy citations.  
  - Maintain full audit trails: model version, prompts, citations, and decisions.  
  - Provide observability for token usage, latency, and guardrail rejections.

- **Enterprise Integration Ready**  
  - Microservices design for easy integration with airline systems (crew rostering, booking engines, customer messaging platforms).  
  - Cloud-native and containerized, deployable on AWS (Fargate, RDS, Bedrock) or other environments.  
  - Extensible agent framework for future tools (crew legality checks, cost impact models, weather feeds).

---

# FlightOps Copilot — IRROPs-in-a-Box

A production-style, **agentic GenAI** demo tailored for airline operations (e.g., Air New Zealand) to showcase:
- Python microservices (FastAPI) + Docker
- Retrieval Augmented Generation (RAG) with **pgvector**
- Agent with **tool calls** (flight lookup, impact assessment, rebooking options, comms drafting, policy grounding)
- Guardrails (PII redaction, prompt-injection filter, grounding + citations)
- Observability (structured logs + Prometheus metrics endpoints)
- Minimal React UI (Vite + Tailwind) for a crisp demo

> **Note:** LLM features use OpenAI by default via environment variables. If no key is provided, the app falls back to simple keyword retrieval & mock LLM responses so you can still demo end-to-end flows.

## Quick Start

### Prereqs
- Docker & Docker Compose
- (Optional) OpenAI key

### 1) Configure env
Copy the example env file and edit as needed:
```bash
cp .env.example .env
# edit .env to add OPENAI_API_KEY if available
```

### 2) Build & run
```bash
docker compose up --build
```

Services:
- http://localhost:8080 -> **gateway-api** (OpenAPI docs at `/docs`)
- http://localhost:8081 -> **retrieval-svc** (OpenAPI)
- http://localhost:8082 -> **agent-svc** (OpenAPI)
- http://localhost:8083 -> **comms-svc** (OpenAPI)
- http://localhost:5173 -> **web UI**

### 3) Ingest seed data & docs
Once containers are up:
```bash
# seed documents (policies/SOPs) and build vector index
curl -X POST http://localhost:8084/ingest/seed
```
> Alternatively, visit **gateway** `/demo/seed` to trigger in UI-friendly way.

### 4) Demo flow
Open the UI at http://localhost:5173. Choose a scenario (e.g., delay for NZ123) and chat:
- “What’s the passenger and crew impact for NZ123 on 2025-09-17?”
- “Propose top 2 rebooking options with pros/cons and cost.”
- “Draft email and SMS to affected passengers with citations to policy.”

### 5) Prometheus metrics
Each service exposes `/metrics`. You can add a Prometheus server to scrape these; configs included in `infra/prometheus/` (optional).

## Architecture
```
flightops-copilot/
  services/
    gateway-api/          # entrypoint + auth + routes
    retrieval-svc/        # RAG: hybrid search + citations
    agent-svc/            # tool-using agent orchestration
    comms-svc/            # grounded comms drafts
    ingest-svc/           # load datasets + docs -> pgvector
  ui/web/                 # React + Vite + Tailwind
  data/
    csv/                  # flights, bookings, crew, weather
    docs/                 # policies, SOPs, templates
  infra/
    docker-compose.yml
    prometheus/           # optional Prometheus config
```

## Env Vars
See `.env.example`:
- `OPENAI_API_KEY` — optional (enables real LLM + embeddings)
- `EMBEDDINGS_MODEL` — default `text-embedding-3-small`
- `CHAT_MODEL` — default `gpt-4o-mini`
- `DB_HOST`, `DB_NAME`, `DB_USER`, `DB_PASS` — database
- `REDIS_URL` — background jobs/cache (currently basic usage)
- `ALLOW_UNGROUNDED_ANSWERS=false` — require citations for policy answers

## Notes
- If you lack GPU/internet access in the container, embeddings fall back to keyword search.
- The “rebooking optimizer” uses a heuristic (no heavy OR-Tools) to keep images small.
- Replace OpenAI with AWS Bedrock by swapping the `llm.py` in each service (adapter provided stub).

## License
MIT
