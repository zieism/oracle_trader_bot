#!/bin/bash

# Oracle Trader Bot - Health Check Script
# Tests all important endpoints

SERVER_URL="http://194.127.178.181"
echo "🔍 Testing Oracle Trader Bot endpoints on $SERVER_URL"
echo "================================================"

# Test main page
echo "1. Testing main page..."
curl -s -o /dev/null -w "Status: %{http_code} | Time: %{time_total}s" "$SERVER_URL/"
echo ""

# Test dashboard
echo "2. Testing dashboard..."
curl -s -o /dev/null -w "Status: %{http_code} | Time: %{time_total}s" "$SERVER_URL/dashboard/"
echo ""

# Test health endpoint
echo "3. Testing health endpoint..."
curl -s -w "Status: %{http_code} | Time: %{time_total}s" "$SERVER_URL/health"
echo ""

# Test API health
echo "4. Testing API health..."
curl -s -w "Status: %{http_code} | Time: %{time_total}s" "$SERVER_URL/api/health"
echo ""

# Test dashboard API test endpoint
echo "5. Testing dashboard test endpoint..."
curl -s -w "Status: %{http_code} | Time: %{time_total}s" "$SERVER_URL/dashboard/api/test-data"
echo ""

# Test main dashboard API
echo "6. Testing dashboard data endpoint..."
curl -s -o /dev/null -w "Status: %{http_code} | Time: %{time_total}s" "$SERVER_URL/dashboard/api/dashboard-data"
echo ""

echo "================================================"
echo "✅ Health check complete!"
echo ""
echo "Expected responses:"
echo "- Status 200: Endpoint working correctly"
echo "- Status 302: Redirect (normal for main page)"
echo "- Status 404: Endpoint not found"
echo "- Status 500: Server error"
echo ""
echo "If all endpoints return 200/302, the server is healthy!"
