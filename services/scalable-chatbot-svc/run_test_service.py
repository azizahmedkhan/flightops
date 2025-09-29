#!/usr/bin/env python3
"""
Test service runner - starts the chatbot service in test mode
"""

import os
import sys
import asyncio
import uvicorn
from main import app

def main():
    """Run the service in test mode"""
    print("Starting chatbot service in test mode...")
    
    # Set environment variables for test mode
    os.environ["REDIS_URL"] = "redis://localhost:6379"
    os.environ["KNOWLEDGE_SERVICE_URL"] = "http://localhost:8081"
    os.environ["DB_ROUTER_URL"] = "http://localhost:8000"
    
    # Disable debug mode for cleaner output
    os.environ.pop("DEBUGPY", None)
    
    print("Environment configured for testing:")
    print(f"  - Redis URL: {os.environ.get('REDIS_URL')}")
    print(f"  - Knowledge Service: {os.environ.get('KNOWLEDGE_SERVICE_URL')}")
    print(f"  - DB Router: {os.environ.get('DB_ROUTER_URL')}")
    print()
    
    try:
        # Start the service
        uvicorn.run(
            "main:app",
            host="0.0.0.0",
            port=8088,
            reload=False,
            workers=1,
            loop="asyncio",
            log_level="info"
        )
    except KeyboardInterrupt:
        print("\nService stopped by user")
    except Exception as e:
        print(f"Error starting service: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
