"""
Stage 3.5 Verification Tests - Error Handling and Progress

Run with: pytest -m stage_3_5 -v

These tests verify:
1. Error parsing from pipeline output
2. Error code mapping
3. User-friendly error messages
4. Progress parsing
"""
import pytest

# Mark all tests in this module as stage_3_5
pytestmark = pytest.mark.stage_3_5


class TestErrorParsing:
    """Verify error parsing from pipeline output."""
    
    def test_parse_cuda_oom(self):
        """CUDA OOM should be detected."""
        from backend.services.error_handler import ErrorCode, parse_error_from_output
        
        output = "RuntimeError: CUDA out of memory. Tried to allocate 2.00 GiB"
        assert parse_error_from_output(output) == ErrorCode.GPU_OOM
    
    def test_parse_gpu_memory_error(self):
        """GPU memory error variations should be detected."""
        from backend.services.error_handler import ErrorCode, parse_error_from_output
        
        outputs = [
            "Out of memory error occurred",
            "CUDA error: out of memory",
            "GPU memory allocation failed",
        ]
        for output in outputs:
            assert parse_error_from_output(output) == ErrorCode.GPU_OOM
    
    def test_parse_file_not_found(self):
        """File not found should be detected."""
        from backend.services.error_handler import ErrorCode, parse_error_from_output
        
        output = "FileNotFoundError: Input file not found: /path/to/file"
        assert parse_error_from_output(output) == ErrorCode.FILE_NOT_FOUND
    
    def test_parse_dicom_error(self):
        """DICOM errors should be detected."""
        from backend.services.error_handler import ErrorCode, parse_error_from_output
        
        output = "Error reading DICOM series: No valid DICOM files found"
        assert parse_error_from_output(output) == ErrorCode.DICOM_ERROR
    
    def test_parse_segmentation_failed(self):
        """Segmentation failure should be detected."""
        from backend.services.error_handler import ErrorCode, parse_error_from_output
        
        output = "Segmentation failed: No valid labels produced"
        assert parse_error_from_output(output) == ErrorCode.SEGMENTATION_FAILED
    
    def test_parse_nsm_error(self):
        """NSM errors should be detected."""
        from backend.services.error_handler import ErrorCode, parse_error_from_output
        
        output = "NSM Error: Failed to fit shape model"
        assert parse_error_from_output(output) == ErrorCode.NSM_FAILED
    
    def test_parse_unknown_defaults_to_pipeline_error(self):
        """Unknown error should default to PIPELINE_ERROR."""
        from backend.services.error_handler import ErrorCode, parse_error_from_output
        
        output = "Some random unexpected error that doesn't match patterns"
        assert parse_error_from_output(output) == ErrorCode.PIPELINE_ERROR


class TestErrorResponses:
    """Verify error response formatting."""
    
    def test_error_response_has_required_fields(self):
        """Error response should have all required fields."""
        from backend.services.error_handler import ErrorCode, get_error_response
        
        response = get_error_response(ErrorCode.GPU_OOM)
        
        assert "error_code" in response
        assert "message" in response
        assert "recovery_hint" in response
    
    def test_error_response_includes_details(self):
        """Error response should include provided details."""
        from backend.services.error_handler import ErrorCode, get_error_response
        
        response = get_error_response(ErrorCode.GPU_OOM, "Technical: 15GB required, 12GB available")
        
        assert response["details"] == "Technical: 15GB required, 12GB available"
    
    def test_all_error_codes_have_messages(self):
        """All error codes should have user-friendly messages."""
        from backend.services.error_handler import ERROR_MESSAGES, ErrorCode
        
        for code in ErrorCode:
            assert code in ERROR_MESSAGES, f"Missing message for {code}"
            assert ERROR_MESSAGES[code].message, f"Empty message for {code}"
            assert ERROR_MESSAGES[code].recovery_hint, f"Empty recovery hint for {code}"


class TestProgressParsing:
    """Verify progress parsing from pipeline output."""
    
    def test_parse_segmentation_progress(self):
        """Segmentation step should be detected."""
        from backend.services.progress_parser import parse_progress_line
        
        progress = parse_progress_line("Running segmentation model...")
        
        assert progress is not None
        assert "segmentation" in progress.step_name.lower()
    
    def test_parse_mesh_generation(self):
        """Mesh generation should be detected."""
        from backend.services.progress_parser import parse_progress_line
        
        progress = parse_progress_line("Generating 3D mesh for femur...")
        
        assert progress is not None
        assert "mesh" in progress.step_name.lower()
    
    def test_parse_explicit_progress_marker(self):
        """Explicit [PROGRESS] markers should be parsed."""
        from backend.services.progress_parser import parse_progress_line
        
        progress = parse_progress_line("[PROGRESS] 5/10: Computing thickness")
        
        assert progress is not None
        assert progress.step == 5
        assert progress.total_steps == 10
        assert "thickness" in progress.step_name.lower()
    
    def test_parse_percentage(self):
        """Percentage markers should be parsed."""
        from backend.services.progress_parser import parse_progress_line
        
        progress = parse_progress_line("Processing... 45%")
        
        assert progress is not None
        assert progress.percent == 45
    
    def test_no_progress_in_random_line(self):
        """Random lines should not produce progress."""
        from backend.services.progress_parser import parse_progress_line
        
        progress = parse_progress_line("2024-01-15 10:30:45 INFO Loading configuration")
        
        # Should return None for non-progress lines
        assert progress is None
    
    def test_parse_loading_model(self):
        """Loading model should be detected."""
        from backend.services.progress_parser import parse_progress_line
        
        progress = parse_progress_line("Loading segmentation model from checkpoint...")
        
        assert progress is not None
        assert "loading" in progress.step_name.lower()
    
    def test_parse_preprocessing(self):
        """Preprocessing should be detected."""
        from backend.services.progress_parser import parse_progress_line
        
        progress = parse_progress_line("Preprocessing image data...")
        
        assert progress is not None
        assert "preprocessing" in progress.step_name.lower()


