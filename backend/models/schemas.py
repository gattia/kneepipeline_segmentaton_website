"""
Pydantic schemas for request/response validation.

These schemas define the API contract and provide automatic validation.
"""
from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field

# Type aliases for Literal types
SegmentationModel = Literal[
    "nnunet_fullres", "nnunet_cascade", "goyal_sagittal", "goyal_coronal", "goyal_axial", "staple"
]

NsmType = Literal["bone_and_cart", "bone_only", "both"]

JobStatus = Literal["queued", "processing", "complete", "error"]


class UploadOptions(BaseModel):
    """Options submitted with file upload."""

    email: Optional[str] = Field(
        default=None, description="Optional email for tracking and notifications"
    )
    segmentation_model: SegmentationModel = Field(
        default="nnunet_fullres", description="Segmentation model to use"
    )
    perform_nsm: bool = Field(default=True, description="Whether to perform Neural Shape Modeling")
    nsm_type: NsmType = Field(
        default="bone_and_cart", description="Type of NSM analysis to perform"
    )
    retain_results: bool = Field(
        default=True, description="Allow anonymized results to be retained for research"
    )
    cartilage_smoothing: float = Field(
        default=0.3125,
        ge=0.0,
        le=1.0,
        description="Cartilage smoothing parameter (not exposed in UI)",
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


class HealthResponse(BaseModel):
    """Health check response model."""

    status: Literal["healthy", "unhealthy"]
    redis: Literal["connected", "disconnected"]
    worker: Literal["available", "unavailable"]
    gpu: Literal["available", "unavailable"]
    timestamp: datetime
    error: Optional[str] = None
