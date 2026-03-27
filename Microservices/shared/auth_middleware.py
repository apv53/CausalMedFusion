"""
API Key Authentication Middleware
==================================
Validates the X-API-Key header on every incoming request to the ML Gateway.
Only requests bearing the correct pre-shared secret are processed.
The /health and /docs endpoints are exempted for monitoring and dev use.
"""

import os
from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

# Paths that do NOT require authentication
EXEMPT_PATHS = {"/health", "/docs", "/openapi.json", "/redoc"}

ML_GATEWAY_API_KEY = os.getenv("ML_GATEWAY_API_KEY", "")

# Optional IP whitelist (comma-separated).  Leave blank to disable (API key
# auth still enforced).  Default is blank so Docker bridge IPs are accepted.
_raw_ips = os.getenv("ALLOWED_CALLER_IPS", "").strip()
ALLOWED_CALLER_IPS = [ip.strip() for ip in _raw_ips.split(",") if ip.strip()] if _raw_ips else []


class APIKeyAuthMiddleware(BaseHTTPMiddleware):
    """
    Starlette middleware that enforces:
      1. A valid X-API-Key header matching the server secret.
      2. (Optional) Caller IP is in the whitelist.
    """

    async def dispatch(self, request: Request, call_next):
        path = request.url.path

        # Skip auth for health/docs endpoints
        if path in EXEMPT_PATHS:
            return await call_next(request)

        # ── Check 1: API Key ────────────────────────────────────────
        if not ML_GATEWAY_API_KEY:
            # If no key is configured, reject everything (fail-closed)
            return JSONResponse(
                status_code=500,
                content={"detail": "ML_GATEWAY_API_KEY is not configured on the server."},
            )

        request_key = request.headers.get("X-API-Key", "")
        if request_key != ML_GATEWAY_API_KEY:
            return JSONResponse(
                status_code=401,
                content={"detail": "Unauthorized: invalid or missing X-API-Key."},
            )

        # ── Check 2: IP Whitelist ───────────────────────────────────
        client_ip = request.client.host if request.client else None
        if ALLOWED_CALLER_IPS and client_ip not in ALLOWED_CALLER_IPS:
            return JSONResponse(
                status_code=403,
                content={"detail": f"Forbidden: caller IP {client_ip} is not whitelisted."},
            )

        return await call_next(request)
