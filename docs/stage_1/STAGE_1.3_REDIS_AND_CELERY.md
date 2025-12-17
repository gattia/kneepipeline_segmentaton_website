# Stage 1.3: Redis + Celery Setup

## Overview

**Goal**: Create Celery configuration, task definitions, and a dummy worker that processes jobs and creates output files.

**Estimated Time**: ~30-45 minutes

**Deliverable**: A working Celery worker that can execute tasks, update job status in Redis, and produce a dummy results zip file.

---

## Prerequisites

**Stage 1.2 must be complete.** Verify by running:

```bash
conda activate kneepipeline
cd ~/programming/kneepipeline_segmentaton_website

# All Stage 1.1 and 1.2 tests should pass
make verify

# Redis should be running
make redis-ping  # Should return PONG

# Models and services should be importable
python -c "from backend.models import Job; print('Job model OK')"
python -c "from backend.services import record_processing_time, increment_processed_count; print('Services OK')"
```

See [STAGE_1.2_COMPLETED.md](./STAGE_1.2_COMPLETED.md) for details on what was created.

---

## What This Stage Creates

### New Files

```
backend/workers/
├── __init__.py              # UPDATE: export celery_app, REDIS_URL, and tasks
├── celery_app.py            # NEW: Celery configuration + REDIS_URL export
├── tasks.py                 # NEW: process_pipeline task
└── dummy_worker.py          # NEW: Dummy processing function

tests/
└── test_stage_1_3.py        # NEW: Stage 1.3 verification tests
```

### Components

| File | Purpose |
|------|---------|
| `celery_app.py` | Celery app with Redis broker/backend, worker settings. **Exports `REDIS_URL`** |
| `tasks.py` | `process_pipeline` task that updates job status through steps. **Imports `REDIS_URL` from celery_app** |
| `dummy_worker.py` | Creates zeroed image copy, dummy JSON/CSV, and results zip. **Has `simulate_delay` parameter for tests** |
| `test_stage_1_3.py` | 20+ tests verifying Celery configuration and task execution. **Uses fixtures from conftest.py** |

---

## Design Decisions (Avoiding Redundancy)

These design decisions prevent code duplication and improve maintainability:

### 1. Centralized REDIS_URL
- **Defined once** in `celery_app.py`
- **Imported** by `tasks.py` (not re-read from environment)
- Avoids duplicate `os.getenv()` calls that could diverge

### 2. Two Redis Client Functions (Intentional)
| Function | Location | Use When |
|----------|----------|----------|
| `get_redis_client()` | `job_service.py` | In FastAPI route handlers (uses `Depends()`) |
| `get_redis_client()` | `tasks.py` | In Celery tasks (standalone, no FastAPI context) |

These are **intentionally separate** because FastAPI's `Depends()` pattern doesn't work inside Celery workers.

### 3. Shared Test Fixtures
- `temp_dir` and `redis_client` fixtures are in `tests/conftest.py`
- Test files **do not redefine** these fixtures
- All tests share the same fixture implementations

### 4. Configurable Delays in Dummy Worker
- `simulate_delay=True` (default): Adds realistic delays for manual testing
- `simulate_delay=False`: Skips delays for fast automated test execution
- Tests should always use `simulate_delay=False`

---

## Success Criteria

- [ ] `make worker` starts Celery worker without errors
- [ ] Celery app is importable: `python -c "from backend.workers.celery_app import celery_app; print(celery_app)"`
- [ ] Tasks are importable: `python -c "from backend.workers.tasks import process_pipeline; print(process_pipeline)"`
- [ ] Dummy worker is importable: `python -c "from backend.workers.dummy_worker import dummy_pipeline; print('OK')"`
- [ ] All Stage 1.3 tests pass: `pytest -m stage_1_3 -v`
- [ ] Task can be submitted and completes (manual verification)

---

## Verification: pytest Tests

Run the Stage 1.3 tests to verify completion:

```bash
conda activate kneepipeline
cd ~/programming/kneepipeline_segmentaton_website
pytest -m stage_1_3 -v
```

**Expected:** All tests pass.

---

## Detailed Implementation

### Step 1: Create Celery Configuration

**File**: `backend/workers/celery_app.py`

> **Note**: This module exports `REDIS_URL` which is imported by `tasks.py` to avoid duplicating the environment variable read.

