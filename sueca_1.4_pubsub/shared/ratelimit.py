import os
from fastapi import Request, HTTPException
import hashlib
from redis import Redis

_redis: Redis | None = None


def _get_redis() -> Redis:
    global _redis
    if _redis is None:
        url = os.getenv("REDIS_URL", "redis://redis:6379/0")
        _redis = Redis.from_url(url, decode_responses=True, socket_connect_timeout=5, socket_keepalive=True)
    return _redis


def rate_limit_dependency(limit: int = 60, window_seconds: int = 60):
    async def _dep(request: Request):
        redis = _get_redis()
        # Prefer trusted forwarding headers when present (gateway/proxy).
        xff = request.headers.get("x-forwarded-for")
        if xff:
            # X-Forwarded-For may contain a comma-separated list; use first entry
            ip = xff.split(",")[0].strip()
        else:
            ip = (request.client.host or "unknown")
        route = request.url.path
        # Incorporate a stable hash of the Authorization token when present so
        # rate limits can be distinguished per-actor even behind a shared IP.
        auth = request.headers.get("authorization", "")
        user_suffix = ""
        if auth.startswith("Bearer "):
            token = auth[7:].strip()
            if token:
                user_suffix = hashlib.sha256(token.encode()).hexdigest()[:8]

        key = f"ratelimit:{route}:{ip}:{user_suffix}"
        try:
            count = redis.incr(key)
            if count == 1:
                redis.expire(key, window_seconds)
            if count > limit:
                ttl = redis.ttl(key)
                raise HTTPException(status_code=429, detail=f"rate limit exceeded, retry in {ttl}s")
        except HTTPException:
            raise
        except Exception as e:
            # On Redis failure, allow requests but log to stdout
            print(f"[ratelimit] Redis error: {e}")
            return

    return _dep
