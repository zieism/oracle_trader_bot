# Troubleshooting Guide

## Common Issues & Solutions

### 🌐 CORS & Origin Issues

#### **Problem**: CORS errors when accessing frontend from different IP/port

**Symptoms:**
```
Access to XMLHttpRequest at 'http://localhost:8000/api/v1/settings' 
from origin 'http://192.168.1.100:5173' has been blocked by CORS policy
```

**Solutions:**

1. **Update SERVER_PUBLIC_IP in environment:**
```bash
# In .env file
SERVER_PUBLIC_IP=192.168.1.100  # Your actual server IP
```

2. **Add custom origins to CORS_ALLOWED_ORIGINS:**
```python
# In app/core/config.py or via environment
CORS_ALLOWED_ORIGINS=["http://192.168.1.100:5173", "http://localhost:5173"]
```

3. **Check frontend API base URL:**
```bash
# In oracle-trader-frontend/.env  
VITE_API_BASE_URL=http://192.168.1.100:8000/api/v1
```

4. **Restart both frontend and backend after changes**

#### **Problem**: CORS policy blocks requests from production domain

**Solution:**
```python
# Add production domains to CORS origins
CORS_ALLOWED_ORIGINS=[
    "https://your-domain.com",
    "https://www.your-domain.com", 
    "http://localhost:5173"  # Keep for development
]
```

---

### 💾 Database & Mode Switching

#### **Problem**: "Database connection failed" in full mode

**Symptoms:**
```
sqlalchemy.exc.OperationalError: (psycopg2.OperationalError) 
connection to server at "localhost" (127.0.0.1), port 5432 failed
```

**Solutions:**

1. **Switch to lite mode temporarily:**
```bash
set APP_STARTUP_MODE=lite
set SKIP_DB_INIT=true
```

2. **Check PostgreSQL service:**
```bash
# Windows
Get-Service postgresql*

# Linux
sudo systemctl status postgresql

# Mac
brew services list | grep postgresql
```

3. **Verify database credentials:**
```bash
# Test connection manually
psql -h localhost -U your_username -d oracle_trader_bot
```

4. **Check firewall/port access:**
```bash
# Test port connectivity
telnet localhost 5432
```

#### **Problem**: Settings lost when switching between modes

**Explanation**: Lite mode uses `settings.json`, full mode uses database. They don't sync automatically.

**Solutions:**

1. **Export settings before switching:**
```bash
# From lite mode, backup settings.json
cp oracle_trader_bot/settings.json settings_backup.json
```

2. **Import to database mode:**
```python
# In full mode, use settings API to bulk import
# Or manually copy important settings
```

3. **Use consistent mode in production:**
```bash
# Set once and don't change
APP_STARTUP_MODE=full  # For production with DB
# or
APP_STARTUP_MODE=lite  # For development/simple deployments
```

---

### 🔑 Authentication & Authorization

#### **Problem**: 401 Unauthorized errors on settings endpoints

**Symptoms:**
```
HTTP 401: {"detail": {"ok": false, "reason": "unauthorized"}}
```

**Diagnosis:**
```bash
# Check if admin auth is enabled
echo $ADMIN_API_TOKEN
# If this returns a value, admin auth is enabled
```

**Solutions:**

1. **Disable admin auth (development):**
```bash
set ADMIN_API_TOKEN=""
# or remove the environment variable entirely
```

2. **Provide admin token in requests:**
```javascript
// In frontend API calls
headers: {
  'X-Admin-Token': 'your_admin_token_here'
}
```

3. **Check token match:**
```bash
# Verify token is exactly as expected (no extra spaces)
echo "[$ADMIN_API_TOKEN]"  # Should show [your_token] without extra chars
```

#### **Problem**: Admin token not working despite being set

**Common Issues:**

1. **Whitespace in token:**
```bash
# Wrong (has spaces)
ADMIN_API_TOKEN=" my-token "

# Correct  
ADMIN_API_TOKEN="my-token"
```

2. **Case sensitivity:**
```bash
# Header must be exactly
X-Admin-Token: your_token

# Not x-admin-token or X-ADMIN-TOKEN
```