```python
"""
Celery application configuration.

This module configures Celery with Redis as both the message broker
and result backend. It's designed for single-worker GPU processing.

Exports:
    celery_app: The configured Celery application instance
    REDIS_URL: Redis connection URL (used by tasks.py for Redis client)
"""
import os

from celery import Celery

# Redis URL from environment or default
# NOTE: This is exported and imported by tasks.py to avoid duplication
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

# Create Celery app
celery_app = Celery(
    "knee_pipeline",
    broker=REDIS_URL,
    backend=REDIS_URL,
    include=["backend.workers.tasks"]
)

# Celery configuration
celery_app.conf.update(
    # Serialization
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    
    # Timezone
    timezone="UTC",
    enable_utc=True,
    
    # Task tracking - allows us to see when task starts
    task_track_started=True,
    
    # Single worker for GPU constraint (one job at a time)
    worker_concurrency=1,
    
    # Acknowledge after completion (handles crashes gracefully)
    # If worker crashes mid-task, task will be requeued
    task_acks_late=True,
    
    # Prefetch only 1 task at a time (important for GPU memory)
    worker_prefetch_multiplier=1,
    
    # Retry configuration
    task_default_retry_delay=60,  # Wait 60s before retry
    task_max_retries=2,           # Max 2 retries
    
    # Result expiration (24 hours)
    result_expires=86400,
    
    # Don't store successful task results (we use Redis directly for job status)
    task_ignore_result=False,
)
```

---

### Step 2: Create Dummy Worker

**File**: `backend/workers/dummy_worker.py`

```python
"""
Dummy pipeline worker for Phase 1 development.

This module simulates the real processing pipeline by:
1. Validating the input is a readable medical image
2. Creating a zeroed copy of the image
3. Generating dummy results JSON and CSV
4. Packaging everything into a results zip file

The real pipeline will replace this in Phase 3.
"""
import json
import shutil
import time
from pathlib import Path
from typing import Callable, Optional


def dummy_pipeline(
    input_path: str,
    options: dict,
    output_dir: Path,
    progress_callback: Optional[Callable[[int, int, str], None]] = None,
    simulate_delay: bool = True
) -> Path:
    """
    Dummy worker for Phase 1 development.
    
    Creates a zeroed copy of the input image and packages results.
    Simulates processing time for realistic UX testing.
    
    Args:
        input_path: Path to the validated medical image
        options: Processing options from user
        output_dir: Directory to save results
        progress_callback: Optional callback(step, total_steps, step_name) for progress updates
        simulate_delay: If True, adds time.sleep() calls to simulate real processing time.
                       Set to False for faster test execution. Default: True.
        
    Returns:
        Path to the results zip file
        
    Raises:
        ValueError: If input cannot be read
        RuntimeError: If processing fails
    """
    import SimpleITK as sitk
    
    input_path = Path(input_path)
    
    # Create output directory
    results_dir = output_dir / "results"
    results_dir.mkdir(parents=True, exist_ok=True)
    
    def update_progress(step: int, total: int, name: str):
        """Helper to call progress callback if provided."""
        if progress_callback:
            progress_callback(step, total, name)
    
    def maybe_sleep(seconds: float):
        """Sleep only if simulate_delay is enabled (for faster tests)."""
        if simulate_delay:
            time.sleep(seconds)
    
    total_steps = 4
    
    # Step 1: Validate input
    update_progress(1, total_steps, "Validating input")
    maybe_sleep(1)  # Simulate work
    
    # Load the image
    try:
        if input_path.is_dir():
            # DICOM series
            reader = sitk.ImageSeriesReader()
            dicom_files = reader.GetGDCMSeriesFileNames(str(input_path))
            if not dicom_files:
                raise ValueError("No DICOM files found in directory")
            reader.SetFileNames(dicom_files)
            img = reader.Execute()
        else:
            # Single file (NIfTI, NRRD, or single DICOM)
            img = sitk.ReadImage(str(input_path))
    except Exception as e:
        raise ValueError(f"Failed to read input image: {e}")
    
    # Step 2: Process image (create zeroed copy)
    update_progress(2, total_steps, "Processing image")
    maybe_sleep(2)  # Simulate processing
    
    # Create zeroed copy (same dimensions/metadata, all zeros)
    zeroed = sitk.Image(img.GetSize(), img.GetPixelID())
    zeroed.CopyInformation(img)
    
    # Step 3: Generate results
    update_progress(3, total_steps, "Generating results")
    maybe_sleep(1)  # Simulate work
    
    # Determine input stem for naming
    input_stem = input_path.stem
    if input_path.suffix == '.gz':
        input_stem = Path(input_stem).stem  # Remove .nii from .nii.gz
    if input_path.is_dir():
        input_stem = input_path.name  # Use directory name for DICOM
    
    # Save zeroed image as "segmentation"
    sitk.WriteImage(zeroed, str(results_dir / "dummy_segmentation.nii.gz"))
    
    # Create dummy results JSON
    results_summary = {
        "status": "dummy_processing",
        "phase": "Phase 1 MVP",
        "input_file": input_path.name,
        "input_dimensions": list(img.GetSize()),
        "input_spacing": list(img.GetSpacing()),
        "options": options,
        "message": (
            "This is a dummy result from Phase 1 development. "
            "Real processing will be enabled in Phase 3."
        ),
        "dummy_metrics": {
            "femur_cartilage_thickness_mm": 2.45,
            "tibia_cartilage_thickness_mm": 2.12,
            "patella_cartilage_thickness_mm": 2.89,
            "bscore": -0.5,
            "note": "These are placeholder values"
        }
    }
    
    with open(results_dir / "results.json", "w") as f:
        json.dump(results_summary, f, indent=2)
    
    # Create dummy CSV
    csv_content = """region,mean_thickness_mm,std_thickness_mm,min_thickness_mm,max_thickness_mm,n_points
femur_medial,2.45,0.32,1.82,3.21,1500
femur_lateral,2.38,0.28,1.75,3.15,1400
tibia_medial,2.12,0.25,1.55,2.85,1200
tibia_lateral,2.08,0.22,1.48,2.78,1100
patella,2.89,0.35,2.10,3.65,800
"""
    with open(results_dir / "results.csv", "w") as f:
        f.write(csv_content)
    
    # Step 4: Package results
    update_progress(4, total_steps, "Packaging output")
    maybe_sleep(0.5)  # Simulate work
    
    # Create zip archive
    zip_path = shutil.make_archive(
        str(output_dir / f"{input_stem}_results"),
        'zip',
        results_dir
    )
    
    return Path(zip_path)
```

