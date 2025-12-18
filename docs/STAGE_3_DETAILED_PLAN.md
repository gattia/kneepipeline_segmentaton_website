# Stage 3: Real Pipeline Integration - Detailed Implementation Plan

## Overview

**Goal**: Replace the dummy worker with the actual knee MRI segmentation pipeline, enabling real segmentation, mesh generation, thickness measurements, and BScore computation.

**Estimated Duration**: ~1 week

**Key Deliverable**: A fully functional pipeline that processes real MRI data and produces segmentations, meshes, and metrics.

---

## Table of Contents

1. [Prerequisites & GPU Environment](#1-prerequisites--gpu-environment)
2. [Task Breakdown](#2-task-breakdown)
3. [Dependencies & Libraries](#3-dependencies--libraries)
4. [Model Weights](#4-model-weights)
5. [Step-by-Step Guides](#5-step-by-step-guides)
6. [Success Criteria](#6-success-criteria)
7. [Task Checklist](#7-task-checklist)

---

## 1. Prerequisites & GPU Environment

### 1.1 System Requirements

| Requirement | Version/Details |
|-------------|-----------------|
| GPU | NVIDIA T4 or better (15GB+ VRAM) |
| CUDA | 12.0+ (via NVIDIA driver) |
| Python | 3.10 |
| Conda | Miniconda with `kneepipeline` environment |
| Docker | With NVIDIA Container Toolkit |
| Redis | 7.x (running in Docker) |

### 1.2 Verify GPU Setup

```bash
# Verify GPU is accessible
nvidia-smi

# Verify Docker can access GPU
docker run --rm --gpus all nvidia/cuda:12.0.0-base-ubuntu22.04 nvidia-smi

# Expected output: Tesla T4 with 15360MiB memory
```

### 1.3 Pipeline Library Location

The main pipeline library is located at:
```
/home/gattia/programming/kneepipeline/
├── dosma_knee_seg.py           # Main orchestrator
├── seg_thick_t2_pipeline.py    # Segmentation, meshes, thickness
├── NSM_analysis.py             # Neural Shape Model (bone + cartilage)
├── NSM_analysis_bone_only.py   # Neural Shape Model (bone only)
├── utils.py                    # Utility functions
├── config_template.json        # Configuration template
├── BSCORE_MODELS/              # BScore model files (included)
└── DEPENDENCIES/
    └── nnunet_knee_inference/  # nnU-Net submodule (needs init)
```

---

## 2. Task Breakdown

### Stage 3.1: Pipeline Dependencies Installation (~1-2 hours)
Install all Python dependencies required for the segmentation pipeline.

- [ ] Install PyTorch with CUDA support
- [ ] Install NSM library
- [ ] Install DOSMA (bone_seg branch)
- [ ] Install nnU-Net inference package
- [ ] Install supporting libraries (VTK, pymskt)
- [ ] Handle NumPy/TensorFlow compatibility issues
- [ ] Verify all imports work

### Stage 3.2: Model Download and Configuration (~30 mins - 1 hour)
Download model weights and configure paths.

- [ ] Initialize nnunet_knee_inference submodule
- [ ] Download nnU-Net models from HuggingFace
- [ ] Download DOSMA weights from HuggingFace
- [ ] Download NSM models from HuggingFace
- [ ] Create `config.json` with correct paths
- [ ] Verify pipeline runs manually with test image

### Stage 3.3: Pipeline Worker Integration (~2-3 hours)
Replace the dummy worker with real pipeline execution.

- [ ] Create `backend/workers/pipeline_worker.py`
- [ ] Create `backend/services/config_generator.py`
- [ ] Update `backend/workers/tasks.py` to use real pipeline
- [ ] Add GPU memory management
- [ ] Add subprocess timeout handling
- [ ] Create Stage 3.3 verification tests

### Stage 3.4: Configuration Mapping (~1 hour)
Map web UI options to pipeline configuration.

- [ ] Map segmentation model selection
- [ ] Map NSM options (bone+cart, bone only, both)
- [ ] Handle DOSMA vs nnU-Net model paths
- [ ] Validate configuration before execution
- [ ] Create Stage 3.4 verification tests

### Stage 3.5: Error Handling and Progress Updates (~1-2 hours)
Add proper error handling and real progress tracking.

- [ ] Parse pipeline stdout for progress updates
- [ ] Map pipeline errors to user-friendly messages
- [ ] Handle GPU OOM errors gracefully
- [ ] Add timeout for long-running jobs
- [ ] Create Stage 3.5 verification tests

### Stage 3.6: End-to-End Testing (~1-2 hours)
Full integration testing with real MRI data.

- [ ] Test with NIfTI input
- [ ] Test with DICOM input (if available)
- [ ] Verify output files are correct
- [ ] Test error scenarios
- [ ] Performance benchmarking
- [ ] Create comprehensive test documentation

---

## 3. Dependencies & Libraries

### 3.1 Pipeline Requirements

The pipeline requires these Python packages:

```txt
# Deep Learning
torch>=2.0.0
torchvision
nnunetv2

# Medical Imaging
SimpleITK
dosma  # bone_seg branch from github.com/gattia/DOSMA

# Shape Modeling
nsm  # from github.com/gattia/nsm
mskt  # pymskt for mesh processing

# Visualization & Mesh
vtk

# Utilities
numpy==1.24.3  # Specific version for TensorFlow compatibility
huggingface-hub
```

### 3.2 Known Compatibility Issues

| Package | Requirement | Notes |
|---------|-------------|-------|
| NumPy | 1.24.x | TensorFlow 2.11 requires NumPy < 2.0 |
| TensorFlow | 2.11 | Required for DOSMA `.h5` model loading |
| Keras | < 3.0 | Needed to avoid `groups` argument errors |
| PyTorch | 2.x | Works with NumPy 1.24.x |

---

## 4. Model Weights

### 4.1 Required Models

| Model | Source | Size | Purpose |
|-------|--------|------|---------|
| nnU-Net Fullres | HuggingFace (`gattia/nnunet_knee_inference`) | ~800MB | Primary segmentation |
| nnU-Net Cascade | HuggingFace (`gattia/nnunet_knee_inference`) | ~1.6GB | Alternative segmentation |
| DOSMA Weights | HuggingFace (`aagatti/dosma_bones`) | ~200MB | Sagittal/Coronal/Axial models |
| NSM Models | HuggingFace (`aagatti/ShapeMedKnee`) | ~500MB | Neural Shape Model |

### 4.2 BScore Models (Included)

BScore models are already included in the kneepipeline repository:
```
/home/gattia/programming/kneepipeline/BSCORE_MODELS/
├── NSM_Orig_BScore_Bone_Cartilage_April_17_2025/
└── NSM_Orig_BScore_Bone_Only_April_18_2025/
```

---

## 5. Step-by-Step Guides

Each stage has a detailed implementation guide:

| Step | Document | Description |
|------|----------|-------------|
| 3.1 | [STAGE_3.1_PIPELINE_DEPENDENCIES.md](stage_3/STAGE_3.1_PIPELINE_DEPENDENCIES.md) | Install all pipeline dependencies |
| 3.2 | [STAGE_3.2_MODEL_DOWNLOAD.md](stage_3/STAGE_3.2_MODEL_DOWNLOAD.md) | Download models and configure paths |
| 3.3 | [STAGE_3.3_PIPELINE_WORKER.md](stage_3/STAGE_3.3_PIPELINE_WORKER.md) | Integrate real pipeline into web app |
| 3.4 | [STAGE_3.4_CONFIG_MAPPING.md](stage_3/STAGE_3.4_CONFIG_MAPPING.md) | Map web options to pipeline config |
| 3.5 | [STAGE_3.5_ERROR_HANDLING.md](stage_3/STAGE_3.5_ERROR_HANDLING.md) | Error handling and progress updates |
| 3.6 | [STAGE_3.6_INTEGRATION_TESTING.md](stage_3/STAGE_3.6_INTEGRATION_TESTING.md) | End-to-end testing |

---

## 6. Success Criteria

### Functional Requirements

- [ ] Real segmentation produces valid NIfTI/NRRD output files
- [ ] 3D meshes are viewable in ParaView/3D Slicer
- [ ] Thickness measurements are computed for all regions
- [ ] BScore is computed from NSM latent vector
- [ ] All segmentation models work (nnU-Net fullres, cascade, DOSMA variants)
- [ ] NSM analysis works (bone+cart, bone only, or both)

### Performance Requirements

- [ ] Processing time: 5-10 minutes for typical MRI
- [ ] GPU memory stable across multiple jobs
- [ ] No memory leaks after 10+ consecutive jobs
- [ ] Errors handled gracefully with user-friendly messages

### Integration Requirements

- [ ] Web upload → real pipeline → download works end-to-end
- [ ] Progress updates show real pipeline progress
- [ ] Job status accurately reflects pipeline state
- [ ] Results zip contains all expected output files

---

## 7. Task Checklist

### Stage 3.1: Pipeline Dependencies
- [ ] Install PyTorch with CUDA
- [ ] Clone and install NSM library
- [ ] Clone and install DOSMA (bone_seg branch)
- [ ] Initialize and install nnunet_knee_inference
- [ ] Install remaining dependencies
- [ ] Fix NumPy/TensorFlow compatibility
- [ ] Verify all imports

### Stage 3.2: Model Download
- [ ] Download nnU-Net models
- [ ] Download DOSMA weights
- [ ] Download NSM models
- [ ] Create config.json with paths
- [ ] Test pipeline manually

### Stage 3.3: Pipeline Worker
- [ ] Create pipeline_worker.py
- [ ] Create config_generator.py
- [ ] Update tasks.py
- [ ] Add GPU memory cleanup
- [ ] Add timeout handling
- [ ] Write tests

### Stage 3.4: Configuration Mapping
- [ ] Map segmentation models
- [ ] Map NSM options
- [ ] Validate configuration
- [ ] Write tests

### Stage 3.5: Error Handling
- [ ] Parse progress from stdout
- [ ] Map errors to messages
- [ ] Handle GPU OOM
- [ ] Add job timeout
- [ ] Write tests

### Stage 3.6: Integration Testing
- [ ] Test NIfTI input
- [ ] Test DICOM input
- [ ] Verify outputs
- [ ] Test errors
- [ ] Performance benchmark

---

## Development Commands Reference

```bash
# Activate environment
conda activate kneepipeline
cd ~/programming/kneepipeline_segmentaton_website

# Start Redis
make redis-start

# Start FastAPI server
make run

# Start Celery worker
make worker

# Run Stage 3 tests
pytest -m stage_3 -v

# Test pipeline manually
cd ~/programming/kneepipeline
python dosma_knee_seg.py /path/to/test.nii.gz /path/to/output/ nnunet_knee
```

---

## Next Steps After Stage 3

Once Stage 3 is complete:

1. **Performance Optimization**: Profile and optimize slow steps
2. **Horizontal Scaling**: Add support for multiple GPU workers
3. **3D Preview**: Add WebGL mesh preview in browser
4. **Email Notifications**: Send download links via email
5. **S3 Integration**: Move result storage to S3

---

## References

- [PROJECT_OVERVIEW.md](./PROJECT_OVERVIEW.md) - Full architecture details
- [kneepipeline README](https://github.com/gattia/kneepipeline) - Pipeline documentation
- [nnunet_knee_inference](https://github.com/gattia/nnunet_knee_inference) - nnU-Net inference package
- [GCP GPU Driver Installation](https://docs.cloud.google.com/compute/docs/gpus/install-drivers-gpu#verify-linux)


