# Stage 3.4: Configuration Mapping

## Overview

**Goal**: Ensure all web UI options are correctly mapped to pipeline configuration, with proper validation.

**Estimated Time**: ~1 hour

**Deliverable**: Complete mapping from web UI options to pipeline config with validation.

---

## Prerequisites

**Stage 3.3 must be complete.** Verify by running:

```bash
conda activate kneepipeline
cd ~/programming/kneepipeline_segmentaton_website

# Stage 3.3 tests should pass
pytest -m stage_3_3 -v

# Config generator should be importable
python -c "from backend.services.config_generator import generate_pipeline_config; print('OK')"
```

---

## What This Stage Creates

### Modified Files

```
backend/
├── services/
│   └── config_generator.py      # MODIFY: Add full option mapping and validation
├── routes/
│   └── upload.py                # MODIFY: Add new options to schema
└── models/
    └── schemas.py               # MODIFY: Add NSM options to upload schema

frontend/
└── js/
    └── app.js                   # MODIFY: Add NSM option UI controls

tests/
└── test_stage_3_4.py            # NEW: Configuration mapping tests
```

---

## Success Criteria

- [ ] All web UI segmentation models map correctly to pipeline config
- [ ] NSM options (bone_and_cart, bone_only, both, none) work correctly
- [ ] Additional options (cartilage smoothing, batch size) pass through
- [ ] Invalid option combinations are rejected with clear errors
- [ ] Frontend UI shows all available options
- [ ] All Stage 3.4 tests pass: `pytest -m stage_3_4 -v`

---

## Configuration Option Reference

### Segmentation Models

| Web UI Value | Pipeline Config | Notes |
|--------------|-----------------|-------|
| `nnunet_fullres` | `default_seg_model: "nnunet_knee"`, `nnunet.type: "fullres"` | Primary recommended model |
| `nnunet_cascade` | `default_seg_model: "nnunet_knee"`, `nnunet.type: "cascade"` | More accurate, slower |
| `goyal_sagittal` | `default_seg_model: "goyal_sagittal"` | DOSMA sagittal model |
| `goyal_coronal` | `default_seg_model: "goyal_coronal"` | DOSMA coronal model |
| `goyal_axial` | `default_seg_model: "goyal_axial"` | DOSMA axial model |
| `staple` | `default_seg_model: "staple"` | Multi-model ensemble |

### NSM Options

| Web UI Value | Config Fields |
|--------------|---------------|
| `bone_and_cart` | `perform_bone_and_cart_nsm: true`, `perform_bone_only_nsm: false` |
| `bone_only` | `perform_bone_and_cart_nsm: false`, `perform_bone_only_nsm: true` |
| `both` | `perform_bone_and_cart_nsm: true`, `perform_bone_only_nsm: true` |
| `none` | `perform_bone_and_cart_nsm: false`, `perform_bone_only_nsm: false` |

### Additional Options

| Web UI Option | Config Field | Default | Range |
|---------------|--------------|---------|-------|
| `cartilage_smoothing` | `image_smooth_var_cart` | 0.5 | 0.0 - 2.0 |
| `batch_size` | `batch_size` | 32 | 1 - 64 |
| `clip_femur_top` | `clip_femur_top` | true | boolean |

---

## Detailed Implementation

### Step 1: Update Upload Schema

**File**: `backend/models/schemas.py`

Add new fields for pipeline options:

