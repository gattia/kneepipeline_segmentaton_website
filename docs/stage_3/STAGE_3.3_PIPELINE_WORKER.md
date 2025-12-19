# Stage 3.3: Pipeline Worker Integration

## Overview

**Goal**: Replace the dummy worker with real pipeline execution, integrating the knee MRI segmentation pipeline into the web application.

**Estimated Time**: ~2-3 hours

**Deliverable**: A working pipeline worker that executes real segmentation, mesh generation, and NSM analysis.

---

## Prerequisites

**Stage 3.2 must be complete.** Verify by running:

```bash
conda activate kneepipeline
cd ~/programming/kneepipeline

# Verify config.json exists and pipeline runs
python dosma_knee_seg.py --help 2>/dev/null || python -c "print('Pipeline script found')"
cat config.json | head -5
```

---

## What This Stage Creates

### New Files

```
backend/
├── workers/
│   └── pipeline_worker.py       # NEW: Real pipeline execution
└── services/
    └── config_generator.py      # NEW: Generate job-specific config

tests/
└── test_stage_3_3.py            # NEW: Stage 3.3 verification tests
```

### Modified Files

```
backend/
└── workers/
    └── tasks.py                 # MODIFY: Use real pipeline instead of dummy
```

---

## Success Criteria

- [ ] `backend/workers/pipeline_worker.py` executes real pipeline
- [ ] `backend/services/config_generator.py` generates valid config.json
- [ ] `tasks.py` calls real pipeline when appropriate
- [ ] GPU memory is cleaned up after each job
- [ ] Pipeline timeout is handled gracefully
- [ ] All Stage 3.3 tests pass: `pytest -m stage_3_3 -v`

---

## Detailed Implementation

### Step 1: Create Config Generator Service

**File**: `backend/services/config_generator.py`

```python
"""
Configuration generator for the segmentation pipeline.

This module creates job-specific config.json files that configure
the pipeline based on user-selected options from the web UI.
"""
import json
import os
from pathlib import Path
from typing import Optional


# Base path for the kneepipeline library
KNEEPIPELINE_PATH = Path(os.path.expanduser("~/programming/kneepipeline"))


def generate_pipeline_config(
    job_dir: Path,
    options: dict,
    base_config_path: Optional[Path] = None
) -> Path:
    """
    Generate a job-specific config.json for the pipeline.
    
    Args:
        job_dir: Directory to save the config file
        options: Processing options from web UI
        base_config_path: Path to base config.json (defaults to kneepipeline/config.json)
        
    Returns:
        Path to the generated config.json
    """
    if base_config_path is None:
        base_config_path = KNEEPIPELINE_PATH / "config.json"
    
    # Load base configuration
    with open(base_config_path) as f:
        config = json.load(f)
    
    # Map segmentation model selection
    seg_model = options.get("segmentation_model", "nnunet_fullres")
    config["default_seg_model"] = _map_segmentation_model(seg_model)
    
    # Map NSM options
    nsm_type = options.get("nsm_type", "bone_and_cart")
    perform_nsm = options.get("perform_nsm", True)
    
    if perform_nsm:
        config["perform_bone_and_cart_nsm"] = nsm_type in ["bone_and_cart", "both"]
        config["perform_bone_only_nsm"] = nsm_type in ["bone_only", "both"]
    else:
        config["perform_bone_and_cart_nsm"] = False
        config["perform_bone_only_nsm"] = False
    
    # Map nnU-Net type
    if "cascade" in seg_model:
        config["nnunet"]["type"] = "cascade"
    else:
        config["nnunet"]["type"] = "fullres"
    
    # Cartilage smoothing (optional, uses default if not specified)
    if "cartilage_smoothing" in options:
        config["image_smooth_var_cart"] = options["cartilage_smoothing"]
    
    # Save job-specific config
    job_dir.mkdir(parents=True, exist_ok=True)
    config_path = job_dir / "config.json"
    
    with open(config_path, "w") as f:
        json.dump(config, f, indent=2)
    
    return config_path


def _map_segmentation_model(web_model: str) -> str:
    """
    Map web UI model selection to pipeline model name.
    
    Args:
        web_model: Model name from web UI
        
    Returns:
        Pipeline model name
    """
    model_mapping = {
        "nnunet_fullres": "nnunet_knee",
        "nnunet_cascade": "nnunet_knee",
        "goyal_sagittal": "goyal_sagittal",
        "goyal_coronal": "goyal_coronal",
        "goyal_axial": "goyal_axial",
        "staple": "staple",
    }
    return model_mapping.get(web_model, "nnunet_knee")


def get_pipeline_script_path() -> Path:
    """Get the path to the main pipeline script."""
    return KNEEPIPELINE_PATH / "dosma_knee_seg.py"


def get_base_config_path() -> Path:
    """Get the path to the base config.json."""
    return KNEEPIPELINE_PATH / "config.json"
```

