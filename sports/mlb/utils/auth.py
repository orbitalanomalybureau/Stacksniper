"""STACKSNIPER MLB — Authentication (bcrypt + JWT)"""
import os
import datetime
from functools import wraps

import bcrypt
import jwt
from flask import request, jsonify, g

from sports.mlb.data.database import db
from sports.mlb.utils.logger import get_logger

log = get_logger("Auth")

JWT_SECRET = os.getenv("JWT_SECRET", "change-me-to-a-random-string")
JWT_ALGORITHM = "HS256"
JWT_EXPIRY_DAYS = 7


# ── Password helpers ─────────────────────────────────────────────────

def _hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def _check_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))


# ── Token helpers ────────────────────────────────────────────────────

def _create_token(user_id: int, email: str) -> str:
    payload = {
        "sub": user_id,
        "email": email,
        "iat": datetime.datetime.utcnow(),
        "exp": datetime.datetime.utcnow() + datetime.timedelta(days=JWT_EXPIRY_DAYS),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def verify_token(token: str) :
    """Decode and verify a JWT. Returns the payload dict or None on failure."""
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        log.debug("Token expired")
        return None
    except jwt.InvalidTokenError as exc:
        log.debug(f"Invalid token: {exc}")
        return None


# ── Public API ───────────────────────────────────────────────────────

def register_user(email: str, password: str) -> dict:
    """Register a new user. Returns ``{"user": …, "token": …}`` or ``{"error": …}``."""
    email = email.strip().lower()
    if not email or "@" not in email:
        return {"error": "Invalid email address."}
    if len(password) < 8:
        return {"error": "Password must be at least 8 characters."}

    existing = db.get_user_by_email(email)
    if existing:
        return {"error": "Email already registered."}

    password_hash = _hash_password(password)
    user = db.create_user(email, password_hash)
    if not user:
        return {"error": "Failed to create user."}

    token = _create_token(user["id"], user["email"])
    log.info(f"User registered: {email}")
    return {"user": _safe_user(user), "token": token}


def login_user(email: str, password: str) -> dict:
    """Authenticate a user. Returns ``{"user": …, "token": …}`` or ``{"error": …}``."""
    email = email.strip().lower()
    user = db.get_user_by_email(email)
    if not user:
        return {"error": "Invalid email or password."}

    if not _check_password(password, user["password_hash"]):
        return {"error": "Invalid email or password."}

    # Update last_login
    db.update_user(user["id"], last_login=datetime.datetime.utcnow().isoformat())

    token = _create_token(user["id"], user["email"])
    log.info(f"User logged in: {email}")
    return {"user": _safe_user(user), "token": token}


def get_current_user() :
    """Read the JWT from the Authorization: Bearer header and return the user dict, or None."""
    # Cache on Flask g for the duration of the request
    if hasattr(g, "_current_user"):
        return g._current_user

    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        g._current_user = None
        return None

    token = auth_header[7:]
    payload = verify_token(token)
    if not payload:
        g._current_user = None
        return None

    user = db.get_user_by_id(payload["sub"])
    g._current_user = user
    return user


# ── Decorator ────────────────────────────────────────────────────────

def require_login(f):
    """Decorator that enforces JWT authentication. Returns 401 if invalid."""
    @wraps(f)
    def decorated(*args, **kwargs):
        user = get_current_user()
        if not user:
            return jsonify({
                "error": {
                    "code": "AUTH_REQUIRED",
                    "message": "Please log in.",
                    "upgrade_url": "/pricing",
                }
            }), 401
        return f(*args, **kwargs)
    return decorated


# ── Helpers ──────────────────────────────────────────────────────────

def _safe_user(user: dict) -> dict:
    """Strip sensitive fields before sending to client."""
    return {
        "id": user["id"],
        "email": user["email"],
        "tier": user.get("tier", "free"),
        "subscription_status": user.get("subscription_status", "none"),
        "referral_code": user.get("referral_code"),
        "onboarding_complete": user.get("onboarding_complete", 0),
        "consecutive_days": user.get("consecutive_days", 0),
        "total_sims": user.get("total_sims", 0),
        "lineups_generated": user.get("lineups_generated", 0),
        "ai_chats": user.get("ai_chats", 0),
        "created_at": user.get("created_at"),
        "last_login": user.get("last_login"),
    }
