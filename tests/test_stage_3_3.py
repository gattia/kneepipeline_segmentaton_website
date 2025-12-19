"""
Stage 3.3 Verification Tests - Pipeline Worker Integration

Run with: pytest -m stage_3_3 -v

These tests verify:
1. Config generator creates valid configuration
2. Pipeline worker module structure
3. Model name mapping
4. Error code mapping
5. GPU cleanup functionality
"""
import json
import os
from pathlib import Path

import pytest

# Mark all tests in this module as stage_3_3
pytestmark = pytest.mark.stage_3_3


class TestConfigGenerator:
    """Verify config generator creates valid configuration."""

    def test_config_generator_importable(self):
        """Config generator should be importable."""
        from backend.services.config_generator import generate_pipeline_config
        assert generate_pipeline_config is not None

    def test_generate_config_creates_file(self, temp_dir):
        """generate_pipeline_config should create a config.json file."""
        from backend.services.config_generator import generate_pipeline_config

        # Skip if base config doesn't exist
        base_config = Path(os.path.expanduser("~/programming/kneepipeline/config.json"))
        if not base_config.exists():
            pytest.skip("Base config.json not found")

        config_path = generate_pipeline_config(
            job_dir=temp_dir,
            options={"segmentation_model": "nnunet_fullres"}
        )

        assert config_path.exists()
        assert config_path.name == "config.json"

    def test_generate_config_valid_json(self, temp_dir):
        """Generated config should be valid JSON."""
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

        assert isinstance(config, dict)
        assert "default_seg_model" in config

    def test_config_nsm_options_bone_and_cart(self, temp_dir):
        """Config should enable bone+cart NSM when selected."""
        from backend.services.config_generator import generate_pipeline_config

        base_config = Path(os.path.expanduser("~/programming/kneepipeline/config.json"))
        if not base_config.exists():
            pytest.skip("Base config.json not found")

        config_path = generate_pipeline_config(
            job_dir=temp_dir,
            options={
                "segmentation_model": "nnunet_fullres",
                "perform_nsm": True,
                "nsm_type": "bone_and_cart"
            }
        )

        with open(config_path) as f:
            config = json.load(f)

        assert config["perform_bone_and_cart_nsm"] is True
        assert config["perform_bone_only_nsm"] is False

    def test_config_nsm_options_both(self, temp_dir):
        """Config should enable both NSM types when 'both' selected."""
        from backend.services.config_generator import generate_pipeline_config

        base_config = Path(os.path.expanduser("~/programming/kneepipeline/config.json"))
        if not base_config.exists():
            pytest.skip("Base config.json not found")

        config_path = generate_pipeline_config(
            job_dir=temp_dir,
            options={
                "segmentation_model": "nnunet_fullres",
                "perform_nsm": True,
                "nsm_type": "both"
            }
        )

        with open(config_path) as f:
            config = json.load(f)

        assert config["perform_bone_and_cart_nsm"] is True
        assert config["perform_bone_only_nsm"] is True

    def test_config_nsm_disabled(self, temp_dir):
        """Config should disable NSM when perform_nsm is False."""
        from backend.services.config_generator import generate_pipeline_config

        base_config = Path(os.path.expanduser("~/programming/kneepipeline/config.json"))
        if not base_config.exists():
            pytest.skip("Base config.json not found")

        config_path = generate_pipeline_config(
            job_dir=temp_dir,
            options={
                "segmentation_model": "nnunet_fullres",
                "perform_nsm": False,
            }
        )

        with open(config_path) as f:
            config = json.load(f)

        assert config["perform_bone_and_cart_nsm"] is False
        assert config["perform_bone_only_nsm"] is False

    def test_config_cascade_model(self, temp_dir):
        """Config should set nnunet type to cascade when cascade model selected."""
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


class TestPipelineWorker:
    """Verify pipeline worker module structure."""

    def test_pipeline_worker_importable(self):
        """Pipeline worker should be importable."""
        from backend.workers.pipeline_worker import run_real_pipeline
        assert run_real_pipeline is not None

    def test_cleanup_gpu_memory_importable(self):
        """cleanup_gpu_memory should be importable."""
        from backend.workers.pipeline_worker import cleanup_gpu_memory
        assert cleanup_gpu_memory is not None

    def test_cleanup_gpu_memory_runs_without_error(self):
        """cleanup_gpu_memory should run without error."""
        from backend.workers.pipeline_worker import cleanup_gpu_memory
        # Should not raise even without GPU
        cleanup_gpu_memory()

    def test_pipeline_constants_defined(self):
        """Pipeline constants should be defined."""
        from backend.workers.pipeline_worker import (
            KNEEPIPELINE_PATH,
            PIPELINE_SCRIPT,
            PIPELINE_TIMEOUT_SECONDS,
        )
        assert KNEEPIPELINE_PATH is not None
        assert PIPELINE_SCRIPT is not None
        assert PIPELINE_TIMEOUT_SECONDS == 1800


