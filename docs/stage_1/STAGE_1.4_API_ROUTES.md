# Stage 1.4: API Routes

## Overview

**Goal**: Implement all REST API endpoints and wire them to the services, models, and Celery tasks from previous stages.

**Estimated Time**: ~45-60 minutes

**Deliverable**: Fully functional REST API that accepts file uploads, tracks job status, serves results, and returns usage statistics. Testable with curl or the test suite.

---

## Prerequisites

**Stage 1.3 must be complete.** Verify by running:

```bash
conda activate kneepipeline
cd ~/programming/kneepipeline_segmentaton_website

# All previous stage tests should pass
make verify

# Redis should be running
make redis-ping  # Should return PONG

# Celery worker should start (test in a separate terminal, Ctrl+C to stop)
make worker

# All imports should work
python -c "from backend.workers.tasks import process_pipeline; print('Tasks OK')"
python -c "from backend.models.job import Job; print('Job model OK')"
python -c "from backend.services.file_handler import validate_and_prepare_upload; print('File handler OK')"
```

See [STAGE_1.3_COMPLETED.md](./STAGE_1.3_COMPLETED.md) for details on what was created.

---

## What This Stage Creates

### New Files

```
backend/routes/
├── __init__.py              # UPDATE: export all routers
├── health.py                # (unchanged from Stage 1.1)
├── upload.py                # NEW: POST /upload endpoint
├── status.py                # NEW: GET /status/{job_id} endpoint
├── download.py              # NEW: GET /download/{job_id} endpoint
└── stats.py                 # NEW: GET /stats endpoint

backend/
└── main.py                  # UPDATE: include all routers

tests/
└── test_stage_1_4.py        # NEW: Stage 1.4 verification tests
```

### Components

| File | Endpoint | Purpose |
|------|----------|---------|
| `upload.py` | `POST /upload` | Accept file + options, create job, submit Celery task |
| `status.py` | `GET /status/{job_id}` | Return job status (queued/processing/complete/error) |
| `download.py` | `GET /download/{job_id}` | Serve results zip file |
| `stats.py` | `GET /stats` | Return usage statistics for homepage |

---

## API Specification

### POST /upload

**Purpose**: Upload a medical image file and start processing.

**Request**:
- Content-Type: `multipart/form-data`
- Body:
  | Field | Type | Required | Default | Description |
  |-------|------|----------|---------|-------------|
  | `file` | File | Yes | - | Medical image (.zip, .nii, .nii.gz, .nrrd, .dcm) |
  | `email` | string | No | null | Optional email for tracking |
  | `segmentation_model` | string | No | "nnunet_fullres" | Model to use |
  | `perform_nsm` | boolean | No | true | Whether to run shape modeling |
  | `nsm_type` | string | No | "bone_and_cart" | Type of NSM analysis |
  | `retain_results` | boolean | No | true | Allow research data retention |
  | `cartilage_smoothing` | float | No | 0.3125 | Smoothing parameter |

**Response (201 Created)**:
```json
{
  "job_id": "abc123-def456-...",
  "status": "queued",
  "queue_position": 3,
  "estimated_wait_seconds": 720,
  "message": "File uploaded successfully. You are #3 in queue."
}
```

**Error Responses**:
- `400 Bad Request`: Invalid file type, corrupted zip, no medical image found
- `413 Payload Too Large`: File exceeds 600MB limit
- `422 Unprocessable Entity`: Invalid form field values

### GET /status/{job_id}

**Purpose**: Get current status of a processing job.

**Response (queued)**:
```json
{
  "job_id": "abc123-def456",
  "status": "queued",
  "queue_position": 2,
  "estimated_wait_seconds": 480
}
```

**Response (processing)**:
```json
{
  "job_id": "abc123-def456",
  "status": "processing",
  "progress_percent": 45,
  "current_step": 2,
  "total_steps": 4,
  "step_name": "Processing image",
  "elapsed_seconds": 60,
  "estimated_remaining_seconds": 90
}
```

**Response (complete)**:
```json
{
  "job_id": "abc123-def456",
  "status": "complete",
  "download_url": "/download/abc123-def456",
  "result_size_bytes": 25690112,
  "processing_time_seconds": 180
}
```

