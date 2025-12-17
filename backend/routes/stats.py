"""
Stats route - GET /stats

Returns usage statistics for homepage display.
"""
import redis
from fastapi import APIRouter, Depends

from ..models.job import Job
from ..models.schemas import StatsResponse
from ..services.job_service import get_redis_client
from ..services.statistics import get_statistics

router = APIRouter()


@router.get("/stats", response_model=StatsResponse)
async def get_stats(redis_client: redis.Redis = Depends(get_redis_client)) -> StatsResponse:
    """
    Get usage statistics for display on the main page.

    Returns:
    - total_jobs_processed: All-time job count
    - total_jobs_today: Jobs processed today
    - unique_users: Count of unique email addresses
    - average_processing_time_seconds: Rolling average of recent jobs
    - jobs_in_queue: Current queue depth
    - uptime_hours: Time since server started
    """
    stats = get_statistics(redis_client)

    return StatsResponse(
        total_jobs_processed=stats["total_processed"],
        total_jobs_today=stats["today_processed"],
        unique_users=stats["unique_users"],
        average_processing_time_seconds=stats["avg_processing_time"],
        jobs_in_queue=Job.get_queue_length(redis_client),
        uptime_hours=stats["uptime_hours"],
    )
