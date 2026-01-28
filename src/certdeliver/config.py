"""
Configuration management for CertDeliver.
Supports environment variables, .env files, and YAML configuration.
"""

import logging
from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Configure module logger
logger = logging.getLogger(__name__)


class ServerSettings(BaseSettings):
    """Server configuration settings."""

    model_config = SettingsConfigDict(
        env_prefix="CERTDELIVER_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Authentication
    token: str = Field(default="", description="API authentication token")

    # Domain whitelist
    domain_list: list[str] | str = Field(
        default_factory=list,
        description="List of allowed domains for whitelist verification",
    )

    # Server settings
    host: str = Field(default="0.0.0.0", description="Server bind address")
    port: int = Field(default=8000, description="Server port")

    # Paths
    targets_dir: Path = Field(
        default=Path("/opt/CertDeliver/targets"),
        description="Directory containing certificate files",
    )
    log_file: Path | None = Field(
        default=None, description="Log file path (None for stdout)"
    )

    # Rate limiting
    rate_limit_enabled: bool = Field(default=True, description="Enable rate limiting")
    rate_limit_requests: int = Field(default=100, description="Max requests per minute")

    @field_validator("domain_list", mode="before")
    @classmethod
    def parse_domain_list(cls, v: list[str] | str) -> list[str]:
        """Parse domain list from comma-separated string or list."""
        if isinstance(v, str):
            return [d.strip() for d in v.split(",") if d.strip()]
        return v

    @field_validator("targets_dir", mode="before")
    @classmethod
    def parse_path(cls, v: str | Path) -> Path:
        """Convert string to Path."""
        if isinstance(v, str):
            return Path(v)
        return v


class ClientSettings(BaseSettings):
    """Client configuration settings."""

    model_config = SettingsConfigDict(
        env_prefix="CERTDELIVER_CLIENT_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Server connection
    server_url: str = Field(
        default="https://localhost:8000/api/v1/", description="CertDeliver server URL"
    )
    token: str = Field(default="", description="API authentication token")

    # Certificate settings
    cert_name: str = Field(
        default="cert", description="Certificate name (matches certbot --cert-name)"
    )

    # Paths
    cert_dest_path: Path = Field(
        default=Path("/etc/ssl/certs/certdeliver"),
        description="Destination path for certificates",
    )
    local_cache_dir: Path = Field(
        default=Path("/var/cache/certdeliver"),
        description="Local cache directory for downloaded certs",
    )

    # Post-update command (optional)
    post_update_command: str | None = Field(
        default=None,
        description="Command to run after certificate update (e.g., 'systemctl reload nginx')",
    )

    # Request settings
    timeout: int = Field(default=30, description="Request timeout in seconds")
    verify_ssl: bool = Field(default=True, description="Verify SSL certificates")

    @field_validator("cert_dest_path", "local_cache_dir", mode="before")
    @classmethod
    def parse_path(cls, v: str | Path) -> Path:
        """Convert string to Path."""
        if isinstance(v, str):
            return Path(v)
        return v


class HookSettings(BaseSettings):
    """Certbot hook configuration settings."""

    model_config = SettingsConfigDict(
        env_prefix="CERTDELIVER_HOOK_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Paths
    letsencrypt_live_dir: Path = Field(
        default=Path("/etc/letsencrypt/live"),
        description="Let's Encrypt live certificates directory",
    )
    output_dir: Path = Field(
        default=Path("/opt/CertDeliver/targets"),
        description="Output directory for packaged certificates",
    )
    cert_name: str = Field(default="cert", description="Certificate name to package")

    @field_validator("letsencrypt_live_dir", "output_dir", mode="before")
    @classmethod
    def parse_path(cls, v: str | Path) -> Path:
        """Convert string to Path."""
        if isinstance(v, str):
            return Path(v)
        return v


@lru_cache
def get_server_settings() -> ServerSettings:
    """Get cached server settings instance."""
    return ServerSettings()


@lru_cache
def get_client_settings() -> ClientSettings:
    """Get cached client settings instance."""
    return ClientSettings()


@lru_cache
def get_hook_settings() -> HookSettings:
    """Get cached hook settings instance."""
    return HookSettings()


def setup_logging(
    log_file: Path | None = None,
    level: int = logging.INFO,
    component: str = "certdeliver",
) -> logging.Logger:
    """
    Configure logging for CertDeliver components.

    Args:
        log_file: Optional path to log file. If None, logs to stdout.
        level: Logging level.
        component: Component name for logger.

    Returns:
        Configured logger instance.
    """
    log_format = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"

    handlers: list = []

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(logging.Formatter(log_format))
    handlers.append(console_handler)

    # File handler (if specified)
    if log_file:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setFormatter(logging.Formatter(log_format))
        handlers.append(file_handler)

    # Configure root logger for this component
    logger = logging.getLogger(component)
    logger.setLevel(level)
    logger.handlers = handlers

    return logger
