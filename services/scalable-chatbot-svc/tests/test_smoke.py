"""Lightweight concurrency smoke test for the scalable chatbot service."""

from __future__ import annotations

import asyncio
import json
import os
import uuid
from typing import List

import httpx
import pytest
import websockets

DEFAULT_TIMEOUT = float(os.getenv("SMOKE_HTTP_TIMEOUT", "30"))  # 30 seconds for LLM processing
MAX_MESSAGE_RETRIES = int(os.getenv("SMOKE_MESSAGE_RETRIES", "2"))  # Keep at 2 retries
CONCURRENCY_LIMIT = int(os.getenv("SMOKE_CONCURRENCY_LIMIT", "100"))  # Reduce to 3 for stability
SESSION_COUNT = 100  # Testing higher concurrency

MESSAGES: List[str] = [
    "Hello there!",
    "Can you help me with my booking?",
    "When is the next flight to Wellington?",
    "I need information about flight NZ123 from Auckland to Sydney",
    "Thanks for the info!",
]

CHATBOT_BASE_URL = os.getenv("CHATBOT_BASE_URL", "http://localhost:8088")


def _smoke_tests_enabled() -> tuple[bool, str]:
    """Determine whether the smoke test should run."""
    run_load_tests = os.getenv("RUN_LOAD_TESTS")
    run_load_test = os.getenv("RUN_LOAD_TEST") 
    run_smoke_tests = os.getenv("RUN_SMOKE_TESTS")
    
    run_flag = run_load_tests or run_load_test or run_smoke_tests or "0"

    if run_flag != "1":
        return False, f"Set RUN_LOAD_TESTS=1 (or RUN_LOAD_TEST/RUN_SMOKE_TESTS) to enable. Current values: RUN_LOAD_TESTS={run_load_tests}, RUN_LOAD_TEST={run_load_test}, RUN_SMOKE_TESTS={run_smoke_tests}"

    # Don't check health at import time - do it in the test
    return True, ""


_RUN_SMOKE_TESTS, _SKIP_REASON = _smoke_tests_enabled()

pytestmark = pytest.mark.skipif(
    not _RUN_SMOKE_TESTS,
    reason=_SKIP_REASON or "Set RUN_LOAD_TESTS=1 to enable smoke tests",
)

