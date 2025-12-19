# Model Weights Reference

This document is the canonical reference for all model weights used by the knee MRI segmentation pipeline.

---

## Quick Reference

| Model Type | HuggingFace Repo | Local Directory | Purpose |
|------------|------------------|-----------------|---------|
| nnU-Net | `aagatti/nnunet_knee` | `DEPENDENCIES/nnunet_knee_inference/huggingface/` | Primary segmentation |
| DOSMA | `aagatti/dosma_bones` | `DOSMA_WEIGHTS/` | Alternative segmentation |
| NSM | `aagatti/ShapeMedKnee` | `NSM_MODELS/` | Neural Shape Models |
| BScore | (included in repo) | `BSCORE_MODELS/` | BScore computation |

**Base Path**: `~/programming/kneepipeline/` (or `KNEEPIPELINE_PATH` env var)

---

## Current Model Versions

### Segmentation Models

| Model Name | File/Folder | Size | Notes |
|------------|-------------|------|-------|
| Goyal 2024 Sagittal 2D UNet | `DOSMA_WEIGHTS/Goyal_Bone_Cart_July_2024_best_model.h5` | 324MB | **Default, recommended** |
| nnU-Net Fullres | `DEPENDENCIES/nnunet_knee_inference/huggingface/models/Dataset500_KneeMRI/` | ~800MB | Alternative |
| nnU-Net Cascade | Same as above | ~1.6GB | Higher quality, slower |
| Sagittal 2D UNet | `DOSMA_WEIGHTS/sagittal_best_model.h5` | 324MB | Sagittal plane only |
| Coronal 2D UNet | `DOSMA_WEIGHTS/coronal_best_model.h5` | 165MB | Coronal plane only |
| Axial 2D UNet | `DOSMA_WEIGHTS/axial_best_model.h5` | 165MB | Axial plane only |

> **Note**: STAPLE (combining multiple orientation models) is available in the code but not recommended for production use.

### NSM Models (Neural Shape Models)

| Model Name | Folder | Purpose | Config Key |
|------------|--------|---------|------------|
| Bone + Cartilage | `NSM_MODELS/647_nsm_femur_v0.0.1/` | Full femur with cartilage | `nsm` |
| Bone Only | `NSM_MODELS/551_nsm_femur_bone_v0.0.1/` | Femur bone only | `nsm_bone_only` |

**NSM Model Files:**
```
647_nsm_femur_v0.0.1/
├── model_params_config.json    # Model configuration
└── model/
    └── 2000.pth                # Model weights (epoch 2000)

551_nsm_femur_bone_v0.0.1/
├── model_params_config.json    # Model configuration
└── model/
    └── 1150.pth                # Model weights (epoch 1150)
```

### BScore Models

| Model Name | Folder | Purpose |
|------------|--------|---------|
| Bone + Cartilage | `BSCORE_MODELS/NSM_Orig_BScore_Bone_Cartilage_April_17_2025/` | BScore for bone+cart NSM |
| Bone Only | `BSCORE_MODELS/NSM_Orig_BScore_Bone_Only_April_18_2025/` | BScore for bone-only NSM |

---

## Expected Directory Structure

After downloading all models:

```
~/programming/kneepipeline/
├── config.json                              # Pipeline configuration
├── DEPENDENCIES/
│   └── nnunet_knee_inference/
│       └── huggingface/
│           ├── models/
│           │   └── Dataset500_KneeMRI/
│           │       ├── nnUNetTrainer__nnUNetResEncUNetMPlans__3d_fullres/
│           │       ├── nnUNetTrainer__nnUNetResEncUNetMPlans__3d_cascade_fullres/
│           │       └── nnUNetTrainer__nnUNetResEncUNetMPlans__3d_lowres/
│           └── test_data/
├── DOSMA_WEIGHTS/
│   ├── Goyal_Bone_Cart_July_2024_best_model.h5
│   ├── sagittal_best_model.h5
│   ├── coronal_best_model.h5
│   └── axial_best_model.h5
├── NSM_MODELS/
│   ├── 647_nsm_femur_v0.0.1/
│   │   ├── model_params_config.json
│   │   └── model/2000.pth
│   └── 551_nsm_femur_bone_v0.0.1/
│       ├── model_params_config.json
│       └── model/1150.pth
└── BSCORE_MODELS/
    ├── NSM_Orig_BScore_Bone_Cartilage_April_17_2025/
    └── NSM_Orig_BScore_Bone_Only_April_18_2025/
```

