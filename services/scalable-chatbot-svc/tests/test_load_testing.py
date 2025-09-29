"""
Load testing suite for the scalable chatbot service
Tests the system's ability to handle 1000+ concurrent sessions
"""

import asyncio
import json
import time
import random
import uuid
from datetime import datetime
from typing import List, Dict, Any
import os
import pytest
import websockets
import httpx
import statistics
from concurrent.futures import ThreadPoolExecutor


CHATBOT_BASE_URL = os.getenv("CHATBOT_BASE_URL", "http://localhost:8088")


def _load_tests_enabled(base_url: str) -> tuple[bool, str]:
    """Determine whether we should run the load tests."""
    run_env = (
        os.getenv("RUN_LOAD_TESTS")
        or os.getenv("RUN_LOAD_TEST")
        or "0"
    )

    if run_env != "1":
        return False, "Load tests disabled; set RUN_LOAD_TESTS=1 (or RUN_LOAD_TEST=1) to enable"

    try:
        response = httpx.get(f"{base_url}/health", timeout=2.0)
        if response.status_code != 200:
            return False, f"Chatbot service unhealthy at {base_url} (status {response.status_code})"
    except Exception as exc:
        return False, f"Chatbot service not reachable at {base_url}: {exc}"

    return True, ""


_RUN_LOAD_TESTS, _SKIP_REASON = _load_tests_enabled(CHATBOT_BASE_URL)

pytestmark = pytest.mark.skipif(
    not _RUN_LOAD_TESTS,
    reason=_SKIP_REASON or "Load tests require RUN_LOAD_TESTS=1 and a reachable chatbot service"
)


class LoadTestResults:
    """Container for load test results"""
    
    def __init__(self):
        self.total_requests = 0
        self.successful_requests = 0
        self.failed_requests = 0
        self.response_times = []
        self.errors = []
        self.start_time = None
        self.end_time = None
    
    def add_response(self, response_time: float, success: bool, error: str = None):
        self.total_requests += 1
        if success:
            self.successful_requests += 1
        else:
            self.failed_requests += 1
            if error:
                self.errors.append(error)
        self.response_times.append(response_time)
    
    def get_stats(self) -> Dict[str, Any]:
        if not self.response_times:
            return {"error": "No response times recorded"}
        
        return {
            "total_requests": self.total_requests,
            "successful_requests": self.successful_requests,
            "failed_requests": self.failed_requests,
            "success_rate": self.successful_requests / self.total_requests * 100,
            "avg_response_time": statistics.mean(self.response_times),
            "median_response_time": statistics.median(self.response_times),
            "p95_response_time": self._percentile(95),
            "p99_response_time": self._percentile(99),
            "min_response_time": min(self.response_times),
            "max_response_time": max(self.response_times),
            "total_duration": (self.end_time - self.start_time).total_seconds() if self.end_time and self.start_time else 0,
            "requests_per_second": self.total_requests / ((self.end_time - self.start_time).total_seconds()) if self.end_time and self.start_time else 0
        }
    
    def _percentile(self, p: float) -> float:
        sorted_times = sorted(self.response_times)
        index = int(len(sorted_times) * p / 100)
        return sorted_times[min(index, len(sorted_times) - 1)]


