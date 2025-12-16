# Stage 1.1: Project Scaffolding & Backend Core

## Overview

**Goal**: Set up the project structure, dependencies, and a minimal running FastAPI application.

**Estimated Time**: ~30 minutes

**Deliverable**: A FastAPI app running on the GCP VM with a working `/health` endpoint.

---

## Prerequisites

**Stage 0 must be complete.** You should have:
- ✅ Miniconda installed with `kneepipeline` environment (Python 3.10)
- ✅ Docker running with Redis on port 6379
- ✅ Build tools (gcc, etc.)

See [STAGE_0_DEV_ENVIRONMENT.md](../STAGE_0_DEV_ENVIRONMENT.md) if not complete.

---

## What This Stage Covers

1. **Project Directory Structure** - Create all folders (backend/, frontend/, tests/, etc.)
2. **Python Dependencies** - requirements.txt, install with pip in conda env
3. **Configuration Module** - `backend/config.py` with pydantic-settings
4. **FastAPI Entry Point** - `backend/main.py` with basic app setup
5. **Health Endpoint** - `backend/routes/health.py` - verify the app runs
6. **Git Setup** - .gitignore, .env.example, first commit

---

## Success Criteria

- [ ] Project directory structure created
- [ ] `conda activate kneepipeline && pip install -r backend/requirements.txt` succeeds
- [ ] `uvicorn backend.main:app --reload` starts without errors
- [ ] `curl http://localhost:8000/health` returns a valid JSON response
- [ ] `pytest -m stage_1_1` passes all tests
- [ ] Project committed to git with proper .gitignore

---

## Verification: pytest Tests

Run the Stage 1.1 tests to verify completion:

```bash
conda activate kneepipeline
cd ~/programming/kneepipeline_segmentaton_website
pytest -m stage_1_1 -v
```

**Expected:** All tests pass.

### Tests to Create: `tests/test_stage_1_1.py`

This test file verifies Stage 1.1 is complete:

```python
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
```

### pytest Configuration

Add to `pyproject.toml`:

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
markers = [
    "stage_1_1: Stage 1.1 - Project Scaffolding",
    "stage_1_2: Stage 1.2 - Models & Services",
    "stage_1_3: Stage 1.3 - Redis + Celery",
    "stage_1_4: Stage 1.4 - API Routes",
    "stage_1_5: Stage 1.5 - Frontend",
    "stage_1_6: Stage 1.6 - Docker & Deployment",
]
asyncio_mode = "auto"
addopts = "-v --tb=short"
```

---

## Expected Final State

After completing Stage 1.1, your project should have this structure:

```
kneepipeline_segmentaton_website/
├── .gitignore
├── .env.example
├── pyproject.toml           # pytest configuration
├── backend/
│   ├── __init__.py
│   ├── main.py              # FastAPI app entry point
│   ├── config.py            # Settings with pydantic-settings
│   ├── requirements.txt
│   ├── routes/
│   │   ├── __init__.py
│   │   └── health.py        # GET /health endpoint
│   ├── services/
│   │   └── __init__.py
│   ├── workers/
│   │   └── __init__.py
│   └── models/
│       └── __init__.py
├── frontend/
│   ├── css/
│   ├── js/
│   └── assets/
├── tests/
│   ├── __init__.py
│   └── test_stage_1_1.py    # Stage 1.1 verification tests
└── data/                    # gitignored
    ├── uploads/
    ├── temp/
    ├── logs/
    └── results/
```

---

## Detailed Steps

### Step 1: Create Directory Structure

```bash
cd ~/programming/kneepipeline_segmentaton_website

# Create backend structure
mkdir -p backend/{routes,services,workers,models}
touch backend/__init__.py
touch backend/routes/__init__.py
touch backend/services/__init__.py
touch backend/workers/__init__.py
touch backend/models/__init__.py

# Create frontend structure
mkdir -p frontend/{css,js,assets}

# Create data directories (gitignored)
mkdir -p data/{uploads,temp,logs,results}

# Create tests directory
mkdir -p tests
touch tests/__init__.py

# Create GitHub Actions directory
mkdir -p .github/workflows
```

### Step 2: Create requirements.txt

Create `backend/requirements.txt`:

```txt
# Web Framework
fastapi==0.109.0
uvicorn[standard]==0.27.0
python-multipart==0.0.6

# Job Queue
celery==5.3.4
redis==5.0.1

# Medical Image Handling
SimpleITK==2.3.1

# Utilities
pydantic==2.5.3
pydantic-settings==2.1.0
python-dotenv==1.0.0

# Development & Testing
pytest==7.4.4
httpx==0.26.0
pytest-asyncio==0.23.3
pytest-cov==4.1.0
ruff==0.1.11
```

### Step 3: Install Dependencies

```bash
conda activate kneepipeline
cd ~/programming/kneepipeline_segmentaton_website
pip install -r backend/requirements.txt
```

### Step 4: Create Configuration Files

See [STAGE_1_DETAILED_PLAN.md](../STAGE_1_DETAILED_PLAN.md) for:
- `backend/config.py` - Settings class with pydantic-settings
- `.env.example` - Environment variable template
- `.gitignore` - Ignore patterns

### Step 5: Create FastAPI App and Health Endpoint

See [STAGE_1_DETAILED_PLAN.md](../STAGE_1_DETAILED_PLAN.md) for:
- `backend/main.py` - FastAPI app entry point
- `backend/routes/health.py` - Health check endpoint

### Step 6: Test the Application

```bash
conda activate kneepipeline
cd ~/programming/kneepipeline_segmentaton_website
uvicorn backend.main:app --reload --port 8000

# In another terminal:
curl http://localhost:8000/health
```

### Step 7: Git Commit

```bash
git add .
git commit -m "Stage 1.1: Project scaffolding and health endpoint"
```