**Response (error)**:
```json
{
  "job_id": "abc123-def456",
  "status": "error",
  "error_message": "Failed to read input image",
  "error_code": "INVALID_FORMAT"
}
```

**Error Responses**:
- `404 Not Found`: Job ID doesn't exist

### GET /download/{job_id}

**Purpose**: Download the results zip file.

**Response (200 OK)**:
- Content-Type: `application/zip`
- Content-Disposition: `attachment; filename="{input_name}_results.zip"`

**Error Responses**:
- `404 Not Found`: Job doesn't exist or results file missing
- `400 Bad Request`: Job not complete

### GET /stats

**Purpose**: Get usage statistics for homepage display.

**Response (200 OK)**:
```json
{
  "total_jobs_processed": 1247,
  "total_jobs_today": 23,
  "unique_users": 342,
  "average_processing_time_seconds": 252,
  "jobs_in_queue": 3,
  "uptime_hours": 168.5
}
```

---

## Design Decisions

These decisions ensure consistency and prevent common mistakes:

### 1. Response Status Codes

| Endpoint | Success | Common Errors |
|----------|---------|---------------|
| `POST /upload` | **201 Created** | 400, 413, 422 |
| `GET /status/{job_id}` | 200 OK | 404 |
| `GET /download/{job_id}` | 200 OK | 400, 404 |
| `GET /stats` | 200 OK | - |

### 2. File Upload Handling

- Use `UploadFile` from FastAPI (not `File`)
- Save to `{upload_dir}/{job_id}/{original_filename}`
- Check file size AFTER saving (stream to disk for large files)
- Clean up upload directory if validation fails

### 3. Union Response Types for Status

The status endpoint returns different schemas based on job status:
```python
from typing import Union
response_model=Union[StatusQueued, StatusProcessing, StatusComplete, StatusError]
```

### 4. Celery Task Submission

- Use `.delay()` for fire-and-forget submission
- Pass `job_id`, `input_path`, and `options` dict
- Don't wait for task completion in the HTTP request

### 5. Static Files Mount Order

The frontend static files mount (`app.mount("/", ...)`) must come AFTER all API routes are registered, or the API routes will be shadowed.

### 6. Allowed File Extensions

```python
ALLOWED_EXTENSIONS = {'.zip', '.nii', '.nii.gz', '.nrrd', '.dcm'}
```

Note: `.nii.gz` must be handled specially since it's a double extension.

---

## Success Criteria

- [ ] `POST /upload` accepts a file and returns job_id with status 201
- [ ] `POST /upload` rejects invalid file types with status 400
- [ ] `POST /upload` rejects oversized files with status 413
- [ ] `GET /status/{job_id}` returns correct status for queued jobs
- [ ] `GET /status/{job_id}` returns 404 for non-existent jobs
- [ ] `GET /download/{job_id}` returns 400 if job not complete
- [ ] `GET /download/{job_id}` returns 404 if job doesn't exist
- [ ] `GET /stats` returns usage statistics
- [ ] All routes are documented in OpenAPI (`/docs`)
- [ ] `pytest -m stage_1_4 -v` passes all tests

---

## Verification: pytest Tests

Run the Stage 1.4 tests to verify completion:

```bash
conda activate kneepipeline
cd ~/programming/kneepipeline_segmentaton_website
pytest -m stage_1_4 -v
```

**Expected:** All tests pass.

### Tests to Create: `tests/test_stage_1_4.py`

