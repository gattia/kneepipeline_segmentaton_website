# Stage 3.1: Pipeline Dependencies Installation

## Overview

**Goal**: Install all Python dependencies required for the real knee MRI segmentation pipeline.

**Estimated Time**: ~1-2 hours

**Deliverable**: All pipeline libraries installed and importable in the `kneepipeline` conda environment.

---

## Prerequisites

**GPU environment must be ready.** Verify by running:

```bash
# Verify GPU is accessible
nvidia-smi

# Should show Tesla T4 with ~15GB memory
# Driver Version: 580.x or higher
# CUDA Version: 12.0 or higher

# Verify conda environment exists
conda activate kneepipeline
python --version  # Should be Python 3.10.x
```

---

## What This Stage Creates

### Environment Changes

- PyTorch with CUDA support installed
- NSM library installed from GitHub
- DOSMA library installed from GitHub (bone_seg branch)
- nnU-Net v2 installed
- Supporting libraries (VTK, pymskt, etc.)
- NumPy pinned to 1.26.x for TensorFlow/nnU-Net compatibility

### No New Files

This stage only installs dependencies; no new code files are created.

---

## Success Criteria

- [x] `python -c "import torch; print(torch.cuda.is_available())"` returns `True`
- [x] `python -c "import NSM; print('NSM OK')"` works (note: capital letters)
- [x] `python -c "from dosma.models import OAIUnet2D; print('DOSMA OK')"` works
- [x] `python -c "from nnunetv2.inference.predict_from_raw_data import nnUNetPredictor; print('nnU-Net OK')"` works
- [x] `python -c "import vtk; print('VTK OK')"` works
- [x] `python -c "import pymskt; print('pymskt OK')"` works (note: pymskt not mskt)
- [x] NumPy version is 1.26.x (works with both TF 2.11 and nnU-Net)

---

## Detailed Implementation

### Step 1: Activate Environment and Navigate to Dependencies Directory

```bash
conda activate kneepipeline
cd ~/programming/kneepipeline/DEPENDENCIES
```

### Step 2: Install PyTorch with CUDA Support

```bash
# Install PyTorch with CUDA 12.1 support
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121

# Verify CUDA is available
python -c "import torch; print(f'PyTorch: {torch.__version__}'); print(f'CUDA available: {torch.cuda.is_available()}'); print(f'CUDA device: {torch.cuda.get_device_name(0) if torch.cuda.is_available() else \"N/A\"}')"
```

**Expected output:**
```
PyTorch: 2.x.x+cu121
CUDA available: True
CUDA device: Tesla T4
```

### Step 3: Install NSM Library

```bash
cd ~/programming/kneepipeline/DEPENDENCIES

# Clone NSM repository (if not already cloned)
if [ ! -d "nsm" ]; then
    git clone https://github.com/gattia/nsm
fi

cd nsm

# Install NSM requirements and package
pip install -r requirements.txt
pip install .

# Verify NSM installation
python -c "from nsm import NSM; print('NSM installed successfully')"
```

### Step 4: Install DOSMA Library

```bash
cd ~/programming/kneepipeline/DEPENDENCIES

# Clone DOSMA repository (if not already cloned)
if [ ! -d "DOSMA" ]; then
    git clone https://github.com/gattia/DOSMA
fi

cd DOSMA

# Switch to bone_seg branch
git checkout bone_seg

# Install DOSMA with AI dependencies
pip install '.[ai]'

# Verify DOSMA installation
python -c "from dosma.models import OAIUnet2D; print('DOSMA installed successfully')"
```

### Step 5: Initialize and Install nnU-Net Inference Package

```bash
cd ~/programming/kneepipeline

# Initialize git submodule for nnunet_knee_inference
git submodule update --init --recursive

# If submodule is empty, clone directly
if [ ! -f "DEPENDENCIES/nnunet_knee_inference/requirements.txt" ]; then
    cd DEPENDENCIES
    rm -rf nnunet_knee_inference
    git clone https://github.com/gattia/nnunet_knee_inference
    cd ..
fi

# Install nnU-Net inference dependencies
cd ~/programming/kneepipeline/DEPENDENCIES/nnunet_knee_inference
pip install -r requirements.txt

# Verify nnU-Net installation
python -c "from nnunetv2.inference.predict_from_raw_data import nnUNetPredictor; print('nnU-Net installed successfully')"
```

### Step 6: Install Supporting Libraries

```bash
# Install pymskt for mesh processing
pip install mskt

# Install VTK for mesh visualization
pip install vtk

# Install HuggingFace Hub for model downloads
pip install huggingface-hub

# Verify installations
python -c "import mskt; print('pymskt OK')"
python -c "import vtk; print('VTK OK')"
python -c "from huggingface_hub import snapshot_download; print('HuggingFace Hub OK')"
```

### Step 7: Fix NumPy/TensorFlow Compatibility

The pipeline requires TensorFlow 2.11 for DOSMA models, which needs NumPy < 2.0:

```bash
# Install compatible TensorFlow and Keras versions
pip install tensorflow==2.11
pip install "keras<3"

# Pin NumPy to compatible version (1.26.x works with both TF 2.11 and nnU-Net)
pip install "numpy>=1.26,<2"

# Verify compatibility
python -c "
import numpy
import torch
import tensorflow
print(f'NumPy: {numpy.__version__}')
print(f'PyTorch: {torch.__version__}')
print(f'TensorFlow: {tensorflow.__version__}')
print(f'CUDA available: {torch.cuda.is_available()}')
"
```