---

### Step 2: Create Pipeline Worker

**File**: `backend/workers/pipeline_worker.py`

```python
"""
Real pipeline worker for knee MRI segmentation.

This module executes the actual segmentation pipeline as a subprocess,
handling configuration, progress tracking, and error management.
"""
import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Callable, Optional

import torch


# Pipeline paths
KNEEPIPELINE_PATH = Path(os.path.expanduser("~/programming/kneepipeline"))
PIPELINE_SCRIPT = KNEEPIPELINE_PATH / "dosma_knee_seg.py"

# Timeout for pipeline execution (30 minutes)
PIPELINE_TIMEOUT_SECONDS = 1800


def run_real_pipeline(
    input_path: str,
    options: dict,
    output_dir: Path,
    config_path: Path,
    progress_callback: Optional[Callable[[int, int, str], None]] = None,
) -> Path:
    """
    Execute the real segmentation pipeline.
    
    Args:
        input_path: Path to the input medical image
        options: Processing options from web UI
        output_dir: Directory to save results
        config_path: Path to job-specific config.json
        progress_callback: Optional callback(step, total_steps, step_name)
        
    Returns:
        Path to the results zip file
        
    Raises:
        ValueError: If input cannot be processed
        RuntimeError: If pipeline execution fails
        TimeoutError: If pipeline exceeds timeout
    """
    input_path = Path(input_path)
    output_dir = Path(output_dir)
    
    # Create output directory
    results_dir = output_dir / "pipeline_output"
    results_dir.mkdir(parents=True, exist_ok=True)
    
    def update_progress(step: int, total: int, name: str):
        if progress_callback:
            progress_callback(step, total, name)
    
    total_steps = 5
    
    # Step 1: Setup
    update_progress(1, total_steps, "Preparing pipeline")
    
    # Determine model name from options
    seg_model = options.get("segmentation_model", "nnunet_fullres")
    model_name = _map_model_name(seg_model)
    
    # Step 2: Run segmentation pipeline
    update_progress(2, total_steps, "Running segmentation")
    
    # Build command
    command = [
        sys.executable,  # Use same Python interpreter
        str(PIPELINE_SCRIPT),
        str(input_path),
        str(results_dir),
        model_name,
    ]
    
    # Set environment with config path
    env = os.environ.copy()
    env["KNEEPIPELINE_CONFIG"] = str(config_path)
    
    # Add kneepipeline to PYTHONPATH
    python_path = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = f"{KNEEPIPELINE_PATH}:{python_path}"
    
    try:
        # Run pipeline as subprocess
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=PIPELINE_TIMEOUT_SECONDS,
            cwd=str(KNEEPIPELINE_PATH),
            env=env,
        )
        
        # Log output
        if result.stdout:
            print(f"Pipeline stdout:\n{result.stdout}")
        if result.stderr:
            print(f"Pipeline stderr:\n{result.stderr}")
        
        # Check for errors
        if result.returncode != 0:
            error_msg = _parse_pipeline_error(result.stderr or result.stdout)
            raise RuntimeError(f"Pipeline failed: {error_msg}")
            
    except subprocess.TimeoutExpired:
        raise TimeoutError(f"Pipeline exceeded {PIPELINE_TIMEOUT_SECONDS}s timeout")
    
    # Step 3: Verify outputs
    update_progress(3, total_steps, "Verifying outputs")
    
    if not _verify_pipeline_outputs(results_dir):
        raise RuntimeError("Pipeline completed but expected output files are missing")
    
    # Step 4: Package results
    update_progress(4, total_steps, "Packaging results")
    
    # Determine input stem for naming
    input_stem = input_path.stem
    if input_path.suffix == '.gz':
        input_stem = Path(input_stem).stem
    if input_path.is_dir():
        input_stem = input_path.name
    
    # Create results zip
    zip_path = shutil.make_archive(
        str(output_dir / f"{input_stem}_results"),
        'zip',
        results_dir
    )
    
    # Step 5: Cleanup GPU memory
    update_progress(5, total_steps, "Cleaning up")
    cleanup_gpu_memory()
    
    return Path(zip_path)


def _map_model_name(web_model: str) -> str:
    """Map web UI model name to pipeline model name."""
    mapping = {
        "nnunet_fullres": "nnunet_knee",
        "nnunet_cascade": "nnunet_knee",
        "goyal_sagittal": "goyal_sagittal",
        "goyal_coronal": "goyal_coronal",
        "goyal_axial": "goyal_axial",
        "staple": "staple",
    }
    return mapping.get(web_model, "nnunet_knee")


def _verify_pipeline_outputs(output_dir: Path) -> bool:
    """
    Verify that expected pipeline outputs exist.
    
    Returns True if at least segmentation file exists.
    """
    # Check for segmentation file (various possible names)
    seg_patterns = ["*seg*.nii.gz", "*seg*.nrrd", "segmentation*"]
    for pattern in seg_patterns:
        if list(output_dir.glob(pattern)):
            return True
    
    # Check for any NIfTI or NRRD files
    if list(output_dir.glob("*.nii.gz")) or list(output_dir.glob("*.nrrd")):
        return True
    
    return False


def _parse_pipeline_error(error_output: str) -> str:
    """
    Parse pipeline error output and return user-friendly message.
    """
    error_output = error_output.lower()
    
    if "out of memory" in error_output or "cuda out of memory" in error_output:
        return "GPU ran out of memory. Try a smaller file or contact support."
    elif "no such file" in error_output or "not found" in error_output:
        return "Input file could not be read. Please check the file format."
    elif "invalid" in error_output and "format" in error_output:
        return "Invalid file format. Supported formats: NIfTI, NRRD, DICOM."
    elif "permission denied" in error_output:
        return "Permission denied when accessing files."
    elif "segmentation failed" in error_output:
        return "Segmentation failed. The image quality may be insufficient."
    else:
        # Return first line of error as fallback
        lines = error_output.strip().split('\n')
        return lines[-1][:200] if lines else "Unknown error occurred"


def cleanup_gpu_memory():
    """
    Clean up GPU memory after pipeline execution.
    
    Should be called after each job to prevent memory leaks.
    """
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
        torch.cuda.synchronize()
        
        # Force garbage collection
        import gc
        gc.collect()
        
        # Small delay to ensure memory is freed
        time.sleep(1)
```

