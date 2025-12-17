"""
Upload route - POST /upload

Accepts file uploads, validates them, creates a job, and submits to Celery.
"""
import shutil
import uuid
from pathlib import Path

import redis
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile

from ..config import Settings, get_settings
from ..models.job import Job
from ..models.schemas import UploadResponse
from ..services.file_handler import validate_and_prepare_upload
from ..services.job_service import get_estimated_wait, get_redis_client
from ..services.statistics import track_user_email
from ..workers.tasks import process_pipeline

router = APIRouter()

# Allowed file extensions
ALLOWED_EXTENSIONS = {".zip", ".nii", ".nii.gz", ".nrrd", ".dcm"}


def _get_file_extension(filename: str) -> str:
    """Get file extension, handling .nii.gz specially."""
    if filename.lower().endswith(".nii.gz"):
        return ".nii.gz"
    return Path(filename).suffix.lower()


# TODO (Phase 2): Add rate limiting - 10 uploads/hour per IP to prevent abuse


@router.post("/upload", response_model=UploadResponse, status_code=201)
async def upload_file(
    file: UploadFile = File(...),
    email: str = Form(default=None),
    segmentation_model: str = Form(default="nnunet_fullres"),
    perform_nsm: bool = Form(default=True),
    nsm_type: str = Form(default="bone_and_cart"),
    retain_results: bool = Form(default=True),
    cartilage_smoothing: float = Form(default=0.3125),
    settings: Settings = Depends(get_settings),
    redis_client: redis.Redis = Depends(get_redis_client),
) -> UploadResponse:
    """
    Upload a file and start processing.

    Accepts multipart form data with:
    - file: The medical image file (.zip, .nii, .nii.gz, .nrrd, .dcm)
    - email: Optional email for tracking and notifications
    - segmentation_model: Model to use for segmentation
    - perform_nsm: Whether to perform Neural Shape Modeling
    - nsm_type: Type of NSM analysis ("bone_and_cart", "bone_only", "both")
    - retain_results: Allow anonymized results to be retained for research
    - cartilage_smoothing: Smoothing parameter for cartilage analysis

    Returns job_id and queue position.
    """
    # 1. Validate file extension
    filename = file.filename or "unknown"
    extension = _get_file_extension(filename)

    if extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type '{extension}'. Accepted: {', '.join(sorted(ALLOWED_EXTENSIONS))}",
        )

    # 2. Generate unique job ID
    job_id = str(uuid.uuid4())

    # 3. Create job upload directory
    job_upload_dir = settings.upload_dir / job_id
    job_upload_dir.mkdir(parents=True, exist_ok=True)
    upload_path = job_upload_dir / filename

    try:
        # 4. Save uploaded file to disk
        with open(upload_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        shutil.rmtree(job_upload_dir, ignore_errors=True)
        raise HTTPException(status_code=500, detail=f"Failed to save file: {e}") from e
    finally:
        file.file.close()

    # 5. Check file size
    file_size = upload_path.stat().st_size
    max_size_bytes = settings.max_upload_size_mb * 1024 * 1024

    if file_size > max_size_bytes:
        shutil.rmtree(job_upload_dir, ignore_errors=True)
        raise HTTPException(
            status_code=413,
            detail=f"File too large ({file_size / 1024 / 1024:.1f} MB). Maximum: {settings.max_upload_size_mb} MB.",
        )

    if file_size == 0:
        shutil.rmtree(job_upload_dir, ignore_errors=True)
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    # 6. Validate and prepare (extract zip if needed, validate medical image)
    try:
        temp_dir = settings.temp_dir / job_id
        prepared_path = validate_and_prepare_upload(upload_path, temp_dir)
    except ValueError as e:
        shutil.rmtree(job_upload_dir, ignore_errors=True)
        shutil.rmtree(settings.temp_dir / job_id, ignore_errors=True)
        raise HTTPException(status_code=400, detail=str(e)) from e

    # 7. Create options dict
    options = {
        "segmentation_model": segmentation_model,
        "perform_nsm": perform_nsm,
        "nsm_type": nsm_type,
        "retain_results": retain_results,
        "cartilage_smoothing": cartilage_smoothing,
    }

    # 8. Track unique user if email provided
    if email:
        track_user_email(email, redis_client)

    # 9. Create and save job
    job = Job(
        id=job_id,
        input_filename=filename,
        input_path=str(prepared_path),
        options=options,
        retain_for_research=retain_results,
        email=email,
    )
    job.save(redis_client)

    # 10. Submit Celery task
    process_pipeline.delay(job_id, str(prepared_path), options)

    # 11. Get queue info
    queue_position = Job.get_queue_position(job_id, redis_client)
    estimated_wait = get_estimated_wait(queue_position, redis_client)

    return UploadResponse(
        job_id=job_id,
        status="queued",
        queue_position=queue_position,
        estimated_wait_seconds=estimated_wait,
        message=f"File uploaded successfully. You are #{queue_position} in queue.",
    )
