# Architecture Documentation

## Project Overview

Oracle Trader Bot is a professionalized Python trading bot with FastAPI backend and React TypeScript frontend. The system provides dual operating modes, comprehensive security features, and professional-grade architecture patterns.

## 🏗️ System Architecture

### Backend Structure
```
oracle_trader_bot/
├── app/
│   ├── main.py                     # FastAPI application entry point
│   ├── core/
│   │   ├── config.py               # Centralized configuration management
│   │   └── bot_process_manager.py  # Bot lifecycle management
│   ├── api/
│   │   ├── dependencies.py         # FastAPI dependencies
│   │   └── endpoints/
│   │       ├── settings_api.py     # Settings CRUD endpoints
│   │       └── health.py          # Health check endpoints
│   ├── middleware/
│   │   └── security_headers.py     # Security headers middleware
│   ├── security/
│   │   └── admin_auth.py          # Optional admin authentication
│   ├── utils/
│   │   ├── rate_limiter.py        # Token bucket rate limiting
│   │   ├── audit_logger.py        # Append-only audit logging
│   │   └── crypto_helper.py       # Optional AES-GCM encryption
│   ├── crud/
│   │   └── crud_settings.py       # Settings persistence layer
│   ├── models/                    # SQLAlchemy ORM models
│   ├── schemas/                   # Pydantic schemas
│   ├── strategies/                # Trading strategies
│   ├── exchange_clients/          # Exchange API clients
│   └── logs/                      # Application logs
├── bot_engine.py                  # Core trading bot logic
└── requirements.txt               # Python dependencies
```

### Frontend Structure
```
oracle-trader-frontend/
├── src/
│   ├── main.tsx                   # React application entry point
│   ├── App.tsx                    # Main application component
│   ├── services/
│   │   └── apiClient.ts          # Centralized API client with URL management
│   ├── components/               # Reusable React components
│   ├── pages/                    # Page-level components
│   └── assets/                   # Static assets
├── public/                       # Public static files
├── package.json                  # Node.js dependencies
├── vite.config.ts               # Vite build configuration
└── tsconfig.json                # TypeScript configuration
```

## 🔧 Settings Lifecycle Management

### Dual Persistence Architecture

The system operates with dual persistence modes:

#### **Lite Mode (File-based)**
- **Trigger**: `APP_STARTUP_MODE=lite` or missing DB credentials
- **Storage**: `settings.json` in application directory
- **Features**: Full settings UI, file-based persistence, zero DB dependency
- **Use Case**: Development, testing, simple deployments

#### **Full Mode (Database-based)**
- **Trigger**: `APP_STARTUP_MODE=full` with valid DB credentials
- **Storage**: PostgreSQL database via SQLAlchemy ORM
- **Features**: Full settings UI, database persistence, audit logging, migrations
- **Use Case**: Production deployments with PostgreSQL

### Settings Processing Pipeline

```
1. Request → 2. Validation → 3. Security → 4. Persistence → 5. Response
     ↓             ↓             ↓            ↓             ↓
   FastAPI    Pydantic     Masking/      File/DB      Masked JSON
  Endpoint    Schemas     Encryption    Storage       Response
```

### Secret Management

**Masking on GET Requests:**
- Secrets (API keys, passwords) masked as `***` in responses
- Original values preserved in storage
- Field detection via `SECRET_FIELDS` pattern matching

**Preservation on PUT Requests:**
- Empty values (`""`, `null`) → preserved existing secret
- Masked values (`***`) → preserved existing secret  
- New values → updated and stored securely

**Optional Encryption (AES-GCM):**
- **Trigger**: `SETTINGS_ENCRYPTION_KEY` environment variable set
- **Algorithm**: AES-256-GCM with random IV per encryption
- **Storage**: Base64-encoded encrypted JSON in file mode
- **Scope**: All settings data when encryption enabled

## 📊 Audit Logging System

### Append-Only Architecture
- **Format**: JSON Lines (JSONL) for efficient parsing
- **Storage**: `audit_settings.log` in logs directory
- **Immutability**: Append-only, no modifications allowed
- **Structure**: Timestamp, actor info, field changes with redacted secrets

### Actor Tracking
```json
{
  "timestamp": "2025-08-15T01:30:00.000Z",
  "actor": {
    "ip": "192.168.1.100",
    "user_agent": "Mozilla/5.0...",
    "headers": {"X-Admin-Token": "[REDACTED]"}
  },
  "changes": {
    "PROJECT_NAME": {"old": "Old Name", "new": "New Name"},
    "KUCOIN_API_KEY": {"old": "[REDACTED]", "new": "[REDACTED]"}
  }
}
```