---

### Step 3: Create Celery Tasks

**File**: `backend/workers/tasks.py`

> **Note**: This module imports `REDIS_URL` from `celery_app.py` to avoid duplicating the environment variable read. The `get_redis_client()` function here is separate from the one in `job_service.py` because that one uses FastAPI's `Depends()` pattern which doesn't work inside Celery tasks.

```python
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
from pathlib import Path

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
            "duration_seconds": duration
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
```

---

### Step 4: Update Workers Package Init

**File**: `backend/workers/__init__.py`

```python
"""
Workers package - Celery app and task definitions.

Exports:
    celery_app: The configured Celery application
    REDIS_URL: Redis connection URL (for creating Redis clients in tasks)
    process_pipeline: Main processing Celery task
    dummy_pipeline: Phase 1 dummy processing function
"""
from .celery_app import REDIS_URL, celery_app
from .dummy_worker import dummy_pipeline
from .tasks import process_pipeline

__all__ = [
    "celery_app",
    "REDIS_URL",
    "process_pipeline",
    "dummy_pipeline",
]
```

---

### Step 5: Create Stage 1.3 Tests

**File**: `tests/test_stage_1_3.py`

```python
"""
Stage 1.3 Verification Tests - Redis + Celery

Run with: pytest -m stage_1_3 -v

These tests verify:
1. Celery app configuration
2. Task definitions
3. Dummy worker functionality
4. Integration with Job model and services
"""
import json
import tempfile
import time
from pathlib import Path

import pytest

# Mark all tests in this module as stage_1_3
pytestmark = pytest.mark.stage_1_3


class TestCeleryAppConfiguration:
    """Verify Celery app is correctly configured."""
    
    def test_celery_app_importable(self):
        """Celery app should be importable."""
        from backend.workers.celery_app import celery_app
        assert celery_app is not None
    
    def test_celery_app_name(self):
        """Celery app should have correct name."""
        from backend.workers.celery_app import celery_app
        assert celery_app.main == "knee_pipeline"
    
    def test_celery_uses_redis_broker(self):
        """Celery should use Redis as broker."""
        from backend.workers.celery_app import celery_app
        broker_url = celery_app.conf.broker_url
        assert broker_url is not None
        assert "redis" in broker_url
    
    def test_celery_uses_redis_backend(self):
        """Celery should use Redis as result backend."""
        from backend.workers.celery_app import celery_app
        backend = str(celery_app.conf.result_backend)
        assert "redis" in backend
    
    def test_celery_single_concurrency(self):
        """Celery should be configured for single worker (GPU constraint)."""
        from backend.workers.celery_app import celery_app
        assert celery_app.conf.worker_concurrency == 1
    
    def test_celery_task_tracking_enabled(self):
        """Celery should track task started state."""
        from backend.workers.celery_app import celery_app
        assert celery_app.conf.task_track_started is True
    
    def test_celery_late_ack(self):
        """Celery should acknowledge after task completion."""
        from backend.workers.celery_app import celery_app
        assert celery_app.conf.task_acks_late is True
    
    def test_celery_json_serialization(self):
        """Celery should use JSON serialization."""
        from backend.workers.celery_app import celery_app
        assert celery_app.conf.task_serializer == "json"
        assert "json" in celery_app.conf.accept_content


class TestCeleryTasks:
    """Verify Celery tasks are correctly defined."""
    
    def test_process_pipeline_importable(self):
        """process_pipeline task should be importable."""
        from backend.workers.tasks import process_pipeline
        assert process_pipeline is not None
    
    def test_process_pipeline_is_celery_task(self):
        """process_pipeline should be a Celery task."""
        from backend.workers.tasks import process_pipeline
        # Celery tasks have a 'delay' method
        assert hasattr(process_pipeline, 'delay')
        assert hasattr(process_pipeline, 'apply_async')
    
    def test_process_pipeline_bound(self):
        """process_pipeline should be bound (access to self)."""
        from backend.workers.tasks import process_pipeline
        # Bound tasks have bind=True, accessible via task property
        assert process_pipeline.bind is True
    
    def test_process_pipeline_max_retries(self):
        """process_pipeline should have retry configuration."""
        from backend.workers.tasks import process_pipeline
        assert process_pipeline.max_retries == 2
    
    def test_tasks_registered_with_celery(self):
        """Tasks should be registered with Celery app."""
        from backend.workers.celery_app import celery_app
        registered_tasks = list(celery_app.tasks.keys())
        # Filter out built-in celery tasks
        custom_tasks = [t for t in registered_tasks if 'backend.workers' in t]
        assert len(custom_tasks) >= 1
        assert any('process_pipeline' in t for t in custom_tasks)


class TestDummyWorker:
    """Verify dummy worker functionality."""
    
    def test_dummy_pipeline_importable(self):
        """dummy_pipeline should be importable."""
        from backend.workers.dummy_worker import dummy_pipeline
        assert dummy_pipeline is not None
    
    def test_dummy_pipeline_creates_output_dir(self, temp_dir):
        """dummy_pipeline should create output directory."""
        from backend.workers.dummy_worker import dummy_pipeline
        
        # Create a minimal valid NIfTI file
        input_file = _create_test_nifti(temp_dir / "input")
        output_dir = temp_dir / "output"
        
        result = dummy_pipeline(
            input_path=str(input_file),
            options={"segmentation_model": "nnunet_fullres"},
            output_dir=output_dir,
            simulate_delay=False  # Fast test execution
        )
        
        assert output_dir.exists()
        assert result.exists()
    
    def test_dummy_pipeline_creates_zip(self, temp_dir):
        """dummy_pipeline should create a zip file."""
        from backend.workers.dummy_worker import dummy_pipeline
        
        input_file = _create_test_nifti(temp_dir / "input")
        output_dir = temp_dir / "output"
        
        result = dummy_pipeline(
            input_path=str(input_file),
            options={},
            output_dir=output_dir,
            simulate_delay=False  # Fast test execution
        )
        
        assert result.suffix == ".zip"
        assert result.stat().st_size > 0
    
    def test_dummy_pipeline_zip_contains_expected_files(self, temp_dir):
        """Results zip should contain expected files."""
        from backend.workers.dummy_worker import dummy_pipeline
        import zipfile
        
        input_file = _create_test_nifti(temp_dir / "input")
        output_dir = temp_dir / "output"
        
        result = dummy_pipeline(
            input_path=str(input_file),
            options={},
            output_dir=output_dir,
            simulate_delay=False  # Fast test execution
        )
        
        with zipfile.ZipFile(result, 'r') as zf:
            names = zf.namelist()
            # Should contain segmentation, json, and csv
            assert any('segmentation' in n for n in names)
            assert any('results.json' in n for n in names)
            assert any('results.csv' in n for n in names)
    
    def test_dummy_pipeline_results_json_valid(self, temp_dir):
        """Results JSON should be valid and contain expected fields."""
        from backend.workers.dummy_worker import dummy_pipeline
        import zipfile
        
        input_file = _create_test_nifti(temp_dir / "input")
        output_dir = temp_dir / "output"
        
        result = dummy_pipeline(
            input_path=str(input_file),
            options={"segmentation_model": "nnunet_cascade"},
            output_dir=output_dir,
            simulate_delay=False  # Fast test execution
        )
        
        with zipfile.ZipFile(result, 'r') as zf:
            json_content = zf.read("results.json")
            data = json.loads(json_content)
            
            assert data["status"] == "dummy_processing"
            assert "options" in data
            assert "dummy_metrics" in data
            assert "bscore" in data["dummy_metrics"]
    
    def test_dummy_pipeline_progress_callback(self, temp_dir):
        """dummy_pipeline should call progress callback."""
        from backend.workers.dummy_worker import dummy_pipeline
        
        input_file = _create_test_nifti(temp_dir / "input")
        output_dir = temp_dir / "output"
        
        progress_calls = []
        
        def callback(step, total, name):
            progress_calls.append((step, total, name))
        
        dummy_pipeline(
            input_path=str(input_file),
            options={},
            output_dir=output_dir,
            progress_callback=callback,
            simulate_delay=False  # Fast test execution
        )
        
        # Should have 4 progress updates (4 steps)
        assert len(progress_calls) == 4
        # Steps should be 1, 2, 3, 4
        steps = [c[0] for c in progress_calls]
        assert steps == [1, 2, 3, 4]
    
    def test_dummy_pipeline_invalid_input_raises(self, temp_dir):
        """dummy_pipeline should raise error for invalid input."""
        from backend.workers.dummy_worker import dummy_pipeline
        
        # Create a non-existent path
        fake_path = temp_dir / "nonexistent.nii.gz"
        output_dir = temp_dir / "output"
        
        with pytest.raises(ValueError) as exc_info:
            dummy_pipeline(
                input_path=str(fake_path),
                options={},
                output_dir=output_dir,
                simulate_delay=False  # Fast test execution
            )
        
        assert "read" in str(exc_info.value).lower() or "failed" in str(exc_info.value).lower()


class TestWorkersPackageExports:
    """Verify workers __init__.py exports correctly."""
    
    def test_workers_package_importable(self):
        """Workers package should be importable."""
        from backend import workers
        assert workers is not None
    
    def test_celery_app_exported(self):
        """celery_app should be exported from workers package."""
        from backend.workers import celery_app
        assert celery_app is not None
    
    def test_process_pipeline_exported(self):
        """process_pipeline should be exported from workers package."""
        from backend.workers import process_pipeline
        assert process_pipeline is not None
    
    def test_dummy_pipeline_exported(self):
        """dummy_pipeline should be exported from workers package."""
        from backend.workers import dummy_pipeline
        assert dummy_pipeline is not None


class TestTaskJobIntegration:
    """Verify task integrates correctly with Job model."""
    
    def test_task_updates_job_status(self, redis_client, temp_dir):
        """Task should update job status in Redis."""
        from backend.models.job import Job
        from backend.workers.dummy_worker import dummy_pipeline
        
        # Create a test job
        job = Job(
            id="integration-test-job",
            input_filename="test.nii.gz",
            input_path="/fake/path",  # We'll use a real path below
            options={"segmentation_model": "nnunet_fullres"}
        )
        job.save(redis_client)
        
        # Verify initial state
        assert job.status == "queued"
        assert Job.get_queue_position("integration-test-job", redis_client) > 0
    
    def test_error_code_mapping(self):
        """Error codes should be mapped correctly."""
        from backend.workers.tasks import _get_error_code
        
        assert _get_error_code(Exception("File not found")) == "FILE_NOT_FOUND"
        assert _get_error_code(Exception("Cannot read format")) == "INVALID_FORMAT"
        assert _get_error_code(Exception("Out of memory")) == "GPU_OOM"
        assert _get_error_code(Exception("DICOM error")) == "DICOM_ERROR"
        assert _get_error_code(Exception("Unknown error")) == "PIPELINE_ERROR"


# =============================================================================
# Test Helpers (fixtures are in conftest.py)
# =============================================================================

# NOTE: The temp_dir and redis_client fixtures are defined in tests/conftest.py
# and are automatically available to all test modules. Do not redefine them here.


def _create_test_nifti(output_dir: Path) -> Path:
    """
    Create a minimal valid NIfTI file for testing.
    
    Returns:
        Path to the created NIfTI file
    """
    import SimpleITK as sitk
    
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Create a small 3D image (16x16x16)
    img = sitk.Image([16, 16, 16], sitk.sitkInt16)
    img.SetSpacing([1.0, 1.0, 1.0])
    img.SetOrigin([0.0, 0.0, 0.0])
    
    # Fill with some non-zero values
    for x in range(16):
        for y in range(16):
            for z in range(16):
                img[x, y, z] = x + y + z
    
    output_path = output_dir / "test_image.nii.gz"
    sitk.WriteImage(img, str(output_path))
    
    return output_path
```

