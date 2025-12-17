"""
Stage 1.7: HTTPS with Caddy Tests

Tests verify:
- Caddyfile exists and has correct configuration
- Docker Compose includes Caddy service
- Caddy service is properly configured
"""

from pathlib import Path

import pytest
import yaml

# Mark all tests in this module as stage_1_7
pytestmark = pytest.mark.stage_1_7

# Project root directory
PROJECT_ROOT = Path(__file__).parent.parent


class TestCaddyfile:
    """Tests for Caddyfile configuration."""

    def test_caddyfile_exists(self):
        """Caddyfile exists in docker/ directory."""
        caddyfile = PROJECT_ROOT / "docker" / "Caddyfile"
        assert caddyfile.exists(), "docker/Caddyfile not found"

    def test_caddyfile_has_domain(self):
        """Caddyfile configures the main domain."""
        caddyfile = PROJECT_ROOT / "docker" / "Caddyfile"
        content = caddyfile.read_text()
        assert "openmsk.com" in content, "Caddyfile should configure openmsk.com"

    def test_caddyfile_has_reverse_proxy(self):
        """Caddyfile includes reverse_proxy directive."""
        caddyfile = PROJECT_ROOT / "docker" / "Caddyfile"
        content = caddyfile.read_text()
        assert "reverse_proxy" in content, "Caddyfile should have reverse_proxy"

    def test_caddyfile_proxies_to_web(self):
        """Caddyfile proxies to web service on port 8000."""
        caddyfile = PROJECT_ROOT / "docker" / "Caddyfile"
        content = caddyfile.read_text()
        assert "web:8000" in content, "Caddyfile should proxy to web:8000"

    def test_caddyfile_has_www_redirect(self):
        """Caddyfile redirects www to non-www."""
        caddyfile = PROJECT_ROOT / "docker" / "Caddyfile"
        content = caddyfile.read_text()
        assert "www.openmsk.com" in content, "Caddyfile should handle www subdomain"
        assert "redir" in content, "Caddyfile should redirect www"


class TestDockerComposeWithCaddy:
    """Tests for Docker Compose Caddy configuration."""

    def test_docker_compose_has_caddy_service(self):
        """docker-compose.yml includes caddy service."""
        compose_file = PROJECT_ROOT / "docker" / "docker-compose.yml"
        config = yaml.safe_load(compose_file.read_text())

        assert "services" in config
        assert "caddy" in config["services"], "Must have caddy service"

    def test_caddy_uses_correct_image(self):
        """Caddy service uses caddy:2-alpine image."""
        compose_file = PROJECT_ROOT / "docker" / "docker-compose.yml"
        config = yaml.safe_load(compose_file.read_text())
        caddy = config["services"]["caddy"]

        assert "caddy" in caddy.get("image", ""), "Caddy should use caddy image"

    def test_caddy_exposes_port_80(self):
        """Caddy service exposes port 80 for HTTP."""
        compose_file = PROJECT_ROOT / "docker" / "docker-compose.yml"
        config = yaml.safe_load(compose_file.read_text())
        caddy = config["services"]["caddy"]

        ports = [str(p) for p in caddy.get("ports", [])]
        assert any("80" in p for p in ports), "Caddy should expose port 80"

    def test_caddy_exposes_port_443(self):
        """Caddy service exposes port 443 for HTTPS."""
        compose_file = PROJECT_ROOT / "docker" / "docker-compose.yml"
        config = yaml.safe_load(compose_file.read_text())
        caddy = config["services"]["caddy"]

        ports = [str(p) for p in caddy.get("ports", [])]
        assert any("443" in p for p in ports), "Caddy should expose port 443"

    def test_caddy_mounts_caddyfile(self):
        """Caddy service mounts Caddyfile."""
        compose_file = PROJECT_ROOT / "docker" / "docker-compose.yml"
        config = yaml.safe_load(compose_file.read_text())
        caddy = config["services"]["caddy"]

        volumes = caddy.get("volumes", [])
        volume_strings = [str(v) for v in volumes]
        assert any("Caddyfile" in v for v in volume_strings), \
            "Caddy should mount Caddyfile"

    def test_caddy_has_data_volume(self):
        """Caddy service has data volume for certificates."""
        compose_file = PROJECT_ROOT / "docker" / "docker-compose.yml"
        config = yaml.safe_load(compose_file.read_text())
        caddy = config["services"]["caddy"]

        volumes = caddy.get("volumes", [])
        volume_strings = [str(v) for v in volumes]
        assert any("caddy_data" in v or "/data" in v for v in volume_strings), \
            "Caddy should have data volume for certificates"

    def test_caddy_depends_on_web(self):
        """Caddy service depends on web service."""
        compose_file = PROJECT_ROOT / "docker" / "docker-compose.yml"
        config = yaml.safe_load(compose_file.read_text())
        caddy = config["services"]["caddy"]

        depends_on = caddy.get("depends_on", [])
        # depends_on can be a list or dict
        if isinstance(depends_on, dict):
            assert "web" in depends_on, "Caddy should depend on web"
        else:
            assert "web" in depends_on, "Caddy should depend on web"

    def test_web_not_exposed_externally(self):
        """Web service uses 'expose' not 'ports' (internal only)."""
        compose_file = PROJECT_ROOT / "docker" / "docker-compose.yml"
        config = yaml.safe_load(compose_file.read_text())
        web = config["services"]["web"]

        # Should have 'expose' not 'ports'
        assert "expose" in web, "Web should use 'expose' for internal access"
        # Should NOT have external ports
        assert "ports" not in web, "Web should not expose ports externally"

    def test_redis_not_exposed_externally(self):
        """Redis service uses 'expose' not 'ports' (internal only)."""
        compose_file = PROJECT_ROOT / "docker" / "docker-compose.yml"
        config = yaml.safe_load(compose_file.read_text())
        redis = config["services"]["redis"]

        # Should have 'expose' not 'ports'
        assert "expose" in redis, "Redis should use 'expose' for internal access"
        # Should NOT have external ports
        assert "ports" not in redis, "Redis should not expose ports externally"

    def test_caddy_volumes_defined(self):
        """Docker compose defines caddy volumes."""
        compose_file = PROJECT_ROOT / "docker" / "docker-compose.yml"
        config = yaml.safe_load(compose_file.read_text())

        volumes = config.get("volumes", {})
        assert "caddy_data" in volumes, "Should define caddy_data volume"
        assert "caddy_config" in volumes, "Should define caddy_config volume"


class TestSecurityConfiguration:
    """Tests for security-related configuration."""

    def test_only_caddy_exposed_to_internet(self):
        """Only Caddy service has external ports."""
        compose_file = PROJECT_ROOT / "docker" / "docker-compose.yml"
        config = yaml.safe_load(compose_file.read_text())

        services_with_ports = []
        for name, service in config["services"].items():
            if "ports" in service:
                services_with_ports.append(name)

        assert services_with_ports == ["caddy"], \
            f"Only caddy should have external ports, found: {services_with_ports}"
