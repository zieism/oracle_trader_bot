#!/bin/bash

# SSH Commands for Oracle Trader Bot Deployment
SERVER="194.127.178.181"
USER="root"
PASSWORD="Z9X07C##z9z9z9"

echo "Oracle Trader Bot - Server Deployment Commands"
echo "=============================================="
echo ""

echo "1. First, connect to server:"
echo "ssh $USER@$SERVER"
echo "Password: $PASSWORD"
echo ""

echo "2. Check current directory:"
echo "pwd"
echo "ls -la"
echo ""

echo "3. Navigate to project:"
echo "cd /opt/oracle_trader_bot || cd /root/oracle_trader_bot"
echo ""

echo "4. Update code from GitHub:"
echo "git pull origin main"
echo ""

echo "5. Check Docker status:"
echo "docker ps -a"
echo ""

echo "6. Stop current containers:"
echo "docker-compose -f oracle_trader_bot/deployment/docker-compose.yml down"
echo ""

echo "7. Rebuild and start:"
echo "docker-compose -f oracle_trader_bot/deployment/docker-compose.yml up -d --build"
echo ""

echo "8. Check container logs:"
echo "docker-compose -f oracle_trader_bot/deployment/docker-compose.yml logs oracle-trader"
echo ""

echo "9. Test the endpoints:"
echo "curl http://localhost/health"
echo "curl http://localhost/dashboard/api/test-data"
echo ""

echo "=============================================="
