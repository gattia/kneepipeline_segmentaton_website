# Stage 3.5: Error Handling and Progress Updates

## Overview

**Goal**: Add robust error handling and real-time progress tracking for the pipeline.

**Estimated Time**: ~1-2 hours

**Deliverable**: User-friendly error messages and accurate progress updates during processing.

---

## Prerequisites

**Stage 3.4 must be complete.** Verify by running:

```bash
conda activate kneepipeline
cd ~/programming/kneepipeline_segmentaton_website

# Stage 3.4 tests should pass
pytest -m stage_3_4 -v

# Config generation should work
python -c "from backend.services.config_generator import validate_options; print('OK')"
```

---

## What This Stage Creates

### New Files

```
backend/
└── services/
    └── error_handler.py         # NEW: Error mapping and handling

tests/
└── test_stage_3_5.py            # NEW: Stage 3.5 verification tests
```

### Modified Files

```
backend/
└── workers/
    ├── pipeline_worker.py       # MODIFY: Add progress parsing
    └── tasks.py                 # MODIFY: Use error handler
```

---

## Success Criteria

- [ ] Pipeline errors map to user-friendly messages
- [ ] Progress updates show real step names from pipeline
- [ ] GPU OOM errors are handled gracefully
- [ ] Timeout errors provide helpful guidance
- [ ] File format errors are specific and actionable
- [ ] All Stage 3.5 tests pass: `pytest -m stage_3_5 -v`

---

## Error Categories

| Error Code | User Message | Recovery Action |
|------------|--------------|-----------------|
| `GPU_OOM` | GPU ran out of memory | Retry with smaller batch, or try different model |
| `TIMEOUT` | Processing took too long | Contact support, file may be too large |
| `INVALID_FORMAT` | File format not recognized | Use NIfTI (.nii.gz), NRRD, or DICOM zip |
| `FILE_NOT_FOUND` | Input file could not be found | Re-upload the file |
| `DICOM_ERROR` | DICOM files could not be read | Ensure valid DICOM series |
| `SEGMENTATION_FAILED` | Segmentation could not complete | Try different model, check image quality |
| `NSM_FAILED` | Shape analysis failed | Run without NSM, or try bone-only |
| `PIPELINE_ERROR` | An unexpected error occurred | Contact support |

---

## Detailed Implementation

### Step 1: Create Error Handler Module

**File**: `backend/services/error_handler.py`

```python
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
```

---

### Step 2: Create Progress Parser

**File**: `backend/services/progress_parser.py`

```python
"""
Progress parsing from pipeline output.

Parses stdout from the pipeline to extract progress information
for real-time updates to the web UI.
"""
import re
from dataclasses import dataclass
from typing import Optional


@dataclass
class ProgressUpdate:
    """Parsed progress information."""
    step: int
    total_steps: int
    step_name: str
    percent: int
    substep: Optional[str] = None


# Pipeline step patterns to watch for
STEP_PATTERNS = [
    # Pattern: (regex, step_number, step_name)
    (r"loading.*model", 1, "Loading segmentation model"),
    (r"preprocessing", 2, "Preprocessing image"),
    (r"running.*segmentation", 3, "Running segmentation"),
    (r"postprocessing", 4, "Postprocessing results"),
    (r"generating.*mesh", 5, "Generating 3D meshes"),
    (r"calculating.*thickness", 6, "Calculating cartilage thickness"),
    (r"running.*nsm|neural shape model", 7, "Running Neural Shape Model"),
    (r"computing.*bscore", 8, "Computing BScore"),
    (r"saving.*results", 9, "Saving results"),
    (r"complete|finished|done", 10, "Complete"),
]

# Total steps in full pipeline
TOTAL_STEPS = 10


def parse_progress_line(line: str) -> Optional[ProgressUpdate]:
    """
    Parse a single line of pipeline output for progress.
    
    Args:
        line: Single line from pipeline stdout/stderr
        
    Returns:
        ProgressUpdate if progress detected, None otherwise
    """
    line_lower = line.lower().strip()
    
    for pattern, step, step_name in STEP_PATTERNS:
        if re.search(pattern, line_lower):
            percent = int((step / TOTAL_STEPS) * 100)
            return ProgressUpdate(
                step=step,
                total_steps=TOTAL_STEPS,
                step_name=step_name,
                percent=percent,
            )
    
    # Check for explicit progress markers (if pipeline outputs them)
    # Format: [PROGRESS] step/total: step_name
    progress_match = re.search(r'\[PROGRESS\]\s*(\d+)/(\d+):\s*(.+)', line)
    if progress_match:
        step = int(progress_match.group(1))
        total = int(progress_match.group(2))
        name = progress_match.group(3).strip()
        return ProgressUpdate(
            step=step,
            total_steps=total,
            step_name=name,
            percent=int((step / total) * 100),
        )
    
    # Check for percentage markers
    # Format: Processing... 45% or [45%] or (45%)
    percent_match = re.search(r'(\d{1,3})%', line)
    if percent_match:
        percent = min(int(percent_match.group(1)), 100)
        step = max(1, int((percent / 100) * TOTAL_STEPS))
        return ProgressUpdate(
            step=step,
            total_steps=TOTAL_STEPS,
            step_name="Processing...",
            percent=percent,
        )
    
    return None


def estimate_progress_from_time(elapsed_seconds: float, estimated_total: float) -> ProgressUpdate:
    """
    Estimate progress based on elapsed time.
    
    Used as fallback when pipeline doesn't provide progress info.
    
    Args:
        elapsed_seconds: Time since processing started
        estimated_total: Estimated total processing time
        
    Returns:
        ProgressUpdate based on time
    """
    if estimated_total <= 0:
        estimated_total = 300  # Default 5 minutes
    
    percent = min(95, int((elapsed_seconds / estimated_total) * 100))
    step = max(1, int((percent / 100) * TOTAL_STEPS))
    
    # Map step to name
    step_names = {
        1: "Loading model",
        2: "Preprocessing",
        3: "Running segmentation",
        4: "Postprocessing",
        5: "Generating meshes",
        6: "Calculating thickness",
        7: "Running NSM",
        8: "Computing BScore",
        9: "Saving results",
        10: "Complete",
    }
    
    return ProgressUpdate(
        step=step,
        total_steps=TOTAL_STEPS,
        step_name=step_names.get(step, "Processing..."),
        percent=percent,
    )
```

