# Repository Guidelines

  ## Project Structure & Module Organization
  The repo is organized around containerized FastAPI services. `services/gateway-api`,
  `services/agent-svc`, `services/retrieval-svc`, `services/comms-svc`, and `services/ingest-
  svc` each expose a `main.py`, `utils.py`, and `Dockerfile` for their bounded context. Shared
  datasets and reference documents live under `data/csv` and `data/docs`. The React front end
  resides in `ui/web` (Vite + Tailwind). Docker and infra configs sit in `infra/`, including
  `docker-compose.yml` and optional Prometheus setup. Copy `.env.example` to `.env` at the
  root before running anything.

  ## Build, Test, and Development Commands
  Use Docker for the default workflow. `docker compose up --build` builds every service,
  Postgres (pgvector), Redis, and the UI. After containers are ready, seed the knowledge base
  with `curl -X POST http://localhost:8084/ingest/seed`. Tail logs with `docker compose logs
  -f gateway-api` (swap the service name as needed). For UI-only tweaks, `cd ui/web && npm
  install && npm run dev` serves the React client on port 5173.

  ## Coding Style & Naming Conventions
  Python services target 3.11—follow PEP 8 with 4-space indentation, descriptive snake_case
  function names, and typed Pydantic models for request/response schemas. Keep FastAPI routers
  slim by pushing helpers into `utils.py`. Prefer structured logging via Loguru. In the UI,
  stick with functional React components, camelCase hooks/handlers, and Tailwind utility
  classes grouped by layout → color → state.

  ## Testing Guidelines
  Add FastAPI unit tests with pytest and httpx’s AsyncClient; place them under `services/
  <service>/tests/test_*.py`. Run them in-container with `docker compose run --rm agent-svc
  pytest` (swap to the service you're targeting). For ingestion changes, include integration
  checks that validate seeded tables. UI behavior should be covered with Vitest + React
  Testing Library (`npm run test` once configured); snapshot anything that renders policy
  citations.

  ## Commit & Pull Request Guidelines
  Write imperative, present-tense commit subjects (e.g., `agent-svc: improve rebooking
  scoring`). Keep related backend and UI changes in separate commits. PRs should link the
  tracked issue, summarize service-level impacts, and note any new env vars or migrations.
  Attach screenshots or terminal recordings for UI changes and provide sample curl requests
  for API updates. Always rerun docker-compose smoke tests and include evidence in the PR
  body.