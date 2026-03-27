"""
Security Headers Middleware
============================
Injects hardened HTTP security headers into every response from the ML Gateway.
"""

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Adds industry-standard security response headers to every outgoing response.
    """

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)

        # Prevent MIME-type sniffing attacks
        response.headers["X-Content-Type-Options"] = "nosniff"

        # Prevent clickjacking via iframe embedding
        response.headers["X-Frame-Options"] = "DENY"

        # Enforce HTTPS for 1 year (browsers will auto-upgrade HTTP → HTTPS)
        response.headers["Strict-Transport-Security"] = (
            "max-age=31536000; includeSubDomains; preload"
        )

        # Prevent caching of sensitive inference results
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"
        response.headers["Pragma"] = "no-cache"

        # Block cross-site scripting reflection
        response.headers["X-XSS-Protection"] = "1; mode=block"

        # Restrict referrer leakage
        response.headers["Referrer-Policy"] = "no-referrer"

        return response
