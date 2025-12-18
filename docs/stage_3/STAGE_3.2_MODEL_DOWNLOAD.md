# Stage 3.2: Model Download and Configuration

## Overview

**Goal**: Download all trained model weights and create the pipeline configuration file.

**Estimated Time**: ~30 minutes - 1 hour (depending on download speed)

**Deliverable**: All model weights downloaded and `config.json` created with correct paths.

---

## Prerequisites

**Stage 3.1 must be complete.** Verify by running:

```bash
conda activate kneepipeline

# All dependencies should be importable
python -c "import torch; from nsm import NSM; from dosma.models import OAIUnet2D; print('OK')"
python -c "from huggingface_hub import snapshot_download; print('HuggingFace Hub OK')"
```

---

## What This Stage Creates

### Downloaded Files

```
~/programming/kneepipeline/
├── NNUNET_MODELS/               # NEW: nnU-Net model weights
│   └── huggingface/
│       ├── Dataset500_KneeMRI/
│       └── test_data/
├── DOSMA_WEIGHTS/               # NEW: DOSMA segmentation weights
│   ├── sagittal_best_model.h5
│   ├── coronal_best_model.h5
│   └── axial_best_model.h5
├── NSM_MODELS/                  # NEW: Neural Shape Model weights
│   ├── 647_nsm_femur_cartilage_v0.0.1/
│   └── 551_nsm_femur_bone_v0.0.1/
└── config.json                  # NEW: Configuration with paths
```

---

## Success Criteria

- [ ] nnU-Net models downloaded to `NNUNET_MODELS/`
- [ ] DOSMA weights downloaded to `DOSMA_WEIGHTS/`
- [ ] NSM models downloaded to `NSM_MODELS/`
- [ ] `config.json` created with correct absolute paths
- [ ] Pipeline runs successfully with test image

---

## Detailed Implementation

### Step 1: Set Up HuggingFace Authentication (Optional)

Some models may require HuggingFace authentication. Set up if needed:

```bash
# Install HuggingFace CLI if not already installed
pip install huggingface-hub

# Login to HuggingFace (optional, only if models are private)
huggingface-cli login
# Enter your access token when prompted
# Get token from: https://huggingface.co/settings/tokens
```

### Step 2: Download nnU-Net Models

```bash
conda activate kneepipeline
cd ~/programming/kneepipeline/DEPENDENCIES/nnunet_knee_inference

# Download models using the provided script
python download_models.py

# This downloads:
# - nnU-Net fullres model (~800MB)
# - nnU-Net cascade model (~1.6GB, optional)
# - Test data for validation
```

Alternatively, download manually:

```python
# Run in Python
from huggingface_hub import snapshot_download

# Download nnU-Net models
snapshot_download(
    repo_id="gattia/nnunet_knee_inference",
    local_dir="./huggingface"
)
```

### Step 3: Download DOSMA Weights

```bash
cd ~/programming/kneepipeline

# Create directory
mkdir -p DOSMA_WEIGHTS

# Download DOSMA weights from HuggingFace
python << 'EOF'
from huggingface_hub import snapshot_download
import os

# Download DOSMA bone segmentation weights
snapshot_download(
    repo_id="aagatti/dosma_bones",
    local_dir="./DOSMA_WEIGHTS"
)

print("DOSMA weights downloaded successfully!")
print("Contents:")
for f in os.listdir("./DOSMA_WEIGHTS"):
    print(f"  - {f}")
EOF
```

**Expected files:**
- `sagittal_best_model.h5`
- `coronal_best_model.h5`
- `axial_best_model.h5`

### Step 4: Download NSM Models

```bash
cd ~/programming/kneepipeline

# Create directory
mkdir -p NSM_MODELS

# Download NSM models from HuggingFace
python << 'EOF'
from huggingface_hub import snapshot_download
import os

# Download NSM models (bone+cartilage and bone-only)
snapshot_download(
    repo_id="aagatti/ShapeMedKnee",
    local_dir="./NSM_MODELS"
)

print("NSM models downloaded successfully!")
print("Contents:")
for root, dirs, files in os.walk("./NSM_MODELS"):
    level = root.replace("./NSM_MODELS", "").count(os.sep)
    indent = " " * 2 * level
    print(f"{indent}{os.path.basename(root)}/")
    subindent = " " * 2 * (level + 1)
    for file in files[:5]:  # Show first 5 files
        print(f"{subindent}{file}")
    if len(files) > 5:
        print(f"{subindent}... and {len(files) - 5} more files")
EOF
```