```python
"""Request/Response schemas for the API."""
from typing import Optional
from pydantic import BaseModel, Field, validator


class UploadOptions(BaseModel):
    """Options for MRI processing."""
    
    segmentation_model: str = Field(
        default="nnunet_fullres",
        description="Segmentation model to use"
    )
    
    perform_nsm: bool = Field(
        default=True,
        description="Whether to perform Neural Shape Model analysis"
    )
    
    nsm_type: str = Field(
        default="bone_and_cart",
        description="Type of NSM analysis: bone_and_cart, bone_only, both, or none"
    )
    
    cartilage_smoothing: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=2.0,
        description="Cartilage smoothing variance (0.0-2.0)"
    )
    
    batch_size: Optional[int] = Field(
        default=None,
        ge=1,
        le=64,
        description="Batch size for inference (1-64)"
    )
    
    clip_femur_top: bool = Field(
        default=True,
        description="Whether to clip the top of the femur"
    )
    
    @validator("segmentation_model")
    def validate_segmentation_model(cls, v):
        valid_models = [
            "nnunet_fullres",
            "nnunet_cascade",
            "goyal_sagittal",
            "goyal_coronal",
            "goyal_axial",
            "staple",
        ]
        if v not in valid_models:
            raise ValueError(f"Invalid segmentation model. Must be one of: {valid_models}")
        return v
    
    @validator("nsm_type")
    def validate_nsm_type(cls, v):
        valid_types = ["bone_and_cart", "bone_only", "both", "none"]
        if v not in valid_types:
            raise ValueError(f"Invalid NSM type. Must be one of: {valid_types}")
        return v


class UploadResponse(BaseModel):
    """Response after successful upload."""
    job_id: str
    status: str
    queue_position: int
    estimated_wait_minutes: int


class JobStatusResponse(BaseModel):
    """Response for job status query."""
    job_id: str
    status: str
    progress_percent: int = 0
    current_step: Optional[int] = None
    total_steps: Optional[int] = None
    step_name: Optional[str] = None
    queue_position: Optional[int] = None
    error_message: Optional[str] = None
    result_ready: bool = False


class StatsResponse(BaseModel):
    """Response for system statistics."""
    jobs_processed_today: int
    jobs_processed_total: int
    average_processing_time_minutes: float
    current_queue_length: int
```

---

### Step 2: Update Config Generator

**File**: `backend/services/config_generator.py`

Enhance with full validation and option mapping:

