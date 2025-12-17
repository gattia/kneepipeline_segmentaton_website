"""
Stage 1.6: Docker & Deployment Tests

Tests verify:
- Docker configuration files exist and are valid
- Environment configuration
- GitHub Actions workflows
- Docker build (optional, marked slow)
"""

import subprocess
from pathlib import Path

import pytest
import yaml

# Mark all tests in this module as stage_1_6
pytestmark = pytest.mark.stage_1_6

# Project root directory
PROJECT_ROOT = Path(__file__).parent.parent


class TestDockerConfiguration:
    """Tests for Docker configuration files."""

    def test_dockerfile_exists(self):
        """Dockerfile exists in docker/ directory."""
        dockerfile = PROJECT_ROOT / "docker" / "Dockerfile"
        assert dockerfile.exists(), "docker/Dockerfile not found"

    def test_dockerfile_has_required_instructions(self):
        """Dockerfile contains required instructions."""
        dockerfile = PROJECT_ROOT / "docker" / "Dockerfile"
        content = dockerfile.read_text()

        # Check for required instructions
        assert "FROM" in content, "Dockerfile must have FROM instruction"
        assert "WORKDIR" in content, "Dockerfile must have WORKDIR instruction"
        assert "COPY" in content, "Dockerfile must have COPY instruction"
        assert "EXPOSE" in content, "Dockerfile must have EXPOSE instruction"
        assert "uvicorn" in content, "Dockerfile must run uvicorn"

    def test_dockerfile_uses_python_310(self):
        """Dockerfile uses Python 3.10 base image."""
        dockerfile = PROJECT_ROOT / "docker" / "Dockerfile"
        content = dockerfile.read_text()
        assert "python:3.10" in content, "Dockerfile should use Python 3.10"

    def test_dockerfile_exposes_port_8000(self):
        """Dockerfile exposes port 8000."""
        dockerfile = PROJECT_ROOT / "docker" / "Dockerfile"
        content = dockerfile.read_text()
        assert "EXPOSE 8000" in content, "Dockerfile should expose port 8000"

    def test_docker_compose_exists(self):
        """docker-compose.yml exists in docker/ directory."""
        compose_file = PROJECT_ROOT / "docker" / "docker-compose.yml"
        assert compose_file.exists(), "docker/docker-compose.yml not found"

    def test_docker_compose_valid_yaml(self):
        """docker-compose.yml is valid YAML."""
        compose_file = PROJECT_ROOT / "docker" / "docker-compose.yml"
        content = compose_file.read_text()
        try:
            config = yaml.safe_load(content)
            assert config is not None
        except yaml.YAMLError as e:
            pytest.fail(f"Invalid YAML in docker-compose.yml: {e}")

    def test_docker_compose_has_required_services(self):
        """docker-compose.yml has redis, web, and worker services."""
        compose_file = PROJECT_ROOT / "docker" / "docker-compose.yml"
        config = yaml.safe_load(compose_file.read_text())

        assert "services" in config, "docker-compose.yml must have services"
        services = config["services"]

        assert "redis" in services, "Must have redis service"
        assert "web" in services, "Must have web service"
        assert "worker" in services, "Must have worker service"

    def test_docker_compose_redis_service(self):
        """Redis service is properly configured."""
        compose_file = PROJECT_ROOT / "docker" / "docker-compose.yml"
        config = yaml.safe_load(compose_file.read_text())
        redis = config["services"]["redis"]

        assert "redis" in redis.get("image", ""), "Redis should use redis image"
        assert "healthcheck" in redis, "Redis should have healthcheck"

    def test_docker_compose_web_has_port_8000(self):
        """Web service has port 8000 (external or internal)."""
        compose_file = PROJECT_ROOT / "docker" / "docker-compose.yml"
        config = yaml.safe_load(compose_file.read_text())
        web = config["services"]["web"]

        # Check for either external ports or internal expose (Stage 1.7 with Caddy)
        ports = web.get("ports", [])
        expose = web.get("expose", [])
        all_ports = [str(p) for p in ports + expose]
        assert any("8000" in p for p in all_ports), \
            "Web service should have port 8000 (via ports or expose)"

    def test_docker_compose_worker_runs_celery(self):
        """Worker service runs Celery."""
        compose_file = PROJECT_ROOT / "docker" / "docker-compose.yml"
        config = yaml.safe_load(compose_file.read_text())
        worker = config["services"]["worker"]

        command = worker.get("command", "")
        assert "celery" in command, "Worker should run celery command"

    def test_docker_compose_has_volumes(self):
        """docker-compose.yml defines required volumes."""
        compose_file = PROJECT_ROOT / "docker" / "docker-compose.yml"
        config = yaml.safe_load(compose_file.read_text())

        assert "volumes" in config, "docker-compose.yml must define volumes"
        volumes = config["volumes"]

        # Check for named volumes
        assert len(volumes) >= 2, "Should have at least 2 volumes (redis_data, app_data)"

    def test_dockerignore_exists(self):
        """".dockerignore exists in project root."""
        dockerignore = PROJECT_ROOT / ".dockerignore"
        assert dockerignore.exists(), ".dockerignore not found"

    def test_dockerignore_excludes_tests(self):
        """.dockerignore excludes tests/ directory."""
        dockerignore = PROJECT_ROOT / ".dockerignore"
        content = dockerignore.read_text()
        assert "tests/" in content, ".dockerignore should exclude tests/"

    def test_dockerignore_excludes_git(self):
        """.dockerignore excludes .git directory."""
        dockerignore = PROJECT_ROOT / ".dockerignore"
        content = dockerignore.read_text()
        assert ".git" in content, ".dockerignore should exclude .git"


