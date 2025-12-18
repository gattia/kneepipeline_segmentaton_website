"""
Real pipeline worker for knee MRI segmentation.

This module executes the actual segmentation pipeline as a subprocess,
handling configuration, progress tracking, and error management.
"""
import gc
import os
import shutil
import subprocess
import sys
import threading
import time
from pathlib import Path
from queue import Empty, Queue
from typing import Callable, Optional

import torch

from backend.services.progress_parser import (
    estimate_progress_from_time,
    parse_progress_line,
)


# Pipeline paths
KNEEPIPELINE_PATH = Path(os.path.expanduser("~/programming/kneepipeline"))
PIPELINE_SCRIPT = KNEEPIPELINE_PATH / "dosma_knee_seg.py"

# Timeout for pipeline execution (30 minutes)
PIPELINE_TIMEOUT_SECONDS = 1800

# Path translation for Docker -> Host
# The web container uses /app/data, but the host uses /mnt/data/knee_pipeline_data
DOCKER_DATA_PATH = "/app/data"
HOST_DATA_PATH = os.getenv("HOST_DATA_PATH", "/mnt/data/knee_pipeline_data")


def translate_docker_path(path: str) -> str:
    """
    Translate Docker container path to host path.
    
    The web container stores files at /app/data/..., but the worker
    running on the host needs to access them at /mnt/data/knee_pipeline_data/...
    """
    if path.startswith(DOCKER_DATA_PATH):
        return path.replace(DOCKER_DATA_PATH, HOST_DATA_PATH, 1)
    return path


def run_real_pipeline(
    input_path: str,
    options: dict,
    output_dir: Path,
    config_path: Path,
    progress_callback: Optional[Callable[[int, int, str], None]] = None,
) -> Path:
    """
    Execute the real segmentation pipeline.

    Args:
        input_path: Path to the input medical image
        options: Processing options from web UI
        output_dir: Directory to save results
        config_path: Path to job-specific config.json
        progress_callback: Optional callback(step, total_steps, step_name)

    Returns:
        Path to the results zip file

    Raises:
        ValueError: If input cannot be processed
        RuntimeError: If pipeline execution fails
        TimeoutError: If pipeline exceeds timeout
    """
    # Translate Docker paths to host paths
    input_path = Path(translate_docker_path(str(input_path)))
    output_dir = Path(translate_docker_path(str(output_dir)))
    config_path = Path(translate_docker_path(str(config_path)))

    # Create output directory
    results_dir = output_dir / "pipeline_output"
    results_dir.mkdir(parents=True, exist_ok=True)

    def update_progress(step: int, total: int, name: str):
        if progress_callback:
            progress_callback(step, total, name)

    total_steps = 5

    # Step 1: Setup
    update_progress(1, total_steps, "Preparing pipeline")

    # Determine model name from options
    seg_model = options.get("segmentation_model", "nnunet_fullres")
    model_name = _map_model_name(seg_model)

    # Step 2: Run segmentation pipeline
    update_progress(2, total_steps, "Running segmentation")

    # Build command
    command = [
        sys.executable,  # Use same Python interpreter
        str(PIPELINE_SCRIPT),
        str(input_path),
        str(results_dir),
        model_name,
    ]

    # Set environment with config path
    env = os.environ.copy()
    env["KNEEPIPELINE_CONFIG"] = str(config_path)

    # Add kneepipeline to PYTHONPATH
    python_path = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = f"{KNEEPIPELINE_PATH}:{python_path}"

    try:
        # Run pipeline as subprocess
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=PIPELINE_TIMEOUT_SECONDS,
            cwd=str(KNEEPIPELINE_PATH),
            env=env,
        )

        # Log output
        if result.stdout:
            print(f"Pipeline stdout:\n{result.stdout}")
        if result.stderr:
            print(f"Pipeline stderr:\n{result.stderr}")

        # Check for errors
        if result.returncode != 0:
            error_msg = _parse_pipeline_error(result.stderr or result.stdout)
            raise RuntimeError(f"Pipeline failed: {error_msg}")

    except subprocess.TimeoutExpired as e:
        raise TimeoutError(f"Pipeline exceeded {PIPELINE_TIMEOUT_SECONDS}s timeout") from e

    # Step 3: Verify outputs
    update_progress(3, total_steps, "Verifying outputs")

    if not _verify_pipeline_outputs(results_dir):
        raise RuntimeError("Pipeline completed but expected output files are missing")

    # Step 4: Package results
    update_progress(4, total_steps, "Packaging results")

    # Determine input stem for naming
    input_stem = input_path.stem
    if input_path.suffix == ".gz":
        input_stem = Path(input_stem).stem
    if input_path.is_dir():
        input_stem = input_path.name

    # Create results zip
    zip_path = shutil.make_archive(
        str(output_dir / f"{input_stem}_results"),
        "zip",
        results_dir
    )

    # Step 5: Cleanup GPU memory
    update_progress(5, total_steps, "Cleaning up")
    cleanup_gpu_memory()

    return Path(zip_path)


