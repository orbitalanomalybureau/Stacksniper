"""STACKSNIPER MLB — Tier Gating & Feature Limits"""
from functools import wraps
from flask import jsonify
from sports.mlb.utils.auth import get_current_user

TIER_LEVELS = {"free": 0, "pro": 1, "elite": 2}

TIER_LIMITS = {
    "simulate": {"free": 100, "pro": 2000, "elite": 10000},
    "copilot_daily": {"free": 0, "pro": 5, "elite": 999},
}


def require_tier(min_tier):
    """Decorator that enforces a minimum subscription tier."""
    def decorator(f):
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
            user_level = TIER_LEVELS.get(user.get("tier", "free"), 0)
            required_level = TIER_LEVELS.get(min_tier, 0)
            if user_level < required_level:
                return jsonify({
                    "error": {
                        "code": "TIER_REQUIRED",
                        "message": f"This feature requires {min_tier} tier.",
                        "required_tier": min_tier,
                        "current_tier": user.get("tier", "free"),
                        "upgrade_url": "/pricing",
                    }
                }), 403
            return f(*args, **kwargs)
        return decorated
    return decorator


def get_sim_limit(user):
    """Return the simulation count limit for the user's tier."""
    tier = user.get("tier", "free") if user else "free"
    return TIER_LIMITS["simulate"].get(tier, 100)