---

## config.json Reference

The `config.json` file in `~/programming/kneepipeline/` must have correct paths to all models:

```json
{
  "perform_bone_only_nsm": true,
  "perform_bone_and_cart_nsm": true,
  "clip_femur_top": true,
  "default_seg_model": "acl_qdess_bone_july_2024",
  "batch_size": 64,
  "models": {
    "acl_qdess_bone_july_2024": "/mnt/data/programming/kneepipeline/DOSMA_WEIGHTS/Goyal_Bone_Cart_July_2024_best_model.h5",
    "goyal_sagittal": "/mnt/data/programming/kneepipeline/DOSMA_WEIGHTS/sagittal_best_model.h5",
    "goyal_coronal": "/mnt/data/programming/kneepipeline/DOSMA_WEIGHTS/coronal_best_model.h5",
    "goyal_axial": "/mnt/data/programming/kneepipeline/DOSMA_WEIGHTS/axial_best_model.h5"
  },
  "nnunet": {
    "type": "fullres",
    "model_name": "Dataset500_KneeMRI"
  },
  "nsm": {
    "path_model_config": "/mnt/data/programming/kneepipeline/NSM_MODELS/647_nsm_femur_v0.0.1/model_params_config.json",
    "path_model_state": "/mnt/data/programming/kneepipeline/NSM_MODELS/647_nsm_femur_v0.0.1/model/2000.pth"
  },
  "bscore": {
    "path_model_folder": "/mnt/data/programming/kneepipeline/BSCORE_MODELS/NSM_Orig_BScore_Bone_Cartilage_April_17_2025"
  },
  "nsm_bone_only": {
    "path_model_config": "/mnt/data/programming/kneepipeline/NSM_MODELS/551_nsm_femur_bone_v0.0.1/model_params_config.json",
    "path_model_state": "/mnt/data/programming/kneepipeline/NSM_MODELS/551_nsm_femur_bone_v0.0.1/model/1150.pth"
  },
  "bscore_bone_only": {
    "path_model_folder": "/mnt/data/programming/kneepipeline/BSCORE_MODELS/NSM_Orig_BScore_Bone_Only_April_18_2025"
  }
}
```

> **Note**: Paths use `/mnt/data/programming/kneepipeline/` because `~/programming` is a symlink to `/mnt/data/programming` on the production server.

---

## Downloading Models

### Prerequisites

```bash
pip install huggingface_hub
huggingface-cli login  # For gated repos like ShapeMedKnee
```

### Download Commands

```bash
cd ~/programming/kneepipeline

# 1. nnU-Net models
cd DEPENDENCIES/nnunet_knee_inference
python download_models.py
cd ../..

# 2. DOSMA models
python -c "from huggingface_hub import snapshot_download; snapshot_download('aagatti/dosma_bones', local_dir='./DOSMA_WEIGHTS')"

# 3. NSM models (requires authentication)
python download_nsm_models.py --token YOUR_HF_TOKEN
# Or: python -c "from huggingface_hub import snapshot_download, login; login(); snapshot_download('aagatti/ShapeMedKnee', local_dir='./NSM_MODELS')"
```

### Verification

