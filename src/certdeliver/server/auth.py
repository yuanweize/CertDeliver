"""
Authentication and authorization utilities for CertDeliver server.
"""

import secrets
import logging
from typing import Optional
from functools import wraps

from fastapi import HTTPException, Request, status

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
        provided_token.encode('utf-8'),
        expected_token.encode('utf-8')
    )


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
    
    def __init__(self, expected_token: str):
        """
        Initialize the token validator.
        
        Args:
            expected_token: The valid API token.
        """
        self.expected_token = expected_token
        self._failed_attempts: dict[str, int] = {}
        self._max_failed_attempts = 5
    
    def validate(self, token: str, client_ip: Optional[str] = None) -> bool:
        """
        Validate the provided token.
        
        Args:
            token: Token to validate.
            client_ip: Client IP for rate limiting (optional).
        
        Returns:
            True if valid, False otherwise.
        """
        is_valid = verify_token(token, self.expected_token)
        
        if client_ip:
            if is_valid:
                # Reset failed attempts on success
                self._failed_attempts.pop(client_ip, None)
            else:
                # Track failed attempts
                self._failed_attempts[client_ip] = \
                    self._failed_attempts.get(client_ip, 0) + 1
                
                if self._failed_attempts[client_ip] >= self._max_failed_attempts:
                    logger.warning(
                        f"Too many failed auth attempts from {client_ip}"
                    )
        
        return is_valid
    
    def is_blocked(self, client_ip: str) -> bool:
        """Check if a client IP is blocked due to too many failed attempts."""
        return self._failed_attempts.get(client_ip, 0) >= self._max_failed_attempts
    
    def reset_attempts(self, client_ip: str) -> None:
        """Reset failed attempts for a client IP."""
        self._failed_attempts.pop(client_ip, None)
