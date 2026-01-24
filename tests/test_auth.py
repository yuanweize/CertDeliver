"""
Tests for CertDeliver server authentication module.
"""

import pytest
from certdeliver.server.auth import (
    verify_token,
    sanitize_log_token,
    TokenValidator,
)


class TestVerifyToken:
    """Tests for token verification."""

    def test_matching_tokens(self):
        """Test that matching tokens return True."""
        assert verify_token("secret123", "secret123") is True

    def test_non_matching_tokens(self):
        """Test that non-matching tokens return False."""
        assert verify_token("secret123", "secret456") is False

    def test_empty_tokens(self):
        """Test that empty tokens return False."""
        assert verify_token("", "secret") is False
        assert verify_token("secret", "") is False
        assert verify_token("", "") is False

    def test_unicode_tokens(self):
        """Test that unicode tokens are handled correctly."""
        assert verify_token("密码123", "密码123") is True
        assert verify_token("密码123", "密码456") is False


class TestSanitizeLogToken:
    """Tests for token sanitization in logs."""

    def test_normal_token(self):
        """Test sanitization of normal token."""
        result = sanitize_log_token("mysecrettoken123")
        assert result == "***3123"
        assert "mysecret" not in result

    def test_short_token(self):
        """Test sanitization of short token."""
        result = sanitize_log_token("abc")
        assert result == "***"

    def test_empty_token(self):
        """Test sanitization of empty token."""
        result = sanitize_log_token("")
        assert result == "***"

    def test_custom_visible_chars(self):
        """Test custom visible characters count."""
        result = sanitize_log_token("mysecrettoken123", visible_chars=6)
        assert result == "***en123"


class TestTokenValidator:
    """Tests for TokenValidator class."""

    def test_valid_token(self):
        """Test validation of correct token."""
        validator = TokenValidator("valid-token")
        assert validator.validate("valid-token") is True

    def test_invalid_token(self):
        """Test validation of incorrect token."""
        validator = TokenValidator("valid-token")
        assert validator.validate("invalid-token") is False

    def test_failed_attempts_tracking(self):
        """Test that failed attempts are tracked per IP."""
        validator = TokenValidator("valid-token")
        
        # Make some failed attempts
        for _ in range(3):
            validator.validate("wrong", client_ip="192.168.1.1")
        
        assert validator._failed_attempts.get("192.168.1.1") == 3

    def test_successful_attempt_resets_count(self):
        """Test that successful attempt resets failed count."""
        validator = TokenValidator("valid-token")
        
        # Make some failed attempts
        for _ in range(3):
            validator.validate("wrong", client_ip="192.168.1.1")
        
        # Successful attempt
        validator.validate("valid-token", client_ip="192.168.1.1")
        
        assert validator._failed_attempts.get("192.168.1.1") is None

    def test_is_blocked(self):
        """Test blocking after too many failed attempts."""
        validator = TokenValidator("valid-token")
        validator._max_failed_attempts = 3
        
        # Make failed attempts up to the limit
        for _ in range(3):
            validator.validate("wrong", client_ip="192.168.1.1")
        
        assert validator.is_blocked("192.168.1.1") is True
        assert validator.is_blocked("192.168.1.2") is False

    def test_reset_attempts(self):
        """Test manual reset of failed attempts."""
        validator = TokenValidator("valid-token")
        
        validator.validate("wrong", client_ip="192.168.1.1")
        validator.reset_attempts("192.168.1.1")
        
        assert validator._failed_attempts.get("192.168.1.1") is None
