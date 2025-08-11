"""
Simple health check API endpoint to verify server connectivity
"""
from fastapi import APIRouter
from fastapi.responses import JSONResponse
import time

# Create a simple router for health checks
health_router = APIRouter()

@health_router.get("/health")
async def simple_health():
    """Simple health check endpoint"""
    return JSONResponse({
        "status": "ok",
        "timestamp": time.time(),
        "service": "Oracle Trader Bot",
        "version": "0.2.0_dashboard"
    })

@health_router.get("/api/health")
async def api_health():
    """API health check endpoint"""
    return JSONResponse({
        "status": "healthy",
        "timestamp": time.time(),
        "api_version": "v1",
        "endpoints": {
            "dashboard": "/dashboard/",
            "health": "/health",
            "test": "/dashboard/api/test-data"
        }
    })