---

### Step 3: Update Tasks to Use Real Pipeline

**File**: `backend/workers/tasks.py`

Update the `process_pipeline` task to use the real pipeline:

```python
"""
Celery task definitions.

This module defines the main processing task that orchestrates
job execution, progress updates, and result handling.
"""
import os
from datetime import datetime
from pathlib import Path

import redis

from .celery_app import REDIS_URL, celery_app


def get_redis_client() -> redis.Redis:
    """Get Redis client for Celery task operations."""
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
    """
    # Deferred imports to avoid circular imports
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
        # Setup output directory
        output_dir = settings.results_dir / job_id
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
            "duration_seconds": duration
        }
        
    except TimeoutError as e:
        job.status = "error"
        job.error_message = str(e)
        job.error_code = "TIMEOUT"
        job.save(redis_client)
        _cleanup_after_error()
        raise
        
    except Exception as e:
        job.status = "error"
        job.error_message = str(e)
        job.error_code = _get_error_code(e)
        job.save(redis_client)
        _cleanup_after_error()
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


def _get_error_code(exception: Exception) -> str:
    """Map exception to error code for API response."""
    error_msg = str(exception).lower()
    
    if "timeout" in error_msg:
        return "TIMEOUT"
    elif "not found" in error_msg:
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

### Step 4: Update Services Package Init

**File**: `backend/services/__init__.py`

Add the new config_generator module:

```python
"""
Services package - Business logic and helper services.
"""
from .config_generator import generate_pipeline_config, get_pipeline_script_path
from .file_handler import validate_and_prepare_upload
from .job_service import get_estimated_wait, get_redis_client, record_processing_time
from .statistics import get_statistics, increment_processed_count, track_user_email

