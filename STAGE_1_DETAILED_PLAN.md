# Stage 1: MVP Detailed Implementation Plan

## Overview

**Goal**: Build an end-to-end working prototype with dummy processing that validates the complete user flow: upload → queue → process → download.

**Estimated Duration**: ~1 week

**Key Deliverable**: A functional web application where users can upload MRI files, see queue position, and download a dummy results zip file.

---

## Table of Contents

1. [Prerequisites & Environment Setup](#1-prerequisites--environment-setup)
2. [Project Scaffolding](#2-project-scaffolding)
3. [Backend: FastAPI Application](#3-backend-fastapi-application)
4. [Backend: Job Queue (Celery + Redis)](#4-backend-job-queue-celery--redis)
5. [Backend: Dummy Worker](#5-backend-dummy-worker)
6. [Frontend: Upload Interface](#6-frontend-upload-interface)
7. [Integration & Testing](#7-integration--testing)
8. [Task Checklist](#8-task-checklist)

---

## 1. Prerequisites & Environment Setup

### 1.1 System Requirements

| Requirement | Version/Details |
|-------------|-----------------|
| Python | 3.10+ |
| Redis | 7.x (via Docker or local install) |
| Node.js | Not required (vanilla JS frontend) |

### 1.2 Python Dependencies

Create `backend/requirements.txt`:

```txt
# Web Framework
fastapi==0.109.0
uvicorn[standard]==0.27.0
python-multipart==0.0.6

# Job Queue
celery==5.3.4
redis==5.0.1

# Medical Image Handling
SimpleITK==2.3.1

# Utilities
pydantic==2.5.3
pydantic-settings==2.1.0
python-dotenv==1.0.0

# Development & Testing
pytest==7.4.4
httpx==0.26.0
pytest-asyncio==0.23.3
pytest-cov==4.1.0
ruff==0.1.11
```

### 1.3 Environment Setup Commands

```bash
# 1. Create project directory structure
mkdir -p backend/{routes,services,workers,models}
mkdir -p frontend/{css,js,assets}
mkdir -p data/{uploads,temp,logs}
mkdir -p tests

# 2. Set up Python virtual environment
cd backend
python -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows
pip install -r requirements.txt

# 3. Start Redis (choose one)
# Option A: Docker (recommended)
docker run -d --name redis -p 6379:6379 redis:7-alpine

# Option B: macOS
brew install redis && brew services start redis

# Option C: Ubuntu
sudo apt install redis-server && sudo systemctl start redis
```

---

## 2. Project Scaffolding

### 2.1 Directory Structure to Create

```
kneepipeline_segmentation_website/
├── .github/
│   └── workflows/
│       ├── test.yml            # Run tests on push/PR
│       └── docker-build.yml    # Validate Docker builds
│
├── backend/
│   ├── __init__.py
│   ├── main.py                 # FastAPI app entry point
│   ├── config.py               # Configuration (env vars, paths)
│   ├── requirements.txt
│   │
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── upload.py           # POST /upload
│   │   ├── status.py           # GET /status/{job_id}
│   │   ├── download.py         # GET /download/{job_id}
│   │   ├── stats.py            # GET /stats
│   │   └── health.py           # GET /health
│   │
│   ├── services/
│   │   ├── __init__.py
│   │   ├── file_handler.py     # File validation, zip extraction
│   │   ├── job_service.py      # Job CRUD operations
│   │   └── statistics.py       # Usage stats tracking
│   │
│   ├── workers/
│   │   ├── __init__.py
│   │   ├── celery_app.py       # Celery configuration
│   │   ├── tasks.py            # Celery task definitions
│   │   └── dummy_worker.py     # Phase 1 dummy processor
│   │
│   └── models/
│       ├── __init__.py
│       ├── job.py              # Job dataclass
│       └── schemas.py          # Pydantic request/response models
│
├── frontend/
│   ├── index.html
│   ├── css/
│   │   └── styles.css
│   ├── js/
│   │   └── app.js
│   └── assets/
│       └── (placeholder for icons/images)
│
├── data/                       # Runtime data (gitignored)
│   ├── uploads/
│   ├── temp/
│   └── logs/
│
├── tests/
│   ├── __init__.py
│   ├── conftest.py
│   ├── test_upload.py
│   ├── test_status.py
│   ├── test_file_handler.py
│   └── test_dummy_worker.py
│
├── .env.example
├── .gitignore
└── README.md
```

### 2.2 Create Essential Files

#### `.gitignore`

```gitignore
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
venv/
.venv/
*.egg-info/
dist/
build/

# Environment
.env
.env.local

# Data directories
data/uploads/
data/temp/
data/logs/

# IDE
.vscode/
.idea/
*.swp
*.swo

# Testing
.pytest_cache/
.coverage
htmlcov/

# OS
.DS_Store
Thumbs.db
```

#### `.env.example`

```env
# Redis Configuration
REDIS_URL=redis://localhost:6379/0

# Application Settings
DEBUG=true
MAX_UPLOAD_SIZE_MB=600
UPLOAD_DIR=./data/uploads
TEMP_DIR=./data/temp
LOG_DIR=./data/logs

# Result Storage (Phase 1: local, Phase 2+: S3)
RESULTS_DIR=./data/results
RESULTS_EXPIRY_HOURS=24
```

---

## 3. Backend: FastAPI Application

### 3.1 Configuration Module

**File**: `backend/config.py`

```python
from pydantic_settings import BaseSettings
from pathlib import Path
from functools import lru_cache

class Settings(BaseSettings):
    # Redis
    redis_url: str = "redis://localhost:6379/0"
    
    # Application
    debug: bool = True
    max_upload_size_mb: int = 600
    
    # Directories
    upload_dir: Path = Path("./data/uploads")
    temp_dir: Path = Path("./data/temp")
    log_dir: Path = Path("./data/logs")
    results_dir: Path = Path("./data/results")
    
    # Results
    results_expiry_hours: int = 24
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

@lru_cache()
def get_settings() -> Settings:
    return Settings()
```

### 3.2 Main Application Entry Point

**File**: `backend/main.py`

**Requirements**:
- Initialize FastAPI app with metadata
- Mount static files for frontend
- Include all route routers
- Add CORS middleware for development
- Create required directories on startup

**Implementation Outline**:

```python
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from .config import get_settings
from .routes import upload, status, download, stats, health

@asynccontextmanager
async def lifespan(app: FastAPI):
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
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:8000"],
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

# Routes
app.include_router(health.router, tags=["Health"])
app.include_router(upload.router, tags=["Upload"])
app.include_router(status.router, tags=["Status"])
app.include_router(download.router, tags=["Download"])
app.include_router(stats.router, tags=["Statistics"])

# Serve frontend static files
app.mount("/", StaticFiles(directory="frontend", html=True), name="frontend")
```

### 3.3 Pydantic Schemas

**File**: `backend/models/schemas.py`

Define request/response models for API type safety:

```python
from pydantic import BaseModel, Field
from typing import Optional, Literal
from datetime import datetime

# Enums for options
SegmentationModel = Literal[
    "nnunet_fullres", "nnunet_cascade", 
    "goyal_sagittal", "goyal_coronal", "goyal_axial", "staple"
]

NsmType = Literal["bone_and_cart", "bone_only", "both"]

JobStatus = Literal["queued", "processing", "complete", "error"]

# Upload Request (form data)
class UploadOptions(BaseModel):
    email: Optional[str] = Field(default=None, description="Optional email for tracking and notifications")
    segmentation_model: SegmentationModel = "nnunet_fullres"
    perform_nsm: bool = True
    nsm_type: NsmType = "bone_and_cart"
    retain_results: bool = True
    cartilage_smoothing: float = Field(default=0.3125, ge=0.0, le=1.0)

# Upload Response
class UploadResponse(BaseModel):
    job_id: str
    status: JobStatus
    queue_position: int
    estimated_wait_seconds: int
    message: str

# Status Response (queued)
class StatusQueued(BaseModel):
    job_id: str
    status: Literal["queued"]
    queue_position: int
    estimated_wait_seconds: int

# Status Response (processing)
class StatusProcessing(BaseModel):
    job_id: str
    status: Literal["processing"]
    progress_percent: int
    current_step: int
    total_steps: int
    step_name: str
    elapsed_seconds: int
    estimated_remaining_seconds: int

# Status Response (complete)
class StatusComplete(BaseModel):
    job_id: str
    status: Literal["complete"]
    download_url: str
    result_size_bytes: int
    processing_time_seconds: int

# Status Response (error)
class StatusError(BaseModel):
    job_id: str
    status: Literal["error"]
    error_message: str
    error_code: str

# Stats Response
class StatsResponse(BaseModel):
    total_jobs_processed: int
    total_jobs_today: int
    unique_users: int
    average_processing_time_seconds: int
    jobs_in_queue: int
    uptime_hours: float

# Health Response
class HealthResponse(BaseModel):
    status: Literal["healthy", "unhealthy"]
    redis: Literal["connected", "disconnected"]
    worker: Literal["available", "unavailable"]
    timestamp: datetime
    error: Optional[str] = None
```

### 3.4 Job Model

**File**: `backend/models/job.py`

```python
from dataclasses import dataclass, asdict, field
from datetime import datetime
from typing import Optional
import json
import redis

@dataclass
class Job:
    id: str
    input_filename: str
    input_path: str
    options: dict
    status: str = "queued"  # queued, processing, complete, error
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
    email: Optional[str] = None  # Optional email for tracking/notifications
    
    def to_dict(self) -> dict:
        return asdict(self)
    
    def save(self, redis_client: redis.Redis) -> None:
        """Persist job state to Redis."""
        redis_client.hset("jobs", self.id, json.dumps(self.to_dict()))
        # Also track in queue order if queued
        if self.status == "queued":
            redis_client.zadd("job_queue", {self.id: datetime.fromisoformat(self.created_at).timestamp()})
    
    def delete_from_queue(self, redis_client: redis.Redis) -> None:
        """Remove from queue tracking (when starts processing)."""
        redis_client.zrem("job_queue", self.id)
    
    @classmethod
    def load(cls, job_id: str, redis_client: redis.Redis) -> Optional["Job"]:
        """Load job from Redis."""
        data = redis_client.hget("jobs", job_id)
        if data:
            return cls(**json.loads(data))
        return None
    
    @classmethod
    def get_queue_position(cls, job_id: str, redis_client: redis.Redis) -> int:
        """Get 1-indexed queue position (0 if not in queue)."""
        rank = redis_client.zrank("job_queue", job_id)
        return rank + 1 if rank is not None else 0
    
    @classmethod
    def get_queue_length(cls, redis_client: redis.Redis) -> int:
        """Get total number of jobs in queue."""
        return redis_client.zcard("job_queue")
```

### 3.5 Route Implementations

#### 3.5.1 Health Check Route

**File**: `backend/routes/health.py`

```python
from fastapi import APIRouter, Depends
from datetime import datetime
import redis

from ..config import get_settings, Settings
from ..models.schemas import HealthResponse

router = APIRouter()

def get_redis_client(settings: Settings = Depends(get_settings)) -> redis.Redis:
    return redis.from_url(settings.redis_url)

@router.get("/health", response_model=HealthResponse)
async def health_check(redis_client: redis.Redis = Depends(get_redis_client)):
    """Check health of the application and its dependencies."""
    try:
        # Test Redis connection
        redis_client.ping()
        redis_status = "connected"
    except redis.ConnectionError:
        redis_status = "disconnected"
    
    # TODO: Check Celery worker status (inspect active workers)
    worker_status = "available"  # Placeholder for Phase 1
    
    status = "healthy" if redis_status == "connected" else "unhealthy"
    
    return HealthResponse(
        status=status,
        redis=redis_status,
        worker=worker_status,
        timestamp=datetime.utcnow(),
        error=None if status == "healthy" else "Redis connection failed"
    )
```

#### 3.5.2 Upload Route

**File**: `backend/routes/upload.py`

**Key Responsibilities**:
1. Accept multipart form data with file and options
2. Validate file extension (frontend validation is just UX)
3. Save file to upload directory with unique name
4. If zip, extract and validate contents
5. Create Job record in Redis
6. Submit Celery task
7. Return job_id and queue position

```python
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends
from pathlib import Path
import uuid
import shutil

from ..config import get_settings, Settings
from ..models.job import Job
from ..models.schemas import UploadResponse, UploadOptions
from ..services.file_handler import validate_and_prepare_upload
from ..services.job_service import get_redis_client, get_estimated_wait
from ..services.statistics import track_user_email
from ..workers.tasks import process_pipeline

router = APIRouter()

ALLOWED_EXTENSIONS = {'.zip', '.nii', '.nii.gz', '.nrrd', '.dcm'}
MAX_SIZE_BYTES = 600 * 1024 * 1024  # 600 MB

@router.post("/upload", response_model=UploadResponse)
async def upload_file(
    file: UploadFile = File(...),
    email: str = Form(default=None),
    segmentation_model: str = Form(default="nnunet_fullres"),
    perform_nsm: bool = Form(default=True),
    nsm_type: str = Form(default="bone_and_cart"),
    retain_results: bool = Form(default=True),
    cartilage_smoothing: float = Form(default=0.3125),
    settings: Settings = Depends(get_settings),
    redis_client = Depends(get_redis_client)
):
    """Upload a file and start processing."""
    
    # 1. Validate file extension
    filename = file.filename or "unknown"
    suffix = Path(filename).suffix.lower()
    if filename.endswith('.nii.gz'):
        suffix = '.nii.gz'
    
    if suffix not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400, 
            detail=f"Invalid file type '{suffix}'. Accepted: {ALLOWED_EXTENSIONS}"
        )
    
    # 2. Generate unique job ID
    job_id = str(uuid.uuid4())
    
    # 3. Save uploaded file
    job_upload_dir = settings.upload_dir / job_id
    job_upload_dir.mkdir(parents=True, exist_ok=True)
    upload_path = job_upload_dir / filename
    
    try:
        with open(upload_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    finally:
        file.file.close()
    
    # 4. Validate file size
    file_size = upload_path.stat().st_size
    if file_size > MAX_SIZE_BYTES:
        shutil.rmtree(job_upload_dir)
        raise HTTPException(
            status_code=413,
            detail=f"File too large ({file_size / 1024 / 1024:.1f} MB). Maximum: 600 MB."
        )
    
    # 5. Validate and prepare (extract zip if needed, validate medical image)
    try:
        prepared_path = validate_and_prepare_upload(upload_path, settings.temp_dir / job_id)
    except ValueError as e:
        shutil.rmtree(job_upload_dir)
        raise HTTPException(status_code=400, detail=str(e))
    
    # 6. Create job options dict
    options = {
        "segmentation_model": segmentation_model,
        "perform_nsm": perform_nsm,
        "nsm_type": nsm_type,
        "retain_results": retain_results,
        "cartilage_smoothing": cartilage_smoothing,
    }
    
    # 7. Track unique user if email provided
    if email:
        track_user_email(email, redis_client)
    
    # 8. Create and save job
    job = Job(
        id=job_id,
        input_filename=filename,
        input_path=str(prepared_path),
        options=options,
        retain_for_research=retain_results,
        email=email,
    )
    job.save(redis_client)
    
    # 9. Submit Celery task
    process_pipeline.delay(job_id, str(prepared_path), options)
    
    # 10. Get queue info
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

#### 3.5.3 Status Route

**File**: `backend/routes/status.py`

```python
from fastapi import APIRouter, HTTPException, Depends
from datetime import datetime
from typing import Union

from ..models.job import Job
from ..models.schemas import StatusQueued, StatusProcessing, StatusComplete, StatusError
from ..services.job_service import get_redis_client, get_estimated_wait

router = APIRouter()

@router.get("/status/{job_id}", response_model=Union[StatusQueued, StatusProcessing, StatusComplete, StatusError])
async def get_status(job_id: str, redis_client = Depends(get_redis_client)):
    """Get current status of a processing job."""
    
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
        
        # Estimate remaining based on average per step
        avg_per_step = 60  # Default 60 seconds per step
        remaining = max(0, (job.total_steps - job.current_step) * avg_per_step)
        
        return StatusProcessing(
            job_id=job_id,
            status="processing",
            progress_percent=job.progress_percent,
            current_step=job.current_step,
            total_steps=job.total_steps,
            step_name=job.step_name,
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

#### 3.5.4 Download Route

**File**: `backend/routes/download.py`

```python
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import FileResponse
from pathlib import Path

from ..models.job import Job
from ..services.job_service import get_redis_client
from ..config import get_settings, Settings

router = APIRouter()

@router.get("/download/{job_id}")
async def download_results(
    job_id: str, 
    redis_client = Depends(get_redis_client),
    settings: Settings = Depends(get_settings)
):
    """Download the results zip file."""
    
    job = Job.load(job_id, redis_client)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    if job.status != "complete":
        raise HTTPException(
            status_code=400, 
            detail=f"Job not complete. Current status: {job.status}"
        )
    
    if not job.result_path:
        raise HTTPException(status_code=404, detail="Results not found")
    
    result_path = Path(job.result_path)
    if not result_path.exists():
        raise HTTPException(status_code=404, detail="Results file not found")
    
    # Generate download filename
    input_stem = Path(job.input_filename).stem.replace('.nii', '')
    download_name = f"{input_stem}_results.zip"
    
    return FileResponse(
        path=result_path,
        filename=download_name,
        media_type="application/zip"
    )
```

#### 3.5.5 Stats Route

**File**: `backend/routes/stats.py`

```python
from fastapi import APIRouter, Depends
from datetime import datetime

from ..models.job import Job
from ..models.schemas import StatsResponse
from ..services.job_service import get_redis_client
from ..services.statistics import get_statistics

router = APIRouter()

@router.get("/stats", response_model=StatsResponse)
async def get_stats(redis_client = Depends(get_redis_client)):
    """Get usage statistics for display on the main page."""
    
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

### 3.6 Services

#### 3.6.1 File Handler Service

**File**: `backend/services/file_handler.py`

```python
from pathlib import Path
import shutil
import zipfile
from typing import Optional

def validate_and_prepare_upload(upload_path: Path, temp_dir: Path) -> Path:
    """
    Process uploaded file: extract if zip, validate medical image format.
    
    Returns path to the validated medical image (file or DICOM directory).
    Raises ValueError if validation fails.
    """
    temp_dir.mkdir(parents=True, exist_ok=True)
    
    if upload_path.suffix == '.zip':
        return _handle_zip(upload_path, temp_dir)
    else:
        return _validate_medical_image(upload_path)

def _handle_zip(zip_path: Path, extract_dir: Path) -> Path:
    """Extract zip and find medical image inside."""
    try:
        with zipfile.ZipFile(zip_path, 'r') as zf:
            zf.extractall(extract_dir)
    except zipfile.BadZipFile:
        raise ValueError("Invalid zip file")
    
    # Search for medical images in extracted contents
    medical_image = _find_medical_image(extract_dir)
    if not medical_image:
        raise ValueError("No valid medical image found in zip file")
    
    return medical_image

def _find_medical_image(directory: Path) -> Optional[Path]:
    """Recursively search for a medical image file or DICOM directory."""
    
    # First, look for single files
    for pattern in ['*.nii.gz', '*.nii', '*.nrrd']:
        matches = list(directory.rglob(pattern))
        if matches:
            return matches[0]
    
    # Look for DICOM directories
    for subdir in directory.rglob('*'):
        if subdir.is_dir() and _is_dicom_directory(subdir):
            return subdir
    
    # Check for single 3D DICOM file
    for dcm in directory.rglob('*.dcm'):
        return dcm
    
    return None

def _is_dicom_directory(path: Path) -> bool:
    """Check if directory contains DICOM series (multiple .dcm files)."""
    dcm_files = list(path.glob('*.dcm'))
    return len(dcm_files) >= 10  # Require at least 10 slices for valid series

def _validate_medical_image(path: Path) -> Path:
    """
    Validate that path is a readable medical image using SimpleITK.
    Returns the path if valid, raises ValueError otherwise.
    """
    try:
        import SimpleITK as sitk
        
        if path.is_dir():
            # DICOM series
            reader = sitk.ImageSeriesReader()
            dicom_files = reader.GetGDCMSeriesFileNames(str(path))
            
            if not dicom_files:
                raise ValueError("No DICOM files found in directory")
            
            if len(dicom_files) < 10:
                raise ValueError(f"DICOM series too short ({len(dicom_files)} slices)")
            
            reader.SetFileNames(dicom_files)
            reader.ReadImageInformation()
        else:
            # Single file
            reader = sitk.ImageFileReader()
            reader.SetFileName(str(path))
            reader.ReadImageInformation()
            
            dims = reader.GetDimension()
            if dims < 3:
                raise ValueError(f"Image is {dims}D, expected 3D volume")
            
            size = reader.GetSize()
            if any(s < 10 for s in size[:3]):
                raise ValueError(f"Image dimensions too small: {size}")
        
        return path
        
    except Exception as e:
        if "SimpleITK" in str(type(e)):
            raise ValueError(f"Failed to read medical image: {e}")
        raise
```

#### 3.6.2 Job Service

**File**: `backend/services/job_service.py`

```python
import redis
from fastapi import Depends
from ..config import get_settings, Settings

def get_redis_client(settings: Settings = Depends(get_settings)) -> redis.Redis:
    """Get Redis client instance."""
    return redis.from_url(settings.redis_url, decode_responses=True)

def get_estimated_wait(queue_position: int, redis_client: redis.Redis) -> int:
    """Calculate estimated wait time based on queue position and average processing time."""
    avg_time = get_average_processing_time(redis_client)
    return int(queue_position * avg_time)

def get_average_processing_time(redis_client: redis.Redis) -> float:
    """Get rolling average of last 20 processing times."""
    times = redis_client.lrange("processing_times", 0, 19)
    if not times:
        return 240  # Default 4 minutes if no history
    return sum(float(t) for t in times) / len(times)

def record_processing_time(duration_seconds: float, redis_client: redis.Redis) -> None:
    """Record a processing time for averaging."""
    redis_client.lpush("processing_times", duration_seconds)
    redis_client.ltrim("processing_times", 0, 19)  # Keep only last 20
```

#### 3.6.3 Statistics Service

**File**: `backend/services/statistics.py`

```python
import redis
from datetime import datetime, date

def get_statistics(redis_client: redis.Redis) -> dict:
    """Get usage statistics."""
    
    # Total jobs processed
    total_processed = redis_client.get("stats:total_processed")
    total_processed = int(total_processed) if total_processed else 0
    
    # Jobs today
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
        # Set startup time if not set
        redis_client.set("stats:startup_time", datetime.now().isoformat())
    
    return {
        "total_processed": total_processed,
        "today_processed": today_processed,
        "unique_users": unique_users,
        "avg_processing_time": avg_time,
        "uptime_hours": round(uptime_hours, 1)
    }

def increment_processed_count(redis_client: redis.Redis) -> None:
    """Increment the processed job counter."""
    redis_client.incr("stats:total_processed")
    today_key = f"stats:processed:{date.today().isoformat()}"
    redis_client.incr(today_key)
    redis_client.expire(today_key, 86400 * 7)  # Keep for 7 days

def track_user_email(email: str, redis_client: redis.Redis) -> None:
    """
    Track unique user email addresses.
    
    Uses a Redis set to store unique emails for counting.
    Also maintains a list for potential future contact.
    """
    import hashlib
    
    # Normalize email
    email_normalized = email.lower().strip()
    
    # Add to unique set (for counting)
    redis_client.sadd("stats:unique_emails", email_normalized)
    
    # Store email with hash for lookup (email -> hash mapping)
    email_hash = hashlib.sha256(email_normalized.encode()).hexdigest()[:16]
    redis_client.hset("user_emails", email_hash, email_normalized)

def get_all_user_emails(redis_client: redis.Redis) -> list:
    """Get all stored user emails (for admin use only)."""
    return list(redis_client.hvals("user_emails"))
```

---

## 4. Backend: Job Queue (Celery + Redis)

### 4.1 Celery Configuration

**File**: `backend/workers/celery_app.py`

```python
from celery import Celery
import os

# Redis URL from environment or default
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

celery_app = Celery(
    "knee_pipeline",
    broker=REDIS_URL,
    backend=REDIS_URL,
    include=["backend.workers.tasks"]
)

celery_app.conf.update(
    # Serialization
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    
    # Timezone
    timezone="UTC",
    enable_utc=True,
    
    # Task tracking
    task_track_started=True,
    
    # Single worker for GPU constraint
    worker_concurrency=1,
    
    # Acknowledge after completion (handles crashes)
    task_acks_late=True,
    
    # Retry configuration
    task_default_retry_delay=60,
    task_max_retries=2,
    
    # Result expiration (24 hours)
    result_expires=86400,
)
```

### 4.2 Celery Tasks

**File**: `backend/workers/tasks.py`

```python
from celery import current_task
from datetime import datetime
import redis
import os

from .celery_app import celery_app
from .dummy_worker import dummy_pipeline
from ..models.job import Job
from ..services.job_service import record_processing_time
from ..services.statistics import increment_processed_count

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
redis_client = redis.from_url(REDIS_URL, decode_responses=True)

@celery_app.task(bind=True)
def process_pipeline(self, job_id: str, input_path: str, options: dict):
    """Main pipeline task executed by Celery worker."""
    
    job = Job.load(job_id, redis_client)
    if not job:
        raise ValueError(f"Job {job_id} not found")
    
    # Update status to processing
    job.status = "processing"
    job.started_at = datetime.now().isoformat()
    job.delete_from_queue(redis_client)
    job.save(redis_client)
    
    try:
        # Define processing steps
        steps = [
            ("Validating input", 25),
            ("Processing image", 50),
            ("Generating results", 75),
            ("Packaging output", 100),
        ]
        
        for i, (step_name, progress) in enumerate(steps):
            job.current_step = i + 1
            job.step_name = step_name
            job.progress_percent = progress
            job.save(redis_client)
        
        # Run dummy pipeline
        from pathlib import Path
        from ..config import get_settings
        settings = get_settings()
        
        result_path = dummy_pipeline(
            input_path=input_path,
            options=options,
            output_dir=settings.results_dir / job_id
        )
        
        # Mark complete
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
        
        return {"status": "complete", "result_path": str(result_path)}
        
    except Exception as e:
        job.status = "error"
        job.error_message = str(e)
        job.error_code = "PIPELINE_ERROR"
        job.save(redis_client)
        raise
```

---

## 5. Backend: Dummy Worker

### 5.1 Dummy Pipeline Implementation

**File**: `backend/workers/dummy_worker.py`

```python
from pathlib import Path
import shutil
import json
import time

def dummy_pipeline(input_path: str, options: dict, output_dir: Path) -> Path:
    """
    Dummy worker for Phase 1 development.
    
    Creates a zeroed copy of the input image and packages results.
    Simulates processing time for realistic UX testing.
    
    Args:
        input_path: Path to the validated medical image
        options: Processing options from user
        output_dir: Directory to save results
        
    Returns:
        Path to the results zip file
    """
    import SimpleITK as sitk
    
    input_path = Path(input_path)
    
    # Create output directory
    results_dir = output_dir / "results"
    results_dir.mkdir(parents=True, exist_ok=True)
    
    # Simulate step 1: Validation (already done, just wait)
    time.sleep(2)
    
    # Simulate step 2: Load and create zeroed image
    time.sleep(2)
    
    if input_path.is_dir():
        # DICOM series
        reader = sitk.ImageSeriesReader()
        dicom_files = reader.GetGDCMSeriesFileNames(str(input_path))
        reader.SetFileNames(dicom_files)
        img = reader.Execute()
    else:
        # Single file
        img = sitk.ReadImage(str(input_path))
    
    # Create zeroed copy (same dimensions/metadata)
    zeroed = sitk.Image(img.GetSize(), img.GetPixelID())
    zeroed.CopyInformation(img)
    
    # Simulate step 3: Save results
    time.sleep(2)
    
    # Determine input stem for naming
    input_stem = input_path.stem
    if input_path.suffix == '.gz':
        input_stem = Path(input_stem).stem  # Remove .nii from .nii.gz
    
    # Save zeroed image as "segmentation"
    sitk.WriteImage(zeroed, str(results_dir / "dummy_segmentation.nii.gz"))
    
    # Create dummy results JSON
    results_summary = {
        "status": "dummy_processing",
        "phase": "Phase 1 MVP",
        "input_file": input_path.name,
        "options": options,
        "message": "This is a dummy result from Phase 1 development. "
                   "Real processing will be enabled in Phase 3.",
        "dummy_metrics": {
            "femur_cartilage_thickness_mm": 2.45,
            "tibia_cartilage_thickness_mm": 2.12,
            "bscore": -0.5,
            "note": "These are placeholder values"
        }
    }
    
    with open(results_dir / "results.json", "w") as f:
        json.dump(results_summary, f, indent=2)
    
    # Create dummy CSV
    csv_content = """region,mean_thickness_mm,std_thickness_mm,n_points
femur_medial,2.45,0.32,1500
femur_lateral,2.38,0.28,1400
tibia_medial,2.12,0.25,1200
tibia_lateral,2.08,0.22,1100
"""
    with open(results_dir / "results.csv", "w") as f:
        f.write(csv_content)
    
    # Simulate step 4: Package
    time.sleep(1)
    
    # Create zip archive
    zip_path = shutil.make_archive(
        str(output_dir / f"{input_stem}_results"),
        'zip',
        results_dir
    )
    
    return Path(zip_path)
```

---

## 6. Frontend: Upload Interface

### 6.1 HTML Structure

**File**: `frontend/index.html`

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Knee MRI Analysis Pipeline</title>
    <link rel="stylesheet" href="/css/styles.css">
    <!-- FilePond CSS -->
    <link href="https://unpkg.com/filepond@^4/dist/filepond.css" rel="stylesheet" />
</head>
<body>
    <div class="container">
        <header>
            <h1>🦴 Knee MRI Analysis Pipeline</h1>
            <p class="subtitle">Automated segmentation and analysis of knee MRI data</p>
        </header>

        <!-- Upload Section -->
        <section id="upload-section" class="section">
            <div class="upload-area">
                <input type="file" id="file-input" accept=".zip,.nii,.nii.gz,.nrrd,.dcm">
            </div>
            
            <div class="config-panel">
                <h3>Configuration</h3>
                
                <div class="form-group">
                    <label for="email-input">Email (optional):</label>
                    <input type="email" id="email-input" placeholder="your@email.com">
                    <p class="help-text">
                        For usage tracking and to receive your download link via email.
                    </p>
                </div>
                
                <div class="form-group">
                    <label for="seg-model">Segmentation Model:</label>
                    <select id="seg-model">
                        <option value="nnunet_fullres" selected>nnU-Net FullRes (recommended)</option>
                        <option value="nnunet_cascade">nnU-Net Cascade</option>
                        <option value="goyal_sagittal">DOSMA Sagittal</option>
                        <option value="goyal_coronal">DOSMA Coronal</option>
                        <option value="goyal_axial">DOSMA Axial</option>
                        <option value="staple">DOSMA STAPLE (ensemble)</option>
                    </select>
                </div>
                
                <div class="form-group">
                    <label class="checkbox-label">
                        <input type="checkbox" id="perform-nsm" checked>
                        Perform Shape Modeling (NSM)
                    </label>
                </div>
                
                <div class="form-group" id="nsm-options">
                    <label>NSM Type:</label>
                    <div class="radio-group">
                        <label>
                            <input type="radio" name="nsm-type" value="bone_and_cart" checked>
                            Bone + Cartilage
                        </label>
                        <label>
                            <input type="radio" name="nsm-type" value="bone_only">
                            Bone Only
                        </label>
                        <label>
                            <input type="radio" name="nsm-type" value="both">
                            Both
                        </label>
                    </div>
                </div>
                
                <div class="form-group">
                    <label class="checkbox-label">
                        <input type="checkbox" id="retain-results" checked>
                        Allow anonymized results to be retained for research
                    </label>
                    <p class="help-text">
                        Only derived data (segmentations, meshes, metrics) will be retained. 
                        No original MRI images are stored.
                    </p>
                </div>
            </div>
            
            <button id="submit-btn" class="btn primary" disabled>
                Process Data
            </button>
        </section>

        <!-- Processing Section -->
        <section id="processing-section" class="section hidden">
            <div class="processing-info">
                <h2>Processing: <span id="processing-filename"></span></h2>
                
                <div class="alert warning">
                    ⚠️ Please keep this page open until processing completes.
                </div>
                
                <div class="queue-info">
                    <p>Queue Position: <strong id="queue-position">#1</strong></p>
                    <p>Estimated Wait: <strong id="estimated-wait">~4 minutes</strong></p>
                </div>
                
                <div class="progress-container">
                    <div class="progress-bar">
                        <div class="progress-fill" id="progress-fill"></div>
                    </div>
                    <p class="progress-text">
                        <span id="progress-percent">0%</span> - 
                        <span id="step-name">Initializing...</span>
                    </p>
                </div>
                
                <button id="cancel-btn" class="btn secondary">Cancel</button>
            </div>
        </section>

        <!-- Complete Section -->
        <section id="complete-section" class="section hidden">
            <div class="complete-info">
                <h2>✅ Processing Complete!</h2>
                
                <p>File: <strong id="complete-filename"></strong></p>
                <p>Duration: <strong id="processing-duration"></strong></p>
                
                <button id="download-btn" class="btn primary large">
                    ⬇️ Download Results (<span id="result-size"></span>)
                </button>
                
                <div class="alert info">
                    ⏰ Download available for 24 hours.<br>
                    ⚠️ Do not reload this page until you have downloaded your results.
                </div>
                
                <button id="new-upload-btn" class="btn secondary">
                    Process Another
                </button>
            </div>
        </section>

        <!-- Error Section -->
        <section id="error-section" class="section hidden">
            <div class="error-info">
                <h2>❌ Processing Error</h2>
                <p id="error-message"></p>
                <button id="retry-btn" class="btn primary">Try Again</button>
            </div>
        </section>

        <!-- Footer with Stats -->
        <footer>
            <div class="stats">
                📊 <span id="total-processed">0</span> images processed | 
                <span id="unique-users">0</span> users |
                Avg time: <span id="avg-time">0</span> min
            </div>
            <div class="disclaimer">
                ⚠️ Research use only. Not for clinical diagnosis.
            </div>
        </footer>
    </div>

    <!-- FilePond JS -->
    <script src="https://unpkg.com/filepond@^4/dist/filepond.js"></script>
    <script src="/js/app.js"></script>
</body>
</html>
```

### 6.2 CSS Styles

**File**: `frontend/css/styles.css`

```css
/* Base Styles */
:root {
    --primary-color: #2563eb;
    --primary-hover: #1d4ed8;
    --success-color: #10b981;
    --warning-color: #f59e0b;
    --error-color: #ef4444;
    --bg-color: #f8fafc;
    --card-bg: #ffffff;
    --text-color: #1e293b;
    --text-muted: #64748b;
    --border-color: #e2e8f0;
    --border-radius: 12px;
}

* {
    box-sizing: border-box;
    margin: 0;
    padding: 0;
}

body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
    background: var(--bg-color);
    color: var(--text-color);
    line-height: 1.6;
    min-height: 100vh;
}

.container {
    max-width: 680px;
    margin: 0 auto;
    padding: 2rem 1rem;
}

/* Header */
header {
    text-align: center;
    margin-bottom: 2rem;
}

header h1 {
    font-size: 1.75rem;
    margin-bottom: 0.5rem;
}

header .subtitle {
    color: var(--text-muted);
}

/* Sections */
.section {
    background: var(--card-bg);
    border-radius: var(--border-radius);
    padding: 1.5rem;
    margin-bottom: 1.5rem;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

.hidden {
    display: none !important;
}

/* Upload Area */
.upload-area {
    margin-bottom: 1.5rem;
}

.filepond--root {
    font-family: inherit;
}

/* Config Panel */
.config-panel {
    border-top: 1px solid var(--border-color);
    padding-top: 1.5rem;
    margin-bottom: 1.5rem;
}

.config-panel h3 {
    font-size: 1rem;
    margin-bottom: 1rem;
}

.form-group {
    margin-bottom: 1rem;
}

.form-group label {
    display: block;
    margin-bottom: 0.5rem;
    font-weight: 500;
}

.form-group select,
.form-group input[type="email"] {
    width: 100%;
    padding: 0.5rem 0.75rem;
    border: 1px solid var(--border-color);
    border-radius: 6px;
    font-size: 1rem;
}

.form-group input[type="email"]:focus {
    outline: none;
    border-color: var(--primary-color);
    box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.1);
}

.checkbox-label {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    cursor: pointer;
}

.checkbox-label input {
    width: 18px;
    height: 18px;
}

.radio-group {
    display: flex;
    gap: 1rem;
    flex-wrap: wrap;
}

.radio-group label {
    display: flex;
    align-items: center;
    gap: 0.25rem;
    font-weight: normal;
    cursor: pointer;
}

.help-text {
    font-size: 0.85rem;
    color: var(--text-muted);
    margin-top: 0.5rem;
}

/* Buttons */
.btn {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    padding: 0.75rem 1.5rem;
    border: none;
    border-radius: 8px;
    font-size: 1rem;
    font-weight: 500;
    cursor: pointer;
    transition: background-color 0.2s, opacity 0.2s;
}

.btn:disabled {
    opacity: 0.5;
    cursor: not-allowed;
}

.btn.primary {
    background: var(--primary-color);
    color: white;
    width: 100%;
}

.btn.primary:hover:not(:disabled) {
    background: var(--primary-hover);
}

.btn.secondary {
    background: var(--border-color);
    color: var(--text-color);
}

.btn.secondary:hover {
    background: #d1d5db;
}

.btn.large {
    padding: 1rem 2rem;
    font-size: 1.125rem;
}

/* Alerts */
.alert {
    padding: 1rem;
    border-radius: 8px;
    margin: 1rem 0;
}

.alert.warning {
    background: #fef3c7;
    color: #92400e;
}

.alert.info {
    background: #dbeafe;
    color: #1e40af;
}

.alert.error {
    background: #fee2e2;
    color: #991b1b;
}

/* Progress */
.progress-container {
    margin: 1.5rem 0;
}

.progress-bar {
    height: 24px;
    background: var(--border-color);
    border-radius: 12px;
    overflow: hidden;
}

.progress-fill {
    height: 100%;
    background: var(--primary-color);
    transition: width 0.3s ease;
    width: 0%;
}

.progress-text {
    text-align: center;
    margin-top: 0.5rem;
    color: var(--text-muted);
}

/* Queue Info */
.queue-info {
    text-align: center;
    margin: 1rem 0;
}

.queue-info p {
    margin: 0.25rem 0;
}

/* Complete Section */
.complete-info {
    text-align: center;
}

.complete-info h2 {
    color: var(--success-color);
    margin-bottom: 1rem;
}

.complete-info p {
    margin: 0.5rem 0;
}

#download-btn {
    margin: 1.5rem 0;
}

#new-upload-btn {
    margin-top: 1rem;
}

/* Error Section */
.error-info {
    text-align: center;
}

.error-info h2 {
    color: var(--error-color);
    margin-bottom: 1rem;
}

#error-message {
    margin-bottom: 1.5rem;
    color: var(--text-muted);
}

/* Footer */
footer {
    text-align: center;
    padding: 1rem;
    color: var(--text-muted);
    font-size: 0.9rem;
}

.stats {
    margin-bottom: 0.5rem;
}

.disclaimer {
    font-size: 0.85rem;
}

/* Responsive */
@media (max-width: 480px) {
    .container {
        padding: 1rem;
    }
    
    .radio-group {
        flex-direction: column;
        gap: 0.5rem;
    }
}
```

### 6.3 JavaScript Application Logic

**File**: `frontend/js/app.js`

```javascript
// State management
const state = {
    jobId: null,
    filename: null,
    pollInterval: null,
};

// DOM Elements
const elements = {
    // Sections
    uploadSection: document.getElementById('upload-section'),
    processingSection: document.getElementById('processing-section'),
    completeSection: document.getElementById('complete-section'),
    errorSection: document.getElementById('error-section'),
    
    // Upload
    fileInput: document.getElementById('file-input'),
    submitBtn: document.getElementById('submit-btn'),
    emailInput: document.getElementById('email-input'),
    segModel: document.getElementById('seg-model'),
    performNsm: document.getElementById('perform-nsm'),
    nsmOptions: document.getElementById('nsm-options'),
    retainResults: document.getElementById('retain-results'),
    
    // Processing
    processingFilename: document.getElementById('processing-filename'),
    queuePosition: document.getElementById('queue-position'),
    estimatedWait: document.getElementById('estimated-wait'),
    progressFill: document.getElementById('progress-fill'),
    progressPercent: document.getElementById('progress-percent'),
    stepName: document.getElementById('step-name'),
    cancelBtn: document.getElementById('cancel-btn'),
    
    // Complete
    completeFilename: document.getElementById('complete-filename'),
    processingDuration: document.getElementById('processing-duration'),
    downloadBtn: document.getElementById('download-btn'),
    resultSize: document.getElementById('result-size'),
    newUploadBtn: document.getElementById('new-upload-btn'),
    
    // Error
    errorMessage: document.getElementById('error-message'),
    retryBtn: document.getElementById('retry-btn'),
    
    // Stats
    totalProcessed: document.getElementById('total-processed'),
    uniqueUsers: document.getElementById('unique-users'),
    avgTime: document.getElementById('avg-time'),
};

// Initialize FilePond
let pond = null;

function initFilePond() {
    pond = FilePond.create(elements.fileInput, {
        allowMultiple: false,
        maxFileSize: '600MB',
        acceptedFileTypes: ['.zip', '.nii', '.nii.gz', '.nrrd', '.dcm'],
        labelIdle: '📁 Drop your MRI data here or <span class="filepond--label-action">browse</span><br><small>Accepted: .zip, .nii.gz, .nrrd, .dcm</small>',
        credits: false,
    });
    
    pond.on('addfile', (error, file) => {
        if (!error) {
            elements.submitBtn.disabled = false;
        }
    });
    
    pond.on('removefile', () => {
        elements.submitBtn.disabled = true;
    });
}

// Section visibility
function showSection(sectionId) {
    ['upload', 'processing', 'complete', 'error'].forEach(id => {
        const section = document.getElementById(`${id}-section`);
        section.classList.toggle('hidden', id !== sectionId);
    });
}

// Format time
function formatDuration(seconds) {
    if (seconds < 60) return `${seconds} seconds`;
    const minutes = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return secs > 0 ? `${minutes} min ${secs} sec` : `${minutes} minutes`;
}

function formatSize(bytes) {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

// Upload file
async function uploadFile() {
    const files = pond.getFiles();
    if (files.length === 0) return;
    
    const file = files[0].file;
    state.filename = file.name;
    
    const formData = new FormData();
    formData.append('file', file);
    
    // Include email if provided
    const email = elements.emailInput.value.trim();
    if (email) {
        formData.append('email', email);
    }
    
    formData.append('segmentation_model', elements.segModel.value);
    formData.append('perform_nsm', elements.performNsm.checked);
    formData.append('nsm_type', document.querySelector('input[name="nsm-type"]:checked').value);
    formData.append('retain_results', elements.retainResults.checked);
    
    try {
        elements.submitBtn.disabled = true;
        elements.submitBtn.textContent = 'Uploading...';
        
        const response = await fetch('/upload', {
            method: 'POST',
            body: formData,
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Upload failed');
        }
        
        const data = await response.json();
        state.jobId = data.job_id;
        
        // Show processing section
        elements.processingFilename.textContent = state.filename;
        elements.queuePosition.textContent = `#${data.queue_position}`;
        elements.estimatedWait.textContent = `~${formatDuration(data.estimated_wait_seconds)}`;
        
        showSection('processing');
        startPolling();
        
    } catch (error) {
        showError(error.message);
    } finally {
        elements.submitBtn.disabled = false;
        elements.submitBtn.textContent = 'Process Data';
    }
}

// Poll for status
function startPolling() {
    if (state.pollInterval) {
        clearInterval(state.pollInterval);
    }
    
    pollStatus(); // Immediate first poll
    state.pollInterval = setInterval(pollStatus, 2000); // Every 2 seconds
}

async function pollStatus() {
    if (!state.jobId) return;
    
    try {
        const response = await fetch(`/status/${state.jobId}`);
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to get status');
        }
        
        const data = await response.json();
        
        switch (data.status) {
            case 'queued':
                elements.queuePosition.textContent = `#${data.queue_position}`;
                elements.estimatedWait.textContent = `~${formatDuration(data.estimated_wait_seconds)}`;
                elements.progressFill.style.width = '0%';
                elements.progressPercent.textContent = '0%';
                elements.stepName.textContent = 'Waiting in queue...';
                break;
                
            case 'processing':
                elements.queuePosition.textContent = 'Processing';
                elements.estimatedWait.textContent = formatDuration(data.estimated_remaining_seconds);
                elements.progressFill.style.width = `${data.progress_percent}%`;
                elements.progressPercent.textContent = `${data.progress_percent}%`;
                elements.stepName.textContent = `Step ${data.current_step}/${data.total_steps}: ${data.step_name}`;
                break;
                
            case 'complete':
                stopPolling();
                showComplete(data);
                break;
                
            case 'error':
                stopPolling();
                showError(data.error_message);
                break;
        }
        
    } catch (error) {
        console.error('Polling error:', error);
        // Don't show error on polling failures, just keep trying
    }
}

function stopPolling() {
    if (state.pollInterval) {
        clearInterval(state.pollInterval);
        state.pollInterval = null;
    }
}

// Show complete
function showComplete(data) {
    elements.completeFilename.textContent = state.filename;
    elements.processingDuration.textContent = formatDuration(data.processing_time_seconds);
    elements.resultSize.textContent = formatSize(data.result_size_bytes);
    elements.downloadBtn.onclick = () => {
        window.location.href = data.download_url;
    };
    showSection('complete');
}

// Show error
function showError(message) {
    elements.errorMessage.textContent = message;
    showSection('error');
}

// Reset to upload
function resetToUpload() {
    state.jobId = null;
    state.filename = null;
    stopPolling();
    pond.removeFiles();
    elements.submitBtn.disabled = true;
    showSection('upload');
}

// Load stats
async function loadStats() {
    try {
        const response = await fetch('/stats');
        if (response.ok) {
            const data = await response.json();
            elements.totalProcessed.textContent = data.total_jobs_processed.toLocaleString();
            elements.uniqueUsers.textContent = data.unique_users.toLocaleString();
            elements.avgTime.textContent = (data.average_processing_time_seconds / 60).toFixed(1);
        }
    } catch (error) {
        console.error('Failed to load stats:', error);
    }
}

// Event listeners
elements.submitBtn.addEventListener('click', uploadFile);
elements.performNsm.addEventListener('change', (e) => {
    elements.nsmOptions.classList.toggle('hidden', !e.target.checked);
});
elements.newUploadBtn.addEventListener('click', resetToUpload);
elements.retryBtn.addEventListener('click', resetToUpload);

// Cancel button (for future implementation)
elements.cancelBtn.addEventListener('click', () => {
    if (confirm('Are you sure you want to cancel processing?')) {
        // TODO: Call cancel API endpoint
        resetToUpload();
    }
});

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    initFilePond();
    loadStats();
    
    // Refresh stats periodically
    setInterval(loadStats, 60000); // Every minute
});
```

---

## 7. Integration & Testing

### 7.1 Test Configuration

**File**: `tests/conftest.py`

```python
import pytest
from fastapi.testclient import TestClient
import redis
import tempfile
from pathlib import Path

@pytest.fixture
def temp_dir():
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)

@pytest.fixture
def redis_client():
    client = redis.Redis(host='localhost', port=6379, db=15)  # Use separate test db
    client.flushdb()  # Clean before test
    yield client
    client.flushdb()  # Clean after test

@pytest.fixture
def test_client():
    from backend.main import app
    return TestClient(app)
```

### 7.2 Unit Tests

**File**: `tests/test_file_handler.py`

```python
import pytest
from pathlib import Path
from backend.services.file_handler import validate_and_prepare_upload

def test_validate_nifti_file(temp_dir):
    """Test validation of a valid NIfTI file."""
    # Create a simple test file (would need actual NIfTI for real test)
    # For now, just test the structure
    pass

def test_reject_invalid_extension(temp_dir):
    """Test rejection of invalid file types."""
    invalid_file = temp_dir / "test.txt"
    invalid_file.write_text("not a medical image")
    
    with pytest.raises(ValueError):
        validate_and_prepare_upload(invalid_file, temp_dir)
```

**File**: `tests/test_upload.py`

```python
def test_upload_endpoint_validation(test_client):
    """Test that upload endpoint validates file type."""
    response = test_client.post(
        "/upload",
        files={"file": ("test.txt", b"not valid", "text/plain")},
        data={"segmentation_model": "nnunet_fullres"}
    )
    assert response.status_code == 400

def test_stats_endpoint(test_client):
    """Test stats endpoint returns valid response."""
    response = test_client.get("/stats")
    assert response.status_code == 200
    data = response.json()
    assert "total_jobs_processed" in data
```

### 7.3 Manual Testing Procedure

1. **Start Services**:
   ```bash
   # Terminal 1: Redis
   docker run -d --name redis -p 6379:6379 redis:7-alpine
   
   # Terminal 2: FastAPI
   cd backend
   source venv/bin/activate
   uvicorn main:app --reload --port 8000
   
   # Terminal 3: Celery Worker
   cd backend
   source venv/bin/activate
   celery -A workers.celery_app worker --loglevel=info --concurrency=1
   ```

2. **Test Upload Flow**:
   - Open http://localhost:8000
   - Upload a small NIfTI file
   - Observe queue position display
   - Watch progress updates
   - Download results zip
   - Verify zip contains dummy outputs

3. **Test Error Handling**:
   - Upload invalid file type → expect error message
   - Upload too-large file → expect size limit error

### 7.4 GitHub Actions CI/CD

Automated testing runs on every push and pull request.

**File**: `.github/workflows/test.yml`

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

**File**: `.github/workflows/docker-build.yml` (optional, for validating Docker builds)

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

### 7.5 Linting Configuration

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

---

## 8. Task Checklist

### Backend Setup
- [ ] Create project directory structure
- [ ] Create `requirements.txt` with all dependencies
- [ ] Set up Python virtual environment
- [ ] Create `.env.example` and `.gitignore`
- [ ] Implement `config.py` with Settings

### FastAPI Application
- [ ] Create `main.py` with FastAPI app and lifespan
- [ ] Create `models/schemas.py` with Pydantic models
- [ ] Create `models/job.py` with Job dataclass
- [ ] Implement `routes/health.py`
- [ ] Implement `routes/upload.py`
- [ ] Implement `routes/status.py`
- [ ] Implement `routes/download.py`
- [ ] Implement `routes/stats.py`

### Services
- [ ] Implement `services/file_handler.py`
- [ ] Implement `services/job_service.py`
- [ ] Implement `services/statistics.py`

### Job Queue
- [ ] Implement `workers/celery_app.py`
- [ ] Implement `workers/tasks.py`
- [ ] Implement `workers/dummy_worker.py`
- [ ] Test Redis connection
- [ ] Test Celery task execution

### Frontend
- [ ] Create `index.html` with full layout
- [ ] Create `css/styles.css`
- [ ] Create `js/app.js` with upload logic
- [ ] Integrate FilePond for file upload
- [ ] Implement status polling
- [ ] Implement download functionality
- [ ] Test responsive design

### Testing & CI/CD
- [ ] Create `tests/conftest.py`
- [ ] Write unit tests for file handler
- [ ] Write API endpoint tests
- [ ] Perform manual end-to-end testing
- [ ] Create `.github/workflows/test.yml` for automated testing
- [ ] Create `pyproject.toml` with linting configuration
- [ ] Verify CI passes on push

### Documentation
- [ ] Create basic `README.md` with setup instructions
- [ ] Document API endpoints

---

## Development Commands Reference

```bash
# Start development environment
docker run -d --name redis -p 6379:6379 redis:7-alpine
cd backend && source venv/bin/activate

# Run FastAPI (development mode with auto-reload)
uvicorn main:app --reload --port 8000

# Run Celery worker (separate terminal)
celery -A workers.celery_app worker --loglevel=info --concurrency=1

# Run tests
pytest tests/ -v

# Monitor Celery tasks
celery -A workers.celery_app flower  # Optional: Flower monitoring UI

# Check Redis
redis-cli ping
redis-cli HGETALL jobs

# View logs
tail -f data/logs/app.log
```

---

## Next Steps After Stage 1

Once Stage 1 is complete and tested:

1. **Phase 2**: Add progress polling refinements, rolling time estimates, session persistence via localStorage
2. **Phase 3**: Replace dummy worker with real pipeline integration
3. **Phase 4**: Add 3D preview, S3 storage, email notifications