```python
"""
Configuration generator for the segmentation pipeline.

This module creates job-specific config.json files that configure
the pipeline based on user-selected options from the web UI.
"""
import json
import os
from pathlib import Path
from typing import Optional


# Base path for the kneepipeline library
KNEEPIPELINE_PATH = Path(os.path.expanduser("~/programming/kneepipeline"))

# Valid options
VALID_SEG_MODELS = [
    "nnunet_fullres",
    "nnunet_cascade", 
    "goyal_sagittal",
    "goyal_coronal",
    "goyal_axial",
    "staple",
]

VALID_NSM_TYPES = ["bone_and_cart", "bone_only", "both", "none"]


class ConfigValidationError(ValueError):
    """Raised when configuration validation fails."""
    pass


def validate_options(options: dict) -> None:
    """
    Validate processing options before config generation.
    
    Args:
        options: Processing options dict
        
    Raises:
        ConfigValidationError: If options are invalid
    """
    # Validate segmentation model
    seg_model = options.get("segmentation_model", "nnunet_fullres")
    if seg_model not in VALID_SEG_MODELS:
        raise ConfigValidationError(
            f"Invalid segmentation_model '{seg_model}'. "
            f"Must be one of: {VALID_SEG_MODELS}"
        )
    
    # Validate NSM type
    nsm_type = options.get("nsm_type", "bone_and_cart")
    if nsm_type not in VALID_NSM_TYPES:
        raise ConfigValidationError(
            f"Invalid nsm_type '{nsm_type}'. "
            f"Must be one of: {VALID_NSM_TYPES}"
        )
    
    # Validate cartilage smoothing
    if "cartilage_smoothing" in options:
        smooth = options["cartilage_smoothing"]
        if not isinstance(smooth, (int, float)) or smooth < 0 or smooth > 2:
            raise ConfigValidationError(
                f"cartilage_smoothing must be between 0.0 and 2.0, got {smooth}"
            )
    
    # Validate batch size
    if "batch_size" in options:
        batch = options["batch_size"]
        if not isinstance(batch, int) or batch < 1 or batch > 64:
            raise ConfigValidationError(
                f"batch_size must be between 1 and 64, got {batch}"
            )


def generate_pipeline_config(
    job_dir: Path,
    options: dict,
    base_config_path: Optional[Path] = None,
    validate: bool = True
) -> Path:
    """
    Generate a job-specific config.json for the pipeline.
    
    Args:
        job_dir: Directory to save the config file
        options: Processing options from web UI
        base_config_path: Path to base config.json
        validate: Whether to validate options before generation
        
    Returns:
        Path to the generated config.json
        
    Raises:
        ConfigValidationError: If validation is enabled and options are invalid
        FileNotFoundError: If base config doesn't exist
    """
    if validate:
        validate_options(options)
    
    if base_config_path is None:
        base_config_path = KNEEPIPELINE_PATH / "config.json"
    
    if not base_config_path.exists():
        raise FileNotFoundError(
            f"Base config not found: {base_config_path}. "
            "Ensure Stage 3.2 (Model Download) is complete."
        )
    
    # Load base configuration
    with open(base_config_path) as f:
        config = json.load(f)
    
    # Map segmentation model
    seg_model = options.get("segmentation_model", "nnunet_fullres")
    config["default_seg_model"] = _map_segmentation_model(seg_model)
    
    # Set nnU-Net type
    if "cascade" in seg_model:
        config["nnunet"]["type"] = "cascade"
    else:
        config["nnunet"]["type"] = "fullres"
    
    # Map NSM options
    perform_nsm = options.get("perform_nsm", True)
    nsm_type = options.get("nsm_type", "bone_and_cart")
    
    # Handle "none" type or perform_nsm=False
    if not perform_nsm or nsm_type == "none":
        config["perform_bone_and_cart_nsm"] = False
        config["perform_bone_only_nsm"] = False
    else:
        config["perform_bone_and_cart_nsm"] = nsm_type in ["bone_and_cart", "both"]
        config["perform_bone_only_nsm"] = nsm_type in ["bone_only", "both"]
    
    # Map additional options
    if "cartilage_smoothing" in options and options["cartilage_smoothing"] is not None:
        config["image_smooth_var_cart"] = options["cartilage_smoothing"]
    
    if "batch_size" in options and options["batch_size"] is not None:
        config["batch_size"] = options["batch_size"]
    
    if "clip_femur_top" in options:
        config["clip_femur_top"] = options["clip_femur_top"]
    
    # Save job-specific config
    job_dir = Path(job_dir)
    job_dir.mkdir(parents=True, exist_ok=True)
    config_path = job_dir / "config.json"
    
    with open(config_path, "w") as f:
        json.dump(config, f, indent=2)
    
    return config_path


def _map_segmentation_model(web_model: str) -> str:
    """Map web UI model selection to pipeline model name."""
    model_mapping = {
        "nnunet_fullres": "nnunet_knee",
        "nnunet_cascade": "nnunet_knee",
        "goyal_sagittal": "goyal_sagittal",
        "goyal_coronal": "goyal_coronal", 
        "goyal_axial": "goyal_axial",
        "staple": "staple",
    }
    return model_mapping.get(web_model, "nnunet_knee")


def get_available_models() -> list:
    """Get list of available segmentation models."""
    return VALID_SEG_MODELS.copy()


def get_available_nsm_types() -> list:
    """Get list of available NSM types."""
    return VALID_NSM_TYPES.copy()


def get_pipeline_script_path() -> Path:
    """Get the path to the main pipeline script."""
    return KNEEPIPELINE_PATH / "dosma_knee_seg.py"


def get_base_config_path() -> Path:
    """Get the path to the base config.json."""
    return KNEEPIPELINE_PATH / "config.json"
```

---

### Step 3: Update Upload Route

**File**: `backend/routes/upload.py`

Update to accept all options:

```python
"""Upload route - handles file uploads and job creation."""
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile

from backend.models.schemas import UploadResponse
from backend.services.config_generator import (
    ConfigValidationError,
    VALID_NSM_TYPES,
    VALID_SEG_MODELS,
    validate_options,
)
from backend.services.file_handler import validate_and_prepare_upload
from backend.services.job_service import get_estimated_wait, get_redis_client

router = APIRouter()


@router.post("/upload", response_model=UploadResponse)
async def upload_file(
    file: UploadFile = File(...),
    segmentation_model: str = Form(default="nnunet_fullres"),
    perform_nsm: bool = Form(default=True),
    nsm_type: str = Form(default="bone_and_cart"),
    cartilage_smoothing: float | None = Form(default=None),
    batch_size: int | None = Form(default=None),
    clip_femur_top: bool = Form(default=True),
    redis=Depends(get_redis_client),
):
    """
    Upload an MRI file for processing.
    
    Args:
        file: The MRI file (NIfTI, NRRD, or DICOM zip)
        segmentation_model: Which model to use for segmentation
        perform_nsm: Whether to run Neural Shape Model analysis
        nsm_type: Type of NSM (bone_and_cart, bone_only, both, none)
        cartilage_smoothing: Smoothing variance (0.0-2.0)
        batch_size: Inference batch size (1-64)
        clip_femur_top: Whether to clip top of femur
        
    Returns:
        UploadResponse with job ID and queue position
    """
    # Build options dict
    options = {
        "segmentation_model": segmentation_model,
        "perform_nsm": perform_nsm,
        "nsm_type": nsm_type,
        "clip_femur_top": clip_femur_top,
    }
    
    if cartilage_smoothing is not None:
        options["cartilage_smoothing"] = cartilage_smoothing
    
    if batch_size is not None:
        options["batch_size"] = batch_size
    
    # Validate options
    try:
        validate_options(options)
    except ConfigValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    # Process upload
    try:
        job = await validate_and_prepare_upload(file, options, redis)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    # Calculate queue position and wait time
    queue_position = job.get_queue_position(redis) or 1
    estimated_wait = get_estimated_wait(queue_position, redis)
    
    return UploadResponse(
        job_id=job.id,
        status=job.status,
        queue_position=queue_position,
        estimated_wait_minutes=estimated_wait,
    )


@router.get("/models")
async def get_available_models():
    """Get list of available segmentation models."""
    return {
        "segmentation_models": VALID_SEG_MODELS,
        "nsm_types": VALID_NSM_TYPES,
        "defaults": {
            "segmentation_model": "nnunet_fullres",
            "perform_nsm": True,
            "nsm_type": "bone_and_cart",
            "clip_femur_top": True,
        }
    }
```

---

### Step 4: Update Frontend

**File**: `frontend/js/app.js`

Add NSM option controls to the upload form (add to existing form handling):

```javascript
// Add to the form HTML generation or existing form elements
const nsmOptionsHtml = `
<div class="form-group nsm-options">
    <label for="perform_nsm">
        <input type="checkbox" id="perform_nsm" name="perform_nsm" checked>
        Perform Neural Shape Model Analysis
    </label>
</div>

<div class="form-group nsm-type-options" id="nsm-type-container">
    <label>NSM Analysis Type:</label>
    <div class="radio-group">
        <label>
            <input type="radio" name="nsm_type" value="bone_and_cart" checked>
            Bone + Cartilage
        </label>
        <label>
            <input type="radio" name="nsm_type" value="bone_only">
            Bone Only
        </label>
        <label>
            <input type="radio" name="nsm_type" value="both">
            Both
        </label>
    </div>
</div>

<div class="form-group advanced-options" style="display: none;">
    <details>
        <summary>Advanced Options</summary>
        <div class="advanced-options-content">
            <label for="cartilage_smoothing">
                Cartilage Smoothing (0.0-2.0):
                <input type="number" id="cartilage_smoothing" name="cartilage_smoothing" 
                       min="0" max="2" step="0.1" placeholder="Default: 0.5">
            </label>
            <label for="batch_size">
                Batch Size (1-64):
                <input type="number" id="batch_size" name="batch_size" 
                       min="1" max="64" placeholder="Default: 32">
            </label>
            <label>
                <input type="checkbox" id="clip_femur_top" name="clip_femur_top" checked>
                Clip Femur Top
            </label>
        </div>
    </details>
</div>
`;

// Toggle NSM type options based on perform_nsm checkbox
document.getElementById('perform_nsm')?.addEventListener('change', function(e) {
    const nsmTypeContainer = document.getElementById('nsm-type-container');
    if (nsmTypeContainer) {
        nsmTypeContainer.style.display = e.target.checked ? 'block' : 'none';
    }
});

// Update form submission to include new options
function collectFormOptions() {
    const options = {
        segmentation_model: document.getElementById('segmentation_model')?.value || 'nnunet_fullres',
        perform_nsm: document.getElementById('perform_nsm')?.checked ?? true,
        nsm_type: document.querySelector('input[name="nsm_type"]:checked')?.value || 'bone_and_cart',
        clip_femur_top: document.getElementById('clip_femur_top')?.checked ?? true,
    };
    
    const smoothing = document.getElementById('cartilage_smoothing')?.value;
    if (smoothing) {
        options.cartilage_smoothing = parseFloat(smoothing);
    }
    
    const batchSize = document.getElementById('batch_size')?.value;
    if (batchSize) {
        options.batch_size = parseInt(batchSize);
    }
    
    return options;
}
```

---

### Step 5: Create Stage 3.4 Tests

**File**: `tests/test_stage_3_4.py`