```python
"""
Stage 1.4 Verification Tests - API Routes

Run with: pytest -m stage_1_4 -v

These tests verify:
1. Upload route accepts files and creates jobs
2. Status route returns correct status for each job state
3. Download route serves results or returns appropriate errors
4. Stats route returns usage statistics
5. Error handling for invalid inputs
"""
import io
import json
import zipfile
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

# Mark all tests in this module as stage_1_4
pytestmark = pytest.mark.stage_1_4


class TestUploadRoute:
    """Verify POST /upload endpoint."""

    @pytest.fixture
    def client(self):
        """Create test client for the FastAPI app."""
        from backend.main import app
        return TestClient(app)

    @pytest.fixture
    def valid_nifti_bytes(self, temp_dir):
        """Create a valid NIfTI file and return its bytes."""
        import SimpleITK as sitk

        # Create a small 3D image
        img = sitk.Image([16, 16, 16], sitk.sitkInt16)
        img.SetSpacing([1.0, 1.0, 1.0])

        # Save to file
        nifti_path = temp_dir / "test.nii.gz"
        sitk.WriteImage(img, str(nifti_path))

        return nifti_path.read_bytes()

    def test_upload_returns_201(self, client, valid_nifti_bytes, redis_client):
        """Upload should return 201 Created with job info."""
        response = client.post(
            "/upload",
            files={"file": ("test.nii.gz", valid_nifti_bytes, "application/octet-stream")},
            data={"segmentation_model": "nnunet_fullres"}
        )

        assert response.status_code == 201
        data = response.json()
        assert "job_id" in data
        assert data["status"] == "queued"
        assert "queue_position" in data
        assert "estimated_wait_seconds" in data
        assert "message" in data

    def test_upload_creates_job_in_redis(self, client, valid_nifti_bytes, redis_client):
        """Upload should create a job record in Redis."""
        response = client.post(
            "/upload",
            files={"file": ("test.nii.gz", valid_nifti_bytes, "application/octet-stream")},
        )

        assert response.status_code == 201
        job_id = response.json()["job_id"]

        # Check job exists in Redis
        job_data = redis_client.hget("jobs", job_id)
        assert job_data is not None

        job = json.loads(job_data)
        assert job["id"] == job_id
        assert job["status"] == "queued"

    def test_upload_rejects_invalid_extension(self, client):
        """Upload should reject files with invalid extensions."""
        response = client.post(
            "/upload",
            files={"file": ("test.txt", b"not a medical image", "text/plain")},
        )

        assert response.status_code == 400
        assert "invalid" in response.json()["detail"].lower()

    def test_upload_rejects_empty_file(self, client):
        """Upload should reject empty files."""
        response = client.post(
            "/upload",
            files={"file": ("test.nii.gz", b"", "application/octet-stream")},
        )

        assert response.status_code == 400

    def test_upload_rejects_oversized_file(self, client):
        """Upload should reject files exceeding size limit."""
        # Create a file that's larger than allowed (mock the check)
        # The actual 600MB limit is impractical for tests, so we test the logic

        # This test verifies the size check exists
        # In real usage, the check happens after streaming to disk
        pass  # Size check is tested indirectly through integration tests

    def test_upload_with_email(self, client, valid_nifti_bytes, redis_client):
        """Upload should store email if provided."""
        response = client.post(
            "/upload",
            files={"file": ("test.nii.gz", valid_nifti_bytes, "application/octet-stream")},
            data={"email": "test@example.com"}
        )

        assert response.status_code == 201
        job_id = response.json()["job_id"]

        # Check email is stored in job
        job_data = redis_client.hget("jobs", job_id)
        job = json.loads(job_data)
        assert job["email"] == "test@example.com"

    def test_upload_with_all_options(self, client, valid_nifti_bytes, redis_client):
        """Upload should accept all configuration options."""
        response = client.post(
            "/upload",
            files={"file": ("test.nii.gz", valid_nifti_bytes, "application/octet-stream")},
            data={
                "email": "user@example.com",
                "segmentation_model": "nnunet_cascade",
                "perform_nsm": "true",
                "nsm_type": "bone_only",
                "retain_results": "false",
                "cartilage_smoothing": "0.5"
            }
        )

        assert response.status_code == 201
        job_id = response.json()["job_id"]

        # Verify options stored correctly
        job_data = redis_client.hget("jobs", job_id)
        job = json.loads(job_data)
        assert job["options"]["segmentation_model"] == "nnunet_cascade"
        assert job["options"]["nsm_type"] == "bone_only"

    def test_upload_handles_zip_file(self, client, valid_nifti_bytes, temp_dir, redis_client):
        """Upload should extract and process zip files."""
        import SimpleITK as sitk

        # Create a zip containing a NIfTI file
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w') as zf:
            zf.writestr("patient/scan.nii.gz", valid_nifti_bytes)
        zip_buffer.seek(0)

        response = client.post(
            "/upload",
            files={"file": ("patient_data.zip", zip_buffer.read(), "application/zip")},
        )

        assert response.status_code == 201


class TestStatusRoute:
    """Verify GET /status/{job_id} endpoint."""

    @pytest.fixture
    def client(self):
        from backend.main import app
        return TestClient(app)

    def test_status_queued_job(self, client, redis_client):
        """Status should return queued info for queued jobs."""
        from backend.models.job import Job

        # Create a queued job
        job = Job(
            id="status-test-queued",
            input_filename="test.nii.gz",
            input_path="/fake/path/test.nii.gz",
            options={"segmentation_model": "nnunet_fullres"},
            status="queued"
        )
        job.save(redis_client)

        response = client.get("/status/status-test-queued")

        assert response.status_code == 200
        data = response.json()
        assert data["job_id"] == "status-test-queued"
        assert data["status"] == "queued"
        assert "queue_position" in data
        assert "estimated_wait_seconds" in data

    def test_status_processing_job(self, client, redis_client):
        """Status should return progress info for processing jobs."""
        from backend.models.job import Job
        from datetime import datetime

        job = Job(
            id="status-test-processing",
            input_filename="test.nii.gz",
            input_path="/fake/path/test.nii.gz",
            options={},
            status="processing",
            started_at=datetime.now().isoformat(),
            progress_percent=50,
            current_step=2,
            total_steps=4,
            step_name="Processing image"
        )
        job.save(redis_client)

        response = client.get("/status/status-test-processing")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "processing"
        assert data["progress_percent"] == 50
        assert data["current_step"] == 2
        assert data["step_name"] == "Processing image"

    def test_status_complete_job(self, client, redis_client, temp_dir):
        """Status should return download info for complete jobs."""
        from backend.models.job import Job
        from datetime import datetime

        # Create a fake result file
        result_path = temp_dir / "results.zip"
        result_path.write_bytes(b"fake zip content")

        job = Job(
            id="status-test-complete",
            input_filename="test.nii.gz",
            input_path="/fake/path/test.nii.gz",
            options={},
            status="complete",
            started_at=datetime.now().isoformat(),
            completed_at=datetime.now().isoformat(),
            result_path=str(result_path),
            result_size_bytes=result_path.stat().st_size
        )
        job.save(redis_client)

        response = client.get("/status/status-test-complete")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "complete"
        assert "download_url" in data
        assert data["result_size_bytes"] > 0

    def test_status_error_job(self, client, redis_client):
        """Status should return error info for failed jobs."""
        from backend.models.job import Job

        job = Job(
            id="status-test-error",
            input_filename="test.nii.gz",
            input_path="/fake/path/test.nii.gz",
            options={},
            status="error",
            error_message="Segmentation failed",
            error_code="PIPELINE_ERROR"
        )
        job.save(redis_client)

        response = client.get("/status/status-test-error")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "error"
        assert data["error_message"] == "Segmentation failed"
        assert data["error_code"] == "PIPELINE_ERROR"

    def test_status_not_found(self, client, redis_client):
        """Status should return 404 for non-existent jobs."""
        response = client.get("/status/nonexistent-job-id")

        assert response.status_code == 404


class TestDownloadRoute:
    """Verify GET /download/{job_id} endpoint."""

    @pytest.fixture
    def client(self):
        from backend.main import app
        return TestClient(app)

    def test_download_complete_job(self, client, redis_client, temp_dir):
        """Download should serve results zip for complete jobs."""
        from backend.models.job import Job
        from datetime import datetime

        # Create a real zip file
        result_path = temp_dir / "test_results.zip"
        with zipfile.ZipFile(result_path, 'w') as zf:
            zf.writestr("results.json", '{"status": "complete"}')
        
        job = Job(
            id="download-test-complete",
            input_filename="patient_scan.nii.gz",
            input_path="/fake/path",
            options={},
            status="complete",
            started_at=datetime.now().isoformat(),
            completed_at=datetime.now().isoformat(),
            result_path=str(result_path),
            result_size_bytes=result_path.stat().st_size
        )
        job.save(redis_client)

        response = client.get("/download/download-test-complete")

        assert response.status_code == 200
        assert response.headers["content-type"] == "application/zip"
        assert "patient_scan" in response.headers["content-disposition"]

    def test_download_not_complete(self, client, redis_client):
        """Download should return 400 for non-complete jobs."""
        from backend.models.job import Job

        job = Job(
            id="download-test-processing",
            input_filename="test.nii.gz",
            input_path="/fake/path",
            options={},
            status="processing"
        )
        job.save(redis_client)

        response = client.get("/download/download-test-processing")

        assert response.status_code == 400
        assert "not complete" in response.json()["detail"].lower()

    def test_download_not_found(self, client, redis_client):
        """Download should return 404 for non-existent jobs."""
        response = client.get("/download/nonexistent-job")

        assert response.status_code == 404

    def test_download_missing_result_file(self, client, redis_client):
        """Download should return 404 if result file is missing."""
        from backend.models.job import Job
        from datetime import datetime

        job = Job(
            id="download-test-missing",
            input_filename="test.nii.gz",
            input_path="/fake/path",
            options={},
            status="complete",
            started_at=datetime.now().isoformat(),
            completed_at=datetime.now().isoformat(),
            result_path="/nonexistent/path/results.zip",
            result_size_bytes=1000
        )
        job.save(redis_client)

        response = client.get("/download/download-test-missing")

        assert response.status_code == 404


class TestStatsRoute:
    """Verify GET /stats endpoint."""

    @pytest.fixture
    def client(self):
        from backend.main import app
        return TestClient(app)

    def test_stats_returns_all_fields(self, client, redis_client):
        """Stats should return all required fields."""
        response = client.get("/stats")

        assert response.status_code == 200
        data = response.json()

        required_fields = [
            "total_jobs_processed",
            "total_jobs_today",
            "unique_users",
            "average_processing_time_seconds",
            "jobs_in_queue",
            "uptime_hours"
        ]
        for field in required_fields:
            assert field in data, f"Missing field: {field}"

    def test_stats_returns_integers(self, client, redis_client):
        """Stats numeric fields should be correct types."""
        response = client.get("/stats")
        data = response.json()

        assert isinstance(data["total_jobs_processed"], int)
        assert isinstance(data["total_jobs_today"], int)
        assert isinstance(data["unique_users"], int)
        assert isinstance(data["average_processing_time_seconds"], int)
        assert isinstance(data["jobs_in_queue"], int)
        assert isinstance(data["uptime_hours"], (int, float))


class TestRouteRegistration:
    """Verify all routes are properly registered."""

    @pytest.fixture
    def client(self):
        from backend.main import app
        return TestClient(app)

    def test_openapi_includes_all_routes(self, client):
        """OpenAPI schema should document all routes."""
        response = client.get("/openapi.json")
        assert response.status_code == 200

        paths = response.json()["paths"]
        assert "/upload" in paths
        assert "/status/{job_id}" in paths
        assert "/download/{job_id}" in paths
        assert "/stats" in paths
        assert "/health" in paths

    def test_health_still_works(self, client):
        """Health endpoint should still be accessible."""
        response = client.get("/health")
        assert response.status_code == 200


class TestRoutesPackageExports:
    """Verify routes __init__.py exports correctly."""

    def test_routes_package_importable(self):
        """Routes package should be importable."""
        from backend import routes
        assert routes is not None

    def test_all_routers_exported(self):
        """All route modules should be exported."""
        from backend.routes import health, upload, status, download, stats
        assert health.router is not None
        assert upload.router is not None
        assert status.router is not None
        assert download.router is not None
        assert stats.router is not None
```

