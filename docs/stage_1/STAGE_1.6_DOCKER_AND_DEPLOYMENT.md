# Stage 1.6: Docker & GCP Deployment

## Overview

**Goal**: Containerize the application with Docker and deploy on GCP VM accessible via public IP.

**Estimated Time**: ~60 minutes

**Deliverable**: Production-ready deployment accessible via public IP, with CI/CD pipeline.

---

## Prerequisites

- ✅ Stage 1.5 complete (all 108 tests passing)
- ✅ GCP VM running with external IP
- ✅ Docker installed on GCP VM

---

## Task Summary

| Task | Type | Description |
|------|------|-------------|
| 1.6.1 | AI Agent | Create `docker/Dockerfile` |
| 1.6.2 | AI Agent | Create `docker/docker-compose.yml` |
| 1.6.3 | AI Agent | Create `docker/.env.example` |
| 1.6.4 | AI Agent | Create `.dockerignore` |
| 1.6.5 | AI Agent | Create GitHub Actions workflows |
| 1.6.6 | AI Agent | Create `tests/test_stage_1_6.py` |
| 1.6.7 | **HUMAN** | Configure GCP firewall rules |
| 1.6.8 | Mixed | Deploy and verify |

---

## 1.6.1: Create Dockerfile

**File**: `docker/Dockerfile`

**Requirements**:
- Python 3.10 slim base image (no GPU for Stage 1)
- Install system dependencies (gcc)
- Copy `backend/requirements.txt` and install with pip
- Copy `backend/` and `frontend/` directories
- Create data directories: `/app/data/uploads`, `/app/data/temp`, `/app/data/results`, `/app/data/logs`
- Expose port 8000
- Default CMD: `uvicorn backend.main:app --host 0.0.0.0 --port 8000`

**Verification**:
```bash
docker build -f docker/Dockerfile -t knee-pipeline:test .
```

---

## 1.6.2: Create docker-compose.yml

**File**: `docker/docker-compose.yml`

Define three services:

### redis service
- Image: `redis:7-alpine`
- Container name: `knee-pipeline-redis`
- Ports: `6379:6379`
- Volume: `redis_data:/data`
- Command: `redis-server --appendonly yes`
- Healthcheck: `redis-cli ping`
- Restart: `unless-stopped`

### web service
- Build from `../` with `docker/Dockerfile`
- Container name: `knee-pipeline-web`
- Ports: `8000:8000`
- Volume: `app_data:/app/data`
- Depends on: redis (healthy)
- Environment: `REDIS_URL=redis://redis:6379/0`, `DEBUG=false`
- env_file: `.env`
- Restart: `unless-stopped`

### worker service
- Same build as web
- Container name: `knee-pipeline-worker`
- Command: `celery -A backend.workers.celery_app worker --loglevel=info --concurrency=1`
- Volume: `app_data:/app/data`
- Depends on: redis (healthy)
- Environment: `REDIS_URL=redis://redis:6379/0`
- env_file: `.env`
- Restart: `unless-stopped`

### volumes
- `redis_data` (named: `knee-pipeline-redis-data`)
- `app_data` (named: `knee-pipeline-app-data`)

**Verification**:
```bash
cd docker && docker-compose config
```

---

## 1.6.3: Create Environment Template

**File**: `docker/.env.example`

```bash
# Copy to docker/.env and customize
DEBUG=false
MAX_UPLOAD_SIZE_MB=600
RESULTS_EXPIRY_HOURS=24
```

Also ensure `docker/.env` is in `.gitignore`.

---

## 1.6.4: Create .dockerignore

**File**: `.dockerignore` (in project root)

Exclude:
- `.git`, `docs/`, `*.md` (except README.md)
- `.env` files, `__pycache__/`, `tests/`
- `data/`, `docker/`, `.github/`
- IDE files (`.vscode/`, `.idea/`)

---

## 1.6.5: Create GitHub Actions Workflows

### File: `.github/workflows/test.yml`

Triggers: push/PR to main, develop

Jobs:
1. **lint**: Run `ruff check backend/ tests/`
2. **test**: Redis service, install deps, run `pytest tests/ -v`

### File: `.github/workflows/docker-build.yml`

Triggers: push to main, PR to main

Build Docker image with caching, push: false

---

## 1.6.6: Create Tests

**File**: `tests/test_stage_1_6.py`

Mark all tests with `pytestmark = pytest.mark.stage_1_6`

