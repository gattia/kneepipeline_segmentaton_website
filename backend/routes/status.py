"""
Status route - GET /status/{job_id}

Returns current status of a processing job.
"""
from datetime import datetime
from typing import Union

import redis
from fastapi import APIRouter, Depends, HTTPException

from ..models.job import Job
from ..models.schemas import StatusComplete, StatusError, StatusProcessing, StatusQueued
from ..services.job_service import get_estimated_wait, get_redis_client

router = APIRouter()


@router.get(
    "/status/{job_id}",
    response_model=Union[StatusQueued, StatusProcessing, StatusComplete, StatusError],
)
async def get_status(
    job_id: str, redis_client: redis.Redis = Depends(get_redis_client)
) -> Union[StatusQueued, StatusProcessing, StatusComplete, StatusError]:
    """
    Get current status of a processing job.

    Returns different response schemas based on job status:
    - queued: Queue position and estimated wait time
    - processing: Progress percentage and current step
    - complete: Download URL and processing time
    - error: Error message and code
    """
    job = Job.load(job_id, redis_client)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if job.status == "queued":
        queue_position = Job.get_queue_position(job_id, redis_client)
        return StatusQueued(
            job_id=job_id,
            status="queued",
            queue_position=queue_position,
            estimated_wait_seconds=get_estimated_wait(queue_position, redis_client),
        )

    elif job.status == "processing":
        elapsed = 0
        if job.started_at:
            started = datetime.fromisoformat(job.started_at)
            elapsed = int((datetime.now() - started).total_seconds())

        # Estimate remaining based on average time per step
        avg_per_step = 60  # Default 60 seconds per step
        remaining_steps = job.total_steps - job.current_step
        remaining = max(0, remaining_steps * avg_per_step)

        return StatusProcessing(
            job_id=job_id,
            status="processing",
            progress_percent=job.progress_percent,
            current_step=job.current_step,
            total_steps=job.total_steps,
            step_name=job.step_name or "Processing...",
            elapsed_seconds=elapsed,
            estimated_remaining_seconds=remaining,
        )

    elif job.status == "complete":
        processing_time = 0
        if job.started_at and job.completed_at:
            started = datetime.fromisoformat(job.started_at)
            completed = datetime.fromisoformat(job.completed_at)
            processing_time = int((completed - started).total_seconds())

        return StatusComplete(
            job_id=job_id,
            status="complete",
            download_url=f"/download/{job_id}",
            result_size_bytes=job.result_size_bytes or 0,
            processing_time_seconds=processing_time,
        )

    else:  # error
        return StatusError(
            job_id=job_id,
            status="error",
            error_message=job.error_message or "Unknown error",
            error_code=job.error_code or "UNKNOWN",
        )
