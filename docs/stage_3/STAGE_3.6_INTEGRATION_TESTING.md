# Stage 3.6: Integration Testing

## Overview

**Goal**: Verify the complete pipeline works end-to-end with real MRI data.

**Estimated Time**: ~1-2 hours

**Deliverable**: Confirmed working system with documented test results.

---

## Prerequisites

**Stages 3.1-3.5 must be complete.** Verify by running:

```bash
conda activate kneepipeline
cd ~/programming/kneepipeline_segmentaton_website

# All Stage 3 tests should pass
pytest -m "stage_3_3 or stage_3_4 or stage_3_5" -v

# Services should be running
docker exec redis redis-cli ping  # Should return PONG

# Pipeline dependencies should be available
python -c "import torch; print(f'CUDA: {torch.cuda.is_available()}')"
```

---

## What This Stage Creates

### Test Documentation

```
tests/
├── test_stage_3_6_integration.py    # NEW: Full integration tests
└── test_data/
    └── README.md                     # NEW: Test data documentation
```

### Test Artifacts

```
data/test_results/                    # Generated during testing
├── nifti_test/
├── dicom_test/
└── error_test/
```

---

## Success Criteria

- [ ] Upload → Process → Download works end-to-end
- [ ] NIfTI files process successfully
- [ ] DICOM zips process successfully (if available)
- [ ] Results zip contains expected files (segmentation, meshes, JSON)
- [ ] Progress updates appear in job status
- [ ] Errors are handled gracefully with user-friendly messages
- [ ] Processing time is within acceptable range (5-15 minutes)
- [ ] GPU memory is stable after multiple jobs

---

## Test Cases

### Test Case 1: Basic NIfTI Processing

**Input**: Valid NIfTI knee MRI
**Options**: Default (nnunet_fullres, NSM bone+cart)
**Expected**: Complete with segmentation, meshes, thickness data, BScore

### Test Case 2: Cascade Model

**Input**: Valid NIfTI knee MRI
**Options**: nnunet_cascade, NSM bone+cart
**Expected**: Complete (may take longer than fullres)

### Test Case 3: Bone-Only NSM

**Input**: Valid NIfTI knee MRI
**Options**: nnunet_fullres, NSM bone_only
**Expected**: Complete with bone-only BScore

### Test Case 4: No NSM

**Input**: Valid NIfTI knee MRI
**Options**: nnunet_fullres, NSM none
**Expected**: Complete faster (no NSM step)

### Test Case 5: Invalid File

**Input**: Non-medical image (e.g., PNG)
**Expected**: Error with clear message

### Test Case 6: Large File (Optional)

**Input**: Large MRI dataset
**Expected**: Completes or graceful timeout

---

## Detailed Testing Procedure

### Step 1: Start All Services

```bash
# Terminal 1: Start Redis (if not running)
cd ~/programming/kneepipeline_segmentaton_website
make redis-start

# Terminal 2: Start FastAPI server
conda activate kneepipeline
cd ~/programming/kneepipeline_segmentaton_website
make run

# Terminal 3: Start Celery worker
conda activate kneepipeline
cd ~/programming/kneepipeline_segmentaton_website
make worker
```

### Step 2: Obtain Test Data

```bash
# Option A: Use test data from kneepipeline
TEST_IMAGE=~/programming/kneepipeline/DEPENDENCIES/nnunet_knee_inference/huggingface/test_data/sample_knee_mri.nii.gz

# Option B: Use any valid NIfTI knee MRI you have
TEST_IMAGE=/path/to/your/test_knee_mri.nii.gz

# Verify test image exists
ls -la $TEST_IMAGE
```

### Step 3: Run Manual End-to-End Test

