# Stage 1.1: Project Scaffolding & Backend Core

## Overview

**Goal**: Set up the project structure, dependencies, and a minimal running FastAPI application.

**Estimated Time**: ~30 minutes

**Deliverable**: A FastAPI app running on the GCP VM with a working `/health` endpoint.

---

## What This Stage Covers

1. **GCP VM Setup** - Create and configure a small VM instance for development
2. **Project Directory Structure** - Create all folders (backend/, frontend/, tests/, etc.)
3. **Python Environment** - Virtual environment, requirements.txt, install dependencies
4. **Configuration Module** - `backend/config.py` with pydantic-settings
5. **FastAPI Entry Point** - `backend/main.py` with basic app setup
6. **Health Endpoint** - `backend/routes/health.py` - verify the app runs
7. **Git Init** - Initialize repo, .gitignore, first commit

---

## Success Criteria

- [ ] GCP VM running with Python 3.10+ installed
- [ ] Can SSH into VM and navigate to project directory
- [ ] `uvicorn backend.main:app --reload` starts without errors
- [ ] `curl http://localhost:8000/health` returns a valid JSON response
- [ ] Project committed to git

---

## Detailed Steps

*(To be expanded)*