### Automatic Management
- **Pagination**: 50 entries per page (configurable 1-100)
- **Rotation**: Auto-rotation when log exceeds 10MB
- **Privacy**: All secret values redacted as `[REDACTED]`
- **API Access**: GET `/api/v1/settings/audit` with admin token

## 🔐 Admin Guard System

### Optional Authentication Model
```python
# Backward Compatible Design
ADMIN_API_TOKEN=""     # → No authentication required
ADMIN_API_TOKEN="xyz"  # → X-Admin-Token header required
```

### Protected Endpoints
- **Write Operations**: `PUT /settings`, `POST /settings/reset`
- **Sensitive Data**: `GET /settings/audit`
- **Unprotected**: `GET /settings` (read-only, masked secrets)

### Security Features
- **Token Extraction**: `X-Admin-Token` header
- **Request Logging**: IP, User-Agent, success/failure (no token exposure)
- **Flexible Deployment**: Optional feature, zero impact when disabled

## ⚡ Rate Limiting System

### Token Bucket Algorithm
- **Implementation**: In-memory + optional Redis backend
- **Granularity**: Per-IP address tracking
- **Headers**: Standard rate limit headers (X-RateLimit-*)
- **Response**: HTTP 429 when limits exceeded

### Configuration
```bash
SETTINGS_RATE_LIMIT="10/min"    # Settings endpoints
HEALTH_RATE_LIMIT="30/min"      # Health check endpoints  
REDIS_URL="redis://localhost:6379"  # Optional distributed backend
```

### Endpoint Coverage
- **Settings API**: `/api/v1/settings*` → 10 requests/minute
- **Health Checks**: `/api/v1/health/*` → 30 requests/minute
- **Middleware Order**: CORS → Security Headers → Rate Limiting

## 🔄 Exchange Integration Modes

### Authentication-Based Modes

#### **No-Auth Mode**
- **Trigger**: Missing or empty KuCoin API credentials
- **Behavior**: 
  - Health endpoints report `exchange_status: "no_auth"`
  - Bot engine uses mock/simulation mode
  - All API endpoints remain functional
  - UI shows "No credentials configured"

#### **Auth Mode**  
- **Trigger**: Valid KuCoin API credentials provided
- **Behavior**:
  - Health endpoints report `exchange_status: "connected"` 
  - Bot engine uses live exchange connections
  - Full trading functionality enabled
  - UI shows live account information

### Health Endpoint Behavior
```json
// No-Auth Mode Response
{
  "status": "healthy",
  "exchange_status": "no_auth",
  "message": "System operational (no exchange credentials)",
  "timestamp": "2025-08-15T01:30:00.000Z"
}

// Auth Mode Response  
{
  "status": "healthy", 
  "exchange_status": "connected",
  "account_info": {"balance": "1000.00", "positions": 3},
  "timestamp": "2025-08-15T01:30:00.000Z"
}
```

## 🌐 URL Centralization

### Frontend API Client (`apiClient.ts`)
```typescript
export const CONFIG = {
  API_BASE_URL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1',
  WS_BASE_URL: import.meta.env.VITE_WS_BASE_URL || 'ws://localhost:8000/api/v1',
  REQUEST_TIMEOUT: 10000,
} as const;
```

### Backend Configuration (`config.py`)
```python
class Settings(BaseSettings):
    SERVER_PUBLIC_IP: str = "150.241.85.30" 
    API_INTERNAL_BASE_URL: str = "http://127.0.0.1:8000"
    
    @property
    def get_all_cors_origins(self) -> List[str]:
        # Dynamic CORS origins with SERVER_PUBLIC_IP
        return self.CORS_ALLOWED_ORIGINS + [
            f"http://{self.SERVER_PUBLIC_IP}:5173",
            f"https://{self.SERVER_PUBLIC_IP}",
            # ... additional dynamic origins
        ]
```

### Environment Variables
```bash
# Frontend
VITE_API_BASE_URL=http://localhost:8000/api/v1
VITE_WS_BASE_URL=ws://localhost:8000/api/v1

# Backend  
SERVER_PUBLIC_IP=150.241.85.30
API_INTERNAL_BASE_URL=http://127.0.0.1:8000
```

## 🏥 Health Endpoints & Lite Mode Boot

### Startup Modes

#### **Lite Mode Boot Process**
```
1. Load environment variables
2. Initialize file-based settings manager
3. Skip database connection attempts
4. Start FastAPI server
5. Health endpoints report "lite_mode" status
6. All API functionality available
```

#### **Full Mode Boot Process**
```
1. Load environment variables  
2. Test database connectivity
3. Run migrations if needed
4. Initialize database-based settings manager
5. Start FastAPI server
6. Health endpoints report "full_mode" status
```