__all__ = [
    "validate_and_prepare_upload",
    "get_redis_client",
    "get_estimated_wait",
    "record_processing_time",
    "get_statistics",
    "increment_processed_count",
    "track_user_email",
    "generate_pipeline_config",
    "get_pipeline_script_path",
]
```

---

### Step 5: Create Stage 3.3 Tests

**File**: `tests/test_stage_3_3.py`

```python
"""
Stage 3.3 Verification Tests - Pipeline Worker Integration

Run with: pytest -m stage_3_3 -v

These tests verify:
1. Config generator creates valid configuration
2. Pipeline worker module structure
3. Model name mapping
4. Error code mapping
5. GPU cleanup functionality
"""
import json
import os
import tempfile
from pathlib import Path

import pytest

# Mark all tests in this module as stage_3_3
pytestmark = pytest.mark.stage_3_3


class TestConfigGenerator:
    """Verify config generator creates valid configuration."""
    
    def test_config_generator_importable(self):
        """Config generator should be importable."""
        from backend.services.config_generator import generate_pipeline_config
        assert generate_pipeline_config is not None
    
    def test_generate_config_creates_file(self, temp_dir):
        """generate_pipeline_config should create a config.json file."""
        from backend.services.config_generator import generate_pipeline_config
        
        # Skip if base config doesn't exist
        base_config = Path(os.path.expanduser("~/programming/kneepipeline/config.json"))
        if not base_config.exists():
            pytest.skip("Base config.json not found")
        
        config_path = generate_pipeline_config(
            job_dir=temp_dir,
            options={"segmentation_model": "nnunet_fullres"}
        )
        
        assert config_path.exists()
        assert config_path.name == "config.json"
    
    def test_generate_config_valid_json(self, temp_dir):
        """Generated config should be valid JSON."""
        from backend.services.config_generator import generate_pipeline_config
        
        base_config = Path(os.path.expanduser("~/programming/kneepipeline/config.json"))
        if not base_config.exists():
            pytest.skip("Base config.json not found")
        
        config_path = generate_pipeline_config(
            job_dir=temp_dir,
            options={"segmentation_model": "nnunet_fullres"}
        )
        
        with open(config_path) as f:
            config = json.load(f)
        
        assert isinstance(config, dict)
        assert "default_seg_model" in config
    
    def test_config_nsm_options_bone_and_cart(self, temp_dir):
        """Config should enable bone+cart NSM when selected."""
        from backend.services.config_generator import generate_pipeline_config
        
        base_config = Path(os.path.expanduser("~/programming/kneepipeline/config.json"))
        if not base_config.exists():
            pytest.skip("Base config.json not found")
        
        config_path = generate_pipeline_config(
            job_dir=temp_dir,
            options={
                "segmentation_model": "nnunet_fullres",
                "perform_nsm": True,
                "nsm_type": "bone_and_cart"
            }
        )
        
        with open(config_path) as f:
            config = json.load(f)
        
        assert config["perform_bone_and_cart_nsm"] is True
        assert config["perform_bone_only_nsm"] is False
    
    def test_config_nsm_options_both(self, temp_dir):
        """Config should enable both NSM types when 'both' selected."""
        from backend.services.config_generator import generate_pipeline_config
        
        base_config = Path(os.path.expanduser("~/programming/kneepipeline/config.json"))
        if not base_config.exists():
            pytest.skip("Base config.json not found")
        
        config_path = generate_pipeline_config(
            job_dir=temp_dir,
            options={
                "segmentation_model": "nnunet_fullres",
                "perform_nsm": True,
                "nsm_type": "both"
            }
        )
        
        with open(config_path) as f:
            config = json.load(f)
        
        assert config["perform_bone_and_cart_nsm"] is True
        assert config["perform_bone_only_nsm"] is True
    
    def test_config_nsm_disabled(self, temp_dir):
        """Config should disable NSM when perform_nsm is False."""
        from backend.services.config_generator import generate_pipeline_config
        
        base_config = Path(os.path.expanduser("~/programming/kneepipeline/config.json"))
        if not base_config.exists():
            pytest.skip("Base config.json not found")
        
        config_path = generate_pipeline_config(
            job_dir=temp_dir,
            options={
                "segmentation_model": "nnunet_fullres",
                "perform_nsm": False,
            }
        )
        
        with open(config_path) as f:
            config = json.load(f)
        
        assert config["perform_bone_and_cart_nsm"] is False
        assert config["perform_bone_only_nsm"] is False