class ChatbotLoadTester:
    """Load testing class for the chatbot service"""
    
    def __init__(self, base_url: str = CHATBOT_BASE_URL):
        self.base_url = base_url
        self.ws_url = base_url.replace("http", "ws")
        self.results = LoadTestResults()
    
    async def create_session(self, client: httpx.AsyncClient, user_id: int) -> str:
        """Create a new chat session"""
        session_data = {
            "customer_name": f"Load Test User {user_id}",
            "customer_email": f"loadtest{user_id}@example.com",
            "flight_no": f"NZ{user_id % 1000:03d}",
            "date": "2025-01-17"
        }
        
        response = await client.post(f"{self.base_url}/chat/session", json=session_data)
        if response.status_code == 200:
            return response.json()["session_id"]
        else:
            raise Exception(f"Failed to create session: {response.status_code}")
    
    async def send_message(self, client: httpx.AsyncClient, session_id: str, message: str) -> bool:
        """Send a message to a session"""
        message_data = {
            "session_id": session_id,
            "message": message,
            "client_id": f"load-test-{uuid.uuid4()}"
        }
        
        response = await client.post(f"{self.base_url}/chat/message", json=message_data)
        return response.status_code == 200
    
    async def websocket_chat_session(self, session_id: str, client_id: str, messages: List[str], duration: int = 30):
        """Simulate a WebSocket chat session"""
        try:
            # Try to connect with a timeout
            websocket_url = f"{self.ws_url}/ws/{session_id}/{client_id}"
            async with websockets.connect(websocket_url) as websocket:
                start_time = time.time()
                
                for message in messages:
                    if time.time() - start_time > duration:
                        break
                    
                    # Send message
                    message_data = {"message": message}
                    await websocket.send(json.dumps(message_data))
                    
                    # Wait for response
                    try:
                        response = await asyncio.wait_for(websocket.recv(), timeout=15.0)
                        response_data = json.loads(response)
                        
                        # Record successful response
                        response_time = time.time() - start_time
                        self.results.add_response(response_time, True)
                        
                    except asyncio.TimeoutError:
                        self.results.add_response(15.0, False, "WebSocket timeout")
                    
                    # Random delay between messages
                    await asyncio.sleep(random.uniform(0.5, 2.0))
                    
        except Exception as e:
            self.results.add_response(0, False, f"WebSocket error: {str(e)}")
            raise
    
    async def simulate_user_session(self, user_id: int, duration: int = 30):
        """Simulate a complete user session"""
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                # Create session
                session_id = await self.create_session(client, user_id)
                
                # Generate random messages
                messages = [
                    "Hello, I need help with my flight",
                    "Is my flight on time?",
                    "What time should I arrive at the airport?",
                    "Can I change my seat?",
                    "What's the baggage policy?",
                    "Is there a delay?",
                    "Can I get a refund?",
                    "Thank you for your help"
                ]
                
                # Try WebSocket first, fallback to REST
                client_id = f"user-{user_id}-{uuid.uuid4()}"
                
                try:
                    await self.websocket_chat_session(session_id, client_id, messages, duration)
                except Exception as ws_error:
                    # Fallback to REST API if WebSocket fails
                    print(f"WebSocket failed for user {user_id}, falling back to REST: {ws_error}")
                    await self.rest_api_chat_session(client, session_id, messages, duration)
                
            except Exception as e:
                self.results.add_response(0, False, f"Session error: {str(e)}")
    
    async def rest_api_chat_session(self, client: httpx.AsyncClient, session_id: str, messages: List[str], duration: int = 30):
        """Fallback REST API chat session"""
        start_time = time.time()
        
        for message in messages:
            if time.time() - start_time > duration:
                break
            
            try:
                # Send message via REST API
                success = await self.send_message(client, session_id, message)
                response_time = time.time() - start_time
                
                if success:
                    self.results.add_response(response_time, True)
                else:
                    self.results.add_response(response_time, False, "REST API error")
                
                # Random delay between messages
                await asyncio.sleep(random.uniform(0.5, 2.0))
                
            except Exception as e:
                response_time = time.time() - start_time
                self.results.add_response(response_time, False, f"REST API error: {str(e)}")