---

### Step 3: Update Pipeline Worker with Progress Streaming

**File**: `backend/workers/pipeline_worker.py` (add to existing)

Add this function for streaming progress:

```python
import subprocess
import threading
from queue import Queue, Empty
from typing import Callable, Optional

from backend.services.progress_parser import parse_progress_line, estimate_progress_from_time


def run_pipeline_with_progress(
    command: list,
    env: dict,
    cwd: str,
    timeout: int,
    progress_callback: Optional[Callable[[int, int, str], None]] = None,
) -> tuple:
    """
    Run pipeline subprocess with real-time progress parsing.
    
    Args:
        command: Command list to execute
        env: Environment variables
        cwd: Working directory
        timeout: Timeout in seconds
        progress_callback: Callback for progress updates
        
    Returns:
        Tuple of (returncode, stdout, stderr)
    """
    import time
    
    process = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        cwd=cwd,
        env=env,
    )
    
    stdout_lines = []
    stderr_lines = []
    last_progress = None
    start_time = time.time()
    
    # Queues for non-blocking reads
    stdout_queue = Queue()
    stderr_queue = Queue()
    
    def read_stream(stream, queue):
        for line in iter(stream.readline, ''):
            queue.put(line)
        stream.close()
    
    # Start reader threads
    stdout_thread = threading.Thread(target=read_stream, args=(process.stdout, stdout_queue))
    stderr_thread = threading.Thread(target=read_stream, args=(process.stderr, stderr_queue))
    stdout_thread.daemon = True
    stderr_thread.daemon = True
    stdout_thread.start()
    stderr_thread.start()
    
    # Monitor process with timeout
    while True:
        elapsed = time.time() - start_time
        
        # Check timeout
        if elapsed > timeout:
            process.kill()
            raise TimeoutError(f"Pipeline exceeded {timeout}s timeout")
        
        # Read available output
        try:
            while True:
                line = stdout_queue.get_nowait()
                stdout_lines.append(line)
                
                # Try to parse progress
                if progress_callback:
                    progress = parse_progress_line(line)
                    if progress and progress != last_progress:
                        progress_callback(progress.step, progress.total_steps, progress.step_name)
                        last_progress = progress
        except Empty:
            pass
        
        try:
            while True:
                line = stderr_queue.get_nowait()
                stderr_lines.append(line)
                
                # Also check stderr for progress
                if progress_callback:
                    progress = parse_progress_line(line)
                    if progress and progress != last_progress:
                        progress_callback(progress.step, progress.total_steps, progress.step_name)
                        last_progress = progress
        except Empty:
            pass
        
        # Check if process finished
        if process.poll() is not None:
            break
        
        # Update progress based on time if no explicit progress
        if progress_callback and last_progress is None:
            time_progress = estimate_progress_from_time(elapsed, 300)  # 5 min estimate
            progress_callback(time_progress.step, time_progress.total_steps, time_progress.step_name)
        
        time.sleep(0.5)  # Small delay between checks
    
    # Get any remaining output
    stdout_thread.join(timeout=1)
    stderr_thread.join(timeout=1)
    
    return (
        process.returncode,
        ''.join(stdout_lines),
        ''.join(stderr_lines),
    )
```

