"""
Authentication and authorization utilities for CertDeliver server.
"""

import logging
import secrets

logger = logging.getLogger(__name__)


def verify_token(provided_token: str, expected_token: str) -> bool:
    """
    Securely compare tokens using constant-time comparison.

    This prevents timing attacks by ensuring the comparison takes
    the same amount of time regardless of how many characters match.

    Args:
        provided_token: The token provided by the client.
        expected_token: The expected valid token.

    Returns:
        True if tokens match, False otherwise.
    """
    if not provided_token or not expected_token:
        return False

    # Use constant-time comparison to prevent timing attacks
    return secrets.compare_digest(
        provided_token.encode("utf-8"), expected_token.encode("utf-8")
    )


def verify_access(
    provided_token: str, filename: str, tokens_map: dict[str, list[str]]
) -> bool:
    """
    Verify if token is valid and has access to the requested file using fnmatch.

    Args:
        provided_token: Token provided by the requesting client.
        filename: Name of the file being requested.
        tokens_map: Dictionary mapping valid tokens to lists of allowed glob patterns.

    Returns:
        True if token is valid and authorized for the file.
    """
    if not provided_token:
        return False

    import fnmatch

    # Iterate insecurely through keys is fine here since we secure check matches
    # But secrets.compare_digest expects knowing the valid token first.
    # To avoid timing leaks based on WHOSE token it is, we should iterate all.
    # However, in this multi-tenant model without user IDs, we must iterate keys.
    # Mitigation: The comparison itself is constant time PER token.

    for valid_token, patterns in tokens_map.items():
        if secrets.compare_digest(
            provided_token.encode("utf-8"), valid_token.encode("utf-8")
        ):
            # Token matches, now check permissions
            for pattern in patterns:
                if fnmatch.fnmatch(filename, pattern):
                    return True
            # Token found but no matching pattern for file
            return False

    return False


def sanitize_log_token(token: str, visible_chars: int = 4) -> str:
    """
    Sanitize token for logging by masking most characters.

    Args:
        token: The token to sanitize.
        visible_chars: Number of characters to show at the end.

    Returns:
        Sanitized token string.
    """
    if not token or len(token) <= visible_chars:
        return "***"
    return f"***{token[-visible_chars:]}"


class TokenValidator:
    """Token validation with rate limiting support."""

    def __init__(self, tokens_map: dict[str, list[str]]):
        """
        Initialize the token validator.

        Args:
            tokens_map: Dictionary of allowed tokens and their permissions.
        """
        self.tokens_map = tokens_map
        self._failed_attempts: dict[str, int] = {}
        self._max_failed_attempts = 5

    def validate(
        self, token: str, filename: str = "", client_ip: str | None = None
    ) -> bool:
        """
        Validate the provided token for specific access.

        Args:
            token: Token to validate.
            filename: File being accessed (optional, for permission check).
            client_ip: Client IP for rate limiting (optional).

        Returns:
            True if valid, False otherwise.
        """
        is_valid = verify_access(token, filename, self.tokens_map)

        if client_ip:
            if is_valid:
                # Reset failed attempts on success
                self._failed_attempts.pop(client_ip, None)
            else:
                # Track failed attempts
                self._failed_attempts[client_ip] = (
                    self._failed_attempts.get(client_ip, 0) + 1
                )

                if self._failed_attempts[client_ip] >= self._max_failed_attempts:
                    logger.warning(f"Too many failed auth attempts from {client_ip}")

        return is_valid

    def is_blocked(self, client_ip: str) -> bool:
        """Check if a client IP is blocked due to too many failed attempts."""
        return self._failed_attempts.get(client_ip, 0) >= self._max_failed_attempts

    def reset_attempts(self, client_ip: str) -> None:
        """Reset failed attempts for a client IP."""
        self._failed_attempts.pop(client_ip, None)
