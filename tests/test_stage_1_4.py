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
from datetime import datetime
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

# Mark all tests in this module as stage_1_4
pytestmark = pytest.mark.stage_1_4


@pytest.fixture
def app_with_test_redis(redis_client):
    """
    Create FastAPI app with test Redis client injected.

    This ensures both the fixture and the routes use the same Redis database (db 15).
    """
    from backend.main import app
    from backend.services.job_service import get_redis_client

    # Override the dependency to return the test redis client
    def override_get_redis_client():
        return redis_client

    app.dependency_overrides[get_redis_client] = override_get_redis_client
    yield app
    # Clean up the override after the test
    app.dependency_overrides.clear()


@pytest.fixture
def client(app_with_test_redis):
    """Create test client with Redis dependency overridden."""
    return TestClient(app_with_test_redis)


class TestUploadRoute:
    """Verify POST /upload endpoint."""

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
        # Mock the Celery task to avoid actually running it
        with patch("backend.routes.upload.process_pipeline.delay"):
            response = client.post(
                "/upload",
                files={
                    "file": ("test.nii.gz", valid_nifti_bytes, "application/octet-stream")
                },
                data={"segmentation_model": "nnunet_fullres"},
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
        with patch("backend.routes.upload.process_pipeline.delay"):
            response = client.post(
                "/upload",
                files={
                    "file": ("test.nii.gz", valid_nifti_bytes, "application/octet-stream")
                },
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

    def test_upload_rejects_empty_file(self, client, temp_dir):
        """Upload should reject empty files."""
        response = client.post(
            "/upload",
            files={"file": ("empty.nii.gz", b"", "application/octet-stream")},
        )

        assert response.status_code == 400

    def test_upload_with_email(self, client, valid_nifti_bytes, redis_client):
        """Upload should store email if provided."""
        with patch("backend.routes.upload.process_pipeline.delay"):
            response = client.post(
                "/upload",
                files={
                    "file": ("test.nii.gz", valid_nifti_bytes, "application/octet-stream")
                },
                data={"email": "test@example.com"},
            )

        assert response.status_code == 201
        job_id = response.json()["job_id"]

        # Check email is stored in job
        job_data = redis_client.hget("jobs", job_id)
        job = json.loads(job_data)
        assert job["email"] == "test@example.com"

    def test_upload_with_all_options(self, client, valid_nifti_bytes, redis_client):
        """Upload should accept all configuration options."""
        with patch("backend.routes.upload.process_pipeline.delay"):
            response = client.post(
                "/upload",
                files={
                    "file": ("test.nii.gz", valid_nifti_bytes, "application/octet-stream")
                },
                data={
                    "email": "user@example.com",
                    "segmentation_model": "nnunet_cascade",
                    "perform_nsm": "true",
                    "nsm_type": "bone_only",
                    "retain_results": "false",
                    "cartilage_smoothing": "0.5",
                },
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
        # Create a zip containing a NIfTI file
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w") as zf:
            zf.writestr("patient/scan.nii.gz", valid_nifti_bytes)
        zip_buffer.seek(0)

        with patch("backend.routes.upload.process_pipeline.delay"):
            response = client.post(
                "/upload",
                files={"file": ("patient_data.zip", zip_buffer.read(), "application/zip")},
            )

        assert response.status_code == 201


class TestStatusRoute:
    """Verify GET /status/{job_id} endpoint."""

    def test_status_queued_job(self, client, redis_client):
        """Status should return queued info for queued jobs."""
        from backend.models.job import Job

        # Create a queued job
        job = Job(
            id="status-test-queued",
            input_filename="test.nii.gz",
            input_path="/fake/path/test.nii.gz",
            options={"segmentation_model": "nnunet_fullres"},
            status="queued",
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
            step_name="Processing image",
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
            result_size_bytes=result_path.stat().st_size,
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
            error_code="PIPELINE_ERROR",
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

    def test_download_complete_job(self, client, redis_client, temp_dir):
        """Download should serve results zip for complete jobs."""
        from backend.models.job import Job

        # Create a real zip file
        result_path = temp_dir / "test_results.zip"
        with zipfile.ZipFile(result_path, "w") as zf:
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
            result_size_bytes=result_path.stat().st_size,
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
            status="processing",
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

        job = Job(
            id="download-test-missing",
            input_filename="test.nii.gz",
            input_path="/fake/path",
            options={},
            status="complete",
            started_at=datetime.now().isoformat(),
            completed_at=datetime.now().isoformat(),
            result_path="/nonexistent/path/results.zip",
            result_size_bytes=1000,
        )
        job.save(redis_client)

        response = client.get("/download/download-test-missing")

        assert response.status_code == 404


class TestStatsRoute:
    """Verify GET /stats endpoint."""

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
            "uptime_hours",
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
        from backend.routes import download, health, stats, status, upload

        assert health.router is not None
        assert upload.router is not None
        assert status.router is not None
        assert download.router is not None
        assert stats.router is not None
