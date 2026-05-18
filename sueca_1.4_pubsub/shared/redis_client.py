import os
from redis import Redis

_redis: Redis | None = None


def get_redis() -> Redis:
    """Get synchronous Redis client (blocking operations)."""
    global _redis
    if _redis is None:
        url = os.getenv("REDIS_URL", "redis://redis:6379/0")
        _redis = Redis.from_url(url, decode_responses=True, socket_connect_timeout=5, socket_keepalive=True)
    return _redis


def revoke_jti(jti: str, ttl_seconds: int) -> None:
    """Mark a jti as revoked for `ttl_seconds` seconds."""
    r = get_redis()
    key = f"revoked_jti:{jti}"
    r.set(key, "1", ex=ttl_seconds)


def is_jti_revoked(jti: str) -> bool:
    """Check if jti is revoked."""
    r = get_redis()
    key = f"revoked_jti:{jti}"
    return r.exists(key) == 1