3. **Token in wrong location:**
```javascript
// Wrong - in body
{headers: {}, body: {token: "..."}}

// Correct - in headers
{headers: {"X-Admin-Token": "..."}}
```

---

### ⚡ Rate Limiting Issues

#### **Problem**: 429 Too Many Requests errors

**Symptoms:**
```
HTTP 429: Rate limit exceeded. Try again in 42 seconds.
Headers: X-RateLimit-Limit: 10, X-RateLimit-Remaining: 0
```

**Solutions:**

1. **Check rate limit configuration:**
```bash
# Current limits
echo $SETTINGS_RATE_LIMIT  # Default: 10/min
echo $HEALTH_RATE_LIMIT    # Default: 30/min
```

2. **Increase limits for development:**
```bash
set SETTINGS_RATE_LIMIT=100/min
set HEALTH_RATE_LIMIT=200/min
```

3. **Clear rate limit state:**
```bash
# Restart backend to clear in-memory counters
# Or if using Redis:
redis-cli FLUSHDB
```

4. **Use different IP/test from different machine:**
```bash
# Rate limits are per-IP
curl -H "X-Forwarded-For: 192.168.1.200" http://localhost:8000/api/v1/settings
```

#### **Problem**: Rate limiting not working (no headers in response)

**Diagnosis:**
- Check if rate limiting middleware is properly loaded
- Verify endpoints are covered by rate limiting dependencies

**Solution:**
```python
# Ensure rate limiting is applied to endpoints
@router.get("/settings")
async def get_settings(
    _: None = Depends(rate_limit(settings.SETTINGS_RATE_LIMIT, "settings"))
):
```

---

### 🔒 Security Headers Issues

#### **Problem**: Content Security Policy blocking resources

**Symptoms:**
```
Refused to load the script because it violates the following 
Content Security Policy directive: "default-src 'self'"
```

**Solutions:**

1. **Disable CSP temporarily:**
```bash
set SECURITY_HEADERS_CONTENT_SECURITY_POLICY=false
```

2. **Customize CSP policy:**
```python
# In app/middleware/security_headers.py, modify CSP value
csp_value = "default-src 'self' 'unsafe-inline' 'unsafe-eval'"
```

3. **Check browser developer console for specific blocked resources**

#### **Problem**: X-Frame-Options blocking embedded iframe

**Solution:**
```bash
# Allow iframe embedding
set SECURITY_HEADERS_X_FRAME_OPTIONS=false
```

---

### 🔍 Exchange Integration Issues

#### **Problem**: "No exchange credentials" despite setting API keys

**Diagnosis:**
```python
# Test credential detection
from app.core.config import settings
print("Has credentials:", settings.has_exchange_credentials())
print("API Key:", settings.KUCOIN_API_KEY[:10] + "..." if settings.KUCOIN_API_KEY else "None")
```

**Solutions:**

1. **Verify all three credentials are set:**
```bash
# All three required
set KUCOIN_API_KEY=your_api_key
set KUCOIN_API_SECRET=your_api_secret  
set KUCOIN_API_PASSPHRASE=your_passphrase
```

2. **Check for whitespace/hidden characters:**
```bash
# Print exact values to check for issues
echo "[${KUCOIN_API_KEY}]"
```

3. **Test sandbox mode first:**
```bash
set KUCOIN_SANDBOX=true
```

#### **Problem**: Exchange connection fails with valid credentials

**Solutions:**

1. **Check API permissions:**
   - Ensure API key has futures trading permissions
   - Verify IP whitelist includes your server IP

2. **Test API connectivity:**
```bash
# Test direct API call
curl -X GET "https://api-futures.kucoin.com/api/v1/timestamp"
```

3. **Check sandbox vs production URLs:**
```python
# In settings, verify base URL matches sandbox setting
KUCOIN_SANDBOX=true -> uses sandbox URL
KUCOIN_SANDBOX=false -> uses production URL
```

---

### 🔧 Repository Analysis Issues

#### **Problem**: `repo_xray.py` OpenAPI analysis fails

**Symptoms:**
```
Failed to fetch OpenAPI spec from http://localhost:8000/openapi.json
Connection refused / timeout
```

**Solutions:**

