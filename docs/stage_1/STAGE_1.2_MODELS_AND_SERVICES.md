# Stage 1.2: Models & Services

## Overview

**Goal**: Create the data models (Pydantic schemas, Job dataclass) and service layer (file handling, job management, statistics) that the API routes will use.

**Estimated Time**: ~45-60 minutes

**Deliverable**: All model classes and service modules created, tested, and importable without errors.

---

## Prerequisites

**Stage 1.1 must be complete.** Verify by running:

```bash
conda activate kneepipeline
cd ~/programming/kneepipeline_segmentaton_website

# All Stage 1.1 tests should pass
pytest -m stage_1_1 -v

# Redis should be running
docker exec redis redis-cli ping  # Should return PONG

# Health endpoint should work
uvicorn backend.main:app --reload --port 8000 &
curl http://localhost:8000/health
```

See [STAGE_1.1_COMPLETED.md](./STAGE_1.1_COMPLETED.md) for details on what was created.

---

## What This Stage Covers

### 1. Pydantic Schemas (`backend/models/schemas.py`)

Request/response models for type safety and automatic validation:

| Schema | Purpose |
|--------|---------|
| `UploadOptions` | Form data fields for file upload |
| `UploadResponse` | Response after successful upload |
| `StatusQueued` | Status response when job is in queue |
| `StatusProcessing` | Status response when job is processing |
| `StatusComplete` | Status response when job is complete |
| `StatusError` | Status response when job failed |
| `StatsResponse` | Usage statistics for homepage display |

### 2. Job Model (`backend/models/job.py`)

Job dataclass with Redis persistence:

- Job state fields (id, status, progress, paths, etc.)
- `save()` - Persist job state to Redis hash
- `load()` - Load job from Redis by ID
- `get_queue_position()` - Get position in queue using Redis sorted set
- `delete_from_queue()` - Remove from queue tracking when processing starts

### 3. File Handler Service (`backend/services/file_handler.py`)

File validation and preparation:

- `validate_and_prepare_upload()` - Main entry point for processing uploads
- `_handle_zip()` - Extract zip files and find medical images
- `_find_medical_image()` - Recursively search for NIfTI, NRRD, or DICOM
- `_is_dicom_directory()` - Check if directory contains DICOM series
- `_validate_medical_image()` - Use SimpleITK to verify image is readable 3D volume

### 4. Job Service (`backend/services/job_service.py`)

Job queue management:

- `get_redis_client()` - FastAPI dependency for Redis client
- `get_estimated_wait()` - Calculate wait time based on queue position
- `get_average_processing_time()` - Rolling average of last 20 jobs
- `record_processing_time()` - Store processing duration for averaging

### 5. Statistics Service (`backend/services/statistics.py`)

Usage tracking:

- `get_statistics()` - Get all stats for homepage display
- `increment_processed_count()` - Bump counters when job completes
- `track_user_email()` - Store unique emails for user counting
- `get_all_user_emails()` - Admin function to retrieve emails

---

## Success Criteria

- [ ] All model files created with no import errors
- [ ] `python -c "from backend.models import schemas, job"` succeeds
- [ ] `python -c "from backend.services import file_handler, job_service, statistics"` succeeds
- [ ] Unit tests pass for file validation logic
- [ ] `pytest -m stage_1_2 -v` passes all tests

---

## Verification: pytest Tests

Run the Stage 1.2 tests to verify completion:

```bash
conda activate kneepipeline
cd ~/programming/kneepipeline_segmentaton_website
pytest -m stage_1_2 -v
```

**Expected:** All tests pass.

### Tests to Create: `tests/test_stage_1_2.py`