### Step 5: Verify Downloaded Models

```bash
cd ~/programming/kneepipeline

# Check nnU-Net models
echo "=== nnU-Net Models ==="
ls -la DEPENDENCIES/nnunet_knee_inference/huggingface/Dataset500_KneeMRI/ 2>/dev/null || echo "Not found - check download"

# Check DOSMA weights
echo "=== DOSMA Weights ==="
ls -la DOSMA_WEIGHTS/*.h5 2>/dev/null || echo "Not found - check download"

# Check NSM models
echo "=== NSM Models ==="
ls -la NSM_MODELS/ 2>/dev/null || echo "Not found - check download"

# Check BScore models (should already exist)
echo "=== BScore Models ==="
ls -la BSCORE_MODELS/ 2>/dev/null || echo "Not found"
```

### Step 6: Create config.json

Create the configuration file with absolute paths:

```bash
cd ~/programming/kneepipeline

# Create config.json from template
python << 'EOF'
import json
import os
from pathlib import Path

# Base path
base_path = Path(os.path.expanduser("~/programming/kneepipeline"))

# Load template
with open(base_path / "config_template.json") as f:
    config = json.load(f)

# Update paths with absolute paths
config["models"] = {
    "goyal_sagittal": str(base_path / "DOSMA_WEIGHTS/sagittal_best_model.h5"),
    "goyal_coronal": str(base_path / "DOSMA_WEIGHTS/coronal_best_model.h5"),
    "goyal_axial": str(base_path / "DOSMA_WEIGHTS/axial_best_model.h5"),
}

# NSM bone+cartilage model
config["nsm"] = {
    "path_model_config": str(base_path / "NSM_MODELS/647_nsm_femur_cartilage_v0.0.1/model_config.json"),
    "path_model_state": str(base_path / "NSM_MODELS/647_nsm_femur_cartilage_v0.0.1/model/2000.pth"),
}

# BScore bone+cartilage
config["bscore"] = {
    "path_model_folder": str(base_path / "BSCORE_MODELS/NSM_Orig_BScore_Bone_Cartilage_April_17_2025"),
}

# NSM bone-only model
config["nsm_bone_only"] = {
    "path_model_config": str(base_path / "NSM_MODELS/551_nsm_femur_bone_v0.0.1/model_params_config.json"),
    "path_model_state": str(base_path / "NSM_MODELS/551_nsm_femur_bone_v0.0.1/model/1150.pth"),
}

# BScore bone-only
config["bscore_bone_only"] = {
    "path_model_folder": str(base_path / "BSCORE_MODELS/NSM_Orig_BScore_Bone_Only_April_18_2025"),
}

# nnU-Net configuration
config["nnunet"] = {
    "type": "fullres",  # or "cascade"
    "model_name": "Dataset500_KneeMRI",
}

# Default settings
config["default_seg_model"] = "nnunet_knee"
config["perform_bone_and_cart_nsm"] = True
config["perform_bone_only_nsm"] = False
config["clip_femur_top"] = True
config["batch_size"] = 32

# Save config
with open(base_path / "config.json", "w") as f:
    json.dump(config, f, indent=2)

print("config.json created successfully!")
print(f"Location: {base_path / 'config.json'}")

# Verify paths exist
print("\nVerifying paths...")
paths_to_check = [
    config["models"]["goyal_sagittal"],
    config["nsm"]["path_model_config"],
    config["bscore"]["path_model_folder"],
]
for path in paths_to_check:
    exists = os.path.exists(path)
    status = "✓" if exists else "✗"
    print(f"  {status} {path}")
EOF
```

### Step 7: Test Pipeline Manually

Test the pipeline with a sample image:

```bash
cd ~/programming/kneepipeline

# Use the test image from the website project
TEST_IMAGE=~/programming/kneepipeline_segmentaton_website/test_input.nii.gz
OUTPUT_DIR=/tmp/pipeline_test_output

# Create output directory
mkdir -p $OUTPUT_DIR

# Run pipeline with nnU-Net
echo "Testing pipeline with nnU-Net..."
python dosma_knee_seg.py $TEST_IMAGE $OUTPUT_DIR nnunet_knee

# Check output
echo "=== Output files ==="
ls -la $OUTPUT_DIR/

# Verify key output files exist
echo "=== Verification ==="
if [ -f "$OUTPUT_DIR/segmentation.nii.gz" ] || [ -f "$OUTPUT_DIR/seg.nii.gz" ]; then
    echo "✓ Segmentation file created"
else
    echo "✗ Segmentation file missing"
fi

if ls $OUTPUT_DIR/*.vtk 1> /dev/null 2>&1; then
    echo "✓ Mesh files created"
else
    echo "✗ Mesh files missing"
fi

if [ -f "$OUTPUT_DIR/results.json" ] || [ -f "$OUTPUT_DIR/results.csv" ]; then
    echo "✓ Results files created"
else
    echo "✗ Results files missing"
fi
```

