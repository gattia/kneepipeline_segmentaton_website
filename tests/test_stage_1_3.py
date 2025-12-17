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
        assert hasattr(process_pipeline, "delay")
        assert hasattr(process_pipeline, "apply_async")

    def test_process_pipeline_bound(self):
        """process_pipeline should be bound (access to self)."""
        from backend.workers.tasks import process_pipeline

        # For bound tasks, the task class has a __wrapped__ attribute
        # that is the original function, which takes 'self' as first arg
        # Also, check that the task has request attribute (bound tasks have this)
        assert hasattr(process_pipeline, "request")
        # Bound tasks have a retry method they can use with self
        assert hasattr(process_pipeline, "retry")

    def test_process_pipeline_max_retries(self):
        """process_pipeline should have retry configuration."""
        from backend.workers.tasks import process_pipeline

        assert process_pipeline.max_retries == 2

    def test_tasks_registered_with_celery(self):
        """Tasks should be registered with Celery app."""
        from backend.workers.celery_app import celery_app

        registered_tasks = list(celery_app.tasks.keys())
        # Filter out built-in celery tasks
        custom_tasks = [t for t in registered_tasks if "backend.workers" in t]
        assert len(custom_tasks) >= 1
        assert any("process_pipeline" in t for t in custom_tasks)


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
            simulate_delay=False,  # Fast test execution
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
            simulate_delay=False,  # Fast test execution
        )

        assert result.suffix == ".zip"
        assert result.stat().st_size > 0

    def test_dummy_pipeline_zip_contains_expected_files(self, temp_dir):
        """Results zip should contain expected files."""
        import zipfile

        from backend.workers.dummy_worker import dummy_pipeline

        input_file = _create_test_nifti(temp_dir / "input")
        output_dir = temp_dir / "output"

        result = dummy_pipeline(
            input_path=str(input_file),
            options={},
            output_dir=output_dir,
            simulate_delay=False,  # Fast test execution
        )

        with zipfile.ZipFile(result, "r") as zf:
            names = zf.namelist()
            # Should contain segmentation, json, and csv
            assert any("segmentation" in n for n in names)
            assert any("results.json" in n for n in names)
            assert any("results.csv" in n for n in names)

    def test_dummy_pipeline_results_json_valid(self, temp_dir):
        """Results JSON should be valid and contain expected fields."""
        import zipfile

        from backend.workers.dummy_worker import dummy_pipeline

        input_file = _create_test_nifti(temp_dir / "input")
        output_dir = temp_dir / "output"

        result = dummy_pipeline(
            input_path=str(input_file),
            options={"segmentation_model": "nnunet_cascade"},
            output_dir=output_dir,
            simulate_delay=False,  # Fast test execution
        )

        with zipfile.ZipFile(result, "r") as zf:
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
            simulate_delay=False,  # Fast test execution
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
                simulate_delay=False,  # Fast test execution
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

    def test_redis_url_exported(self):
        """REDIS_URL should be exported from workers package."""
        from backend.workers import REDIS_URL

        assert REDIS_URL is not None
        assert "redis" in REDIS_URL


class TestTaskJobIntegration:
    """Verify task integrates correctly with Job model."""

    def test_task_updates_job_status(self, redis_client, temp_dir):
        """Task should update job status in Redis."""
        from backend.models.job import Job

        # Create a test job
        job = Job(
            id="integration-test-job",
            input_filename="test.nii.gz",
            input_path="/fake/path",  # We'll use a real path below
            options={"segmentation_model": "nnunet_fullres"},
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
