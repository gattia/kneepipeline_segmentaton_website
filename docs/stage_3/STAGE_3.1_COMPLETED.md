# Stage 3.1 Completed: Pipeline Dependencies Installation

**Completed**: December 17, 2025

---

## Summary

Successfully installed all Python dependencies required for the real knee MRI segmentation pipeline in the `kneepipeline` conda environment.

---

## What Was Done

### 1. Disk Space Setup

The 10GB root disk was insufficient for the large ML dependencies. We:

- Formatted and mounted `/dev/sdb` (100GB) to `/mnt/data`
- Moved `~/miniconda3` → `/mnt/data/miniconda3` (symlinked back)
- Moved `~/programming` → `/mnt/data/programming` (symlinked back)
- Set `TMPDIR=/mnt/data/tmp` for pip downloads
- Added mount to `/etc/fstab` for persistence across reboots

### 2. Dependencies Installed

| Package | Version | Notes |
|---------|---------|-------|
| **PyTorch** | 2.5.1+cu121 | With CUDA support for Tesla T4 |
| **NSM** | 0.0.1 | From GitHub (gattia/nsm) |
| **DOSMA** | 0.1.2 | bone_seg branch from GitHub |
| **nnU-Net v2** | Latest | Installed via pip |
| **VTK** | 9.5.2 | Required libxrender1 system library |
| **pymskt** | Latest | Mesh processing |
| **SimpleITK** | 2.3.1 | Medical image I/O |
| **TensorFlow** | 2.11.0 | Required for DOSMA .h5 models |
| **Keras** | 2.11.0 | < 3.0 to avoid groups argument error |
| **NumPy** | 1.26.4 | Compatible with both TF 2.11 and nnU-Net |
| **HuggingFace Hub** | Latest | For model downloads |

### 3. System Libraries Installed

```bash
sudo apt-get install -y libxrender1 libgl1-mesa-glx libxcursor1
```

Required for VTK's OpenGL rendering.

---

## Verification Results

All dependencies import successfully:

```
============================================================
Stage 3.1 Verification: Pipeline Dependencies
============================================================
NumPy: 1.26.4
TensorFlow: 2.11.0
Keras: 2.11.0
------------------------------------------------------------
✓ PyTorch 2.5.1+cu121 with CUDA (Tesla T4)
✓ NSM library
✓ DOSMA library
✓ nnU-Net v2
✓ VTK 9.5.2
✓ pymskt
✓ SimpleITK 2.3.1
✓ HuggingFace Hub
============================================================
SUCCESS: All dependencies installed correctly!
============================================================
```

---

## Key Findings / Deviations from Plan

### NumPy Version Change

The original plan specified NumPy 1.24.x, but we used **NumPy 1.26.4** because:

- nnU-Net requires `numpy.exceptions` (added in NumPy 1.25)
- NumPy 1.26.4 works with both TensorFlow 2.11 and nnU-Net
- The blosc2 warning about needing NumPy >= 1.26 is informational only

### TensorFlow Version

Used TensorFlow 2.11.0 (not newer versions) as specified in the kneepipeline README to ensure compatibility with DOSMA .h5 model loading.

### Expected Warnings (Safe to Ignore)

1. **TensorRT warnings**: `Could not load dynamic library 'libnvinfer.so.7'` - Optional GPU optimization, not needed
2. **nnU-Net path warnings**: `nnUNet_raw is not defined...` - Paths will be configured in Stage 3.2
3. **schedulefree warning**: `schedulefree not found, skipping import` - Optional NSM dependency

---

## Directory Structure After Stage 3.1

```
/mnt/data/
├── miniconda3/                 # Conda installation (symlinked from ~/)
│   └── envs/kneepipeline/      # All dependencies installed here
├── programming/                # Code (symlinked from ~/)
│   └── kneepipeline/
│       └── DEPENDENCIES/
│           ├── nsm/            # NSM library source
│           ├── DOSMA/          # DOSMA library source (bone_seg branch)
│           └── nnunet_knee_inference/  # nnU-Net inference code
└── tmp/                        # Temporary directory for pip

/etc/fstab entry:
/dev/sdb /mnt/data ext4 defaults 0 2
```

---

## Verification Commands

```bash
# Activate environment
source ~/miniconda3/etc/profile.d/conda.sh
conda activate kneepipeline

# Quick verification
python -c "import torch; print(f'CUDA: {torch.cuda.is_available()}')"
python -c "import NSM; print('NSM OK')"
python -c "from dosma.models import OAIUnet2D; print('DOSMA OK')"
python -c "from nnunetv2.inference.predict_from_raw_data import nnUNetPredictor; print('nnU-Net OK')"
python -c "import numpy; print(f'NumPy: {numpy.__version__}')"
python -c "import tensorflow; print(f'TensorFlow: {tensorflow.__version__}')"
```

---

## Next Step

**Stage 3.2: Model Download and Configuration**

See [STAGE_3.2_MODEL_DOWNLOAD.md](./STAGE_3.2_MODEL_DOWNLOAD.md)

This stage will:
1. Download nnU-Net models from HuggingFace
2. Download DOSMA weights from HuggingFace
3. Download NSM models from HuggingFace
4. Create `config.json` with correct paths
5. Test pipeline manually with test image