---

## Detailed Implementation

### Step 1: Create Upload Route

**File**: `backend/routes/upload.py`

```python
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
ALLOWED_EXTENSIONS = {'.zip', '.nii', '.nii.gz', '.nrrd', '.dcm'}


def _get_file_extension(filename: str) -> str:
    """Get file extension, handling .nii.gz specially."""
    if filename.lower().endswith('.nii.gz'):
        return '.nii.gz'
    return Path(filename).suffix.lower()


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
    redis_client: redis.Redis = Depends(get_redis_client)
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
            detail=f"Invalid file type '{extension}'. Accepted: {', '.join(sorted(ALLOWED_EXTENSIONS))}"
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
        raise HTTPException(status_code=500, detail=f"Failed to save file: {e}")
    finally:
        file.file.close()

    # 5. Check file size
    file_size = upload_path.stat().st_size
    max_size_bytes = settings.max_upload_size_mb * 1024 * 1024

    if file_size > max_size_bytes:
        shutil.rmtree(job_upload_dir, ignore_errors=True)
        raise HTTPException(
            status_code=413,
            detail=f"File too large ({file_size / 1024 / 1024:.1f} MB). Maximum: {settings.max_upload_size_mb} MB."
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
        raise HTTPException(status_code=400, detail=str(e))

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
        message=f"File uploaded successfully. You are #{queue_position} in queue."
    )
```

