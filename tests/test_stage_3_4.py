"""
Stage 3.4 Verification Tests - Configuration Mapping

Run with: pytest -m stage_3_4 -v

These tests verify:
1. Option validation works correctly
2. All models map correctly
3. NSM type combinations work
4. Invalid options are rejected
5. Upload route accepts new options
6. /models endpoint returns available options
"""
import json
import os
from pathlib import Path

import pytest

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

    def test_valid_staple_model(self):
        """STAPLE ensemble model should be valid."""
        from backend.services.config_generator import validate_options

        validate_options({"segmentation_model": "staple"})

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

    def test_valid_cartilage_smoothing_min(self):
        """Minimum smoothing value should pass."""
        from backend.services.config_generator import validate_options

        validate_options({"cartilage_smoothing": 0.0})

    def test_valid_cartilage_smoothing_mid(self):
        """Middle smoothing value should pass."""
        from backend.services.config_generator import validate_options

        validate_options({"cartilage_smoothing": 1.0})

    def test_valid_cartilage_smoothing_max(self):
        """Maximum smoothing value should pass."""
        from backend.services.config_generator import validate_options

        validate_options({"cartilage_smoothing": 2.0})

    def test_invalid_cartilage_smoothing_negative(self):
        """Negative smoothing should raise error."""
        from backend.services.config_generator import ConfigValidationError, validate_options

        with pytest.raises(ConfigValidationError):
            validate_options({"cartilage_smoothing": -0.1})

    def test_invalid_cartilage_smoothing_too_high(self):
        """Smoothing above 2.0 should raise error."""
        from backend.services.config_generator import ConfigValidationError, validate_options

        with pytest.raises(ConfigValidationError):
            validate_options({"cartilage_smoothing": 2.1})

    def test_cartilage_smoothing_none_is_valid(self):
        """None value for cartilage_smoothing should pass (uses default)."""
        from backend.services.config_generator import validate_options

        validate_options({"cartilage_smoothing": None})

    def test_valid_batch_size_min(self):
        """Minimum batch size should pass."""
        from backend.services.config_generator import validate_options

        validate_options({"batch_size": 1})

    def test_valid_batch_size_default(self):
        """Default batch size (32) should pass."""
        from backend.services.config_generator import validate_options

        validate_options({"batch_size": 32})

    def test_valid_batch_size_max(self):
        """Maximum batch size should pass."""
        from backend.services.config_generator import validate_options

        validate_options({"batch_size": 64})

    def test_invalid_batch_size_zero(self):
        """Zero batch size should raise error."""
        from backend.services.config_generator import ConfigValidationError, validate_options

        with pytest.raises(ConfigValidationError):
            validate_options({"batch_size": 0})

    def test_invalid_batch_size_too_high(self):
        """Batch size above 64 should raise error."""
        from backend.services.config_generator import ConfigValidationError, validate_options

        with pytest.raises(ConfigValidationError):
            validate_options({"batch_size": 65})

    def test_batch_size_none_is_valid(self):
        """None value for batch_size should pass (uses default)."""
        from backend.services.config_generator import validate_options

        validate_options({"batch_size": None})

    def test_combined_valid_options(self):
        """All options combined should validate."""
        from backend.services.config_generator import validate_options

        validate_options(
            {
                "segmentation_model": "nnunet_cascade",
                "nsm_type": "both",
                "cartilage_smoothing": 1.0,
                "batch_size": 16,
            }
        )


