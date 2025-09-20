#!/usr/bin/env python3
"""
Demo script for the scalable chatbot service
Demonstrates the chatbot's capabilities with various test scenarios
"""

import asyncio
import json
import time
import uuid
from datetime import datetime
import httpx
import websockets


class ChatbotDemo:
    """Demo class for showcasing chatbot capabilities"""
    
    def __init__(self, base_url: str = "http://localhost:8088"):
        self.base_url = base_url
        self.ws_url = base_url.replace("http", "ws")
        self.session_id = None
        self.client_id = None
    
    async def create_session(self) -> str:
        """Create a demo session"""
        print("🚀 Creating chat session...")
        
        async with httpx.AsyncClient() as client:
            session_data = {
                "customer_name": "Demo User",
                "customer_email": "demo@example.com",
                "flight_no": "NZ123",
                "date": "2025-01-17"
            }
            
            response = await client.post(f"{self.base_url}/chat/session", json=session_data)
            response.raise_for_status()
            
            session_info = response.json()
            self.session_id = session_info["session_id"]
            print(f"✅ Session created: {self.session_id}")
            return self.session_id
    
    async def connect_websocket(self):
        """Connect to WebSocket"""
        print("🔌 Connecting to WebSocket...")
        
        self.client_id = f"demo-client-{uuid.uuid4()}"
        self.websocket = await websockets.connect(
            f"{self.ws_url}/ws/{self.session_id}/{self.client_id}"
        )
        print("✅ WebSocket connected")
    
    async def send_message(self, message: str) -> str:
        """Send a message and get response"""
        print(f"\n👤 You: {message}")
        
        # Send message
        await self.websocket.send(json.dumps({"message": message}))
        
        # Collect streaming response
        full_response = ""
        chunks = []
        
        while True:
            try:
                response_text = await asyncio.wait_for(self.websocket.recv(), timeout=30.0)
                response_data = json.loads(response_text)
                
                if response_data["type"] == "chunk":
                    chunk = response_data["content"]
                    chunks.append(chunk)
                    full_response += chunk
                    print(f"🤖 Bot: {chunk}", end="", flush=True)
                    
                elif response_data["type"] == "complete":
                    print()  # New line after streaming
                    
                    # Show metadata if available
                    if response_data.get("metadata"):
                        metadata = response_data["metadata"]
                        if metadata.get("tokens_used"):
                            print(f"   📊 Tokens used: {metadata['tokens_used']}")
                        if metadata.get("response_time_ms"):
                            print(f"   ⏱️  Response time: {metadata['response_time_ms']:.0f}ms")
                    
                    break
                    
                elif response_data["type"] == "error":
                    print(f"\n❌ Error: {response_data['content']}")
                    break
                    
            except asyncio.TimeoutError:
                print("\n⏰ Response timeout")
                break
        
        return full_response
    
    async def run_interactive_demo(self):
        """Run interactive demo"""
        print("🎯 Starting Interactive Chatbot Demo")
        print("=" * 50)
        
        # Create session and connect
        await self.create_session()
        await self.connect_websocket()
        
        print("\n💬 Start chatting! Type 'quit' to exit, 'help' for suggestions.")
        
        while True:
            try:
                message = input("\n👤 You: ").strip()
                
                if message.lower() == 'quit':
                    break
                elif message.lower() == 'help':
                    print("\n💡 Try these sample questions:")
                    print("   • 'Is my flight on time?'")
                    print("   • 'What time should I arrive at the airport?'")
                    print("   • 'Can I change my seat?'")
                    print("   • 'What's the baggage policy?'")
                    print("   • 'Is there a delay?'")
                    print("   • 'Can I get a refund?'")
                    continue
                elif not message:
                    continue
                
                await self.send_message(message)
                
            except KeyboardInterrupt:
                print("\n\n👋 Demo interrupted by user")
                break
            except Exception as e:
                print(f"\n❌ Error: {e}")
                break
        
        await self.websocket.close()
        print("\n✅ Demo completed")
    
    async def run_automated_demo(self):
        """Run automated demo with predefined messages"""
        print("🤖 Starting Automated Chatbot Demo")
        print("=" * 50)
        
        # Create session and connect
        await self.create_session()
        await self.connect_websocket()
        
        # Predefined conversation flow
        demo_messages = [
            "Hello, I need help with my flight NZ123",
            "Is my flight on time?",
            "What time should I arrive at the airport?",
            "Can I change my seat?",
            "What's the baggage policy?",
            "Thank you for your help!"
        ]
        
        for i, message in enumerate(demo_messages, 1):
            print(f"\n--- Message {i}/{len(demo_messages)} ---")
            await self.send_message(message)
            await asyncio.sleep(2)  # Pause between messages
        
        await self.websocket.close()
        print("\n✅ Automated demo completed")
    
    async def check_service_health(self):
        """Check service health and metrics"""
        print("🏥 Checking Service Health")
        print("=" * 30)
        
        async with httpx.AsyncClient() as client:
            try:
                # Health check
                health_response = await client.get(f"{self.base_url}/health")
                if health_response.status_code == 200:
                    health_data = health_response.json()
                    print(f"✅ Health Status: {health_data.get('status', 'unknown')}")
                    print(f"   Service: {health_data.get('service', 'unknown')}")
                    print(f"   Redis Status: {health_data.get('redis_status', 'unknown')}")
                    print(f"   Active Connections: {health_data.get('active_connections', 0)}")
                    print(f"   Active Sessions: {health_data.get('active_sessions', 0)}")
                else:
                    print(f"❌ Health check failed: {health_response.status_code}")
                
                # Metrics
                metrics_response = await client.get(f"{self.base_url}/metrics")
                if metrics_response.status_code == 200:
                    metrics_data = metrics_response.json()
                    print(f"\n📊 Metrics:")
                    print(f"   Active Connections: {metrics_data.get('active_connections', 0)}")
                    print(f"   Active Sessions: {metrics_data.get('active_sessions', 0)}")
                    
                    # Show connection metadata
                    connection_metadata = metrics_data.get('connection_metadata', {})
                    if connection_metadata:
                        print(f"   Connection Details:")
                        for client_id, metadata in list(connection_metadata.items())[:3]:  # Show first 3
                            session_id = metadata.get('session_id', 'unknown')
                            connected_at = metadata.get('connected_at', 'unknown')
                            print(f"     - {client_id}: session={session_id}, connected={connected_at}")
                
            except Exception as e:
                print(f"❌ Error checking service: {e}")
    
    async def run_load_test_demo(self, num_concurrent: int = 10):
        """Run a small load test demo"""
        print(f"⚡ Running Load Test Demo ({num_concurrent} concurrent users)")
        print("=" * 50)
        
        # Create multiple sessions
        session_ids = []
        for i in range(num_concurrent):
            async with httpx.AsyncClient() as client:
                session_data = {
                    "customer_name": f"Load Test User {i}",
                    "customer_email": f"loadtest{i}@example.com",
                    "flight_no": f"NZ{i % 100:03d}",
                    "date": "2025-01-17"
                }
                
                response = await client.post(f"{self.base_url}/chat/session", json=session_data)
                if response.status_code == 200:
                    session_ids.append(response.json()["session_id"])
        
        print(f"✅ Created {len(session_ids)} sessions")
        
        # Simulate concurrent conversations
        async def simulate_user_conversation(session_id: str, user_id: int):
            try:
                client_id = f"load-test-{user_id}"
                async with websockets.connect(f"{self.ws_url}/ws/{session_id}/{client_id}") as ws:
                    messages = [
                        f"Hello, I'm user {user_id}",
                        "Is my flight on time?",
                        "Thank you!"
                    ]
                    
                    for message in messages:
                        await ws.send(json.dumps({"message": message}))
                        
                        # Wait for response
                        while True:
                            response_text = await asyncio.wait_for(ws.recv(), timeout=10.0)
                            response_data = json.loads(response_text)
                            if response_data["type"] == "complete":
                                break
                        
                        await asyncio.sleep(1)
                
                return f"User {user_id}: Success"
                
            except Exception as e:
                return f"User {user_id}: Error - {e}"
        
        # Run concurrent conversations
        start_time = time.time()
        tasks = [
            simulate_user_conversation(session_id, i)
            for i, session_id in enumerate(session_ids)
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        end_time = time.time()
        
        # Analyze results
        successful = sum(1 for r in results if "Success" in str(r))
        failed = len(results) - successful
        
        print(f"\n📊 Load Test Results:")
        print(f"   Total Users: {num_concurrent}")
        print(f"   Successful: {successful}")
        print(f"   Failed: {failed}")
        print(f"   Success Rate: {successful/num_concurrent*100:.1f}%")
        print(f"   Total Time: {end_time - start_time:.2f}s")
        print(f"   Avg Time per User: {(end_time - start_time)/num_concurrent:.2f}s")
        
        # Show sample results
        print(f"\n📝 Sample Results:")
        for result in results[:5]:  # Show first 5 results
            print(f"   {result}")


async def main():
    """Main demo function"""
    demo = ChatbotDemo()
    
    print("🎭 Scalable Chatbot Service Demo")
    print("=" * 40)
    
    # Check service health first
    await demo.check_service_health()
    
    print("\n" + "=" * 40)
    print("Choose demo mode:")
    print("1. Interactive Chat Demo")
    print("2. Automated Demo")
    print("3. Load Test Demo")
    print("4. All Demos")
    
    try:
        choice = input("\nEnter choice (1-4): ").strip()
        
        if choice == "1":
            await demo.run_interactive_demo()
        elif choice == "2":
            await demo.run_automated_demo()
        elif choice == "3":
            num_users = input("Number of concurrent users (default 10): ").strip()
            num_users = int(num_users) if num_users.isdigit() else 10
            await demo.run_load_test_demo(num_users)
        elif choice == "4":
            await demo.run_automated_demo()
            await asyncio.sleep(2)
            await demo.run_load_test_demo(5)
        else:
            print("Invalid choice. Running automated demo...")
            await demo.run_automated_demo()
            
    except KeyboardInterrupt:
        print("\n👋 Demo interrupted by user")
    except Exception as e:
        print(f"❌ Demo error: {e}")


if __name__ == "__main__":
    asyncio.run(main())