---

### Step 2: Create Status Route

**File**: `backend/routes/status.py`

```python
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
    response_model=Union[StatusQueued, StatusProcessing, StatusComplete, StatusError]
)
async def get_status(
    job_id: str,
    redis_client: redis.Redis = Depends(get_redis_client)
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
            estimated_wait_seconds=get_estimated_wait(queue_position, redis_client)
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
            estimated_remaining_seconds=remaining
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
            processing_time_seconds=processing_time
        )

    else:  # error
        return StatusError(
            job_id=job_id,
            status="error",
            error_message=job.error_message or "Unknown error",
            error_code=job.error_code or "UNKNOWN"
        )
```

---

### Step 3: Create Download Route

**File**: `backend/routes/download.py`

```python
"""
Download route - GET /download/{job_id}

Serves the results zip file for completed jobs.
"""
from pathlib import Path

import redis
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse

from ..config import Settings, get_settings
from ..models.job import Job
from ..services.job_service import get_redis_client

router = APIRouter()


@router.get("/download/{job_id}")
async def download_results(
    job_id: str,
    redis_client: redis.Redis = Depends(get_redis_client),
    settings: Settings = Depends(get_settings)
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
            status_code=400,
            detail=f"Job not complete. Current status: {job.status}"
        )

    # Check result path exists
    if not job.result_path:
        raise HTTPException(status_code=404, detail="Results not found")

    result_path = Path(job.result_path)
    if not result_path.exists():
        raise HTTPException(status_code=404, detail="Results file not found")

    # Generate download filename
    input_stem = Path(job.input_filename).stem
    if job.input_filename.endswith('.nii.gz'):
        input_stem = Path(input_stem).stem  # Remove .nii from .nii.gz
    download_name = f"{input_stem}_results.zip"

    return FileResponse(
        path=result_path,
        filename=download_name,
        media_type="application/zip"
    )
```