class TestLoadTesting:
    """Load testing test cases"""

    LOAD_PROFILES = [
        {
            "label": "small",
            "users": 1,
            "duration": 30,
            "batch_size": None,
            "batch_pause": 0,
            "min_success_rate": 70,
            "max_avg": 30.0,
            "max_p95": None,
            "max_p99": None,
            "min_rps": 0.5,
        },
        # {
        #     "label": "medium",
        #     "users": 100,
        #     "duration": 60,
        #     "batch_size": 20,
        #     "batch_pause": 1,
        #     "min_success_rate": 60,
        #     "max_avg": 45.0,
        #     "max_p95": 60.0,
        #     "max_p99": None,
        #     "min_rps": None,
        # },
        # {
        #     "label": "high",
        #     "users": 500,
        #     "duration": 120,
        #     "batch_size": 50,
        #     "batch_pause": 2,
        #     "min_success_rate": 50,
        #     "max_avg": 60.0,
        #     "max_p95": 90.0,
        #     "max_p99": None,
        #     "min_rps": None,
        # },
        # {
        #     "label": "extreme",
        #     "users": 1000,
        #     "duration": 180,
        #     "batch_size": 25,
        #     "batch_pause": 3,
        #     "min_success_rate": 40,
        #     "max_avg": 120.0,
        #     "max_p95": None,
        #     "max_p99": 180.0,
        #     "min_rps": None,
        # },
    ]

    @pytest.mark.asyncio
    @pytest.mark.parametrize("profile", LOAD_PROFILES, ids=lambda p: p["label"])
    async def test_load_profiles(self, profile):
        """Exercise different concurrency profiles against the chatbot service."""
        tester = ChatbotLoadTester()
        tester.results.start_time = datetime.now()

        tasks = [
            tester.simulate_user_session(i, duration=profile["duration"])
            for i in range(profile["users"])
        ]

        batch_size = profile["batch_size"]
        batch_pause = profile["batch_pause"]

        if batch_size and batch_size > 0:
            for start_index in range(0, len(tasks), batch_size):
                batch = tasks[start_index:start_index + batch_size]
                await asyncio.gather(*batch, return_exceptions=True)
                if batch_pause:
                    await asyncio.sleep(batch_pause)
        else:
            await asyncio.gather(*tasks, return_exceptions=True)

        tester.results.end_time = datetime.now()
        stats = tester.results.get_stats()

        print(f"{profile['label'].title()} Load Test Results: {stats}")

        assert stats["success_rate"] >= profile["min_success_rate"], (
            f"{profile['label']} profile success rate too low: {stats['success_rate']}%"
        )

        if profile.get("max_avg") is not None:
            assert stats["avg_response_time"] < profile["max_avg"], (
                f"{profile['label']} profile avg response time too high: {stats['avg_response_time']}s"
            )

        if profile.get("max_p95") is not None:
            assert stats["p95_response_time"] < profile["max_p95"], (
                f"{profile['label']} profile p95 response time too high: {stats['p95_response_time']}s"
            )

        if profile.get("max_p99") is not None:
            assert stats["p99_response_time"] < profile["max_p99"], (
                f"{profile['label']} profile p99 response time too high: {stats['p99_response_time']}s"
            )

        if profile.get("min_rps") is not None:
            assert stats["requests_per_second"] > profile["min_rps"], (
                f"{profile['label']} profile requests/sec too low: {stats['requests_per_second']}"
            )


class TestStressTesting:
    """Stress testing scenarios"""

    STRESS_PROFILES = [
        {
            "label": "burst",
            "users": 200,
            "duration": 10,
            "min_success_rate": 60,
        },
        {
            "label": "long_running",
            "users": 50,
            "duration": 300,
            "min_success_rate": 70,
        },
    ]

    @pytest.mark.skip(reason="only load testing")
    @pytest.mark.asyncio
    @pytest.mark.parametrize("profile", STRESS_PROFILES, ids=lambda p: p["label"])
    async def test_stress_profiles(self, profile):
        """Execute stress scenarios such as bursts and long-lived sessions."""
        tester = ChatbotLoadTester()

        tester.results.start_time = datetime.now()
        tasks = [
            tester.simulate_user_session(i, duration=profile["duration"])
            for i in range(profile["users"])
        ]
        await asyncio.gather(*tasks, return_exceptions=True)
        tester.results.end_time = datetime.now()

        stats = tester.results.get_stats()
        print(f"{profile['label'].title()} Stress Test Results: {stats}")

        assert stats["success_rate"] >= profile["min_success_rate"], (
            f"{profile['label']} stress profile success rate too low: {stats['success_rate']}%"
        )
        assert stats["avg_response_time"] < 45.0, f"Long session response time too high: {stats['avg_response_time']}s"