```bash
# Test via curl
cd ~/programming/kneepipeline_segmentaton_website

# Upload file
RESPONSE=$(curl -s -X POST "http://localhost:8000/upload" \
  -F "file=@${TEST_IMAGE}" \
  -F "segmentation_model=nnunet_fullres" \
  -F "perform_nsm=true" \
  -F "nsm_type=bone_and_cart")

echo "Upload response: $RESPONSE"

# Extract job ID
JOB_ID=$(echo $RESPONSE | python -c "import sys,json; print(json.load(sys.stdin)['job_id'])")
echo "Job ID: $JOB_ID"

# Poll status until complete
while true; do
    STATUS=$(curl -s "http://localhost:8000/status/$JOB_ID")
    echo "Status: $STATUS"
    
    JOB_STATUS=$(echo $STATUS | python -c "import sys,json; print(json.load(sys.stdin)['status'])")
    
    if [ "$JOB_STATUS" = "complete" ] || [ "$JOB_STATUS" = "error" ]; then
        break
    fi
    
    sleep 10
done

# Download results if complete
if [ "$JOB_STATUS" = "complete" ]; then
    curl -s "http://localhost:8000/download/$JOB_ID" -o "test_results.zip"
    echo "Downloaded: test_results.zip"
    
    # Verify contents
    unzip -l test_results.zip
fi
```

### Step 4: Verify Results

```bash
# Unzip and inspect results
mkdir -p /tmp/test_results
unzip test_results.zip -d /tmp/test_results

# Check for expected files
echo "=== Results Contents ==="
ls -la /tmp/test_results/

# Check for segmentation
echo "=== Segmentation File ==="
ls -la /tmp/test_results/*seg* 2>/dev/null || echo "No segmentation file found"

# Check for meshes
echo "=== Mesh Files ==="
ls -la /tmp/test_results/*.vtk 2>/dev/null || echo "No VTK mesh files found"
ls -la /tmp/test_results/*.stl 2>/dev/null || echo "No STL mesh files found"

# Check for results JSON
echo "=== Results JSON ==="
if [ -f /tmp/test_results/results.json ]; then
    cat /tmp/test_results/results.json
else
    echo "No results.json found"
fi

# Check for thickness data
echo "=== Thickness Data ==="
ls -la /tmp/test_results/*thickness* 2>/dev/null || echo "No thickness files found"
```

### Step 5: Run Automated Integration Tests

**File**: `tests/test_stage_3_6_integration.py`

