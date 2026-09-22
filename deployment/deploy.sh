#!/bin/bash
set -e

echo "=== Starting FO-X 5M Production Deployment ==="

# Check for .env file
if [ ! -f .env ]; then
    echo "Warning: .env not found! Copying from .env.example..."
    cp .env.example .env
fi

# Create directories
mkdir -p data/research data/paper_trading data/backups logs

# Launch docker-compose stack
echo "Building and launching Docker containers..."
docker compose up -d --build

echo "Checking system health..."
sleep 5
curl -s http://localhost:8000/health | grep "HEALTHY" && echo "System successfully started and verified healthy!" || echo "Warning: Healthcheck did not immediately respond with HEALTHY."

echo "=== Deployment Completed ==="
