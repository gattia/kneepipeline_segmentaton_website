# Stage 3.3 Completed: Pipeline Worker Integration

**Completed**: December 18, 2025

---

## Summary

Successfully integrated the real segmentation pipeline into the web application. The Celery worker can now execute the actual `dosma_knee_seg.py` pipeline as a subprocess, with proper configuration generation, progress tracking, error handling, and GPU memory cleanup.

---

## What Was Done

### 1. Config Generator Created

**File**: `backend/services/config_generator.py`

Generates job-specific `config.json` files based on web UI options:

| Web UI Option | Config Parameter |
|---------------|------------------|
| `segmentation_model: nnunet_fullres` | `default_seg_model: nnunet_knee`, `nnunet.type: fullres` |
| `segmentation_model: nnunet_cascade` | `default_seg_model: nnunet_knee`, `nnunet.type: cascade` |
| `perform_nsm: true, nsm_type: bone_and_cart` | `perform_bone_and_cart_nsm: true` |
| `perform_nsm: true, nsm_type: bone_only` | `perform_bone_only_nsm: true` |
| `perform_nsm: true, nsm_type: both` | Both NSM options enabled |
| `perform_nsm: false` | Both NSM options disabled |

**Functions:**
- `generate_pipeline_config(job_dir, options)` - Creates job-specific config.json
- `_map_segmentation_model(web_model)` - Maps web model names to pipeline names
- `get_pipeline_script_path()` - Returns path to dosma_knee_seg.py
- `get_base_config_path()` - Returns path to base config.json

### 2. Pipeline Worker Created

**File**: `backend/workers/pipeline_worker.py`

Executes the real segmentation pipeline as a subprocess:

| Feature | Implementation |
|---------|----------------|
| **Subprocess Execution** | Runs `dosma_knee_seg.py` with proper environment |
| **Timeout Handling** | 30-minute timeout (configurable via `PIPELINE_TIMEOUT_SECONDS`) |
| **Progress Updates** | 5-step progress callback |
| **GPU Cleanup** | `torch.cuda.empty_cache()` + garbage collection after each job |
| **Error Parsing** | User-friendly error messages for OOM, file not found, etc. |
| **Output Verification** | Checks for expected output files before packaging |

**Functions:**
- `run_real_pipeline(input_path, options, output_dir, config_path, progress_callback)` - Main execution
- `cleanup_gpu_memory()` - Clears GPU memory and runs garbage collection
- `_verify_pipeline_outputs(output_dir)` - Verifies expected files exist
- `_parse_pipeline_error(error_output)` - Creates user-friendly error messages

### 3. Tasks Updated

**File**: `backend/workers/tasks.py`

Updated to use real pipeline by default. Set `USE_DUMMY_PIPELINE=1` env var to use dummy pipeline for testing.

**New Error Codes:**

| Error Code | Triggered By |
|------------|--------------|
| `TIMEOUT` | Pipeline exceeds 30-minute timeout |
| `GPU_OOM` | CUDA out of memory errors |
| `FILE_NOT_FOUND` | Input file missing |
| `INVALID_FORMAT` | Unreadable file format |
| `DICOM_ERROR` | DICOM-specific errors |
| `PIPELINE_ERROR` | General pipeline failures |

### 4. Services Package Updated

**File**: `backend/services/__init__.py`

Added exports: `generate_pipeline_config`, `get_pipeline_script_path`, `get_base_config_path`

### 5. Tests Created

**File**: `tests/test_stage_3_3.py`

41 comprehensive tests covering config generator, pipeline worker, model mapping, error codes, and output verification.

---

## File Changes Summary

### New Files

- `backend/services/config_generator.py` - Generate job-specific config
- `backend/workers/pipeline_worker.py` - Real pipeline execution  
- `tests/test_stage_3_3.py` - 41 verification tests

### Modified Files

- `backend/services/__init__.py` - Added config_generator exports
- `backend/workers/tasks.py` - Use real pipeline, error handling
- `pyproject.toml` - Added stage_3_3 marker

---

## Verification Results

All 41 Stage 3.3 tests pass:

```
$ pytest -m stage_3_3 -v
====================== 41 passed in 5.57s ======================
```

---

## Usage

### Default Behavior

By default, the worker now uses the **real pipeline**:

```bash
make worker
```

### Testing with Dummy Pipeline

```bash
export USE_DUMMY_PIPELINE=1
make worker
```

---

## Next Step

**Stage 3.4: Configuration Mapping** - See [STAGE_3.4_CONFIG_MAPPING.md](./STAGE_3.4_CONFIG_MAPPING.md)
