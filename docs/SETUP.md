# Setup Guide

## Quick Start (Lite Mode)

The fastest way to get Oracle Trader Bot running locally for development and testing.

### Prerequisites
- Python 3.9+
- Node.js 18+
- Git

### 1. Backend Setup (Lite Mode)

```bash
# Clone repository
git clone https://github.com/your-username/oracle_trader_bot.git
cd oracle_trader_bot

# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# Install Python dependencies
cd oracle_trader_bot
pip install -r requirements.txt

# Set lite mode (no database required)
set APP_STARTUP_MODE=lite
set SKIP_DB_INIT=true

# Start backend server
python -m uvicorn app.main:app --reload --port 8000
```

Backend will be available at: `http://localhost:8000`

### 2. Frontend Setup

```bash
# Navigate to frontend directory
cd oracle-trader-frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

Frontend will be available at: `http://localhost:5173`

### 3. Verify Installation

Visit the frontend at `http://localhost:5173` and check:
- Settings page loads correctly
- Health checks show "lite_mode" status
- All UI components functional

## Environment Configuration

### Basic .env.example

Create `.env` file in the root directory:

```bash
# ==================== APP CONFIGURATION ====================
PROJECT_NAME="Oracle Trader Bot"
VERSION="1.0.0"
DEBUG=false

# ==================== STARTUP MODES ====================
# lite: File-based settings, no DB required (development)
# full: Database-based settings, DB required (production)
APP_STARTUP_MODE=lite
SKIP_DB_INIT=true

# ==================== SECURITY ====================
# Optional admin token for settings endpoints (leave empty to disable)
ADMIN_API_TOKEN=""

# Optional encryption key for settings file (32+ characters, leave empty to disable)
SETTINGS_ENCRYPTION_KEY=""

# ==================== FRONTEND URLS ====================
# Frontend API configuration
VITE_API_BASE_URL=http://localhost:8000/api/v1
VITE_WS_BASE_URL=ws://localhost:8000/api/v1

# ==================== BACKEND URLS ====================
# Server public IP for CORS and external access
SERVER_PUBLIC_IP=150.241.85.30
API_INTERNAL_BASE_URL=http://127.0.0.1:8000

# ==================== RATE LIMITING ====================
# Rate limits (format: "requests/timeunit" - min, hour, day)
SETTINGS_RATE_LIMIT=10/min
HEALTH_RATE_LIMIT=30/min

# Optional Redis for distributed rate limiting (leave empty for in-memory)
REDIS_URL=""

# ==================== SECURITY HEADERS ====================
# Security headers (true/false)
SECURITY_HEADERS_X_CONTENT_TYPE_OPTIONS=true
SECURITY_HEADERS_X_FRAME_OPTIONS=true
SECURITY_HEADERS_REFERRER_POLICY=true
SECURITY_HEADERS_STRICT_TRANSPORT_SECURITY=true
SECURITY_HEADERS_CONTENT_SECURITY_POLICY=false

# ==================== EXCHANGE API ====================
# KuCoin API credentials (leave empty for no-auth mode)
KUCOIN_API_KEY=""
KUCOIN_API_SECRET=""
KUCOIN_API_PASSPHRASE=""
KUCOIN_SANDBOX=true

# ==================== DATABASE (Full Mode Only) ====================
POSTGRES_SERVER=localhost
POSTGRES_PORT=5432
POSTGRES_USER=your_username
POSTGRES_PASSWORD=your_password
POSTGRES_DB=oracle_trader_bot
```

## Full Mode Setup (Production)

### 1. Database Setup

#### PostgreSQL Installation
```bash
# Install PostgreSQL (Ubuntu/Debian)
sudo apt update
sudo apt install postgresql postgresql-contrib

# Create database and user
sudo -u postgres psql

CREATE DATABASE oracle_trader_bot;
CREATE USER your_username WITH ENCRYPTED PASSWORD 'your_password';
GRANT ALL PRIVILEGES ON DATABASE oracle_trader_bot TO your_username;
\q
```

#### SQLite (Alternative for testing)
```bash
# SQLite requires no installation, just update connection string
# In .env file:
ASYNC_DATABASE_URL=sqlite+aiosqlite:///./oracle_trader_bot.db
```

### 2. Environment Configuration

Update your `.env` file:
```bash
# Switch to full mode
APP_STARTUP_MODE=full
SKIP_DB_INIT=false

# Database credentials
POSTGRES_SERVER=localhost
POSTGRES_PORT=5432
POSTGRES_USER=your_username
POSTGRES_PASSWORD=your_password
POSTGRES_DB=oracle_trader_bot

# Optional: Enable admin authentication
ADMIN_API_TOKEN=your_secure_admin_token_here

# Optional: Enable settings encryption
SETTINGS_ENCRYPTION_KEY=your_32_character_encryption_key_here
```

### 3. Database Migrations

```bash
# Install Alembic for migrations (if not included)
pip install alembic

# Initialize database (first time only)
cd oracle_trader_bot
python -c "
from app.db.session import init_db
import asyncio
asyncio.run(init_db())
"

# Start in full mode
set APP_STARTUP_MODE=full
python -m uvicorn app.main:app --reload --port 8000
```

