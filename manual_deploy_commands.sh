#!/bin/bash

# Oracle Trader Bot - Manual Deployment Script
# Run these commands manually on your server

echo "🚀 Oracle Trader Bot - Manual Deployment Guide"
echo "=============================================="
echo ""

echo "📍 Step 1: Navigate to project directory"
echo "cd /opt/oracle_trader_bot"
echo ""

echo "📍 Step 2: Check current git status"
echo "git status"
echo "git log --oneline -5"
echo ""

echo "📍 Step 3: Pull latest changes from GitHub"
echo "git pull origin main"
echo ""

echo "📍 Step 4: Check Docker containers status"
echo "docker ps"
echo ""

echo "📍 Step 5: Stop current containers"
echo "docker-compose -f oracle_trader_bot/deployment/docker-compose.yml down"
echo ""

echo "📍 Step 6: Rebuild and start containers"
echo "docker-compose -f oracle_trader_bot/deployment/docker-compose.yml up -d --build"
echo ""

echo "📍 Step 7: Check container status"
echo "docker-compose -f oracle_trader_bot/deployment/docker-compose.yml ps"
echo ""

echo "📍 Step 8: View application logs"
echo "docker-compose -f oracle_trader_bot/deployment/docker-compose.yml logs -f oracle-trader"
echo ""

echo "📍 Step 9: Test endpoints (in new terminal)"
echo "curl http://localhost/health"
echo "curl http://localhost/dashboard/api/test-data"
echo "curl http://localhost/dashboard/"
echo ""

echo "=============================================="
echo "✅ After running these commands, test these URLs:"
echo "   • Main: http://194.127.178.181/"
echo "   • Dashboard: http://194.127.178.181/dashboard/"
echo "   • Health: http://194.127.178.181/health"
echo "   • Test API: http://194.127.178.181/dashboard/api/test-data"
echo ""
echo "🎯 Expected improvements:"
echo "   • Dashboard should load faster"
echo "   • Better error handling" 
echo "   • New test endpoint should work"
echo "   • Mock data fallback when APIs fail"
