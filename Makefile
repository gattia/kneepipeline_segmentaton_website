# Makefile for Knee MRI Segmentation Website
#
# Usage:
#   make help      - Show all available commands
#   make install   - Install dependencies
#   make test      - Run all tests
#   make lint      - Run linter
#   make format    - Auto-fix linting issues
#   make run       - Start development server

.PHONY: help install test test-stage-1-1 test-stage-1-2 lint format run worker clean \
        prod-start prod-stop prod-restart prod-status prod-logs prod-logs-worker prod-logs-web prod-setup \
        admin-emails admin-stats admin-times admin-jobs admin-results \
        admin-emails admin-stats admin-times admin-jobs admin-results

# Default target
help:
	@echo "Knee MRI Segmentation Website - Commands"
	@echo ""
	@echo "Setup:"
	@echo "  make install        Install Python dependencies"
	@echo "  make prod-setup     One-time production setup (data dirs, systemd)"
	@echo ""
	@echo "Testing:"
	@echo "  make test           Run all tests"
	@echo "  make test-stage-1-1 Run Stage 1.1 tests only"
	@echo "  make test-stage-1-2 Run Stage 1.2 tests only"
	@echo "  make test-cov       Run tests with coverage report"
	@echo ""
	@echo "Linting:"
	@echo "  make lint           Check code with ruff"
	@echo "  make format         Auto-fix linting issues with ruff"
	@echo ""
	@echo "Development:"
	@echo "  make run            Start FastAPI development server"
	@echo "  make worker         Start Celery worker"
	@echo "  make redis-start    Start Redis container"
	@echo "  make redis-stop     Stop Redis container"
	@echo ""
	@echo "Production (Docker + systemd):"
	@echo "  make prod-start     Start all production services"
	@echo "  make prod-stop      Stop all production services"
	@echo "  make prod-restart   Restart all production services"
	@echo "  make prod-status    Check status of all services"
	@echo "  make prod-logs      Tail all logs"
	@echo "  make prod-logs-worker  Tail worker logs only"
	@echo "  make prod-logs-web     Tail web server logs only"
	@echo ""
	@echo "Admin:"
	@echo "  make admin-emails   List all user email addresses"
	@echo "  make admin-stats    Show usage statistics"
	@echo "  make admin-times    Show processing time history"
	@echo "  make admin-jobs     List jobs with research consent"
	@echo "  make admin-results  List saved results on disk"
	@echo ""
	@echo "Utilities:"
	@echo "  make clean          Remove cache files"
	@echo "  make verify         Run lint + tests (CI check)"

# =============================================================================
# Setup
# =============================================================================

install:
	pip install -r backend/requirements.txt

# =============================================================================
# Testing
# =============================================================================

test:
	pytest tests/ -v

test-stage-1-1:
	pytest -m stage_1_1 -v

test-stage-1-2:
	pytest -m stage_1_2 -v

test-stage-1-3:
	pytest -m stage_1_3 -v

test-stage-1-4:
	pytest -m stage_1_4 -v

test-stage-1-5:
	pytest -m stage_1_5 -v

test-cov:
	pytest tests/ -v --cov=backend --cov-report=html --cov-report=term
	@echo "Coverage report: htmlcov/index.html"

# =============================================================================
# Linting
# =============================================================================

lint:
	ruff check backend/ tests/

format:
	ruff check backend/ tests/ --fix
	ruff format backend/ tests/

# =============================================================================
# Development Servers
# =============================================================================

run:
	uvicorn backend.main:app --reload --port 8000

worker:
	celery -A backend.workers.celery_app worker --loglevel=info --concurrency=1

# =============================================================================
# Redis
# =============================================================================

redis-start:
	@docker start redis 2>/dev/null || docker run -d \
		--name redis \
		-p 6379:6379 \
		-v redis_data:/data \
		--restart unless-stopped \
		redis:7-alpine redis-server --appendonly yes
	@echo "Redis started on port 6379"

redis-stop:
	docker stop redis
	@echo "Redis stopped"

redis-cli:
	docker exec -it redis redis-cli

redis-ping:
	@docker exec redis redis-cli ping

# =============================================================================
# Utilities
# =============================================================================

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "htmlcov" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	find . -type f -name ".coverage" -delete 2>/dev/null || true
	@echo "Cleaned cache files"

verify: lint test
	@echo ""
	@echo "✅ All checks passed!"

# =============================================================================
# Production (Hybrid Docker + systemd)
# =============================================================================

# Data directory on mounted disk
DATA_DIR := /mnt/data/knee_pipeline_data

prod-setup:
	@echo "Creating data directories on mounted disk..."
	sudo mkdir -p $(DATA_DIR)/uploads $(DATA_DIR)/temp $(DATA_DIR)/results $(DATA_DIR)/logs
	sudo chown -R $(USER):$(USER) $(DATA_DIR)
	chmod 755 $(DATA_DIR)
	@echo ""
	@echo "Installing systemd service..."
	sudo cp systemd/knee-pipeline-worker.service /etc/systemd/system/
	sudo systemctl daemon-reload
	sudo systemctl enable knee-pipeline-worker
	@echo ""
	@echo "✅ Production setup complete!"
	@echo "   Data directory: $(DATA_DIR)"
	@echo "   Run 'make prod-start' to start services"

prod-start:
	@echo "Starting Docker services (Caddy + Redis + FastAPI)..."
	cd docker && docker compose up -d --build
	@echo "Waiting for services to be ready..."
	@sleep 5
	@echo "Starting worker via systemd..."
	sudo systemctl start knee-pipeline-worker
	@echo ""
	@echo "✅ All services started!"
	@make prod-status

prod-stop:
	@echo "Stopping worker..."
	-sudo systemctl stop knee-pipeline-worker 2>/dev/null || true
	@echo "Stopping Docker services..."
	cd docker && docker compose down
	@echo ""
	@echo "✅ All services stopped."

prod-restart:
	@make prod-stop
	@sleep 2
	@make prod-start

prod-status:
	@echo "=== Docker Services ==="
	@cd docker && docker compose ps
	@echo ""
	@echo "=== Worker Service ==="
	@systemctl status knee-pipeline-worker --no-pager -l 2>/dev/null | head -15 || echo "Worker not running"
	@echo ""
	@echo "=== Health Check (https://openmsk.com) ==="
	@curl -s -k https://openmsk.com/health 2>/dev/null | python3 -m json.tool || echo "Web server not responding"

prod-logs:
	@echo "Tailing all logs (Ctrl+C to stop)..."
	@echo "=== Starting log streams ==="
	@journalctl -u knee-pipeline-worker -f &
	@cd docker && docker compose logs -f

prod-logs-worker:
	journalctl -u knee-pipeline-worker -f

prod-logs-web:
	docker logs -f knee-pipeline-web

# =============================================================================
# Admin Commands
# =============================================================================

admin-emails:
	@python admin.py emails

admin-stats:
	@python admin.py stats

admin-times:
	@python admin.py times

admin-jobs:
	@python admin.py jobs

admin-jobs-all:
	@python admin.py jobs --all

admin-results:
	@python admin.py results