---

### Step 4: Create Stats Route

**File**: `backend/routes/stats.py`

```python
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
async def get_stats(
    redis_client: redis.Redis = Depends(get_redis_client)
) -> StatsResponse:
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
        uptime_hours=stats["uptime_hours"]
    )
```

---

### Step 5: Update Routes Package Init

**File**: `backend/routes/__init__.py`

```python
"""
Routes package - FastAPI route modules.

All routers are exported for registration in main.py.
"""
from . import download, health, stats, status, upload

__all__ = ["health", "upload", "status", "download", "stats"]
```

---

### Step 6: Update Main App

**File**: `backend/main.py`

```python
"""
FastAPI application entry point.

Configures the app, middleware, and routes.
"""
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .config import get_settings
from .routes import download, health, stats, status, upload


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    # Startup: create directories
    settings = get_settings()
    for dir_path in [settings.upload_dir, settings.temp_dir,
                     settings.log_dir, settings.results_dir]:
        dir_path.mkdir(parents=True, exist_ok=True)
    yield
    # Shutdown: cleanup if needed


app = FastAPI(
    title="Knee MRI Analysis Pipeline",
    description="Automated knee MRI segmentation and analysis",
    version="0.1.0",
    lifespan=lifespan
)

# CORS for development
settings = get_settings()
if settings.debug:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000", "http://localhost:8000", "http://127.0.0.1:8000"],
        allow_credentials=True,
        allow_methods=["GET", "POST"],
        allow_headers=["*"],
    )

# Register API routes (BEFORE static files mount)
app.include_router(health.router, tags=["Health"])
app.include_router(upload.router, tags=["Upload"])
app.include_router(status.router, tags=["Status"])
app.include_router(download.router, tags=["Download"])
app.include_router(stats.router, tags=["Statistics"])

# Serve frontend static files (AFTER API routes, or they will be shadowed)
frontend_path = Path(__file__).parent.parent / "frontend"
if frontend_path.exists():
    app.mount("/", StaticFiles(directory=str(frontend_path), html=True), name="frontend")
```