```python
"""
Stage 3.6 Integration Tests - End-to-End Pipeline

Run with: pytest -m stage_3_6 -v --run-integration

These tests require:
1. Running Redis, FastAPI, and Celery worker
2. Valid test MRI data
3. GPU available

Note: These tests are skipped by default. Run with --run-integration flag.
"""
import json
import os
import tempfile
import time
import zipfile
from pathlib import Path

import pytest
import requests

# Mark all tests in this module
pytestmark = [pytest.mark.stage_3_6, pytest.mark.integration]

# Test configuration
BASE_URL = os.getenv("TEST_API_URL", "http://localhost:8000")
TEST_IMAGE_PATH = os.getenv("TEST_IMAGE_PATH", 
    os.path.expanduser("~/programming/kneepipeline/DEPENDENCIES/nnunet_knee_inference/huggingface/test_data/sample_knee_mri.nii.gz"))
MAX_WAIT_SECONDS = 900  # 15 minutes max wait


def pytest_addoption(parser):
    parser.addoption(
        "--run-integration",
        action="store_true",
        default=False,
        help="Run integration tests (requires running services)"
    )


@pytest.fixture
def integration_enabled(request):
    """Skip if integration tests not enabled."""
    if not request.config.getoption("--run-integration"):
        pytest.skip("Integration tests disabled. Run with --run-integration")


@pytest.fixture
def test_image():
    """Get path to test image."""
    if not os.path.exists(TEST_IMAGE_PATH):
        pytest.skip(f"Test image not found: {TEST_IMAGE_PATH}")
    return TEST_IMAGE_PATH


@pytest.fixture
def api_available():
    """Check if API is available."""
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        if response.status_code != 200:
            pytest.skip("API not available")
    except requests.exceptions.RequestException:
        pytest.skip("API not available")


def wait_for_job(job_id: str, max_wait: int = MAX_WAIT_SECONDS) -> dict:
    """Wait for job to complete or error."""
    start_time = time.time()
    
    while time.time() - start_time < max_wait:
        response = requests.get(f"{BASE_URL}/status/{job_id}")
        status = response.json()
        
        if status["status"] in ["complete", "error"]:
            return status
        
        time.sleep(10)  # Poll every 10 seconds
    
    raise TimeoutError(f"Job {job_id} did not complete within {max_wait} seconds")


class TestBasicPipeline:
    """Test basic pipeline functionality."""
    
    def test_upload_and_process(self, integration_enabled, api_available, test_image):
        """Complete upload → process → download cycle."""
        # Upload
        with open(test_image, "rb") as f:
            response = requests.post(
                f"{BASE_URL}/upload",
                files={"file": f},
                data={
                    "segmentation_model": "nnunet_fullres",
                    "perform_nsm": "true",
                    "nsm_type": "bone_only",  # Faster than bone_and_cart
                }
            )
        
        assert response.status_code == 200
        upload_data = response.json()
        assert "job_id" in upload_data
        
        job_id = upload_data["job_id"]
        
        # Wait for completion
        final_status = wait_for_job(job_id)
        
        assert final_status["status"] == "complete", f"Job failed: {final_status.get('error_message')}"
        
        # Download results
        response = requests.get(f"{BASE_URL}/download/{job_id}")
        assert response.status_code == 200
        
        # Verify zip contents
        with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as f:
            f.write(response.content)
            zip_path = f.name
        
        try:
            with zipfile.ZipFile(zip_path) as zf:
                names = zf.namelist()
                
                # Should have at least segmentation
                assert any("seg" in n.lower() for n in names), "No segmentation file in results"
        finally:
            os.unlink(zip_path)


class TestModelVariations:
    """Test different model configurations."""
    
    @pytest.mark.slow
    def test_cascade_model(self, integration_enabled, api_available, test_image):
        """Test nnunet_cascade model."""
        with open(test_image, "rb") as f:
            response = requests.post(
                f"{BASE_URL}/upload",
                files={"file": f},
                data={
                    "segmentation_model": "nnunet_cascade",
                    "perform_nsm": "false",  # Skip NSM for faster test
                }
            )
        
        assert response.status_code == 200
        job_id = response.json()["job_id"]
        
        final_status = wait_for_job(job_id)
        assert final_status["status"] == "complete"
    
    def test_no_nsm(self, integration_enabled, api_available, test_image):
        """Test without NSM analysis."""
        with open(test_image, "rb") as f:
            response = requests.post(
                f"{BASE_URL}/upload",
                files={"file": f},
                data={
                    "segmentation_model": "nnunet_fullres",
                    "perform_nsm": "false",
                }
            )
        
        assert response.status_code == 200
        job_id = response.json()["job_id"]
        
        final_status = wait_for_job(job_id)
        assert final_status["status"] == "complete"


class TestErrorHandling:
    """Test error scenarios."""
    
    def test_invalid_file_rejected(self, integration_enabled, api_available):
        """Invalid file should be rejected."""
        # Create a fake file
        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as f:
            f.write(b"This is not a medical image")
            fake_path = f.name
        
        try:
            with open(fake_path, "rb") as f:
                response = requests.post(
                    f"{BASE_URL}/upload",
                    files={"file": ("test.txt", f, "text/plain")},
                )
            
            # Should be rejected at upload or fail during processing
            if response.status_code == 200:
                job_id = response.json()["job_id"]
                final_status = wait_for_job(job_id, max_wait=60)
                assert final_status["status"] == "error"
            else:
                assert response.status_code in [400, 415]
        finally:
            os.unlink(fake_path)
    
    def test_invalid_model_rejected(self, integration_enabled, api_available, test_image):
        """Invalid model should be rejected."""
        with open(test_image, "rb") as f:
            response = requests.post(
                f"{BASE_URL}/upload",
                files={"file": f},
                data={
                    "segmentation_model": "invalid_model_name",
                }
            )
        
        assert response.status_code == 400


class TestProgressUpdates:
    """Test progress tracking."""
    
    def test_progress_updates_during_processing(self, integration_enabled, api_available, test_image):
        """Progress should update during processing."""
        with open(test_image, "rb") as f:
            response = requests.post(
                f"{BASE_URL}/upload",
                files={"file": f},
                data={
                    "segmentation_model": "nnunet_fullres",
                    "perform_nsm": "false",
                }
            )
        
        job_id = response.json()["job_id"]
        
        # Collect progress updates
        progress_values = []
        
        for _ in range(60):  # Check for up to 10 minutes
            status = requests.get(f"{BASE_URL}/status/{job_id}").json()
            
            if status["status"] == "processing":
                progress_values.append(status.get("progress_percent", 0))
            
            if status["status"] in ["complete", "error"]:
                break
            
            time.sleep(10)
        
        # Should have seen some progress updates
        assert len(progress_values) > 0, "No progress updates observed"
        
        # Progress should generally increase (allow for some variation)
        if len(progress_values) >= 3:
            assert max(progress_values) > min(progress_values), "Progress never increased"
```