---

## Expected Final State

After completing Stage 1.3, your project should have:

```
backend/workers/
├── __init__.py              # Exports celery_app, process_pipeline, dummy_pipeline
├── celery_app.py            # Celery configuration with Redis
├── tasks.py                 # process_pipeline task
└── dummy_worker.py          # Dummy processing function

tests/
├── __init__.py
├── conftest.py              # (unchanged from Stage 1.2)
├── test_stage_1_1.py        # 23 tests
├── test_stage_1_2.py        # 35 tests
└── test_stage_1_3.py        # 20+ tests
```

---

## Verification Commands

```bash
# Activate environment
conda activate kneepipeline
cd ~/programming/kneepipeline_segmentaton_website

# Verify imports work
python -c "from backend.workers.celery_app import celery_app; print(f'Celery app: {celery_app.main}')"
python -c "from backend.workers.tasks import process_pipeline; print('Tasks OK')"
python -c "from backend.workers.dummy_worker import dummy_pipeline; print('Dummy worker OK')"

# Run Stage 1.3 tests
pytest -m stage_1_3 -v

# Run all tests (Stage 1.1 + 1.2 + 1.3)
pytest tests/ -v

# Run linter
make lint

# Run full verification
make verify
```

---

## Manual Testing: Start Celery Worker

