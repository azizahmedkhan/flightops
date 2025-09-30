# Scalable Chat Service – Solo Demo Script

> First-person narration for a 10-minute recorded walkthrough. Square brackets mark optional on-screen cues.

---

## 0. Hook (0:00 – 0:30)
I have built a scalable chat service that keeps hundreds of users chatting simultaneously without breaking a sweat. In the next few minutes I’ll walk you through how it stays fast, safe, and context-aware."

---

## 1. Architecture Snapshot (0:30 – 1:30)
"The code lives in `services/scalable-chatbot-svc`. On startup (`main.py` top-level) we initialize FastAPI, the WebSocket router, a Redis-backed cache, and our LLM client. This service is stateless by design; Redis acts as the shared memory so we can run as many replicas as traffic demands."

[Show slide: Client → WebSocket → Async Tasks → Redis + Knowledge/DB + LLM]

---

## 2. WebSocket Flow (1:30 – 3:00)
"Every live conversation rides through `/ws/{session_id}/{client_id}` (`main.py:111`). As soon as the socket opens, `ConnectionManager` stores it, tagging the session and last-activity timestamps (`connection_manager.py:12`). When a new message lands, we hand off processing to an async task using `asyncio.create_task`. That non-blocking hop is the foundation that lets thousands of sessions run in parallel."

[Highlight `asyncio.create_task(process_chat_message(...))` in editor]

---

## 3. Guardrails Before the LLM (3:00 – 4:00)
"Inside `process_chat_message` we apply three guardrails. First, grab the conversation state from Redis so we know context coming in (`redis_manager.py:25`). Second, enforce a per-session rate limit—30 requests per minute—so one chat can’t flood the model (`rate_limiter.py:9`). Third, look up a deterministic hash of the message in Redis; if we’ve answered it before, we serve that cached response instantly (`main.py:178`)."

[Optional: show Redis keys in CLI]

---

## 4. Streaming Replies (4:00 – 5:30)
"If it’s not cached, we call `generate_streaming_response`. The first thing we send back is a quick '🤔 Thinking…' chunk so the UI never freezes (`main.py:296`). Then we split the final message into three-word segments and stream them every 50 ms (`main.py:331`). That steady cadence keeps customers engaged while the LLM finishes composing."

[Live demo: browser chat showing incremental chunks]

---

## 5. Context Engineering Deep Dive (5:30 – 7:30)
"Here’s where accuracy comes from. We run `route_query` to classify intent—policy, database, or flight (`chatbot_toolkit.py:266`). Based on that tag we fetch the right data: policy snippets from the knowledge engine or operational facts from the DB router (`main.py:246`).

All of that context lands inside `create_air_nz_system_prompt` (`chatbot_toolkit.py:402`). The template injects session details—customer name, flight number—and hard rules like 'don’t invent information, always cite sources'. After the model responds, `format_air_nz_response` rewrites it into bullet points with footnotes and optional 'Heads up' warnings (`chatbot_toolkit.py:456`)."

[Show prompt template and formatter side-by-side]

---

## 6. Session Memory & Cleanup (7:30 – 8:30)
"Every answer updates the Redis session: last message, last response, message count, and any structured flight data (`main.py:371`). Because Redis stores JSON per session, any replica can serve the next request without missing context. A background coroutine sweeps stale sockets every five minutes, so idle browsers don’t tie up resources (`main.py:98`)."

---

## 7. Observability and Health (8:30 – 9:30)
"Ops teams get real-time insight via `/health` and `/stats`. `/health` confirms Redis connectivity and active connections, while `/stats` surfaces per-session metadata (`main.py:430`). Those endpoints feed dashboards that tell us when to scale up or if Redis ever slips."

[Run `curl http://localhost:8088/health`]

---

## 8. Wrap-Up (9:30 – 10:00)
"So that’s the scalable chat service in a nutshell: async WebSockets to stay reactive, Redis to share state, rate limiting and caching to control load, and disciplined context engineering to keep the LLM grounded. It’s been battle-tested past a thousand concurrent chats, and the patterns are reusable for any high-volume support workflow. Thanks for watching—happy to dig into any module you saw today."

---

## Recording Checklist
- [ ] Architecture slide visible during Section 1
- [ ] Code editor zoom on WebSocket + `asyncio.create_task`
- [ ] Redis CLI or logs shown when talking guardrails
- [ ] Live chat demo for streaming section
- [ ] Prompt template and formatted response highlighted together
- [ ] `curl /health` recorded near the end

