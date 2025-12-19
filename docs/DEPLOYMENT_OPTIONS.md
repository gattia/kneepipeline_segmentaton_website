# Deployment Options Report

## Current Problem

The Knee MRI Analysis Pipeline has two distinct parts with different dependency requirements:

### Part 1: Web Infrastructure (Simple)
- **Components**: Caddy (HTTPS), Redis (job queue), FastAPI (web server)
- **Dependencies**: Standard Python packages (FastAPI, Celery, Redis client)
- **Status**: ✅ Works perfectly in Docker via `docker-compose.yml`

### Part 2: Pipeline Worker (Complex)
- **Components**: Celery worker that runs the actual segmentation/analysis
- **Dependencies**: 
  - `kneepipeline` (custom package)
  - `nnU-Net` with trained model weights (~2GB+)
  - `DOSMA` with model weights
  - `NSM` (Neural Shape Models)
  - PyTorch with CUDA support
  - SimpleITK, PyVista, and many scientific libraries
- **Status**: ❌ Only works in local `kneepipeline` conda environment

### The Core Issue

The current Docker setup (`docker/Dockerfile`) was built for **Stage 1 development** with a dummy worker. It uses `python:3.10-slim` and only installs basic web dependencies. The real pipeline worker needs:

1. CUDA/GPU access
2. The `kneepipeline` conda environment with all ML dependencies
3. Access to model weight files (nnU-Net, DOSMA)
4. Access to uploaded files and results directories

**File sharing problem**: Docker containers use isolated volumes. If the web server saves uploads to `/app/data` inside Docker, the local worker can't access them (and vice versa).

---

## Solution 1: Hybrid Mode (Docker + Local Worker)

Run web infrastructure in Docker, but run the worker locally.

### Changes Required
1. Modify `docker-compose.yml`:
   - Comment out the `worker` service
   - Change Redis `expose` → `ports` (expose 6379 to host)
   - Change `app_data` volume to bind mount: `../data:/app/data`

2. Create local `data/` directory accessible to both Docker and local worker

3. Run worker locally with nohup or systemd

### Commands
```bash
# Start Docker services
cd ~/programming/kneepipeline_segmentaton_website/docker
docker-compose up -d

# Start worker locally (background)
cd ~/programming/kneepipeline_segmentaton_website
conda activate kneepipeline
nohup make worker > worker.log 2>&1 &
```

### Pros
- ✅ Quick to implement (minutes)
- ✅ Uses existing tested infrastructure
- ✅ Worker has full access to conda env and GPU

### Cons
- ❌ Worker doesn't auto-restart on reboot (need systemd service)
- ❌ Two separate management systems (Docker + systemd/nohup)
- ❌ Must ensure file paths are consistent between Docker and host

---

## Solution 2: Full Docker with Kneepipeline (Recommended Long-term)

Build a Docker image that includes the entire kneepipeline environment.

### Changes Required
1. Create new `Dockerfile.gpu` based on NVIDIA CUDA image
2. Install conda/mamba in container
3. Copy/recreate the kneepipeline environment
4. Download or mount model weights
5. Configure GPU passthrough in docker-compose

### Example Dockerfile Structure
```dockerfile
FROM nvidia/cuda:11.8-cudnn8-runtime-ubuntu22.04

# Install miniconda
RUN wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh && \
    bash Miniconda3-latest-Linux-x86_64.sh -b -p /opt/conda && \
    rm Miniconda3-latest-Linux-x86_64.sh

# Create kneepipeline environment
COPY environment.yml /tmp/
RUN /opt/conda/bin/conda env create -f /tmp/environment.yml

# Install kneepipeline and dependencies
COPY kneepipeline/ /app/kneepipeline/
RUN /opt/conda/bin/conda run -n kneepipeline pip install -e /app/kneepipeline

# Download or mount model weights
# Option A: Download at build time (large image)
# Option B: Mount at runtime (smaller image, separate weight management)

WORKDIR /app
COPY backend/ ./backend/
COPY frontend/ ./frontend/
```

### Docker Compose GPU Support
```yaml
worker:
  build:
    dockerfile: docker/Dockerfile.gpu
  deploy:
    resources:
      reservations:
        devices:
          - driver: nvidia
            count: 1
            capabilities: [gpu]
```

### Pros
- ✅ Single deployment system (all Docker)
- ✅ Reproducible environment
- ✅ Auto-restart on failure/reboot
- ✅ Easier to deploy to other machines

### Cons
- ❌ Complex Dockerfile to create and maintain
- ❌ Large Docker image (10-20GB+ with weights)
- ❌ Need to handle model weight updates
- ❌ May require exporting conda env to `environment.yml`
- ❌ Takes significant effort (hours to days)

---

## Solution 3: All Local with Systemd

Skip Docker entirely for production. Run everything locally with systemd services.

### Changes Required
1. Create systemd service files for:
   - Redis (or keep using Docker just for Redis)
   - FastAPI server
   - Celery worker
   - Caddy (install locally)

2. Install Caddy on the host system

### Service Files
```ini
# /etc/systemd/system/knee-pipeline-web.service
[Unit]
Description=Knee Pipeline Web Server
After=network.target

[Service]
User=gattia
WorkingDirectory=/home/gattia/programming/kneepipeline_segmentaton_website
Environment="PATH=/home/gattia/miniconda3/envs/kneepipeline/bin"
ExecStart=/home/gattia/miniconda3/envs/kneepipeline/bin/uvicorn backend.main:app --host 0.0.0.0 --port 8000
Restart=always

[Install]
WantedBy=multi-user.target
```

### Commands
```bash
# Install services
sudo cp systemd/*.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now knee-pipeline-web knee-pipeline-worker

# Install Caddy
sudo apt install caddy
sudo cp docker/Caddyfile /etc/caddy/Caddyfile
sudo systemctl enable --now caddy
```

### Pros
- ✅ Simple, everything runs natively
- ✅ No Docker complexity
- ✅ No file sharing issues
- ✅ All services auto-restart

### Cons
- ❌ Less portable (tied to this specific machine)
- ❌ Need to install Caddy separately
- ❌ Environment must be maintained on host
- ❌ Harder to replicate on new machines

---

## Recommendation

### For Immediate Launch (Today)
Use **Solution 1: Hybrid Mode**. It's the fastest path to production with minimal changes.

### For Long-term Maintainability
Invest in **Solution 2: Full Docker**. This is the proper DevOps approach and will make future deployments, updates, and scaling much easier.

### Next Steps for Solution 2
1. Export current conda environment: `conda env export -n kneepipeline > environment.yml`
2. Document where model weights are stored
3. Create `Dockerfile.gpu` 
4. Test locally with `docker build` and `docker run --gpus all`
5. Update `docker-compose.yml` for GPU support

---

## Summary Table

| Aspect | Solution 1: Hybrid | Solution 2: Full Docker | Solution 3: All Local |
|--------|-------------------|------------------------|----------------------|
| Setup Time | 30 minutes | 4-8 hours | 1-2 hours |
| Complexity | Medium | High | Low |
| Portability | Low | High | Low |
| Maintainability | Medium | High | Medium |
| Auto-restart | Partial | Yes | Yes |
| GPU Access | Easy | Requires config | Easy |
| File Sharing | Needs care | Built-in | N/A |


