# Knee MRI Segmentation Website

A web application for automated knee MRI segmentation and analysis. Upload knee MRI data, get segmentations, 3D meshes, cartilage thickness measurements, and BScore computation.

## Quick Start

If you've already set up the environment, jump to [Running the Application](#running-the-application).

### Prerequisites

1. Complete the development environment setup:
   - See [New Server Setup (GCP with GPU)](#new-server-setup-gcp-with-gpu) below, or
   - See [docs/STAGE_0_DEV_ENVIRONMENT.md](docs/STAGE_0_DEV_ENVIRONMENT.md)

2. Ensure Redis is running:
   ```bash
   make redis-start
   # or: docker start redis
   ```

### Installation

```bash
conda activate kneepipeline
cd ~/programming/kneepipeline_segmentaton_website
make install
# or: pip install -r backend/requirements.txt
```

---

## New Server Setup (GCP with GPU)

Complete setup instructions for a fresh GCP VM with GPU (tested on Debian 12 with Tesla T4).

### Step 1: Install System Dependencies

```bash
sudo apt update && sudo apt install -y build-essential curl ca-certificates gnupg lsb-release
```

### Step 2: Install Miniconda

```bash
# Download and install Miniconda
mkdir -p ~/miniconda3
wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh -O ~/miniconda3/miniconda.sh
bash ~/miniconda3/miniconda.sh -b -u -p ~/miniconda3
rm ~/miniconda3/miniconda.sh

# Initialize conda
~/miniconda3/bin/conda init bash
source ~/.bashrc

# Accept Terms of Service (required for newer conda versions)
conda tos accept --override-channels --channel https://repo.anaconda.com/pkgs/main
conda tos accept --override-channels --channel https://repo.anaconda.com/pkgs/r

# Create project environment
conda create -n kneepipeline python=3.10 -y
```

### Step 3: Install Docker

```bash
# Add Docker's GPG key
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/debian/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg

# Add Docker repository
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/debian $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# Install Docker
sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# Add user to docker group
sudo usermod -aG docker $USER
newgrp docker

# Verify
docker --version
docker compose version
```

### Step 4: Install NVIDIA GPU Drivers (GCP VMs)

Use Google's official installation script for GCP VMs. See the [GCP GPU driver installation documentation](https://docs.cloud.google.com/compute/docs/gpus/install-drivers-gpu#verify-linux) for more details.

```bash
# Download the installer
curl -L https://storage.googleapis.com/compute-gpu-installation-us/installer/latest/cuda_installer.pyz --output /tmp/cuda_installer.pyz

# Install GPU drivers (for Debian, use binary mode)
sudo python3 /tmp/cuda_installer.pyz install_driver --installation-mode=binary

# Verify installation
nvidia-smi
```

> **Note**: The script may reboot your VM. After reboot, run the installer again to complete installation.

### Step 5: Install NVIDIA Container Toolkit

This allows Docker containers to access the GPU.

```bash
# Add NVIDIA repository
curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg
curl -s -L https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list | \
  sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' | \
  sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list

# Install toolkit
sudo apt-get update
sudo apt-get install -y nvidia-container-toolkit

# Configure Docker for GPU support
sudo nvidia-ctk runtime configure --runtime=docker
sudo systemctl restart docker

# Verify Docker can access GPU
docker run --rm --gpus all nvidia/cuda:12.0.0-base-ubuntu22.04 nvidia-smi
```

### Step 6: Start Redis

```bash
docker run -d \
  --name redis \
  -p 6379:6379 \
  -v redis_data:/data \
  --restart unless-stopped \
  redis:7-alpine redis-server --appendonly yes

# Verify
docker exec redis redis-cli ping
# Should return: PONG
```

### Step 7: Install Python Dependencies

```bash
conda activate kneepipeline
cd ~/programming/kneepipeline_segmentaton_website
pip install -r backend/requirements.txt
```

### Verify Setup

```bash
# Check GPU
nvidia-smi

# Check Docker GPU access
docker run --rm --gpus all nvidia/cuda:12.0.0-base-ubuntu22.04 nvidia-smi

# Check Redis
docker exec redis redis-cli ping

# Check Python environment
conda activate kneepipeline
python -c "import fastapi; import celery; import SimpleITK; print('All packages OK')"
```

---

## Running the Application

### Development Mode

```bash
# Activate environment
conda activate kneepipeline
cd ~/programming/kneepipeline_segmentaton_website

# Ensure Redis is running
make redis-start

# Terminal 1: Start FastAPI server
make run
# or: uvicorn backend.main:app --reload --port 8000

# Terminal 2: Start Celery worker
make worker
# or: celery -A backend.workers.celery_app worker --loglevel=info --concurrency=1
```

Then open http://localhost:8000 in your browser.

### Verify Services

```bash
# Health check
curl http://localhost:8000/health

# Should return something like:
# {"status":"healthy","redis":"connected","worker":"available",...}
```

### Production Deployment (Hybrid Docker + systemd)

The production deployment uses Docker for web services (Caddy, Redis, FastAPI) and systemd for the GPU worker.

**Live URL:** https://openmsk.com

See **[docs/DEPLOYMENT_HYBRID.md](docs/DEPLOYMENT_HYBRID.md)** for complete instructions.

**Quick Reference:**

```bash
cd ~/programming/kneepipeline_segmentaton_website

# Start all services
make prod-start

# Stop all services
make prod-stop

# Check status
make prod-status

# View logs
make prod-logs

# Restart after code changes
sudo systemctl restart knee-pipeline-worker  # Worker code
cd docker && docker compose up -d --build web  # Web code
```

**Services:**
| Service | Location | Purpose |
|---------|----------|---------|
| `knee-pipeline-caddy` | Docker | HTTPS reverse proxy |
| `knee-pipeline-redis` | Docker | Job queue |
| `knee-pipeline-web` | Docker | FastAPI web server |
| `knee-pipeline-worker` | systemd | GPU processing |

> **Note**: The worker runs natively via systemd to access the GPU and conda environment.
> See [docs/DEPLOYMENT_HYBRID.md](docs/DEPLOYMENT_HYBRID.md) for troubleshooting and detailed configuration.

---

## Testing

We use **pytest** for testing. Tests are organized by development stage.

```bash
# Run all tests
make test

# Run specific stage tests
make test-stage-1-1
make test-stage-1-2

# Run with coverage report
make test-cov
```

### Test Markers

| Marker | Description |
|--------|-------------|
| `stage_1_1` | Project scaffolding, health endpoint |
| `stage_1_2` | Models and services |
| `stage_1_3` | Redis + Celery workers |
| `stage_1_4` | API routes |
| `stage_1_5` | Frontend |
| `stage_1_6` | Docker & deployment |
| `stage_1_7` | HTTPS with Caddy |
| `stage_3_3` | Pipeline worker integration |
| `stage_3_4` | Configuration mapping |
| `stage_3_5` | Error handling and progress updates |

Run a specific marker:
```bash
pytest -m stage_1_2 -v
```

---

## Linting

We use **ruff** for linting and formatting (configured in `pyproject.toml`).

```bash
# Check for issues
make lint

# Auto-fix issues
make format
```

Or run directly:
```bash
ruff check backend/ tests/           # Check
ruff check backend/ tests/ --fix     # Fix
ruff format backend/ tests/          # Format
```

---

## Makefile Commands

Run `make help` to see all available commands:

| Command | Description |
|---------|-------------|
| **Development** | |
| `make install` | Install Python dependencies |
| `make run` | Start FastAPI server (dev) |
| `make worker` | Start Celery worker (dev) |
| `make redis-start` | Start Redis container |
| **Testing** | |
| `make test` | Run all tests |
| `make test-cov` | Run tests with coverage |
| `make lint` | Check code with ruff |
| `make format` | Auto-fix linting issues |
| `make verify` | Run lint + tests (CI check) |
| **Production** | |
| `make prod-setup` | One-time setup (data dirs, systemd) |
| `make prod-start` | Start all production services |
| `make prod-stop` | Stop all production services |
| `make prod-status` | Check status of all services |
| `make prod-logs` | Tail all logs |
| **Admin** | |
| `make admin-emails` | List all user email addresses |
| `make admin-stats` | Show usage statistics |
| `make admin-times` | Show processing time history |
| `make admin-jobs` | List jobs with research consent |
| `make admin-results` | List saved results on disk |
| **Utilities** | |
| `make clean` | Remove cache files |

---

## Admin CLI

The `admin.py` script provides easy access to user data, statistics, and results for administrative tasks.

### Quick Commands

```bash
# List all user email addresses
make admin-emails
python admin.py emails --csv > emails.csv   # Export to CSV

# Show usage statistics
make admin-stats
python admin.py stats --json                # Output as JSON

# Show processing time history
make admin-times

# List jobs with research consent
make admin-jobs
python admin.py jobs --all                  # All jobs (not just consented)
python admin.py jobs --all --json           # Export as JSON

# List saved results on disk
make admin-results

# Show details for a specific job
python admin.py job abc123                  # Partial ID works
python admin.py job abc123 --json           # Output as JSON
```

### Data Locations

| Data | Storage | Access |
|------|---------|--------|
| **User emails** | Redis `user_emails` hash | `make admin-emails` |
| **Statistics** | Redis (`stats:*` keys) | `make admin-stats` or `/stats` API |
| **Processing times** | Redis `processing_times` list | `make admin-times` |
| **Job metadata** | Redis `jobs` hash | `make admin-jobs` |
| **Results files** | `/mnt/data/knee_pipeline_data/results/` | `make admin-results` |

### Redis Keys Reference

| Key | Type | Description |
|-----|------|-------------|
| `user_emails` | Hash | email_hash → email address |
| `stats:unique_emails` | Set | unique emails (for counting) |
| `stats:total_processed` | String | all-time job count |
| `stats:processed:YYYY-MM-DD` | String | daily count (7-day retention) |
| `processing_times` | List | last 20 processing durations (seconds) |
| `jobs` | Hash | job_id → job JSON |
| `job_queue` | Sorted Set | active job queue |

---

## Documentation

| Document | Description |
|----------|-------------|
| [docs/PROJECT_OVERVIEW.md](docs/PROJECT_OVERVIEW.md) | Architecture, API design, full specification |
| [docs/DEPLOYMENT_HYBRID.md](docs/DEPLOYMENT_HYBRID.md) | **Production deployment guide** |
| [docs/STAGE_0_DEV_ENVIRONMENT.md](docs/STAGE_0_DEV_ENVIRONMENT.md) | GCP VM setup, Miniconda, Docker, Redis |
| [docs/STAGE_1_DETAILED_PLAN.md](docs/STAGE_1_DETAILED_PLAN.md) | MVP implementation details |
| [docs/stage_1/](docs/stage_1/) | Step-by-step guides for Stage 1 components |
| [docs/STAGE_2_OVERVIEW.md](docs/STAGE_2_OVERVIEW.md) | Progress & statistics enhancements |
| [docs/STAGE_3_OVERVIEW.md](docs/STAGE_3_OVERVIEW.md) | Real pipeline integration with GPU |

---

## Project Status

- [x] Stage 0: Development Environment
- [x] Stage 1.1: Project Scaffolding
- [x] Stage 1.2: Models & Services
- [x] Stage 1.3: Redis & Celery
- [x] Stage 1.4: API Routes
- [x] Stage 1.5: Frontend
- [x] Stage 1.6: Docker & Deployment
- [x] Stage 1.7: HTTPS with Caddy
- [ ] Stage 2: Progress & Statistics  
- [ ] Stage 3: Real Pipeline Integration
  - [x] Stage 3.1: Pipeline Dependencies
  - [x] Stage 3.2: Model Download
  - [x] Stage 3.3: Pipeline Worker Integration
  - [x] Stage 3.4: Configuration Mapping
  - [x] Stage 3.5: Error Handling & Progress Updates
  - [ ] Stage 3.6: Integration Testing

---

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check (Redis, worker status) |
| `/upload` | POST | Upload file and start processing |
| `/models` | GET | List available segmentation models and options |
| `/status/{job_id}` | GET | Get job status |
| `/download/{job_id}` | GET | Download results |
| `/stats` | GET | Usage statistics |
| `/docs` | GET | OpenAPI documentation |

---

## License

Research use only. Not for clinical diagnosis.