After all tests pass, verify the Celery worker starts correctly:

```bash
# Terminal 1: Start Celery worker
conda activate kneepipeline
cd ~/programming/kneepipeline_segmentaton_website
make worker

# Expected output:
# [config]
# .> app:         knee_pipeline:0x...
# .> transport:   redis://localhost:6379/0
# .> results:     redis://localhost:6379/0
# .> concurrency: 1 (prefork)
# ...
# [queues]
# .> celery          exchange=celery(direct) key=celery
# 
# celery@hostname ready.
```

### Optional: Test Task Submission

You can optionally test submitting a task manually (not required for Stage 1.3):

```bash
# Terminal 2: Test task submission (requires a test image)
conda activate kneepipeline
cd ~/programming/kneepipeline_segmentaton_website

python << 'EOF'
import redis
import json
from pathlib import Path
from backend.models.job import Job
from backend.workers.tasks import process_pipeline

# Create a test job (skip if you don't have a test image)
# This is for manual verification only

# Connect to Redis
r = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)

# Check if we have any queued jobs
queued = r.zrange("job_queue", 0, -1)
print(f"Jobs in queue: {queued}")

# List all jobs
all_jobs = r.hgetall("jobs")
for job_id, job_data in all_jobs.items():
    job = json.loads(job_data)
    print(f"Job {job_id}: status={job['status']}")

print("Manual test complete. See worker terminal for task execution.")
EOF
```