@pytest.mark.asyncio
async def test_concurrent_sessions_smoke() -> None:
    """Launch concurrent sessions and send messages via WebSocket (the proper way)."""

    # Quick connectivity check first
    print(f"Testing connectivity to {CHATBOT_BASE_URL}...", flush=True)
    try:
        async with httpx.AsyncClient(timeout=2.0) as quick_client:
            health_resp = await quick_client.get(f"{CHATBOT_BASE_URL}/health")
            print(f"Health check: {health_resp.status_code}", flush=True)
    except Exception as exc:
        print(f"Connectivity check failed: {exc}", flush=True)
        pytest.fail(f"Cannot connect to chatbot service at {CHATBOT_BASE_URL}: {exc}")

    # Test a single session first
    print(f"\n🔍 DEBUGGING: Testing single WebSocket session first...", flush=True)
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            # Create session via REST
            session_payload = {
                "customer_name": "Debug User",
                "customer_email": "debug@example.com", 
                "flight_no": "DEBUG001",
                "date": "2025-01-17",
            }
            print("Test>>📤 Creating debug session...", flush=True)
            session_resp = await client.post(f"{CHATBOT_BASE_URL}/chat/session", json=session_payload)
            session_resp.raise_for_status()
            session_id = session_resp.json()["session_id"]
            print(f"✓ Debug session created: {session_id}", flush=True)
            
            # Connect via WebSocket
            client_id = "debug-client-123"
            ws_url = f"ws://{CHATBOT_BASE_URL.replace('http://', '')}/ws/{session_id}/{client_id}"
            print(f"🔌 Connecting to WebSocket: {ws_url}", flush=True)
            
            async with websockets.connect(ws_url, close_timeout=10) as websocket:
                print("Test>>✅ WebSocket connected", flush=True)
                
                # Send message
                message_data = {"message": "What are the baggage policies for domestic flights?"}
                print(f"📤 Sending message: {message_data}", flush=True)
                await websocket.send(json.dumps(message_data))
                
                # Wait for response
                print("Test>>⏳ Waiting for response...", flush=True)
                response_text = await asyncio.wait_for(websocket.recv(), timeout=30.0)
                response_data = json.loads(response_text)
                print(f"📥 Received: {response_data['type']} - {response_data.get('content', '')[:100]}", flush=True)
                
                # Collect complete response
                full_response = ""
                while True:
                    try:
                        response_text = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                        response_data = json.loads(response_text)
                        
                        if response_data["type"] == "chunk":
                            full_response += response_data["content"]
                        elif response_data["type"] == "complete":
                            full_response = response_data["content"]
                            print(f"✅ Complete response: {full_response[:200]}...", flush=True)
                            break
                    except asyncio.TimeoutError:
                        print("Test>>⏰ Response timeout", flush=True)
                        break
                
                print("Test>>✅ Debug test successful!", flush=True)
                
    except Exception as exc:
        print(f"❌ Debug test failed: {type(exc).__name__}: {exc}", flush=True)
        pytest.fail(f"Debug test failed: {exc}")
    
    print("Test>>✅ Debug test passed, proceeding with concurrency test...", flush=True)

    # Now run the concurrency test
    semaphore = asyncio.Semaphore(CONCURRENCY_LIMIT)

    async def run_session(idx: int) -> None:
        print(f"[SESSION {idx:02d}] 🔄 WAITING FOR SEMAPHORE...", flush=True)
        async with semaphore:
            try:
                print(f"[SESSION {idx:02d}] ===== STARTING SESSION {idx} =====", flush=True)
                
                # Create session via REST
                async with httpx.AsyncClient(timeout=5.0) as client:
                    session_payload = {
                        "customer_name": f"Smoke Test User {idx}",
                        "customer_email": f"smoke{idx}@example.com",
                        "flight_no": f"SM{idx:03d}",
                        "date": "2025-01-17",
                    }
                    
                    print(f"[SESSION {idx:02d}] 📤 Creating session...", flush=True)
                    session_resp = await client.post(f"{CHATBOT_BASE_URL}/chat/session", json=session_payload)
                    session_resp.raise_for_status()
                    session_id = session_resp.json()["session_id"]
                    print(f"[SESSION {idx:02d}] ✓ Session created: {session_id}", flush=True)

                # Connect via WebSocket
                client_id = f"smoke-{idx}-{uuid.uuid4()}"
                ws_url = f"ws://{CHATBOT_BASE_URL.replace('http://', '')}/ws/{session_id}/{client_id}"
                print(f"[SESSION {idx:02d}] 🔌 Connecting to WebSocket...", flush=True)
                
                async with websockets.connect(ws_url, close_timeout=10) as websocket:
                    print(f"[SESSION {idx:02d}] ✅ WebSocket connected", flush=True)

                    for msg_idx, message in enumerate(MESSAGES, 1):
                        print(f"[SESSION {idx:02d}] --- MESSAGE {msg_idx}/{len(MESSAGES)}: '{message}' ---", flush=True)
                        
                        # Send message
                        message_data = {"message": message}
                        print(f"[SESSION {idx:02d}] [MSG {msg_idx}] 📤 Sending message...", flush=True)
                        await websocket.send(json.dumps(message_data))
                        
                        # Collect response
                        full_response = ""
                        response_received = False
                        
                        for attempt in range(1, MAX_MESSAGE_RETRIES + 1):
                            try:
                                print(f"[SESSION {idx:02d}] [MSG {msg_idx}] Attempt {attempt}: Waiting for response...", flush=True)
                                
                                while True:
                                    response_text = await asyncio.wait_for(websocket.recv(), timeout=30.0)
                                    response_data = json.loads(response_text)
                                    
                                    if response_data["type"] == "chunk":
                                        full_response += response_data["content"]
                                        print(f"[SESSION {idx:02d}] [MSG {msg_idx}] 📝 Chunk: {response_data['content'][:50]}...", flush=True)
                                    elif response_data["type"] == "complete":
                                        full_response = response_data["content"]
                                        print(f"[SESSION {idx:02d}] [MSG {msg_idx}] ✅ Complete: {full_response[:100]}...", flush=True)
                                        response_received = True
                                        break
                                    elif response_data["type"] == "error":
                                        print(f"[SESSION {idx:02d}] [MSG {msg_idx}] ❌ Error: {response_data['content']}", flush=True)
                                        raise Exception(f"Chatbot error: {response_data['content']}")
                                
                                if response_received:
                                    break
                                    
                            except asyncio.TimeoutError:
                                print(f"[SESSION {idx:02d}] [MSG {msg_idx}] ⚠ TIMEOUT (attempt {attempt}/{MAX_MESSAGE_RETRIES})", flush=True)
                                if attempt == MAX_MESSAGE_RETRIES:
                                    raise
                                await asyncio.sleep(1)
                            except Exception as exc:
                                print(f"[SESSION {idx:02d}] [MSG {msg_idx}] ✗ ERROR (attempt {attempt}): {type(exc).__name__}: {exc}", flush=True)
                                if attempt == MAX_MESSAGE_RETRIES:
                                    raise
                                await asyncio.sleep(1)

                        print(f"[SESSION {idx:02d}] [MSG {msg_idx}] Completed message {msg_idx}/{len(MESSAGES)}", flush=True)
                        await asyncio.sleep(0.1)  # Small delay between messages
                    
                    print(f"[SESSION {idx:02d}] ===== SESSION {idx} COMPLETED SUCCESSFULLY =====", flush=True)

            except Exception as exc:
                print(f"[SESSION {idx:02d}] ❌ ERROR: {type(exc).__name__}: {exc}", flush=True)
                raise

    print(f"\n🚀 LAUNCHING {SESSION_COUNT} CONCURRENT SESSIONS...", flush=True)
    print(f"📊 Each session will send {len(MESSAGES)} messages via WebSocket (including flight info and policy queries)", flush=True)
    print(f"⚡ Concurrency limit: {CONCURRENCY_LIMIT} simultaneous sessions", flush=True)
    print("Test>>=" * 80, flush=True)
    
    # Start a progress tracker
    import time
    start_time = time.time()
    
    async def progress_tracker():
        while True:
            await asyncio.sleep(10)  # Print every 10 seconds
            elapsed = time.time() - start_time
            print(f"⏰ PROGRESS: {elapsed:.1f}s elapsed, test still running...", flush=True)
    
    # Start progress tracker in background
    progress_task = asyncio.create_task(progress_tracker())

    results = await asyncio.gather(
        *(run_session(i) for i in range(SESSION_COUNT)),
        return_exceptions=True,
    )
    
    # Cancel progress tracker
    progress_task.cancel()
    try:
        await progress_task
    except asyncio.CancelledError:
        pass

    print("Test>>\n" + "=" * 80, flush=True)
    print("Test>>📈 TEST RESULTS SUMMARY", flush=True)
    print("Test>>=" * 80, flush=True)
    
    successful_sessions = [i for i, result in enumerate(results) if not isinstance(result, Exception)]
    failed_sessions = [i for i, result in enumerate(results) if isinstance(result, Exception)]
    
    print(f"✅ Successful sessions: {len(successful_sessions)}/{SESSION_COUNT}", flush=True)
    print(f"❌ Failed sessions: {len(failed_sessions)}/{SESSION_COUNT}", flush=True)
    
    if failed_sessions:
        print(f"\n💥 Failed session IDs: {failed_sessions}", flush=True)
        for session_id in failed_sessions:
            error = results[session_id]
            print(f"   Session {session_id}: {error}", flush=True)

    errors = [exc for exc in results if isinstance(exc, Exception)]
    assert not errors, f"Concurrency smoke test hit {len(errors)} errors: {errors!r}"
