import json
import logging
import time

from core.config import settings

logger = logging.getLogger("redis_client")
_pool = None
_unavailable_until = 0.0


def _get_pool():
    global _pool
    if _pool is not None:
        return _pool
    try:
        import redis as _r
        _pool = _r.ConnectionPool.from_url(
            settings.REDIS_URL,
            decode_responses=True,
            max_connections=20,
            socket_connect_timeout=settings.REDIS_CONNECT_TIMEOUT,
            socket_timeout=settings.REDIS_CONNECT_TIMEOUT,
        )
        return _pool
    except Exception as e:
        logger.warning("Redis pool creation failed: %s", e)
        return None


def get_redis():
    global _unavailable_until
    if not settings.REDIS_ENABLED:
        return None
    if time.monotonic() < _unavailable_until:
        return None
    pool = _get_pool()
    if pool is None:
        return None
    try:
        import redis as _r
        r = _r.Redis(connection_pool=pool)
        r.ping()
        return r
    except Exception as e:
        # Without this circuit breaker, every cache helper waits for a socket
        # timeout when Redis is not running, making one chat reply very slow.
        _unavailable_until = time.monotonic() + settings.REDIS_RETRY_COOLDOWN_SECONDS
        logger.warning("Redis unavailable; retrying in %ss: %s", settings.REDIS_RETRY_COOLDOWN_SECONDS, e)
        return None


def rget(key: str):
    try:
        r = get_redis()
        return r.get(key) if r else None
    except Exception as e:
        logger.warning("Redis GET %s failed: %s", key, e)
        return None


def rset(key: str, value: str, ttl: int = 3600) -> bool:
    try:
        r = get_redis()
        if r:
            r.set(key, value, ex=ttl)
            return True
    except Exception as e:
        logger.warning("Redis SET %s failed: %s", key, e)
    return False


def rdelete(*keys) -> bool:
    try:
        r = get_redis()
        if r:
            r.delete(*keys)
            return True
    except Exception as e:
        logger.warning("Redis DEL failed: %s", e)
    return False


def rjson_get(key: str):
    raw = rget(key)
    if raw is None:
        return None
    try:
        return json.loads(raw)
    except Exception:
        return None


def rjson_set(key: str, data, ttl: int = 3600) -> bool:
    try:
        return rset(key, json.dumps(data, default=str), ttl)
    except Exception as e:
        logger.warning("Redis JSON SET %s failed: %s", key, e)
        return False


def rlist_append(key: str, item: str, max_len: int = 12, ttl: int = 86400):
    try:
        r = get_redis()
        if r:
            pipe = r.pipeline()
            pipe.rpush(key, item)
            pipe.ltrim(key, -max_len, -1)
            pipe.expire(key, ttl)
            pipe.execute()
    except Exception as e:
        logger.warning("Redis RPUSH %s failed: %s", key, e)


def rlist_get(key: str) -> list:
    try:
        r = get_redis()
        if r:
            return r.lrange(key, 0, -1)
    except Exception as e:
        logger.warning("Redis LRANGE %s failed: %s", key, e)
    return []
