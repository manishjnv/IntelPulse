"""Rate limiting middleware using Redis."""

from __future__ import annotations

import time
from typing import Callable

from fastapi import HTTPException, Request, Response, status
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.logging import get_logger
from app.core.redis import redis_client

logger = get_logger(__name__)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Rate limiting middleware with Redis backend.
    
    Implements sliding window rate limiting per IP address.
    """

    def __init__(self, app, calls: int = 100, period: int = 60):
        """Initialize rate limiter.
        
        Args:
            app: FastAPI application
            calls: Number of calls allowed per period
            period: Time period in seconds
        """
        super().__init__(app)
        self.calls = calls
        self.period = period

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Check rate limit before processing request."""
        # Skip rate limiting for health checks
        if request.url.path in ("/api/v1/health", "/health"):
            return await call_next(request)

        # Get client IP
        client_ip = request.client.host if request.client else "unknown"
        
        # Special rate limits for auth endpoints
        if request.url.path.startswith("/api/v1/auth/"):
            if request.url.path == "/api/v1/auth/otp/send":
                # Strict limit for OTP sending (3 per minute)
                allowed = await self._check_limit(f"ratelimit:otp_send:{client_ip}", 3, 60)
            elif request.url.path == "/api/v1/auth/otp/verify":
                # Strict limit for OTP verification (5 per minute)
                allowed = await self._check_limit(f"ratelimit:otp_verify:{client_ip}", 5, 60)
            elif request.url.path == "/api/v1/auth/google/callback":
                # Moderate limit for OAuth callbacks (10 per minute)
                allowed = await self._check_limit(f"ratelimit:oauth:{client_ip}", 10, 60)
            else:
                # General auth endpoint limit
                allowed = await self._check_limit(f"ratelimit:auth:{client_ip}", 20, 60)
        else:
            # General API rate limit
            allowed = await self._check_limit(f"ratelimit:api:{client_ip}", self.calls, self.period)

        if not allowed:
            logger.warning("rate_limit_exceeded", ip=client_ip, path=request.url.path)
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded. Please try again later.",
                headers={"Retry-After": str(self.period)},
            )

        response = await call_next(request)
        return response

    async def _check_limit(self, key: str, calls: int, period: int) -> bool:
        """Check if request is within rate limit using sliding window.
        
        Args:
            key: Redis key for this rate limit
            calls: Number of calls allowed
            period: Time period in seconds
            
        Returns:
            True if request is allowed, False if rate limit exceeded
        """
        try:
            now = time.time()
            window_start = now - period

            # Use Redis sorted set for sliding window
            pipe = redis_client.pipeline()
            
            # Remove old entries
            pipe.zremrangebyscore(key, 0, window_start)
            
            # Count current entries
            pipe.zcard(key)
            
            # Add current request
            pipe.zadd(key, {str(now): now})
            
            # Set expiry
            pipe.expire(key, period + 1)
            
            results = await pipe.execute()
            current_count = results[1]  # Result of zcard
            
            return current_count < calls
            
        except Exception as e:
            logger.error("rate_limit_check_error", error=str(e))
            # Fail open - allow request if Redis is down
            return True
