#!/usr/bin/env python3
"""
Debug script to understand why load tests are failing
"""

import asyncio
import httpx
import json
import sys
import os

async def debug_load_test():
    """Debug the load test to understand what's failing"""
    base_url = "http://localhost:8088"
    
    print("Debugging load test...")
    
    # Test 1: Health check
    print("1. Testing health check...")
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{base_url}/health")
            print(f"   Health check status: {response.status_code}")
            if response.status_code == 200:
                print(f"   Health check response: {response.json()}")
            else:
                print(f"   Health check failed: {response.text}")
    except Exception as e:
        print(f"   Health check error: {e}")
    
    # Test 2: Session creation
    print("\n2. Testing session creation...")
    try:
        session_data = {
            "customer_name": "Debug User",
            "customer_email": "debug@example.com",
            "flight_no": "NZ123",
            "date": "2025-01-17"
        }
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(f"{base_url}/chat/session", json=session_data)
            print(f"   Session creation status: {response.status_code}")
            if response.status_code == 200:
                session_response = response.json()
                session_id = session_response.get("session_id")
                print(f"   Session ID: {session_id}")
                
                # Test 3: Message sending
                print("\n3. Testing message sending...")
                message_data = {
                    "session_id": session_id,
                    "message": "Hello, debug message",
                    "client_id": "debug-client"
                }
                
                response = await client.post(f"{base_url}/chat/message", json=message_data)
                print(f"   Message sending status: {response.status_code}")
                if response.status_code == 200:
                    print(f"   Message response: {response.json()}")
                else:
                    print(f"   Message sending failed: {response.text}")
            else:
                print(f"   Session creation failed: {response.text}")
    except Exception as e:
        print(f"   Session creation error: {e}")
    
    # Test 4: WebSocket connection
    print("\n4. Testing WebSocket connection...")
    try:
        import websockets
        ws_url = f"ws://localhost:8088/ws/test-session/test-client"
        print(f"   WebSocket URL: {ws_url}")
        
        async with websockets.connect(ws_url) as websocket:
            print("   WebSocket connected successfully!")
            
            # Send a test message
            message_data = {"message": "Hello WebSocket"}
            await websocket.send(json.dumps(message_data))
            print("   Message sent via WebSocket")
            
            # Try to receive a response
            try:
                response = await asyncio.wait_for(websocket.recv(), timeout=10.0)
                print(f"   WebSocket response: {response}")
            except asyncio.TimeoutError:
                print("   WebSocket response timeout")
                
    except Exception as e:
        print(f"   WebSocket error: {e}")

async def main():
    """Main debug function"""
    print("Load Test Debug Script")
    print("=" * 40)
    
    await debug_load_test()
    
    print("\n" + "=" * 40)
    print("Debug complete!")

if __name__ == "__main__":
    asyncio.run(main())