---

### Step 4: Update Tasks to Use Error Handler

**File**: `backend/workers/tasks.py` (update error handling section)

```python
# Add import at top
from backend.services.error_handler import format_error_for_job, parse_error_from_output

# Update the exception handling in process_pipeline:
    except TimeoutError as e:
        error_code, error_message = format_error_for_job(e)
        job.status = "error"
        job.error_message = error_message
        job.error_code = error_code
        job.save(redis_client)
        _cleanup_after_error()
        raise
        
    except Exception as e:
        # Try to get more specific error from pipeline output
        output = getattr(e, 'output', str(e))
        error_code, error_message = format_error_for_job(e, output)
        job.status = "error"
        job.error_message = error_message
        job.error_code = error_code
        job.save(redis_client)
        _cleanup_after_error()
        raise
```

---

### Step 5: Create Stage 3.5 Tests

**File**: `tests/test_stage_3_5.py`

```python
"""
Stage 3.5 Verification Tests - Error Handling and Progress

Run with: pytest -m stage_3_5 -v

These tests verify:
1. Error parsing from pipeline output
2. Error code mapping
3. User-friendly error messages
4. Progress parsing
"""
import pytest

# Mark all tests in this module as stage_3_5
pytestmark = pytest.mark.stage_3_5


class TestErrorParsing:
    """Verify error parsing from pipeline output."""
    
    def test_parse_cuda_oom(self):
        """CUDA OOM should be detected."""
        from backend.services.error_handler import ErrorCode, parse_error_from_output
        
        output = "RuntimeError: CUDA out of memory. Tried to allocate 2.00 GiB"
        assert parse_error_from_output(output) == ErrorCode.GPU_OOM
    
    def test_parse_gpu_memory_error(self):
        """GPU memory error variations should be detected."""
        from backend.services.error_handler import ErrorCode, parse_error_from_output
        
        outputs = [
            "Out of memory error occurred",
            "CUDA error: out of memory",
            "GPU memory allocation failed",
        ]
        for output in outputs:
            assert parse_error_from_output(output) == ErrorCode.GPU_OOM
    
    def test_parse_file_not_found(self):
        """File not found should be detected."""
        from backend.services.error_handler import ErrorCode, parse_error_from_output
        
        output = "FileNotFoundError: Input file not found: /path/to/file"
        assert parse_error_from_output(output) == ErrorCode.FILE_NOT_FOUND
    
    def test_parse_dicom_error(self):
        """DICOM errors should be detected."""
        from backend.services.error_handler import ErrorCode, parse_error_from_output
        
        output = "Error reading DICOM series: No valid DICOM files found"
        assert parse_error_from_output(output) == ErrorCode.DICOM_ERROR
    
    def test_parse_segmentation_failed(self):
        """Segmentation failure should be detected."""
        from backend.services.error_handler import ErrorCode, parse_error_from_output
        
        output = "Segmentation failed: No valid labels produced"
        assert parse_error_from_output(output) == ErrorCode.SEGMENTATION_FAILED
    
    def test_parse_nsm_error(self):
        """NSM errors should be detected."""
        from backend.services.error_handler import ErrorCode, parse_error_from_output
        
        output = "NSM Error: Failed to fit shape model"
        assert parse_error_from_output(output) == ErrorCode.NSM_FAILED
    
    def test_parse_unknown_defaults_to_pipeline_error(self):
        """Unknown error should default to PIPELINE_ERROR."""
        from backend.services.error_handler import ErrorCode, parse_error_from_output
        
        output = "Some random unexpected error that doesn't match patterns"
        assert parse_error_from_output(output) == ErrorCode.PIPELINE_ERROR


class TestErrorResponses:
    """Verify error response formatting."""
    
    def test_error_response_has_required_fields(self):
        """Error response should have all required fields."""
        from backend.services.error_handler import ErrorCode, get_error_response
        
        response = get_error_response(ErrorCode.GPU_OOM)
        
        assert "error_code" in response
        assert "message" in response
        assert "recovery_hint" in response
    
    def test_error_response_includes_details(self):
        """Error response should include provided details."""
        from backend.services.error_handler import ErrorCode, get_error_response
        
        response = get_error_response(ErrorCode.GPU_OOM, "Technical: 15GB required, 12GB available")
        
        assert response["details"] == "Technical: 15GB required, 12GB available"
    
    def test_all_error_codes_have_messages(self):
        """All error codes should have user-friendly messages."""
        from backend.services.error_handler import ERROR_MESSAGES, ErrorCode
        
        for code in ErrorCode:
            assert code in ERROR_MESSAGES, f"Missing message for {code}"
            assert ERROR_MESSAGES[code].message, f"Empty message for {code}"
            assert ERROR_MESSAGES[code].recovery_hint, f"Empty recovery hint for {code}"


class TestProgressParsing:
    """Verify progress parsing from pipeline output."""
    
    def test_parse_segmentation_progress(self):
        """Segmentation step should be detected."""
        from backend.services.progress_parser import parse_progress_line
        
        progress = parse_progress_line("Running segmentation model...")
        
        assert progress is not None
        assert "segmentation" in progress.step_name.lower()
    
    def test_parse_mesh_generation(self):
        """Mesh generation should be detected."""
        from backend.services.progress_parser import parse_progress_line
        
        progress = parse_progress_line("Generating 3D mesh for femur...")
        
        assert progress is not None
        assert "mesh" in progress.step_name.lower()
    
    def test_parse_explicit_progress_marker(self):
        """Explicit [PROGRESS] markers should be parsed."""
        from backend.services.progress_parser import parse_progress_line
        
        progress = parse_progress_line("[PROGRESS] 5/10: Computing thickness")
        
        assert progress is not None
        assert progress.step == 5
        assert progress.total_steps == 10
        assert "thickness" in progress.step_name.lower()
    
    def test_parse_percentage(self):
        """Percentage markers should be parsed."""
        from backend.services.progress_parser import parse_progress_line
        
        progress = parse_progress_line("Processing... 45%")
        
        assert progress is not None
        assert progress.percent == 45
    
    def test_no_progress_in_random_line(self):
        """Random lines should not produce progress."""
        from backend.services.progress_parser import parse_progress_line
        
        progress = parse_progress_line("2024-01-15 10:30:45 INFO Loading configuration")
        
        # Should return None for non-progress lines
        assert progress is None


class TestFormatErrorForJob:
    """Verify error formatting for job storage."""
    
    def test_format_timeout_error(self):
        """Timeout error should format correctly."""
        from backend.services.error_handler import format_error_for_job
        
        error_code, message = format_error_for_job(TimeoutError("Pipeline timed out"))
        
        assert error_code == "TIMEOUT"
        assert "took longer" in message.lower()
    
    def test_format_memory_error(self):
        """Memory error should format correctly."""
        from backend.services.error_handler import format_error_for_job
        
        error_code, message = format_error_for_job(
            Exception("CUDA out of memory"),
            output="RuntimeError: CUDA out of memory"
        )
        
        assert error_code == "GPU_OOM"
        assert "gpu" in message.lower() or "memory" in message.lower()
```

