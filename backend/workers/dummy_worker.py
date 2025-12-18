"""
Dummy pipeline worker for Phase 1 development.

This module simulates the real processing pipeline by:
1. Validating the input is a readable medical image
2. Creating a zeroed copy of the image
3. Generating dummy results JSON and CSV
4. Packaging everything into a results zip file

The real pipeline will replace this in Phase 3.
"""
import json
import os
import shutil
import time
from pathlib import Path
from typing import Callable, Optional

# Path translation for Docker -> Host (same as pipeline_worker)
DOCKER_DATA_PATH = "/app/data"
HOST_DATA_PATH = os.getenv("HOST_DATA_PATH", "/mnt/data/knee_pipeline_data")


def translate_docker_path(path: str) -> str:
    """Translate Docker container path to host path."""
    if path.startswith(DOCKER_DATA_PATH):
        return path.replace(DOCKER_DATA_PATH, HOST_DATA_PATH, 1)
    return path


def dummy_pipeline(
    input_path: str,
    options: dict,
    output_dir: Path,
    progress_callback: Optional[Callable[[int, int, str], None]] = None,
    simulate_delay: bool = True,
) -> Path:
    """
    Dummy worker for Phase 1 development.

    Creates a zeroed copy of the input image and packages results.
    Simulates processing time for realistic UX testing.

    Args:
        input_path: Path to the validated medical image
        options: Processing options from user
        output_dir: Directory to save results
        progress_callback: Optional callback(step, total_steps, step_name) for progress updates
        simulate_delay: If True, adds time.sleep() calls to simulate real processing time.
                       Set to False for faster test execution. Default: True.

    Returns:
        Path to the results zip file

    Raises:
        ValueError: If input cannot be read
        RuntimeError: If processing fails
    """
    import SimpleITK as sitk

    # Translate Docker paths to host paths
    input_path = Path(translate_docker_path(str(input_path)))
    output_dir = Path(translate_docker_path(str(output_dir)))

    # Create output directory
    results_dir = output_dir / "results"
    results_dir.mkdir(parents=True, exist_ok=True)

    def update_progress(step: int, total: int, name: str):
        """Helper to call progress callback if provided."""
        if progress_callback:
            progress_callback(step, total, name)

    def maybe_sleep(seconds: float):
        """Sleep only if simulate_delay is enabled (for faster tests)."""
        if simulate_delay:
            time.sleep(seconds)

    total_steps = 4

    # Step 1: Validate input
    update_progress(1, total_steps, "Validating input")
    maybe_sleep(1)  # Simulate work

    # Load the image
    try:
        if input_path.is_dir():
            # DICOM series
            reader = sitk.ImageSeriesReader()
            dicom_files = reader.GetGDCMSeriesFileNames(str(input_path))
            if not dicom_files:
                raise ValueError("No DICOM files found in directory")
            reader.SetFileNames(dicom_files)
            img = reader.Execute()
        else:
            # Single file (NIfTI, NRRD, or single DICOM)
            img = sitk.ReadImage(str(input_path))
    except Exception as e:
        raise ValueError(f"Failed to read input image: {e}") from e

    # Step 2: Process image (create zeroed copy)
    update_progress(2, total_steps, "Processing image")
    maybe_sleep(2)  # Simulate processing

    # Create zeroed copy (same dimensions/metadata, all zeros)
    zeroed = sitk.Image(img.GetSize(), img.GetPixelID())
    zeroed.CopyInformation(img)

    # Step 3: Generate results
    update_progress(3, total_steps, "Generating results")
    maybe_sleep(1)  # Simulate work

    # Determine input stem for naming
    input_stem = input_path.stem
    if input_path.suffix == ".gz":
        input_stem = Path(input_stem).stem  # Remove .nii from .nii.gz
    if input_path.is_dir():
        input_stem = input_path.name  # Use directory name for DICOM

    # Save zeroed image as "segmentation"
    sitk.WriteImage(zeroed, str(results_dir / "dummy_segmentation.nii.gz"))

    # Create dummy results JSON
    results_summary = {
        "status": "dummy_processing",
        "phase": "Phase 1 MVP",
        "input_file": input_path.name,
        "input_dimensions": list(img.GetSize()),
        "input_spacing": list(img.GetSpacing()),
        "options": options,
        "message": (
            "This is a dummy result from Phase 1 development. "
            "Real processing will be enabled in Phase 3."
        ),
        "dummy_metrics": {
            "femur_cartilage_thickness_mm": 2.45,
            "tibia_cartilage_thickness_mm": 2.12,
            "patella_cartilage_thickness_mm": 2.89,
            "bscore": -0.5,
            "note": "These are placeholder values",
        },
    }

    with open(results_dir / "results.json", "w") as f:
        json.dump(results_summary, f, indent=2)

    # Create dummy CSV
    csv_content = """region,mean_thickness_mm,std_thickness_mm,min_thickness_mm,max_thickness_mm,n_points
femur_medial,2.45,0.32,1.82,3.21,1500
femur_lateral,2.38,0.28,1.75,3.15,1400
tibia_medial,2.12,0.25,1.55,2.85,1200
tibia_lateral,2.08,0.22,1.48,2.78,1100
patella,2.89,0.35,2.10,3.65,800
"""
    with open(results_dir / "results.csv", "w") as f:
        f.write(csv_content)

    # Step 4: Package results
    update_progress(4, total_steps, "Packaging output")
    maybe_sleep(0.5)  # Simulate work

    # Create zip archive
    zip_path = shutil.make_archive(str(output_dir / f"{input_stem}_results"), "zip", results_dir)

    return Path(zip_path)