class TestModelNameMapping:
    """Verify model name mapping works correctly."""

    def test_map_nnunet_fullres(self):
        """nnunet_fullres should map to nnunet_knee."""
        from backend.services.config_generator import _map_segmentation_model
        assert _map_segmentation_model("nnunet_fullres") == "nnunet_knee"

    def test_map_nnunet_cascade(self):
        """nnunet_cascade should map to nnunet_knee."""
        from backend.services.config_generator import _map_segmentation_model
        assert _map_segmentation_model("nnunet_cascade") == "nnunet_knee"

    def test_map_goyal_sagittal(self):
        """goyal_sagittal should map to itself."""
        from backend.services.config_generator import _map_segmentation_model
        assert _map_segmentation_model("goyal_sagittal") == "goyal_sagittal"

    def test_map_goyal_coronal(self):
        """goyal_coronal should map to itself."""
        from backend.services.config_generator import _map_segmentation_model
        assert _map_segmentation_model("goyal_coronal") == "goyal_coronal"

    def test_map_goyal_axial(self):
        """goyal_axial should map to itself."""
        from backend.services.config_generator import _map_segmentation_model
        assert _map_segmentation_model("goyal_axial") == "goyal_axial"

    def test_map_staple(self):
        """staple should map to itself."""
        from backend.services.config_generator import _map_segmentation_model
        assert _map_segmentation_model("staple") == "staple"

    def test_map_unknown_defaults_to_nnunet(self):
        """Unknown model should default to nnunet_knee."""
        from backend.services.config_generator import _map_segmentation_model
        assert _map_segmentation_model("unknown_model") == "nnunet_knee"


class TestPipelineWorkerModelMapping:
    """Verify model mapping in pipeline worker matches config generator."""

    def test_map_model_name_fullres(self):
        """nnunet_fullres should map to nnunet_knee."""
        from backend.workers.pipeline_worker import _map_model_name
        assert _map_model_name("nnunet_fullres") == "nnunet_knee"

    def test_map_model_name_cascade(self):
        """nnunet_cascade should map to nnunet_knee."""
        from backend.workers.pipeline_worker import _map_model_name
        assert _map_model_name("nnunet_cascade") == "nnunet_knee"

    def test_map_model_name_unknown(self):
        """Unknown model should default to nnunet_knee."""
        from backend.workers.pipeline_worker import _map_model_name
        assert _map_model_name("unknown") == "nnunet_knee"


class TestErrorCodeMapping:
    """Verify error code mapping via error_handler module."""

    def test_timeout_error_code(self):
        """Timeout should map to TIMEOUT code."""
        from backend.services.error_handler import _map_exception_to_code, ErrorCode
        assert _map_exception_to_code(TimeoutError("Pipeline timed out")) == ErrorCode.TIMEOUT

    def test_memory_error_code(self):
        """Memory error should map to GPU_OOM code."""
        from backend.services.error_handler import _map_exception_to_code, ErrorCode
        assert _map_exception_to_code(Exception("CUDA out of memory")) == ErrorCode.GPU_OOM
        assert _map_exception_to_code(Exception("OOM error")) == ErrorCode.GPU_OOM

    def test_file_not_found_code(self):
        """File not found should map to FILE_NOT_FOUND code."""
        from backend.services.error_handler import _map_exception_to_code, ErrorCode
        assert _map_exception_to_code(FileNotFoundError("File not found")) == ErrorCode.FILE_NOT_FOUND

    def test_format_error_code(self):
        """Format error should map to INVALID_FORMAT code."""
        from backend.services.error_handler import _map_exception_to_code, ErrorCode
        assert _map_exception_to_code(Exception("Invalid format")) == ErrorCode.INVALID_FORMAT

    def test_dicom_error_code(self):
        """DICOM error should map to DICOM_ERROR code (via parse_error_from_output)."""
        from backend.services.error_handler import parse_error_from_output, ErrorCode
        # DICOM errors are detected through output parsing, not exception mapping
        assert parse_error_from_output("DICOM parsing failed") == ErrorCode.DICOM_ERROR

    def test_unknown_error_code(self):
        """Unknown error should map to PIPELINE_ERROR code."""
        from backend.services.error_handler import _map_exception_to_code, ErrorCode
        assert _map_exception_to_code(Exception("Something went wrong")) == ErrorCode.PIPELINE_ERROR


