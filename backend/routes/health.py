from fastapi import APIRouter, Depends
from datetime import datetime
from typing import Literal
from pydantic import BaseModel
import redis

from ..config import get_settings, Settings


router = APIRouter()


class HealthResponse(BaseModel):
    """Health check response model."""
    status: Literal["healthy", "unhealthy"]
    redis: Literal["connected", "disconnected"]
    worker: Literal["available", "unavailable"]
    timestamp: datetime
    error: str | None = None


def get_redis_client(settings: Settings = Depends(get_settings)) -> redis.Redis:
    """Get Redis client instance."""
    return redis.from_url(settings.redis_url, decode_responses=True)


@router.get("/health", response_model=HealthResponse)
async def health_check(redis_client: redis.Redis = Depends(get_redis_client)):
    """Check health of the application and its dependencies."""
    error_msg = None
    
    try:
        # Test Redis connection
        redis_client.ping()
        redis_status = "connected"
    except redis.ConnectionError:
        redis_status = "disconnected"
        error_msg = "Redis connection failed"
    except Exception as e:
        redis_status = "disconnected"
        error_msg = f"Redis error: {str(e)}"
    
    # TODO: Check Celery worker status (inspect active workers)
    # For Phase 1, we just report as available if Redis is connected
    worker_status = "available" if redis_status == "connected" else "unavailable"
    
    status = "healthy" if redis_status == "connected" else "unhealthy"
    
    return HealthResponse(
        status=status,
        redis=redis_status,
        worker=worker_status,
        timestamp=datetime.utcnow(),
        error=error_msg
    )
