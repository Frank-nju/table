"""Version-aware cache.
Provides a global cache keyed by the current data version. Call touch_version() after writes to invalidate cached values.
This cache is shared by app.py and the services layer."""

import threading
import time

_cache = {}
_cache_lock = threading.Lock()
_data_version = 0


def get_version():
    """Get the current data version."""
    with _cache_lock:
        return _data_version


def touch_version():
    """Increment the version to invalidate all cached values."""
    global _data_version
    with _cache_lock:
        _data_version += 1


def cached_build(namespace, ttl_seconds, build_fn, *parts):
    """Build and cache a value using the current version.

The cache key includes the current data version. Calling touch_version() after a write changes the key, so old entries expire naturally."""
    version = get_version()
    cache_key = (namespace, version, parts)
    now_ts = time.time()

    with _cache_lock:
        cached = _cache.get(cache_key)
        if cached and cached['expires_at'] > now_ts:
            return cached['value']

    # run outside the lockbuild，to avoid blocking
    value = build_fn()

    with _cache_lock:
        _cache[cache_key] = {
            'value': value,
            'expires_at': now_ts + max(1, ttl_seconds),
        }
    return value


def clear_all():
    """Clear all cached values (for tests)."""
    with _cache_lock:
        _cache.clear()
