# Oracle Trader Bot - Troubleshooting Guide

This guide helps diagnose and resolve common issues encountered when deploying and running the Oracle Trader Bot.

## Table of Contents

1. [Quick Diagnostic Commands](#quick-diagnostic-commands)
2. [Deployment Issues](#deployment-issues)
3. [Service Issues](#service-issues)
4. [Performance Issues](#performance-issues)
5. [Network & SSL Issues](#network--ssl-issues)
6. [Database Issues](#database-issues)
7. [Application Issues](#application-issues)
8. [Monitoring & Logging](#monitoring--logging)

## Quick Diagnostic Commands

Run these commands first to get an overview of the system status:

```bash
# Check all services status
docker-compose ps

# Check resource usage
docker stats --no-stream

# Check system resources
free -h && df -h

# Check recent logs
docker-compose logs --tail=50

# Run health check
./scripts/monitor.sh

# Check network connectivity
curl -I http://localhost:8000/health
```

## Deployment Issues

### Issue: Deployment Script Fails

**Symptoms:**
- Script exits with error codes
- Services not starting properly
- Permission denied errors

**Diagnosis:**
```bash
# Check script permissions
ls -la scripts/deploy.sh

# Check system requirements
docker --version
docker-compose --version

# Check available disk space
df -h

# Check if ports are already in use
sudo netstat -tlnp | grep -E ':80|:443|:8000'
```

**Solutions:**

1. **Permission Issues:**
   ```bash
   chmod +x scripts/*.sh
   sudo usermod -aG docker $USER
   # Log out and log back in
   ```

2. **Port Conflicts:**
   ```bash
   # Find processes using ports
   sudo lsof -i :80
   sudo lsof -i :443
   
   # Stop conflicting services
   sudo systemctl stop apache2  # or nginx
   ```

3. **Insufficient Resources:**
   ```bash
   # Check memory
   free -h
   
   # Check disk space
   df -h
   
   # Clean up Docker
   docker system prune -a
   ```

### Issue: Environment Configuration Problems

**Symptoms:**
- Services fail to start
- Database connection errors
- Missing environment variables

**Diagnosis:**
```bash
# Check .env file exists and has correct permissions
ls -la .env

# Validate environment file syntax
cat .env | grep -v '^#' | grep -v '^$'

# Check for missing required variables
grep -E "SECRET_KEY|POSTGRES_PASSWORD|DOMAIN" .env
```

**Solutions:**
```bash
# Regenerate .env from template
cp .env.example .env

# Generate new secrets
openssl rand -base64 32

# Set proper permissions
chmod 600 .env
chown $USER:$USER .env
```

## Service Issues

### Issue: Docker Services Not Starting

**Symptoms:**
- `docker-compose ps` shows services as "Exit 1" or "Restarting"
- Services keep restarting

**Diagnosis:**
```bash
# Check service logs
docker-compose logs [service-name]

# Check Docker daemon status
sudo systemctl status docker

# Check container resource limits
docker stats

# Check for port conflicts
sudo netstat -tlnp | grep -E ':5432|:6379|:8000'
```

**Solutions:**

1. **Database Issues:**
   ```bash
   # Reset PostgreSQL data
   docker-compose down
   docker volume rm $(docker volume ls -q | grep postgres)
   docker-compose up -d postgres
   ```

2. **Memory Issues:**
   ```bash
   # Increase memory limits in docker-compose.yml
   deploy:
     resources:
       limits:
         memory: 2G
   ```

3. **Network Issues:**
   ```bash
   # Recreate Docker network
   docker-compose down
   docker network prune
   docker-compose up -d
   ```

### Issue: Health Checks Failing

**Symptoms:**
- Services show as unhealthy
- Load balancer not routing traffic

**Diagnosis:**
```bash
# Check health endpoint directly
curl -v http://localhost:8000/health

# Check application logs
docker-compose logs oracle-trader

# Check database connectivity
docker-compose exec postgres pg_isready -U trader
```

**Solutions:**
```bash
# Restart unhealthy services
docker-compose restart [service-name]

# Check health check configuration
grep -A 10 "healthcheck:" docker-compose.yml

# Increase health check timeouts
# Edit docker-compose.yml:
healthcheck:
  timeout: 30s
  interval: 60s
  retries: 5
```

## Performance Issues

### Issue: High CPU/Memory Usage

**Symptoms:**
- System becomes slow or unresponsive
- Out of memory errors
- High load averages

**Diagnosis:**
```bash
# Check system load
top
htop  # if available

# Check Docker container resources
docker stats

# Check memory usage by container
docker-compose exec oracle-trader cat /proc/meminfo

# Check for memory leaks
# Monitor memory usage over time
watch -n 5 'docker stats --no-stream'
```

**Solutions:**

1. **Scale Down Resource-Intensive Services:**
   ```bash
   # Reduce AI model complexity in application config
   # Limit worker processes
   MAX_WORKERS=2
   
   # Set container memory limits
   docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d
   ```

2. **Database Optimization:**
   ```bash
   # Connect to PostgreSQL
   docker-compose exec postgres psql -U trader -d oracle_trader
   
   # Optimize settings
   ALTER SYSTEM SET shared_buffers = '128MB';
   ALTER SYSTEM SET effective_cache_size = '512MB';
   SELECT pg_reload_conf();
   ```

3. **Clear Caches:**
   ```bash
   # Clear Redis cache
   docker-compose exec redis redis-cli FLUSHALL
   
   # Clear application logs
   docker-compose exec oracle-trader find /app/logs -name "*.log" -delete
   ```

### Issue: Slow Response Times

**Symptoms:**
- Application responds slowly
- Timeouts in web interface
- API calls take too long

**Diagnosis:**
```bash
# Test response times
time curl http://localhost:8000/health

# Check database query performance
docker-compose exec postgres psql -U trader -d oracle_trader -c "
SELECT query, calls, total_time, mean_time 
FROM pg_stat_statements 
ORDER BY total_time DESC 
LIMIT 10;"

# Check network latency
ping your-domain.com
```

**Solutions:**
```bash
# Add database indexes
# Connect to database and analyze slow queries

# Enable connection pooling
# Update DATABASE_URL with connection pooling parameters

# Optimize Nginx
# Add caching headers and compression
```

## Network & SSL Issues

### Issue: SSL Certificate Problems

**Symptoms:**
- Browser shows "Not Secure" warning
- SSL certificate errors
- HTTPS not working

**Diagnosis:**
```bash
# Check certificate status
openssl s_client -connect your-domain.com:443

# Check Let's Encrypt logs
docker-compose logs certbot

# Check certificate files
ls -la /etc/letsencrypt/live/your-domain.com/

# Test certificate renewal
docker-compose run --rm certbot renew --dry-run
```

**Solutions:**

1. **Regenerate Certificates:**
   ```bash
   # Remove existing certificates
   docker-compose run --rm certbot delete --cert-name your-domain.com
   
   # Generate new certificates
   docker-compose run --rm certbot certonly \
     --webroot --webroot-path=/var/www/certbot \
     --email your-email@domain.com \
     --agree-tos \
     -d your-domain.com -d www.your-domain.com
   ```

2. **Check DNS Configuration:**
   ```bash
   # Verify DNS records
   dig your-domain.com
   nslookup your-domain.com
   ```

3. **Force Certificate Renewal:**
   ```bash
   docker-compose run --rm certbot renew --force-renewal
   docker-compose restart nginx
   ```

### Issue: Domain Not Accessible

**Symptoms:**
- Cannot access application via domain
- DNS resolution fails
- Connection timeouts

**Diagnosis:**
```bash
# Check DNS resolution
nslookup your-domain.com
dig your-domain.com

# Check if server is reachable
ping your-server-ip

# Check if services are listening
sudo netstat -tlnp | grep -E ':80|:443'

# Check firewall
sudo ufw status
```

**Solutions:**
```bash
# Update DNS records (A record pointing to server IP)
# Wait for DNS propagation (up to 48 hours)

# Check firewall rules
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# Restart Nginx
docker-compose restart nginx
```

## Database Issues

### Issue: Database Connection Failures

**Symptoms:**
- Application cannot connect to database
- "Connection refused" errors
- Database timeout errors

**Diagnosis:**
```bash
# Check if PostgreSQL is running
docker-compose ps postgres

# Test database connectivity
docker-compose exec postgres pg_isready -U trader

# Check database logs
docker-compose logs postgres

# Test connection from application container
docker-compose exec oracle-trader python -c "
import asyncpg
import asyncio
async def test():
    try:
        conn = await asyncpg.connect('postgresql://trader:password@postgres:5432/oracle_trader')
        print('Connection successful')
        await conn.close()
    except Exception as e:
        print(f'Connection failed: {e}')
asyncio.run(test())
"
```

**Solutions:**

1. **Restart Database:**
   ```bash
   docker-compose restart postgres
   # Wait for database to be ready
   sleep 30
   ```

2. **Reset Database:**
   ```bash
   docker-compose down
   docker volume rm $(docker volume ls -q | grep postgres)
   docker-compose up -d postgres
   # Wait for initialization
   docker-compose exec postgres psql -U trader -c "SELECT version();"
   ```

3. **Check Configuration:**
   ```bash
   # Verify environment variables
   docker-compose exec oracle-trader env | grep POSTGRES
   
   # Check database URL format
   echo $DATABASE_URL
   ```

### Issue: Database Performance Problems

**Symptoms:**
- Slow query responses
- High database CPU usage
- Connection pool exhaustion

**Diagnosis:**
```bash
# Check active connections
docker-compose exec postgres psql -U trader -d oracle_trader -c "
SELECT count(*) as active_connections 
FROM pg_stat_activity 
WHERE state = 'active';"

# Check slow queries
docker-compose exec postgres psql -U trader -d oracle_trader -c "
SELECT query, calls, total_time, mean_time 
FROM pg_stat_statements 
ORDER BY total_time DESC 
LIMIT 5;"

# Check database size
docker-compose exec postgres psql -U trader -d oracle_trader -c "
SELECT pg_size_pretty(pg_database_size('oracle_trader'));"
```

**Solutions:**
```bash
# Optimize PostgreSQL settings
docker-compose exec postgres psql -U trader -d oracle_trader -c "
ALTER SYSTEM SET shared_buffers = '256MB';
ALTER SYSTEM SET effective_cache_size = '1GB';
ALTER SYSTEM SET maintenance_work_mem = '64MB';
SELECT pg_reload_conf();"

# Add indexes for frequently queried columns
# Analyze and vacuum database regularly
docker-compose exec postgres psql -U trader -d oracle_trader -c "VACUUM ANALYZE;"
```

## Application Issues

### Issue: Trading Functions Not Working

**Symptoms:**
- Orders not being placed
- Market data not updating
- AI predictions failing

**Diagnosis:**
```bash
# Check application logs
docker-compose logs oracle-trader | grep -i error

# Test API endpoints
curl -X GET http://localhost:8000/api/health
curl -X GET http://localhost:8000/api/market-data

# Check exchange connectivity
docker-compose exec oracle-trader python -c "
import ccxt
exchange = ccxt.kucoin({'apiKey': 'test', 'secret': 'test'})
try:
    ticker = exchange.fetch_ticker('BTC/USDT')
    print('Exchange connection OK')
except Exception as e:
    print(f'Exchange error: {e}')
"
```

**Solutions:**

1. **Check API Keys:**
   ```bash
   # Verify API keys are set
   grep -E "KUCOIN_|BINANCE_|KRAKEN_" .env
   
   # Test API key validity on exchange websites
   ```

2. **Network Connectivity:**
   ```bash
   # Test external connectivity from container
   docker-compose exec oracle-trader curl -I https://api.kucoin.com
   docker-compose exec oracle-trader curl -I https://api.binance.com
   ```

3. **Restart Application:**
   ```bash
   docker-compose restart oracle-trader
   ```

### Issue: WebSocket Connections Failing

**Symptoms:**
- Real-time data not updating
- WebSocket connection errors
- Frequent reconnections

**Diagnosis:**
```bash
# Check WebSocket endpoint
curl -i -N -H "Connection: Upgrade" -H "Upgrade: websocket" \
  http://localhost:8000/ws

# Check Nginx WebSocket configuration
grep -A 10 "location /ws" nginx/nginx.conf

# Check application WebSocket logs
docker-compose logs oracle-trader | grep -i websocket
```

**Solutions:**
```bash
# Update Nginx WebSocket configuration
# Add to nginx.conf:
location /ws {
    proxy_pass http://oracle_trader_backend;
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
    proxy_read_timeout 86400;
}

# Restart Nginx
docker-compose restart nginx
```

## Monitoring & Logging

### Issue: Missing or Incomplete Logs

**Symptoms:**
- No log files generated
- Logs not rotating
- Missing error information

**Diagnosis:**
```bash
# Check log directories
ls -la logs/

# Check Docker logging driver
docker info | grep "Logging Driver"

# Check log file permissions
ls -la logs/*.log

# Check disk space
df -h
```

**Solutions:**
```bash
# Create log directories
mkdir -p logs/{nginx,postgres,redis,grafana,prometheus}

# Set proper permissions
chmod 755 logs/
chmod 644 logs/*.log

# Configure log rotation
# Create /etc/logrotate.d/oracle-trader
sudo tee /etc/logrotate.d/oracle-trader > /dev/null <<EOF
/opt/oracle-trader/logs/*.log {
    daily
    missingok
    rotate 30
    compress
    notifempty
    copytruncate
}
EOF
```

### Issue: Monitoring Not Working

**Symptoms:**
- Grafana not accessible
- Prometheus not collecting metrics
- Alerts not firing

**Diagnosis:**
```bash
# Check monitoring services
docker-compose ps grafana prometheus

# Check Prometheus targets
curl http://localhost:9090/api/v1/targets

# Check Grafana logs
docker-compose logs grafana

# Test metrics endpoint
curl http://localhost:8000/metrics
```

**Solutions:**
```bash
# Restart monitoring services
docker-compose restart grafana prometheus

# Check Prometheus configuration
docker-compose exec prometheus cat /etc/prometheus/prometheus.yml

# Reset Grafana admin password
docker-compose exec grafana grafana-cli admin reset-admin-password admin123
```

## Common Error Messages and Solutions

### "Permission denied"
```bash
# Fix permissions
sudo chown -R $USER:$USER .
chmod +x scripts/*.sh
```

### "Port already in use"
```bash
# Find and stop conflicting process
sudo lsof -i :80
sudo systemctl stop apache2
```

### "No space left on device"
```bash
# Clean up disk space
docker system prune -a
sudo apt autoremove
```

### "Connection refused"
```bash
# Check service status and restart
docker-compose ps
docker-compose restart [service-name]
```

### "SSL certificate not found"
```bash
# Regenerate SSL certificates
docker-compose run --rm certbot certonly --webroot --webroot-path=/var/www/certbot -d your-domain.com
```

## Getting Additional Help

If you're still experiencing issues after following this guide:

1. **Check the logs** thoroughly for specific error messages
2. **Run the monitoring script** to get a comprehensive health check
3. **Search the issue tracker** on GitHub for similar problems
4. **Create a detailed bug report** including:
   - System information (`uname -a`, `docker --version`)
   - Error messages and logs
   - Steps to reproduce
   - Configuration files (with sensitive data removed)

Remember: Most issues are related to configuration, permissions, or resource constraints. Systematic troubleshooting usually reveals the root cause.