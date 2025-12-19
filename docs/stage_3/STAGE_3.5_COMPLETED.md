# Stage 3.5 Completed: Error Handling and Progress Updates

**Completed**: December 18, 2025

---

## Summary

Successfully implemented robust error handling and real-time progress tracking for the pipeline. Users now receive user-friendly error messages with recovery hints, and progress updates show meaningful step names during processing.

---

## What Was Done

### 1. Created Error Handler Module

**File**: `backend/services/error_handler.py`

A comprehensive error handling module with:

| Component | Description |
|-----------|-------------|
| `ErrorCode` enum | 9 specific error codes for pipeline failures |
| `PipelineError` dataclass | Structured error with code, message, details, recovery hint |
| `ERROR_MESSAGES` dict | User-friendly messages for each error code |
| `parse_error_from_output()` | Parses pipeline stdout/stderr to detect error type |
| `get_error_response()` | Formats error for API response |
| `format_error_for_job()` | Formats error for job storage |
| `_map_exception_to_code()` | Maps Python exceptions to error codes |

**Error Codes**:

| Error Code | Detection Pattern | User Message |
|------------|-------------------|--------------|
| `GPU_OOM` | "cuda out of memory", "oom" | The GPU ran out of memory while processing your file. |
| `TIMEOUT` | "timeout" | Processing took longer than expected and was stopped. |
| `INVALID_FORMAT` | "invalid format", "cannot read" | The uploaded file format is not supported. |
| `FILE_NOT_FOUND` | "not found", "no such file" | The uploaded file could not be found. |
| `DICOM_ERROR` | "dicom", "dcm error" | The DICOM files could not be read properly. |
| `SEGMENTATION_FAILED` | "segmentation failed/error" | The segmentation step failed to complete. |
| `NSM_FAILED` | "nsm error/failed", "shape model" | Neural Shape Model analysis failed. |
| `CONFIG_ERROR` | "config error", "invalid config" | There was an error with the processing configuration. |
| `PIPELINE_ERROR` | (default fallback) | An unexpected error occurred during processing. |

**Usage Example**:

```python
from backend.services.error_handler import (
    parse_error_from_output,
    get_error_response,
    format_error_for_job,
    ErrorCode
)

# Parse error from pipeline output
output = "RuntimeError: CUDA out of memory. Tried to allocate 2.00 GiB"
error_code = parse_error_from_output(output)  # Returns ErrorCode.GPU_OOM

# Get user-friendly response for API
response = get_error_response(error_code)
# Returns: {
#     "error_code": "GPU_OOM",
#     "message": "The GPU ran out of memory while processing your file.",
#     "recovery_hint": "Try reducing the batch size...",
#     "details": None
# }

# Format for job storage
code, message = format_error_for_job(exception, output=output)
# Returns: ("GPU_OOM", "The GPU ran out of memory... Try reducing the batch size...")
```

### 2. Created Progress Parser Module

**File**: `backend/services/progress_parser.py`

Real-time progress parsing from pipeline output:

| Component | Description |
|-----------|-------------|
| `ProgressUpdate` dataclass | Structured progress: step, total_steps, step_name, percent |
| `STEP_PATTERNS` | Regex patterns for detecting pipeline steps |
| `TOTAL_STEPS` | Total pipeline steps (10) |
| `parse_progress_line()` | Parse single line of output for progress |
| `estimate_progress_from_time()` | Time-based fallback when no explicit progress |

**Pipeline Steps Detected**:

| Step | Pattern | Display Name |
|------|---------|--------------|
| 1 | `loading.*model` | Loading segmentation model |
| 2 | `preprocessing` | Preprocessing image |
| 3 | `running.*segmentation` | Running segmentation |
| 4 | `postprocessing` | Postprocessing results |
| 5 | `generating.*mesh` | Generating 3D meshes |
| 6 | `calculating.*thickness` | Calculating cartilage thickness |
| 7 | `running.*nsm\|neural shape model` | Running Neural Shape Model |
| 8 | `computing.*bscore` | Computing BScore |
| 9 | `saving.*results` | Saving results |
| 10 | `complete\|finished\|done` | Complete |

**Progress Detection Methods**:

1. **Pattern Matching**: Matches step patterns in output lines
2. **Explicit Markers**: `[PROGRESS] 5/10: Step name`
3. **Percentage**: `Processing... 45%`
4. **Time-based**: Fallback based on elapsed time

**Usage Example**:

```python
from backend.services.progress_parser import (
    parse_progress_line,
    estimate_progress_from_time
)

# Parse progress from pipeline output
progress = parse_progress_line("Running segmentation model...")
# Returns: ProgressUpdate(step=3, total_steps=10, step_name="Running segmentation", percent=30)

# Time-based fallback
progress = estimate_progress_from_time(elapsed_seconds=150, estimated_total=300)
# Returns: ProgressUpdate(step=5, total_steps=10, step_name="Generating meshes", percent=50)
```

### 3. Added Progress Streaming to Pipeline Worker

**File**: `backend/workers/pipeline_worker.py`

Added `run_pipeline_with_progress()` function for real-time progress streaming:

| Feature | Description |
|---------|-------------|
| Non-blocking I/O | Uses threading and queues to read stdout/stderr |
| Progress callbacks | Invokes callback on each progress update |
| Timeout support | Kills process if timeout exceeded |
| Stream parsing | Parses both stdout and stderr for progress |

**Function Signature**:

```python
def run_pipeline_with_progress(
    command: list,
    env: dict,
    cwd: str,
    timeout: int,
    progress_callback: Optional[Callable[[int, int, str], None]] = None,
) -> tuple:
    """
    Run pipeline subprocess with real-time progress parsing.
    
    Returns: (returncode, stdout, stderr)
    """
```

### 4. Updated Tasks Module

**File**: `backend/workers/tasks.py`

- Updated exception handlers to use `format_error_for_job()`
- Removed old `_get_error_code()` function
- Error messages now include recovery hints for users

**Before** (old code):
```python
except Exception as e:
    job.error_message = str(e)
    job.error_code = _get_error_code(e)
```

**After** (new code):
```python
except Exception as e:
    from backend.services.error_handler import format_error_for_job
    output = getattr(e, 'output', str(e))
    error_code, error_message = format_error_for_job(e, output)
    job.error_message = error_message
    job.error_code = error_code
```

### 5. Updated Service Exports

**File**: `backend/services/__init__.py`

Added exports for new modules:

```python
# Error handler exports
from .error_handler import (
    ERROR_MESSAGES,
    ErrorCode,
    PipelineError,
    format_error_for_job,
    get_error_response,
    parse_error_from_output,
)

# Progress parser exports  
from .progress_parser import (
    STEP_PATTERNS,
    TOTAL_STEPS,
    ProgressUpdate,
    estimate_progress_from_time,
    parse_progress_line,
)
```

### 6. Created Verification Tests

**File**: `tests/test_stage_3_5.py`

30 comprehensive tests across 7 test classes:

| Test Class | Tests | Coverage |
|------------|-------|----------|
| `TestErrorParsing` | 7 | Parsing errors from pipeline output |
| `TestErrorResponses` | 3 | Error response formatting |
| `TestProgressParsing` | 7 | Progress parsing from output |
| `TestTimeBasedProgress` | 3 | Time-based progress estimation |
| `TestFormatErrorForJob` | 4 | Error formatting for job storage |
| `TestExceptionMapping` | 4 | Python exception mapping |
| `TestProgressUpdate` | 2 | ProgressUpdate dataclass |

---

## File Changes Summary

### New Files

| File | Description |
|------|-------------|
| `backend/services/error_handler.py` | Error code mapping and user-friendly messages |
| `backend/services/progress_parser.py` | Progress parsing from pipeline output |
| `tests/test_stage_3_5.py` | 30 verification tests |
| `docs/stage_3/STAGE_3.5_COMPLETED.md` | This file |

### Modified Files

| File | Changes |
|------|---------|
| `backend/workers/pipeline_worker.py` | Added imports, `run_pipeline_with_progress()` function |
| `backend/workers/tasks.py` | Use `format_error_for_job()`, removed `_get_error_code()` |
| `backend/services/__init__.py` | Export error_handler and progress_parser |
| `pyproject.toml` | Added `stage_3_5` pytest marker |
| `tests/test_stage_3_3.py` | Updated TestErrorCodeMapping to use error_handler |

---

## Verification Results

All tests pass:

```bash
# Stage 3.5 tests only
$ pytest -m stage_3_5 -v
============================= 30 passed in 0.83s ==============================

# All Stage 3 tests
$ pytest -m "stage_3_3 or stage_3_4 or stage_3_5" -v
============================= 125 passed in 5.49s ==============================
```

Manual verification:

```python
from backend.services.error_handler import parse_error_from_output, get_error_response

test_outputs = [
    "CUDA out of memory",           # -> GPU_OOM
    "DICOM read error",             # -> DICOM_ERROR
    "Segmentation failed",          # -> SEGMENTATION_FAILED
]

for output in test_outputs:
    code = parse_error_from_output(output)
    print(f"{output} -> {code.value}")
```

---

## Key Features

### Error Handling

1. **Specific Error Codes**: 9 distinct error codes for different failure modes
2. **User-Friendly Messages**: Non-technical messages users can understand
3. **Recovery Hints**: Actionable suggestions for fixing the problem
4. **Output Parsing**: Detects error type from pipeline stdout/stderr
5. **Exception Mapping**: Maps Python exceptions to error codes

### Progress Tracking

1. **Real-time Updates**: Progress parsed from subprocess output
2. **Pattern Matching**: Detects steps from output text
3. **Explicit Markers**: Supports `[PROGRESS]` format
4. **Percentage Detection**: Parses `45%` style markers
5. **Time-based Fallback**: Estimates progress when no markers available
6. **Non-blocking I/O**: Uses threading for responsive updates

---

## Success Criteria Met

- ✅ Pipeline errors map to user-friendly messages
- ✅ Progress updates show real step names from pipeline
- ✅ GPU OOM errors are handled gracefully
- ✅ Timeout errors provide helpful guidance
- ✅ File format errors are specific and actionable
- ✅ All Stage 3.5 tests pass

---

## Next Step

**Stage 3.6: Integration Testing** - See [STAGE_3.6_INTEGRATION_TESTING.md](./STAGE_3.6_INTEGRATION_TESTING.md)