### Health Check Endpoints
- **Application**: `GET /api/v1/health/app` - App status + settings mode
- **Database**: `GET /api/v1/health/db` - DB connectivity (full mode only)
- **Exchange**: `GET /api/v1/health/exchange` - Exchange connection status
- **System**: `GET /api/v1/health/system` - Overall system health

## 🔒 Security Headers Middleware

### Configurable Security Headers
```python
# Default Configuration (Production Ready)
SECURITY_HEADERS_X_CONTENT_TYPE_OPTIONS=True    # nosniff
SECURITY_HEADERS_X_FRAME_OPTIONS=True           # DENY  
SECURITY_HEADERS_REFERRER_POLICY=True           # no-referrer
SECURITY_HEADERS_STRICT_TRANSPORT_SECURITY=True # max-age=15552000 (HTTPS only)
SECURITY_HEADERS_CONTENT_SECURITY_POLICY=False  # Optional: default-src 'self'
```

### HTTPS Detection
- **Methods**: `X-Forwarded-Proto: https` header + `request.url.scheme`
- **HSTS Behavior**: Only applied on HTTPS requests
- **Middleware Order**: CORS → Security Headers → Rate Limiting → Application

## 🔄 Shims & Compatibility Adapters (Deprecated - Removal in v1.2)

> **⚠️ DEPRECATION NOTICE**: All shims and compatibility adapters are deprecated and will be removed in v1.2. See [SHIM_DEPRECATION_PLAN.md](../SHIM_DEPRECATION_PLAN.md) for complete removal plan and migration guide.

### Current Shims (Scheduled for v1.2 Removal)

#### **Backend Python Shims**
- **Package-Level**: `oracle_trader_bot/__init__.py` - Redirects `oracle_trader_bot.app.*` → `backend.app.*`
- **API Endpoints**: `oracle_trader_bot/app/api/endpoints/__init__.py` - Maps old endpoints → new routers
- **Status**: Emits `DeprecationWarning` on usage

#### **Frontend TypeScript Shims**  
- **Vite Aliases**: `@pages` → `/src/features`, `@api` → `/src/services/api`
- **TypeScript Paths**: Legacy path mappings in `tsconfig.json`
- **Status**: Build warnings for deprecated alias usage

#### **Migration Scripts**
- **Backend**: `scripts/rewrite_backend_imports.py`, `scripts/rewrite_phase2_imports.py`
- **Frontend**: `scripts/rewrite_frontend_imports.js`
- **Status**: Available for automated migration assistance

### Breaking Changes in v1.2

```python
# ❌ Will be removed in v1.2:
from oracle_trader_bot.app.core.config import settings
from app.api.endpoints.trading import router

# ✅ Use instead:
from app.core.config import settings
from app.api.routers.trading import router
```

```typescript
// ❌ Will be removed in v1.2:
import '@pages/Component'
import '@api/client'

// ✅ Use instead:  
import '@features/feature-name/components/Component'
import '@services/api/client'
```

### Migration Path
1. **Current (v1.1.x)**: Shims emit deprecation warnings guiding to new paths
2. **v1.1.9**: Final version with compatibility shims
3. **v1.2.0**: Complete shim removal - breaking change for legacy imports

For detailed migration instructions, see [SHIM_DEPRECATION_PLAN.md](../SHIM_DEPRECATION_PLAN.md).

## 🚀 Deployment Architecture

### Development Environment
```
Mode: Lite (APP_STARTUP_MODE=lite)
Storage: settings.json
Database: Optional (SQLite for testing)
Security: Minimal (no admin token)
Frontend: http://localhost:5173
Backend: http://localhost:8000
```

### Production Environment  
```
Mode: Full (APP_STARTUP_MODE=full)
Storage: PostgreSQL database
Database: Required with migrations
Security: Full (admin token, rate limiting, security headers)
Frontend: https://your-domain.com
Backend: https://api.your-domain.com
```

## 🔍 Zero Feature Loss Guarantee

### Compatibility Promise
- **Existing APIs**: All endpoints maintain same interface
- **Configuration**: Environment variables work as before
- **Functionality**: No trading features removed or degraded
- **Performance**: No significant latency increases
- **Dependencies**: Minimal new requirements (optional Redis, optional PostgreSQL)

### Validation Methods
- **Integration Tests**: Comprehensive test suite validates all functionality
- **Backward Compatibility**: Legacy configuration patterns supported
- **Graceful Fallbacks**: DB unavailable → lite mode, Redis unavailable → in-memory
- **Feature Toggles**: All new features can be disabled via environment variables
