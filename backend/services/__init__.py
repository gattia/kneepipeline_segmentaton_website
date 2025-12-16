"""
Services package - Business logic for file handling, jobs, and statistics.
"""
from .file_handler import validate_and_prepare_upload
from .job_service import (
    get_average_processing_time,
    get_estimated_wait,
    get_redis_client,
    record_processing_time,
)
from .statistics import (
    get_all_user_emails,
    get_statistics,
    increment_processed_count,
    track_user_email,
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
