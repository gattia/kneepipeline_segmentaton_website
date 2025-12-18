"""
Celery task definitions.

This module defines the main processing task that orchestrates
job execution, progress updates, and result handling.

Note on Redis client:
    This module has its own get_redis_client() function separate from
    job_service.py because the job_service version uses FastAPI's Depends()
    pattern, which only works in HTTP request context, not in Celery workers.
"""
import os
from datetime import datetime

import redis

# Import REDIS_URL from celery_app to avoid duplicating env var read
from .celery_app import REDIS_URL, celery_app


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
    3. Runs the real pipeline (or dummy for testing)
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
    settings = get_settings()

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
        # Setup output directory (use resolve() for absolute path)
        output_dir = (settings.results_dir / job_id).resolve()
        output_dir.mkdir(parents=True, exist_ok=True)

        # Progress callback to update job status
        def progress_callback(step: int, total: int, step_name: str):
            job.current_step = step
            job.total_steps = total
            job.step_name = step_name
            job.progress_percent = int((step / total) * 100)
            job.save(redis_client)

        # Decide whether to use real or dummy pipeline
        use_real_pipeline = _should_use_real_pipeline(options)

        if use_real_pipeline:
            # Import real pipeline components
            from backend.services.config_generator import generate_pipeline_config
            from backend.workers.pipeline_worker import run_real_pipeline

            # Generate job-specific config
            config_path = generate_pipeline_config(
                job_dir=output_dir,
                options=options
            )

            # Run real pipeline
            result_path = run_real_pipeline(
                input_path=input_path,
                options=options,
                output_dir=output_dir,
                config_path=config_path,
                progress_callback=progress_callback
            )
        else:
            # Use dummy pipeline for testing
            from backend.workers.dummy_worker import dummy_pipeline
            result_path = dummy_pipeline(
                input_path=input_path,
                options=options,
                output_dir=output_dir,
                progress_callback=progress_callback
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

    except TimeoutError as e:
        # Use error handler for user-friendly message
        from backend.services.error_handler import format_error_for_job
        error_code, error_message = format_error_for_job(e)
        job.status = "error"
        job.error_message = error_message
        job.error_code = error_code
        job.save(redis_client)
        _cleanup_after_error()
        raise

    except Exception as e:
        # Try to get more specific error from pipeline output
        from backend.services.error_handler import format_error_for_job
        output = getattr(e, 'output', str(e))
        error_code, error_message = format_error_for_job(e, output)
        job.status = "error"
        job.error_message = error_message
        job.error_code = error_code
        job.save(redis_client)
        _cleanup_after_error()

        # Re-raise to trigger Celery retry if applicable
        raise


def _should_use_real_pipeline(options: dict) -> bool:
    """
    Determine whether to use real pipeline or dummy.

    Uses real pipeline by default. Set USE_DUMMY_PIPELINE=1 env var
    to force dummy pipeline for testing.
    """
    if os.getenv("USE_DUMMY_PIPELINE", "0") == "1":
        return False
    return True


def _cleanup_after_error():
    """Clean up resources after an error."""
    try:
        from backend.workers.pipeline_worker import cleanup_gpu_memory
        cleanup_gpu_memory()
    except Exception:
        pass  # Ignore cleanup errors


