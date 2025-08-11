#!/bin/bash

echo "=== Oracle Trader Bot Deployment Script ==="
echo "Starting deployment process..."

# Navigate to project directory
cd /opt/oracle_trader_bot || { echo "Project directory not found"; exit 1; }

echo "Current directory: $(pwd)"
echo "Git status before pull:"
git status --porcelain

# Pull latest changes
echo "Pulling latest changes from GitHub..."
git pull origin main

echo "Git status after pull:"
git status --porcelain

# Show recent commits
echo "Recent commits:"
git log --oneline -5

# Check if Docker is running
echo "Checking Docker status..."
docker --version
docker-compose --version

# Navigate to deployment directory
cd oracle_trader_bot/deployment || { echo "Deployment directory not found"; exit 1; }

echo "Current directory: $(pwd)"
echo "Available docker-compose files:"
ls -la *.yml

# Stop existing containers
echo "Stopping existing containers..."
docker-compose -f docker-compose.yml down

# Start containers with latest changes
echo "Starting containers with latest build..."
docker-compose -f docker-compose.yml up -d --build

# Wait a moment for containers to start
sleep 10

# Check container status
echo "Container status:"
docker-compose -f docker-compose.yml ps

# Show logs for main application
echo "Recent application logs:"
docker-compose -f docker-compose.yml logs --tail=20 oracle-trader

echo "=== Deployment completed ==="

# Test endpoints
echo "Testing endpoints..."
curl -s -o /dev/null -w "Dashboard status: %{http_code}\n" http://localhost/dashboard/
curl -s -o /dev/null -w "Health status: %{http_code}\n" http://localhost/health
curl -s -o /dev/null -w "API Health status: %{http_code}\n" http://localhost/api/health

echo "=== All done! ==="
