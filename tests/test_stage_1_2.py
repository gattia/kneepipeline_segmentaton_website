"""
Stage 1.2 Verification Tests - Models & Services

Run with: pytest -m stage_1_2 -v
"""
import time
import zipfile

import pytest

# Mark all tests in this module as stage_1_2
pytestmark = pytest.mark.stage_1_2


class TestPydanticSchemas:
    """Verify Pydantic schemas are correctly defined."""

    def test_schemas_importable(self):
        """All schemas should be importable."""
        from backend.models.schemas import (
            StatsResponse,
            StatusComplete,
            StatusError,
            StatusProcessing,
            StatusQueued,
            UploadOptions,
            UploadResponse,
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
        from pydantic import ValidationError

        from backend.models.schemas import UploadOptions

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

        # Create multiple jobs
        for i in range(3):
            job = Job(
                id=f"queue-test-{i}",
                input_filename=f"test{i}.nii.gz",
                input_path=f"/data/uploads/test{i}.nii.gz",
                options={}
            )
            job.save(redis_client)
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

        assert "extension" in str(exc_info.value).lower() or "invalid" in str(exc_info.value).lower()

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
            get_estimated_wait,
            get_redis_client,
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

    def test_models_exports(self):
        """Models package should export all schemas and Job."""
        from backend.models import (
            Job,
            UploadOptions,
        )
        assert UploadOptions
        assert Job


class TestServicesInit:
    """Verify services __init__.py exports correctly."""

    def test_services_package_structure(self):
        """Services package should be importable."""
        from backend import services
        assert services

    def test_services_exports(self):
        """Services package should export all functions."""
        from backend.services import (
            get_statistics,
            validate_and_prepare_upload,
        )
        assert validate_and_prepare_upload
        assert get_statistics
