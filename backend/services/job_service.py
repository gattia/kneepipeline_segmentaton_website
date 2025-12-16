"""
Job queue management service.

Provides Redis client dependency and queue-related calculations.
"""
import redis
from fastapi import Depends

from ..config import Settings, get_settings


def get_redis_client(settings: Settings = Depends(get_settings)) -> redis.Redis:
    """
    FastAPI dependency to get Redis client instance.

    Uses decode_responses=True for automatic string decoding.
    """
    return redis.from_url(settings.redis_url, decode_responses=True)


def get_estimated_wait(queue_position: int, redis_client: redis.Redis) -> int:
    """
    Calculate estimated wait time based on queue position and average processing time.

    Args:
        queue_position: Position in queue (1-indexed)
        redis_client: Redis client instance

    Returns:
        Estimated wait time in seconds
    """
    avg_time = get_average_processing_time(redis_client)
    return int(queue_position * avg_time)


def get_average_processing_time(redis_client: redis.Redis) -> float:
    """
    Get rolling average of last 20 processing times.

    Returns default of 240 seconds (4 minutes) if no history available.
    """
    times = redis_client.lrange("processing_times", 0, 19)
    if not times:
        return 240.0  # Default 4 minutes
    return sum(float(t) for t in times) / len(times)


def record_processing_time(duration_seconds: float, redis_client: redis.Redis) -> None:
    """
    Record a processing time for averaging.

    Maintains a list of the last 20 processing times (FIFO).

    Args:
        duration_seconds: Processing duration to record
        redis_client: Redis client instance
    """
    redis_client.lpush("processing_times", duration_seconds)
    redis_client.ltrim("processing_times", 0, 19)  # Keep only last 20
