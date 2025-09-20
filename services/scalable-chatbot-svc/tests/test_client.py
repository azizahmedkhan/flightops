"""
Test client for the scalable chatbot service
Provides utilities for testing WebSocket and REST API interactions
"""

import asyncio
import json
import uuid
import websockets
import httpx
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ChatbotTestClient:
    """Test client for the scalable chatbot service"""
    
    def __init__(self, base_url: str = "http://localhost:8088"):
        self.base_url = base_url
        self.ws_url = base_url.replace("http", "ws")
        self.session_id = None
        self.client_id = None
        self.websocket = None
        self.responses = []
    
    async def create_session(self, customer_name: str = "Test Customer", 
                           customer_email: str = "test@example.com",
                           flight_no: str = "NZ123", 
                           date: str = "2025-01-17") -> str:
        """Create a new chat session"""
        async with httpx.AsyncClient() as client:
            session_data = {
                "customer_name": customer_name,
                "customer_email": customer_email,
                "flight_no": flight_no,
                "date": date
            }
            
            response = await client.post(f"{self.base_url}/chat/session", json=session_data)
            response.raise_for_status()
            
            data = response.json()
            self.session_id = data["session_id"]
            return self.session_id
    
    async def connect_websocket(self) -> websockets.WebSocketServerProtocol:
        """Connect to WebSocket endpoint"""
        if not self.session_id:
            raise ValueError("Must create session before connecting WebSocket")
        
        self.client_id = f"test-client-{uuid.uuid4()}"
        self.websocket = await websockets.connect(
            f"{self.ws_url}/ws/{self.session_id}/{self.client_id}"
        )
        return self.websocket
    
    async def send_message_websocket(self, message: str) -> Dict[str, Any]:
        """Send message via WebSocket and collect responses"""
        if not self.websocket:
            raise ValueError("Must connect WebSocket before sending messages")
        
        # Send message
        message_data = {"message": message}
        await self.websocket.send(json.dumps(message_data))
        
        # Collect streaming responses
        complete_response = None
        chunks = []
        
        while True:
            try:
                response_text = await asyncio.wait_for(self.websocket.recv(), timeout=30.0)
                response_data = json.loads(response_text)
                
                if response_data["type"] == "chunk":
                    chunks.append(response_data["content"])
                elif response_data["type"] == "complete":
                    complete_response = response_data
                    break
                elif response_data["type"] == "error":
                    return response_data
                
            except asyncio.TimeoutError:
                return {"type": "error", "content": "WebSocket timeout"}
        
        # Store response for analysis
        self.responses.append(complete_response)
        
        return {
            "complete_response": complete_response,
            "chunks": chunks,
            "full_content": "".join(chunks)
        }
    
    async def send_message_rest(self, message: str) -> Dict[str, Any]:
        """Send message via REST API"""
        if not self.session_id:
            raise ValueError("Must create session before sending messages")
        
        async with httpx.AsyncClient() as client:
            message_data = {
                "session_id": self.session_id,
                "message": message,
                "client_id": self.client_id or f"rest-client-{uuid.uuid4()}"
            }
            
            response = await client.post(f"{self.base_url}/chat/message", json=message_data)
            response.raise_for_status()
            
            return response.json()
    
    async def get_session_info(self) -> Dict[str, Any]:
        """Get session information"""
        if not self.session_id:
            raise ValueError("Must create session before getting session info")
        
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{self.base_url}/chat/session/{self.session_id}")
            response.raise_for_status()
            return response.json()
    
    async def health_check(self) -> Dict[str, Any]:
        """Check service health"""
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{self.base_url}/health")
            response.raise_for_status()
            return response.json()
    
    async def get_metrics(self) -> Dict[str, Any]:
        """Get service metrics"""
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{self.base_url}/metrics")
            response.raise_for_status()
            return response.json()
    
    async def close(self):
        """Close WebSocket connection"""
        if self.websocket:
            await self.websocket.close()
            self.websocket = None


