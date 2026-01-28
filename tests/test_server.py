"""
Tests for CertDeliver server API routes.
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from certdeliver.server.app import create_app
from certdeliver.server.routes import _parse_cert_filename


class TestParseCertFilename:
    """Tests for certificate filename parsing."""

    def test_valid_filename_with_extension(self):
        """Test parsing valid filename with .zip extension."""
        name, timestamp = _parse_cert_filename("mycert_1699999999.zip")
        assert name == "mycert"
        assert timestamp == 1699999999

    def test_valid_filename_without_extension(self):
        """Test parsing valid filename without extension."""
        name, timestamp = _parse_cert_filename("mycert_1699999999")
        assert name == "mycert"
        assert timestamp == 1699999999

    def test_invalid_filename_no_underscore(self):
        """Test that invalid filename raises ValueError."""
        with pytest.raises(ValueError):
            _parse_cert_filename("invalidname.zip")

    def test_invalid_filename_no_timestamp(self):
        """Test that filename without timestamp raises ValueError."""
        with pytest.raises(ValueError):
            _parse_cert_filename("mycert_notanumber.zip")


class TestServerApp:
    """Tests for the server application."""

    @pytest.fixture
    def mock_settings(self):
        """Create mock settings."""
        mock = MagicMock()
        mock.token = "test-token"
        mock.domain_list = []
        mock.host = "0.0.0.0"
        mock.port = 8000
        mock.targets_dir = Path("/tmp/test")
        mock.log_file = None
        mock.rate_limit_enabled = False
        return mock

    @pytest.fixture
    def client(self, mock_settings):
        """Create test client with mocked settings."""
        with patch(
            "certdeliver.server.app.get_server_settings", return_value=mock_settings
        ):
            with patch(
                "certdeliver.server.routes.get_server_settings",
                return_value=mock_settings,
            ):
                app = create_app()
                return TestClient(app)

    def test_root_endpoint(self, client):
        """Test root endpoint returns welcome message."""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "CertDeliver" in data.get("service", "")

    def test_health_endpoint(self, client, mock_settings):
        """Test health check endpoint."""
        # Mock directory existence
        with patch("pathlib.Path.exists", return_value=True):
            with patch("pathlib.Path.glob", return_value=[]):
                response = client.get("/health")
                assert response.status_code == 200
                data = response.json()
                assert data.get("status") == "healthy"
                assert "available_certs" in data

    def test_health_endpoint_degraded(self, client, mock_settings):
        """Test health check degraded when targets dir missing."""
        with patch("pathlib.Path.exists", return_value=False):
            response = client.get("/health")
            assert response.status_code == 503
            data = response.json()
            assert data.get("status") == "degraded"
            assert "error" in data

    def test_metrics_endpoint(self, client):
        """Test Prometheus metrics endpoint exists."""
        response = client.get("/metrics")
        assert response.status_code == 200
        assert "certdeliver" in response.text or "python" in response.text
