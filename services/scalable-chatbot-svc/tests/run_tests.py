#!/usr/bin/env python3
"""
Test runner for the scalable chatbot service
Provides different test execution modes and reporting
"""

import asyncio
import argparse
import json
import sys
import time
from datetime import datetime
from typing import Dict, Any, List
import subprocess
import os

# Add the parent directory to the path
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from tests.test_client import ChatbotTestClient, ChatbotLoadTestClient
from tests.test_chatbot import TestChatbotService
from tests.test_load_testing import TestLoadTesting


class TestRunner:
    """Test runner for the chatbot service"""
    
    def __init__(self, base_url: str = "http://localhost:8088"):
        self.base_url = base_url
        self.results = {}
    
    async def run_unit_tests(self) -> Dict[str, Any]:
        """Run unit tests"""
        print("🧪 Running unit tests...")
        start_time = time.time()
        
        try:
            # Run pytest for unit tests
            result = subprocess.run([
                "python", "-m", "pytest", 
                "tests/test_chatbot.py", 
                "-v", "--tb=short"
            ], capture_output=True, text=True, cwd=os.path.dirname(__file__))
            
            duration = time.time() - start_time
            
            return {
                "status": "passed" if result.returncode == 0 else "failed",
                "duration": duration,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "return_code": result.returncode
            }
            
        except Exception as e:
            return {
                "status": "error",
                "duration": time.time() - start_time,
                "error": str(e)
            }
    
    async def run_integration_tests(self) -> Dict[str, Any]:
        """Run integration tests"""
        print("🔗 Running integration tests...")
        start_time = time.time()
        
        try:
            # Test basic functionality
            client = ChatbotTestClient(self.base_url)
            
            # Create session
            session_id = await client.create_session()
            
            # Connect and send message
            await client.connect_websocket()
            response = await client.send_message_websocket("Hello, test message")
            
            # Check health
            health = await client.health_check()
            
            await client.close()
            
            duration = time.time() - start_time
            
            return {
                "status": "passed",
                "duration": duration,
                "session_created": bool(session_id),
                "websocket_connected": True,
                "message_sent": response.get("complete_response") is not None,
                "health_check_passed": health.get("status") == "healthy"
            }
            
        except Exception as e:
            return {
                "status": "failed",
                "duration": time.time() - start_time,
                "error": str(e)
            }
    
    async def run_load_tests(self, num_users: int = 100, duration: int = 60) -> Dict[str, Any]:
        """Run load tests"""
        print(f"⚡ Running load tests with {num_users} users...")
        start_time = time.time()
        
        try:
            load_client = ChatbotLoadTestClient(self.base_url)
            
            results = await load_client.run_load_test(
                num_users=num_users,
                messages_per_user=5,
                duration=duration
            )
            
            test_duration = time.time() - start_time
            
            # Determine if test passed based on success rate
            success_rate = results.get("success_rate", 0)
            status = "passed" if success_rate >= 80 else "failed"
            
            return {
                "status": status,
                "duration": test_duration,
                "success_rate": success_rate,
                "total_users": num_users,
                "total_messages": results.get("total_messages_sent", 0),
                "total_responses": results.get("total_responses_received", 0),
                "total_errors": results.get("total_errors", 0),
                "statistics": results.get("statistics", {}),
                "errors": results.get("errors", [])[:10]  # First 10 errors
            }
            
        except Exception as e:
            return {
                "status": "failed",
                "duration": time.time() - start_time,
                "error": str(e)
            }
    
    async def run_stress_tests(self) -> Dict[str, Any]:
        """Run stress tests"""
        print("💥 Running stress tests...")
        start_time = time.time()
        
        try:
            # Test burst traffic
            load_client = ChatbotLoadTestClient(self.base_url)
            
            # Create many sessions quickly
            session_ids = await load_client.batch_create_sessions(200)
            
            # Test with high concurrency
            tasks = []
            for i, session_id in enumerate(session_ids[:50]):  # Use first 50 sessions
                client_id = f"stress-test-{i}"
                messages = ["Hello", "Help", "Thanks"]
                tasks.append(load_client.simulate_conversation(session_id, client_id, messages))
            
            # Run all tasks concurrently
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            duration = time.time() - start_time
            
            # Analyze results
            successful_results = [r for r in results if isinstance(r, dict) and not r.get("errors")]
            success_rate = len(successful_results) / len(results) * 100 if results else 0
            
            return {
                "status": "passed" if success_rate >= 70 else "failed",
                "duration": duration,
                "sessions_created": len(session_ids),
                "concurrent_tasks": len(tasks),
                "success_rate": success_rate,
                "successful_tasks": len(successful_results)
            }
            
        except Exception as e:
            return {
                "status": "failed",
                "duration": time.time() - start_time,
                "error": str(e)
            }
    
    async def run_websocket_tests(self) -> Dict[str, Any]:
        """Run WebSocket-specific tests"""
        print("🔌 Running WebSocket tests...")
        start_time = time.time()
        
        try:
            client = ChatbotTestClient(self.base_url)
            
            # Create session
            session_id = await client.create_session()
            
            # Test multiple WebSocket connections to same session
            connections = []
            for i in range(5):
                client_id = f"ws-test-{i}"
                ws = await client.connect_websocket()
                connections.append((client_id, ws))
            
            # Send messages from different connections
            responses = []
            for client_id, ws in connections:
                response = await client.send_message_websocket(f"Message from {client_id}")
                responses.append(response)
            
            await client.close()
            
            duration = time.time() - start_time
            
            return {
                "status": "passed",
                "duration": duration,
                "connections_created": len(connections),
                "messages_sent": len(responses),
                "all_responses_received": all(r.get("complete_response") for r in responses)
            }
            
        except Exception as e:
            return {
                "status": "failed",
                "duration": time.time() - start_time,
                "error": str(e)
            }
    
    async def run_all_tests(self, load_test_users: int = 100) -> Dict[str, Any]:
        """Run all tests"""
        print("🚀 Running comprehensive test suite...")
        
        all_results = {
            "timestamp": datetime.now().isoformat(),
            "base_url": self.base_url,
            "tests": {}
        }
        
        # Unit tests
        all_results["tests"]["unit"] = await self.run_unit_tests()
        
        # Integration tests
        all_results["tests"]["integration"] = await self.run_integration_tests()
        
        # WebSocket tests
        all_results["tests"]["websocket"] = await self.run_websocket_tests()
        
        # Load tests
        all_results["tests"]["load"] = await self.run_load_tests(load_test_users)
        
        # Stress tests
        all_results["tests"]["stress"] = await self.run_stress_tests()
        
        # Calculate overall status
        test_statuses = [test["status"] for test in all_results["tests"].values()]
        if all(status == "passed" for status in test_statuses):
            all_results["overall_status"] = "passed"
        elif any(status == "failed" for status in test_statuses):
            all_results["overall_status"] = "failed"
        else:
            all_results["overall_status"] = "error"
        
        return all_results
    
    def print_results(self, results: Dict[str, Any]):
        """Print test results in a formatted way"""
        print("\n" + "="*60)
        print("🧪 TEST RESULTS")
        print("="*60)
        
        print(f"Timestamp: {results.get('timestamp', 'Unknown')}")
        print(f"Base URL: {results.get('base_url', 'Unknown')}")
        print(f"Overall Status: {results.get('overall_status', 'Unknown').upper()}")
        
        print("\nTest Details:")
        print("-"*40)
        
        for test_name, test_result in results.get("tests", {}).items():
            status_emoji = "✅" if test_result["status"] == "passed" else "❌" if test_result["status"] == "failed" else "⚠️"
            print(f"{status_emoji} {test_name.upper()}: {test_result['status'].upper()}")
            print(f"   Duration: {test_result.get('duration', 0):.2f}s")
            
            # Print specific details based on test type
            if test_name == "load" and "success_rate" in test_result:
                print(f"   Success Rate: {test_result['success_rate']:.1f}%")
                if "statistics" in test_result:
                    stats = test_result["statistics"]
                    print(f"   Avg Response Time: {stats.get('avg_response_time', 0):.2f}s")
                    print(f"   P95 Response Time: {stats.get('p95_response_time', 0):.2f}s")
            
            elif test_name == "integration":
                print(f"   Session Created: {test_result.get('session_created', False)}")
                print(f"   WebSocket Connected: {test_result.get('websocket_connected', False)}")
                print(f"   Message Sent: {test_result.get('message_sent', False)}")
            
            elif test_name == "stress":
                print(f"   Sessions Created: {test_result.get('sessions_created', 0)}")
                print(f"   Concurrent Tasks: {test_result.get('concurrent_tasks', 0)}")
                print(f"   Success Rate: {test_result.get('success_rate', 0):.1f}%")
            
            if "error" in test_result:
                print(f"   Error: {test_result['error']}")
            
            print()
    
    def save_results(self, results: Dict[str, Any], filename: str = None):
        """Save test results to JSON file"""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"test_results_{timestamp}.json"
        
        with open(filename, 'w') as f:
            json.dump(results, f, indent=2)
        
        print(f"📁 Results saved to: {filename}")