class TestConfigGeneration:
    """Verify config generation with different options."""

    def test_cascade_sets_nnunet_type(self, temp_dir):
        """nnunet_cascade should set nnunet.type to cascade."""
        from backend.services.config_generator import generate_pipeline_config

        base_config = Path(os.path.expanduser("~/programming/kneepipeline/config.json"))
        if not base_config.exists():
            pytest.skip("Base config.json not found")

        config_path = generate_pipeline_config(
            job_dir=temp_dir, options={"segmentation_model": "nnunet_cascade"}
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
            job_dir=temp_dir, options={"segmentation_model": "nnunet_fullres"}
        )

        with open(config_path) as f:
            config = json.load(f)

        assert config["nnunet"]["type"] == "fullres"

    def test_nsm_bone_and_cart_mapping(self, temp_dir):
        """nsm_type=bone_and_cart should enable only bone_and_cart NSM."""
        from backend.services.config_generator import generate_pipeline_config

        base_config = Path(os.path.expanduser("~/programming/kneepipeline/config.json"))
        if not base_config.exists():
            pytest.skip("Base config.json not found")

        config_path = generate_pipeline_config(
            job_dir=temp_dir, options={"perform_nsm": True, "nsm_type": "bone_and_cart"}
        )

        with open(config_path) as f:
            config = json.load(f)

        assert config["perform_bone_and_cart_nsm"] is True
        assert config["perform_bone_only_nsm"] is False

    def test_nsm_bone_only_mapping(self, temp_dir):
        """nsm_type=bone_only should enable only bone_only NSM."""
        from backend.services.config_generator import generate_pipeline_config

        base_config = Path(os.path.expanduser("~/programming/kneepipeline/config.json"))
        if not base_config.exists():
            pytest.skip("Base config.json not found")

        config_path = generate_pipeline_config(
            job_dir=temp_dir, options={"perform_nsm": True, "nsm_type": "bone_only"}
        )

        with open(config_path) as f:
            config = json.load(f)

        assert config["perform_bone_and_cart_nsm"] is False
        assert config["perform_bone_only_nsm"] is True

    def test_nsm_both_mapping(self, temp_dir):
        """nsm_type=both should enable both NSM analyses."""
        from backend.services.config_generator import generate_pipeline_config

        base_config = Path(os.path.expanduser("~/programming/kneepipeline/config.json"))
        if not base_config.exists():
            pytest.skip("Base config.json not found")

        config_path = generate_pipeline_config(
            job_dir=temp_dir, options={"perform_nsm": True, "nsm_type": "both"}
        )

        with open(config_path) as f:
            config = json.load(f)

        assert config["perform_bone_and_cart_nsm"] is True
        assert config["perform_bone_only_nsm"] is True

    def test_nsm_none_disables_both(self, temp_dir):
        """nsm_type=none should disable both NSM analyses."""
        from backend.services.config_generator import generate_pipeline_config

        base_config = Path(os.path.expanduser("~/programming/kneepipeline/config.json"))
        if not base_config.exists():
            pytest.skip("Base config.json not found")

        config_path = generate_pipeline_config(
            job_dir=temp_dir, options={"perform_nsm": True, "nsm_type": "none"}
        )

        with open(config_path) as f:
            config = json.load(f)

        assert config["perform_bone_and_cart_nsm"] is False
        assert config["perform_bone_only_nsm"] is False

    def test_perform_nsm_false_disables_all(self, temp_dir):
        """perform_nsm=False should disable both NSM analyses regardless of nsm_type."""
        from backend.services.config_generator import generate_pipeline_config

        base_config = Path(os.path.expanduser("~/programming/kneepipeline/config.json"))
        if not base_config.exists():
            pytest.skip("Base config.json not found")

        config_path = generate_pipeline_config(
            job_dir=temp_dir, options={"perform_nsm": False, "nsm_type": "both"}
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
            job_dir=temp_dir, options={"cartilage_smoothing": 1.5}
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

        config_path = generate_pipeline_config(job_dir=temp_dir, options={"batch_size": 16})

        with open(config_path) as f:
            config = json.load(f)

        assert config["batch_size"] == 16

    def test_clip_femur_top_true(self, temp_dir):
        """clip_femur_top=True should be applied."""
        from backend.services.config_generator import generate_pipeline_config

        base_config = Path(os.path.expanduser("~/programming/kneepipeline/config.json"))
        if not base_config.exists():
            pytest.skip("Base config.json not found")

        config_path = generate_pipeline_config(
            job_dir=temp_dir, options={"clip_femur_top": True}
        )

        with open(config_path) as f:
            config = json.load(f)

        assert config["clip_femur_top"] is True

    def test_clip_femur_top_false(self, temp_dir):
        """clip_femur_top=False should be applied."""
        from backend.services.config_generator import generate_pipeline_config

        base_config = Path(os.path.expanduser("~/programming/kneepipeline/config.json"))
        if not base_config.exists():
            pytest.skip("Base config.json not found")

        config_path = generate_pipeline_config(
            job_dir=temp_dir, options={"clip_femur_top": False}
        )

        with open(config_path) as f:
            config = json.load(f)

        assert config["clip_femur_top"] is False

    def test_none_options_not_applied(self, temp_dir):
        """None values for optional options should not override base config."""
        from backend.services.config_generator import generate_pipeline_config

        base_config = Path(os.path.expanduser("~/programming/kneepipeline/config.json"))
        if not base_config.exists():
            pytest.skip("Base config.json not found")

        # Get base config values
        with open(base_config) as f:
            original_config = json.load(f)

        original_smoothing = original_config.get("image_smooth_var_cart")
        original_batch = original_config.get("batch_size")

        config_path = generate_pipeline_config(
            job_dir=temp_dir, options={"cartilage_smoothing": None, "batch_size": None}
        )

        with open(config_path) as f:
            config = json.load(f)

        # None values should leave original values unchanged
        assert config.get("image_smooth_var_cart") == original_smoothing
        assert config.get("batch_size") == original_batch


class TestAvailableOptions:
    """Verify option listing functions."""

    def test_get_available_models(self):
        """Should return list of valid models."""
        from backend.services.config_generator import get_available_models

        models = get_available_models()
        assert "nnunet_fullres" in models
        assert "nnunet_cascade" in models
        assert "goyal_sagittal" in models
        assert "goyal_coronal" in models
        assert "goyal_axial" in models
        assert "staple" in models

    def test_get_available_nsm_types(self):
        """Should return list of valid NSM types."""
        from backend.services.config_generator import get_available_nsm_types

        types = get_available_nsm_types()
        assert "bone_and_cart" in types
        assert "bone_only" in types
        assert "both" in types
        assert "none" in types

    def test_valid_seg_models_constant(self):
        """VALID_SEG_MODELS should contain all expected models."""
        from backend.services.config_generator import VALID_SEG_MODELS

        expected = [
            "nnunet_fullres",
            "nnunet_cascade",
            "goyal_sagittal",
            "goyal_coronal",
            "goyal_axial",
            "staple",
        ]
        assert VALID_SEG_MODELS == expected

    def test_valid_nsm_types_constant(self):
        """VALID_NSM_TYPES should contain all expected types."""
        from backend.services.config_generator import VALID_NSM_TYPES

        expected = ["bone_and_cart", "bone_only", "both", "none"]
        assert VALID_NSM_TYPES == expected


class TestModelMapping:
    """Verify model name mapping."""

    def test_nnunet_fullres_maps_to_nnunet_knee(self):
        """nnunet_fullres should map to nnunet_knee."""
        from backend.services.config_generator import _map_segmentation_model

        assert _map_segmentation_model("nnunet_fullres") == "nnunet_knee"

    def test_nnunet_cascade_maps_to_nnunet_knee(self):
        """nnunet_cascade should map to nnunet_knee."""
        from backend.services.config_generator import _map_segmentation_model

        assert _map_segmentation_model("nnunet_cascade") == "nnunet_knee"

    def test_goyal_models_map_directly(self):
        """DOSMA goyal models should map directly."""
        from backend.services.config_generator import _map_segmentation_model

        assert _map_segmentation_model("goyal_sagittal") == "goyal_sagittal"
        assert _map_segmentation_model("goyal_coronal") == "goyal_coronal"
        assert _map_segmentation_model("goyal_axial") == "goyal_axial"

    def test_staple_maps_directly(self):
        """STAPLE should map directly."""
        from backend.services.config_generator import _map_segmentation_model

        assert _map_segmentation_model("staple") == "staple"

    def test_unknown_model_defaults_to_nnunet_knee(self):
        """Unknown models should default to nnunet_knee."""
        from backend.services.config_generator import _map_segmentation_model

        assert _map_segmentation_model("unknown") == "nnunet_knee"


class TestConfigValidationError:
    """Verify ConfigValidationError behavior."""

    def test_is_value_error_subclass(self):
        """ConfigValidationError should be a ValueError subclass."""
        from backend.services.config_generator import ConfigValidationError

        assert issubclass(ConfigValidationError, ValueError)

    def test_can_be_raised_with_message(self):
        """ConfigValidationError should carry a message."""
        from backend.services.config_generator import ConfigValidationError

        error = ConfigValidationError("test message")
        assert str(error) == "test message"


class TestUploadRouteModels:
    """Test the /models endpoint."""

    def test_models_endpoint_returns_segmentation_models(self):
        """GET /models should return segmentation models."""
        from fastapi.testclient import TestClient

        from backend.main import app

        client = TestClient(app)
        response = client.get("/models")

        assert response.status_code == 200
        data = response.json()
        assert "segmentation_models" in data
        assert "nnunet_fullres" in data["segmentation_models"]

    def test_models_endpoint_returns_nsm_types(self):
        """GET /models should return NSM types."""
        from fastapi.testclient import TestClient

        from backend.main import app

        client = TestClient(app)
        response = client.get("/models")

        assert response.status_code == 200
        data = response.json()
        assert "nsm_types" in data
        assert "bone_and_cart" in data["nsm_types"]
        assert "none" in data["nsm_types"]

    def test_models_endpoint_returns_defaults(self):
        """GET /models should return default values."""
        from fastapi.testclient import TestClient

        from backend.main import app

        client = TestClient(app)
        response = client.get("/models")

        assert response.status_code == 200
        data = response.json()
        assert "defaults" in data
        assert data["defaults"]["segmentation_model"] == "nnunet_fullres"
        assert data["defaults"]["perform_nsm"] is True
        assert data["defaults"]["nsm_type"] == "bone_and_cart"
        assert data["defaults"]["clip_femur_top"] is True

    def test_models_endpoint_returns_ranges(self):
        """GET /models should return valid ranges."""
        from fastapi.testclient import TestClient

        from backend.main import app

        client = TestClient(app)
        response = client.get("/models")

        assert response.status_code == 200
        data = response.json()
        assert "ranges" in data
        assert data["ranges"]["cartilage_smoothing"]["min"] == 0.0
        assert data["ranges"]["cartilage_smoothing"]["max"] == 2.0
        assert data["ranges"]["batch_size"]["min"] == 1
        assert data["ranges"]["batch_size"]["max"] == 64


class TestSchemaValidation:
    """Test Pydantic schema validation."""

    def test_upload_options_valid(self):
        """Valid UploadOptions should be accepted."""
        from backend.models.schemas import UploadOptions

        options = UploadOptions(
            segmentation_model="nnunet_cascade",
            perform_nsm=True,
            nsm_type="both",
            cartilage_smoothing=1.5,
            batch_size=16,
            clip_femur_top=False,
        )
        assert options.segmentation_model == "nnunet_cascade"
        assert options.batch_size == 16

    def test_upload_options_defaults(self):
        """UploadOptions should have correct defaults."""
        from backend.models.schemas import UploadOptions

        options = UploadOptions()
        assert options.segmentation_model == "nnunet_fullres"
        assert options.perform_nsm is True
        assert options.nsm_type == "bone_and_cart"
        assert options.cartilage_smoothing is None
        assert options.batch_size is None
        assert options.clip_femur_top is True

    def test_upload_options_nsm_type_none(self):
        """UploadOptions should accept nsm_type='none'."""
        from backend.models.schemas import UploadOptions

        options = UploadOptions(nsm_type="none")
        assert options.nsm_type == "none"

    def test_upload_options_invalid_model_rejected(self):
        """Invalid segmentation_model should be rejected."""
        from pydantic import ValidationError

        from backend.models.schemas import UploadOptions

        with pytest.raises(ValidationError):
            UploadOptions(segmentation_model="invalid_model")

    def test_upload_options_invalid_nsm_type_rejected(self):
        """Invalid nsm_type should be rejected."""
        from pydantic import ValidationError

        from backend.models.schemas import UploadOptions

        with pytest.raises(ValidationError):
            UploadOptions(nsm_type="invalid_type")

    def test_upload_options_cartilage_smoothing_range(self):
        """cartilage_smoothing should be validated for range 0.0-2.0."""
        from pydantic import ValidationError

        from backend.models.schemas import UploadOptions

        # Valid values
        UploadOptions(cartilage_smoothing=0.0)
        UploadOptions(cartilage_smoothing=2.0)

        # Invalid values
        with pytest.raises(ValidationError):
            UploadOptions(cartilage_smoothing=-0.1)
        with pytest.raises(ValidationError):
            UploadOptions(cartilage_smoothing=2.1)

    def test_upload_options_batch_size_range(self):
        """batch_size should be validated for range 1-64."""
        from pydantic import ValidationError

        from backend.models.schemas import UploadOptions

        # Valid values
        UploadOptions(batch_size=1)
        UploadOptions(batch_size=64)

        # Invalid values
        with pytest.raises(ValidationError):
            UploadOptions(batch_size=0)
        with pytest.raises(ValidationError):
            UploadOptions(batch_size=65)


