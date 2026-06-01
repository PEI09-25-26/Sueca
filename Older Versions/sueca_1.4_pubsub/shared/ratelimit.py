import os
from fastapi import Request, HTTPException
import hashlib
from redis import Redis
import time
import threading

_redis: Redis | None = None


def _get_redis() -> Redis:
    global _redis
    if _redis is None:
        url = os.getenv("REDIS_URL", "redis://redis:6379/0")
        _redis = Redis.from_url(url, decode_responses=True, socket_connect_timeout=5, socket_keepalive=True)
    return _redis


def rate_limit_dependency(limit: int = 60, window_seconds: int = 60):
    async def _dep(request: Request):
        # Try Redis first; fall back to an in-memory token bucket if Redis is unavailable.
        try:
            redis = _get_redis()
            use_redis = True
        except Exception as e:
            redis = None
            use_redis = False
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
        if use_redis and redis is not None:
            try:
                count = redis.incr(key)
                if count == 1:
                    redis.expire(key, window_seconds)
                if count > limit:
                    ttl = redis.ttl(key)
                    raise HTTPException(status_code=429, detail=f"rate limit exceeded, retry in {ttl}s")
                return
            except HTTPException:
                raise
            except Exception as e:
                # Fall through to in-memory fallback
                print(f"[ratelimit] Redis error, falling back to in-memory limiter: {e}")

        # In-memory fallback: simple fixed-window counter per key.
        # Lightweight and best-effort; protected by a small lock.
        if not hasattr(rate_limit_dependency, "_mem_counters"):
            rate_limit_dependency._mem_counters = {}
            rate_limit_dependency._mem_lock = threading.Lock()

        now = int(time.time())
        window = now // window_seconds
        mem_key = f"{key}:{window}"
        with rate_limit_dependency._mem_lock:
            cnt = rate_limit_dependency._mem_counters.get(mem_key, 0) + 1
            rate_limit_dependency._mem_counters[mem_key] = cnt
            # Clean up old windows occasionally
            if len(rate_limit_dependency._mem_counters) > 10000:
                # remove entries older than two windows
                cutoff = (now // window_seconds) - 2
                keys_to_delete = [k for k in rate_limit_dependency._mem_counters.keys() if int(k.rsplit(':', 1)[-1]) < cutoff]
                for k in keys_to_delete:
                    del rate_limit_dependency._mem_counters[k]

        if cnt > limit:
            raise HTTPException(status_code=429, detail="rate limit exceeded (fallback)")
        return

    return _dep
