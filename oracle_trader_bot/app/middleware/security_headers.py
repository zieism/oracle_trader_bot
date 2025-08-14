"""
Security Headers Middleware for Oracle Trader Bot.

Adds configurable security headers to all HTTP responses:
- X-Content-Type-Options: nosniff
- X-Frame-Options: DENY
- Referrer-Policy: no-referrer
- Strict-Transport-Security: max-age=15552000 (HTTPS only)
- Content-Security-Policy: default-src 'self' (optional)

Configuration is controlled via environment variables/settings.
"""

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from typing import Callable
import logging

from app.core.config import settings

logger = logging.getLogger(__name__)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Middleware that adds security headers to HTTP responses.
    
    Headers are configurable via settings and only added when enabled.
    The Strict-Transport-Security header is only added for HTTPS requests.
    """

    def __init__(self, app, dispatch: Callable = None):
        super().__init__(app, dispatch)
        self._log_configuration()

    def _log_configuration(self):
        """Log the current security headers configuration on startup."""
        enabled_headers = []
        
        if settings.SECURITY_HEADERS_X_CONTENT_TYPE_OPTIONS:
            enabled_headers.append("X-Content-Type-Options")
        if settings.SECURITY_HEADERS_X_FRAME_OPTIONS:
            enabled_headers.append("X-Frame-Options")
        if settings.SECURITY_HEADERS_REFERRER_POLICY:
            enabled_headers.append("Referrer-Policy")
        if settings.SECURITY_HEADERS_STRICT_TRANSPORT_SECURITY:
            enabled_headers.append("Strict-Transport-Security (HTTPS only)")
        if settings.SECURITY_HEADERS_CONTENT_SECURITY_POLICY:
            enabled_headers.append("Content-Security-Policy")

        if enabled_headers:
            logger.info(f"Security headers middleware enabled: {', '.join(enabled_headers)}")
        else:
            logger.info("Security headers middleware loaded but all headers disabled")

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process the request and add security headers to the response.
        
        Args:
            request: The incoming HTTP request
            call_next: The next middleware or endpoint handler
            
        Returns:
            Response with security headers added (if enabled)
        """
        # Process the request
        response = await call_next(request)
        
        # Add security headers based on configuration
        self._add_security_headers(request, response)
        
        return response

    def _add_security_headers(self, request: Request, response: Response) -> None:
        """
        Add security headers to the response based on settings.
        
        Args:
            request: The HTTP request (used to check for HTTPS)
            response: The HTTP response to add headers to
        """
        # X-Content-Type-Options: nosniff
        if settings.SECURITY_HEADERS_X_CONTENT_TYPE_OPTIONS:
            response.headers["X-Content-Type-Options"] = "nosniff"

        # X-Frame-Options: DENY
        if settings.SECURITY_HEADERS_X_FRAME_OPTIONS:
            response.headers["X-Frame-Options"] = "DENY"

        # Referrer-Policy: no-referrer
        if settings.SECURITY_HEADERS_REFERRER_POLICY:
            response.headers["Referrer-Policy"] = "no-referrer"

        # Strict-Transport-Security: max-age=15552000 (HTTPS only)
        if settings.SECURITY_HEADERS_STRICT_TRANSPORT_SECURITY and self._is_https_request(request):
            response.headers["Strict-Transport-Security"] = "max-age=15552000"

        # Content-Security-Policy: default-src 'self' (optional)
        if settings.SECURITY_HEADERS_CONTENT_SECURITY_POLICY:
            response.headers["Content-Security-Policy"] = "default-src 'self'"

    def _is_https_request(self, request: Request) -> bool:
        """
        Check if the request was made over HTTPS.
        
        This checks multiple sources:
        1. The URL scheme (request.url.scheme)
        2. The X-Forwarded-Proto header (for reverse proxies)
        3. The X-Forwarded-Protocol header (alternative)
        
        Args:
            request: The HTTP request
            
        Returns:
            True if the request is HTTPS, False otherwise
        """
        # Check the URL scheme directly
        if request.url.scheme == "https":
            return True
            
        # Check forwarded protocol headers (for reverse proxies)
        forwarded_proto = request.headers.get("x-forwarded-proto", "").lower()
        if forwarded_proto == "https":
            return True
            
        # Check alternative forwarded protocol header
        forwarded_protocol = request.headers.get("x-forwarded-protocol", "").lower()
        if forwarded_protocol == "https":
            return True
            
        return False


def create_security_headers_middleware():
    """
    Factory function to create the security headers middleware.
    
    This function can be used to add the middleware to the FastAPI app.
    
    Returns:
        SecurityHeadersMiddleware class ready to be added to app
    """
    return SecurityHeadersMiddleware
