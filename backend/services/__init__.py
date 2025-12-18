"""
Services package - Business logic for file handling, jobs, and statistics.
"""
from .config_generator import (
    ALL_SEG_MODELS,
    VALID_NSM_TYPES,
    VALID_SEG_MODELS,
    ConfigValidationError,
    generate_pipeline_config,
    get_available_models,
    get_available_nsm_types,
    get_base_config_path,
    get_pipeline_script_path,
    validate_options,
)
from .error_handler import (
    ERROR_MESSAGES,
    ErrorCode,
    PipelineError,
    format_error_for_job,
    get_error_response,
    parse_error_from_output,
)
from .file_handler import validate_and_prepare_upload
from .job_service import (
    get_average_processing_time,
    get_estimated_wait,
    get_redis_client,
    record_processing_time,
)
from .progress_parser import (
    STEP_PATTERNS,
    TOTAL_STEPS,
    ProgressUpdate,
    estimate_progress_from_time,
    parse_progress_line,
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
    # Config generator
    "generate_pipeline_config",
    "get_pipeline_script_path",
    "get_base_config_path",
    "validate_options",
    "ConfigValidationError",
    "VALID_SEG_MODELS",
    "ALL_SEG_MODELS",
    "VALID_NSM_TYPES",
    "get_available_models",
    "get_available_nsm_types",
    # Error handler
    "ErrorCode",
    "PipelineError",
    "ERROR_MESSAGES",
    "parse_error_from_output",
    "get_error_response",
    "format_error_for_job",
    # Progress parser
    "ProgressUpdate",
    "STEP_PATTERNS",
    "TOTAL_STEPS",
    "parse_progress_line",
    "estimate_progress_from_time",
]