class TestEnvironmentConfiguration:
    """Tests for environment configuration."""

    def test_env_example_exists(self):
        """docker/.env.example exists."""
        env_example = PROJECT_ROOT / "docker" / ".env.example"
        assert env_example.exists(), "docker/.env.example not found"

    def test_env_example_has_required_vars(self):
        """docker/.env.example has required variables."""
        env_example = PROJECT_ROOT / "docker" / ".env.example"
        content = env_example.read_text()

        assert "DEBUG" in content, ".env.example should have DEBUG"
        assert "MAX_UPLOAD_SIZE_MB" in content, ".env.example should have MAX_UPLOAD_SIZE_MB"

    def test_docker_env_in_gitignore(self):
        """docker/.env is in .gitignore."""
        gitignore = PROJECT_ROOT / ".gitignore"
        content = gitignore.read_text()
        assert "docker/.env" in content, "docker/.env should be in .gitignore"


class TestGitHubActionsWorkflows:
    """Tests for GitHub Actions workflow files."""

    def test_workflows_directory_exists(self):
        """.github/workflows directory exists."""
        workflows_dir = PROJECT_ROOT / ".github" / "workflows"
        assert workflows_dir.exists(), ".github/workflows directory not found"
        assert workflows_dir.is_dir(), ".github/workflows should be a directory"

    def test_test_workflow_exists(self):
        """test.yml workflow exists."""
        test_workflow = PROJECT_ROOT / ".github" / "workflows" / "test.yml"
        assert test_workflow.exists(), ".github/workflows/test.yml not found"

    def test_test_workflow_valid_yaml(self):
        """test.yml is valid YAML."""
        test_workflow = PROJECT_ROOT / ".github" / "workflows" / "test.yml"
        content = test_workflow.read_text()
        try:
            config = yaml.safe_load(content)
            assert config is not None
        except yaml.YAMLError as e:
            pytest.fail(f"Invalid YAML in test.yml: {e}")

    def test_test_workflow_has_triggers(self):
        """test.yml has push and pull_request triggers."""
        test_workflow = PROJECT_ROOT / ".github" / "workflows" / "test.yml"
        config = yaml.safe_load(test_workflow.read_text())

        # YAML parses 'on:' as boolean True, so check for both
        assert "on" in config or True in config, "Workflow must have 'on' trigger"
        triggers = config.get("on") or config.get(True)

        # Allow either dict or list format
        if isinstance(triggers, dict):
            assert "push" in triggers or "pull_request" in triggers, \
                "Workflow should trigger on push or pull_request"

    def test_test_workflow_runs_pytest(self):
        """test.yml runs pytest."""
        test_workflow = PROJECT_ROOT / ".github" / "workflows" / "test.yml"
        content = test_workflow.read_text()
        assert "pytest" in content, "test.yml should run pytest"

    def test_test_workflow_runs_ruff(self):
        """test.yml runs ruff linter."""
        test_workflow = PROJECT_ROOT / ".github" / "workflows" / "test.yml"
        content = test_workflow.read_text()
        assert "ruff" in content, "test.yml should run ruff"

    def test_test_workflow_has_redis_service(self):
        """test.yml has Redis service for tests."""
        test_workflow = PROJECT_ROOT / ".github" / "workflows" / "test.yml"
        content = test_workflow.read_text()
        assert "redis" in content.lower(), "test.yml should have Redis service"

    def test_docker_build_workflow_exists(self):
        """docker-build.yml workflow exists."""
        docker_workflow = PROJECT_ROOT / ".github" / "workflows" / "docker-build.yml"
        assert docker_workflow.exists(), ".github/workflows/docker-build.yml not found"

    def test_docker_build_workflow_valid_yaml(self):
        """docker-build.yml is valid YAML."""
        docker_workflow = PROJECT_ROOT / ".github" / "workflows" / "docker-build.yml"
        content = docker_workflow.read_text()
        try:
            config = yaml.safe_load(content)
            assert config is not None
        except yaml.YAMLError as e:
            pytest.fail(f"Invalid YAML in docker-build.yml: {e}")

    def test_docker_build_workflow_builds_image(self):
        """docker-build.yml builds Docker image."""
        docker_workflow = PROJECT_ROOT / ".github" / "workflows" / "docker-build.yml"
        content = docker_workflow.read_text()
        assert "docker" in content.lower(), "docker-build.yml should build Docker image"