### TestDockerConfiguration
- `test_dockerfile_exists`
- `test_dockerfile_has_required_instructions` (FROM, WORKDIR, COPY, EXPOSE, uvicorn)
- `test_docker_compose_exists`
- `test_docker_compose_valid_yaml`
- `test_docker_compose_has_required_services` (redis, web, worker)
- `test_docker_compose_web_exposes_port_8000`
- `test_docker_compose_worker_runs_celery`
- `test_dockerignore_exists`

### TestEnvironmentConfiguration
- `test_env_example_exists`
- `test_env_not_in_git`

### TestGitHubActionsWorkflows
- `test_workflows_directory_exists`
- `test_test_workflow_exists`
- `test_test_workflow_valid_yaml`
- `test_test_workflow_runs_pytest`
- `test_docker_build_workflow_exists`
- `test_docker_build_workflow_valid_yaml`

### TestDockerBuild (marked `@pytest.mark.slow`)
- `test_docker_build_succeeds`
- `test_docker_image_size_reasonable` (< 1GB)

**Verification**:
```bash
pytest -m stage_1_6 -v
```

---

## 1.6.7: Configure GCP Firewall (HUMAN TASK)

> ⚠️ **This must be done by a human in the GCP Console**

### Steps

1. Go to: https://console.cloud.google.com/
2. Navigate: **VPC network → Firewall** (or search "Firewall")
3. Click **CREATE FIREWALL RULE**
4. Enter these values:

| Field | Value |
|-------|-------|
| Name | `allow-knee-pipeline-8000` |
| Network | `default` |
| Priority | `1000` |
| Direction | Ingress |
| Action | Allow |
| Targets | Specified target tags |
| Target tags | `knee-pipeline` |
| Source IPv4 ranges | `0.0.0.0/0` |
| Protocols/ports | TCP: `8000` |

5. Click **CREATE**

6. **Add network tag to VM**:
   - Go to **Compute Engine → VM instances**
   - Click your VM → **EDIT**
   - Add Network tag: `knee-pipeline`
   - **SAVE**

### Verify (from local machine, not GCP VM)

```bash
curl http://YOUR_EXTERNAL_IP:8000/health
```

---

## 1.6.8: Deploy and Verify

### Deploy

On GCP VM:

```bash
cd ~/programming/kneepipeline_segmentaton_website

# Stop existing Redis if running outside Docker
docker stop redis 2>/dev/null || true

# Create .env file
cp docker/.env.example docker/.env

# Start services
cd docker
docker-compose up -d --build
docker-compose ps
```

### Expected Output

```
NAME                    STATUS    PORTS
knee-pipeline-redis     running   0.0.0.0:6379->6379/tcp
knee-pipeline-web       running   0.0.0.0:8000->8000/tcp
knee-pipeline-worker    running
```

### Verification

```bash
curl http://localhost:8000/health
docker-compose logs -f web
```

### End-to-End Test

From browser: `http://YOUR_EXTERNAL_IP:8000`
1. Upload `test_input.nii.gz`
2. Wait for processing
3. Download results

---

## Success Criteria

### Files (AI Agent)
- [ ] `docker/Dockerfile` exists
- [ ] `docker/docker-compose.yml` exists with 3 services
- [ ] `docker/.env.example` exists
- [ ] `.dockerignore` exists
- [ ] `.github/workflows/test.yml` exists
- [ ] `.github/workflows/docker-build.yml` exists
- [ ] `tests/test_stage_1_6.py` exists

### Tests (AI Agent)
- [ ] `pytest -m stage_1_6 -v` passes
- [ ] `make verify` passes (all ~120 tests)

### GCP (Human)
- [ ] Firewall rule created
- [ ] VM has network tag
- [ ] External access works

### Deployment
- [ ] `docker-compose up -d` starts all services
- [ ] All containers show "running"
- [ ] Health endpoint returns healthy
- [ ] Full upload→process→download works

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| Docker build fails | Check `docker ps`, rebuild with `--progress=plain` |
| Containers not starting | `docker-compose logs` to see errors |
| Cannot access externally | Verify firewall rule and VM network tag |
| Redis connection issues | `docker exec knee-pipeline-redis redis-cli ping` |

---

## Commands Reference

```bash
docker-compose up -d          # Start all
docker-compose down           # Stop all
docker-compose up -d --build  # Rebuild and start
docker-compose logs -f        # Follow logs
docker-compose ps             # Status
docker-compose down -v        # Stop and remove volumes
```