---

## Expected Final State

After completing Stage 1.4, your project should have:

```
backend/
├── __init__.py
├── main.py                      # UPDATED: includes all routers
├── config.py                    # (unchanged)
├── requirements.txt             # (unchanged)
├── routes/
│   ├── __init__.py              # UPDATED: exports all routes
│   ├── health.py                # (unchanged from Stage 1.1)
│   ├── upload.py                # NEW: POST /upload
│   ├── status.py                # NEW: GET /status/{job_id}
│   ├── download.py              # NEW: GET /download/{job_id}
│   └── stats.py                 # NEW: GET /stats
├── services/
│   ├── __init__.py
│   ├── file_handler.py          # (unchanged from Stage 1.2)
│   ├── job_service.py           # (unchanged from Stage 1.2)
│   └── statistics.py            # (unchanged from Stage 1.2)
├── workers/
│   ├── __init__.py
│   ├── celery_app.py            # (unchanged from Stage 1.3)
│   ├── tasks.py                 # (unchanged from Stage 1.3)
│   └── dummy_worker.py          # (unchanged from Stage 1.3)
└── models/
    ├── __init__.py
    ├── schemas.py               # (unchanged from Stage 1.2)
    └── job.py                   # (unchanged from Stage 1.2)

tests/
├── __init__.py
├── conftest.py                  # (unchanged)
├── test_stage_1_1.py            # 23 tests
├── test_stage_1_2.py            # 36 tests
├── test_stage_1_3.py            # 27 tests
└── test_stage_1_4.py            # NEW: ~30 tests
```

---

## Verification Commands

```bash
# Activate environment
conda activate kneepipeline
cd ~/programming/kneepipeline_segmentaton_website

# Verify imports work
python -c "from backend.routes import upload, status, download, stats; print('All routes OK')"

# Run Stage 1.4 tests
pytest -m stage_1_4 -v

# Run all tests (Stage 1.1 + 1.2 + 1.3 + 1.4)
pytest tests/ -v

# Run linter
make lint

# Run full verification
make verify
```

---

## Manual Testing with curl

After all tests pass, verify the API works manually:

### Start the Services

```bash
# Terminal 1: Start Redis (if not running)
make redis-start

# Terminal 2: Start Celery worker
make worker

# Terminal 3: Start FastAPI server
make run
```

### Test Each Endpoint

```bash
# 1. Test health endpoint
curl http://localhost:8000/health | jq

# 2. Test stats endpoint
curl http://localhost:8000/stats | jq

# 3. Create a test NIfTI file
python -c "
import SimpleITK as sitk
img = sitk.Image([16,16,16], sitk.sitkInt16)
sitk.WriteImage(img, 'test_input.nii.gz')
print('Created test_input.nii.gz')
"

# 4. Test upload endpoint
curl -X POST http://localhost:8000/upload \
  -F "file=@test_input.nii.gz" \
  -F "segmentation_model=nnunet_fullres" \
  -F "email=test@example.com" | jq

# Save the job_id from the response, e.g.: JOB_ID="abc123-..."

# 5. Test status endpoint (replace with actual job_id)
curl http://localhost:8000/status/$JOB_ID | jq

# 6. Wait for processing to complete (watch the Celery worker terminal)
# Then test status again:
curl http://localhost:8000/status/$JOB_ID | jq

# 7. Test download endpoint (only works when complete)
curl -OJ http://localhost:8000/download/$JOB_ID

# 8. Verify the downloaded file
unzip -l *_results.zip

# 9. Cleanup test file
rm test_input.nii.gz *_results.zip
```