## Running Tests

### Backend Tests
```bash
cd oracle_trader_bot

# Run all tests
python -m pytest tests/ -v

# Run specific test categories
python -m pytest tests/test_settings_security.py -v  # Settings security
python -m pytest tests/test_rate_limiter.py -v       # Rate limiting
python -m pytest tests/test_admin_auth.py -v         # Admin authentication
python -m pytest tests/test_security_headers.py -v   # Security headers

# Run integration tests
python -m pytest tests/test_integration_smoke.py -v
```

### Frontend Tests
```bash
cd oracle-trader-frontend

# Run frontend tests
npm test

# Run E2E tests (if available)
npm run test:e2e
```

## Common Make Commands

Create a `Makefile` in the root directory:

```makefile
# ==================== DEVELOPMENT ====================
.PHONY: dev-backend dev-frontend dev install-backend install-frontend

install-backend:
	cd oracle_trader_bot && pip install -r requirements.txt

install-frontend:
	cd oracle-trader-frontend && npm install

dev-backend:
	cd oracle_trader_bot && set APP_STARTUP_MODE=lite && python -m uvicorn app.main:app --reload --port 8000

dev-frontend:
	cd oracle-trader-frontend && npm run dev

dev: dev-backend dev-frontend

# ==================== TESTING ====================
.PHONY: test test-backend test-frontend

test-backend:
	cd oracle_trader_bot && python -m pytest tests/ -v

test-frontend:
	cd oracle-trader-frontend && npm test

test: test-backend test-frontend

# ==================== PRODUCTION ====================
.PHONY: build-frontend deploy-prod

build-frontend:
	cd oracle-trader-frontend && npm run build

deploy-prod:
	set APP_STARTUP_MODE=full && cd oracle_trader_bot && python -m uvicorn app.main:app --host 0.0.0.0 --port 8000

# ==================== UTILITIES ====================
.PHONY: clean lint format

clean:
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	find . -type d -name "node_modules" -exec rm -rf {} +

lint:
	cd oracle_trader_bot && python -m flake8 app/ tests/
	cd oracle-trader-frontend && npm run lint

format:
	cd oracle_trader_bot && python -m black app/ tests/
	cd oracle-trader-frontend && npm run format

# ==================== ANALYSIS ====================
.PHONY: analyze

analyze:
	python repo_xray.py
```

### Usage Examples
```bash
# Setup for development
make install-backend install-frontend

# Start development servers
make dev

# Run tests
make test

# Build for production
make build-frontend

# Clean up
make clean
```

## IDE Configuration

### VS Code Settings (`.vscode/settings.json`)
```json
{
  "python.defaultInterpreterPath": "./venv/bin/python",
  "python.linting.enabled": true,
  "python.linting.pylintEnabled": false,
  "python.linting.flake8Enabled": true,
  "python.formatting.provider": "black",
  "typescript.preferences.importModuleSpecifier": "relative",
  "editor.formatOnSave": true,
  "files.exclude": {
    "**/__pycache__": true,
    "**/node_modules": true,
    "**/.git": true
  }
}
```

### Recommended Extensions
- Python
- Pylance  
- TypeScript and JavaScript Language Features
- ES7+ React/Redux/React-Native snippets
- Prettier - Code formatter
- GitLens

## Docker Setup (Optional)

### Backend Dockerfile
```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY oracle_trader_bot/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY oracle_trader_bot/ .

# Expose port
EXPOSE 8000

# Run application
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Frontend Dockerfile
```dockerfile
FROM node:18-alpine AS builder

WORKDIR /app

# Install dependencies
COPY oracle-trader-frontend/package*.json ./
RUN npm ci

# Build application
COPY oracle-trader-frontend/ .
RUN npm run build

# Production stage
FROM nginx:alpine
COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/nginx.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
```

### Docker Compose
```yaml
version: '3.8'

services:
  backend:
    build:
      context: .
      dockerfile: Dockerfile.backend
    ports:
      - "8000:8000"
    environment:
      - APP_STARTUP_MODE=full
      - POSTGRES_SERVER=db
    depends_on:
      - db
      - redis

  frontend:
    build:
      context: .
      dockerfile: Dockerfile.frontend
    ports:
      - "80:80"
    depends_on:
      - backend

  db:
    image: postgres:15
    environment:
      POSTGRES_DB: oracle_trader_bot
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
    volumes:
      - postgres_data:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"

volumes:
  postgres_data:
```

## Next Steps

1. **Development**: Use lite mode for local development
2. **Testing**: Run comprehensive test suites
3. **Production**: Set up PostgreSQL and switch to full mode
4. **Security**: Configure admin tokens and encryption keys
5. **Monitoring**: Set up logging and health check monitoring
6. **Deployment**: Use Docker or direct deployment strategies

For troubleshooting common issues, see [TROUBLESHOOTING.md](./TROUBLESHOOTING.md).