```python
"""
Stage 1.2 Verification Tests - Models & Services

Run with: pytest -m stage_1_2 -v
"""
import pytest
from pathlib import Path
import tempfile
import json

# Mark all tests in this module as stage_1_2
pytestmark = pytest.mark.stage_1_2


class TestPydanticSchemas:
    """Verify Pydantic schemas are correctly defined."""
    
    def test_schemas_importable(self):
        """All schemas should be importable."""
        from backend.models.schemas import (
            UploadOptions,
            UploadResponse,
            StatusQueued,
            StatusProcessing,
            StatusComplete,
            StatusError,
            StatsResponse,
        )
        assert UploadOptions
        assert UploadResponse
        assert StatusQueued
        assert StatusProcessing
        assert StatusComplete
        assert StatusError
        assert StatsResponse
    
    def test_upload_options_defaults(self):
        """UploadOptions should have sensible defaults."""
        from backend.models.schemas import UploadOptions
        
        options = UploadOptions()
        assert options.segmentation_model == "nnunet_fullres"
        assert options.perform_nsm is True
        assert options.nsm_type == "bone_and_cart"
        assert options.retain_results is True
        assert options.cartilage_smoothing == 0.3125
        assert options.email is None
    
    def test_upload_options_validation(self):
        """UploadOptions should validate enum values."""
        from backend.models.schemas import UploadOptions
        from pydantic import ValidationError
        
        # Valid values should work
        options = UploadOptions(segmentation_model="nnunet_cascade")
        assert options.segmentation_model == "nnunet_cascade"
        
        # Invalid values should raise ValidationError
        with pytest.raises(ValidationError):
            UploadOptions(segmentation_model="invalid_model")
    
    def test_upload_response_fields(self):
        """UploadResponse should have all required fields."""
        from backend.models.schemas import UploadResponse
        
        response = UploadResponse(
            job_id="test-123",
            status="queued",
            queue_position=1,
            estimated_wait_seconds=240,
            message="Test message"
        )
        assert response.job_id == "test-123"
        assert response.status == "queued"
        assert response.queue_position == 1
    
    def test_status_queued_fields(self):
        """StatusQueued should have correct structure."""
        from backend.models.schemas import StatusQueued
        
        status = StatusQueued(
            job_id="test-123",
            status="queued",
            queue_position=2,
            estimated_wait_seconds=480
        )
        assert status.status == "queued"
    
    def test_status_processing_fields(self):
        """StatusProcessing should have progress fields."""
        from backend.models.schemas import StatusProcessing
        
        status = StatusProcessing(
            job_id="test-123",
            status="processing",
            progress_percent=45,
            current_step=2,
            total_steps=4,
            step_name="Creating meshes",
            elapsed_seconds=60,
            estimated_remaining_seconds=90
        )
        assert status.progress_percent == 45
        assert status.step_name == "Creating meshes"
    
    def test_status_complete_fields(self):
        """StatusComplete should have download info."""
        from backend.models.schemas import StatusComplete
        
        status = StatusComplete(
            job_id="test-123",
            status="complete",
            download_url="/download/test-123",
            result_size_bytes=25000000,
            processing_time_seconds=180
        )
        assert "/download/" in status.download_url
    
    def test_status_error_fields(self):
        """StatusError should have error details."""
        from backend.models.schemas import StatusError
        
        status = StatusError(
            job_id="test-123",
            status="error",
            error_message="Invalid file format",
            error_code="INVALID_FORMAT"
        )
        assert status.error_code == "INVALID_FORMAT"
    
    def test_stats_response_fields(self):
        """StatsResponse should have all stats fields."""
        from backend.models.schemas import StatsResponse
        
        stats = StatsResponse(
            total_jobs_processed=1000,
            total_jobs_today=25,
            unique_users=150,
            average_processing_time_seconds=240,
            jobs_in_queue=3,
            uptime_hours=168.5
        )
        assert stats.total_jobs_processed == 1000


class TestJobModel:
    """Verify Job model works correctly."""
    
    def test_job_importable(self):
        """Job class should be importable."""
        from backend.models.job import Job
        assert Job
    
    def test_job_creation(self):
        """Job should be creatable with required fields."""
        from backend.models.job import Job
        
        job = Job(
            id="test-job-123",
            input_filename="test.nii.gz",
            input_path="/data/uploads/test.nii.gz",
            options={"segmentation_model": "nnunet_fullres"}
        )
        assert job.id == "test-job-123"
        assert job.status == "queued"  # Default
        assert job.progress_percent == 0
        assert job.total_steps == 4
    
    def test_job_to_dict(self):
        """Job should be serializable to dict."""
        from backend.models.job import Job
        
        job = Job(
            id="test-job-123",
            input_filename="test.nii.gz",
            input_path="/data/uploads/test.nii.gz",
            options={}
        )
        data = job.to_dict()
        assert isinstance(data, dict)
        assert data["id"] == "test-job-123"
        assert "created_at" in data
    
    def test_job_save_and_load(self, redis_client):
        """Job should save to and load from Redis."""
        from backend.models.job import Job
        
        # Create and save a job
        job = Job(
            id="redis-test-123",
            input_filename="test.nii.gz",
            input_path="/data/uploads/test.nii.gz",
            options={"model": "test"}
        )
        job.save(redis_client)
        
        # Load it back
        loaded = Job.load("redis-test-123", redis_client)
        assert loaded is not None
        assert loaded.id == job.id
        assert loaded.input_filename == job.input_filename
    
    def test_job_load_nonexistent(self, redis_client):
        """Loading nonexistent job should return None."""
        from backend.models.job import Job
        
        loaded = Job.load("nonexistent-job", redis_client)
        assert loaded is None
    
    def test_job_queue_position(self, redis_client):
        """Queue position should be trackable."""
        from backend.models.job import Job
        import time
        
        # Create multiple jobs
        jobs = []
        for i in range(3):
            job = Job(
                id=f"queue-test-{i}",
                input_filename=f"test{i}.nii.gz",
                input_path=f"/data/uploads/test{i}.nii.gz",
                options={}
            )
            job.save(redis_client)
            jobs.append(job)
            time.sleep(0.01)  # Ensure different timestamps
        
        # Check positions (1-indexed)
        assert Job.get_queue_position("queue-test-0", redis_client) == 1
        assert Job.get_queue_position("queue-test-1", redis_client) == 2
        assert Job.get_queue_position("queue-test-2", redis_client) == 3
    
    def test_job_queue_length(self, redis_client):
        """Queue length should be trackable."""
        from backend.models.job import Job
        
        # Start with empty queue
        initial_length = Job.get_queue_length(redis_client)
        
        # Add a job
        job = Job(
            id="length-test-job",
            input_filename="test.nii.gz",
            input_path="/data/uploads/test.nii.gz",
            options={}
        )
        job.save(redis_client)
        
        # Length should increase by 1
        assert Job.get_queue_length(redis_client) == initial_length + 1
    
    def test_job_delete_from_queue(self, redis_client):
        """Job should be removable from queue."""
        from backend.models.job import Job
        
        # Create and save a job
        job = Job(
            id="delete-test-job",
            input_filename="test.nii.gz",
            input_path="/data/uploads/test.nii.gz",
            options={}
        )
        job.save(redis_client)
        
        # Verify it's in queue
        assert Job.get_queue_position("delete-test-job", redis_client) > 0
        
        # Remove from queue
        job.delete_from_queue(redis_client)
        
        # Verify it's gone from queue (position 0 means not in queue)
        assert Job.get_queue_position("delete-test-job", redis_client) == 0


class TestFileHandlerService:
    """Verify file handler service works correctly."""
    
    def test_file_handler_importable(self):
        """File handler functions should be importable."""
        from backend.services.file_handler import (
            validate_and_prepare_upload,
        )
        assert validate_and_prepare_upload
    
    def test_reject_invalid_extension(self, temp_dir):
        """Should reject files with invalid extensions."""
        from backend.services.file_handler import validate_and_prepare_upload
        
        # Create a text file
        invalid_file = temp_dir / "test.txt"
        invalid_file.write_text("not a medical image")
        
        with pytest.raises(ValueError) as exc_info:
            validate_and_prepare_upload(invalid_file, temp_dir / "extracted")
        
        assert "extension" in str(exc_info.value).lower() or "valid" in str(exc_info.value).lower()
    
    def test_reject_invalid_zip(self, temp_dir):
        """Should reject invalid/corrupted zip files."""
        from backend.services.file_handler import validate_and_prepare_upload
        
        # Create a fake zip file
        fake_zip = temp_dir / "fake.zip"
        fake_zip.write_bytes(b"not a real zip file")
        
        with pytest.raises(ValueError) as exc_info:
            validate_and_prepare_upload(fake_zip, temp_dir / "extracted")
        
        assert "zip" in str(exc_info.value).lower()
    
    def test_reject_empty_zip(self, temp_dir):
        """Should reject zip files with no medical images."""
        from backend.services.file_handler import validate_and_prepare_upload
        import zipfile
        
        # Create a zip with non-medical files
        zip_path = temp_dir / "empty.zip"
        with zipfile.ZipFile(zip_path, 'w') as zf:
            zf.writestr("readme.txt", "This is not a medical image")
        
        with pytest.raises(ValueError) as exc_info:
            validate_and_prepare_upload(zip_path, temp_dir / "extracted")
        
        assert "no valid medical image" in str(exc_info.value).lower()


class TestJobService:
    """Verify job service works correctly."""
    
    def test_job_service_importable(self):
        """Job service functions should be importable."""
        from backend.services.job_service import (
            get_redis_client,
            get_estimated_wait,
            get_average_processing_time,
            record_processing_time,
        )
        assert get_redis_client
        assert get_estimated_wait
    
    def test_average_processing_time_default(self, redis_client):
        """Should return default time when no history."""
        from backend.services.job_service import get_average_processing_time
        
        # Clear any existing times
        redis_client.delete("processing_times")
        
        avg = get_average_processing_time(redis_client)
        assert avg == 240  # Default 4 minutes
    
    def test_record_and_average_processing_time(self, redis_client):
        """Should correctly calculate average processing time."""
        from backend.services.job_service import (
            get_average_processing_time,
            record_processing_time,
        )
        
        # Clear existing times
        redis_client.delete("processing_times")
        
        # Record some times
        record_processing_time(100, redis_client)
        record_processing_time(200, redis_client)
        record_processing_time(300, redis_client)
        
        # Average should be (100 + 200 + 300) / 3 = 200
        avg = get_average_processing_time(redis_client)
        assert avg == 200.0
    
    def test_estimated_wait(self, redis_client):
        """Should estimate wait time based on queue position."""
        from backend.services.job_service import (
            get_estimated_wait,
            record_processing_time,
        )
        
        # Clear and set known processing time
        redis_client.delete("processing_times")
        record_processing_time(120, redis_client)  # 2 minutes
        
        # Position 3 should wait ~6 minutes (360 seconds)
        wait = get_estimated_wait(3, redis_client)
        assert wait == 360


class TestStatisticsService:
    """Verify statistics service works correctly."""
    
    def test_statistics_importable(self):
        """Statistics functions should be importable."""
        from backend.services.statistics import (
            get_statistics,
            increment_processed_count,
            track_user_email,
        )
        assert get_statistics
        assert increment_processed_count
        assert track_user_email
    
    def test_get_statistics_structure(self, redis_client):
        """Statistics should return expected structure."""
        from backend.services.statistics import get_statistics
        
        stats = get_statistics(redis_client)
        
        assert "total_processed" in stats
        assert "today_processed" in stats
        assert "unique_users" in stats
        assert "avg_processing_time" in stats
        assert "uptime_hours" in stats
    
    def test_increment_processed_count(self, redis_client):
        """Should increment job counters."""
        from backend.services.statistics import (
            get_statistics,
            increment_processed_count,
        )
        
        initial = get_statistics(redis_client)
        increment_processed_count(redis_client)
        updated = get_statistics(redis_client)
        
        assert updated["total_processed"] == initial["total_processed"] + 1
    
    def test_track_user_email(self, redis_client):
        """Should track unique user emails."""
        from backend.services.statistics import (
            get_statistics,
            track_user_email,
        )
        
        initial = get_statistics(redis_client)
        
        # Track a new email
        track_user_email("test@example.com", redis_client)
        updated = get_statistics(redis_client)
        
        assert updated["unique_users"] >= initial["unique_users"]
    
    def test_email_deduplication(self, redis_client):
        """Same email should only count once."""
        from backend.services.statistics import (
            get_statistics,
            track_user_email,
        )
        
        # Track same email multiple times
        track_user_email("duplicate@example.com", redis_client)
        count1 = get_statistics(redis_client)["unique_users"]
        
        track_user_email("duplicate@example.com", redis_client)
        count2 = get_statistics(redis_client)["unique_users"]
        
        # Count should not increase
        assert count1 == count2
    
    def test_email_case_insensitive(self, redis_client):
        """Email tracking should be case-insensitive."""
        from backend.services.statistics import (
            get_statistics,
            track_user_email,
        )
        
        track_user_email("CaseSensitive@Example.COM", redis_client)
        count1 = get_statistics(redis_client)["unique_users"]
        
        track_user_email("casesensitive@example.com", redis_client)
        count2 = get_statistics(redis_client)["unique_users"]
        
        # Should be treated as same user
        assert count1 == count2


class TestModelsInit:
    """Verify models __init__.py exports correctly."""
    
    def test_models_package_structure(self):
        """Models package should be importable."""
        from backend import models
        assert models


class TestServicesInit:
    """Verify services __init__.py exports correctly."""
    
    def test_services_package_structure(self):
        """Services package should be importable."""
        from backend import services
        assert services
```