class TestPipelineWorker:
    """Verify pipeline worker module structure."""
    
    def test_pipeline_worker_importable(self):
        """Pipeline worker should be importable."""
        from backend.workers.pipeline_worker import run_real_pipeline
        assert run_real_pipeline is not None
    
    def test_cleanup_gpu_memory_importable(self):
        """cleanup_gpu_memory should be importable."""
        from backend.workers.pipeline_worker import cleanup_gpu_memory
        assert cleanup_gpu_memory is not None
    
    def test_cleanup_gpu_memory_runs_without_error(self):
        """cleanup_gpu_memory should run without error."""
        from backend.workers.pipeline_worker import cleanup_gpu_memory
        # Should not raise even without GPU
        cleanup_gpu_memory()


class TestModelNameMapping:
    """Verify model name mapping works correctly."""
    
    def test_map_nnunet_fullres(self):
        """nnunet_fullres should map to nnunet_knee."""
        from backend.services.config_generator import _map_segmentation_model
        assert _map_segmentation_model("nnunet_fullres") == "nnunet_knee"
    
    def test_map_nnunet_cascade(self):
        """nnunet_cascade should map to nnunet_knee."""
        from backend.services.config_generator import _map_segmentation_model
        assert _map_segmentation_model("nnunet_cascade") == "nnunet_knee"
    
    def test_map_goyal_sagittal(self):
        """goyal_sagittal should map to itself."""
        from backend.services.config_generator import _map_segmentation_model
        assert _map_segmentation_model("goyal_sagittal") == "goyal_sagittal"
    
    def test_map_unknown_defaults_to_nnunet(self):
        """Unknown model should default to nnunet_knee."""
        from backend.services.config_generator import _map_segmentation_model
        assert _map_segmentation_model("unknown_model") == "nnunet_knee"


class TestErrorCodeMapping:
    """Verify error code mapping in tasks."""
    
    def test_timeout_error_code(self):
        """Timeout should map to TIMEOUT code."""
        from backend.workers.tasks import _get_error_code
        assert _get_error_code(TimeoutError("Pipeline timed out")) == "TIMEOUT"
    
    def test_memory_error_code(self):
        """Memory error should map to GPU_OOM code."""
        from backend.workers.tasks import _get_error_code
        assert _get_error_code(Exception("CUDA out of memory")) == "GPU_OOM"
    
    def test_file_not_found_code(self):
        """File not found should map to FILE_NOT_FOUND code."""
        from backend.workers.tasks import _get_error_code
        assert _get_error_code(FileNotFoundError("File not found")) == "FILE_NOT_FOUND"
    
    def test_unknown_error_code(self):
        """Unknown error should map to PIPELINE_ERROR code."""
        from backend.workers.tasks import _get_error_code
        assert _get_error_code(Exception("Something went wrong")) == "PIPELINE_ERROR"