```python
"""
Stage 3.4 Verification Tests - Configuration Mapping

Run with: pytest -m stage_3_4 -v

These tests verify:
1. Option validation works correctly
2. All models map correctly
3. NSM type combinations work
4. Invalid options are rejected
5. Upload route accepts new options
"""
import json
import os
import pytest
from pathlib import Path

# Mark all tests in this module as stage_3_4
pytestmark = pytest.mark.stage_3_4


class TestOptionValidation:
    """Verify option validation."""
    
    def test_valid_nnunet_fullres(self):
        """nnunet_fullres should be valid."""
        from backend.services.config_generator import validate_options
        validate_options({"segmentation_model": "nnunet_fullres"})
    
    def test_valid_nnunet_cascade(self):
        """nnunet_cascade should be valid."""
        from backend.services.config_generator import validate_options
        validate_options({"segmentation_model": "nnunet_cascade"})
    
    def test_valid_goyal_models(self):
        """DOSMA goyal models should be valid."""
        from backend.services.config_generator import validate_options
        for model in ["goyal_sagittal", "goyal_coronal", "goyal_axial"]:
            validate_options({"segmentation_model": model})
    
    def test_invalid_segmentation_model(self):
        """Invalid model should raise error."""
        from backend.services.config_generator import ConfigValidationError, validate_options
        with pytest.raises(ConfigValidationError):
            validate_options({"segmentation_model": "invalid_model"})
    
    def test_valid_nsm_types(self):
        """All valid NSM types should pass validation."""
        from backend.services.config_generator import validate_options
        for nsm_type in ["bone_and_cart", "bone_only", "both", "none"]:
            validate_options({"nsm_type": nsm_type})
    
    def test_invalid_nsm_type(self):
        """Invalid NSM type should raise error."""
        from backend.services.config_generator import ConfigValidationError, validate_options
        with pytest.raises(ConfigValidationError):
            validate_options({"nsm_type": "invalid"})
    
    def test_valid_cartilage_smoothing(self):
        """Valid smoothing values should pass."""
        from backend.services.config_generator import validate_options
        validate_options({"cartilage_smoothing": 0.0})
        validate_options({"cartilage_smoothing": 1.0})
        validate_options({"cartilage_smoothing": 2.0})
    
    def test_invalid_cartilage_smoothing(self):
        """Invalid smoothing should raise error."""
        from backend.services.config_generator import ConfigValidationError, validate_options
        with pytest.raises(ConfigValidationError):
            validate_options({"cartilage_smoothing": -0.1})
        with pytest.raises(ConfigValidationError):
            validate_options({"cartilage_smoothing": 2.1})
    
    def test_valid_batch_size(self):
        """Valid batch sizes should pass."""
        from backend.services.config_generator import validate_options
        validate_options({"batch_size": 1})
        validate_options({"batch_size": 32})
        validate_options({"batch_size": 64})
    
    def test_invalid_batch_size(self):
        """Invalid batch size should raise error."""
        from backend.services.config_generator import ConfigValidationError, validate_options
        with pytest.raises(ConfigValidationError):
            validate_options({"batch_size": 0})
        with pytest.raises(ConfigValidationError):
            validate_options({"batch_size": 65})


class TestConfigGeneration:
    """Verify config generation with different options."""
    
    def test_cascade_sets_nnunet_type(self, temp_dir):
        """nnunet_cascade should set nnunet.type to cascade."""
        from backend.services.config_generator import generate_pipeline_config
        
        base_config = Path(os.path.expanduser("~/programming/kneepipeline/config.json"))
        if not base_config.exists():
            pytest.skip("Base config.json not found")
        
        config_path = generate_pipeline_config(
            job_dir=temp_dir,
            options={"segmentation_model": "nnunet_cascade"}
        )
        
        with open(config_path) as f:
            config = json.load(f)
        
        assert config["nnunet"]["type"] == "cascade"
    
    def test_fullres_sets_nnunet_type(self, temp_dir):
        """nnunet_fullres should set nnunet.type to fullres."""
        from backend.services.config_generator import generate_pipeline_config
        
        base_config = Path(os.path.expanduser("~/programming/kneepipeline/config.json"))
        if not base_config.exists():
            pytest.skip("Base config.json not found")
        
        config_path = generate_pipeline_config(
            job_dir=temp_dir,
            options={"segmentation_model": "nnunet_fullres"}
        )
        
        with open(config_path) as f:
            config = json.load(f)
        
        assert config["nnunet"]["type"] == "fullres"
    
    def test_nsm_none_disables_both(self, temp_dir):
        """nsm_type=none should disable both NSM analyses."""
        from backend.services.config_generator import generate_pipeline_config
        
        base_config = Path(os.path.expanduser("~/programming/kneepipeline/config.json"))
        if not base_config.exists():
            pytest.skip("Base config.json not found")
        
        config_path = generate_pipeline_config(
            job_dir=temp_dir,
            options={
                "perform_nsm": True,
                "nsm_type": "none"
            }
        )
        
        with open(config_path) as f:
            config = json.load(f)
        
        assert config["perform_bone_and_cart_nsm"] is False
        assert config["perform_bone_only_nsm"] is False
    
    def test_custom_smoothing_applied(self, temp_dir):
        """Custom cartilage_smoothing should be applied."""
        from backend.services.config_generator import generate_pipeline_config
        
        base_config = Path(os.path.expanduser("~/programming/kneepipeline/config.json"))
        if not base_config.exists():
            pytest.skip("Base config.json not found")
        
        config_path = generate_pipeline_config(
            job_dir=temp_dir,
            options={"cartilage_smoothing": 1.5}
        )
        
        with open(config_path) as f:
            config = json.load(f)
        
        assert config["image_smooth_var_cart"] == 1.5
    
    def test_custom_batch_size_applied(self, temp_dir):
        """Custom batch_size should be applied."""
        from backend.services.config_generator import generate_pipeline_config
        
        base_config = Path(os.path.expanduser("~/programming/kneepipeline/config.json"))
        if not base_config.exists():
            pytest.skip("Base config.json not found")
        
        config_path = generate_pipeline_config(
            job_dir=temp_dir,
            options={"batch_size": 16}
        )
        
        with open(config_path) as f:
            config = json.load(f)
        
        assert config["batch_size"] == 16


class TestAvailableOptions:
    """Verify option listing endpoints."""
    
    def test_get_available_models(self):
        """Should return list of valid models."""
        from backend.services.config_generator import get_available_models
        models = get_available_models()
        assert "nnunet_fullres" in models
        assert "nnunet_cascade" in models
        assert "goyal_sagittal" in models
    
    def test_get_available_nsm_types(self):
        """Should return list of valid NSM types."""
        from backend.services.config_generator import get_available_nsm_types
        types = get_available_nsm_types()
        assert "bone_and_cart" in types
        assert "bone_only" in types
        assert "both" in types
        assert "none" in types
```