async def main():
    """Main function"""
    parser = argparse.ArgumentParser(description="Test runner for scalable chatbot service")
    parser.add_argument("--url", default="http://localhost:8088", help="Base URL for the chatbot service")
    parser.add_argument("--test", choices=["unit", "integration", "load", "stress", "websocket", "all"], 
                       default="all", help="Type of test to run")
    parser.add_argument("--users", type=int, default=100, help="Number of users for load tests")
    parser.add_argument("--duration", type=int, default=60, help="Duration for load tests")
    parser.add_argument("--output", help="Output file for results")
    parser.add_argument("--verbose", action="store_true", help="Verbose output")
    
    args = parser.parse_args()
    
    runner = TestRunner(args.url)
    
    if args.test == "unit":
        results = {"tests": {"unit": await runner.run_unit_tests()}}
    elif args.test == "integration":
        results = {"tests": {"integration": await runner.run_integration_tests()}}
    elif args.test == "load":
        results = {"tests": {"load": await runner.run_load_tests(args.users, args.duration)}}
    elif args.test == "stress":
        results = {"tests": {"stress": await runner.run_stress_tests()}}
    elif args.test == "websocket":
        results = {"tests": {"websocket": await runner.run_websocket_tests()}}
    elif args.test == "all":
        results = await runner.run_all_tests(args.users)
    
    runner.print_results(results)
    
    if args.output:
        runner.save_results(results, args.output)
    
    # Exit with appropriate code
    overall_status = results.get("overall_status", "error")
    if overall_status == "passed":
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