---

## Verification Commands

```bash
conda activate kneepipeline
cd ~/programming/kneepipeline_segmentaton_website

# Run Stage 3.5 tests
pytest -m stage_3_5 -v

# Test error parsing manually
python << 'EOF'
from backend.services.error_handler import parse_error_from_output, get_error_response

# Test different error messages
test_outputs = [
    "CUDA out of memory",
    "FileNotFoundError: /path/file",
    "DICOM read error",
    "Segmentation failed",
    "Random unknown error"
]

for output in test_outputs:
    code = parse_error_from_output(output)
    response = get_error_response(code)
    print(f"{output[:30]:<35} -> {code.value}")
EOF
```

---

## Git Commit

```bash
git add .
git commit -m "Stage 3.5: Error handling and progress updates

- Create backend/services/error_handler.py with error code mapping
- Create backend/services/progress_parser.py for pipeline output parsing
- Add user-friendly error messages with recovery hints
- Add progress streaming from pipeline subprocess
- Map GPU OOM, timeout, format, DICOM, segmentation errors
- Add Stage 3.5 verification tests

Error codes supported:
- GPU_OOM: CUDA memory errors
- TIMEOUT: Long-running jobs
- INVALID_FORMAT: Unrecognized file types
- FILE_NOT_FOUND: Missing inputs
- DICOM_ERROR: DICOM read failures
- SEGMENTATION_FAILED: Model failures
- NSM_FAILED: Shape model errors
- PIPELINE_ERROR: Generic fallback
"
```

---

## Next Step: Stage 3.6 - Integration Testing

See [STAGE_3.6_INTEGRATION_TESTING.md](./STAGE_3.6_INTEGRATION_TESTING.md)


