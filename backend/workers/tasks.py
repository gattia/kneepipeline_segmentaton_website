"""
Celery task definitions.

This module defines the main processing task that orchestrates
job execution, progress updates, and result handling.

Note on Redis client:
    This module has its own get_redis_client() function separate from
    job_service.py because the job_service version uses FastAPI's Depends()
    pattern, which only works in HTTP request context, not in Celery workers.
"""
from datetime import datetime

import redis

# Import REDIS_URL from celery_app to avoid duplicating env var read
from .celery_app import REDIS_URL, celery_app
from .dummy_worker import dummy_pipeline


def get_redis_client() -> redis.Redis:
    """
    Get Redis client for Celery task operations.

    Note: This is separate from job_service.get_redis_client() because
    that function uses FastAPI Depends() which doesn't work in Celery context.
    """
    return redis.from_url(REDIS_URL, decode_responses=True)


@celery_app.task(bind=True, max_retries=2)
def process_pipeline(self, job_id: str, input_path: str, options: dict) -> dict:
    """
    Main pipeline task executed by Celery worker.

    This task:
    1. Loads the job from Redis
    2. Updates status to 'processing'
    3. Runs the dummy pipeline (Phase 1) or real pipeline (Phase 3)
    4. Updates job with results or error
    5. Records statistics

    Args:
        job_id: Unique job identifier
        input_path: Path to the validated input file
        options: Processing options dict

    Returns:
        Dict with status and result_path on success

    Raises:
        ValueError: If job not found
        Exception: On processing failure (will be retried)
    """
    # NOTE: These imports are inside the function intentionally to avoid
    # circular imports when Celery loads the workers module at startup.
    # The backend.config and backend.models modules may import from workers,
    # so we defer these imports until task execution time.
    from backend.config import get_settings
    from backend.models.job import Job
    from backend.services.job_service import record_processing_time
    from backend.services.statistics import increment_processed_count

    redis_client = get_redis_client()

    # Load job from Redis
    job = Job.load(job_id, redis_client)
    if not job:
        raise ValueError(f"Job {job_id} not found in Redis")

    # Update status to processing
    job.status = "processing"
    job.started_at = datetime.now().isoformat()
    job.delete_from_queue(redis_client)
    job.save(redis_client)

    try:
        # Get settings for output directory
        settings = get_settings()
        output_dir = settings.results_dir / job_id
        output_dir.mkdir(parents=True, exist_ok=True)

        # Define progress callback to update job status
        def progress_callback(step: int, total: int, step_name: str):
            job.current_step = step
            job.total_steps = total
            job.step_name = step_name
            job.progress_percent = int((step / total) * 100)
            job.save(redis_client)

        # Run dummy pipeline (Phase 1)
        # In Phase 3, this will call the real pipeline
        result_path = dummy_pipeline(
            input_path=input_path,
            options=options,
            output_dir=output_dir,
            progress_callback=progress_callback,
        )

        # Mark job as complete
        job.status = "complete"
        job.progress_percent = 100
        job.completed_at = datetime.now().isoformat()
        job.result_path = str(result_path)
        job.result_size_bytes = result_path.stat().st_size
        job.save(redis_client)

        # Record statistics
        started = datetime.fromisoformat(job.started_at)
        completed = datetime.fromisoformat(job.completed_at)
        duration = (completed - started).total_seconds()
        record_processing_time(duration, redis_client)
        increment_processed_count(redis_client)

        return {
            "status": "complete",
            "job_id": job_id,
            "result_path": str(result_path),
            "duration_seconds": duration,
        }

    except Exception as e:
        # Mark job as error
        job.status = "error"
        job.error_message = str(e)
        job.error_code = _get_error_code(e)
        job.save(redis_client)

        # Re-raise to trigger Celery retry if applicable
        raise


def _get_error_code(exception: Exception) -> str:
    """Map exception to error code for API response."""
    error_msg = str(exception).lower()

    if "not found" in error_msg:
        return "FILE_NOT_FOUND"
    elif "read" in error_msg or "format" in error_msg:
        return "INVALID_FORMAT"
    elif "memory" in error_msg or "oom" in error_msg:
        return "GPU_OOM"
    elif "dicom" in error_msg:
        return "DICOM_ERROR"
    else:
        return "PIPELINE_ERROR"
