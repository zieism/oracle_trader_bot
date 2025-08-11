#!/bin/bash

# SSH Connection Script for Oracle Trader Bot Deployment
# Usage: ./deploy.sh [command]

SERVER_IP="194.127.178.181"
SERVER_USER="root"
SERVER_PORT="22"
PROJECT_PATH="/opt/oracle_trader_bot"

echo "🚀 Oracle Trader Bot Deployment Script"
echo "Server: $SERVER_USER@$SERVER_IP:$SERVER_PORT"
echo "Project Path: $PROJECT_PATH"
echo "=================================="

# Function to execute commands on server
execute_remote() {
    local cmd="$1"
    echo "📟 Executing: $cmd"
    ssh -o StrictHostKeyChecking=no -p $SERVER_PORT $SERVER_USER@$SERVER_IP "$cmd"
}

# Function to deploy application
deploy_app() {
    echo "🔄 Starting deployment..."
    
    # Navigate to project directory
    execute_remote "cd $PROJECT_PATH"
    
    # Pull latest changes
    echo "📥 Pulling latest changes from GitHub..."
    execute_remote "cd $PROJECT_PATH && git pull origin main"
    
    # Stop current containers
    echo "🛑 Stopping current containers..."
    execute_remote "cd $PROJECT_PATH && docker-compose -f oracle_trader_bot/deployment/docker-compose.yml down"
    
    # Build and start new containers
    echo "🔨 Building and starting containers..."
    execute_remote "cd $PROJECT_PATH && docker-compose -f oracle_trader_bot/deployment/docker-compose.yml up -d --build"
    
    # Wait a moment for containers to start
    sleep 10
    
    # Check status
    echo "📊 Checking container status..."
    execute_remote "cd $PROJECT_PATH && docker-compose -f oracle_trader_bot/deployment/docker-compose.yml ps"
    
    echo "✅ Deployment completed!"
}

# Function to check status
check_status() {
    echo "📊 Checking server status..."
    execute_remote "cd $PROJECT_PATH && docker-compose -f oracle_trader_bot/deployment/docker-compose.yml ps"
    
    echo "📋 Recent logs:"
    execute_remote "cd $PROJECT_PATH && docker-compose -f oracle_trader_bot/deployment/docker-compose.yml logs --tail=20 oracle-trader"
}

# Function to view logs
view_logs() {
    echo "📋 Viewing application logs..."
    execute_remote "cd $PROJECT_PATH && docker-compose -f oracle_trader_bot/deployment/docker-compose.yml logs -f oracle-trader"
}

# Main logic
case "$1" in
    "deploy")
        deploy_app
        ;;
    "status")
        check_status
        ;;
    "logs")
        view_logs
        ;;
    *)
        echo "Usage: $0 {deploy|status|logs}"
        echo ""
        echo "Commands:"
        echo "  deploy  - Deploy latest changes to server"
        echo "  status  - Check container status and recent logs"
        echo "  logs    - View live application logs"
        exit 1
        ;;
esac
