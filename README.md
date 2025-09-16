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


Gateway: http://localhost:8080/docs

Retrieval: http://localhost:8081/docs

Agent: http://localhost:8082/docs

Comms: http://localhost:8083/docs

Ingest: http://localhost:8084/docs

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

Kagle Flight Delay Dat
https://www.kaggle.com/datasets/sriharshaeedala/airline-delay/data

## Use Of AI
The AI is not just a chatbot. It's a cognitive orchestrator that automates the four critical tasks an airline operator would otherwise do manually and slowly:

Triage & Synthesis: Instead of the operator manually checking 5 different systems (flight status, passenger bookings, crew roster, weather, maintenance), the AI agent uses tools to instantly pull all that siloed data and the LLM synthesizes it into a single, human-readable summary: "NZ123 is delayed by 2 hours due to wind shear. This affects 214 passengers, 45 with critical connections, and puts the crew at risk of timing out."

Instant Policy Expertise (RAG): The operator doesn't need to frantically search through a 300-page PDF for the correct procedure. They ask, "What's the SOP for ground delays over 90 minutes?" The AI uses RAG to instantly find the exact clause from the internal manuals and provides the answer with citations, ensuring compliance.

Solution Generation & Analysis: Finding the "best" solution is a massive combinatorial problem. The AI agent automates the grunt work by calling multiple tools to:

Find optimal rebooking paths for all 214 passengers.

Estimate the cost of each option (hotel vouchers, overtime pay, etc.).

Check for available aircraft and crew.
It then uses the LLM's reasoning to present a ranked list of solutions with pros and cons.

Automated Communication: The operator doesn't have to manually draft 3 different types of messages. The AI generates context-aware, policy-compliant communications for passengers (empathetic, with compensation info), crew (operational details), and ground staff (instructions).

In short, the AI's job is to compress a 45-minute, high-stress, error-prone manual workflow into a 90-second, data-driven, guided process. It's about speed, accuracy, and reducing cognitive load on the human operator.

Of course. Let's get into a precise, step-by-step implementation plan. We'll focus on creating a robust foundation for your demo.

Step 1: Data Setup & Enhancement (The Foundation)
Your initial data schema is good, but we can make it much more powerful for this specific IRROPs use case.

A) Enhance Your Data Schema:
Yes, you should add more fields and one more data type. This will make the agent's impact assessment far more realistic.

flights table: Your schema is good. Let's add tail_number to link to a specific aircraft.

flight_no, flight_date, origin, destination, sched_dep_time, sched_arr_time, status, tail_number

bookings table: This is critical. Add a field for connecting flights. This is the source of most IRROPs pain.

flight_no, flight_date, pnr, passenger_name, has_connection (boolean), connecting_flight_no (nullable)

crew_roster table: Good start.

flight_no, flight_date, crew_id, crew_role (e.g., Captain, First Officer, Cabin Crew)

NEW crew_details table: You need to know if the crew will "time out." This is a major constraint.

crew_id, crew_name, duty_start_time, max_duty_hours

NEW aircraft_status table: Is the plane even available?

tail_number, current_location, status (e.g., 'Ready', 'Maintenance', 'In-Flight')

B) Correcting the Policy Format:
You mentioned "policies in md5 format." I believe you mean Markdown (.md) format. This is the correct choice. MD5 is a hashing algorithm, whereas Markdown is a text format perfect for documents. Use .md files for your policies, as they are easy to parse and chunk for the RAG system.

Step 2: Storage Strategy (Postgres is Your Best Friend)
You asked whether to store data in a vector DB or in Postgres. For this MVP, the answer is blunt:

Use Postgres with the pgvector extension for everything.

Here's why:

Simplicity: You manage one database, not two. This radically simplifies your Docker Compose setup and application code.

Hybrid Power: Your agent needs to perform two types of queries:

Structured Queries: "Find all passengers on NZ123 with a connection." (Perfect for standard SQL).