### Add Redis Fixture to `tests/conftest.py`

Update the `conftest.py` file to include the Redis fixture needed by Stage 1.2 tests:

```python
import pytest
from pathlib import Path
import tempfile
import redis


@pytest.fixture
def temp_dir():
    """Create a temporary directory for test files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def redis_client():
    """
    Get a Redis client for testing.
    Uses database 15 (separate from production db 0) and flushes before/after tests.
    """
    client = redis.Redis(host='localhost', port=6379, db=15, decode_responses=True)
    client.flushdb()  # Clean before test
    yield client
    client.flushdb()  # Clean after test
    client.close()
```

### Update `pyproject.toml` pytest markers

Ensure the `stage_1_2` marker is defined (should already be there from Stage 1.1):

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

## Detailed Implementation

### Step 1: Create Pydantic Schemas

**File**: `backend/models/schemas.py`

```python
"""
Pydantic schemas for request/response validation.

These schemas define the API contract and provide automatic validation.
"""
from pydantic import BaseModel, Field
from typing import Optional, Literal
from datetime import datetime


# Type aliases for Literal types
SegmentationModel = Literal[
    "nnunet_fullres", "nnunet_cascade", 
    "goyal_sagittal", "goyal_coronal", "goyal_axial", "staple"
]

NsmType = Literal["bone_and_cart", "bone_only", "both"]

JobStatus = Literal["queued", "processing", "complete", "error"]


class UploadOptions(BaseModel):
    """Options submitted with file upload."""
    email: Optional[str] = Field(
        default=None, 
        description="Optional email for tracking and notifications"
    )
    segmentation_model: SegmentationModel = Field(
        default="nnunet_fullres",
        description="Segmentation model to use"
    )
    perform_nsm: bool = Field(
        default=True,
        description="Whether to perform Neural Shape Modeling"
    )
    nsm_type: NsmType = Field(
        default="bone_and_cart",
        description="Type of NSM analysis to perform"
    )
    retain_results: bool = Field(
        default=True,
        description="Allow anonymized results to be retained for research"
    )
    cartilage_smoothing: float = Field(
        default=0.3125, 
        ge=0.0, 
        le=1.0,
        description="Cartilage smoothing parameter (not exposed in UI)"
    )


class UploadResponse(BaseModel):
    """Response after successful file upload."""
    job_id: str
    status: JobStatus
    queue_position: int
    estimated_wait_seconds: int
    message: str


class StatusQueued(BaseModel):
    """Status response when job is waiting in queue."""
    job_id: str
    status: Literal["queued"]
    queue_position: int
    estimated_wait_seconds: int


class StatusProcessing(BaseModel):
    """Status response when job is actively processing."""
    job_id: str
    status: Literal["processing"]
    progress_percent: int = Field(ge=0, le=100)
    current_step: int
    total_steps: int
    step_name: str
    elapsed_seconds: int
    estimated_remaining_seconds: int


class StatusComplete(BaseModel):
    """Status response when job has completed successfully."""
    job_id: str
    status: Literal["complete"]
    download_url: str
    result_size_bytes: int
    processing_time_seconds: int


class StatusError(BaseModel):
    """Status response when job has failed."""
    job_id: str
    status: Literal["error"]
    error_message: str
    error_code: str


class StatsResponse(BaseModel):
    """Usage statistics for homepage display."""
    total_jobs_processed: int
    total_jobs_today: int
    unique_users: int
    average_processing_time_seconds: int
    jobs_in_queue: int
    uptime_hours: float
```

