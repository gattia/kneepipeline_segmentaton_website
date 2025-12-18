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

### Docker Deployment (Production)

```bash
cd ~/programming/kneepipeline_segmentaton_website

# Stop any existing Redis running outside Docker
docker stop redis 2>/dev/null || true

# Create environment file
cp docker/.env.example docker/.env

# Build and start all services
cd docker
docker compose up -d --build

# Check status
docker compose ps

# View logs
docker compose logs -f
```

**Services started:**
- `knee-pipeline-caddy` - Reverse proxy with auto-HTTPS (ports 80, 443)
- `knee-pipeline-redis` - Redis (internal only)
- `knee-pipeline-web` - FastAPI (internal only)
- `knee-pipeline-worker` - Celery worker

**Access via HTTPS:** `https://openmsk.com`

> **Note**: The application uses Caddy for automatic HTTPS. Access via domain name, not IP address.
> See [docs/stage_1/STAGE_1.7_HTTPS_CADDY.md](docs/stage_1/STAGE_1.7_HTTPS_CADDY.md) for setup details.

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
| `make install` | Install Python dependencies |
| `make test` | Run all tests |
| `make test-cov` | Run tests with coverage |
| `make lint` | Check code with ruff |
| `make format` | Auto-fix linting issues |
| `make run` | Start FastAPI server |
| `make worker` | Start Celery worker |
| `make redis-start` | Start Redis container |
| `make verify` | Run lint + tests (CI check) |
| `make clean` | Remove cache files |

---

## Documentation

| Document | Description |
|----------|-------------|
| [docs/PROJECT_OVERVIEW.md](docs/PROJECT_OVERVIEW.md) | Architecture, API design, full specification |
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
