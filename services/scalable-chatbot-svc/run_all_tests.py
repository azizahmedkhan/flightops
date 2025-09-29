#!/usr/bin/env python3
"""
Comprehensive test runner for the chatbot service
"""

import asyncio
import subprocess
import sys
import os
import time
import signal
import psutil
from pathlib import Path

def find_process_on_port(port):
    """Find process running on specified port"""
    for proc in psutil.process_iter(['pid', 'name', 'connections']):
        try:
            for conn in proc.info['connections'] or []:
                if conn.laddr.port == port:
                    return proc
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass
    return None

def kill_process_on_port(port):
    """Kill process running on specified port"""
    proc = find_process_on_port(port)
    if proc:
        print(f"Killing process {proc.pid} on port {port}")
        proc.kill()
        time.sleep(2)

def run_command(cmd, cwd=None, timeout=30):
    """Run a command and return the result"""
    try:
        result = subprocess.run(
            cmd, 
            shell=True, 
            cwd=cwd, 
            capture_output=True, 
            text=True, 
            timeout=timeout
        )
        return result.returncode == 0, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return False, "", f"Command timed out after {timeout} seconds"
    except Exception as e:
        return False, "", str(e)

async def test_service_health():
    """Test if the service is healthy"""
    import httpx
    
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get("http://localhost:8088/health")
            if response.status_code == 200:
                data = response.json()
                return data.get("status") == "healthy"
    except:
        pass
    return False

async def main():
    """Main test function"""
    print("Chatbot Service Test Suite")
    print("=" * 50)
    
    # Change to the service directory
    service_dir = Path(__file__).parent
    os.chdir(service_dir)
    
    # Step 1: Check if service is already running
    print("1. Checking if service is already running...")
    if find_process_on_port(8088):
        print("   ✓ Service is already running on port 8088")
        if await test_service_health():
            print("   ✓ Service is healthy")
        else:
            print("   ✗ Service is running but not healthy")
            kill_process_on_port(8088)
            time.sleep(2)
    else:
        print("   - No service running on port 8088")
    
    # Step 2: Start the service if not running
    if not await test_service_health():
        print("2. Starting chatbot service...")
        
        # Kill any existing process
        kill_process_on_port(8088)
        
        # Start the service
        try:
            service_process = subprocess.Popen(
                [sys.executable, "run_test_service.py"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            # Wait for service to start
            print("   Waiting for service to start...")
            for i in range(30):  # Wait up to 30 seconds
                await asyncio.sleep(1)
                if await test_service_health():
                    print("   ✓ Service started successfully")
                    break
            else:
                print("   ✗ Service failed to start within 30 seconds")
                service_process.terminate()
                return False
                
        except Exception as e:
            print(f"   ✗ Failed to start service: {e}")
            return False
    
    # Step 3: Run basic functionality tests
    print("3. Running basic functionality tests...")
    success, stdout, stderr = run_command(
        f"{sys.executable} test_service_startup.py",
        timeout=30
    )
    
    if success:
        print("   ✓ Basic functionality tests passed")
    else:
        print("   ✗ Basic functionality tests failed")
        print(f"   Error: {stderr}")
        return False
    
    # Step 4: Run unit tests
    print("4. Running unit tests...")
    success, stdout, stderr = run_command(
        f"{sys.executable} -m pytest tests/test_chatbot.py -v",
        timeout=60
    )
    
    if success:
        print("   ✓ Unit tests passed")
    else:
        print("   ✗ Unit tests failed")
        print(f"   Error: {stderr}")
        # Don't return False here, continue with load tests
    
    # Step 5: Run load tests
    print("5. Running load tests...")
    success, stdout, stderr = run_command(
        f"{sys.executable} -m pytest tests/test_load_testing.py -v --tb=short",
        timeout=300  # 5 minutes for load tests
    )
    
    if success:
        print("   ✓ Load tests passed")
    else:
        print("   ✗ Load tests failed")
        print(f"   Error: {stderr}")
        # Show the last few lines of output for debugging
        if stdout:
            lines = stdout.strip().split('\n')
            print("   Last 10 lines of output:")
            for line in lines[-10:]:
                print(f"     {line}")
    
    # Step 6: Cleanup
    print("6. Cleaning up...")
    kill_process_on_port(8088)
    
    print("\n" + "=" * 50)
    print("Test suite completed!")
    
    return True

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nTest suite interrupted by user")
        kill_process_on_port(8088)
        sys.exit(1)
    except Exception as e:
        print(f"\nTest suite failed with error: {e}")
        kill_process_on_port(8088)
        sys.exit(1)
