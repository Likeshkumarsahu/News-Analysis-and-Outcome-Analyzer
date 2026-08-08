"""
cache/api_cache.py
====================
Caches raw connector responses (GDELT / NewsAPI / future sources) so
repeated ingestion runs over the same query+date-range don't re-hit rate
-limited external APIs. Separate keyspace from cache/redis_cache.py,
which caches LLM /api/analyze results — same graceful-degrade pattern
(ingestion keeps working with caching effectively disabled if Redis
isn't reachable).
"""

import hashlib
import json
import os

import redis

REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
API_CACHE_TTL = int(os.getenv("API_CACHE_TTL_SECONDS", 21600))  # 6 hours default

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
            print(f"  Redis unavailable, API caching disabled: {e}")
            _available = False
    return _client if _available else None


def _make_key(connector: str, query: str, start_date: str, end_date: str, extra: str = "") -> str:
    raw = f"{connector}|{query.strip().lower()}|{start_date}|{end_date}|{extra}"
    return "newsana:api_cache:" + hashlib.md5(raw.encode()).hexdigest()


def get_cached_response(connector: str, query: str, start_date: str, end_date: str,
                         extra: str = "") -> list | None:
    """Returns a cached list of raw article dicts, or None on miss / Redis unavailable."""
    client = _get_client()
    if not client:
        return None
    try:
        raw = client.get(_make_key(connector, query, start_date, end_date, extra))
        return json.loads(raw) if raw else None
    except Exception as e:
        print(f"  API cache read error: {e}")
        return None


def set_cached_response(connector: str, query: str, start_date: str, end_date: str,
                         articles: list, extra: str = "") -> None:
    """Stores a list of raw article dicts (JSON-serializable) with TTL."""
    client = _get_client()
    if not client:
        return
    try:
        key = _make_key(connector, query, start_date, end_date, extra)
        client.setex(key, API_CACHE_TTL, json.dumps(articles))
    except Exception as e:
        print(f"  API cache write error: {e}")


def clear_api_cache() -> int:
    """Clear all cached API responses. Returns count deleted."""
    client = _get_client()
    if not client:
        return 0
    keys = client.keys("newsana:api_cache:*")
    if keys:
        client.delete(*keys)
    return len(keys)