class ChatbotLoadTestClient:
    """Load testing client for the chatbot service"""
    
    def __init__(self, base_url: str = "http://localhost:8088"):
        self.base_url = base_url
        self.ws_url = base_url.replace("http", "ws")
    
    async def simulate_conversation(self, session_id: str, client_id: str, 
                                  messages: List[str], 
                                  response_handler: Optional[Callable] = None) -> Dict[str, Any]:
        """Simulate a complete conversation"""
        results = {
            "session_id": session_id,
            "client_id": client_id,
            "messages_sent": 0,
            "responses_received": 0,
            "errors": [],
            "response_times": [],
            "start_time": datetime.now(),
            "end_time": None
        }
        
        try:
            async with websockets.connect(f"{self.ws_url}/ws/{session_id}/{client_id}") as websocket:
                for message in messages:
                    start_time = datetime.now()
                    
                    # Send message
                    message_data = {"message": message}
                    await websocket.send(json.dumps(message_data))
                    results["messages_sent"] += 1
                    
                    # Wait for complete response
                    complete_response = None
                    while True:
                        try:
                            response_text = await asyncio.wait_for(websocket.recv(), timeout=30.0)
                            response_data = json.loads(response_text)
                            
                            if response_data["type"] == "complete":
                                complete_response = response_data
                                break
                            elif response_data["type"] == "error":
                                results["errors"].append(response_data["content"])
                                break
                                
                        except asyncio.TimeoutError:
                            results["errors"].append("Response timeout")
                            break
                    
                    # Calculate response time
                    end_time = datetime.now()
                    response_time = (end_time - start_time).total_seconds()
                    results["response_times"].append(response_time)
                    
                    if complete_response:
                        results["responses_received"] += 1
                        
                        # Call response handler if provided
                        if response_handler:
                            await response_handler(complete_response)
                    
                    # Small delay between messages
                    await asyncio.sleep(1)
                    
        except Exception as e:
            results["errors"].append(f"WebSocket error: {str(e)}")
        
        results["end_time"] = datetime.now()
        return results
    
    async def batch_create_sessions(self, num_sessions: int) -> List[str]:
        """Create multiple sessions in batch"""
        session_ids = []
        
        async with httpx.AsyncClient() as client:
            tasks = []
            for i in range(num_sessions):
                session_data = {
                    "customer_name": f"Load Test User {i}",
                    "customer_email": f"loadtest{i}@example.com",
                    "flight_no": f"NZ{i % 1000:03d}",
                    "date": "2025-01-17"
                }
                tasks.append(client.post(f"{self.base_url}/chat/session", json=session_data))
            
            responses = await asyncio.gather(*tasks, return_exceptions=True)
            
            for response in responses:
                if isinstance(response, httpx.Response) and response.status_code == 200:
                    session_ids.append(response.json()["session_id"])
                else:
                    logger.error(f"Failed to create session: {response}")
        
        return session_ids
    
    async def run_load_test(self, num_users: int, messages_per_user: int = 5,
                          duration: int = 60) -> Dict[str, Any]:
        """Run a comprehensive load test"""
        logger.info(f"Starting load test with {num_users} users")
        
        # Create sessions
        session_ids = await self.batch_create_sessions(num_users)
        logger.info(f"Created {len(session_ids)} sessions")
        
        # Prepare test messages
        test_messages = [
            "Hello, I need help with my flight",
            "Is my flight on time?",
            "What time should I arrive at the airport?",
            "Can I change my seat?",
            "What's the baggage policy?",
            "Is there a delay?",
            "Can I get a refund?",
            "Thank you for your help"
        ]
        
        # Run conversations concurrently
        tasks = []
        for i, session_id in enumerate(session_ids):
            client_id = f"load-test-client-{i}"
            user_messages = test_messages[:messages_per_user]
            tasks.append(self.simulate_conversation(session_id, client_id, user_messages))
        
        # Execute load test
        start_time = datetime.now()
        results = await asyncio.gather(*tasks, return_exceptions=True)
        end_time = datetime.now()
        
        # Aggregate results
        aggregated_results = {
            "total_users": num_users,
            "sessions_created": len(session_ids),
            "total_messages_sent": 0,
            "total_responses_received": 0,
            "total_errors": 0,
            "response_times": [],
            "errors": [],
            "duration_seconds": (end_time - start_time).total_seconds(),
            "detailed_results": []
        }
        
        for result in results:
            if isinstance(result, dict):
                aggregated_results["total_messages_sent"] += result["messages_sent"]
                aggregated_results["total_responses_received"] += result["responses_received"]
                aggregated_results["total_errors"] += len(result["errors"])
                aggregated_results["response_times"].extend(result["response_times"])
                aggregated_results["errors"].extend(result["errors"])
                aggregated_results["detailed_results"].append(result)
            else:
                aggregated_results["errors"].append(f"Task failed: {result}")
                aggregated_results["total_errors"] += 1
        
        # Calculate statistics
        if aggregated_results["response_times"]:
            response_times = aggregated_results["response_times"]
            aggregated_results["statistics"] = {
                "avg_response_time": sum(response_times) / len(response_times),
                "min_response_time": min(response_times),
                "max_response_time": max(response_times),
                "p95_response_time": sorted(response_times)[int(len(response_times) * 0.95)],
                "p99_response_time": sorted(response_times)[int(len(response_times) * 0.99)]
            }
        
        aggregated_results["success_rate"] = (
            aggregated_results["total_responses_received"] / 
            aggregated_results["total_messages_sent"] * 100
            if aggregated_results["total_messages_sent"] > 0 else 0
        )
        
        return aggregated_results


# Utility functions for testing
async def test_basic_functionality():
    """Test basic chatbot functionality"""
    client = ChatbotTestClient()
    
    try:
        # Create session
        session_id = await client.create_session()
        print(f"Created session: {session_id}")
        
        # Connect WebSocket
        await client.connect_websocket()
        print("Connected to WebSocket")
        
        # Send test message
        response = await client.send_message_websocket("Hello, I need help with my flight")
        print(f"Response: {response}")
        
        # Get session info
        session_info = await client.get_session_info()
        print(f"Session info: {session_info}")
        
        # Health check
        health = await client.health_check()
        print(f"Health: {health}")
        
    finally:
        await client.close()


async def test_load_performance(num_users: int = 100):
    """Test load performance"""
    load_client = ChatbotLoadTestClient()
    
    results = await load_client.run_load_test(
        num_users=num_users,
        messages_per_user=5,
        duration=60
    )
    
    print(f"Load Test Results:")
    print(f"Success Rate: {results['success_rate']:.2f}%")
    print(f"Total Messages: {results['total_messages_sent']}")
    print(f"Total Responses: {results['total_responses_received']}")
    print(f"Total Errors: {results['total_errors']}")
    
    if "statistics" in results:
        stats = results["statistics"]
        print(f"Average Response Time: {stats['avg_response_time']:.2f}s")
        print(f"P95 Response Time: {stats['p95_response_time']:.2f}s")
        print(f"P99 Response Time: {stats['p99_response_time']:.2f}s")
    
    return results


if __name__ == "__main__":
    # Run basic functionality test
    print("Running basic functionality test...")
    asyncio.run(test_basic_functionality())
    
    # Run load test
    print("\nRunning load test...")
    asyncio.run(test_load_performance(50))
