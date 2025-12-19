"""
Error handling and user message mapping.

This module provides:
- Error code enumeration
- User-friendly error messages
- Recovery suggestions
- Error parsing from pipeline output
"""
from dataclasses import dataclass
from enum import Enum
from typing import Optional


class ErrorCode(str, Enum):
    """Pipeline error codes."""
    GPU_OOM = "GPU_OOM"
    TIMEOUT = "TIMEOUT"
    INVALID_FORMAT = "INVALID_FORMAT"
    FILE_NOT_FOUND = "FILE_NOT_FOUND"
    DICOM_ERROR = "DICOM_ERROR"
    SEGMENTATION_FAILED = "SEGMENTATION_FAILED"
    NSM_FAILED = "NSM_FAILED"
    CONFIG_ERROR = "CONFIG_ERROR"
    PIPELINE_ERROR = "PIPELINE_ERROR"


@dataclass
class PipelineError:
    """Structured pipeline error with user-friendly details."""
    code: ErrorCode
    message: str
    details: Optional[str] = None
    recovery_hint: Optional[str] = None


# User-friendly error messages
ERROR_MESSAGES = {
    ErrorCode.GPU_OOM: PipelineError(
        code=ErrorCode.GPU_OOM,
        message="The GPU ran out of memory while processing your file.",
        recovery_hint="Try reducing the batch size, using a different segmentation model, or processing a smaller image."
    ),
    ErrorCode.TIMEOUT: PipelineError(
        code=ErrorCode.TIMEOUT,
        message="Processing took longer than expected and was stopped.",
        recovery_hint="Your file may be very large. Try processing a smaller region or contact support."
    ),
    ErrorCode.INVALID_FORMAT: PipelineError(
        code=ErrorCode.INVALID_FORMAT,
        message="The uploaded file format is not supported.",
        recovery_hint="Please upload a NIfTI (.nii, .nii.gz), NRRD (.nrrd), or DICOM zip file."
    ),
    ErrorCode.FILE_NOT_FOUND: PipelineError(
        code=ErrorCode.FILE_NOT_FOUND,
        message="The uploaded file could not be found.",
        recovery_hint="Please try uploading the file again."
    ),
    ErrorCode.DICOM_ERROR: PipelineError(
        code=ErrorCode.DICOM_ERROR,
        message="The DICOM files could not be read properly.",
        recovery_hint="Ensure the zip contains a valid DICOM series. Try converting to NIfTI format."
    ),
    ErrorCode.SEGMENTATION_FAILED: PipelineError(
        code=ErrorCode.SEGMENTATION_FAILED,
        message="The segmentation step failed to complete.",
        recovery_hint="The image quality may be insufficient. Try a different segmentation model."
    ),
    ErrorCode.NSM_FAILED: PipelineError(
        code=ErrorCode.NSM_FAILED,
        message="Neural Shape Model analysis failed.",
        recovery_hint="Try running without NSM, or use bone-only analysis instead."
    ),
    ErrorCode.CONFIG_ERROR: PipelineError(
        code=ErrorCode.CONFIG_ERROR,
        message="There was an error with the processing configuration.",
        recovery_hint="Please try again with default settings or contact support."
    ),
    ErrorCode.PIPELINE_ERROR: PipelineError(
        code=ErrorCode.PIPELINE_ERROR,
        message="An unexpected error occurred during processing.",
        recovery_hint="Please try again. If the problem persists, contact support."
    ),
}


def parse_error_from_output(output: str) -> ErrorCode:
    """
    Parse pipeline output to determine error code.
    
    Args:
        output: stderr or stdout from pipeline execution
        
    Returns:
        Most appropriate ErrorCode
    """
    output_lower = output.lower()
    
    # Check for GPU/CUDA memory errors
    if any(phrase in output_lower for phrase in [
        "cuda out of memory",
        "out of memory",
        "cuda error",
        "cudnn error",
        "gpu memory",
        "oom",
    ]):
        return ErrorCode.GPU_OOM
    
    # Check for timeout
    if "timeout" in output_lower:
        return ErrorCode.TIMEOUT
    
    # Check for file/format errors
    if any(phrase in output_lower for phrase in [
        "not found",
        "does not exist",
        "no such file",
    ]):
        return ErrorCode.FILE_NOT_FOUND
    
    if any(phrase in output_lower for phrase in [
        "invalid format",
        "cannot read",
        "unsupported format",
        "not a valid",
    ]):
        return ErrorCode.INVALID_FORMAT
    
    # Check for DICOM errors
    if any(phrase in output_lower for phrase in [
        "dicom",
        "dcm error",
        "no dicom",
    ]):
        return ErrorCode.DICOM_ERROR
    
    # Check for segmentation errors
    if any(phrase in output_lower for phrase in [
        "segmentation failed",
        "segmentation error",
        "no segmentation",
    ]):
        return ErrorCode.SEGMENTATION_FAILED
    
    # Check for NSM errors
    if any(phrase in output_lower for phrase in [
        "nsm error",
        "nsm failed",
        "shape model",
        "bscore error",
    ]):
        return ErrorCode.NSM_FAILED
    
    # Check for config errors
    if any(phrase in output_lower for phrase in [
        "config error",
        "invalid config",
        "missing config",
    ]):
        return ErrorCode.CONFIG_ERROR
    
    # Default to generic pipeline error
    return ErrorCode.PIPELINE_ERROR


def get_error_response(code: ErrorCode, details: Optional[str] = None) -> dict:
    """
    Get user-friendly error response for API.
    
    Args:
        code: Error code
        details: Optional technical details
        
    Returns:
        Dict suitable for API response
    """
    error_info = ERROR_MESSAGES.get(code, ERROR_MESSAGES[ErrorCode.PIPELINE_ERROR])
    
    return {
        "error_code": error_info.code.value,
        "message": error_info.message,
        "recovery_hint": error_info.recovery_hint,
        "details": details if details else None,
    }


def format_error_for_job(exception: Exception, output: Optional[str] = None) -> tuple:
    """
    Format exception for job storage.
    
    Args:
        exception: The caught exception
        output: Optional pipeline output for parsing
        
    Returns:
        Tuple of (error_code, error_message)
    """
    # Try to parse error from output first
    if output:
        code = parse_error_from_output(output)
    else:
        code = _map_exception_to_code(exception)
    
    error_info = ERROR_MESSAGES.get(code, ERROR_MESSAGES[ErrorCode.PIPELINE_ERROR])
    
    # Combine message with recovery hint for job storage
    message = f"{error_info.message} {error_info.recovery_hint}"
    
    return (code.value, message)


def _map_exception_to_code(exception: Exception) -> ErrorCode:
    """Map Python exception to error code."""
    exception_str = str(exception).lower()
    exception_type = type(exception).__name__
    
    if exception_type == "TimeoutError" or "timeout" in exception_str:
        return ErrorCode.TIMEOUT
    
    if "memory" in exception_str or "oom" in exception_str:
        return ErrorCode.GPU_OOM
    
    if "not found" in exception_str:
        return ErrorCode.FILE_NOT_FOUND
    
    if exception_type == "FileNotFoundError":
        return ErrorCode.FILE_NOT_FOUND
    
    if "format" in exception_str or "read" in exception_str:
        return ErrorCode.INVALID_FORMAT
    
    return ErrorCode.PIPELINE_ERROR


