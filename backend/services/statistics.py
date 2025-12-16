"""
Usage statistics tracking service.

Tracks:
- Total jobs processed (all time)
- Jobs processed today
- Unique users (by email)
- Processing time averages
- Application uptime
"""
import hashlib
from datetime import date, datetime

import redis


def get_statistics(redis_client: redis.Redis) -> dict:
    """
    Get all usage statistics.

    Returns:
        Dictionary with stats fields:
        - total_processed: All-time job count
        - today_processed: Jobs processed today
        - unique_users: Count of unique email addresses
        - avg_processing_time: Average processing time in seconds
        - uptime_hours: Hours since server start
    """
    # Total jobs processed (all time)
    total_processed = redis_client.get("stats:total_processed")
    total_processed = int(total_processed) if total_processed else 0

    # Jobs processed today
    today_key = f"stats:processed:{date.today().isoformat()}"
    today_processed = redis_client.get(today_key)
    today_processed = int(today_processed) if today_processed else 0

    # Unique users (count of unique emails)
    unique_users = redis_client.scard("stats:unique_emails")

    # Average processing time
    times = redis_client.lrange("processing_times", 0, 19)
    avg_time = int(sum(float(t) for t in times) / len(times)) if times else 240

    # Uptime (from startup timestamp)
    startup_time = redis_client.get("stats:startup_time")
    if startup_time:
        started = datetime.fromisoformat(startup_time)
        uptime_hours = (datetime.now() - started).total_seconds() / 3600
    else:
        uptime_hours = 0.0
        # Set startup time if not already set
        redis_client.set("stats:startup_time", datetime.now().isoformat())

    return {
        "total_processed": total_processed,
        "today_processed": today_processed,
        "unique_users": unique_users,
        "avg_processing_time": avg_time,
        "uptime_hours": round(uptime_hours, 1)
    }


def increment_processed_count(redis_client: redis.Redis) -> None:
    """
    Increment the processed job counter.

    Updates both all-time and daily counters.
    Daily counter expires after 7 days.
    """
    redis_client.incr("stats:total_processed")

    today_key = f"stats:processed:{date.today().isoformat()}"
    redis_client.incr(today_key)
    redis_client.expire(today_key, 86400 * 7)  # Keep for 7 days


def track_user_email(email: str, redis_client: redis.Redis) -> None:
    """
    Track unique user email addresses.

    Uses a Redis set to store normalized emails for counting.
    Also maintains a hash for potential future contact (admin use).

    Args:
        email: User's email address
        redis_client: Redis client instance
    """
    # Normalize email (lowercase, strip whitespace)
    email_normalized = email.lower().strip()

    # Add to unique set (for counting)
    redis_client.sadd("stats:unique_emails", email_normalized)

    # Store email with hash for lookup (email -> hash mapping)
    email_hash = hashlib.sha256(email_normalized.encode()).hexdigest()[:16]
    redis_client.hset("user_emails", email_hash, email_normalized)


def get_all_user_emails(redis_client: redis.Redis) -> list:
    """
    Get all stored user emails (admin function).

    Returns:
        List of all email addresses
    """
    return list(redis_client.hvals("user_emails"))
