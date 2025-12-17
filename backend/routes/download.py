"""
Download route - GET /download/{job_id}

Serves the results zip file for completed jobs.
"""
from pathlib import Path

import redis
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse

from ..models.job import Job
from ..services.job_service import get_redis_client

router = APIRouter()


@router.get("/download/{job_id}")
async def download_results(
    job_id: str,
    redis_client: redis.Redis = Depends(get_redis_client),
) -> FileResponse:
    """
    Download the results zip file.

    Only available for completed jobs. Returns a zip file containing:
    - Segmentation masks
    - Results summary (JSON and CSV)
    - Additional outputs (meshes, etc. in Phase 3)
    """
    # Load job
    job = Job.load(job_id, redis_client)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    # Check job is complete
    if job.status != "complete":
        raise HTTPException(
            status_code=400, detail=f"Job not complete. Current status: {job.status}"
        )

    # Check result path exists
    if not job.result_path:
        raise HTTPException(status_code=404, detail="Results not found")

    result_path = Path(job.result_path)
    if not result_path.exists():
        raise HTTPException(status_code=404, detail="Results file not found")

    # Generate download filename
    input_stem = Path(job.input_filename).stem
    if job.input_filename.endswith(".nii.gz"):
        input_stem = Path(input_stem).stem  # Remove .nii from .nii.gz
    download_name = f"{input_stem}_results.zip"

    return FileResponse(path=result_path, filename=download_name, media_type="application/zip")
