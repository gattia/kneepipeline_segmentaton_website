"""
Progress parsing from pipeline output.

Parses stdout from the pipeline to extract progress information
for real-time updates to the web UI.
"""
import re
from dataclasses import dataclass
from typing import Optional


@dataclass
class ProgressUpdate:
    """Parsed progress information."""
    step: int
    total_steps: int
    step_name: str
    percent: int
    substep: Optional[str] = None


# Pipeline step patterns to watch for
STEP_PATTERNS = [
    # Pattern: (regex, step_number, step_name)
    (r"loading.*model", 1, "Loading segmentation model"),
    (r"preprocessing", 2, "Preprocessing image"),
    (r"running.*segmentation", 3, "Running segmentation"),
    (r"postprocessing", 4, "Postprocessing results"),
    (r"generating.*mesh", 5, "Generating 3D meshes"),
    (r"calculating.*thickness", 6, "Calculating cartilage thickness"),
    (r"running.*nsm|neural shape model", 7, "Running Neural Shape Model"),
    (r"computing.*bscore", 8, "Computing BScore"),
    (r"saving.*results", 9, "Saving results"),
    (r"complete|finished|done", 10, "Complete"),
]

# Total steps in full pipeline
TOTAL_STEPS = 10


def parse_progress_line(line: str) -> Optional[ProgressUpdate]:
    """
    Parse a single line of pipeline output for progress.
    
    Args:
        line: Single line from pipeline stdout/stderr
        
    Returns:
        ProgressUpdate if progress detected, None otherwise
    """
    line_lower = line.lower().strip()
    
    for pattern, step, step_name in STEP_PATTERNS:
        if re.search(pattern, line_lower):
            percent = int((step / TOTAL_STEPS) * 100)
            return ProgressUpdate(
                step=step,
                total_steps=TOTAL_STEPS,
                step_name=step_name,
                percent=percent,
            )
    
    # Check for explicit progress markers (if pipeline outputs them)
    # Format: [PROGRESS] step/total: step_name
    progress_match = re.search(r'\[PROGRESS\]\s*(\d+)/(\d+):\s*(.+)', line)
    if progress_match:
        step = int(progress_match.group(1))
        total = int(progress_match.group(2))
        name = progress_match.group(3).strip()
        return ProgressUpdate(
            step=step,
            total_steps=total,
            step_name=name,
            percent=int((step / total) * 100),
        )
    
    # Check for percentage markers
    # Format: Processing... 45% or [45%] or (45%)
    percent_match = re.search(r'(\d{1,3})%', line)
    if percent_match:
        percent = min(int(percent_match.group(1)), 100)
        step = max(1, int((percent / 100) * TOTAL_STEPS))
        return ProgressUpdate(
            step=step,
            total_steps=TOTAL_STEPS,
            step_name="Processing...",
            percent=percent,
        )
    
    return None


def estimate_progress_from_time(elapsed_seconds: float, estimated_total: float) -> ProgressUpdate:
    """
    Estimate progress based on elapsed time.
    
    Used as fallback when pipeline doesn't provide progress info.
    
    Args:
        elapsed_seconds: Time since processing started
        estimated_total: Estimated total processing time
        
    Returns:
        ProgressUpdate based on time
    """
    if estimated_total <= 0:
        estimated_total = 300  # Default 5 minutes
    
    percent = min(95, int((elapsed_seconds / estimated_total) * 100))
    step = max(1, int((percent / 100) * TOTAL_STEPS))
    
    # Map step to name
    step_names = {
        1: "Loading model",
        2: "Preprocessing",
        3: "Running segmentation",
        4: "Postprocessing",
        5: "Generating meshes",
        6: "Calculating thickness",
        7: "Running NSM",
        8: "Computing BScore",
        9: "Saving results",
        10: "Complete",
    }
    
    return ProgressUpdate(
        step=step,
        total_steps=TOTAL_STEPS,
        step_name=step_names.get(step, "Processing..."),
        percent=percent,
    )


