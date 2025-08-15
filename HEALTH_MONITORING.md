# Health Monitoring System

This directory contains the health monitoring system for Oracle Trader Bot, providing automated health checks and alerting.

## 📁 Files

- **`health_monitor.py`** - Main health monitoring script
- **`.github/workflows/health-monitor.yml`** - GitHub Action for automated monitoring
- **`test_health_monitor_demo.py`** - Demo script to test health monitoring locally

## 🏥 Health Monitor Script

The `health_monitor.py` script provides comprehensive health monitoring capabilities:

### Features
- **Async endpoint checking** using aiohttp
- **Multiple health endpoints** support (`/health/app`, `/health/db`, `/health/exchange`)
- **Configurable timeouts** and retry logic
- **JSON and human-readable output** formats
- **Continuous monitoring mode** with configurable intervals
- **Comprehensive error handling** with detailed reporting

### Usage

```bash
# Basic health check
python health_monitor.py --url http://localhost:8000

# JSON output (for automation)
python health_monitor.py --url http://localhost:8000 --json

# Continuous monitoring (every 60 seconds)
python health_monitor.py --url http://localhost:8000 --interval 60

# Verbose output with detailed logging
python health_monitor.py --url http://localhost:8000 --verbose

# Custom timeout (default: 10 seconds)
python health_monitor.py --url http://localhost:8000 --timeout 30
```

### Exit Codes
- **0** - All health checks passed
- **1** - One or more health checks failed
- **2** - Critical error (network, configuration, etc.)

## 🤖 GitHub Action

The GitHub Action (`.github/workflows/health-monitor.yml`) provides automated monitoring:

### Features
- **Scheduled execution** - Runs every hour using cron
- **Multiple notification channels**:
  - Slack webhook integration
  - Email notifications via SMTP
  - GitHub Issues creation for persistent tracking
- **Artifact management** - Stores health check results
- **Comprehensive error handling** with fallback notifications

### Configuration

The GitHub Action uses the following secrets (configure in repository settings):

```bash
# Slack Integration (optional)
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/WEBHOOK/URL

# Email Notifications (optional)
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-app-password
NOTIFICATION_EMAIL=alerts@yourcompany.com
```

### Notification Channels

1. **Slack** - Real-time alerts to team channels
2. **Email** - Direct email notifications to administrators  
3. **GitHub Issues** - Creates issues for tracking and resolution
4. **GitHub Actions** - Native workflow failure notifications

## 🧪 Testing

Use the demo script to test the health monitoring locally:

```bash
# Run the interactive demo
python test_health_monitor_demo.py
```

The demo will:
1. Start a test server on http://localhost:8000
2. Run health checks against the test server
3. Display both human-readable and JSON output
4. Clean up the test server automatically

## 🔧 Customization

### Adding New Health Endpoints

To monitor additional endpoints, modify the `ENDPOINTS` list in `health_monitor.py`:

```python
ENDPOINTS = [
    "/api/v1/health/app",
    "/api/v1/health/db", 
    "/api/v1/health/exchange",
    "/api/v1/health/custom"  # Add your endpoint
]
```

### Adjusting Monitoring Frequency

Modify the cron schedule in `.github/workflows/health-monitor.yml`:

```yaml
on:
  schedule:
    - cron: '0 * * * *'    # Every hour
    # - cron: '*/15 * * * *'  # Every 15 minutes
    # - cron: '0 */6 * * *'   # Every 6 hours
```

### Custom Notification Logic

The GitHub Action supports conditional notifications. Modify the notification steps to customize when alerts are sent.

## 📊 Monitoring Dashboard

The health monitoring system provides several output formats:

### Human-Readable Output
```
🏥 Oracle Trader Bot - Health Monitor
==================================

🔍 Checking health endpoints...

✅ /api/v1/health/app - OK (123ms)
   Status: healthy
   
❌ /api/v1/health/db - FAILED (5000ms)
   Status: unhealthy
   Error: Connection timeout
   
⚠️  /api/v1/health/exchange - WARNING (2341ms)
   Status: degraded
   Details: Rate limit approaching

📊 Health Check Summary
======================
Total Checks: 3
✅ Passed: 1
❌ Failed: 1  
⚠️  Warnings: 1
Duration: 7.45s
```

### JSON Output
```json
{
  "timestamp": "2024-01-15T10:30:00Z",
  "base_url": "https://api.oracletrader.app",
  "total_duration": 7.45,
  "summary": {
    "total": 3,
    "passed": 1,
    "failed": 1,
    "warnings": 1
  },
  "results": [
    {
      "endpoint": "/api/v1/health/app",
      "success": true,
      "status_code": 200,
      "response_time": 0.123,
      "details": "healthy"
    }
  ]
}
```

## 🚀 Production Deployment

1. **Configure secrets** in GitHub repository settings
2. **Enable GitHub Actions** if not already enabled
3. **Test locally** using the demo script
4. **Commit and push** the health monitoring files
5. **Verify workflow execution** in GitHub Actions tab

The monitoring system will automatically begin running on the configured schedule and send notifications when health issues are detected.

## 📞 Support

For issues with the health monitoring system:

1. Check GitHub Actions logs for workflow execution details
2. Test locally using `test_health_monitor_demo.py`
3. Verify network connectivity and endpoint availability
4. Review notification channel configurations
