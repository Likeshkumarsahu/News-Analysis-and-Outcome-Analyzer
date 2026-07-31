import os
import json
import hashlib
import redis

REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
CACHE_TTL  = int(os.getenv("CACHE_TTL_SECONDS", 3600))  # 1 hour default

_client = None
_available = None


def _get_client():
    global _client, _available
    if _client is None:
        try:
            _client = redis.Redis(
                host=REDIS_HOST, port=REDIS_PORT, db=0,
                decode_responses=True, socket_connect_timeout=2,
            )
            _client.ping()
            _available = True
        except Exception as e:
            print(f"  Redis unavailable, caching disabled: {e}")
            _available = False
    return _client if _available else None


def _make_key(query: str, provider: str, groq_model: str = None) -> str:
    raw = f"{query.strip().lower()}|{provider}|{groq_model or ''}"
    return "newsana:analyze:" + hashlib.md5(raw.encode()).hexdigest()


def get_cached(query: str, provider: str, groq_model: str = None) -> dict | None:
    """Return cached analyze result, or None if not cached / Redis unavailable."""
    client = _get_client()
    if not client:
        return None
    try:
        key = _make_key(query, provider, groq_model)
        raw = client.get(key)
        return json.loads(raw) if raw else None
    except Exception as e:
        print(f"  Redis read error: {e}")
        return None


def set_cached(query: str, provider: str, result: dict, groq_model: str = None) -> None:
    """Store analyze result in cache with TTL."""
    client = _get_client()
    if not client:
        return
    try:
        key = _make_key(query, provider, groq_model)
        client.setex(key, CACHE_TTL, json.dumps(result))
    except Exception as e:
        print(f"  Redis write error: {e}")


def clear_cache() -> int:
    """Clear all Newsana cache keys. Returns count deleted."""
    client = _get_client()
    if not client:
        return 0
    keys = client.keys("newsana:analyze:*")
    if keys:
        client.delete(*keys)
    return len(keys)


def cache_status() -> dict:
    client = _get_client()
    if not client:
        return {"available": False}
    try:
        keys = client.keys("newsana:analyze:*")
        return {"available": True, "cached_queries": len(keys)}
    except Exception:
        return {"available": False}
        