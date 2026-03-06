"""Rate limiting configuration using slowapi and Redis."""

from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from fastapi import Request, HTTPException, status
from app.core.config import get_settings

settings = get_settings()

# Initialize Redis client for rate limiting
import redis
redis_client = redis.from_url(settings.redis_url)

# Create limiter instance
limiter = Limiter(
    key_func=get_remote_address,
    storage_uri=settings.redis_url,
    default_limits=["1000/hour"]  # Global limit
)

# Custom error handler for rate limiting
async def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded):
    """Custom handler for rate limit exceeded."""
    raise HTTPException(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        detail={
            "error": "Rate limit exceeded",
            "limit": exc.detail,
            "retry_after": exc.retry_after,
        },
    )
