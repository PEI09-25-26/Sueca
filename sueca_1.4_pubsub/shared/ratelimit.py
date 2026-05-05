import os
from fastapi import Request, HTTPException
from redis.asyncio import Redis

_redis: Redis | None = None


def _get_redis() -> Redis:
    global _redis
    if _redis is None:
        url = os.getenv("REDIS_URL", "redis://redis:6379/0")
        _redis = Redis.from_url(url, decode_responses=True)
    return _redis


def rate_limit_dependency(limit: int = 60, window_seconds: int = 60):
    async def _dep(request: Request):
        redis = _get_redis()
        ip = (request.client.host or "unknown")
        route = request.url.path
        key = f"ratelimit:{route}:{ip}"
        try:
            count = await redis.incr(key)
            if count == 1:
                await redis.expire(key, window_seconds)
            if count > limit:
                ttl = await redis.ttl(key)
                raise HTTPException(status_code=429, detail=f"rate limit exceeded, retry in {ttl}s")
        except Exception as e:
            # On Redis failure, allow requests but log to stdout
            print(f"[ratelimit] Redis error: {e}")
            return

    return _dep