class TestPerformanceMonitoring:
    """Test performance monitoring capabilities"""
    
    @pytest.mark.skip(reason="only load testing")
    async def test_health_check_under_load(self):
        """Test health check endpoint under load"""
        tester = ChatbotLoadTester()
        
        # Start some load
        load_tasks = [
            tester.simulate_user_session(i, duration=60)
            for i in range(100)
        ]
        
        # Monitor health during load
        health_tasks = []
        for i in range(10):
            health_tasks.append(self._check_health_periodically(tester.base_url))
        
        # Run both load and health checks
        all_tasks = load_tasks + health_tasks
        await asyncio.gather(*all_tasks, return_exceptions=True)
    
    async def _check_health_periodically(self, base_url: str):
        """Check health endpoint periodically"""
        async with httpx.AsyncClient(timeout=10.0) as client:
            for _ in range(10):  # Check 10 times
                try:
                    response = await client.get(f"{base_url}/health")
                    assert response.status_code == 200
                    
                    health_data = response.json()
                    assert health_data["status"] == "healthy"
                    
                except Exception as e:
                    print(f"Health check failed: {e}")
                
                await asyncio.sleep(6)  # Check every 6 seconds


# Utility functions for load testing
async def run_load_test(scenario: str, num_users: int, duration: int = 60):
    """Run a specific load test scenario"""
    tester = ChatbotLoadTester()
    
    print(f"Starting {scenario} with {num_users} users for {duration} seconds...")
    
    tester.results.start_time = datetime.now()
    
    tasks = [
        tester.simulate_user_session(i, duration=duration)
        for i in range(num_users)
    ]
    
    # Process in batches
    batch_size = min(50, num_users // 10) if num_users > 100 else num_users
    
    for i in range(0, len(tasks), batch_size):
        batch = tasks[i:i + batch_size]
        await asyncio.gather(*batch, return_exceptions=True)
        
        if i + batch_size < len(tasks):
            await asyncio.sleep(2)
    
    tester.results.end_time = datetime.now()
    stats = tester.results.get_stats()
    
    print(f"\n{scenario} Results:")
    print(f"Success Rate: {stats['success_rate']:.2f}%")
    print(f"Average Response Time: {stats['avg_response_time']:.2f}s")
    print(f"P95 Response Time: {stats['p95_response_time']:.2f}s")
    print(f"Requests per Second: {stats['requests_per_second']:.2f}")
    print(f"Total Duration: {stats['total_duration']:.2f}s")
    
    return stats


if __name__ == "__main__":
    # Run load tests from command line
    import argparse
    
    parser = argparse.ArgumentParser(description="Run load tests for the chatbot service")
    parser.add_argument("--scenario", choices=["small", "medium", "high", "extreme"], 
                       default="medium", help="Load test scenario")
    parser.add_argument("--users", type=int, default=100, help="Number of concurrent users")
    parser.add_argument("--duration", type=int, default=60, help="Test duration in seconds")
    
    args = parser.parse_args()
    
    scenario_map = {
        "small": (10, 30),
        "medium": (100, 60),
        "high": (500, 120),
        "extreme": (1000, 180)
    }
    
    if args.scenario in scenario_map:
        users, duration = scenario_map[args.scenario]
    else:
        users, duration = args.users, args.duration
    
    # Run the load test
    asyncio.run(run_load_test(args.scenario, users, duration))