---

### Step 2: Create Job Model

**File**: `backend/models/job.py`

```python
"""
Job model with Redis persistence.

The Job dataclass represents a processing job and handles its persistence to Redis.
Queue position is tracked using Redis sorted sets for efficient ordering.
"""
from dataclasses import dataclass, asdict, field
from datetime import datetime
from typing import Optional
import json
import redis


@dataclass
class Job:
    """
    Represents a processing job in the pipeline.
    
    Attributes:
        id: Unique job identifier (UUID)
        input_filename: Original filename uploaded by user
        input_path: Path to the validated input file
        options: Processing options dict
        status: Current job status (queued, processing, complete, error)
        created_at: ISO timestamp when job was created
        started_at: ISO timestamp when processing started
        completed_at: ISO timestamp when processing finished
        progress_percent: Current progress (0-100)
        current_step: Current processing step number
        total_steps: Total number of processing steps
        step_name: Human-readable name of current step
        result_path: Path to results zip file (when complete)
        result_size_bytes: Size of results file in bytes
        error_message: Error description (when failed)
        error_code: Error code for categorization
        retain_for_research: Whether user consented to research retention
        email: Optional user email for tracking/notifications
    """
    id: str
    input_filename: str
    input_path: str
    options: dict
    status: str = "queued"
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    progress_percent: int = 0
    current_step: int = 0
    total_steps: int = 4
    step_name: str = ""
    result_path: Optional[str] = None
    result_size_bytes: Optional[int] = None
    error_message: Optional[str] = None
    error_code: Optional[str] = None
    retain_for_research: bool = True
    email: Optional[str] = None
    
    def to_dict(self) -> dict:
        """Convert job to dictionary for serialization."""
        return asdict(self)
    
    def save(self, redis_client: redis.Redis) -> None:
        """
        Persist job state to Redis.
        
        Jobs are stored in a hash (jobs -> job_id -> job_json).
        Queued jobs are also tracked in a sorted set (job_queue) for position tracking.
        """
        # Save to hash
        redis_client.hset("jobs", self.id, json.dumps(self.to_dict()))
        
        # Track in queue if status is queued
        if self.status == "queued":
            # Use created_at timestamp as score for FIFO ordering
            score = datetime.fromisoformat(self.created_at).timestamp()
            redis_client.zadd("job_queue", {self.id: score})
    
    def delete_from_queue(self, redis_client: redis.Redis) -> None:
        """Remove job from queue tracking (called when processing starts)."""
        redis_client.zrem("job_queue", self.id)
    
    @classmethod
    def load(cls, job_id: str, redis_client: redis.Redis) -> Optional["Job"]:
        """
        Load job from Redis by ID.
        
        Returns None if job doesn't exist.
        """
        data = redis_client.hget("jobs", job_id)
        if data:
            return cls(**json.loads(data))
        return None
    
    @classmethod
    def get_queue_position(cls, job_id: str, redis_client: redis.Redis) -> int:
        """
        Get 1-indexed position in queue.
        
        Returns 0 if job is not in queue (already processing or complete).
        """
        rank = redis_client.zrank("job_queue", job_id)
        return rank + 1 if rank is not None else 0
    
    @classmethod
    def get_queue_length(cls, redis_client: redis.Redis) -> int:
        """Get total number of jobs currently in queue."""
        return redis_client.zcard("job_queue")
```

