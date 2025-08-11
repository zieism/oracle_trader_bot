# Oracle Trader Bot - Server Deployment Guide

## Current Status
- **Server**: http://194.127.178.181/
- **Repository**: https://github.com/zieism/oracle_trader_bot
- **Branch**: main

## Recent Changes (Latest)

### 1. Dashboard API Improvements
- Fixed error handling in `app/dashboard/routes.py`
- Added mock data fallback for market data and account balance
- Added new test endpoint: `/dashboard/api/test-data`

### 2. Health Check Endpoints
- Added `app/api/endpoints/health_simple.py`
- New endpoints:
  - `/health` - Simple health check
  - `/api/health` - Detailed API health check

### 3. Frontend Resilience
- Improved `app/static/js/dashboard.js`
- Added fallback mechanism for failed API calls
- Better error handling and loading states
- Mock data display when all APIs fail

## Deployment Steps

### 1. Connect to Server
```bash
ssh root@194.127.178.181
```

### 2. Navigate to Project
```bash
cd /opt/oracle_trader_bot
```

### 3. Pull Latest Changes
```bash
git pull origin main
```

### 4. Restart Services
```bash
# Stop current containers
docker-compose -f oracle_trader_bot/deployment/docker-compose.yml down

# Rebuild and start
docker-compose -f oracle_trader_bot/deployment/docker-compose.yml up -d --build

# View logs
docker-compose -f oracle_trader_bot/deployment/docker-compose.yml logs -f oracle-trader
```

## Testing Endpoints

After deployment, test these URLs:

1. **Main Dashboard**: http://194.127.178.181/dashboard/
2. **Health Check**: http://194.127.178.181/health
3. **API Health**: http://194.127.178.181/api/health  
4. **Test Data**: http://194.127.178.181/dashboard/api/test-data

## Common Issues & Solutions

### Issue: Dashboard shows "Loading..." forever
**Solution**: 
1. Check if API endpoints are responding
2. Test `/dashboard/api/test-data` endpoint
3. Check container logs for errors

### Issue: Database connection errors
**Solution**:
1. Verify PostgreSQL container is running
2. Check environment variables in deployment
3. Verify database credentials

### Issue: WebSocket not connecting
**Solution**:
1. Check nginx configuration for WebSocket proxying
2. Verify WebSocket manager initialization
3. Check firewall settings

## Monitoring

### Check Container Status
```bash
docker ps
```

### View Logs
```bash
# Main application logs
docker logs oracle-trader-app

# Nginx logs  
docker logs oracle-trader-nginx

# Database logs
docker logs oracle-trader-postgres
```

### Check Resource Usage
```bash
docker stats
```

## Environment Configuration

Key environment variables to verify in deployment:
- `POSTGRES_USER`
- `POSTGRES_PASSWORD` 
- `POSTGRES_DB`
- `KUCOIN_API_KEY` (if using real trading)
- `KUCOIN_API_SECRET`
- `KUCOIN_API_PASSPHRASE`

## Next Steps

1. **Deploy current changes** to server
2. **Test all endpoints** to ensure they work
3. **Monitor logs** for any runtime errors
4. **Add real Kucoin integration** if needed
5. **Set up proper monitoring** with Grafana/Prometheus

## Contact

If issues persist, check:
1. Server logs: `/opt/oracle_trader_bot/logs/`
2. Docker container logs
3. GitHub repository for latest updates

Last updated: August 11, 2025
