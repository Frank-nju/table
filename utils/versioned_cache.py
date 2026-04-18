"""
版本感知缓存模块

提供带数据版本号的全局缓存，写入操作通过 touch_version() 使缓存失效。
app.py 和 services/ 层共用此缓存。
"""

import threading
import time

_cache = {}
_cache_lock = threading.Lock()
_data_version = 0


def get_version():
    """获取当前数据版本号"""
    with _cache_lock:
        return _data_version


def touch_version():
    """递增版本号，使所有缓存失效"""
    global _data_version
    with _cache_lock:
        _data_version += 1


def cached_build(namespace, ttl_seconds, build_fn, *parts):
    """
    带版本号的缓存构建函数。

    缓存键包含当前版本号，写入时调用 touch_version() 递增版本号，
    旧的缓存键不再匹配，自然失效。
    """
    version = get_version()
    cache_key = (namespace, version, parts)
    now_ts = time.time()

    with _cache_lock:
        cached = _cache.get(cache_key)
        if cached and cached['expires_at'] > now_ts:
            return cached['value']

    # 在锁外执行构建，避免阻塞
    value = build_fn()

    with _cache_lock:
        _cache[cache_key] = {
            'value': value,
            'expires_at': now_ts + max(1, ttl_seconds),
        }
    return value


def clear_all():
    """清除所有缓存（用于测试）"""
    with _cache_lock:
        _cache.clear()
