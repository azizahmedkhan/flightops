#!/usr/bin/env python3
"""
Simple test script to verify the chatbot service can start and basic functionality works
"""

import asyncio
import httpx
import json
import sys
import os

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(__file__))

async def test_service_startup():
    """Test if the service can start and respond to basic requests"""
    base_url = "http://localhost:8088"
    
    print("Testing chatbot service startup...")
    
    # Test 1: Health check
    print("1. Testing health check endpoint...")
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{base_url}/health")
            if response.status_code == 200:
                health_data = response.json()
                print(f"   ✓ Health check passed: {health_data.get('status')}")
            else:
                print(f"   ✗ Health check failed: {response.status_code}")
                return False
    except Exception as e:
        print(f"   ✗ Health check failed: {e}")
        return False
    
    # Test 2: Test endpoint
    print("2. Testing test endpoint...")
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{base_url}/test")
            if response.status_code == 200:
                test_data = response.json()
                print(f"   ✓ Test endpoint passed: {test_data.get('status')}")
            else:
                print(f"   ✗ Test endpoint failed: {response.status_code}")
                return False
    except Exception as e:
        print(f"   ✗ Test endpoint failed: {e}")
        return False
    
    # Test 3: Session creation
    print("3. Testing session creation...")
    try:
        session_data = {
            "customer_name": "Test User",
            "customer_email": "test@example.com",
            "flight_no": "NZ123",
            "date": "2025-01-17"
        }
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(f"{base_url}/chat/session", json=session_data)
            if response.status_code == 200:
                session_response = response.json()
                session_id = session_response.get("session_id")
                print(f"   ✓ Session creation passed: {session_id}")
                
                # Test 4: Send message
                print("4. Testing message sending...")
                message_data = {
                    "session_id": session_id,
                    "message": "Hello, test message",
                    "client_id": "test-client"
                }
                
                response = await client.post(f"{base_url}/chat/message", json=message_data)
                if response.status_code == 200:
                    message_response = response.json()
                    print(f"   ✓ Message sending passed: {message_response.get('status')}")
                else:
                    print(f"   ✗ Message sending failed: {response.status_code}")
                    return False
            else:
                print(f"   ✗ Session creation failed: {response.status_code}")
                return False
    except Exception as e:
        print(f"   ✗ Session creation failed: {e}")
        return False
    
    print("\n✓ All basic tests passed! Service is working correctly.")
    return True

async def main():
    """Main test function"""
    print("Chatbot Service Startup Test")
    print("=" * 40)
    
    success = await test_service_startup()
    
    if success:
        print("\n🎉 Service is ready for load testing!")
        sys.exit(0)
    else:
        print("\n❌ Service has issues that need to be fixed.")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