class TestDockerBuild:
    """Tests for actual Docker build (marked slow)."""

    @pytest.mark.slow
    def test_docker_build_succeeds(self):
        """Docker image builds successfully."""
        result = subprocess.run(
            ["docker", "build", "-f", "docker/Dockerfile", "-t", "knee-pipeline:test", "."],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            timeout=300,  # 5 minute timeout
        )
        assert result.returncode == 0, f"Docker build failed: {result.stderr}"

    @pytest.mark.slow
    def test_docker_image_size_reasonable(self):
        """Docker image is under 1GB."""
        # First build the image if not already built
        subprocess.run(
            ["docker", "build", "-f", "docker/Dockerfile", "-t", "knee-pipeline:test", "."],
            cwd=PROJECT_ROOT,
            capture_output=True,
            timeout=300,
        )

        # Get image size
        result = subprocess.run(
            ["docker", "image", "inspect", "knee-pipeline:test", "--format", "{{.Size}}"],
            capture_output=True,
            text=True,
        )

        if result.returncode == 0:
            size_bytes = int(result.stdout.strip())
            size_gb = size_bytes / (1024**3)
            assert size_gb < 1.0, f"Docker image too large: {size_gb:.2f} GB"


class TestDockerComposeConfig:
    """Tests for docker-compose configuration validation."""

    def test_docker_compose_config_valid(self):
        """docker-compose config validates successfully."""
        compose_dir = PROJECT_ROOT / "docker"

        # Create a temporary .env file if it doesn't exist for config validation
        env_file = compose_dir / ".env"
        env_created = False
        if not env_file.exists():
            env_file.write_text("DEBUG=false\nMAX_UPLOAD_SIZE_MB=600\n")
            env_created = True

        try:
            result = subprocess.run(
                ["docker", "compose", "config"],
                cwd=compose_dir,
                capture_output=True,
                text=True,
                timeout=30,
            )
            # docker compose config returns 0 on success
            assert result.returncode == 0, f"docker-compose config failed: {result.stderr}"
        finally:
            # Clean up temporary .env if we created it
            if env_created and env_file.exists():
                env_file.unlink()
