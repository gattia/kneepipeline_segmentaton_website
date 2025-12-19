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
# Can be overridden via KNEEPIPELINE_PATH environment variable
KNEEPIPELINE_PATH = Path(os.getenv("KNEEPIPELINE_PATH", os.path.expanduser("~/programming/kneepipeline")))

# All possible segmentation models (some may not have weights downloaded)
# Note: "staple" is available in pipeline code but not exposed in UI
ALL_SEG_MODELS = [
    "dosma_ananya",  # Goyal 2024 - default, best performance
    "nnunet_fullres",
    "nnunet_cascade",
    "goyal_sagittal",
    "goyal_coronal",
    "goyal_axial",
]

# Model weight paths for checking availability
MODEL_WEIGHT_PATHS = {
    "dosma_ananya": KNEEPIPELINE_PATH / "DOSMA_WEIGHTS" / "Goyal_Bone_Cart_July_2024_best_model.h5",
    "nnunet_fullres": KNEEPIPELINE_PATH / "DEPENDENCIES" / "nnunet_knee_inference" / "huggingface" / "models",
    "nnunet_cascade": KNEEPIPELINE_PATH / "DEPENDENCIES" / "nnunet_knee_inference" / "huggingface" / "models",
    "goyal_sagittal": KNEEPIPELINE_PATH / "DOSMA_WEIGHTS" / "sagittal_best_model.h5",
    "goyal_coronal": KNEEPIPELINE_PATH / "DOSMA_WEIGHTS" / "coronal_best_model.h5",
    "goyal_axial": KNEEPIPELINE_PATH / "DOSMA_WEIGHTS" / "axial_best_model.h5",
}


def get_available_models() -> list:
    """
    Get list of segmentation models that have weights downloaded.
    
    Priority:
    1. If AVAILABLE_MODELS env var is set, use that (comma-separated list)
    2. Otherwise, dynamically check if model weight files exist
    3. If path doesn't exist (Docker), fall back to env var or empty list
    
    Set AVAILABLE_MODELS in docker-compose.yml for the web container.
    """
    # Check for explicit environment variable first
    available_env = os.getenv("AVAILABLE_MODELS")
    if available_env:
        # Parse comma-separated list, filter to valid models
        models = [m.strip() for m in available_env.split(",") if m.strip()]
        return [m for m in models if m in ALL_SEG_MODELS]
    
    # If kneepipeline path doesn't exist, return empty (no models available)
    # This happens when running in Docker where only the worker has access to weights
    if not KNEEPIPELINE_PATH.exists():
        return []
    
    # Dynamically check which models have weights
    available = []
    for model in ALL_SEG_MODELS:
        weight_path = MODEL_WEIGHT_PATHS.get(model)
        if weight_path and weight_path.exists():
            available.append(model)
    
    return available


# For backward compatibility, VALID_SEG_MODELS will be computed dynamically
def _get_valid_seg_models():
    """Get valid models (those with weights available)."""
    return get_available_models()


VALID_SEG_MODELS = ALL_SEG_MODELS  # Accept all for validation, check availability separately

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
            f"Invalid nsm_type '{nsm_type}'. " f"Must be one of: {VALID_NSM_TYPES}"
        )

    # Validate cartilage smoothing
    if "cartilage_smoothing" in options and options["cartilage_smoothing"] is not None:
        smooth = options["cartilage_smoothing"]
        if not isinstance(smooth, (int, float)) or smooth < 0 or smooth > 2:
            raise ConfigValidationError(
                f"cartilage_smoothing must be between 0.0 and 2.0, got {smooth}"
            )

    # Validate batch size
    if "batch_size" in options and options["batch_size"] is not None:
        batch = options["batch_size"]
        if not isinstance(batch, int) or batch < 1 or batch > 256:
            raise ConfigValidationError(f"batch_size must be between 1 and 256, got {batch}")


def generate_pipeline_config(
    job_dir: Path,
    options: dict,
    base_config_path: Optional[Path] = None,
    validate: bool = True,
) -> Path:
    """
    Generate a job-specific config.json for the pipeline.

    Args:
        job_dir: Directory to save the config file
        options: Processing options from web UI
        base_config_path: Path to base config.json (defaults to kneepipeline/config.json)
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

    # Map segmentation model selection
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
    """
    Map web UI model selection to pipeline model name.

    Args:
        web_model: Model name from web UI

    Returns:
        Pipeline model name
    """
    model_mapping = {
        "nnunet_fullres": "nnunet_knee",
        "nnunet_cascade": "nnunet_knee",
        "dosma_ananya": "acl_qdess_bone_july_2024",
        "goyal_sagittal": "goyal_sagittal",
        "goyal_coronal": "goyal_coronal",
        "goyal_axial": "goyal_axial",
        "staple": "staple",
    }
    return model_mapping.get(web_model, "nnunet_knee")


def get_available_nsm_types() -> list:
    """Get list of available NSM types."""
    return VALID_NSM_TYPES.copy()


def get_pipeline_script_path() -> Path:
    """Get the path to the main pipeline script."""
    return KNEEPIPELINE_PATH / "dosma_knee_seg.py"


def get_base_config_path() -> Path:
    """Get the path to the base config.json."""
    return KNEEPIPELINE_PATH / "config.json"


