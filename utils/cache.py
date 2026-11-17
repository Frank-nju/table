"""Cache utilities.
Provides a simple in-memory cache."""

import threading
from datetime import datetime, timedelta
from functools import wraps

# Thread-safe global cache
_cache = {}
_cache_lock = threading.Lock()


def cached_build(cache_key, ttl_seconds, builder_func, *args):
    """Build a value with caching.

Args:
    cache_key: Cache key.
    ttl_seconds: Cache lifetime in seconds.
    builder_func: Function used to build the value.
    *args: Arguments passed to the builder.

Returns:
    The cached value or a newly built value."""
    full_key = (cache_key, args)

    now = datetime.now()
    with _cache_lock:
        if full_key in _cache:
            cached_data, cached_time = _cache[full_key]
            if now - cached_time < timedelta(seconds=ttl_seconds):
                return cached_data

    # rebuild（run outside the lock，to avoid blocking）
    result = builder_func()
    with _cache_lock:
        _cache[full_key] = (result, now)
    return result


def clear_cache(cache_key=None):
    """Clear cached values.

Args:
    cache_key: Cache key to clear; None clears the entire cache."""
    global _cache
    with _cache_lock:
        if cache_key is None:
            _cache = {}
        else:
            keys_to_remove = [k for k in _cache if k[0] == cache_key]
            for k in keys_to_remove:
                del _cache[k]


def cache_decorator(ttl_seconds=300):
    """
    cachedecorator

    Usage:
        @cache_decorator(ttl_seconds=60)
        def expensive_function():
            ...
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            cache_key = (func.__name__, args, tuple(sorted(kwargs.items())))
            now = datetime.now()

            with _cache_lock:
                if cache_key in _cache:
                    cached_data, cached_time = _cache[cache_key]
                    if now - cached_time < timedelta(seconds=ttl_seconds):
                        return cached_data

            result = func(*args, **kwargs)
            with _cache_lock:
                _cache[cache_key] = (result, now)
            return result
        return wrapper
    return decorator