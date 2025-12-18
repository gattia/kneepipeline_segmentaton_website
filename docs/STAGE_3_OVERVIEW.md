# Stage 3: Real Pipeline Integration

> **📋 Detailed Step-by-Step Guide**: See [STAGE_3_DETAILED_PLAN.md](./STAGE_3_DETAILED_PLAN.md) and the [stage_3/](./stage_3/) folder for actionable implementation steps designed for AI agents.

## Overview

**Goal**: Replace the dummy worker with the actual knee MRI segmentation pipeline.

**Estimated Time**: 1 week

**Prerequisites**: 
- Stage 1 complete (Stage 2 optional)
- GPU VM available (NVIDIA T4 or better with CUDA)
- Access to trained model weights (downloadable from HuggingFace)

---

## What This Stage Adds

| Feature | Description |
|---------|-------------|
| **Real Segmentation** | Automatic knee MRI segmentation (femur, tibia, patella, cartilage) |
| **3D Mesh Generation** | VTK surface meshes for all structures |
| **Cartilage Thickness** | Regional thickness measurements |
| **T2 Mapping** | T2 relaxation maps (DICOM qDESS input only) |
| **Neural Shape Model** | NSM fitting with BScore computation |

---

## Pipeline Architecture

```
User Upload → FastAPI → Celery Worker → Real Pipeline → Results Zip
                              │
                              ▼
                    ┌─────────────────────┐
                    │  dosma_knee_seg.py  │  ← Orchestrator script
                    │                     │
                    │  • Input validation │
                    │  • Config loading   │
                    │  • Progress updates │
                    └─────────┬───────────┘
                              │
              ┌───────────────┼───────────────┐
              ▼               ▼               ▼
    ┌─────────────────┐ ┌──────────┐ ┌──────────────────┐
    │ seg_thick_t2_   │ │ T2       │ │ NSM_analysis.py  │
    │ pipeline.py     │ │ mapping  │ │                  │
    │                 │ │ (if DICOM│ │ • Shape fitting  │
    │ • Segmentation  │ │  qDESS)  │ │ • BScore calc    │
    │ • Mesh creation │ └──────────┘ └──────────────────┘
    │ • Thickness     │
    └─────────────────┘
```

---

## Task Breakdown

### 3.1: GPU Environment Setup (~1 day)

- [ ] Provision GPU VM (e.g., NVIDIA T4 or better)
- [ ] Install NVIDIA drivers and CUDA toolkit
- [ ] Install PyTorch with CUDA support
- [ ] Install pipeline dependencies (DOSMA, VTK, etc.)
- [ ] Copy trained model weights to VM
- [ ] Test pipeline manually with sample input

### 3.2: Pipeline Worker Integration (~2 days)

**Goal**: Replace `dummy_pipeline()` with real pipeline execution

- [ ] Create `backend/workers/pipeline_worker.py`
- [ ] Call `dosma_knee_seg.py` as subprocess
- [ ] Pass configuration options (model path, output settings)
- [ ] Capture stdout/stderr for logging
- [ ] Parse progress from pipeline output
- [ ] Update job status in Redis during processing

**Key Implementation**:

```python
# backend/workers/pipeline_worker.py
import subprocess
from pathlib import Path

def run_pipeline(input_path: Path, output_dir: Path, config: dict) -> Path:
    """Execute the real segmentation pipeline."""
    
    # Generate config.json for pipeline
    config_path = output_dir / "config.json"
    config_path.write_text(json.dumps(config))
    
    # Call pipeline subprocess
    result = subprocess.run([
        "python", "dosma_knee_seg.py",
        "--input", str(input_path),
        "--output", str(output_dir),
        "--config", str(config_path)
    ], capture_output=True, text=True, check=True)
    
    # Return path to results zip
    return output_dir / "results.zip"
```

### 3.3: Configuration Mapping (~0.5 day)

**Goal**: Map web UI options to pipeline config.json

| Web Option | Pipeline Config |
|------------|-----------------|
| Model selection | `model_path` |
| Include T2 mapping | `compute_t2` |
| Include NSM analysis | `run_nsm` |
| Output format | `output_format` |

- [ ] Create config template
- [ ] Validate options before pipeline execution
- [ ] Handle model path resolution (relative to weights directory)

### 3.4: GPU Management (~0.5 day)

**Goal**: Ensure stable GPU memory management

- [ ] Single job at a time (Celery concurrency=1)
- [ ] Clear GPU memory after each job (torch.cuda.empty_cache())
- [ ] Monitor GPU memory usage
- [ ] Graceful handling of OOM errors

