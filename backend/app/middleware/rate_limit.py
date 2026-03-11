from __future__ import annotations

from fastapi import Request
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.services.auth_service import AuthService


def _get_rate_limit_key(request: Request) -> str:
    auth_header = request.headers.get("authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header[7:]
        payload = AuthService.verify_token(token)
        if payload and payload.get("sub"):
            return payload["sub"]
    return get_remote_address(request)


limiter = Limiter(key_func=_get_rate_limit_key, default_limits=["10/minute"])

TIER_LIMITS = {
    "free": "10/minute",
    "pro": "60/minute",
    "elite": "200/minute",
}
