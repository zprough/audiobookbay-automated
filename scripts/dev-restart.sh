#!/bin/bash

echo "🔄 Rebuilding and restarting development container..."

DEV_PORT_VALUE="${DEV_PORT:-5079}"
DEV_COMPOSE_FILE="docker-compose.dev.yaml"

# Stop and remove existing container
docker compose -f "$DEV_COMPOSE_FILE" down

# Build and start the container
docker compose -f "$DEV_COMPOSE_FILE" up --build -d

echo "✅ Development container is running!"
echo "🌐 Access the app at: http://localhost:${DEV_PORT_VALUE}"
echo "📋 View logs with: docker logs -f audiobookbay-downloader-dev"
echo "🛑 Stop with: docker compose -f ${DEV_COMPOSE_FILE} down"
