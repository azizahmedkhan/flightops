# FlightOps Lean Architecture Proposal

## Goals Tailored for the Interview Demo
- Keep the story simple: one customer-facing service, one knowledge service, one ingestion worker.
- Make data and tool access obvious: embeddings and SQL sit together so the LLM sees identical truth sources.
- Preserve performance: asynchronous ingestion keeps demo traffic fast, while the knowledge service stays hot in memory (pgvector + cached SQL).
- Reduce moving parts so you can diagram it in minutes and answer "why" questions confidently.

## Core Services (3 Boxes You Can Draw)

### 1. Experience API (`experience-api`)
- Rolls up `gateway-api`, `agent-svc`, and `scalable-chatbot-svc` into a single FastAPI app with REST + WebSocket endpoints.
- Handles chat turns, routes tool calls, and streams responses back to the UI (`ui/web`).
- Uses shared prompt + logging utilities from `services/shared` (or a future `platform-core` package) to keep policies consistent.
- Only external dependency: the Knowledge Engine over HTTP; no direct DB connections to keep latency predictable.

### 2. Knowledge Engine (`knowledge-engine`)
- Combines what lives today in `retrieval-svc` + `db-router-svc` + embedding helpers.
- Responsibilities:
  - Hybrid retrieval (pgvector similarity + lightweight BM25 backup).
  - SQL tool execution with parameterized queries against Postgres (flight, crew, disruption tables).
  - LLM tool surface: `search_policies`, `lookup_flight`, `fetch_booking`, etc., all exposed through a single `/tools/*` API consumed by Experience API.
  - Token usage + performance telemetry pushed to Loguru + Postgres.
- Keeps an in-process cache (Redis optional) so repeated demo queries hit warm results.

### 3. Ingestion Worker (`ingestion-worker`)
- Lightweight worker (FastAPI or Celery runner) that watches `/data/docs` or an upload endpoint for markdown/CSV updates.
- Runs chunking + embedding jobs and writes straight into the Knowledge schema (`docs`, `doc_chunks`, `doc_embeddings`).
- Triggers invalidation callbacks on the Knowledge Engine (simple HTTP POST) so caches refresh without downtime.
- Keeps ingestion off the request path, which protects demo latency while still letting you show continuous learning.

## Supporting Pieces (Kept Minimal)
- **Shared Utilities**: existing `services/shared` code becomes a small Python package so both Experience API and Knowledge Engine import identical logging, prompt, and LLM clients.
- **Postgres**: single instance with two logical schemas—`core_ops` for operational data, `knowledge` for docs/embeddings.
- **Redis (optional)**: enable if you want cached retrieval results; otherwise the system still runs without extra explanation.

## Service Realignment Map (Old → New)

| Current Service | Destination | Rationale |
|-----------------|-------------|-----------|
| `gateway-api`, `agent-svc`, `scalable-chatbot-svc`, `customer-chat-svc` | `experience-api` | Single front door, simpler story, no cross-service chatter during demo. |
| `retrieval-svc`, `db-router-svc` (tooling portions) | `knowledge-engine` | Embeddings + SQL live together; exposes one toolbox for LLM calls. |
| `ingest-svc` | `ingestion-worker` | Background job runner; can be invoked manually before demo. |
| `comms-svc`, `crew-svc`, `predictive-svc` | Defer / keep offline | Optional for demo; wire in later if needed, but not part of core story. |

## Key Flows You Can Explain

### Chat Turn (Happy Path)
1. UI message hits `experience-api /chat`.
2. Experience API calls `knowledge-engine /tools/search_policies` and `/tools/lookup_flight` as needed.
3. Knowledge Engine runs embeddings + SQL in the same process, returns structured snippets with citations.
4. Experience API feeds snippets into LLM prompt, streams final answer back to UI, and logs telemetry.

### Data Refresh
1. New markdown drops into `/data/docs` or is uploaded via admin endpoint.
2. `ingestion-worker` detects file, chunks + embeds, writes to Postgres `knowledge` schema.
3. Worker notifies `knowledge-engine` → cache invalidated → next chat turn sees fresh data.

### Tool Execution Safety
- Experience API never touches the database directly; it calls Knowledge Engine with signed requests.
- Knowledge Engine owns parameterized SQL and input validation, so you can describe one guardrail surface during interviews.

## Why This Meets the Simplicity + Performance Goals
- **Single customer-facing box** (Experience API) keeps diagrams obvious and reduces coordination latency.
- **Embeddings + SQL co-located** eliminates cross-service hops during retrieval, making the demo snappy and easier to reason about.
- **Background ingestion** isolates slow work while still letting you demo continuous updates if asked.
- **Shared utilities package** means you talk about one logging/prompting story instead of repeating yourself per service.

## Implementation Sequence (4 Steps)
1. **Collapse to Experience API**: move chat routes + WebSocket streaming into one service; point UI at it.
2. **Stand up Knowledge Engine**: merge retrieval + SQL tooling; define `/tools/*` contract; point Experience API to it.
3. **Spin up Ingestion Worker**: adapt current `ingest-svc` scripts to push into `knowledge` schema and notify Knowledge Engine.
4. **Package Shared Utilities**: optional polish—bundle common code so the services stay small and interview-ready.

Run docker compose with just these three services (+ Postgres) for the interview to highlight the clear separation of responsibilities.
