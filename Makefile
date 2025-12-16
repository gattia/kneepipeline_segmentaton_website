# Makefile for Knee MRI Segmentation Website
#
# Usage:
#   make help      - Show all available commands
#   make install   - Install dependencies
#   make test      - Run all tests
#   make lint      - Run linter
#   make format    - Auto-fix linting issues
#   make run       - Start development server

.PHONY: help install test test-stage-1-1 test-stage-1-2 lint format run worker clean

# Default target
help:
	@echo "Knee MRI Segmentation Website - Development Commands"
	@echo ""
	@echo "Setup:"
	@echo "  make install        Install Python dependencies"
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
