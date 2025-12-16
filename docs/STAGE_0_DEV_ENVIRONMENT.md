# Stage 0: Development Environment Setup

## Overview

**Goal**: Prepare the GCP VM with all required development tools before starting Stage 1.

**Estimated Time**: ~15-20 minutes

**VM Specifications** (current):
- **OS**: Debian 12 (bookworm)
- **Python**: 3.11.2 (system installed)
- **Memory**: 4GB RAM
- **CPU**: 2 vCPUs
- **Disk**: ~6GB free
- **Git**: Installed ✓

---

## Required Tools

| Tool | Purpose | Installation Method |
|------|---------|---------------------|
| **Miniconda** | Python environment management | Official installer |
| **Docker** | Run Redis, containerize app | Official Docker repo |
| **Docker Compose** | Multi-container orchestration | Docker plugin |
| **curl** | API testing | apt package |
| **build-essential** | Compile Python packages | apt package |

> **Note**: We use Miniconda for Python environment management (familiar workflow, handles complex dependencies in Stage 3) and Docker for Redis (clean, matches production).

---

## Installation Steps

### Step 1: Update System Packages

```bash
sudo apt update && sudo apt upgrade -y
```

### Step 2: Install System Dependencies

```bash
# Build tools and utilities (needed for compiling Python packages)
sudo apt install -y \
    build-essential \
    curl \
    ca-certificates \
    gnupg \
    lsb-release
```

### Step 3: Install Miniconda

```bash
# Download Miniconda installer
mkdir -p ~/miniconda3
wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh -O ~/miniconda3/miniconda.sh

# Install Miniconda (silent mode)
bash ~/miniconda3/miniconda.sh -b -u -p ~/miniconda3

# Remove installer
rm ~/miniconda3/miniconda.sh

# Initialize conda for bash
~/miniconda3/bin/conda init bash

# Reload shell to activate conda (or start a new terminal)
source ~/.bashrc

# Accept Terms of Service (required for newer conda versions)
conda tos accept --override-channels --channel https://repo.anaconda.com/pkgs/main
conda tos accept --override-channels --channel https://repo.anaconda.com/pkgs/r

# Verify installation
conda --version
```

> **Note**: After `conda init bash`, you'll need to start a new shell or run `source ~/.bashrc` for conda to be available. The ToS acceptance is a one-time requirement.

### Step 4: Install Docker

Docker is needed to run Redis (and later for deployment).

```bash
# Add Docker's official GPG key
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/debian/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg

# Add Docker repository
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/debian \
  $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# Install Docker Engine
sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# Add current user to docker group (no sudo needed for docker commands)
sudo usermod -aG docker $USER

# Apply group changes (or log out and back in)
newgrp docker
```

### Step 5: Verify Installations

```bash
# Verify conda
conda --version

# Verify Docker
docker --version
docker compose version

# Test Docker (run hello-world)
docker run --rm hello-world

# Verify build tools
gcc --version
```

### Step 6: Start Redis (Docker)

```bash
# Start Redis container (will persist data in named volume)
docker run -d \
    --name redis \
    -p 6379:6379 \
    -v redis_data:/data \
    --restart unless-stopped \
    redis:7-alpine redis-server --appendonly yes

# Verify Redis is running
docker ps | grep redis

# Test Redis connection
docker exec redis redis-cli ping
# Should return: PONG
```

---

### Step 7: Create Conda Environment for Project

```bash
# Create environment with Python 3.10 (matches project requirements)
conda create -n kneepipeline python=3.10 -y

# Activate the environment
conda activate kneepipeline

# Verify Python version
python --version
```

---

## Verification Checklist

After completing all steps, verify:

- [ ] `conda --version` - conda is available
- [ ] `conda activate kneepipeline && python --version` - environment works, Python 3.10.x
- [ ] `docker ps` - shows Redis running
- [ ] `docker exec redis redis-cli ping` - returns PONG
- [ ] `docker compose version` - shows version info
- [ ] `gcc --version` - build tools available

---

## Quick Reference: Docker Commands

```bash
# Start Redis (if stopped)
docker start redis

# Stop Redis
docker stop redis

# View Redis logs
docker logs redis

# Connect to Redis CLI
docker exec -it redis redis-cli

# Remove Redis container (data preserved in volume)
docker rm -f redis

# Remove Redis data volume (destructive!)
docker volume rm redis_data
```

---

## Troubleshooting

### Docker permission denied

If you get "permission denied" when running docker commands:

```bash
# Make sure you're in the docker group
groups

# If docker not listed, add yourself and start new shell
sudo usermod -aG docker $USER
newgrp docker
```

### Redis connection refused

```bash
# Check if Redis container is running
docker ps -a | grep redis

# If exited, check logs
docker logs redis

# Restart the container
docker start redis
```

### Port 6379 already in use

```bash
# Find what's using the port
sudo lsof -i :6379

# Kill the process or use a different port for Redis
docker run -d --name redis -p 6380:6379 redis:7-alpine
# Then update REDIS_URL in .env to use port 6380
```

---

## Next Steps

Once this setup is complete, proceed to **Stage 1.1: Project Scaffolding**.

The environment will have:
- ✅ Miniconda with `kneepipeline` environment (Python 3.10)
- ✅ Docker running Redis on port 6379
- ✅ Docker Compose for multi-container workflows
- ✅ Build tools for compiling Python packages

### Quick Start for Development

```bash
# Always activate conda environment before working on the project
conda activate kneepipeline
cd ~/programming/kneepipeline_segmentaton_website
```

