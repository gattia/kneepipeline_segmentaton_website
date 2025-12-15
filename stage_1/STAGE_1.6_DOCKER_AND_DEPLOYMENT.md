# Stage 1.6: Docker & GCP Deployment

## Overview

**Goal**: Containerize the application and deploy it properly on GCP with systemd services.

**Estimated Time**: ~45 minutes

**Deliverable**: Production-ready deployment running on GCP VM accessible via public IP.

---

## What This Stage Covers

1. **Dockerfile** - `docker/Dockerfile`
   - Python base image (no GPU needed for Stage 1)
   - Install dependencies
   - Copy application code
   - Expose port 8000

2. **Docker Compose** - `docker/docker-compose.yml`
   - Redis service
   - Web service (FastAPI)
   - Worker service (Celery)
   - Volume mounts for data persistence

3. **Environment Configuration**
   - `.env` file for secrets
   - Environment variables for Redis URL, etc.

4. **GCP Firewall Rules**
   - Open port 8000 (or 80/443 with reverse proxy)
   
5. **Systemd Service** (alternative to Docker)
   - Service files for uvicorn and celery
   - Auto-restart on failure

6. **GitHub Actions CI/CD** - `.github/workflows/`
   - Run tests on push
   - Validate Docker build

7. **Final Testing**
   - Access from external browser
   - Full end-to-end test

---

## Success Criteria

- [ ] `docker-compose up` starts all services
- [ ] Application accessible from public internet
- [ ] Services restart automatically on failure
- [ ] GitHub Actions CI passes

---

## Detailed Steps

*(To be expanded)*