### Step 6: Create pytest Configuration for Integration Tests

Add to `pyproject.toml`:

```toml
[tool.pytest.ini_options]
markers = [
    # ... existing markers ...
    "stage_3_6: Stage 3.6 - Integration testing",
    "integration: Integration tests requiring running services",
    "slow: Slow tests",
]
```

### Step 7: Run Integration Tests

```bash
# Run with integration tests enabled
pytest -m stage_3_6 --run-integration -v

# Run only fast integration tests
pytest -m "stage_3_6 and not slow" --run-integration -v
```

---

## Expected Test Results

### Successful Test Output

```
tests/test_stage_3_6_integration.py::TestBasicPipeline::test_upload_and_process PASSED
tests/test_stage_3_6_integration.py::TestModelVariations::test_no_nsm PASSED
tests/test_stage_3_6_integration.py::TestErrorHandling::test_invalid_file_rejected PASSED
tests/test_stage_3_6_integration.py::TestErrorHandling::test_invalid_model_rejected PASSED
tests/test_stage_3_6_integration.py::TestProgressUpdates::test_progress_updates_during_processing PASSED

==================== 5 passed in 423.56s ====================
```

### Performance Benchmarks

| Test Case | Expected Time | Acceptable Range |
|-----------|---------------|------------------|
| nnunet_fullres + NSM bone_only | 5-8 min | < 15 min |
| nnunet_fullres no NSM | 3-5 min | < 10 min |
| nnunet_cascade + NSM | 8-12 min | < 20 min |

---

## GPU Memory Verification

After running tests, verify GPU memory is released:

```bash
# Check GPU memory
nvidia-smi

# Expected: GPU memory should return to baseline after job completes
# If memory stays high, there may be a leak in cleanup
```

---

## Troubleshooting

### Job Stuck in "Processing"

```bash
# Check Celery worker logs
tail -f /path/to/celery.log

# Check for GPU errors
nvidia-smi

# Restart worker if needed
pkill -f celery
make worker
```

### Results Missing Expected Files

```bash
# Check pipeline output directory
ls -la data/results/<job_id>/

# Check job config
cat data/results/<job_id>/config.json

# Check for pipeline errors in worker log
grep -i error /path/to/celery.log
```

### GPU OOM Errors

```bash
# Check current GPU memory usage
nvidia-smi

# Clear GPU memory
python -c "import torch; torch.cuda.empty_cache()"

# Try with smaller batch size
# Add batch_size=16 to upload options
```

---

## Git Commit

```bash
git add .
git commit -m "Stage 3.6: Integration testing complete

- Create test_stage_3_6_integration.py with end-to-end tests
- Add integration test fixtures and configuration
- Document test data requirements
- Add performance benchmarks
- Test: basic pipeline, model variations, error handling, progress

Test coverage:
- NIfTI processing with various options
- Error handling for invalid files
- Progress update verification
- GPU memory stability check

All integration tests passing with real MRI data.
"
```

---

## Stage 3 Complete!

Congratulations! Stage 3 is now complete. The web application is fully integrated with the real knee MRI segmentation pipeline.

### Summary of What Was Built

1. **Stage 3.1**: Installed all pipeline dependencies (PyTorch, NSM, DOSMA, nnU-Net)
2. **Stage 3.2**: Downloaded model weights and created config.json
3. **Stage 3.3**: Created pipeline worker to execute real segmentation
4. **Stage 3.4**: Mapped all web UI options to pipeline configuration
5. **Stage 3.5**: Added error handling and progress tracking
6. **Stage 3.6**: Verified everything works end-to-end

### Next Steps

After Stage 3, consider:

1. **Performance Optimization**: Profile slow steps, optimize batch sizes
2. **Monitoring**: Add logging, metrics, alerting
3. **Scaling**: Multiple workers, load balancing
4. **Features**: 3D preview, email notifications, user accounts