class TestTimeBasedProgress:
    """Verify time-based progress estimation."""
    
    def test_estimate_progress_from_time(self):
        """Time-based progress should be estimated correctly."""
        from backend.services.progress_parser import estimate_progress_from_time
        
        # 50% of estimated time
        progress = estimate_progress_from_time(150, 300)
        
        assert progress is not None
        assert progress.percent == 50
    
    def test_progress_capped_at_95(self):
        """Time-based progress should not exceed 95%."""
        from backend.services.progress_parser import estimate_progress_from_time
        
        # 200% of estimated time
        progress = estimate_progress_from_time(600, 300)
        
        assert progress is not None
        assert progress.percent <= 95
    
    def test_progress_with_zero_estimate(self):
        """Should handle zero estimated time."""
        from backend.services.progress_parser import estimate_progress_from_time
        
        progress = estimate_progress_from_time(10, 0)
        
        # Should use default 300 seconds
        assert progress is not None
        assert progress.percent >= 0


class TestFormatErrorForJob:
    """Verify error formatting for job storage."""
    
    def test_format_timeout_error(self):
        """Timeout error should format correctly."""
        from backend.services.error_handler import format_error_for_job
        
        error_code, message = format_error_for_job(TimeoutError("Pipeline timed out"))
        
        assert error_code == "TIMEOUT"
        assert "took longer" in message.lower()
    
    def test_format_memory_error(self):
        """Memory error should format correctly."""
        from backend.services.error_handler import format_error_for_job
        
        error_code, message = format_error_for_job(
            Exception("CUDA out of memory"),
            output="RuntimeError: CUDA out of memory"
        )
        
        assert error_code == "GPU_OOM"
        assert "gpu" in message.lower() or "memory" in message.lower()
    
    def test_format_file_not_found(self):
        """File not found error should format correctly."""
        from backend.services.error_handler import format_error_for_job
        
        error_code, message = format_error_for_job(
            FileNotFoundError("Input file not found")
        )
        
        assert error_code == "FILE_NOT_FOUND"
        assert "upload" in message.lower()
    
    def test_output_takes_priority(self):
        """Pipeline output should take priority over exception type."""
        from backend.services.error_handler import format_error_for_job
        
        # Exception is generic, but output is specific
        error_code, message = format_error_for_job(
            Exception("Something went wrong"),
            output="Segmentation failed: No valid labels"
        )
        
        assert error_code == "SEGMENTATION_FAILED"


class TestExceptionMapping:
    """Verify Python exception to error code mapping."""
    
    def test_map_timeout_exception(self):
        """TimeoutError should map to TIMEOUT code."""
        from backend.services.error_handler import _map_exception_to_code, ErrorCode
        
        assert _map_exception_to_code(TimeoutError("timed out")) == ErrorCode.TIMEOUT
    
    def test_map_file_not_found_exception(self):
        """FileNotFoundError should map to FILE_NOT_FOUND code."""
        from backend.services.error_handler import _map_exception_to_code, ErrorCode
        
        assert _map_exception_to_code(FileNotFoundError("/path/to/file")) == ErrorCode.FILE_NOT_FOUND
    
    def test_map_generic_exception(self):
        """Generic exception should map to PIPELINE_ERROR."""
        from backend.services.error_handler import _map_exception_to_code, ErrorCode
        
        assert _map_exception_to_code(ValueError("some error")) == ErrorCode.PIPELINE_ERROR
    
    def test_map_memory_error_in_message(self):
        """Exception with 'memory' in message should map to GPU_OOM."""
        from backend.services.error_handler import _map_exception_to_code, ErrorCode
        
        assert _map_exception_to_code(RuntimeError("out of memory")) == ErrorCode.GPU_OOM


class TestProgressUpdate:
    """Verify ProgressUpdate dataclass behavior."""
    
    def test_progress_update_fields(self):
        """ProgressUpdate should have all expected fields."""
        from backend.services.progress_parser import ProgressUpdate
        
        progress = ProgressUpdate(
            step=5,
            total_steps=10,
            step_name="Test step",
            percent=50,
            substep="Substep A"
        )
        
        assert progress.step == 5
        assert progress.total_steps == 10
        assert progress.step_name == "Test step"
        assert progress.percent == 50
        assert progress.substep == "Substep A"
    
    def test_progress_update_optional_substep(self):
        """Substep should be optional."""
        from backend.services.progress_parser import ProgressUpdate
        
        progress = ProgressUpdate(
            step=5,
            total_steps=10,
            step_name="Test step",
            percent=50
        )
        
        assert progress.substep is None