1. **Ensure backend is running:**
```bash
cd oracle_trader_bot
python -m uvicorn app.main:app --port 8000
```

2. **Use static analysis fallback:**
```bash
# repo_xray.py automatically falls back to static analysis
# Check output shows "Using static analysis (OpenAPI unavailable)"
```

3. **Update OpenAPI endpoint URL:**
```python
# In repo_xray.py, verify URL matches your setup
OPENAPI_URL = "http://localhost:8000/openapi.json"
```

#### **Problem**: Analyzer reports missing files/endpoints

**Solutions:**

1. **Refresh analysis:**
```bash
python repo_xray.py --force-refresh
```

2. **Check file permissions:**
```bash
# Ensure analyzer can read all files
chmod -R 755 oracle_trader_bot/
```

---

### 📱 Frontend Development Issues

#### **Problem**: Frontend can't connect to backend API

**Symptoms:**
```
Network Error: Request failed with status code undefined
```

**Solutions:**

1. **Check API base URL:**
```bash
# In oracle-trader-frontend/.env.local
VITE_API_BASE_URL=http://localhost:8000/api/v1
```

2. **Verify backend is accessible:**
```bash
curl http://localhost:8000/api/v1/health/app
```

3. **Check for port conflicts:**
```bash
netstat -an | grep 8000
```

#### **Problem**: Hot reload not working in development

**Solutions:**

1. **Check Vite configuration:**
```javascript
// vite.config.ts
export default defineConfig({
  server: {
    host: true,  // Enable network access
    port: 5173
  }
})
```

2. **Restart dev server:**
```bash
cd oracle-trader-frontend
npm run dev
```

---

### 🧪 Testing Issues

#### **Problem**: Tests failing with "Module not found" errors

**Solutions:**

1. **Ensure correct Python path:**
```bash
cd oracle_trader_bot
python -m pytest tests/ -v
# Not: python tests/test_something.py
```

2. **Install test dependencies:**
```bash
pip install pytest pytest-asyncio httpx
```

3. **Check test environment variables:**
```bash
# Some tests may need specific env vars
set TESTING=true
```

#### **Problem**: Integration tests timeout

**Solutions:**

1. **Increase test timeouts:**
```python
# In test files
@pytest.mark.timeout(60)  # 60 seconds
```

2. **Check for port conflicts during testing:**
```bash
# Kill any running servers before tests
taskkill /F /IM python.exe  # Windows
pkill -f uvicorn              # Linux/Mac
```

---

### 🚀 Production Deployment Issues

#### **Problem**: Application crashes with "Permission denied" errors

**Solutions:**

1. **Check file permissions:**
```bash
chmod 644 oracle_trader_bot/settings.json
chmod 755 oracle_trader_bot/logs/
```

2. **Verify user has write access to log directory:**
```bash
ls -la oracle_trader_bot/logs/
# Should show write permissions for running user
```

#### **Problem**: Environment variables not loaded in production

**Solutions:**

1. **Verify .env file location:**
```bash
# Should be in root directory alongside oracle_trader_bot/
ls -la .env
```

2. **Check environment variable precedence:**
```bash
# System env vars override .env file
export APP_STARTUP_MODE=full  # This overrides .env
```

3. **Use explicit environment loading:**
```python
# In production startup script
from dotenv import load_dotenv
load_dotenv()
```

---

## Getting Help

### Log Analysis
1. **Check application logs:**
```bash
# Backend logs
tail -f oracle_trader_bot/logs/api_server.log

# System logs (Linux)
journalctl -u your-service-name -f
```

2. **Enable debug logging:**
```bash
set DEBUG=true
set LOG_LEVEL=DEBUG
```

### Community Support
- Check GitHub Issues for similar problems
- Create detailed issue reports with:
  - Environment details (OS, Python version)
  - Configuration (anonymized)
  - Error logs and stack traces
  - Steps to reproduce

### Advanced Debugging
```python
# Add to startup code for debugging
import logging
logging.basicConfig(level=logging.DEBUG)
```

```bash
# Network debugging
curl -v http://localhost:8000/api/v1/health/app
```

For architecture details, see [ARCHITECTURE.md](./ARCHITECTURE.md)  
For setup instructions, see [SETUP.md](./SETUP.md)