---

### Step 3: Create File Handler Service

**File**: `backend/services/file_handler.py`

```python
"""
File handling service for upload validation and preparation.

Handles:
- File extension validation
- Zip extraction
- Medical image discovery (NIfTI, NRRD, DICOM)
- SimpleITK validation of image readability
"""
from pathlib import Path
import shutil
import zipfile
from typing import Optional


# Valid medical image extensions
VALID_EXTENSIONS = {'.nii', '.nii.gz', '.nrrd', '.dcm', '.zip'}


def validate_and_prepare_upload(upload_path: Path, temp_dir: Path) -> Path:
    """
    Process uploaded file: validate extension, extract if zip, validate medical image.
    
    Args:
        upload_path: Path to the uploaded file
        temp_dir: Directory for extracting zip contents
        
    Returns:
        Path to the validated medical image (file or DICOM directory)
        
    Raises:
        ValueError: If file is invalid or no medical image found
    """
    # Check extension
    suffix = upload_path.suffix.lower()
    if upload_path.name.endswith('.nii.gz'):
        suffix = '.nii.gz'
    
    if suffix not in VALID_EXTENSIONS:
        raise ValueError(
            f"Invalid file extension '{suffix}'. "
            f"Accepted formats: {', '.join(sorted(VALID_EXTENSIONS))}"
        )
    
    temp_dir.mkdir(parents=True, exist_ok=True)
    
    if suffix == '.zip':
        return _handle_zip(upload_path, temp_dir)
    else:
        return _validate_medical_image(upload_path)


def _handle_zip(zip_path: Path, extract_dir: Path) -> Path:
    """
    Extract zip and find medical image inside.
    
    Args:
        zip_path: Path to the zip file
        extract_dir: Directory to extract contents to
        
    Returns:
        Path to the medical image found in the zip
        
    Raises:
        ValueError: If zip is invalid or contains no medical images
    """
    try:
        with zipfile.ZipFile(zip_path, 'r') as zf:
            zf.extractall(extract_dir)
    except zipfile.BadZipFile:
        raise ValueError("Invalid or corrupted zip file")
    
    # Search for medical images in extracted contents
    medical_image = _find_medical_image(extract_dir)
    if not medical_image:
        raise ValueError(
            "No valid medical image found in zip file. "
            "Expected: .nii, .nii.gz, .nrrd, or DICOM series folder"
        )
    
    return medical_image


def _find_medical_image(directory: Path) -> Optional[Path]:
    """
    Recursively search for a medical image file or DICOM directory.
    
    Search order:
    1. NIfTI files (.nii.gz, .nii)
    2. NRRD files (.nrrd)
    3. DICOM directories (containing 10+ .dcm files)
    4. Single DICOM files (.dcm)
    
    Args:
        directory: Directory to search
        
    Returns:
        Path to the medical image, or None if not found
    """
    # First, look for NIfTI files (preferred)
    for pattern in ['*.nii.gz', '*.nii']:
        matches = list(directory.rglob(pattern))
        if matches:
            return matches[0]
    
    # Look for NRRD files
    nrrd_matches = list(directory.rglob('*.nrrd'))
    if nrrd_matches:
        return nrrd_matches[0]
    
    # Look for DICOM directories (folder with multiple .dcm files)
    for subdir in directory.rglob('*'):
        if subdir.is_dir() and _is_dicom_directory(subdir):
            return subdir
    
    # Check for single 3D DICOM file
    dcm_files = list(directory.rglob('*.dcm'))
    if dcm_files:
        return dcm_files[0]
    
    return None


def _is_dicom_directory(path: Path) -> bool:
    """
    Check if directory contains a DICOM series (multiple .dcm files).
    
    Requires at least 10 slices to be considered a valid 3D series.
    """
    if not path.is_dir():
        return False
    dcm_files = list(path.glob('*.dcm'))
    return len(dcm_files) >= 10


def _validate_medical_image(path: Path) -> Path:
    """
    Validate that path is a readable 3D medical image using SimpleITK.
    
    Args:
        path: Path to the image file or DICOM directory
        
    Returns:
        The input path if validation passes
        
    Raises:
        ValueError: If image cannot be read or is not 3D
    """
    try:
        import SimpleITK as sitk
        
        if path.is_dir():
            # DICOM series - folder with multiple slices
            reader = sitk.ImageSeriesReader()
            dicom_files = reader.GetGDCMSeriesFileNames(str(path))
            
            if not dicom_files:
                raise ValueError("No DICOM files found in directory")
            
            if len(dicom_files) < 10:
                raise ValueError(
                    f"DICOM series too short ({len(dicom_files)} slices). "
                    "Expected 3D volume with at least 10 slices."
                )
            
            # Try to read series info to validate
            reader.SetFileNames(dicom_files)
            reader.ReadImageInformation()
            
        else:
            # Single file (NIfTI, NRRD, or single 3D DICOM)
            reader = sitk.ImageFileReader()
            reader.SetFileName(str(path))
            reader.ReadImageInformation()
            
            # Check dimensions (should be 3D)
            dims = reader.GetDimension()
            if dims < 3:
                raise ValueError(
                    f"Image is {dims}D, expected 3D volume. "
                    "Please upload a 3D MRI scan."
                )
            
            # Check size is reasonable
            size = reader.GetSize()
            if any(s < 10 for s in size[:3]):
                raise ValueError(
                    f"Image dimensions too small: {size}. "
                    "Expected a full 3D MRI volume."
                )
        
        return path
        
    except ImportError:
        raise ValueError("SimpleITK not installed - cannot validate medical image")
    except Exception as e:
        if "ValueError" in type(e).__name__:
            raise
        raise ValueError(f"Failed to read medical image: {str(e)}")
```

