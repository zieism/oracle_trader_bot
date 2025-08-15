"""
Network utilities for Oracle Trader Bot

Provides unified helpers for resolving external base URLs without hardcoded IPs.
Supports environment variables, proxy headers, and request context resolution.
"""

from typing import Optional
import os
from urllib.parse import urlparse

try:
    from fastapi import Request
except ImportError:
    Request = None  # For environments where FastAPI isn't available


def resolve_external_base_url(request: Optional["Request"] = None) -> str:
    """
    Resolve the external base URL for the API service.
    
    Priority order:
    1. EXTERNAL_BASE_URL environment variable (highest priority)
    2. X-Forwarded-* headers when behind reverse proxy
    3. Request URL (scheme + host) when request context exists
    4. Fallback to configured internal base URL
    
    Args:
        request: Optional FastAPI Request object for context
        
    Returns:
        str: Complete base URL (e.g., "https://api.mybot.com" or "http://localhost:8000")
    """
    
    # Priority 1: Explicit environment override
    external_url = os.getenv("EXTERNAL_BASE_URL")
    if external_url:
        return external_url.rstrip('/')
    
    # Priority 2-3: Extract from request context (headers or URL)
    if request:
        base_url = _resolve_from_request(request)
        if base_url:
            return base_url
    
    # Priority 4: Fallback to internal base URL
    internal_url = os.getenv("API_INTERNAL_BASE_URL", "http://localhost:8000")
    return internal_url.rstrip('/')


def _resolve_from_request(request: "Request") -> Optional[str]:
    """
    Resolve base URL from FastAPI request context.
    
    Checks X-Forwarded headers first (reverse proxy), then request.url.
    """
    
    # Check for reverse proxy headers (Nginx, load balancer, etc.)
    forwarded_proto = request.headers.get("x-forwarded-proto")
    forwarded_host = request.headers.get("x-forwarded-host")
    forwarded_port = request.headers.get("x-forwarded-port")
    
    if forwarded_proto and forwarded_host:
        # Build URL from forwarded headers
        port_suffix = ""
        if forwarded_port and forwarded_port not in ("80", "443"):
            port_suffix = f":{forwarded_port}"
        
        return f"{forwarded_proto}://{forwarded_host}{port_suffix}"
    
    # Fallback to request URL components
    if hasattr(request, 'url') and request.url:
        # Extract scheme and netloc from request URL
        url_parts = urlparse(str(request.url))
        if url_parts.scheme and url_parts.netloc:
            return f"{url_parts.scheme}://{url_parts.netloc}"
    
    return None


def get_cors_origins(request: Optional["Request"] = None) -> list[str]:
    """
    Get dynamic CORS allowed origins based on external base URL resolution.
    
    Returns both the resolved base URL and common development origins.
    """
    
    base_url = resolve_external_base_url(request)
    
    # Standard development origins
    dev_origins = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",  # Alternative dev ports
    ]
    
    # Add production origin if different from dev
    origins = dev_origins.copy()
    if base_url not in origins:
        # Add both HTTP and HTTPS variants of the resolved host
        parsed = urlparse(base_url)
        if parsed.netloc:
            http_origin = f"http://{parsed.netloc}"
            https_origin = f"https://{parsed.netloc}"
            
            if http_origin not in origins:
                origins.append(http_origin)
            if https_origin not in origins:
                origins.append(https_origin)
    
    return origins


# Deprecated: For backward compatibility during transition
def get_server_public_ip() -> str:
    """
    DEPRECATED: Use resolve_external_base_url() instead.
    
    This function is maintained for backward compatibility but should not be used
    in new code. It attempts to extract hostname from external base URL.
    """
    import warnings
    warnings.warn(
        "get_server_public_ip() is deprecated. Use resolve_external_base_url() instead.",
        DeprecationWarning,
        stacklevel=2
    )
    
    base_url = resolve_external_base_url()
    parsed = urlparse(base_url)
    return parsed.hostname or "localhost"