**Expected output:**
```
NumPy: 1.26.4
PyTorch: 2.5.1+cu121
TensorFlow: 2.11.0
CUDA available: True
```

### Step 8: Verify All Imports

Run this comprehensive verification script:

```bash
python << 'EOF'
print("=" * 60)
print("Stage 3.1 Verification: Pipeline Dependencies")
print("=" * 60)

errors = []

# Check PyTorch with CUDA
try:
    import torch
    if not torch.cuda.is_available():
        errors.append("PyTorch CUDA not available")
    else:
        print(f"✓ PyTorch {torch.__version__} with CUDA ({torch.cuda.get_device_name(0)})")
except Exception as e:
    errors.append(f"PyTorch: {e}")

# Check NSM
try:
    from nsm import NSM
    print("✓ NSM library")
except Exception as e:
    errors.append(f"NSM: {e}")

# Check DOSMA
try:
    from dosma.models import OAIUnet2D
    print("✓ DOSMA library")
except Exception as e:
    errors.append(f"DOSMA: {e}")

# Check nnU-Net
try:
    from nnunetv2.inference.predict_from_raw_data import nnUNetPredictor
    print("✓ nnU-Net v2")
except Exception as e:
    errors.append(f"nnU-Net: {e}")

# Check VTK
try:
    import vtk
    print(f"✓ VTK {vtk.vtkVersion.GetVTKVersion()}")
except Exception as e:
    errors.append(f"VTK: {e}")

# Check pymskt
try:
    import mskt
    print("✓ pymskt")
except Exception as e:
    errors.append(f"pymskt: {e}")

# Check SimpleITK
try:
    import SimpleITK as sitk
    print(f"✓ SimpleITK {sitk.Version()}")
except Exception as e:
    errors.append(f"SimpleITK: {e}")

# Check NumPy version
try:
    import numpy as np
    version = np.__version__
    if version.startswith("1.24"):
        print(f"✓ NumPy {version} (compatible)")
    else:
        errors.append(f"NumPy version {version} may cause issues (need 1.24.x)")
except Exception as e:
    errors.append(f"NumPy: {e}")

# Check TensorFlow
try:
    import tensorflow as tf
    print(f"✓ TensorFlow {tf.__version__}")
except Exception as e:
    errors.append(f"TensorFlow: {e}")

# Summary
print("=" * 60)
if errors:
    print(f"FAILED: {len(errors)} error(s)")
    for err in errors:
        print(f"  ✗ {err}")
else:
    print("SUCCESS: All dependencies installed correctly!")
print("=" * 60)
EOF
```

---

## Troubleshooting

### PyTorch CUDA Not Available

```bash
# Check if NVIDIA driver is loaded
nvidia-smi

# Reinstall PyTorch with correct CUDA version
pip uninstall torch torchvision torchaudio
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
```

### TensorFlow NumPy Compatibility Error

If you see:
```
A module that was compiled using NumPy 1.x cannot be run in NumPy 2.x
```

Fix:
```bash
pip install numpy==1.24.3
```

### DOSMA Import Error

If DOSMA fails to import:
```bash
cd ~/programming/kneepipeline/DEPENDENCIES/DOSMA
git checkout bone_seg
pip install '.[ai]' --force-reinstall
```

### Keras Groups Error

If you see:
```
ValueError: Unrecognized keyword arguments passed to Conv2DTranspose: {'groups': 1}
```

Fix:
```bash
pip install "keras<3"
```

### nnU-Net Submodule Empty

```bash
cd ~/programming/kneepipeline/DEPENDENCIES
rm -rf nnunet_knee_inference
git clone https://github.com/gattia/nnunet_knee_inference
cd nnunet_knee_inference
pip install -r requirements.txt
```

---

## Expected Final State

After completing Stage 3.1:

1. All pipeline dependencies are installed in the `kneepipeline` conda environment
2. PyTorch has CUDA support and can access the T4 GPU
3. NSM, DOSMA, and nnU-Net are all importable
4. NumPy is pinned to 1.26.x for TensorFlow/nnU-Net compatibility

> **✅ COMPLETED**: See [STAGE_3.1_COMPLETED.md](./STAGE_3.1_COMPLETED.md) for full completion report.

---

## Verification Commands

```bash
conda activate kneepipeline
cd ~/programming/kneepipeline_segmentaton_website

# Quick verification
python -c "import torch; print(f'CUDA: {torch.cuda.is_available()}')"
python -c "import NSM; print('NSM OK')"
python -c "from dosma.models import OAIUnet2D; print('DOSMA OK')"
python -c "from nnunetv2.inference.predict_from_raw_data import nnUNetPredictor; print('nnU-Net OK')"
python -c "import numpy; print(f'NumPy: {numpy.__version__}')"
```

---

## Git Commit

After completing Stage 3.1:

```bash
# No code changes, but update requirements if needed
git add .
git commit -m "Stage 3.1: Install pipeline dependencies

- Install PyTorch with CUDA 12.1 support
- Install NSM library from GitHub
- Install DOSMA library (bone_seg branch)
- Initialize and install nnunet_knee_inference submodule
- Install supporting libraries (VTK, pymskt, huggingface-hub)
- Pin NumPy to 1.24.3 for TensorFlow 2.11 compatibility
- All pipeline dependencies verified and working
"
```

---

## Next Step: Stage 3.2 - Model Download

See [STAGE_3.2_MODEL_DOWNLOAD.md](./STAGE_3.2_MODEL_DOWNLOAD.md)

Stage 3.2 downloads the trained model weights:
1. nnU-Net segmentation models
2. DOSMA segmentation weights
3. NSM shape models
4. Creates config.json with correct paths