def _map_model_name(web_model: str) -> str:
    """Map web UI model name to pipeline model name."""
    mapping = {
        "nnunet_fullres": "nnunet_knee",
        "nnunet_cascade": "nnunet_knee",
        "goyal_sagittal": "goyal_sagittal",
        "goyal_coronal": "goyal_coronal",
        "goyal_axial": "goyal_axial",
        "staple": "staple",
    }
    return mapping.get(web_model, "nnunet_knee")


def _verify_pipeline_outputs(output_dir: Path) -> bool:
    """
    Verify that expected pipeline outputs exist.

    Returns True if at least segmentation file exists.
    """
    # Check for segmentation file (various possible names)
    seg_patterns = ["*seg*.nii.gz", "*seg*.nrrd", "segmentation*"]
    for pattern in seg_patterns:
        if list(output_dir.glob(pattern)):
            return True

    # Check for any NIfTI or NRRD files
    if list(output_dir.glob("*.nii.gz")) or list(output_dir.glob("*.nrrd")):
        return True

    # Check for result files (JSON or CSV)
    if list(output_dir.glob("*.json")) or list(output_dir.glob("*.csv")):
        return True

    return False


def _parse_pipeline_error(error_output: str) -> str:
    """
    Parse pipeline error output and return user-friendly message.
    """
    error_output = error_output.lower()

    if "out of memory" in error_output or "cuda out of memory" in error_output:
        return "GPU ran out of memory. Try a smaller file or contact support."
    elif "no such file" in error_output or "not found" in error_output:
        return "Input file could not be read. Please check the file format."
    elif "invalid" in error_output and "format" in error_output:
        return "Invalid file format. Supported formats: NIfTI, NRRD, DICOM."
    elif "permission denied" in error_output:
        return "Permission denied when accessing files."
    elif "segmentation failed" in error_output:
        return "Segmentation failed. The image quality may be insufficient."
    else:
        # Return last line of error as fallback
        lines = error_output.strip().split("\n")
        return lines[-1][:200] if lines else "Unknown error occurred"


def cleanup_gpu_memory():
    """
    Clean up GPU memory after pipeline execution.

    Should be called after each job to prevent memory leaks.
    """
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
        torch.cuda.synchronize()

    # Force garbage collection
    gc.collect()

    # Small delay to ensure memory is freed
    time.sleep(1)


def run_pipeline_with_progress(
    command: list,
    env: dict,
    cwd: str,
    timeout: int,
    progress_callback: Optional[Callable[[int, int, str], None]] = None,
) -> tuple:
    """
    Run pipeline subprocess with real-time progress parsing.
    
    Args:
        command: Command list to execute
        env: Environment variables
        cwd: Working directory
        timeout: Timeout in seconds
        progress_callback: Callback for progress updates
        
    Returns:
        Tuple of (returncode, stdout, stderr)
    """
    process = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        cwd=cwd,
        env=env,
    )
    
    stdout_lines = []
    stderr_lines = []
    last_progress = None
    start_time = time.time()
    
    # Queues for non-blocking reads
    stdout_queue: Queue = Queue()
    stderr_queue: Queue = Queue()
    
    def read_stream(stream, queue):
        for line in iter(stream.readline, ''):
            queue.put(line)
        stream.close()
    
    # Start reader threads
    stdout_thread = threading.Thread(target=read_stream, args=(process.stdout, stdout_queue))
    stderr_thread = threading.Thread(target=read_stream, args=(process.stderr, stderr_queue))
    stdout_thread.daemon = True
    stderr_thread.daemon = True
    stdout_thread.start()
    stderr_thread.start()
    
    # Monitor process with timeout
    while True:
        elapsed = time.time() - start_time
        
        # Check timeout
        if elapsed > timeout:
            process.kill()
            raise TimeoutError(f"Pipeline exceeded {timeout}s timeout")
        
        # Read available output
        try:
            while True:
                line = stdout_queue.get_nowait()
                stdout_lines.append(line)
                
                # Try to parse progress
                if progress_callback:
                    progress = parse_progress_line(line)
                    if progress and progress != last_progress:
                        progress_callback(progress.step, progress.total_steps, progress.step_name)
                        last_progress = progress
        except Empty:
            pass
        
        try:
            while True:
                line = stderr_queue.get_nowait()
                stderr_lines.append(line)
                
                # Also check stderr for progress
                if progress_callback:
                    progress = parse_progress_line(line)
                    if progress and progress != last_progress:
                        progress_callback(progress.step, progress.total_steps, progress.step_name)
                        last_progress = progress
        except Empty:
            pass
        
        # Check if process finished
        if process.poll() is not None:
            break
        
        # Update progress based on time if no explicit progress
        if progress_callback and last_progress is None:
            time_progress = estimate_progress_from_time(elapsed, 300)  # 5 min estimate
            progress_callback(time_progress.step, time_progress.total_steps, time_progress.step_name)
        
        time.sleep(0.5)  # Small delay between checks
    
    # Get any remaining output
    stdout_thread.join(timeout=1)
    stderr_thread.join(timeout=1)
    
    return (
        process.returncode,
        ''.join(stdout_lines),
        ''.join(stderr_lines),
    )