```python
# After each job
import torch
if torch.cuda.is_available():
    torch.cuda.empty_cache()
    torch.cuda.synchronize()
```

### 3.5: Error Handling (~1 day)

**Goal**: User-friendly error messages for pipeline failures

| Error Type | User Message |
|------------|--------------|
| Invalid input format | "Unable to read MRI file. Please ensure it's a valid NIfTI, NRRD, or DICOM." |
| Segmentation failed | "Segmentation failed. The image quality may be insufficient." |
| OOM error | "Processing failed due to memory limits. Try a smaller file." |
| Timeout | "Processing took too long. Please try again." |

- [ ] Catch subprocess errors
- [ ] Parse pipeline error output
- [ ] Map to user-friendly messages
- [ ] Log detailed errors for debugging

### 3.6: Progress Updates (~0.5 day)

**Goal**: Real progress from pipeline (not simulated)

Pipeline steps to track:
1. Loading input (5%)
2. Preprocessing (10%)
3. Segmentation (40%)
4. Mesh generation (60%)
5. Thickness calculation (70%)
6. T2 mapping (80%) - if applicable
7. NSM analysis (90%) - if applicable
8. Packaging results (100%)

- [ ] Modify pipeline to output progress markers
- [ ] Parse progress from subprocess output
- [ ] Update Redis job status in real-time

---

## Testing Strategy

| Test | Description |
|------|-------------|
| `test_pipeline_worker_called` | Verify subprocess invocation |
| `test_config_generation` | Config.json generated correctly |
| `test_error_handling` | Graceful failure on bad input |
| `test_gpu_cleanup` | Memory freed after job |
| Integration test | Full upload → real pipeline → download |

**Note**: Most tests will use mocked pipeline (real pipeline tests need GPU).

---

## Files to Create/Modify

| File | Changes |
|------|---------|
| `backend/workers/pipeline_worker.py` | New: Real pipeline execution |
| `backend/workers/tasks.py` | Replace dummy_pipeline with real call |
| `backend/services/config_mapper.py` | New: Web options → pipeline config |
| `docker/Dockerfile.gpu` | New: GPU-enabled Docker image |
| `docker/docker-compose.gpu.yml` | New: GPU deployment config |
| `tests/test_stage_3.py` | New test file |

---

## GPU Docker Configuration

```dockerfile
# docker/Dockerfile.gpu
FROM nvidia/cuda:11.8-cudnn8-runtime-ubuntu22.04

# Install Python and dependencies
RUN apt-get update && apt-get install -y python3.10 python3-pip

# Install PyTorch with CUDA
RUN pip install torch torchvision --index-url https://download.pytorch.org/whl/cu118

# Install pipeline dependencies
COPY requirements-gpu.txt .
RUN pip install -r requirements-gpu.txt

# Copy pipeline code and models
COPY pipeline/ /app/pipeline/
COPY models/ /app/models/

# ... rest of Dockerfile
```

```yaml
# docker/docker-compose.gpu.yml
services:
  worker:
    build:
      context: ..
      dockerfile: docker/Dockerfile.gpu
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]
```

---

## Success Criteria

- [ ] Real segmentation produces valid output files
- [ ] 3D meshes viewable in external tools (ParaView, 3D Slicer)
- [ ] Thickness measurements match expected values
- [ ] BScore computed for test inputs
- [ ] Processing time ~5-10 minutes for typical MRI
- [ ] Errors handled gracefully with user-friendly messages
- [ ] GPU memory stable across multiple jobs

---

## Model Weights

Required model files (not in git, stored separately):

```
models/
├── segmentation/
│   └── knee_seg_model.pth      # ~500MB
├── nsm/
│   ├── nsm_encoder.pth
│   └── nsm_decoder.pth
└── config/
    └── default_config.json
```

**Storage**: GCS bucket or mounted volume

---

## References

- [PROJECT_OVERVIEW.md](./PROJECT_OVERVIEW.md) - Full architecture details
- [Reference: Existing Pipeline](./PROJECT_OVERVIEW.md#reference-existing-pipeline) - Original pipeline documentation
- DOSMA documentation: https://github.com/ad12/DOSMA

---

## Notes

- **Single GPU**: Start with one GPU worker; horizontal scaling in Phase 4
- **Cold start**: First job may take longer (model loading); consider keeping models in memory
- **Testing on CPU**: Pipeline should work on CPU (slower) for testing without GPU
