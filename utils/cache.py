"""
缓存工具模块

提供简单的内存缓存功能
"""

import threading
from datetime import datetime, timedelta
from functools import wraps

# 全局缓存存储（线程安全）
_cache = {}
_cache_lock = threading.Lock()


def cached_build(cache_key, ttl_seconds, builder_func, *args):
    """
    带缓存的构建函数

    Args:
        cache_key: 缓存键
        ttl_seconds: 缓存过期时间（秒）
        builder_func: 构建函数
        *args: 传递给构建函数的参数

    Returns:
        构建函数的结果（从缓存或重新构建）
    """
    full_key = (cache_key, args)

    now = datetime.now()
    with _cache_lock:
        if full_key in _cache:
            cached_data, cached_time = _cache[full_key]
            if now - cached_time < timedelta(seconds=ttl_seconds):
                return cached_data

    # 重新构建（在锁外执行，避免阻塞）
    result = builder_func()
    with _cache_lock:
        _cache[full_key] = (result, now)
    return result


def clear_cache(cache_key=None):
    """
    清除缓存

    Args:
        cache_key: 要清除的缓存键，None 表示清除所有
    """
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
    缓存装饰器

    用法:
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