---

### Step 4: Create Job Service

**File**: `backend/services/job_service.py`

```python
"""
Job queue management service.

Provides Redis client dependency and queue-related calculations.
"""
import redis
from fastapi import Depends
from ..config import get_settings, Settings


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
```

---

### Step 5: Create Statistics Service

**File**: `backend/services/statistics.py`

```python
"""
Usage statistics tracking service.

Tracks:
- Total jobs processed (all time)
- Jobs processed today
- Unique users (by email)
- Processing time averages
- Application uptime
"""
import redis
from datetime import datetime, date
import hashlib


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
```

---

### Step 6: Update Package Init Files

**File**: `backend/models/__init__.py`

```python
"""
Models package - Pydantic schemas and Job dataclass.
"""
from .schemas import (
    UploadOptions,
    UploadResponse,
    StatusQueued,
    StatusProcessing,
    StatusComplete,
    StatusError,
    StatsResponse,
)
from .job import Job

__all__ = [
    "UploadOptions",
    "UploadResponse",
    "StatusQueued",
    "StatusProcessing",
    "StatusComplete",
    "StatusError",
    "StatsResponse",
    "Job",
]
```

**File**: `backend/services/__init__.py`

```python
"""
Services package - Business logic for file handling, jobs, and statistics.
"""
from .file_handler import validate_and_prepare_upload
from .job_service import (
    get_redis_client,
    get_estimated_wait,
    get_average_processing_time,
    record_processing_time,
)
from .statistics import (
    get_statistics,
    increment_processed_count,
    track_user_email,
    get_all_user_emails,
)

__all__ = [
    # File handler
    "validate_and_prepare_upload",
    # Job service
    "get_redis_client",
    "get_estimated_wait",
    "get_average_processing_time",
    "record_processing_time",
    # Statistics
    "get_statistics",
    "increment_processed_count",
    "track_user_email",
    "get_all_user_emails",
]
```