---

## Git Commit

After completing Stage 1.3:

```bash
git add .
git commit -m "$(cat <<'EOF'
Stage 1.3: Redis and Celery setup

- Add Celery app configuration with Redis broker/backend
- Add process_pipeline task with job status updates
- Add dummy_worker for Phase 1 mock processing
- Add progress callback support for step-by-step updates
- Add simulate_delay parameter for fast test execution
- Centralize REDIS_URL in celery_app.py (imported by tasks.py)
- Add Stage 1.3 verification tests (20+ tests, using shared fixtures)
- All 75+ tests passing (Stage 1.1 + 1.2 + 1.3)

Design decisions:
- Two Redis client functions (job_service.py for FastAPI, tasks.py for Celery)
- Shared test fixtures in conftest.py (not duplicated in test files)
- Configurable delays in dummy_worker (simulate_delay param)
EOF
)"
```

---

## Next Step: Stage 1.4 - API Routes

See [STAGE_1.4_API_ROUTES.md](./STAGE_1.4_API_ROUTES.md)

Stage 1.4 creates the FastAPI routes that wire everything together:

1. **POST /upload** - Receive file, validate, create job, submit task
2. **GET /status/{job_id}** - Return job status (queued/processing/complete/error)
3. **GET /download/{job_id}** - Return results zip file
4. **GET /stats** - Return usage statistics

