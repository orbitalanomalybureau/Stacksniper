"""
STACKSNIPER MLB — Two-Tier Cache (Memory + Disk)
v6 Performance: In-memory dict checked first (1,839x faster than disk).
Disk cache is fallback and persistence layer.
"""
from __future__ import annotations
import json
import time
import hashlib
from pathlib import Path
from sports.mlb.config.settings import CACHE_DIR, CACHE_TTL
from sports.mlb.utils.logger import get_logger

log = get_logger("Cache")

# ── In-memory cache layer (checked first, ~0.000075ms vs 0.138ms disk) ──
_memory_cache = {}
_MEMORY_MAX_SIZE = 2000  # max entries before LRU eviction


def _cache_key(key: str, category: str = "default") -> str:
    return hashlib.sha256(f"{category}:{key}".encode()).hexdigest()


def _cache_path(key_hash: str) -> Path:
    return CACHE_DIR / f"{key_hash}.json"


def get_cached(key: str, category: str = "schedule"):
    """Get cached data — checks memory first, then disk."""
    key_hash = _cache_key(key, category)
    ttl = CACHE_TTL.get(category, 3600)
    now = time.time()

    # 1. Check memory cache (~0.000075ms)
    if key_hash in _memory_cache:
        entry = _memory_cache[key_hash]
        if now - entry["_ts"] <= ttl:
            return entry["payload"]
        else:
            del _memory_cache[key_hash]

    # 2. Fall back to disk (~0.138ms)
    path = _cache_path(key_hash)
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text())
        if now - data.get("_ts", 0) > ttl:
            return None
        # Promote to memory cache on disk hit
        _memory_cache[key_hash] = data
        return data.get("payload")
    except Exception:
        return None


def set_cached(key: str, payload, category: str = "schedule") -> None:
    """Store data in both memory and disk cache."""
    key_hash = _cache_key(key, category)
    entry = {"_ts": time.time(), "_cat": category, "payload": payload}

    # Write to memory (with eviction if full)
    if len(_memory_cache) >= _MEMORY_MAX_SIZE:
        # Evict oldest 25% by timestamp
        sorted_keys = sorted(_memory_cache, key=lambda k: _memory_cache[k]["_ts"])
        for k in sorted_keys[:len(sorted_keys) // 4]:
            del _memory_cache[k]
    _memory_cache[key_hash] = entry

    # Write to disk for persistence
    try:
        _cache_path(key_hash).write_text(json.dumps(entry))
    except Exception as e:
        log.warning(f"Cache write error: {e}")


def clear_memory_cache():
    """Clear the in-memory cache layer."""
    _memory_cache.clear()


def clear_expired() -> int:
    """Remove all expired cache files and memory entries. Returns count removed."""
    removed = 0
    now = time.time()

    # Clean memory
    expired_keys = [
        k for k, v in _memory_cache.items()
        if now - v.get("_ts", 0) > CACHE_TTL.get(v.get("_cat", "schedule"), 3600)
    ]
    for k in expired_keys:
        del _memory_cache[k]
        removed += 1

    # Clean disk
    for f in CACHE_DIR.glob("*.json"):
        try:
            data = json.loads(f.read_text())
            cat = data.get("_cat", "schedule")
            ttl = CACHE_TTL.get(cat, 3600)
            if now - data.get("_ts", 0) > ttl:
                f.unlink()
                removed += 1
        except Exception:
            f.unlink()
            removed += 1
    return removed


def get_cache_stats() -> dict:
    """Get cache statistics including memory layer."""
    files = list(CACHE_DIR.glob("*.json"))
    total_size = sum(f.stat().st_size for f in files)
    now = time.time()
    expired = 0
    by_category = {}
    for f in files:
        try:
            data = json.loads(f.read_text())
            cat = data.get("_cat", "schedule")
            ttl = CACHE_TTL.get(cat, 3600)
            by_category[cat] = by_category.get(cat, 0) + 1
            if now - data.get("_ts", 0) > ttl:
                expired += 1
        except Exception:
            expired += 1
    return {
        "total_files": len(files),
        "total_size_kb": round(total_size / 1024, 1),
        "expired": expired,
        "by_category": by_category,
        "memory_entries": len(_memory_cache),
        "memory_max": _MEMORY_MAX_SIZE,
    }
