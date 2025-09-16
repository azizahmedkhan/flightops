# Repository Guidelines

## Project Structure & Module Organization
The repository is organized around containerized FastAPI microservices under `services/`; each service exposes a `main.py`, `utils.py`, and `Dockerfile`. Domain datasets and reference docs live in `data/csv` and `data/docs`. Shared infrastructure such as `docker-compose.yml`, Prometheus scaffolding, and Terraform modules sit inside `infra/`. The React client resides in `ui/web`, while root-level tooling and environment templates support local orchestration.

## Build, Test, and Development Commands
- `docker compose up --build`: build every service along with Postgres (pgvector), Redis, and the UI.
- `curl -X POST http://localhost:8084/ingest/seed`: populate the knowledge base once containers are healthy.
- `docker compose logs -f gateway-api`: tail service logs; swap the service name for other containers.
- `cd ui/web && npm install && npm run dev`: install UI dependencies and launch the Vite dev server on port 5173.

## Coding Style & Naming Conventions
Target Python 3.11 and follow PEP 8 with 4-space indentation, snake_case helpers, and typed Pydantic models for request/response schemas. Keep FastAPI routers lean by pushing business logic into `utils.py` modules and prefer Loguru for structured logging. In the UI, ship functional React components, camelCase hooks/handlers, and Tailwind utility classes grouped layout → color → state.

## Testing Guidelines
Write FastAPI unit tests with pytest and httpx's `AsyncClient`; place them under `services/<service>/tests/test_*.py`. Execute them via `docker compose run --rm agent-svc pytest` (swap the target service). For ingestion flows, add integration assertions that confirm seeded tables. Cover UI behavior with Vitest and React Testing Library (`npm run test`) and snapshot components that render policy citations.

## Commit & Pull Request Guidelines
Use imperative, present-tense commit subjects like `agent-svc: improve rebooking scoring`, and keep backend and UI changes in separate commits. Pull requests must link the tracked issue, summarize service-level impacts, call out new environment variables or migrations, and attach screenshots or terminal captures for UI changes. Include sample curl requests for API updates and evidence of docker-compose smoke tests.

## Security & Configuration Tips
Copy `.env.example` to `.env` before local runs and store secrets outside version control. Prefer Docker secrets or environment variables when deploying. Rotate shared API tokens in `.env` and update dependent services promptly.
