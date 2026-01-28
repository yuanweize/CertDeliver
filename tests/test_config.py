"""
Tests for CertDeliver configuration module.
"""

import os
from pathlib import Path
from unittest.mock import patch

from certdeliver.config import (
    ClientSettings,
    HookSettings,
    ServerSettings,
    setup_logging,
)


class TestServerSettings:
    """Tests for ServerSettings."""

    def test_default_values(self):
        """Test default configuration values."""
        with patch.dict(os.environ, {}, clear=True):
            settings = ServerSettings()
            assert settings.host == "0.0.0.0"
            assert settings.port == 8000
            assert settings.rate_limit_enabled is True

    def test_env_variable_loading(self):
        """Test loading configuration from environment variables."""
        env_vars = {
            "CERTDELIVER_TOKEN": "test-token-123",
            "CERTDELIVER_DOMAIN_LIST": "example.com,test.com",
            "CERTDELIVER_PORT": "9000",
        }
        with patch.dict(os.environ, env_vars, clear=True):
            settings = ServerSettings()
            assert settings.token == "test-token-123"
            assert settings.domain_list == ["example.com", "test.com"]
            assert settings.port == 9000

    def test_domain_list_parsing(self):
        """Test domain list is properly parsed from comma-separated string."""
        env_vars = {
            "CERTDELIVER_DOMAIN_LIST": "  a.com , b.com,  c.com  ",
        }
        with patch.dict(os.environ, env_vars, clear=True):
            settings = ServerSettings()
            assert settings.domain_list == ["a.com", "b.com", "c.com"]


class TestClientSettings:
    """Tests for ClientSettings."""

    def test_default_values(self):
        """Test default configuration values."""
        with patch.dict(os.environ, {}, clear=True):
            settings = ClientSettings()
            assert settings.timeout == 30
            assert settings.verify_ssl is True
            assert settings.cert_name == "cert"

    def test_path_parsing(self):
        """Test path values are converted to Path objects."""
        env_vars = {
            "CERTDELIVER_CLIENT_CERT_DEST_PATH": "/custom/path/certs",
        }
        with patch.dict(os.environ, env_vars, clear=True):
            settings = ClientSettings()
            assert isinstance(settings.cert_dest_path, Path)
            assert str(settings.cert_dest_path) == "/custom/path/certs"


class TestHookSettings:
    """Tests for HookSettings."""

    def test_default_values(self):
        """Test default configuration values."""
        with patch.dict(os.environ, {}, clear=True):
            settings = HookSettings()
            assert settings.cert_name == "cert"
            assert isinstance(settings.letsencrypt_live_dir, Path)


class TestSetupLogging:
    """Tests for logging setup."""

    def test_setup_logging_returns_logger(self):
        """Test that setup_logging returns a logger instance."""
        logger = setup_logging(component="test")
        assert logger is not None
        assert logger.name == "test"

    def test_setup_logging_with_file(self, tmp_path):
        """Test logging setup with file output."""
        log_file = tmp_path / "test.log"
        logger = setup_logging(log_file=log_file, component="test_file")
        logger.info("Test message")

        # Check file was created
        assert log_file.exists()