---

## Verification Commands

```bash
conda activate kneepipeline
cd ~/programming/kneepipeline_segmentaton_website

# Run Stage 3.4 tests
pytest -m stage_3_4 -v

# Test option validation manually
python << 'EOF'
from backend.services.config_generator import validate_options, ConfigValidationError

# Test valid options
try:
    validate_options({
        "segmentation_model": "nnunet_cascade",
        "nsm_type": "both",
        "cartilage_smoothing": 1.0,
        "batch_size": 16
    })
    print("✓ Valid options accepted")
except ConfigValidationError as e:
    print(f"✗ Error: {e}")

# Test invalid options
try:
    validate_options({"segmentation_model": "invalid"})
    print("✗ Should have rejected invalid model")
except ConfigValidationError:
    print("✓ Invalid model rejected")
EOF
```

---

## Git Commit

```bash
git add .
git commit -m "Stage 3.4: Complete configuration mapping

- Add full validation for all pipeline options
- Add ConfigValidationError for clear error messages
- Map NSM type 'none' to disable both NSM analyses
- Add cartilage_smoothing and batch_size options
- Update upload route to accept all options
- Add /models endpoint to list available options
- Add Stage 3.4 verification tests

Options now supported:
- segmentation_model: nnunet_fullres, nnunet_cascade, goyal_*, staple
- nsm_type: bone_and_cart, bone_only, both, none
- cartilage_smoothing: 0.0-2.0
- batch_size: 1-64
- clip_femur_top: true/false
"
```

---

## Next Step: Stage 3.5 - Error Handling and Progress Updates

See [STAGE_3.5_ERROR_HANDLING.md](./STAGE_3.5_ERROR_HANDLING.md)


