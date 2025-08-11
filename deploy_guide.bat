@echo off
echo ====================================================
echo Oracle Trader Bot - VPS Deployment Instructions  
echo ====================================================
echo.
echo Server Information:
echo   IP: 194.127.178.181
echo   User: root
echo   Password: Z9X07C##z9z9z9
echo.
echo Step 1: Connect to server
echo   ssh root@194.127.178.181
echo   (Enter password when prompted)
echo.
echo Step 2: Find and navigate to project
echo   ls -la
echo   cd /opt/oracle_trader_bot
echo   (If not found, try: cd /root/oracle_trader_bot)
echo.
echo Step 3: Update code from GitHub
echo   git pull origin main
echo.
echo Step 4: Check current Docker containers
echo   docker ps -a
echo.
echo Step 5: Stop current services
echo   docker-compose -f oracle_trader_bot/deployment/docker-compose.yml down
echo.
echo Step 6: Rebuild and start services  
echo   docker-compose -f oracle_trader_bot/deployment/docker-compose.yml up -d --build
echo.
echo Step 7: Check service logs
echo   docker-compose -f oracle_trader_bot/deployment/docker-compose.yml logs oracle-trader
echo.
echo Step 8: Test endpoints
echo   curl http://localhost/health
echo   curl http://localhost/dashboard/api/test-data
echo.
echo Step 9: Verify external access
echo   Test in browser: http://194.127.178.181/dashboard/
echo.
echo ====================================================
pause
