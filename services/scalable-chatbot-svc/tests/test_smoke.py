"""Lightweight concurrency smoke test for the scalable chatbot service."""

from __future__ import annotations

import asyncio
import os
import uuid
from typing import List

import httpx
import pytest


DEFAULT_TIMEOUT = float(os.getenv("SMOKE_HTTP_TIMEOUT", "60"))
MAX_MESSAGE_RETRIES = int(os.getenv("SMOKE_MESSAGE_RETRIES", "3"))
CONCURRENCY_LIMIT = int(os.getenv("SMOKE_CONCURRENCY_LIMIT", "10"))


CHATBOT_BASE_URL = os.getenv("CHATBOT_BASE_URL", "http://localhost:8088")


def _smoke_tests_enabled(base_url: str) -> tuple[bool, str]:
    """Determine whether the smoke test should run."""
    run_flag = (
        os.getenv("RUN_LOAD_TESTS")
        or os.getenv("RUN_LOAD_TEST")
        or os.getenv("RUN_SMOKE_TESTS")
        or "0"
    )

    if run_flag != "1":
        return False, "Set RUN_LOAD_TESTS=1 (or RUN_LOAD_TEST/RUN_SMOKE_TESTS) to enable"

    try:
        response = httpx.get(f"{base_url}/health", timeout=2.0)
        if response.status_code != 200:
            return False, f"Chatbot health endpoint returned {response.status_code}"
    except Exception as exc:  # noqa: BLE001
        return False, f"Chatbot service unreachable at {base_url}: {exc}"

    return True, ""


_RUN_SMOKE_TESTS, _SKIP_REASON = _smoke_tests_enabled(CHATBOT_BASE_URL)

pytestmark = pytest.mark.skipif(
    not _RUN_SMOKE_TESTS,
    reason=_SKIP_REASON or "Chatbot service not ready for concurrency smoke test",
)


MESSAGES: List[str] = [
    "Hello there!",
    "Can you help me with my booking?",
    "Thanks for the info!",
]

SESSION_COUNT = 50


@pytest.mark.asyncio
async def test_concurrent_sessions_smoke() -> None:
    """Launch 50 concurrent sessions and send three messages each via REST."""

    timeout = httpx.Timeout(
        DEFAULT_TIMEOUT,
        connect=min(DEFAULT_TIMEOUT, 10.0),
        write=min(DEFAULT_TIMEOUT, 10.0),
        pool=DEFAULT_TIMEOUT,
        read=DEFAULT_TIMEOUT,
    )

    async with httpx.AsyncClient(base_url=CHATBOT_BASE_URL, timeout=timeout) as client:
        semaphore = asyncio.Semaphore(CONCURRENCY_LIMIT)

        async def run_session(idx: int) -> None:
            async with semaphore:
                session_payload = {
                    "customer_name": f"Smoke Test User {idx}",
                    "customer_email": f"smoke{idx}@example.com",
                    "flight_no": f"SM{idx:03d}",
                    "date": "2025-01-17",
                }

                session_resp = await client.post("/chat/session", json=session_payload)
                session_resp.raise_for_status()
                session_id = session_resp.json()["session_id"]

                for message in MESSAGES:
                    message_payload = {
                        "session_id": session_id,
                        "message": message,
                        "client_id": f"smoke-{idx}-{uuid.uuid4()}",
                    }

                    for attempt in range(1, MAX_MESSAGE_RETRIES + 1):
                        try:
                            message_resp = await client.post("/chat/message", json=message_payload)
                            message_resp.raise_for_status()
                        except (httpx.ReadTimeout, httpx.WriteTimeout) as exc:
                            if attempt == MAX_MESSAGE_RETRIES:
                                raise
                            await asyncio.sleep(1)
                        else:
                            break

                    # Yield control to allow other sessions to progress
                    await asyncio.sleep(0.05)

        results = await asyncio.gather(
            *(run_session(i) for i in range(SESSION_COUNT)),
            return_exceptions=True,
        )

    errors = [exc for exc in results if isinstance(exc, Exception)]
    assert not errors, f"Concurrency smoke test hit {len(errors)} errors: {errors!r}"
