import logging
import time

import redis.asyncio as aioredis
from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.config import settings

logger = logging.getLogger("app.rate_limit")


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Middleware enforcing sliding-window IP rate limiting on chat endpoints via Redis."""

    def __init__(
        self,
        app,
        redis_url: str = settings.REDIS_URL,
        max_requests: int = 45,
        window_seconds: int = 60,
    ):
        super().__init__(app)
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.redis_client: aioredis.Redis | None = None
        try:
            self.redis_client = aioredis.from_url(redis_url, decode_responses=True)
        except Exception as e:
            logger.warning(f"Redis connection failed. Rate limiting is disabled: {e}")
            self.redis_client = None

    async def close(self):
        """Close connection to Redis client."""
        if self.redis_client:
            await self.redis_client.close()

    async def dispatch(self, request: Request, call_next):
        # Apply rate limiting specifically to the chat endpoint
        if request.url.path in ("/api/chat", "/api/chat/"):
            client_ip = request.client.host if request.client else "unknown"

            if self.redis_client:
                key = f"rate_limit:{client_ip}"
                now = time.time()
                window_start = now - self.window_seconds

                try:
                    pipe = self.redis_client.pipeline()
                    pipe.zremrangebyscore(key, 0, window_start)
                    pipe.zadd(key, {str(now): now})
                    pipe.zcard(key)
                    pipe.expire(key, self.window_seconds)
                    results = await pipe.execute()
                    request_count = results[2]

                    if request_count > self.max_requests:
                        return JSONResponse(
                            status_code=429,
                            content={
                                "detail": "Terlalu banyak mengirim pesan. Silakan tunggu 1 menit ya, Bu!"
                            },
                        )
                except Exception as e:
                    # Fail-open if Redis encounters errors
                    logger.error(f"Redis rate limiter failed (failing open): {e}")

        response = await call_next(request)
        return response
