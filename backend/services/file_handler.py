"""
File handling service for upload validation and preparation.

Handles:
- File extension validation
- Zip extraction
- Medical image discovery (NIfTI, NRRD, DICOM)
- SimpleITK validation of image readability
"""
import zipfile
from pathlib import Path
from typing import Optional

# Valid medical image extensions
VALID_EXTENSIONS = {'.nii', '.nii.gz', '.nrrd', '.dcm', '.zip'}


def validate_and_prepare_upload(upload_path: Path, temp_dir: Path) -> Path:
    """
    Process uploaded file: validate extension, extract if zip, validate medical image.

    Args:
        upload_path: Path to the uploaded file
        temp_dir: Directory for extracting zip contents

    Returns:
        Path to the validated medical image (file or DICOM directory)

    Raises:
        ValueError: If file is invalid or no medical image found
    """
    # Check extension
    suffix = upload_path.suffix.lower()
    if upload_path.name.endswith('.nii.gz'):
        suffix = '.nii.gz'

    if suffix not in VALID_EXTENSIONS:
        raise ValueError(
            f"Invalid file extension '{suffix}'. "
            f"Accepted formats: {', '.join(sorted(VALID_EXTENSIONS))}"
        )

    temp_dir.mkdir(parents=True, exist_ok=True)

    if suffix == '.zip':
        return _handle_zip(upload_path, temp_dir)
    else:
        return _validate_medical_image(upload_path)


def _handle_zip(zip_path: Path, extract_dir: Path) -> Path:
    """
    Extract zip and find medical image inside.

    Args:
        zip_path: Path to the zip file
        extract_dir: Directory to extract contents to

    Returns:
        Path to the medical image found in the zip

    Raises:
        ValueError: If zip is invalid or contains no medical images
    """
    try:
        with zipfile.ZipFile(zip_path, 'r') as zf:
            zf.extractall(extract_dir)
    except zipfile.BadZipFile as err:
        raise ValueError("Invalid or corrupted zip file") from err

    # Search for medical images in extracted contents
    medical_image = _find_medical_image(extract_dir)
    if not medical_image:
        raise ValueError(
            "No valid medical image found in zip file. "
            "Expected: .nii, .nii.gz, .nrrd, or DICOM series folder"
        )

    return medical_image


def _find_medical_image(directory: Path) -> Optional[Path]:
    """
    Recursively search for a medical image file or DICOM directory.

    Search order:
    1. NIfTI files (.nii.gz, .nii)
    2. NRRD files (.nrrd)
    3. DICOM directories (containing 10+ .dcm files)
    4. Single DICOM files (.dcm)

    Args:
        directory: Directory to search

    Returns:
        Path to the medical image, or None if not found
    """
    # First, look for NIfTI files (preferred)
    for pattern in ['*.nii.gz', '*.nii']:
        matches = list(directory.rglob(pattern))
        if matches:
            return matches[0]

    # Look for NRRD files
    nrrd_matches = list(directory.rglob('*.nrrd'))
    if nrrd_matches:
        return nrrd_matches[0]

    # Look for DICOM directories (folder with multiple .dcm files)
    for subdir in directory.rglob('*'):
        if subdir.is_dir() and _is_dicom_directory(subdir):
            return subdir

    # Check for single 3D DICOM file
    dcm_files = list(directory.rglob('*.dcm'))
    if dcm_files:
        return dcm_files[0]

    return None


def _is_dicom_directory(path: Path) -> bool:
    """
    Check if directory contains a DICOM series (multiple .dcm files).

    Requires at least 10 slices to be considered a valid 3D series.
    """
    if not path.is_dir():
        return False
    dcm_files = list(path.glob('*.dcm'))
    return len(dcm_files) >= 10


def _validate_medical_image(path: Path) -> Path:
    """
    Validate that path is a readable 3D medical image using SimpleITK.

    Args:
        path: Path to the image file or DICOM directory

    Returns:
        The input path if validation passes

    Raises:
        ValueError: If image cannot be read or is not 3D
    """
    try:
        import SimpleITK as sitk

        if path.is_dir():
            # DICOM series - folder with multiple slices
            reader = sitk.ImageSeriesReader()
            dicom_files = reader.GetGDCMSeriesFileNames(str(path))

            if not dicom_files:
                raise ValueError("No DICOM files found in directory")

            if len(dicom_files) < 10:
                raise ValueError(
                    f"DICOM series too short ({len(dicom_files)} slices). "
                    "Expected 3D volume with at least 10 slices."
                )

            # Try to read series info to validate
            reader.SetFileNames(dicom_files)
            reader.ReadImageInformation()

        else:
            # Single file (NIfTI, NRRD, or single 3D DICOM)
            reader = sitk.ImageFileReader()
            reader.SetFileName(str(path))
            reader.ReadImageInformation()

            # Check dimensions (should be 3D)
            dims = reader.GetDimension()
            if dims < 3:
                raise ValueError(
                    f"Image is {dims}D, expected 3D volume. "
                    "Please upload a 3D MRI scan."
                )

            # Check size is reasonable
            size = reader.GetSize()
            if any(s < 10 for s in size[:3]):
                raise ValueError(
                    f"Image dimensions too small: {size}. "
                    "Expected a full 3D MRI volume."
                )

        return path

    except ImportError as err:
        raise ValueError("SimpleITK not installed - cannot validate medical image") from err
    except Exception as e:
        if "ValueError" in type(e).__name__:
            raise
        raise ValueError(f"Failed to read medical image: {str(e)}") from e