Unstructured (Semantic) Queries: "Find the policy section about passenger compensation for weather delays." (Perfect for vector search).

Efficiency: Postgres + pgvector lets you do both in the same database, sometimes even in the same query. It's the most efficient architecture for a RAG + structured data application like this.

Your Postgres setup will look like this:

Standard Tables: flights, bookings, crew_roster, crew_details, aircraft_status.

A "Policies" Table with a Vector Column:

id (PK), content (text of the policy chunk), source_document (e.g., 'passenger_compensation.md'), embedding (a vector type column from pgvector).

Step 3: Triggering the Scenario
You asked: "Now delayed a flight in the UI to test?"

No, do not build functionality to actually change the database from the UI. That's too complex. The best way to trigger the test is with a Scenario Selector in your React UI.

Create a dropdown menu in the UI with pre-canned scenarios.

Scenario 1: Severe Wind at AKL delays NZ123

Scenario 2: Crew Sickness grounds UA456

Scenario 3: Maintenance issue on plane XA-BC1

When you select a scenario, the UI does two things:

It sends a hardcoded, detailed prompt to your backend API. For Scenario 1, it would send: "There is severe wind at AKL, causing a 2-hour delay for flight NZ123 departing today, September 17, 2025. What is the full impact, what are our rebooking options, and what communications should we send?"

The UI can visually update the status of flight NZ123 to "Delayed" on the screen to make the demo feel interactive, but this is a front-end-only change.

This approach is simple, reliable, and focuses the effort on the AI backend, which is what you're trying to showcase.

1. What are the functionalities when a flight is delayed?

When the AI backend receives the prompt about the delay, it triggers a chain of functionalities:

Impact Assessment: It identifies all affected passengers, crew, and aircraft.

Constraint Checking: It checks for specific problems like passengers missing connections or crew exceeding their legal duty hours.

Policy & Procedure Lookup: It finds the company's official rules for handling this specific type of delay.

Solution Generation: It proposes concrete plans, like rebooking passengers on specific alternate flights.

Cost & Impact Analysis: It estimates the financial cost and customer experience score for each proposed solution.

Communication Drafting: It generates the exact text for emails and SMS messages to be sent to passengers and crew.

2. Which of those functionalities will use AI?

Here is the precise breakdown of AI usage:

The AI Agent (The "Brain"): The entire process is orchestrated by the AI agent. It receives the initial prompt, reasons about which of the functionalities above are needed, and decides which tools to call in what order. This orchestration is the primary use of AI.

Impact Assessment & Constraint Checking: These primarily use standard database queries (SQL), but the AI's LLM is used to synthesize the raw data from those queries into a natural language summary for the operator.

Policy & Procedure Lookup: This is a classic RAG (Retrieval-Augmented Generation) use case. The system performs a vector search to find relevant policy documents, and the AI's LLM summarizes the findings.

Solution Generation: The agent might call a non-AI tool like OR-Tools, but it uses the LLM's reasoning and world knowledge to frame the problem for the optimizer and to interpret the results (e.g., adding pros and cons).

Communication Drafting: This is a pure Generative AI task. The LLM takes all the context (the delay, the rebooking plan, the policy rules) and generates human-like, empathetic, and accurate text for the messages.

#Impact math = from your data, not AI.
Count affected bookings and crew from DB.
That’s deterministic logic in agent-svc (fast, reliable).

#Remedy rules = from policies, retrieved (RAG), not “decided” by AI.
retrieval-svc pulls the relevant policy snippets (citations).
You enforce: no citations ⇒ no action (guardrail).

#Communication wording = template first, AI optional.
comms-svc renders Email/SMS via template.
If a key is present, you may run a single AI rewrite to polish tone; otherwise skip.
So: we don’t ask AI to “figure out effects.” We compute impact with code, ground remedies in policy via retrieval, and optionally polish wording with AI.




## License
MIT
