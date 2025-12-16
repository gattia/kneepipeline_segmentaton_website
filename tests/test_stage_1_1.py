"""
Stage 1.1 Verification Tests

Run with: pytest -m stage_1_1 -v
"""
import pytest
from pathlib import Path
from fastapi.testclient import TestClient


# Mark all tests in this module as stage_1_1
pytestmark = pytest.mark.stage_1_1


class TestDirectoryStructure:
    """Verify required files and directories exist."""
    
    @pytest.fixture
    def project_root(self):
        """Get project root directory."""
        return Path(__file__).parent.parent
    
    def test_backend_init_exists(self, project_root):
        assert (project_root / "backend" / "__init__.py").exists()
    
    def test_backend_main_exists(self, project_root):
        assert (project_root / "backend" / "main.py").exists()
    
    def test_backend_config_exists(self, project_root):
        assert (project_root / "backend" / "config.py").exists()
    
    def test_backend_requirements_exists(self, project_root):
        assert (project_root / "backend" / "requirements.txt").exists()
    
    def test_routes_health_exists(self, project_root):
        assert (project_root / "backend" / "routes" / "health.py").exists()
    
    def test_frontend_directory_exists(self, project_root):
        assert (project_root / "frontend").is_dir()
    
    def test_tests_directory_exists(self, project_root):
        assert (project_root / "tests").is_dir()
    
    def test_gitignore_exists(self, project_root):
        assert (project_root / ".gitignore").exists()


class TestDependencies:
    """Verify all required dependencies are importable."""
    
    def test_fastapi_importable(self):
        import fastapi
        assert fastapi.__version__
    
    def test_uvicorn_importable(self):
        import uvicorn
        assert uvicorn
    
    def test_redis_importable(self):
        import redis
        assert redis.__version__
    
    def test_celery_importable(self):
        import celery
        assert celery.__version__
    
    def test_simpleitk_importable(self):
        import SimpleITK
        assert SimpleITK.Version_MajorVersion() >= 2
    
    def test_pydantic_settings_importable(self):
        import pydantic_settings
        assert pydantic_settings


class TestHealthEndpoint:
    """Verify the /health endpoint works correctly."""
    
    @pytest.fixture
    def client(self):
        """Create test client for the FastAPI app."""
        from backend.main import app
        return TestClient(app)
    
    def test_health_returns_200(self, client):
        """Health endpoint should return HTTP 200."""
        response = client.get("/health")
        assert response.status_code == 200
    
    def test_health_returns_json(self, client):
        """Health endpoint should return valid JSON."""
        response = client.get("/health")
        data = response.json()
        assert isinstance(data, dict)
    
    def test_health_has_required_fields(self, client):
        """Health response must contain required fields."""
        response = client.get("/health")
        data = response.json()
        
        required_fields = ["status", "redis", "worker", "timestamp"]
        for field in required_fields:
            assert field in data, f"Missing required field: {field}"
    
    def test_health_status_valid(self, client):
        """Status field must be 'healthy' or 'unhealthy'."""
        response = client.get("/health")
        data = response.json()
        assert data["status"] in ["healthy", "unhealthy"]


class TestAPIDocs:
    """Verify FastAPI auto-generated docs are accessible."""
    
    @pytest.fixture
    def client(self):
        from backend.main import app
        return TestClient(app)
    
    def test_docs_accessible(self, client):
        """OpenAPI docs should be accessible at /docs."""
        response = client.get("/docs")
        assert response.status_code == 200
    
    def test_openapi_json_accessible(self, client):
        """OpenAPI JSON schema should be accessible."""
        response = client.get("/openapi.json")
        assert response.status_code == 200
        assert "openapi" in response.json()


class TestGitIgnore:
    """Verify .gitignore has required patterns."""
    
    @pytest.fixture
    def gitignore_content(self):
        project_root = Path(__file__).parent.parent
        return (project_root / ".gitignore").read_text()
    
    def test_pycache_ignored(self, gitignore_content):
        assert "__pycache__" in gitignore_content
    
    def test_env_ignored(self, gitignore_content):
        assert ".env" in gitignore_content
    
    def test_data_dir_ignored(self, gitignore_content):
        # Should ignore data/ or data/* or similar
        assert "data" in gitignore_content.lower()
