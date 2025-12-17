from datetime import datetime

import redis
from fastapi import APIRouter, Depends

from ..models.schemas import HealthResponse
from ..services.job_service import get_redis_client

router = APIRouter()


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

    # TODO: Check GPU availability (Phase 3 - real pipeline integration)
    # For Phase 1, we report as unavailable since we're using dummy processing
    gpu_status = "unavailable"

    status = "healthy" if redis_status == "connected" else "unhealthy"

    return HealthResponse(
        status=status,
        redis=redis_status,
        worker=worker_status,
        gpu=gpu_status,
        timestamp=datetime.utcnow(),
        error=error_msg,
    )
