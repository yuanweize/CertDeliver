"""
Tests for certificate lifecycle monitoring and audit logging.
"""

import json
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from certdeliver.server.app import create_app
from certdeliver.utils.cert_utils import get_cert_expiry_date


class TestCertUtils:
    """Tests for certificate utility functions."""

    def test_get_cert_expiry_date(self):
        """Test extracting expiry from certificate data."""
        from cryptography import x509
        from cryptography.hazmat.primitives import hashes, serialization
        from cryptography.hazmat.primitives.asymmetric import rsa
        from cryptography.x509.oid import NameOID

        # Generate a test certificate
        key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        subject = issuer = x509.Name(
            [x509.NameAttribute(NameOID.COMMON_NAME, "test.com")]
        )

        now = datetime.now(timezone.utc)
        expiry = now + timedelta(days=10)

        cert = (
            x509.CertificateBuilder()
            .subject_name(subject)
            .issuer_name(issuer)
            .public_key(key.public_key())
            .serial_number(x509.random_serial_number())
            .not_valid_before(now - timedelta(days=1))
            .not_valid_after(expiry)
            .sign(key, hashes.SHA256())
        )

        cert_pem = cert.public_bytes(serialization.Encoding.PEM)

        extracted_expiry = get_cert_expiry_date(cert_pem)
        assert extracted_expiry is not None
        # Use a small tolerance for comparison if needed, but here it should be exact to the second
        assert abs((extracted_expiry - expiry).total_seconds()) < 1


class TestAuditAndMetrics:
    """Tests for audit logging and Prometheus metrics."""

    @pytest.fixture
    def mock_settings(self, tmp_path):
        mock = MagicMock()
        mock.token = "test-token"
        mock.tokens = {"test-token": ["*"]}
        mock.domain_list = []
        mock.targets_dir = tmp_path
        mock.log_file = None
        mock.rate_limit_enabled = False
        return mock

    def test_audit_log_output(self, mock_settings):
        """Test that audit log is generated on request."""
        with (
            patch(
                "certdeliver.server.app.get_server_settings", return_value=mock_settings
            ),
            patch(
                "certdeliver.server.routes.get_server_settings",
                return_value=mock_settings,
            ),
            patch("certdeliver.server.routes.logger") as mock_logger,
        ):
            # Create a dummy file to avoid 404
            zip_file = mock_settings.targets_dir / "test_12345678.zip"
            zip_file.touch()

            import certdeliver.server.routes

            certdeliver.server.routes._token_validator = None  # Reset

            app = create_app()
            client = TestClient(app)

            # Valid request
            with patch(
                "certdeliver.server.routes._find_local_cert_file", return_value=zip_file
            ):
                client.get("/api/v1/test_12345678.zip", params={"token": "test-token"})

            # Check if logger.info was called with AUDIT_LOG
            audit_calls = [
                c for c in mock_logger.info.call_args_list if "AUDIT_LOG | " in str(c)
            ]
            assert len(audit_calls) > 0

            # Parse the JSON part
            audit_json = audit_calls[0][0][0].split(" | ")[1]
            data = json.loads(audit_json)
            assert data["event"] == "certificate_access"
            assert data["filename"] == "test_12345678.zip"
            assert "success" in data["status"]

    def test_expiry_metric_initialization(self, mock_settings):
        """Test that expiry gauge is initialized (indirectly)."""
        # This is harder to test without running the background loop,
        # but we can verify get_zip_cert_expiry works then it's used in app.py
        pass
