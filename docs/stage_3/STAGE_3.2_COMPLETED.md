# Stage 3.2 Completed: Model Download and Configuration

**Completed**: December 18, 2025

---

## Summary

Successfully downloaded all model weights and created the pipeline configuration file. The pipeline has been tested end-to-end with a real MRI image.

---

## What Was Done

### 1. nnU-Net Models Downloaded

Downloaded from HuggingFace (`aagatti/nnunet_knee`):

```
~/programming/kneepipeline/DEPENDENCIES/nnunet_knee_inference/huggingface/
├── models/
│   └── Dataset500_KneeMRI/
│       ├── nnUNetTrainer__nnUNetResEncUNetMPlans__3d_fullres/   # ~778 MB
│       ├── nnUNetTrainer__nnUNetResEncUNetMPlans__3d_cascade_fullres/
│       └── nnUNetTrainer__nnUNetResEncUNetMPlans__3d_lowres/
├── test_data/
│   ├── test_image.nii.gz      # 307 MB test image
│   ├── test_ground_truth.nii.gz
│   └── test_prediction.nii.gz
├── config.json
├── dataset.json
└── plans.json
```

**Inference Test Results:**
- Mean Dice Score: **0.915** (Excellent)
- Inference time: ~160 seconds (cascade) / ~70 seconds (fullres)

### 2. DOSMA Weights Downloaded

Downloaded from HuggingFace (`aagatti/dosma_bones`):

```
~/programming/kneepipeline/DOSMA_WEIGHTS/
└── Goyal_Bone_Cart_July_2024_best_model.h5   # 324 MB
```

**Note**: Only the combined model is currently available on HuggingFace. The separate orientation models (`sagittal_best_model.h5`, `coronal_best_model.h5`, `axial_best_model.h5`) for DOSMA-based segmentation are not yet uploaded. These can be added later if needed.

**Impact**: None - nnU-Net is the default and recommended model. DOSMA models are optional alternatives.

### 3. NSM Models Downloaded

Downloaded from HuggingFace (`aagatti/ShapeMedKnee`) - gated repo requiring authentication:

```
~/programming/kneepipeline/NSM_MODELS/
├── 231_nsm_femur_cartilage_v0.0.1/    # Bone + Cartilage NSM
│   ├── model_config.json
│   ├── model/2000.pth
│   └── latent_codes/2000.pth
└── NSM_BScore_Aug_2024/               # Older BScore (not used)
    ├── model.json
    └── Bscore.py
```

**Available Models:**
- ✅ Bone + Cartilage NSM (`231_nsm_femur_cartilage_v0.0.1`)
- ❌ Bone-Only NSM (not in HuggingFace repo - can be copied manually if needed)

**config.json updated:**
- `perform_bone_and_cart_nsm`: `true` (enabled)
- `perform_bone_only_nsm`: `false` (model not available)

### 4. BScore Models - Already Included

BScore models are already included in the kneepipeline repository:

```
~/programming/kneepipeline/BSCORE_MODELS/
├── NSM_Orig_BScore_Bone_Cartilage_April_17_2025/
└── NSM_Orig_BScore_Bone_Only_April_18_2025/
```

### 5. config.json Created

Created `~/programming/kneepipeline/config.json` with:

| Setting | Value | Notes |
|---------|-------|-------|
| `default_seg_model` | `nnunet_knee` | Uses nnU-Net (recommended) |
| `nnunet.type` | `fullres` | Can be changed to `cascade` |
| `perform_bone_and_cart_nsm` | `true` | ✅ Enabled - NSM model downloaded |
| `perform_bone_only_nsm` | `false` | Model not available in HuggingFace |
| `clip_femur_top` | `true` | Standard preprocessing |
| `batch_size` | `32` | Adjust based on GPU memory |

---

## Pipeline Test Results

Ran full pipeline with test image:

```bash
cd ~/programming/kneepipeline
python dosma_knee_seg.py \
    DEPENDENCIES/nnunet_knee_inference/huggingface/test_data/test_image.nii.gz \
    /tmp/pipeline_test_output \
    nnunet_knee
```

### Output Files Generated

| File | Size | Description |
|------|------|-------------|
| `test_image_all-labels.nii.gz` | 172 KB | Segmentation mask |
| `test_image_all-labels.nrrd` | 268 KB | Segmentation mask (NRRD) |
| `test_image_subregions-labels.nii.gz` | 172 KB | Subregion labels |
| `test_image_subregions-labels.nrrd` | 267 KB | Subregion labels (NRRD) |
| `femur_mesh.vtk` | 1.9 MB | Femur bone surface mesh |
| `femur_cart_0_mesh.vtk` | 8.4 MB | Femoral cartilage mesh |
| `tibia_mesh.vtk` | 1.9 MB | Tibia bone surface mesh |
| `tibia_cart_0_mesh.vtk` | 4.8 MB | Medial tibial cartilage mesh |
| `tibia_cart_1_mesh.vtk` | 6.4 MB | Lateral tibial cartilage mesh |
| `patella_mesh.vtk` | 0.9 MB | Patella bone surface mesh |
| `patella_cart_0_mesh.vtk` | 5.1 MB | Patellar cartilage mesh |
| `test_image_results.json` | 1.2 KB | Thickness metrics |
| `test_image_results.csv` | 1.0 KB | Thickness metrics (CSV) |