class TestTaskConfiguration:
    """Verify task configuration options."""

    def test_should_use_real_pipeline_default(self):
        """Should use real pipeline by default."""
        from backend.workers.tasks import _should_use_real_pipeline

        # Save current env value
        original = os.environ.get("USE_DUMMY_PIPELINE")

        # Ensure env var is not set
        if "USE_DUMMY_PIPELINE" in os.environ:
            del os.environ["USE_DUMMY_PIPELINE"]

        try:
            assert _should_use_real_pipeline({}) is True
        finally:
            # Restore original value
            if original is not None:
                os.environ["USE_DUMMY_PIPELINE"] = original

    def test_should_use_dummy_pipeline_when_env_set(self):
        """Should use dummy pipeline when env var is set."""
        from backend.workers.tasks import _should_use_real_pipeline

        # Save current env value
        original = os.environ.get("USE_DUMMY_PIPELINE")

        try:
            os.environ["USE_DUMMY_PIPELINE"] = "1"
            assert _should_use_real_pipeline({}) is False
        finally:
            # Restore original value
            if original is not None:
                os.environ["USE_DUMMY_PIPELINE"] = original
            elif "USE_DUMMY_PIPELINE" in os.environ:
                del os.environ["USE_DUMMY_PIPELINE"]


class TestServicesExports:
    """Verify services package exports config_generator functions."""

    def test_generate_pipeline_config_exported(self):
        """generate_pipeline_config should be exported from services package."""
        from backend.services import generate_pipeline_config
        assert generate_pipeline_config is not None

    def test_get_pipeline_script_path_exported(self):
        """get_pipeline_script_path should be exported from services package."""
        from backend.services import get_pipeline_script_path
        assert get_pipeline_script_path is not None

    def test_get_base_config_path_exported(self):
        """get_base_config_path should be exported from services package."""
        from backend.services import get_base_config_path
        assert get_base_config_path is not None


class TestPipelineErrorParsing:
    """Verify pipeline error parsing produces user-friendly messages."""

    def test_parse_oom_error(self):
        """OOM errors should produce user-friendly message."""
        from backend.workers.pipeline_worker import _parse_pipeline_error
        result = _parse_pipeline_error("CUDA out of memory. Tried to allocate...")
        assert "GPU ran out of memory" in result

    def test_parse_file_not_found_error(self):
        """File not found errors should produce user-friendly message."""
        from backend.workers.pipeline_worker import _parse_pipeline_error
        result = _parse_pipeline_error("FileNotFoundError: No such file or directory")
        assert "could not be read" in result

    def test_parse_permission_error(self):
        """Permission errors should produce user-friendly message."""
        from backend.workers.pipeline_worker import _parse_pipeline_error
        result = _parse_pipeline_error("PermissionError: Permission denied")
        assert "Permission denied" in result

    def test_parse_unknown_error(self):
        """Unknown errors should return last line (lowercased)."""
        from backend.workers.pipeline_worker import _parse_pipeline_error
        result = _parse_pipeline_error("Line 1\nLine 2\nActual error message")
        # Note: _parse_pipeline_error lowercases the input for matching
        assert "actual error message" in result


class TestOutputVerification:
    """Verify pipeline output verification logic."""

    def test_verify_outputs_with_nifti(self, temp_dir):
        """Should return True when NIfTI files exist."""
        from backend.workers.pipeline_worker import _verify_pipeline_outputs

        # Create a dummy NIfTI file
        (temp_dir / "output.nii.gz").touch()

        assert _verify_pipeline_outputs(temp_dir) is True

    def test_verify_outputs_with_nrrd(self, temp_dir):
        """Should return True when NRRD files exist."""
        from backend.workers.pipeline_worker import _verify_pipeline_outputs

        # Create a dummy NRRD file
        (temp_dir / "output.nrrd").touch()

        assert _verify_pipeline_outputs(temp_dir) is True

    def test_verify_outputs_with_seg_file(self, temp_dir):
        """Should return True when segmentation files exist."""
        from backend.workers.pipeline_worker import _verify_pipeline_outputs

        # Create a dummy segmentation file
        (temp_dir / "test_seg_output.nii.gz").touch()

        assert _verify_pipeline_outputs(temp_dir) is True

    def test_verify_outputs_with_json(self, temp_dir):
        """Should return True when JSON result files exist."""
        from backend.workers.pipeline_worker import _verify_pipeline_outputs

        # Create a dummy JSON file
        (temp_dir / "results.json").touch()

        assert _verify_pipeline_outputs(temp_dir) is True

    def test_verify_outputs_empty_dir(self, temp_dir):
        """Should return False when directory is empty."""
        from backend.workers.pipeline_worker import _verify_pipeline_outputs

        assert _verify_pipeline_outputs(temp_dir) is False


