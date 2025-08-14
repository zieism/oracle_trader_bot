# app/security/admin_auth.py
"""
Optional Admin Authentication Guard

Provides optional token-based authentication for sensitive admin endpoints.
When ADMIN_API_TOKEN is not set, all endpoints remain accessible (backward compatibility).
When set, requires X-Admin-Token header for protected endpoints.
"""

import os
import logging
from typing import Optional
from fastapi import HTTPException, Request, status
from fastapi.security import HTTPBearer
from fastapi.security.utils import get_authorization_scheme_param

logger = logging.getLogger(__name__)

class AdminAuthGuard:
    """
    Optional admin authentication guard.
    
    Behavior:
    - If ADMIN_API_TOKEN is empty/unset: No authentication required (backward compatible)
    - If ADMIN_API_TOKEN is set: Requires X-Admin-Token header with matching value
    """
    
    def __init__(self):
        self.admin_token = os.getenv("ADMIN_API_TOKEN", "").strip()
        self.is_enabled = bool(self.admin_token)
        
        if self.is_enabled:
            logger.info("Admin authentication guard is ENABLED - protected endpoints require X-Admin-Token header")
        else:
            logger.info("Admin authentication guard is DISABLED - protected endpoints remain open")
    
    def _extract_token_from_header(self, request: Request) -> Optional[str]:
        """Extract token from X-Admin-Token header"""
        return request.headers.get("X-Admin-Token", "").strip()
    
    def _log_auth_attempt(self, request: Request, success: bool, reason: str = ""):
        """Log authentication attempts (without exposing token values)"""
        client_ip = "unknown"
        if request.client:
            client_ip = request.client.host
        elif "x-forwarded-for" in request.headers:
            client_ip = request.headers["x-forwarded-for"].split(",")[0].strip()
        elif "x-real-ip" in request.headers:
            client_ip = request.headers["x-real-ip"]
            
        user_agent = request.headers.get("user-agent", "unknown")[:100]  # Truncate long user agents
        
        if success:
            logger.info(f"Admin auth SUCCESS - IP: {client_ip}, UA: {user_agent}")
        else:
            logger.warning(f"Admin auth FAILED - IP: {client_ip}, UA: {user_agent}, Reason: {reason}")
    
    def verify_admin_token(self, request: Request) -> None:
        """
        Verify admin token if authentication is enabled.
        
        Args:
            request: FastAPI request object
            
        Raises:
            HTTPException: 401 if authentication fails when enabled
        """
        # If admin auth is not enabled, allow all requests
        if not self.is_enabled:
            return
            
        # Extract token from header
        provided_token = self._extract_token_from_header(request)
        
        # Check if token is provided
        if not provided_token:
            self._log_auth_attempt(request, success=False, reason="missing_token")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"ok": False, "reason": "unauthorized"}
            )
        
        # Verify token matches
        if provided_token != self.admin_token:
            self._log_auth_attempt(request, success=False, reason="invalid_token")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"ok": False, "reason": "unauthorized"}
            )
        
        # Token is valid
        self._log_auth_attempt(request, success=True)

# Global admin auth guard instance
admin_auth = AdminAuthGuard()