### Cartilage Thickness Results

| Region | Mean (mm) | Std (mm) | Median (mm) |
|--------|-----------|----------|-------------|
| Patellar cartilage | 2.66 | 0.87 | 2.74 |
| Anterior femoral | 1.91 | 0.68 | 1.87 |
| Medial WB femoral | 1.89 | 0.55 | 2.02 |
| Lateral WB femoral | 1.38 | 0.32 | 1.42 |
| Medial posterior femoral | 1.35 | 0.32 | 1.38 |
| Lateral posterior femoral | 1.51 | 0.47 | 1.62 |
| Medial tibial | 1.95 | 0.70 | 1.92 |
| Lateral tibial | 1.99 | 0.85 | 1.94 |

### Processing Time

| Step | Duration |
|------|----------|
| Image loading | ~3 sec |
| nnU-Net segmentation | ~70 sec |
| Post-processing | ~14 sec |
| Mesh generation | ~3.5 min |
| T2 computation | Skipped (not qDESS) |
| **Total** | **~5.5 minutes** |

---

## Expected Warnings (Safe to Ignore)

1. **TensorFlow/TensorRT warnings**: `Could not load dynamic library 'libnvinfer.so.7'` - Optional GPU optimization
2. **SimpleITK warning**: `Non-orthogonal direction matrix coerced to orthogonal` - Normal for some NIFTI files
3. **PyVista warning**: `Mesh is now synonymous with pyvista.PolyData` - Deprecation notice, no impact
4. **NumPy warnings**: `Mean of empty slice` / `invalid value encountered` - Expected for some regions

---

## Directory Structure After Stage 3.2

```
~/programming/kneepipeline/
├── config.json                  # ✓ Created with correct paths
├── download_nsm_models.py       # ✓ Helper script for NSM download
├── DOSMA_WEIGHTS/               # ⚠️ Partial (1 of 4 models)
│   └── Goyal_Bone_Cart_July_2024_best_model.h5
├── NSM_MODELS/                  # ✓ Downloaded (bone+cart only)
│   └── 231_nsm_femur_cartilage_v0.0.1/
├── BSCORE_MODELS/               # ✓ Already included
│   ├── NSM_Orig_BScore_Bone_Cartilage_April_17_2025/
│   └── NSM_Orig_BScore_Bone_Only_April_18_2025/
└── DEPENDENCIES/
    └── nnunet_knee_inference/
        └── huggingface/         # ✓ Downloaded
            ├── models/Dataset500_KneeMRI/
            └── test_data/
```

---

## Verification Commands

```bash
# Activate environment
source ~/miniconda3/etc/profile.d/conda.sh
conda activate kneepipeline
cd ~/programming/kneepipeline

# Verify config loads
python -c "import json; c = json.load(open('config.json')); print(f'Model: {c[\"default_seg_model\"]}, Type: {c[\"nnunet\"][\"type\"]}')"

# Run nnU-Net inference test
cd DEPENDENCIES/nnunet_knee_inference
python test_inference.py

# Run full pipeline test (takes ~5 minutes)
cd ~/programming/kneepipeline
python dosma_knee_seg.py \
    DEPENDENCIES/nnunet_knee_inference/huggingface/test_data/test_image.nii.gz \
    /tmp/test_output \
    nnunet_knee
```

---

## Next Step: Stage 3.3 - Pipeline Worker Integration

See [STAGE_3.3_PIPELINE_WORKER.md](./STAGE_3.3_PIPELINE_WORKER.md)

Stage 3.3 integrates the real pipeline into the web application:
1. Create `backend/workers/pipeline_worker.py`
2. Create `backend/services/config_generator.py`
3. Update `tasks.py` to call real pipeline
4. Add GPU memory management
5. Add subprocess timeout handling

---

## Notes

### NSM Models

NSM bone+cartilage model is now downloaded and enabled in config.json.

**Current Status:**
- ✅ Bone + Cartilage NSM: Downloaded and enabled
- ❌ Bone-Only NSM: Not available in HuggingFace repo (can be copied manually if needed)

**To disable NSM analysis:**
```json
{
  "perform_bone_and_cart_nsm": false,
  "perform_bone_only_nsm": false
}
```

### Switching nnU-Net Models

To use cascade instead of fullres (potentially better quality, ~2x slower):

```json
{
  "nnunet": {
    "type": "cascade",
    "model_name": "Dataset500_KneeMRI"
  }
}
```

### GPU Memory

If you encounter OOM errors, try:
- Reducing `batch_size` in config.json
- Using fullres instead of cascade
- Clearing GPU memory before running: `torch.cuda.empty_cache()`