---

## Notes for Next Agent

### What's Ready to Use

- **Celery App**: Import from `backend.workers.celery_app`
- **Tasks**: Import `process_pipeline` from `backend.workers.tasks`
- **Dummy Worker**: Import `dummy_pipeline` from `backend.workers.dummy_worker`
- **Redis URL**: Import `REDIS_URL` from `backend.workers.celery_app` (centralized, avoid duplicating env var read)

### Key Design Decisions

1. **Single Concurrency**: `worker_concurrency=1` ensures only one job runs at a time (GPU constraint)
2. **Late Acknowledgment**: `task_acks_late=True` ensures tasks are requeued if worker crashes
3. **Progress Callback**: `dummy_pipeline` accepts optional callback for progress updates
4. **Error Code Mapping**: `_get_error_code()` maps exceptions to API error codes
5. **Simulate Delay**: `dummy_pipeline` has `simulate_delay` parameter (default `True`) - set to `False` in tests for faster execution
6. **Centralized REDIS_URL**: Defined once in `celery_app.py`, imported by `tasks.py` to avoid duplication

### Two Redis Client Functions (Important!)

There are **two** `get_redis_client()` functions in the codebase:

| Location | Purpose | Context |
|----------|---------|---------|
| `backend/services/job_service.py` | FastAPI dependency | HTTP request handlers (routes) |
| `backend/workers/tasks.py` | Celery task helper | Celery worker tasks |

**Why two?** The `job_service.py` version uses `Depends(get_settings)` which only works in FastAPI request context. Celery tasks run outside of FastAPI, so they need their own Redis client function.

**Do not confuse them!** Use the appropriate one for your context.

### How to Start the Worker

```bash
make worker
# or: celery -A backend.workers.celery_app worker --loglevel=info --concurrency=1
```

### Integration Points

The `process_pipeline` task:
- Loads `Job` from Redis using `Job.load()`
- Updates job status and progress via `job.save()`
- Removes job from queue via `job.delete_from_queue()`
- Records statistics via `record_processing_time()` and `increment_processed_count()`

### Testing Without Worker

Most tests don't require a running Celery worker - they test the components directly.
The worker is only needed for end-to-end integration testing (Stage 1.6).

---

## Troubleshooting

### Redis Connection Refused

```bash
# Make sure Redis is running
make redis-start
make redis-ping  # Should return PONG
```

### Celery Worker Won't Start

```bash
# Check for import errors
python -c "from backend.workers.celery_app import celery_app"

# Check Redis connectivity
python -c "import redis; r = redis.Redis(); r.ping()"
```

### Tests Fail with Redis Error

```bash
# Tests use Redis database 15 to avoid conflicts
# Make sure Redis is running
docker exec redis redis-cli -n 15 ping
```
