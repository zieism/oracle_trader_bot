Write-Host "Oracle Trader Bot - Server Deployment Commands" -ForegroundColor Green
Write-Host "=============================================" -ForegroundColor Gray
Write-Host ""
Write-Host "Server: 194.127.178.181" -ForegroundColor Yellow
Write-Host "User: root" -ForegroundColor Yellow  
Write-Host "Password: Z9X07C##z9z9z9" -ForegroundColor Yellow
Write-Host ""
Write-Host "1. Connect to server:" -ForegroundColor Cyan
Write-Host "   ssh root@194.127.178.181" -ForegroundColor White
Write-Host ""
Write-Host "2. Navigate to project directory:" -ForegroundColor Cyan
Write-Host "   cd /opt/oracle_trader_bot" -ForegroundColor White
Write-Host "   # OR if not found:" -ForegroundColor Gray
Write-Host "   cd /root/oracle_trader_bot" -ForegroundColor White
Write-Host ""
Write-Host "3. Update code from GitHub:" -ForegroundColor Cyan
Write-Host "   git pull origin main" -ForegroundColor White
Write-Host ""
Write-Host "4. Check current containers:" -ForegroundColor Cyan
Write-Host "   docker ps -a" -ForegroundColor White
Write-Host ""
Write-Host "5. Stop containers:" -ForegroundColor Cyan
Write-Host "   docker-compose -f oracle_trader_bot/deployment/docker-compose.yml down" -ForegroundColor White
Write-Host ""
Write-Host "6. Rebuild and start:" -ForegroundColor Cyan
Write-Host "   docker-compose -f oracle_trader_bot/deployment/docker-compose.yml up -d --build" -ForegroundColor White
Write-Host ""
Write-Host "7. Check logs:" -ForegroundColor Cyan
Write-Host "   docker-compose -f oracle_trader_bot/deployment/docker-compose.yml logs oracle-trader" -ForegroundColor White
Write-Host ""
Write-Host "8. Test endpoints:" -ForegroundColor Cyan
Write-Host "   curl http://localhost/health" -ForegroundColor White
Write-Host "   curl http://localhost/dashboard/api/test-data" -ForegroundColor White