---

## Troubleshooting

### HuggingFace Download Fails

```bash
# Check if you need authentication
huggingface-cli login

# Or download with token
python << 'EOF'
from huggingface_hub import snapshot_download
import os

snapshot_download(
    repo_id="aagatti/dosma_bones",
    local_dir="./DOSMA_WEIGHTS",
    token=os.environ.get("HF_TOKEN")  # Set HF_TOKEN env var
)
EOF
```

### Model Path Not Found

Double-check the actual file names after download:
```bash
find ~/programming/kneepipeline -name "*.h5" -o -name "*.pth" | head -20
```

### Pipeline Fails to Start

```bash
# Check config.json is valid JSON
python -c "import json; json.load(open('config.json')); print('Config OK')"

# Check all paths exist
python << 'EOF'
import json
import os

with open('config.json') as f:
    config = json.load(f)

def check_paths(d, prefix=""):
    for k, v in d.items():
        if isinstance(v, dict):
            check_paths(v, f"{prefix}{k}.")
        elif isinstance(v, str) and ("path" in k.lower() or v.endswith((".h5", ".pth", ".json"))):
            exists = os.path.exists(v)
            print(f"{'✓' if exists else '✗'} {prefix}{k}: {v}")

check_paths(config)
EOF
```

### GPU Memory Error During Test

```bash
# Clear GPU memory
python -c "import torch; torch.cuda.empty_cache()"

# Run with smaller batch size
# Edit config.json and set "batch_size": 16
```

---

## Expected Final State

After completing Stage 3.2:

```
~/programming/kneepipeline/
├── config.json                  # ✓ Created with correct paths
├── DOSMA_WEIGHTS/               # ✓ Downloaded
│   ├── sagittal_best_model.h5
│   ├── coronal_best_model.h5
│   └── axial_best_model.h5
├── NSM_MODELS/                  # ✓ Downloaded
│   ├── 647_nsm_femur_cartilage_v0.0.1/
│   └── 551_nsm_femur_bone_v0.0.1/
├── BSCORE_MODELS/               # ✓ Already included
└── DEPENDENCIES/
    └── nnunet_knee_inference/
        └── huggingface/         # ✓ Downloaded
            └── Dataset500_KneeMRI/
```

---

## Verification Commands

```bash
conda activate kneepipeline
cd ~/programming/kneepipeline

# Verify config exists and is valid
python -c "import json; c = json.load(open('config.json')); print(f'Default model: {c[\"default_seg_model\"]}')"

# Verify model files exist
ls -la DOSMA_WEIGHTS/*.h5 | head -3
ls -la NSM_MODELS/
ls -la DEPENDENCIES/nnunet_knee_inference/huggingface/

# Quick pipeline test (if test image available)
# python dosma_knee_seg.py /path/to/test.nii.gz /tmp/test_output nnunet_knee
```

---

## Git Commit

After completing Stage 3.2:

```bash
cd ~/programming/kneepipeline
git add config.json
git commit -m "Stage 3.2: Create config.json with model paths

- Download nnU-Net models from HuggingFace
- Download DOSMA weights from HuggingFace  
- Download NSM models from HuggingFace
- Create config.json with absolute paths to all models
- Verify pipeline runs successfully with test image

Model locations:
- nnU-Net: DEPENDENCIES/nnunet_knee_inference/huggingface/
- DOSMA: DOSMA_WEIGHTS/
- NSM: NSM_MODELS/
- BScore: BSCORE_MODELS/ (already included)
"
```

---

## Next Step: Stage 3.3 - Pipeline Worker Integration

See [STAGE_3.3_PIPELINE_WORKER.md](./STAGE_3.3_PIPELINE_WORKER.md)

Stage 3.3 integrates the real pipeline into the web application:
1. Create `backend/workers/pipeline_worker.py`
2. Create `backend/services/config_generator.py`
3. Update `tasks.py` to call real pipeline
4. Add GPU memory management