class TestTaskConfiguration:
    """Verify task configuration options."""
    
    def test_should_use_real_pipeline_default(self):
        """Should use real pipeline by default."""
        from backend.workers.tasks import _should_use_real_pipeline
        
        # Save current env value
        original = os.environ.get("USE_DUMMY_PIPELINE")
        
        # Ensure env var is not set
        if "USE_DUMMY_PIPELINE" in os.environ:
            del os.environ["USE_DUMMY_PIPELINE"]
        
        try:
            assert _should_use_real_pipeline({}) is True
        finally:
            # Restore original value
            if original is not None:
                os.environ["USE_DUMMY_PIPELINE"] = original
    
    def test_should_use_dummy_pipeline_when_env_set(self):
        """Should use dummy pipeline when env var is set."""
        from backend.workers.tasks import _should_use_real_pipeline
        
        # Save current env value
        original = os.environ.get("USE_DUMMY_PIPELINE")
        
        try:
            os.environ["USE_DUMMY_PIPELINE"] = "1"
            assert _should_use_real_pipeline({}) is False
        finally:
            # Restore original value
            if original is not None:
                os.environ["USE_DUMMY_PIPELINE"] = original
            elif "USE_DUMMY_PIPELINE" in os.environ:
                del os.environ["USE_DUMMY_PIPELINE"]
```

---

### Step 6: Update pyproject.toml with Stage 3.3 Marker

Add the stage_3_3 marker to `pyproject.toml`:

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
asyncio_mode = "auto"
addopts = "-v --tb=short"
markers = [
    "stage_1_1: Stage 1.1 - Project scaffolding",
    "stage_1_2: Stage 1.2 - Models and services",
    "stage_1_3: Stage 1.3 - Redis and Celery",
    "stage_1_4: Stage 1.4 - API routes",
    "stage_1_5: Stage 1.5 - Frontend",
    "stage_1_6: Stage 1.6 - Docker deployment",
    "stage_1_7: Stage 1.7 - HTTPS with Caddy",
    "stage_3_3: Stage 3.3 - Pipeline worker integration",
]
```

---

## Verification Commands

```bash
conda activate kneepipeline
cd ~/programming/kneepipeline_segmentaton_website

# Verify new modules are importable
python -c "from backend.services.config_generator import generate_pipeline_config; print('Config generator OK')"
python -c "from backend.workers.pipeline_worker import run_real_pipeline; print('Pipeline worker OK')"

# Run Stage 3.3 tests
pytest -m stage_3_3 -v

# Run all tests
make verify
```

---

## Manual Testing

After tests pass, test with a real image:

```bash
# Start services
make redis-start
make run &
make worker &

# Upload a test image via the web UI at http://localhost:8000
# Or use curl:
curl -X POST "http://localhost:8000/upload" \
  -F "file=@test_input.nii.gz" \
  -F "segmentation_model=nnunet_fullres" \
  -F "perform_nsm=true" \
  -F "nsm_type=bone_and_cart"
```

---

## Git Commit

```bash
git add .
git commit -m "Stage 3.3: Pipeline worker integration

- Create backend/services/config_generator.py for job-specific configs
- Create backend/workers/pipeline_worker.py for real pipeline execution
- Update tasks.py to use real pipeline (with dummy fallback via env var)
- Add GPU memory cleanup after each job
- Add pipeline timeout handling (30 minutes)
- Add Stage 3.3 verification tests

The worker now:
- Generates job-specific config.json from web UI options
- Runs dosma_knee_seg.py as subprocess
- Cleans up GPU memory after each job
- Maps errors to user-friendly messages
"
```

---

## Next Step: Stage 3.4 - Configuration Mapping

See [STAGE_3.4_CONFIG_MAPPING.md](./STAGE_3.4_CONFIG_MAPPING.md)



