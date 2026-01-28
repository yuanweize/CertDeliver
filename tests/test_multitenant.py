"""
Tests for multi-tenant support and granular permissions.
"""

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from certdeliver.config import ServerSettings
from certdeliver.server.app import create_app
from certdeliver.server.auth import verify_access


class TestMultiTenantAuth:
    """Tests for multi-tenant authentication logic."""

    def test_verify_access_legacy_token(self):
        """Test access with legacy master token (wildcard permission)."""
        tokens = {"master-token": ["*"]}
        assert verify_access("master-token", "any_file.zip", tokens) is True
        assert verify_access("master-token", "another_file", tokens) is True

    def test_verify_access_specific_token(self):
        """Test access with specific file permission."""
        tokens = {"client-a": ["client_a.zip"]}
        # Exact match
        assert verify_access("client-a", "client_a.zip", tokens) is True
        # Mismatch
        assert verify_access("client-a", "client_b.zip", tokens) is False

    def test_verify_access_wildcard_pattern(self):
        """Test access with wildcard patterns."""
        tokens = {"client-group": ["group_*.zip"]}
        assert verify_access("client-group", "group_1.zip", tokens) is True
        assert verify_access("client-group", "group_test.zip", tokens) is True
        assert verify_access("client-group", "other_1.zip", tokens) is False

    def test_verify_access_multiple_patterns(self):
        """Test access with multiple permission patterns."""
        tokens = {"admin": ["log_*.txt", "config_*.json"]}
        assert verify_access("admin", "log_2024.txt", tokens) is True
        assert verify_access("admin", "config_v1.json", tokens) is True
        assert verify_access("admin", "data.db", tokens) is False

    def test_verify_access_invalid_token(self):
        """Test access with invalid token."""
        tokens = {"valid": ["*"]}
        assert verify_access("invalid", "any.zip", tokens) is False
        assert verify_access("", "any.zip", tokens) is False


class TestConfigParsing:
    """Tests for configuration parsing."""

    def test_parse_tokens_json(self):
        """Test parsing tokens from JSON string."""
        json_str = '{"token1": ["file1"], "token2": ["file2"]}'
        tokens = ServerSettings.parse_tokens(json_str)
        assert tokens["token1"] == ["file1"]
        assert tokens["token2"] == ["file2"]

    def test_parse_tokens_invalid_json(self):
        """Test parsing invalid JSON string returns empty dict."""
        tokens = ServerSettings.parse_tokens("{invalid-json}")
        assert tokens == {}

    def test_parse_tokens_dict(self):
        """Test parsing dict input (pass-through)."""
        input_dict = {"t": ["f"]}
        tokens = ServerSettings.parse_tokens(input_dict)
        assert tokens == input_dict

    def test_legacy_token_merge(self):
        """Test that legacy token is merged into tokens dict."""
        settings = ServerSettings(token="legacy", tokens={})
        assert "legacy" in settings.tokens
        assert settings.tokens["legacy"] == ["*"]


class TestMultiTenantRoutes:
    """Tests for API routes with multi-tenant config."""

    @pytest.fixture
    def mock_settings(self):
        mock = MagicMock()
        mock.token = ""
        mock.tokens = {
            "master": ["*"],
            "client-a": ["cert_a_*.zip"],
            "client-b": ["cert_b_*.zip"],
        }
        mock.domain_list = []
        mock.host = "0.0.0.0"
        mock.port = 8000
        mock.targets_dir = MagicMock()
        mock.targets_dir.exists.return_value = True
        mock.targets_dir.glob.return_value = []
        mock.log_file = None
        mock.rate_limit_enabled = False
        return mock

    @pytest.fixture
    def client(self, mock_settings):
        """Create test client with mocked settings."""
        with (
            patch(
                "certdeliver.server.app.get_server_settings", return_value=mock_settings
            ),
            patch(
                "certdeliver.server.routes.get_server_settings",
                return_value=mock_settings,
            ),
        ):
            # Reset global variables in routes
            import certdeliver.server.routes

            certdeliver.server.routes._token_validator = None

            app = create_app()
            with TestClient(app) as c:
                yield c

    def test_access_denied_forbidden(self, client):
        """Test that authorized token gets 403 for unauthorized file."""
        # client-a allowed for cert_a_*, trying to access cert_b_1.zip
        # Note: We need a file that 'exists' or at least pass validation step

        # Mock finding a file so we don't hit 404 first
        # We need a valid local file name to pass the server configuration check
        mock_local_file = MagicMock()
        mock_local_file.name = "cert_a_123.zip"

        with patch(
            "certdeliver.server.routes._find_local_cert_file",
            return_value=mock_local_file,
        ):
            # Requesting a file that client-a is NOT allowed to access (client-a only allows cert_a_*)
            response = client.get("/api/v1/cert_b_1.zip", params={"token": "client-a"})
            # Should be 403 Forbidden
            assert response.status_code == 403

    def test_access_allowed(self, client):
        """Test that authorized token gets access."""
        # Mock file existence
        mock_path = MagicMock()
        mock_path.name = "cert_a_123.zip"

        with patch(
            "certdeliver.server.routes._find_local_cert_file", return_value=mock_path
        ):
            response = client.get(
                "/api/v1/cert_a_123.zip", params={"token": "client-a"}
            )
            # 200 OK means auth passed (response might be json "up to date" or file)
            assert response.status_code in [
                200,
                400,
            ]  # 400 if mismatch, but auth passed
            assert response.status_code != 403
            assert response.status_code != 401
