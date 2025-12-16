# Knee MRI Segmentation & Analysis Website

## Project Overview

A web application that provides automated knee MRI segmentation and analysis through a simple browser interface. Users upload knee MRI data, select processing options, and receive comprehensive results including segmentations, 3D surface meshes, cartilage thickness measurements, T2 maps, and neural shape model (NSM) analysis with BScore computation.

---

## Table of Contents

1. [Core Functionality](#core-functionality)
2. [Architecture](#architecture)
3. [Technology Stack](#technology-stack)
4. [User Interface](#user-interface)
5. [API Endpoints](#api-endpoints)
6. [Processing Pipeline](#processing-pipeline)
7. [Job Queue System](#job-queue-system)
8. [File Handling](#file-handling)
9. [Results Storage & Retention](#results-storage--retention)
10. [Development Phases](#development-phases)
11. [Project Structure](#project-structure)
12. [Deployment](#deployment)
13. [Testing & CI/CD](#testing--cicd)
14. [Logging & Monitoring](#logging--monitoring)
15. [Security Considerations](#security-considerations)
16. [Data Privacy & Research Use](#data-privacy--research-use)
17. [Model Configuration](#model-configuration)
18. [Reference: Existing Pipeline](#reference-existing-pipeline)

---

## Core Functionality

### What the Pipeline Does

1. **Segmentation**: Automatically segments knee MRI into anatomical structures (femur, tibia, patella, cartilage regions)
2. **3D Surface Extraction**: Creates mesh representations of bones and cartilage
3. **Cartilage Thickness**: Computes mean thickness metrics by anatomical region
4. **T2 Mapping**: Generates T2 relaxation maps and computes mean T2 values (DICOM input only)
5. **Neural Shape Model (NSM)**: Fits a learned shape model to the femur/cartilage
6. **BScore Computation**: Derives an osteoarthritis severity score from the NSM latent vector

### Input Requirements

- **File Formats Accepted**:
  - `.zip` containing a **single** DICOM series folder (multi-series not supported)
  - `.zip` containing NIfTI/NRRD file
  - Single `.nii` or `.nii.gz` file
  - Single `.nrrd` file
  - Single `.dcm` file (3D DICOM)

- **Maximum File Size**: 600 MB (configurable)

> **DICOM Note**: Only single-series DICOM folders are accepted. If a zip contains multiple series, the upload will be rejected with an error message. T2 mapping is only performed for qDESS sequences with the required private tags (GL_AREA, TG).

### Output

A zip file (`{input_name}_results.zip`) containing:
- Segmentation masks (`.nii.gz`, `.nrrd`)
- Segmentation with subregions
- 3D mesh files (`.vtk`) for bones and cartilage
- NSM-preprocessed meshes (original mesh transformed for NSM fitting: flipped if left knee, clipped)
- NSM-reconstructed meshes (shape model output - regularized version conforming to learned patterns)
- T2 maps (if DICOM input with required tags)
- Results summary (`results.csv`, `results.json`)
- NSM parameters and BScore (`NSM_recon_params.json`)

> **Note**: Both preprocessed and reconstructed meshes are included so users can compare original vs. shape-model-fitted surfaces (this is how ASSD reconstruction error is computed).

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    FRONTEND (Vanilla JS)                         │
│  index.html + styles.css + app.js                               │
│                                                                  │
│  Components:                                                     │
│  • File upload dropzone (FilePond or Dropzone.js)               │
│  • Configuration form (model selection, options)                │
│  • Queue position display                                       │
│  • Progress indicator                                           │
│  • Download button (user-initiated, not auto-download)          │
│  • Usage statistics display                                     │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           │ HTTP REST API
                           │ WebSocket (Phase 2+)
                           │
┌──────────────────────────▼──────────────────────────────────────┐
│                    BACKEND (FastAPI)                             │
│                                                                  │
│  Endpoints:                                                      │
│  • POST /upload      - Receive file + options, return job_id    │
│  • GET  /status/{id} - Return progress, queue position, ETA     │
│  • GET  /download/{id} - Return results zip                     │
│  • GET  /stats       - Return usage statistics                  │
│  • WS   /ws/{id}     - Real-time progress updates (Phase 2)     │
│                                                                  │
│  Services:                                                       │
│  • File validation and storage                                  │
│  • Job management                                               │
│  • Statistics tracking                                          │
└──────────────────────────┬──────────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────────┐
│              JOB QUEUE (Celery + Redis)                          │
│                                                                  │
│  Features:                                                       │
│  • FIFO queue with position tracking                            │
│  • Estimated time calculation (rolling average)                 │
│  • Single worker (GPU constraint)                               │
│  • Job status persistence in Redis                              │
│  • Survives server restarts                                     │
│  • Automatic task retry on failure                              │
└──────────────────────────┬──────────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────────┐
│                  PROCESSING WORKER                               │
│                                                                  │
│  Phase 1: Dummy worker                                          │
│  • Validates input format                                       │
│  • Creates zeroed copy of image                                 │
│  • Returns results zip                                          │
│                                                                  │
│  Phase 3: Real pipeline                                         │
│  • dosma_knee_seg.py (orchestrator)                             │
│  • seg_thick_t2_pipeline.py (segmentation, meshes, thickness)   │
│  • NSM_analysis.py / NSM_analysis_bone_only.py (shape model)    │
└─────────────────────────────────────────────────────────────────┘
```

---

## Technology Stack

| Component | Technology | Rationale |
|-----------|------------|-----------|
| **Backend Framework** | FastAPI | Native async, automatic API docs, excellent for ML workloads, Python-native |
| **Frontend** | Vanilla HTML/CSS/JS | Simple, no build step, easy to deploy, sufficient for single-page app |
| **File Upload** | FilePond or Dropzone.js | Mature libraries with drag-drop, progress, and validation |
| **Job Queue** | Celery + Redis | Production-grade, persistent, handles restarts gracefully |
| **Message Broker** | Redis | Fast, reliable, also used for caching |
| **Real-time Updates** | WebSocket (FastAPI native) | Built-in support, ~20 lines of code |
| **Deployment** | Docker + NVIDIA Container Toolkit | Reproducible environment, GPU support, portable |

---

## User Interface

### Main Page Layout

```
┌─────────────────────────────────────────────────────────────────┐
│  🦴 Knee MRI Analysis Pipeline                                   │
│                                                                  │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  📁 Drop your MRI data here                               │  │
│  │     or click to browse                                    │  │
│  │                                                           │  │
│  │  Accepted: .zip, .nii.gz, .nrrd, .dcm                     │  │
│  └───────────────────────────────────────────────────────────┘  │
│                                                                  │
│  ┌─ Configuration ──────────────────────────────────────────┐   │
│  │                                                           │   │
│  │  Email (optional):   [_________________________]         │   │
│  │  For usage tracking and to receive your download link    │   │
│  │                                                           │   │
│  │  Segmentation Model:  [nnU-Net FullRes        ▼]         │   │
│  │                                                           │   │
│  │  ☑ Perform Shape Modeling (NSM)                          │   │
│  │                                                           │   │
│  │  NSM Type:  ○ Bone + Cartilage  ○ Bone Only  ○ Both      │   │
│  │                                                           │   │
│  └───────────────────────────────────────────────────────────┘  │
│                                                                  │
│  ☑ Allow anonymized results to be retained for research         │
│                                                                  │
│  [ Process Data ]                                               │
│                                                                  │
│  ─────────────────────────────────────────────────────────────  │
│  📊 1,247 images processed | 342 users | Avg time: 4.2 min      │
│                                                                  │
│  ⚠️ Disclaimer: Research use only. Not for clinical diagnosis.  │
└─────────────────────────────────────────────────────────────────┘
```

### Processing State

```
┌─────────────────────────────────────────────────────────────────┐
│  Processing: patient_001_qdess.nii.gz                           │
│                                                                  │
│  ⚠️ Please keep this page open until processing completes.      │
│                                                                  │
│  Queue Position: #2 of 5                                        │
│  Estimated Wait: ~8 minutes                                     │
│                                                                  │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │ ████████████████████░░░░░░░░░░░░░░░░░░░░  45%             │  │
│  │ Step 2/4: Creating 3D meshes...                           │  │
│  └───────────────────────────────────────────────────────────┘  │
│                                                                  │
│  [ Cancel ]                                                     │
└─────────────────────────────────────────────────────────────────┘
```

### Completed State

```
┌─────────────────────────────────────────────────────────────────┐
│  ✅ Processing Complete!                                        │
│                                                                  │
│  File: patient_001_qdess.nii.gz                                 │
│  Duration: 3 minutes 42 seconds                                 │
│                                                                  │
│  [ ⬇️ Download Results (24.5 MB) ]                              │
│                                                                  │
│  ⏰ Download available for 24 hours.                            │
│  ⚠️ Do not reload this page until you have downloaded your      │
│     results - you may lose access to your download link.        │
│                                                                  │
│  [ Process Another ]                                            │
└─────────────────────────────────────────────────────────────────┘
```

### Configuration Options

| Option | UI Element | Values | Default |
|--------|------------|--------|---------|
| **Email** | Text input (optional) | Valid email address | Empty |
| **Segmentation Model** | Dropdown | See below | `nnU-Net FullRes` |
| **Perform Shape Modeling** | Checkbox | On/Off | On |
| **NSM Type** | Radio buttons (visible when NSM on) | Bone + Cartilage, Bone Only, Both | Bone + Cartilage |
| **Retain Results for Research** | Checkbox | On/Off | On |

> **Note**: Email is optional but encouraged. It enables us to send download links (useful for long processing times), track usage for grant reporting, and contact users about service updates or research opportunities. Cartilage smoothing parameter (`image_smooth_var_cart`) is accepted by the API but not exposed in the UI.

#### Segmentation Model Options

| Display Name | Internal Value | Description |
|--------------|----------------|-------------|
| nnU-Net FullRes | `nnunet_fullres` | High-performance deep learning (recommended) |
| nnU-Net Cascade | `nnunet_cascade` | Two-stage nnU-Net for complex cases |
| DOSMA Sagittal | `goyal_sagittal` | 2D U-Net, sagittal slices |
| DOSMA Coronal | `goyal_coronal` | 2D U-Net, coronal slices |
| DOSMA Axial | `goyal_axial` | 2D U-Net, axial slices |
| DOSMA STAPLE | `staple` | Ensemble of all DOSMA orientations |

---

## API Endpoints

### GET `/health`

Health check endpoint for monitoring and container orchestration.

**Response (healthy):**
```json
{
  "status": "healthy",
  "redis": "connected",
  "worker": "available",
  "gpu": "available",
  "timestamp": "2025-01-15T10:30:00Z"
}
```

**Response (unhealthy):**
```json
{
  "status": "unhealthy",
  "redis": "disconnected",
  "worker": "unavailable",
  "gpu": "unavailable",
  "error": "Redis connection failed"
}
```

### POST `/upload`

Upload a file and start processing.

**Request:**
```
Content-Type: multipart/form-data

file: <binary>
email: "user@example.com"   # Optional, for tracking and notifications
segmentation_model: "nnunet_fullres"
perform_nsm: true
nsm_type: "bone_and_cart"  # "bone_and_cart" | "bone_only" | "both"
retain_results: true        # Allow anonymized results to be retained for research
cartilage_smoothing: 0.3125 # Optional, not exposed in UI, uses default if omitted
```

**Response:**
```json
{
  "job_id": "abc123-def456",
  "status": "queued",
  "queue_position": 3,
  "estimated_wait_seconds": 480,
  "message": "File uploaded successfully. You are #3 in queue."
}
```

### GET `/status/{job_id}`

Get current status of a processing job.

**Response (queued):**
```json
{
  "job_id": "abc123-def456",
  "status": "queued",
  "queue_position": 2,
  "estimated_wait_seconds": 320
}
```

**Response (processing):**
```json
{
  "job_id": "abc123-def456",
  "status": "processing",
  "progress_percent": 45,
  "current_step": 2,
  "total_steps": 4,
  "step_name": "Creating 3D meshes",
  "elapsed_seconds": 120,
  "estimated_remaining_seconds": 150
}
```

**Response (complete):**
```json
{
  "job_id": "abc123-def456",
  "status": "complete",
  "download_url": "/download/abc123-def456",
  "result_size_bytes": 25690112,
  "processing_time_seconds": 222
}
```

**Response (error):**
```json
{
  "job_id": "abc123-def456",
  "status": "error",
  "error_message": "Invalid file format. Expected medical image.",
  "error_code": "INVALID_FORMAT"
}
```

### GET `/download/{job_id}`

Download the results zip file.

**Response:**
- Content-Type: `application/zip`
- Content-Disposition: `attachment; filename="patient_001_results.zip"`

### GET `/stats`

Get usage statistics for display on the main page.

**Response:**
```json
{
  "total_jobs_processed": 1247,
  "total_jobs_today": 23,
  "unique_users": 342,
  "average_processing_time_seconds": 252,
  "jobs_in_queue": 3,
  "uptime_hours": 168
}
```

### WebSocket `/ws/{job_id}` (Phase 2+)

Real-time progress updates.

**Messages from server:**
```json
{
  "type": "progress",
  "progress_percent": 45,
  "current_step": 2,
  "total_steps": 4,
  "step_name": "Creating 3D meshes"
}
```

```json
{
  "type": "complete",
  "download_url": "/download/abc123-def456"
}
```

---

## Processing Pipeline

### Pipeline Steps

| Step | Description | Approx. Time |
|------|-------------|--------------|
| 1 | **Segmentation**: Run model to segment structures | 60-120s |
| 2 | **Mesh Creation**: Extract 3D surfaces, compute thickness | 30-60s |
| 3 | **T2 Mapping**: Generate T2 map and compute metrics (DICOM only) | 10-20s |
| 4 | **Shape Modeling**: Fit NSM, compute BScore | 60-90s |

### Configuration Mapping

Website options map to `config.json` parameters:

| Website Option | Config Parameter |
|----------------|------------------|
| Segmentation Model | `default_seg_model` + `nnunet.type` |
| Perform NSM (bone+cart) | `perform_bone_and_cart_nsm` |
| Perform NSM (bone only) | `perform_bone_only_nsm` |
| Cartilage Smoothing (API only) | Passed to `calc_cartilage_thickness(image_smooth_var_cart=X)` - default: 0.3125 |

### Dummy Worker (Phase 1)

For initial development, the worker validates input and returns a zeroed image:

```python
def dummy_pipeline(input_path: str, options: dict, output_dir: Path) -> Path:
    """
    Dummy worker for Phase 1 development.
    
    1. Validate input is a valid medical image format
    2. Load the image
    3. Create a zeroed copy (same dimensions, metadata)
    4. Save to output directory
    5. Create results zip
    6. Return path to zip file
    """
    import SimpleITK as sitk
    import shutil
    
    # Validate
    valid_extensions = {'.nii', '.nii.gz', '.nrrd', '.dcm'}
    if not any(input_path.lower().endswith(ext) for ext in valid_extensions):
        raise ValueError(f"Invalid file format. Accepted: {valid_extensions}")
    
    # Load
    img = sitk.ReadImage(str(input_path))
    
    # Create zeroed copy
    zeroed = sitk.Image(img.GetSize(), img.GetPixelID())
    zeroed.CopyInformation(img)
    
    # Save
    input_stem = Path(input_path).stem.replace('.nii', '')
    result_dir = output_dir / f"{input_stem}_results"
    result_dir.mkdir(parents=True, exist_ok=True)
    
    sitk.WriteImage(zeroed, str(result_dir / "zeroed_image.nii.gz"))
    
    # Also save a dummy results.json
    results = {
        "status": "dummy_processing",
        "input_file": Path(input_path).name,
        "options": options,
        "message": "This is a dummy result from Phase 1 development"
    }
    with open(result_dir / "results.json", "w") as f:
        json.dump(results, f, indent=2)
    
    # Zip results
    zip_path = shutil.make_archive(str(result_dir), 'zip', result_dir)
    
    return Path(zip_path)
```

---

## Job Queue System

### Implementation (Celery + Redis)

Using Celery with Redis provides production-grade job queuing with persistence, automatic retries, and graceful handling of server restarts.

**Celery Configuration (`backend/workers/celery_app.py`):**

```python
from celery import Celery

celery_app = Celery(
    "knee_pipeline",
    broker="redis://localhost:6379/0",
    backend="redis://localhost:6379/1",
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,  # Track when task starts processing
    worker_concurrency=1,      # Single GPU worker
    task_acks_late=True,       # Acknowledge after completion (handles crashes)
)
```

**Job Model (`backend/models/job.py`):**

```python
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Optional
import json
import redis

@dataclass
class Job:
    id: str
    input_path: str
    options: dict
    status: str  # "queued", "processing", "complete", "error"
    created_at: str  # ISO format for JSON serialization
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    progress_percent: int = 0
    current_step: int = 0
    total_steps: int = 4
    step_name: str = ""
    result_path: Optional[str] = None
    error_message: Optional[str] = None
    
    def save(self, redis_client: redis.Redis):
        """Persist job state to Redis."""
        redis_client.hset("jobs", self.id, json.dumps(asdict(self)))
    
    @classmethod
    def load(cls, job_id: str, redis_client: redis.Redis) -> Optional["Job"]:
        """Load job from Redis."""
        data = redis_client.hget("jobs", job_id)
        if data:
            return cls(**json.loads(data))
        return None
```

**Pipeline Task (`backend/workers/tasks.py`):**

```python
from celery import current_task
from .celery_app import celery_app
from ..models.job import Job
import redis

redis_client = redis.Redis(host='localhost', port=6379, db=1)

@celery_app.task(bind=True)
def process_pipeline(self, job_id: str, input_path: str, options: dict):
    """Main pipeline task executed by Celery worker."""
    job = Job.load(job_id, redis_client)
    job.status = "processing"
    job.started_at = datetime.now().isoformat()
    job.save(redis_client)
    
    try:
        # Update progress through steps
        steps = [
            ("Validating input", validate_input),
            ("Running segmentation", run_segmentation),
            ("Creating meshes", create_meshes),
            ("Fitting shape model", fit_nsm),
        ]
        
        for i, (step_name, step_func) in enumerate(steps):
            job.current_step = i + 1
            job.step_name = step_name
            job.progress_percent = int((i / len(steps)) * 100)
            job.save(redis_client)
            
            step_func(input_path, options)
        
        # Complete
        job.status = "complete"
        job.progress_percent = 100
        job.completed_at = datetime.now().isoformat()
        job.result_path = f"/results/{job_id}_results.zip"
        job.save(redis_client)
        
    except Exception as e:
        job.status = "error"
        job.error_message = str(e)
        job.save(redis_client)
        raise
```

**Queue Position Calculation:**

```python
def get_queue_position(job_id: str) -> int:
    """Get position in queue (1-indexed, 0 if not queued)."""
    # Get all queued jobs from Redis, sorted by created_at
    all_jobs = redis_client.hgetall("jobs")
    queued = [
        Job(**json.loads(data)) 
        for data in all_jobs.values()
        if json.loads(data)["status"] == "queued"
    ]
    queued.sort(key=lambda j: j.created_at)
    
    for i, job in enumerate(queued):
        if job.id == job_id:
            return i + 1
    return 0

def get_estimated_wait(job_id: str) -> float:
    """Estimate wait time based on queue position and rolling average."""
    position = get_queue_position(job_id)
    avg_time = get_average_processing_time()
    return position * avg_time

def get_average_processing_time() -> float:
    """Get rolling average of last 20 processing times."""
    times = redis_client.lrange("processing_times", 0, 19)
    if not times:
        return 240  # Default 4 minutes
    return sum(float(t) for t in times) / len(times)
```

### Queue Position Display

The frontend polls `/status/{job_id}` and displays:
- "You are #3 in queue"
- "Estimated wait: ~8 minutes"

Estimated time is calculated from rolling average of last 20 job processing times.

### Statistics Tracking

Track and persist:
- Total jobs processed (all time)
- Jobs processed today
- Processing times per job (for averaging)
- Processing times per step (for detailed estimates)

---

## File Handling

### Upload Flow

```
User selects file
       │
       ▼
Frontend validates extension
(.zip, .nii, .nii.gz, .nrrd, .dcm)
       │
       ▼
Upload to server via POST /upload
       │
       ▼
Backend saves to temp directory
       │
       ▼
If .zip: Extract contents
       │
       ▼
Validate medical image format
       │
       ▼
Create job, add to queue
       │
       ▼
Return job_id to frontend
```

### File Validation

```python
def validate_medical_image(path: Path) -> tuple[bool, str]:
    """
    Validate that path is a readable medical image.
    
    Handles:
    - Single 3D files: NIfTI (.nii, .nii.gz), NRRD (.nrrd), single 3D DICOM
    - DICOM series: Folder containing multiple 2D DICOM slices
    
    Returns:
        (is_valid, error_message)
    """
    import SimpleITK as sitk
    
    try:
        if path.is_dir():
            # DICOM series - folder with multiple slices
            reader = sitk.ImageSeriesReader()
            dicom_files = reader.GetGDCMSeriesFileNames(str(path))
            
            if not dicom_files:
                return False, "No DICOM files found in directory"
            
            if len(dicom_files) < 10:
                return False, f"DICOM series too short ({len(dicom_files)} slices). Expected 3D volume."
            
            # Try to read series info
            reader.SetFileNames(dicom_files)
            reader.ReadImageInformation()
            return True, ""
            
        else:
            # Single file (NIfTI, NRRD, or single 3D DICOM)
            reader = sitk.ImageFileReader()
            reader.SetFileName(str(path))
            reader.ReadImageInformation()
            
            # Check dimensions (should be 3D)
            dims = reader.GetDimension()
            if dims < 3:
                return False, f"Image is {dims}D, expected 3D volume"
            
            # Check size is reasonable
            size = reader.GetSize()
            if any(s < 10 for s in size[:3]):
                return False, f"Image dimensions too small: {size}"
                
            return True, ""
            
    except Exception as e:
        return False, f"Failed to read image: {str(e)}"
```

### Zip Handling

```python
def process_upload(uploaded_file: Path, temp_dir: Path) -> Path:
    """Process uploaded file, extract if zip, return path to image."""
    
    if uploaded_file.suffix == '.zip':
        # Extract zip
        extract_dir = temp_dir / "extracted"
        shutil.unpack_archive(uploaded_file, extract_dir)
        
        # Find medical image in extracted contents
        for root, dirs, files in os.walk(extract_dir):
            for file in files:
                file_path = Path(root) / file
                # Check for valid medical image extensions (handle .nii.gz properly)
                if file.endswith(('.nii', '.nii.gz', '.nrrd', '.dcm')):
                    return file_path
            
            # Check if directory contains DICOM series
            if is_dicom_directory(Path(root)):
                return Path(root)
        
        raise ValueError("No valid medical image found in zip file")
    
    else:
        return uploaded_file
```

---

## Results Storage & Retention

### Storage Architecture

Results are stored in AWS S3 (or S3-compatible storage) with automatic lifecycle management:

```
┌─────────────────────────────────────────────────────────────────┐
│                    S3 BUCKET: knee-pipeline-results             │
│                                                                  │
│  ├── downloads/                    # User-downloadable results  │
│  │   └── {job_id}/                                              │
│  │       └── {input_name}_results.zip                           │
│  │       (Auto-deleted after 24 hours via lifecycle policy)     │
│  │                                                              │
│  └── research/                     # Retained for research      │
│      └── {job_id}/                 (Only if user consented)     │
│          ├── segmentation.nii.gz   # No pixel data              │
│          ├── meshes/*.vtk                                       │
│          ├── thickness_results.csv                              │
│          └── nsm_params.json                                    │
└─────────────────────────────────────────────────────────────────┘
```

### Download Links

- Results are available for download via **pre-signed S3 URLs** (more secure than exposing job_id)
- Download links expire after **24 hours**
- After expiration, the `downloads/` folder results are automatically deleted from S3

> **Note**: The 24-hour expiration applies only to the downloadable results zip. If the user consented to research retention, the derived data (segmentations, meshes, metrics) in the `research/` folder is kept **indefinitely** for research purposes.

**Pre-signed URL Generation:**

```python
import boto3
from datetime import timedelta

def generate_download_url(job_id: str, filename: str) -> str:
    """Generate a pre-signed URL for downloading results."""
    s3_client = boto3.client('s3')
    
    url = s3_client.generate_presigned_url(
        'get_object',
        Params={
            'Bucket': 'knee-pipeline-results',
            'Key': f'downloads/{job_id}/{filename}'
        },
        ExpiresIn=86400  # 24 hours in seconds
    )
    return url
```

### S3 Lifecycle Policy

```json
{
  "Rules": [
    {
      "ID": "Delete downloads after 24 hours",
      "Status": "Enabled",
      "Filter": {
        "Prefix": "downloads/"
      },
      "Expiration": {
        "Days": 1
      }
    }
  ]
}
```

> **Important**: The `research/` prefix has **no expiration policy** - consented research data is retained indefinitely.

### Research Data Retention

When users consent to research data retention (checkbox enabled by default):

- **Only derived data is retained** - no original pixel data
- **Retained indefinitely**: Segmentation masks, meshes, thickness metrics, NSM parameters
- **Not retained**: Original MRI images, T2 maps (contain pixel data)
- **Purpose**: Building research datasets, improving models, publishing aggregate statistics
- **Storage**: `research/{job_id}/` in S3 (no expiration policy)

---

## Development Phases

### Phase 1: MVP (~1 week)

**Goal**: End-to-end flow with dummy processing

- [ ] FastAPI backend setup
  - [ ] Project structure
  - [ ] `/upload` endpoint
  - [ ] `/status/{job_id}` endpoint
  - [ ] `/download/{job_id}` endpoint
  - [ ] `/stats` endpoint
  - [ ] File validation (single files and DICOM series)

- [ ] Celery + Redis job queue
  - [ ] Redis setup (docker or local install)
  - [ ] Celery worker configuration
  - [ ] Job model with Redis persistence
  - [ ] FIFO queue with position tracking

- [ ] Dummy processing worker
  - [ ] Validate input format
  - [ ] Create zeroed image copy
  - [ ] Package results zip

- [ ] Vanilla JS frontend
  - [ ] HTML page with upload form
  - [ ] FilePond or Dropzone integration
  - [ ] Configuration options (model, NSM, smoothing)
  - [ ] Status polling and display
  - [ ] Download button
  - [ ] Basic styling

### Phase 2: Progress & Statistics (~3-5 days)

**Goal**: Polish progress display, add usage statistics, and improve session persistence

- [ ] Progress updates via HTTP polling
  - [ ] Frontend polls `/status/{job_id}` every 2 seconds
  - [ ] Update progress bar and step name
  - [ ] Show queue position and ETA
  - [ ] (WebSocket can be added later if needed, but polling is simpler and works through proxies)

- [ ] Time estimation
  - [ ] Track processing times per job in Redis
  - [ ] Rolling average calculation (last 20 jobs)
  - [ ] Display ETA on frontend

- [ ] Usage statistics
  - [ ] Track total jobs processed
  - [ ] Display on homepage
  - [ ] Persist in Redis across restarts

- [ ] Session persistence via localStorage
  - [ ] Store job_id in browser localStorage when processing starts
  - [ ] On page load, check for pending job and show "Resume previous job?" prompt
  - [ ] Clear localStorage when download completes or job expires
  - [ ] Allows users to return after browser close (within 24-hour window)

### Phase 3: Real Pipeline Integration (~1 week)

**Goal**: Connect actual segmentation pipeline

- [ ] Replace dummy worker with real pipeline
  - [ ] Call `dosma_knee_seg.py` subprocess
  - [ ] Pass configuration options
  - [ ] Handle pipeline errors gracefully

- [ ] Configuration mapping
  - [ ] Generate `config.json` from web options
  - [ ] Model path resolution

- [ ] GPU management
  - [ ] Ensure single job at a time
  - [ ] Memory cleanup between jobs

- [ ] Error handling
  - [ ] Invalid input detection
  - [ ] Pipeline failure recovery
  - [ ] User-friendly error messages

### Phase 4: Future Enhancements

- [ ] 3D mesh preview (VTK.js or Three.js)
- [ ] Results dashboard with metrics table
- [ ] User authentication
- [ ] Job history per user
- [ ] Email notifications for download links
  - [ ] Optional email field in upload form
  - [ ] Send download link when processing completes
  - [ ] Allows users to close browser and receive results via email
- [ ] Horizontal scaling (multiple GPU workers)

---

## Project Structure

```
kneepipeline_segmentation_website/
│
├── .github/
│   └── workflows/
│       ├── test.yml            # Run tests on push/PR
│       └── docker-build.yml    # Validate Docker builds
│
├── backend/
│   ├── main.py                 # FastAPI app entry point
│   ├── config.py               # Server configuration
│   ├── requirements.txt        # Python dependencies
│   │
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── upload.py           # POST /upload
│   │   ├── status.py           # GET /status/{job_id}
│   │   ├── download.py         # GET /download/{job_id}
│   │   └── stats.py            # GET /stats
│   │
│   ├── services/
│   │   ├── __init__.py
│   │   ├── job_queue.py        # Job queue management
│   │   ├── file_handler.py     # File validation, zip handling
│   │   ├── statistics.py       # Usage stats tracking
│   │   └── pipeline.py         # Pipeline execution wrapper
│   │
│   ├── workers/
│   │   ├── __init__.py
│   │   ├── celery_app.py       # Celery configuration
│   │   ├── tasks.py            # Celery task definitions
│   │   ├── dummy_worker.py     # Phase 1 dummy processor
│   │   └── pipeline_worker.py  # Phase 3 real pipeline
│   │
│   └── models/
│       ├── __init__.py
│       └── job.py              # Job dataclass/model
│
├── frontend/
│   ├── index.html              # Main page
│   ├── css/
│   │   └── styles.css          # Custom styles
│   ├── js/
│   │   └── app.js              # Upload logic, polling, UI updates
│   └── assets/
│       └── (images, icons)
│
├── kneepipeline/               # Existing pipeline (submodule or copy)
│   ├── dosma_knee_seg.py
│   ├── seg_thick_t2_pipeline.py
│   ├── NSM_analysis.py
│   ├── NSM_analysis_bone_only.py
│   ├── config.json
│   ├── utils.py
│   ├── DEPENDENCIES/
│   │   └── nnunet_knee_inference/  # nnU-Net inference code (see below)
│   └── ...
│
├── docker/
│   ├── Dockerfile              # GPU-enabled Python image
│   ├── docker-compose.yml      # Full stack (app + redis if needed)
│   └── .dockerignore
│
├── data/                       # Runtime data (gitignored)
│   ├── uploads/                # Temporary upload storage (deleted after processing)
│   ├── temp/                   # Temporary processing workspace (cleaned up after each job)
│   └── logs/                   # Application logs (daily rotation, 30-day retention)
│
├── tests/
│   ├── conftest.py             # Pytest fixtures
│   ├── test_upload.py
│   ├── test_job_queue.py
│   └── test_file_handler.py
│
├── PROJECT_OVERVIEW.md         # This document
├── README.md                   # Quick start guide
├── pyproject.toml              # Linting and pytest configuration
└── .gitignore
```

---

## Deployment

### Development (Local)

```bash
# 1. Start Redis (via Docker - should already be running from Stage 0)
docker start redis  # If not already running
docker exec redis redis-cli ping  # Verify with PONG

# 2. Backend - Terminal 1
conda activate kneepipeline
cd ~/programming/kneepipeline_segmentaton_website
pip install -r backend/requirements.txt  # First time only
uvicorn backend.main:app --reload --port 8000

# 3. Celery Worker - Terminal 2
conda activate kneepipeline
cd ~/programming/kneepipeline_segmentaton_website
celery -A backend.workers.celery_app worker --loglevel=info --concurrency=1

# Frontend is served by FastAPI from frontend/ directory
```

### Production (Docker)

```dockerfile
# docker/Dockerfile
FROM nvidia/cuda:11.8-cudnn8-runtime-ubuntu22.04

# Install Python
RUN apt-get update && apt-get install -y python3.10 python3-pip

# Install dependencies
WORKDIR /app
COPY backend/requirements.txt .
RUN pip install -r requirements.txt

# Copy application
COPY backend/ ./backend/
COPY frontend/ ./frontend/
COPY kneepipeline/ ./kneepipeline/

# Expose port
EXPOSE 8000

# Run
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

```yaml
# docker/docker-compose.yml
services:
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    command: redis-server --appendonly yes  # Persist data
    
  web:
    build:
      context: ..
      dockerfile: docker/Dockerfile
    ports:
      - "8000:8000"
    volumes:
      - ../data:/app/data
      - /models:/models:ro  # Model weights (read-only)
    depends_on:
      - redis
    environment:
      - REDIS_URL=redis://redis:6379
      - S3_BUCKET=knee-pipeline-results
      - AWS_ACCESS_KEY_ID=${AWS_ACCESS_KEY_ID}
      - AWS_SECRET_ACCESS_KEY=${AWS_SECRET_ACCESS_KEY}
      - AWS_REGION=us-west-2
      
  worker:
    build:
      context: ..
      dockerfile: docker/Dockerfile
    command: celery -A backend.workers.celery_app worker --loglevel=info --concurrency=1
    volumes:
      - ../data:/app/data
      - /models:/models:ro  # Model weights (read-only)
    depends_on:
      - redis
    environment:
      - REDIS_URL=redis://redis:6379
      - S3_BUCKET=knee-pipeline-results
      - AWS_ACCESS_KEY_ID=${AWS_ACCESS_KEY_ID}
      - AWS_SECRET_ACCESS_KEY=${AWS_SECRET_ACCESS_KEY}
      - AWS_REGION=us-west-2
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]

volumes:
  redis_data:
```

### GPU Server Requirements

- NVIDIA GPU with CUDA support
- nvidia-container-toolkit installed
- Sufficient VRAM for model (8GB+ recommended)
- Storage for uploads and results

---

## Testing & CI/CD

### Test Strategy

Tests are organized into three levels:

| Level | Purpose | When Run |
|-------|---------|----------|
| **Unit Tests** | Test individual functions (file validation, job model, etc.) | Every push |
| **Integration Tests** | Test API endpoints with Redis | Every push |
| **End-to-End Tests** | Full upload → process → download flow | Pre-release |

### Running Tests Locally

```bash
# Start Redis (required for integration tests)
docker run -d --name redis -p 6379:6379 redis:7-alpine

# Run all tests
conda activate kneepipeline
cd ~/programming/kneepipeline_segmentaton_website
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=backend --cov-report=html

# Run specific test file
pytest tests/test_upload.py -v

# Run linter (already installed via requirements.txt)
ruff check backend/ tests/
```

### GitHub Actions CI/CD

Automated tests run on every push and pull request to `main` and `develop` branches.

**Workflow File**: `.github/workflows/test.yml`

```yaml
name: Tests

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main, develop]

jobs:
  test:
    runs-on: ubuntu-latest
    
    services:
      redis:
        image: redis:7-alpine
        ports:
          - 6379:6379
        options: >-
          --health-cmd "redis-cli ping"
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5

    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.10'
          cache: 'pip'
          cache-dependency-path: backend/requirements.txt

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r backend/requirements.txt

      - name: Run tests
        env:
          REDIS_URL: redis://localhost:6379/0
        run: |
          pytest tests/ -v --tb=short

      - name: Upload coverage report
        uses: actions/upload-artifact@v4
        if: always()
        with:
          name: coverage-report
          path: htmlcov/
          retention-days: 7

  lint:
    runs-on: ubuntu-latest
    
    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.10'

      - name: Install linting tools
        run: |
          pip install ruff

      - name: Run linter
        run: |
          ruff check backend/ tests/
```

**Docker Build Validation**: `.github/workflows/docker-build.yml`

```yaml
name: Docker Build

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  build:
    runs-on: ubuntu-latest
    
    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3

      - name: Build Docker image
        uses: docker/build-push-action@v5
        with:
          context: .
          file: docker/Dockerfile
          push: false
          tags: knee-pipeline:test
          cache-from: type=gha
          cache-to: type=gha,mode=max
```

### Linting Configuration

**File**: `pyproject.toml`

```toml
[tool.ruff]
target-version = "py310"
line-length = 100
select = [
    "E",   # pycodestyle errors
    "W",   # pycodestyle warnings
    "F",   # Pyflakes
    "I",   # isort
    "B",   # flake8-bugbear
    "C4",  # flake8-comprehensions
]
ignore = [
    "E501",  # line too long (handled by formatter)
]

[tool.ruff.per-file-ignores]
"tests/*" = ["B011"]  # Allow assert in tests

[tool.pytest.ini_options]
testpaths = ["tests"]
asyncio_mode = "auto"
addopts = "-v --tb=short"
```

### CI/CD Pipeline Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                    GitHub Actions CI/CD                          │
│                                                                  │
│  Push/PR to main or develop                                      │
│       │                                                          │
│       ▼                                                          │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐          │
│  │    Lint     │    │    Test     │    │Docker Build │          │
│  │   (ruff)    │    │  (pytest)   │    │ (optional)  │          │
│  └─────────────┘    └─────────────┘    └─────────────┘          │
│       │                   │                   │                  │
│       └───────────────────┼───────────────────┘                  │
│                           ▼                                      │
│                    All checks pass                               │
│                           │                                      │
│                           ▼                                      │
│                    Merge allowed                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Logging & Monitoring

### Logging Strategy

Application logs are written to daily rotating files with 30-day retention. No external logging service is required initially.

**Configuration (`backend/config.py`):**

```python
import logging
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path
import json
from datetime import datetime

LOG_DIR = Path("/app/data/logs")
LOG_DIR.mkdir(parents=True, exist_ok=True)

class JSONFormatter(logging.Formatter):
    """Structured JSON logging for easier parsing."""
    def format(self, record):
        log_data = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "request_id": getattr(record, 'request_id', None),
            "job_id": getattr(record, 'job_id', None),
        }
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_data)

def setup_logging():
    """Configure application logging."""
    handler = TimedRotatingFileHandler(
        LOG_DIR / "app.log",
        when="midnight",
        interval=1,
        backupCount=30,  # Keep 30 days of logs
    )
    handler.setFormatter(JSONFormatter())
    
    logging.basicConfig(
        level=logging.INFO,
        handlers=[handler, logging.StreamHandler()]
    )
```

**Request ID Middleware:**

```python
import uuid
from fastapi import Request

@app.middleware("http")
async def add_request_id(request: Request, call_next):
    """Add unique request ID for tracing."""
    request_id = str(uuid.uuid4())[:8]
    request.state.request_id = request_id
    
    # Add to logging context
    logger = logging.getLogger()
    old_factory = logging.getLogRecordFactory()
    
    def record_factory(*args, **kwargs):
        record = old_factory(*args, **kwargs)
        record.request_id = request_id
        return record
    
    logging.setLogRecordFactory(record_factory)
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response
```

### Log Files

```
data/logs/
├── app.log           # Current day's logs
├── app.log.2025-01-14  # Previous day
├── app.log.2025-01-13
└── ...               # Up to 30 days retained
```

### What Gets Logged

| Event | Level | Details |
|-------|-------|---------|
| File upload | INFO | job_id, filename, size, options |
| Processing start | INFO | job_id, step name |
| Processing complete | INFO | job_id, duration, result size |
| Processing error | ERROR | job_id, error message, stack trace |
| Download | INFO | job_id, client IP |
| Validation failure | WARN | filename, reason |

### Error Handling

When a processing error occurs:

1. Error is logged with full stack trace
2. Job status updated to "error" in Redis
3. Error message returned via `/status/{job_id}` endpoint
4. User sees friendly error message in UI

**Error Response:**
```json
{
  "job_id": "abc123-def456",
  "status": "error",
  "error_message": "Segmentation failed: Unable to detect knee structures. Please ensure the image contains a knee MRI.",
  "error_code": "SEGMENTATION_FAILED"
}
```

### Error Codes

| Code | Description |
|------|-------------|
| `INVALID_FORMAT` | File is not a valid medical image |
| `INVALID_DIMENSIONS` | Image is not 3D or too small |
| `MULTI_SERIES` | DICOM zip contains multiple series |
| `SEGMENTATION_FAILED` | Model could not segment the image |
| `GPU_OOM` | GPU ran out of memory |
| `PIPELINE_ERROR` | General pipeline failure |

---

## Security Considerations

1. **File Validation**: Strictly validate uploaded files before processing
2. **Size Limits**: Enforce 600MB upload limit. If exceeded, show specific error: "File too large (X MB). Maximum allowed: 600 MB. Consider compressing or contact us for large datasets."
3. **Cleanup**: Delete uploaded original images immediately after processing. Download results expire after 24 hours via S3 lifecycle policy.
4. **No Execution**: Never execute uploaded files; only read as data
5. **Anonymization Warning**: Remind users to upload only anonymized data
6. **Terms of Service**: Require agreement before upload
7. **HTTPS**: All production traffic must use HTTPS (configure via reverse proxy, e.g., nginx/Caddy with Let's Encrypt)
8. **Rate Limiting**: Consider adding rate limiting for uploads (e.g., 10 uploads/hour per IP) to prevent abuse
9. **Pre-signed URLs**: Download links use time-limited pre-signed S3 URLs rather than exposing job IDs directly

### CORS Configuration

CORS is configured in FastAPI to allow same-origin requests in production and localhost in development:

```python
from fastapi.middleware.cors import CORSMiddleware

# Development origins
DEV_ORIGINS = [
    "http://localhost:3000",
    "http://localhost:8000",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:8000",
]

# Production: same-origin, no CORS needed when serving frontend from FastAPI
# For development, allow localhost origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=DEV_ORIGINS if DEBUG else [],
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)
```

---

## Data Privacy & Research Use

### Privacy by Design

This pipeline is designed to minimize privacy risk:

1. **No Original Images Retained**: Uploaded MRI pixel data is deleted immediately after processing
2. **Only Derived Data**: Retained research data consists solely of:
   - Segmentation masks (anatomical labels, no pixel intensities)
   - 3D surface meshes (geometric representations only)
   - Quantitative metrics (thickness values, T2 values, shape parameters)
3. **No Re-identification Possible**: Without the original MRI, retained data cannot be used to identify subjects or reconstruct the underlying images

### Research Data Retention

When users consent (opt-in checkbox, enabled by default):

| Data Type | Retained | Purpose |
|-----------|----------|---------|
| Original MRI images | ❌ No | Never stored beyond processing |
| T2 maps | ❌ No | Contains pixel data |
| Segmentation masks | ✅ Yes | Training data for improved models |
| Surface meshes | ✅ Yes | Shape analysis research |
| Thickness metrics | ✅ Yes | Population studies, normative databases |
| NSM parameters | ✅ Yes | Osteoarthritis severity research |

### Email Collection & Usage

Email addresses are collected optionally and stored separately from processing data:

| Purpose | Description |
|---------|-------------|
| **Usage Tracking** | Count unique users for grant reporting and impact metrics |
| **Download Links** | Send results link when processing completes (user can close browser) |
| **Service Updates** | Notify users of downtime, new features, or model improvements |
| **Research Contact** | Reach out about collaboration opportunities (with explicit consent) |

**Email Storage:**
- Stored in Redis with hashed identifier for counting unique users
- Associated with job records for notification purposes
- Never shared with third parties
- Users can request deletion via contact email

### How Retained Data Will Be Used

- **Dataset Creation**: Building open research datasets with anonymized shape/thickness data
- **Model Improvement**: Training better segmentation and shape models
- **Population Studies**: Aggregate statistics published in research papers
- **Collaboration**: Shared with research community under appropriate data use agreements

### User Consent

The upload form includes a clear consent checkbox:

> ☑ **Allow anonymized results to be retained for research**
>
> Only derived data (segmentations, meshes, metrics) will be retained. No original MRI images or identifiable information is stored. Retained data may be used for research and shared with the scientific community.

Users may uncheck this option if they prefer their derived data not be retained.

### Terms of Service

Users must agree to the following before uploading:

1. Research use only - not for clinical diagnosis
2. Upload only anonymized/de-identified data
3. No protected health information (PHI) in filenames
4. Consent to derived data retention (if checkbox selected)

---

## Model Configuration

### Model Weights Storage

Model weights are stored outside the Docker image to keep image size manageable. They are mounted as volumes at runtime.

**Production Directory Structure:**

```
/models/                          # Mounted volume for model weights
├── dosma_weights/
│   ├── sagittal_best_model.h5
│   ├── coronal_best_model.h5
│   └── axial_best_model.h5
├── nnunet_models/
│   └── Dataset500_KneeMRI/
│       ├── nnUNetTrainer__nnUNetPlans__3d_fullres/
│       └── nnUNetTrainer__nnUNetPlans__3d_cascade_fullres/
├── nsm_models/
│   ├── 647_nsm_femur_cartilage_v0.0.1/
│   │   ├── model_config.json
│   │   └── model/2000.pth
│   └── 551_nsm_femur_bone_v0.0.1/
│       ├── model_params_config.json
│       └── model/1150.pth
└── bscore_models/
    ├── NSM_Orig_BScore_Bone_Cartilage_April_17_2025/
    └── NSM_Orig_BScore_Bone_Only_April_18_2025/
```

### Configuration File

The pipeline uses a `config.json` file. The web backend generates this dynamically based on user options:

```python
def generate_config(options: dict, job_dir: Path) -> Path:
    """Generate config.json for a specific job."""
    config = {
        "perform_bone_only_nsm": options.get("nsm_type") in ["bone_only", "both"],
        "perform_bone_and_cart_nsm": options.get("nsm_type") in ["bone_and_cart", "both"],
        "clip_femur_top": True,
        "default_seg_model": options.get("segmentation_model", "nnunet_fullres"),
        "batch_size": 32,
        "models": {
            "goyal_sagittal": "/models/dosma_weights/sagittal_best_model.h5",
            "goyal_coronal": "/models/dosma_weights/coronal_best_model.h5",
            "goyal_axial": "/models/dosma_weights/axial_best_model.h5",
        },
        "nnunet": {
            "type": "fullres" if "fullres" in options.get("segmentation_model", "") else "cascade",
            "model_name": "Dataset500_KneeMRI"
        },
        "nsm": {
            "path_model_config": "/models/nsm_models/647_nsm_femur_cartilage_v0.0.1/model_config.json",
            "path_model_state": "/models/nsm_models/647_nsm_femur_cartilage_v0.0.1/model/2000.pth"
        },
        "bscore": {
            "path_model_folder": "/models/bscore_models/NSM_Orig_BScore_Bone_Cartilage_April_17_2025"
        },
        "nsm_bone_only": {
            "path_model_config": "/models/nsm_models/551_nsm_femur_bone_v0.0.1/model_params_config.json",
            "path_model_state": "/models/nsm_models/551_nsm_femur_bone_v0.0.1/model/1150.pth"
        },
        "bscore_bone_only": {
            "path_model_folder": "/models/bscore_models/NSM_Orig_BScore_Bone_Only_April_18_2025"
        },
        # ... regions and bones config (copied from template)
    }
    
    config_path = job_dir / "config.json"
    with open(config_path, "w") as f:
        json.dump(config, f, indent=2)
    
    return config_path
```

### nnU-Net Dependency

The nnU-Net inference code must be installed separately:

**Repository**: [nnunet_knee_inference](https://github.com/YOUR_ORG/nnunet_knee_inference) (TODO: add actual URL)

**Installation:**
```bash
cd kneepipeline/DEPENDENCIES
git clone https://github.com/YOUR_ORG/nnunet_knee_inference.git
```

The pipeline imports from this directory:
```python
nnunet_path = os.path.join(os.path.dirname(__file__), 'DEPENDENCIES', 'nnunet_knee_inference')
sys.path.append(nnunet_path)
from scripts.inference import KneeSegmentationInference
```

---

## Reference: Existing Pipeline

The website wraps the existing `kneepipeline` which provides:

- **Entry Point**: `dosma_knee_seg.py` - orchestrates the full pipeline
- **Core Processing**: `seg_thick_t2_pipeline.py` - segmentation, meshes, thickness, T2
- **Shape Modeling**: `NSM_analysis.py`, `NSM_analysis_bone_only.py`
- **Utilities**: `utils.py` - helper functions (e.g., `clip_femur_top`)
- **Configuration**: `config.json` - model paths, parameters

### Pipeline Invocation

The website creates a job-specific `config.json` and invokes the pipeline as a subprocess:

```python
import subprocess
from pathlib import Path

def run_pipeline(input_path: Path, output_dir: Path, config_path: Path, model_name: str):
    """Run the segmentation pipeline as a subprocess."""
    command = [
        "python",
        "/app/kneepipeline/dosma_knee_seg.py",
        str(input_path),
        str(output_dir),
        model_name,
    ]
    
    # Set environment to use job-specific config
    env = os.environ.copy()
    env["KNEEPIPELINE_CONFIG"] = str(config_path)
    
    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        env=env,
        timeout=1800,  # 30 minute timeout
    )
    
    if result.returncode != 0:
        raise RuntimeError(f"Pipeline failed: {result.stderr}")
    
    return result
```

> **Note**: The current pipeline reads `config.json` from its own directory. For web use, the pipeline should be modified to accept a config path as an argument or environment variable.

