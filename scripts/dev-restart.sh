#!/bin/bash

echo "🔄 Rebuilding and restarting development container..."

DEV_PORT_VALUE="${DEV_PORT:-5079}"

# Stop and remove existing container
docker compose -f docker-compose.dev.yaml down

# Build and start the container
docker compose -f docker-compose.dev.yaml up --build -d

echo "✅ Development container is running!"
echo "🌐 Access the app at: http://localhost:${DEV_PORT_VALUE}"
echo "📋 View logs with: docker logs -f audiobookbay-automated-dev"
echo "🛑 Stop with: docker compose -f docker-compose.dev.yaml down"