```bash
# Check all model paths exist
echo "=== Checking Model Paths ===" && \
test -d ~/programming/kneepipeline/DEPENDENCIES/nnunet_knee_inference/huggingface/models && echo "✓ nnunet models" || echo "✗ nnunet models" && \
test -f ~/programming/kneepipeline/DOSMA_WEIGHTS/Goyal_Bone_Cart_July_2024_best_model.h5 && echo "✓ dosma_ananya" || echo "✗ dosma_ananya" && \
test -f ~/programming/kneepipeline/DOSMA_WEIGHTS/sagittal_best_model.h5 && echo "✓ goyal_sagittal" || echo "✗ goyal_sagittal" && \
test -f ~/programming/kneepipeline/DOSMA_WEIGHTS/coronal_best_model.h5 && echo "✓ goyal_coronal" || echo "✗ goyal_coronal" && \
test -f ~/programming/kneepipeline/DOSMA_WEIGHTS/axial_best_model.h5 && echo "✓ goyal_axial" || echo "✗ goyal_axial" && \
test -f ~/programming/kneepipeline/NSM_MODELS/647_nsm_femur_v0.0.1/model/2000.pth && echo "✓ NSM bone+cart (647)" || echo "✗ NSM bone+cart (647)" && \
test -f ~/programming/kneepipeline/NSM_MODELS/551_nsm_femur_bone_v0.0.1/model/1150.pth && echo "✓ NSM bone only (551)" || echo "✗ NSM bone only (551)" && \
test -d ~/programming/kneepipeline/BSCORE_MODELS/NSM_Orig_BScore_Bone_Cartilage_April_17_2025 && echo "✓ BScore bone+cart" || echo "✗ BScore bone+cart" && \
test -d ~/programming/kneepipeline/BSCORE_MODELS/NSM_Orig_BScore_Bone_Only_April_18_2025 && echo "✓ BScore bone only" || echo "✗ BScore bone only"
```

---

## Updating Models on HuggingFace

When you train new models and need to update the HuggingFace repos:

### Prerequisites

1. Create a **write-enabled** HuggingFace token at https://huggingface.co/settings/tokens
2. Install Git LFS: `git lfs install`

### Push New Models

```bash
# Install/login
pip install huggingface_hub
huggingface-cli login  # Use write-enabled token

# Example: Add new NSM model to ShapeMedKnee
cd /tmp
git clone https://huggingface.co/aagatti/ShapeMedKnee
cd ShapeMedKnee

# Copy new model folder
cp -r /path/to/new_model_folder .

# Ensure LFS tracks large files
git lfs track "*.pth"
git lfs track "*.h5"
git add .gitattributes

# Commit and push
git add .
git commit -m "Add new_model_folder"
git push

# Cleanup
cd /tmp && rm -rf ShapeMedKnee
```

### Troubleshooting Push Errors

**"You have read access but not the required permissions"**
- Your token only has read access. Create a new token with **write** permission.

**Large file errors**
- Ensure Git LFS is installed and tracking the file type
- Run `git lfs ls-files` to verify files are tracked

---

## Model Availability in Web UI

The web application checks which models have weights downloaded before showing them in the UI.

**Configuration**: `backend/services/config_generator.py`

```python
MODEL_WEIGHT_PATHS = {
    "nnunet_fullres": KNEEPIPELINE_PATH / "DEPENDENCIES" / "nnunet_knee_inference" / "huggingface" / "models",
    "nnunet_cascade": KNEEPIPELINE_PATH / "DEPENDENCIES" / "nnunet_knee_inference" / "huggingface" / "models",
    "dosma_ananya": KNEEPIPELINE_PATH / "DOSMA_WEIGHTS" / "Goyal_Bone_Cart_July_2024_best_model.h5",
    "goyal_sagittal": KNEEPIPELINE_PATH / "DOSMA_WEIGHTS" / "sagittal_best_model.h5",
    "goyal_coronal": KNEEPIPELINE_PATH / "DOSMA_WEIGHTS" / "coronal_best_model.h5",
    "goyal_axial": KNEEPIPELINE_PATH / "DOSMA_WEIGHTS" / "axial_best_model.h5",
    "staple": KNEEPIPELINE_PATH / "DOSMA_WEIGHTS" / "sagittal_best_model.h5",
}
```

For Docker deployments, set `AVAILABLE_MODELS` env var in `docker/docker-compose.yml`:

```yaml
environment:
  - AVAILABLE_MODELS=nnunet_fullres,nnunet_cascade,dosma_ananya,goyal_sagittal,goyal_coronal,goyal_axial,staple
```

---

## Changelog

| Date | Change |
|------|--------|
| 2025-12-19 | Updated NSM to 647_nsm_femur_v0.0.1, added 551_nsm_femur_bone_v0.0.1, added DOSMA orientation models |
| 2025-12-18 | Initial setup with 231_nsm_femur_cartilage_v0.0.1 (now deprecated) |
