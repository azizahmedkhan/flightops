# AeroOps Copilot

## Project Overview

This project is a AeroOps Copilot, an AI-powered assistant for airlines to manage irregular operations (IRROPs). It is built with a microservices architecture using Python (FastAPI) for the backend services and a Next.js (React) frontend. The system leverages a PostgreSQL database with the pgvector extension for storing and querying both structured data and vector embeddings for Knowledge Augmented Generation (RAG).

The core functionalities include:
- **Operational Decision Support:** Assessing passenger and crew impact, generating rebooking options, and grounding recommendations in airline policies.
- **Customer Communication:** Drafting policy-compliant and empathetic communications.
- **Governance & Compliance:** Enforcing grounded answers, maintaining audit trails, and providing observability.

## Architecture

The project is composed of the following services:

- **`gateway-api`**: The main entry point for the application, routing requests to the appropriate backend services.
- **`agent-svc`**: The core agent that orchestrates the workflow, using tools to interact with other services and the database.
- **`knowledge-engine`**: Handles the Knowledge Augmented Generation (RAG) by performing hybrid search on documents and data.
- **`comms-svc`**: Responsible for generating grounded communications.
- **`ingest-svc`**: Ingests data and documents into the PostgreSQL database and builds the vector index.
- **`customer-chat-svc`**: A service for customer-facing chat functionality.
- **`predictive-svc`**: A service for predictive functionalities.
- **`crew-svc`**: A service for crew-related functionalities.
- **`web`**: The Next.js frontend application.
- **`db`**: A PostgreSQL database with the `pgvector` extension.
- **`redis`**: A Redis instance for caching and background jobs.

## Building and Running

The project is containerized using Docker and can be orchestrated with `docker-compose`.

**Prerequisites:**
- Docker and Docker Compose

**1. Configure Environment:**
Copy the example `.env.example` file to `.env` and add your `OPENAI_API_KEY` if you want to use OpenAI's models.

```bash
cp .env.example .env
```

**2. Build and Run:**
```bash
docker compose up --build
```

This will start all the services. You can access the web UI at [http://localhost:3000](http://localhost:3000) and the API gateway at [http://localhost:8080](http://localhost:8080).

**3. Ingest Data:**
Once the containers are running, you need to ingest the seed data and documents.

```bash
curl -X POST http://localhost:8084/ingest/seed
```

## Development Conventions

- **Backend:** The backend services are written in Python using the FastAPI framework. They follow a standard structure with `main.py` as the entry point. Dependencies are managed with `requirements.txt` files.
- **Frontend:** The frontend is a Next.js application written in TypeScript. It uses Tailwind CSS for styling. Dependencies are managed with `package.json`.
- **API:** The services communicate with each other through REST APIs. The `gateway-api` serves as the central entry point.
- **Observability:** Each service exposes a `/metrics` endpoint for Prometheus to scrape.
- **Testing:** The `README.md` does not explicitly mention a testing strategy, but the project structure suggests that tests could be added in a `tests` directory within each service.
