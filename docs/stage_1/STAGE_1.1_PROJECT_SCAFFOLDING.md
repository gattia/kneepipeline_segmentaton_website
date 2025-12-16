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
- [ ] Project committed to git with proper .gitignore

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