---

### Step 7: Update conftest.py

**File**: `tests/conftest.py`

Add the Redis and temp_dir fixtures:

```python
"""
Shared pytest fixtures for all test modules.
"""
import pytest
from pathlib import Path
import tempfile
import redis


@pytest.fixture
def temp_dir():
    """Create a temporary directory for test files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def redis_client():
    """
    Get a Redis client for testing.
    
    Uses database 15 (separate from production db 0) and flushes before/after tests.
    Requires Redis to be running on localhost:6379.
    """
    client = redis.Redis(host='localhost', port=6379, db=15, decode_responses=True)
    client.flushdb()  # Clean before test
    yield client
    client.flushdb()  # Clean after test
    client.close()
```

---

## Expected Final State

After completing Stage 1.2, your project should have:

```
backend/
├── __init__.py
├── main.py                      # (unchanged from Stage 1.1)
├── config.py                    # (unchanged from Stage 1.1)
├── requirements.txt             # (unchanged from Stage 1.1)
├── routes/
│   ├── __init__.py
│   └── health.py                # (unchanged from Stage 1.1)
├── services/
│   ├── __init__.py              # NEW: exports all service functions
│   ├── file_handler.py          # NEW: file validation
│   ├── job_service.py           # NEW: queue management
│   └── statistics.py            # NEW: usage tracking
├── workers/
│   └── __init__.py              # (empty, for Stage 1.3)
└── models/
    ├── __init__.py              # NEW: exports all models
    ├── schemas.py               # NEW: Pydantic schemas
    └── job.py                   # NEW: Job dataclass

tests/
├── __init__.py
├── conftest.py                  # UPDATED: added redis_client and temp_dir fixtures
├── test_stage_1_1.py            # (unchanged)
└── test_stage_1_2.py            # NEW: Stage 1.2 verification tests
```

