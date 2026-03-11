from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from jose import jwt

from app.config import settings


@pytest.mark.asyncio
async def test_security_headers_present(client):
    """All security headers should be present on every response."""
    response = await client.get("/health")
    assert response.headers.get("X-Content-Type-Options") == "nosniff"
    assert response.headers.get("X-Frame-Options") == "DENY"
    assert response.headers.get("X-XSS-Protection") == "1; mode=block"
    assert "max-age=" in response.headers.get("Strict-Transport-Security", "")
    assert response.headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"
    assert "camera=()" in response.headers.get("Permissions-Policy", "")


@pytest.mark.asyncio
async def test_request_id_header(client):
    """Every response should include a unique X-Request-ID."""
    r1 = await client.get("/health")
    r2 = await client.get("/health")
    rid1 = r1.headers.get("X-Request-ID")
    rid2 = r2.headers.get("X-Request-ID")
    assert rid1 is not None
    assert rid2 is not None
    assert rid1 != rid2
    assert len(rid1) == 36  # UUID format


@pytest.mark.asyncio
async def test_jwt_expired_token_rejected(client):
    """An expired JWT should be rejected with 401."""
    expired_token = jwt.encode(
        {"sub": "fake-user-id", "exp": datetime.now(timezone.utc) - timedelta(hours=1), "tier": "free"},
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM,
    )
    response = await client.get("/api/auth/me", headers={"Authorization": f"Bearer {expired_token}"})
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_jwt_invalid_signature_rejected(client):
    """A JWT signed with the wrong key should be rejected."""
    bad_token = jwt.encode(
        {"sub": "fake-user-id", "exp": datetime.now(timezone.utc) + timedelta(hours=1), "tier": "free"},
        "wrong-secret-key",
        algorithm=settings.ALGORITHM,
    )
    response = await client.get("/api/auth/me", headers={"Authorization": f"Bearer {bad_token}"})
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_jwt_missing_sub_claim_rejected(client):
    """A JWT without the required 'sub' claim should be rejected."""
    token_no_sub = jwt.encode(
        {"exp": datetime.now(timezone.utc) + timedelta(hours=1), "tier": "free"},
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM,
    )
    response = await client.get("/api/auth/me", headers={"Authorization": f"Bearer {token_no_sub}"})
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_sql_injection_login(client):
    """SQL injection attempt in email field should fail gracefully."""
    response = await client.post("/api/auth/login", json={
        "email": "' OR 1=1 --",
        "password": "anything",
    })
    # Should be 401 (bad credentials) or 422 (validation), not 500
    assert response.status_code in (401, 422)


@pytest.mark.asyncio
async def test_xss_in_display_name(client):
    """XSS payload in display_name should be stored and returned as plain text."""
    xss_payload = "<script>alert(1)</script>"
    resp = await client.post("/api/auth/register", json={
        "email": "xss@test.com",
        "password": "password123",
        "display_name": xss_payload,
    })
    assert resp.status_code == 201
    token = resp.json()["access_token"]
    me_resp = await client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me_resp.status_code == 200
    # The display name should be stored as-is (JSON API, not HTML rendered)
    assert me_resp.json()["display_name"] == xss_payload


@pytest.mark.asyncio
async def test_health_check_enhanced(client):
    """Enhanced health endpoint returns db_connected, timestamp, uptime."""
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["db_connected"] is True
    assert "timestamp" in data
    assert "uptime_seconds" in data
    assert isinstance(data["uptime_seconds"], (int, float))
