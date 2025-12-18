# Hybrid Deployment Guide

Deploy the Knee MRI Analysis Pipeline using Docker for web services and systemd for the GPU worker.

**Live URL:** https://openmsk.com

---

## Quick Reference

### Start Everything
```bash
cd ~/programming/kneepipeline_segmentaton_website
make prod-start
```

### Stop Everything
```bash
make prod-stop
```

### Check Status
```bash
make prod-status
```

### View Logs
```bash
# All logs
make prod-logs

# Worker only
make prod-logs-worker

# Web only  
make prod-logs-web
```

### Restart After Code Changes
```bash
# If you changed worker code (backend/workers/):
sudo systemctl restart knee-pipeline-worker

# If you changed web code (backend/routes/, frontend/):
cd docker && docker compose up -d --build web
```

---

## Architecture

```
Internet (HTTPS)
      │
      ▼
┌─────────────────────────────────────────────────┐
│            DOCKER CONTAINERS                     │
│  ┌─────────┐  ┌─────────┐  ┌──────────────┐    │
│  │  Caddy  │  │  Redis  │  │   FastAPI    │    │
│  │ :80/443 │  │  :6379  │  │    :8000     │    │
│  └─────────┘  └────┬────┘  └──────────────┘    │
└────────────────────┼────────────────────────────┘
                     │ localhost:6379
                     ▼
┌─────────────────────────────────────────────────┐
│          SYSTEMD SERVICE (Native)                │
│  ┌───────────────────────────────────────────┐  │
│  │           Celery Worker                    │  │
│  │  • kneepipeline conda environment         │  │
│  │  • Full GPU access (CUDA)                 │  │
│  │  • Runs nnU-Net segmentation              │  │
│  └───────────────────────────────────────────┘  │
└─────────────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────┐
│        /mnt/data/knee_pipeline_data/            │
│  uploads/ │ temp/ │ results/ │ logs/            │
└─────────────────────────────────────────────────┘
```

| Service | Location | Purpose |
|---------|----------|---------|
| **Caddy** | Docker | HTTPS, auto SSL certificates |
| **Redis** | Docker | Job queue |
| **FastAPI** | Docker | Web server, API |
| **Worker** | systemd | GPU processing, runs pipeline |

---

## Service Management

### Using Makefile (Recommended)

| Command | Description |
|---------|-------------|
| `make prod-start` | Start all services |
| `make prod-stop` | Stop all services |
| `make prod-restart` | Restart all services |
| `make prod-status` | Check status of all services |
| `make prod-logs` | Tail all logs |
| `make prod-logs-worker` | Tail worker logs only |
| `make prod-logs-web` | Tail web logs only |

### Manual Commands

**Docker services (Caddy, Redis, Web):**
```bash
cd ~/programming/kneepipeline_segmentaton_website/docker

# Start
docker compose up -d

# Stop
docker compose down

# Restart
docker compose restart

# Status
docker compose ps

# Logs
docker compose logs -f
docker logs -f knee-pipeline-web
docker logs -f knee-pipeline-caddy
```

**Worker service (systemd):**
```bash
# Start
sudo systemctl start knee-pipeline-worker

# Stop
sudo systemctl stop knee-pipeline-worker

# Restart
sudo systemctl restart knee-pipeline-worker

# Status
sudo systemctl status knee-pipeline-worker

# Logs
journalctl -u knee-pipeline-worker -f
journalctl -u knee-pipeline-worker -n 100  # Last 100 lines
```

---

## Common Tasks

### Rebuild Web Container After Code Changes

If you modify code in `backend/routes/`, `backend/services/`, `frontend/`, etc.:

```bash
cd ~/programming/kneepipeline_segmentaton_website/docker
docker compose up -d --build web
```

### Restart Worker After Code Changes

If you modify code in `backend/workers/`:

```bash
sudo systemctl restart knee-pipeline-worker
```

### Check Health