---

## Verification Commands

```bash
# Activate environment
conda activate kneepipeline
cd ~/programming/kneepipeline_segmentaton_website

# Verify imports work
python -c "from backend.models import schemas, job; print('Models OK')"
python -c "from backend.services import file_handler, job_service, statistics; print('Services OK')"

# Run Stage 1.2 tests
pytest -m stage_1_2 -v

# Run all tests (Stage 1.1 + 1.2)
pytest tests/ -v

# Run linter
ruff check backend/ tests/
```

---

## Git Commit

After completing Stage 1.2:

```bash
git add .
git commit -m "Stage 1.2: Models and services

- Add Pydantic schemas for all API request/response types
- Add Job model with Redis persistence and queue tracking
- Add file handler service for upload validation
- Add job service for queue position calculations
- Add statistics service for usage tracking
- Add Stage 1.2 verification tests"
```

---

## Next Step: Stage 1.3 - Redis & Celery

See [STAGE_1.3_REDIS_AND_CELERY.md](./STAGE_1.3_REDIS_AND_CELERY.md)

Stage 1.3 will create:
1. Celery app configuration (`backend/workers/celery_app.py`)
2. Celery tasks (`backend/workers/tasks.py`)
3. Dummy pipeline worker (`backend/workers/dummy_worker.py`)
4. Tests verifying Celery task execution

---

## Notes for Next Agent

- The models and services created here are **not yet used by routes**. Routes will be created in Stage 1.4.
- The `file_handler.py` uses SimpleITK for validation - ensure the `kneepipeline` conda environment is active.
- Redis must be running for tests to pass. Start with: `docker start redis`
- All code follows the patterns established in `docs/STAGE_1_DETAILED_PLAN.md`.
- The `get_redis_client` function in `job_service.py` is designed to work as a FastAPI dependency.
