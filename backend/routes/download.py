"""
Download route - GET /download/{job_id}

Serves the results zip file for completed jobs.
"""
import os
from pathlib import Path

import redis
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse

from ..models.job import Job
from ..services.job_service import get_redis_client

router = APIRouter()

# Path translation for Host -> Docker (reverse of worker translation)
# The worker stores paths as host paths, but download runs in Docker
HOST_DATA_PATH = "/mnt/data/knee_pipeline_data"
DOCKER_DATA_PATH = os.getenv("DOCKER_DATA_PATH", "/app/data")


def translate_host_path_to_docker(path: str) -> str:
    """
    Translate host path to Docker container path.
    
    The worker stores result paths as host paths (/mnt/data/knee_pipeline_data/...),
    but when running in Docker, we need to access them at /app/data/...
    """
    if path.startswith(HOST_DATA_PATH):
        return path.replace(HOST_DATA_PATH, DOCKER_DATA_PATH, 1)
    return path


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

    # Translate host path to Docker path (worker stores host paths)
    translated_path = translate_host_path_to_docker(job.result_path)
    result_path = Path(translated_path)
    if not result_path.exists():
        raise HTTPException(status_code=404, detail="Results file not found")

    # Generate download filename
    input_stem = Path(job.input_filename).stem
    if job.input_filename.endswith(".nii.gz"):
        input_stem = Path(input_stem).stem  # Remove .nii from .nii.gz
    download_name = f"{input_stem}_results.zip"

    return FileResponse(path=result_path, filename=download_name, media_type="application/zip")
