# End-to-End Tests

This directory contains comprehensive end-to-end tests for the Oracle Trader Bot system.

## Tests Overview

### 🔧 API Flow Tests (`test_api_flow.py`)
Tests the complete backend API workflow:

1. **Settings GET** → Retrieve current settings with masked secrets
2. **Health Check (Before)** → Check exchange status without credentials  
3. **Settings PUT** → Set sandbox KuCoin credentials
4. **Health Check (After)** → Verify exchange status changes to authenticated
5. **Analysis Endpoint** → Test market data analysis endpoint
6. **Trade Endpoint** → Test dry-run trading signal endpoint

### 🎭 UI Tests (`test_ui_minimal.py`) 
Basic frontend UI tests using Playwright:

1. **Page Load** → Verify settings page loads correctly
2. **Form Interaction** → Test form elements and basic interactions

## Quick Start

### 1. Install Dependencies
```bash
pip install -r tests_e2e/requirements.txt
```

### 2. For UI Tests (Optional)
```bash
playwright install
```

### 3. Run Tests

#### API Tests Only
```bash
python tests_e2e/test_api_flow.py
```

#### UI Tests Only  
```bash
python tests_e2e/test_ui_minimal.py
```

#### All Tests with Pytest
```bash
pytest tests_e2e/ -v
```

## Test Configuration

### Backend API Base URL
The API tests will automatically use:
- `settings.API_INTERNAL_BASE_URL` from your config
- Default: `http://localhost:8000`

### Frontend UI Base URL  
The UI tests default to:
- `http://localhost:3000` (typical Vite/React dev server)
- Override by modifying the `base_url` parameter

### Test Credentials
The API tests use safe sandbox credentials:
- **API Key**: `test_api_key_sandbox_60f123abc456def`
- **Secret**: `test-secret-sandbox-12345678-abcd-efgh-ijkl-123456789abc`  
- **Passphrase**: `test_passphrase_sandbox_v2`
- **Sandbox Mode**: `true`

These are safe test credentials and won't affect any real trading accounts.

## Expected Results

### ✅ Successful E2E Test Flow:
1. Settings API accessible (GET/PUT work)
2. Health endpoint shows status change after authentication
3. Analysis endpoint returns market data (or acceptable error in no-auth mode)
4. Trading endpoint accessible (may return validation errors in sandbox)
5. UI page loads and basic form elements are present

### 🔍 What Gets Tested:
- **API Connectivity**: All endpoints respond appropriately
- **Authentication Flow**: Credential setting changes system behavior  
- **Data Flow**: Market analysis pipeline works
- **UI Basics**: Frontend loads and has interactive elements
- **Error Handling**: Graceful handling of sandbox/test limitations

## Troubleshooting

### Backend Server Not Running
```bash
# Start the backend server first
cd oracle_trader_bot
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### Frontend Not Running  
```bash
# Start the frontend server
cd oracle-trader-frontend
npm run dev
```

### Playwright Issues
```bash
# Reinstall browsers
playwright install

# Install system dependencies (Linux)
playwright install-deps
```

### Import Errors
Ensure you're running from the project root and the Oracle Trader Bot modules are in your Python path.

## CI/CD Integration

These tests are designed to work in CI/CD pipelines:

- **Headless mode**: UI tests run without GUI
- **Configurable timeouts**: Suitable for various environments  
- **Graceful failures**: Tests provide detailed error information
- **Flexible assertions**: Accept reasonable error states for sandbox/testing

## Test Philosophy

These E2E tests focus on:
- **System Integration**: Verify components work together
- **User Workflows**: Test realistic usage scenarios  
- **Deployment Validation**: Ensure production deployments work
- **Regression Prevention**: Catch integration breaking changes

The tests are designed to be:
- **Fast**: Complete flow in under 30 seconds
- **Reliable**: Work in various environments (local, CI, Docker)
- **Informative**: Provide clear success/failure reasons