```bash
# Via curl
curl -s https://openmsk.com/health | python3 -m json.tool

# Expected output:
{
    "status": "healthy",
    "redis": "connected",
    "worker": "available",
    ...
}
```

### Update Available Models

If you download new model weights:

1. Edit `docker/docker-compose.yml`
2. Update the `AVAILABLE_MODELS` line:
   ```yaml
   - AVAILABLE_MODELS=nnunet_fullres,nnunet_cascade,dosma_ananya,NEW_MODEL
   ```
3. Restart web: `cd docker && docker compose up -d web`

**Currently available models:**
- `nnunet_fullres` - nnU-Net FullRes (recommended)
- `nnunet_cascade` - nnU-Net Cascade  
- `dosma_ananya` - DOSMA 2D UNet

---

## Troubleshooting

### Processing Errors

Check worker logs for the actual error:
```bash
journalctl -u knee-pipeline-worker -n 200 --no-pager | less
```

### Worker Won't Start

```bash
# Check status
sudo systemctl status knee-pipeline-worker

# Check logs
journalctl -u knee-pipeline-worker -n 50 --no-pager

# Try running manually
cd ~/programming/kneepipeline_segmentaton_website
conda activate kneepipeline
celery -A backend.workers.celery_app worker --loglevel=debug
```

### Redis Connection Issues

```bash
# Check Redis container
docker ps | grep redis
docker logs knee-pipeline-redis

# Test connectivity
docker exec knee-pipeline-redis redis-cli ping
# Should return: PONG
```

### Web Server Not Responding

```bash
# Check container
docker logs knee-pipeline-web

# Rebuild
cd docker && docker compose up -d --build web
```

### Permission Issues

```bash
sudo chown -R gattia:gattia /mnt/data/knee_pipeline_data
chmod -R 755 /mnt/data/knee_pipeline_data
```

### GPU Not Working

```bash
# Check GPU is visible
nvidia-smi

# Check PyTorch sees GPU
conda activate kneepipeline
python -c "import torch; print(f'CUDA available: {torch.cuda.is_available()}')"
```

---

## Configuration Files

| File | Purpose |
|------|---------|
| `docker/docker-compose.yml` | Docker service definitions |
| `docker/Caddyfile` | HTTPS/domain configuration |
| `systemd/knee-pipeline-worker.service` | Worker systemd service |
| `.env` | Environment variables (development) |

### Key Paths

| Path | Description |
|------|-------------|
| `/mnt/data/knee_pipeline_data/` | All application data |
| `/mnt/data/knee_pipeline_data/uploads/` | User uploads |
| `/mnt/data/knee_pipeline_data/results/` | Processing results |
| `/mnt/data/programming/kneepipeline_segmentaton_website/` | Application code |
| `/mnt/data/miniconda3/envs/kneepipeline/` | Conda environment |
| `~/programming/kneepipeline/` | Pipeline code & model weights |

---

## Path Translation (Technical Note)

The Docker web container and native worker use different paths for the same data:

| Component | Sees data at |
|-----------|--------------|
| Docker (web) | `/app/data/...` |
| Host (worker) | `/mnt/data/knee_pipeline_data/...` |

Path translation is handled automatically:
- **Worker**: Translates `/app/data/` → `/mnt/data/knee_pipeline_data/` for input files
- **Download**: Translates `/mnt/data/knee_pipeline_data/` → `/app/data/` for results

---

## First-Time Setup

If setting up on a new server, run:

```bash
cd ~/programming/kneepipeline_segmentaton_website
make prod-setup
```

This will:
1. Create `/mnt/data/knee_pipeline_data/` directories
2. Install the systemd service
3. Enable auto-start on boot

Then start with `make prod-start`.

---

## Security

- **Redis**: Only exposed on localhost (127.0.0.1:6379)
- **Web server**: Only accessible via Caddy (not directly exposed)
- **HTTPS**: Automatic Let's Encrypt certificates via Caddy
- **Data**: Stored on mounted disk, not web-accessible
