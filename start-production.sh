#!/bin/bash

# AeroOps Production Startup Script

echo "🚀 Starting AeroOps in Production Mode..."

# Check if .env file exists
if [ ! -f .env ]; then
    echo "❌ Error: .env file not found!"
    echo "Please create a .env file with your production configuration."
    echo "Required variables:"
    echo "  - OPENAI_API_KEY"
    echo "  - DB_PASS (secure database password)"
    echo "  - NODE_ENV=production"
    exit 1
fi

# Set production environment
export NODE_ENV=production

# Build and start all services
echo "🔨 Building and starting production services..."
docker compose -f infra/docker-compose.prod.yml up --build -d

# Wait for services to be ready
echo "⏳ Waiting for services to start..."
sleep 10

# Check service health
echo "🔍 Checking service health..."
docker compose -f infra/docker-compose.prod.yml ps

echo "✅ AeroOps is running in production mode!"
echo "🌐 Web UI: http://localhost:3000"
echo "🔗 Gateway API: http://localhost:8080"
echo "📊 API Docs: http://localhost:8080/docs"

echo ""
echo "To stop the services:"
echo "  docker compose -f infra/docker-compose.prod.yml down"
echo ""
echo "To view logs:"
echo "  docker compose -f infra/docker-compose.prod.yml logs -f"
