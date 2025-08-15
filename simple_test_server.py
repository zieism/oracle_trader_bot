#!/usr/bin/env python3
"""
Simple test server for CORS validation with environment-driven allowlist
"""
import uvicorn
import time
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from collections import defaultdict
import os

app = FastAPI(title="Oracle Trader Bot - CORS Test Server")

# Environment-driven CORS configuration
FRONTEND_ORIGINS = os.environ.get(
    "FRONTEND_ORIGINS", 
    "http://localhost:5173,https://oracletrader.app,https://www.oracletrader.app"
)

def parse_csv_env(value: str) -> list[str]:
    """Parse comma-separated environment variable into list of strings."""
    if not value:
        return []
    return list(set(origin.strip() for origin in value.split(',') if origin.strip()))

def get_all_cors_origins() -> list[str]:
    """Get all CORS origins from environment configuration."""
    return parse_csv_env(FRONTEND_ORIGINS)

# Get exact origins from environment
origins = get_all_cors_origins()
print(f"CORS allowed origins: {origins}")

# Add CORS middleware with exact origin allowlist (NO wildcards with credentials=True)
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,  # Exact origins only
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["X-RateLimit-Limit", "X-RateLimit-Remaining", "X-RateLimit-Reset", "Retry-After"],
    max_age=600,  # Cache preflight requests for 10 minutes
)

# Simple rate limiting storage
request_counts = defaultdict(list)

def check_rate_limit(client_ip: str, limit: int = 10, window: int = 60) -> tuple[bool, dict]:
    """Check if client is rate limited and return headers"""
    current_time = time.time()
    
    # Clean old requests
    request_counts[client_ip] = [
        req_time for req_time in request_counts[client_ip] 
        if current_time - req_time < window
    ]
    
    # Count current requests
    requests_in_window = len(request_counts[client_ip])
    remaining = max(0, limit - requests_in_window - 1)
    
    # Rate limit headers
    headers = {
        "X-RateLimit-Limit": str(limit),
        "X-RateLimit-Remaining": str(remaining), 
        "X-RateLimit-Reset": str(int(current_time + window))
    }
    
    # Check if rate limited
    if requests_in_window >= limit:
        return False, headers
    
    # Add current request
    request_counts[client_ip].append(current_time)
    return True, headers

# Rate limiting simulation (just headers)
from typing import Dict, Any

def add_rate_limit_headers() -> Dict[str, str]:
    return {
        "X-RateLimit-Limit": "10",
        "X-RateLimit-Remaining": "9", 
        "X-RateLimit-Reset": "1640995200"
    }

def add_security_headers() -> Dict[str, str]:
    return {
        "X-Content-Type-Options": "nosniff",
        "X-Frame-Options": "DENY",
        "Referrer-Policy": "no-referrer"
    }

@app.get("/")
async def root(request: Request):
    client_ip = request.client.host
    allowed, rate_headers = check_rate_limit(client_ip)
    
    if not allowed:
        headers = {**add_security_headers(), **rate_headers}
        return JSONResponse(
            content={"error": "Rate limit exceeded"}, 
            status_code=429,
            headers=headers
        )
    
    headers = {**add_security_headers(), **rate_headers}
    return JSONResponse(
        content={"message": "Oracle Trader Bot Frontend", "status": "running"},
        headers=headers
    )

@app.get("/api/v1/health/app")
async def health_app(request: Request):
    client_ip = request.client.host
    allowed, rate_headers = check_rate_limit(client_ip)
    
    if not allowed:
        headers = {**add_security_headers(), **rate_headers}
        return JSONResponse(
            content={"error": "Rate limit exceeded"}, 
            status_code=429,
            headers=headers
        )
    
    headers = {**add_security_headers(), **rate_headers}
    return JSONResponse(
        content={
            "status": "healthy",
            "service": "oracle-trader-bot",
            "version": "1.0.0",
            "timestamp": "2025-01-15T02:25:00Z"
        },
        headers=headers
    )

@app.get("/api/v1/settings/")
async def get_settings(request: Request):
    client_ip = request.client.host
    allowed, rate_headers = check_rate_limit(client_ip)
    
    if not allowed:
        headers = {**add_security_headers(), **rate_headers}
        return JSONResponse(
            content={"error": "Rate limit exceeded"}, 
            status_code=429,
            headers=headers
        )
    
    headers = {**add_security_headers(), **rate_headers}
    return JSONResponse(
        content={
            "KUCOIN_API_KEY": "***",
            "KUCOIN_API_SECRET": "***", 
            "KUCOIN_API_PASSPHRASE": "***",
            "ADMIN_API_TOKEN": "***",
            "TRADING_MODE": "paper",
            "MAX_RISK_PER_TRADE": 0.02
        },
        headers=headers
    )

@app.get("/api/v1/settings/audit")
async def get_audit(request: Request):
    client_ip = request.client.host
    allowed, rate_headers = check_rate_limit(client_ip)
    
    if not allowed:
        headers = {**add_security_headers(), **rate_headers}
        return JSONResponse(
            content={"error": "Rate limit exceeded"}, 
            status_code=429,
            headers=headers
        )
    
    headers = {**add_security_headers(), **rate_headers}
    return JSONResponse(
        content={
            "message": "Audit endpoint accessible",
            "last_modified": "2025-01-15T02:25:00Z"
        },
        headers=headers
    )

# Handle OPTIONS for CORS (FastAPI CORSMiddleware should handle this, but let's ensure proper 204 response)
@app.options("/api/v1/{path:path}")
async def options_handler(path: str, request: Request):
    """Handle OPTIONS requests and return 204 for valid origins"""
    origin = request.headers.get("origin", "")
    
    headers = {
        **add_security_headers(),
        "Access-Control-Allow-Origin": origin if origin in origins else "",
        "Access-Control-Allow-Methods": "GET, POST, PUT, PATCH, DELETE, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type, Authorization, X-Requested-With",
        "Access-Control-Allow-Credentials": "true",
        "Access-Control-Max-Age": "600"
    }
    
    # Only return CORS headers if origin is allowed
    if origin not in origins:
        headers = {k: v for k, v in headers.items() if not k.startswith("Access-Control")}
    
    return JSONResponse(content=None, status_code=204, headers=headers)

if __name__ == "__main__":
    print("Starting Simple Test Server for Smoke Testing...")
    print("Server available at: http://localhost:8000")
    uvicorn.run(app, host="0.0.0.0", port=8000)