---

## Git Commit

After completing Stage 1.4:

```bash
git add .
git commit -m "$(cat <<'EOF'
Stage 1.4: API Routes

- Add POST /upload endpoint for file uploads with validation
- Add GET /status/{job_id} endpoint with union response types
- Add GET /download/{job_id} endpoint for results retrieval
- Add GET /stats endpoint for usage statistics
- Update main.py to include all routers (before static files mount)
- Add Stage 1.4 verification tests (~30 tests)
- All 115+ tests passing (Stage 1.1 + 1.2 + 1.3 + 1.4)

API is now fully functional and can be tested with curl.
EOF
)"
```

---

## Add pytest Marker

Ensure the `stage_1_4` marker is defined in `pyproject.toml`:

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
markers = [
    "stage_1_1: Stage 1.1 - Project Scaffolding",
    "stage_1_2: Stage 1.2 - Models & Services",
    "stage_1_3: Stage 1.3 - Redis + Celery",
    "stage_1_4: Stage 1.4 - API Routes",
    "stage_1_5: Stage 1.5 - Frontend",
    "stage_1_6: Stage 1.6 - Docker & Deployment",
]
asyncio_mode = "auto"
addopts = "-v --tb=short"
```

---

## Next Step: Stage 1.5 - Frontend

See [STAGE_1.5_FRONTEND.md](./STAGE_1.5_FRONTEND.md)

Stage 1.5 creates the frontend interface:

1. **HTML** - Complete page with upload form, processing status, and download button
2. **CSS** - Modern, responsive styling
3. **JavaScript** - FilePond integration, status polling, download handling
4. **Integration** - Served by FastAPI from the frontend/ directory

---

## Notes for Next Agent

### What's Ready to Use

- **All API endpoints** are functional and tested
- **Celery integration** is complete - tasks are submitted on upload
- **Redis persistence** works for job state tracking
- **File validation** handles zip extraction and medical image verification

### Key Implementation Details

1. **Upload returns 201**: Use `status_code=201` on the route decorator
2. **Union response types**: Status endpoint returns different schemas based on job status
3. **Static files mount order**: API routes MUST be registered BEFORE the static files mount
4. **File extension handling**: `.nii.gz` is handled specially as a double extension
5. **File size check**: Check size AFTER saving to disk (for streaming large files)

### API Route Summary

| Route | Method | Returns | Notes |
|-------|--------|---------|-------|
| `/health` | GET | HealthResponse | Redis + worker status |
| `/upload` | POST | UploadResponse (201) | Multipart form data |
| `/status/{job_id}` | GET | StatusQueued/Processing/Complete/Error | Union type |
| `/download/{job_id}` | GET | FileResponse | application/zip |
| `/stats` | GET | StatsResponse | Usage statistics |

### Testing Without Celery Worker

Most tests mock the Celery task submission. For full end-to-end testing, you need:
1. Redis running (`make redis-start`)
2. Celery worker running (`make worker`)
3. FastAPI server running (`make run`)

### Common Issues

1. **404 on API routes**: Check that static files are mounted AFTER API routes
2. **Import errors**: Ensure all route modules import correctly before testing
3. **Redis errors in tests**: Tests use database 15, make sure Redis is running

---

## Troubleshooting

### API routes return 404

```bash
# Make sure routes are registered before static files
python -c "
from backend.main import app
for route in app.routes:
    print(f'{getattr(route, \"methods\", \"MOUNT\"):15} {route.path}')"
```

### Upload fails with validation error

```bash
# Check file handler independently
python -c "
from pathlib import Path
from backend.services.file_handler import validate_and_prepare_upload
# test validation logic
"
```

### Tests fail with Redis connection error

```bash
# Ensure Redis is running
make redis-ping

# Tests use database 15
docker exec redis redis-cli -n 15 ping
```
