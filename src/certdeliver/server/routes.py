"""
API routes for CertDeliver server.
"""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Query, Request
from fastapi.responses import FileResponse, JSONResponse

from ..config import get_server_settings
from .auth import TokenValidator, sanitize_log_token
from .whitelist import WhitelistManager

logger = logging.getLogger(__name__)

# Initialize router
router = APIRouter(prefix="/api/v1", tags=["certificates"])

# These will be initialized when the app starts
_token_validator: TokenValidator | None = None
_whitelist_manager: WhitelistManager | None = None


def init_routes(
    token: str = "",
    domains: list[str] | None = None,
    tokens: dict[str, list[str]] | None = None,
) -> None:
    """
    Initialize route dependencies.

    Args:
        token: API authentication token (legacy).
        domains: List of allowed domains for whitelist.
        tokens: Dictionary of valid tokens and their permissions (multi-tenant).
    """
    global _token_validator, _whitelist_manager

    # Use provided tokens map, or fallback to legacy token if tokens map is empty
    auth_tokens = tokens or {}
    if not auth_tokens and token:
        auth_tokens = {token: ["*"]}

    _token_validator = TokenValidator(auth_tokens)
    _whitelist_manager = WhitelistManager(domains or [])


def _get_client_ip(request: Request) -> str:
    """Extract client IP from request, considering proxy headers."""
    # Check for forwarded headers (when behind proxy)
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        # Get the first (original) client IP
        return forwarded_for.split(",")[0].strip()

    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip.strip()

    # Fallback to direct connection IP
    return request.client.host if request.client else "unknown"


def _parse_cert_filename(filename: str) -> tuple[str, int]:
    """
    Parse certificate filename to extract name and timestamp.

    Expected format: {cert_name}_{timestamp}.zip

    Args:
        filename: The filename to parse.

    Returns:
        Tuple of (cert_name, timestamp).

    Raises:
        ValueError: If filename format is invalid.
    """
    try:
        # Remove .zip extension if present
        base_name = filename.replace(".zip", "")
        parts = base_name.rsplit("_", 1)

        if len(parts) != 2:
            raise ValueError("Invalid filename format")

        cert_name = parts[0]
        timestamp = int(parts[1])

        return cert_name, timestamp
    except (ValueError, IndexError) as e:
        raise ValueError(f"Invalid certificate filename format: {filename}") from e


def _find_local_cert_file(targets_dir: Path) -> Path | None:
    """
    Find the certificate file in the targets directory.

    Args:
        targets_dir: Path to the targets directory.

    Returns:
        Path to the cert file, or None if not found.
    """
    if not targets_dir.exists():
        return None

    zip_files = list(targets_dir.glob("*.zip"))

    if len(zip_files) == 0:
        return None
    elif len(zip_files) > 1:
        logger.warning(f"Multiple cert files found in {targets_dir}")
        # Return the newest one
        return max(zip_files, key=lambda f: f.stat().st_mtime)

    return zip_files[0]


def _log_audit(
    request: Request,
    filename: str,
    status: str,
    token: str = "",
    reason: str = "",
) -> None:
    """
    Log a structured audit record for security events.
    """
    client_ip = _get_client_ip(request)
    user_agent = request.headers.get("user-agent", "unknown")
    masked_token = sanitize_log_token(token) if token else "none"

    audit_data = {
        "event": "certificate_access",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "client_ip": client_ip,
        "filename": filename,
        "status": status,
        "token_masked": masked_token,
        "user_agent": user_agent,
        "reason": reason,
    }

    # Log as a single line JSON-like string for easy parsing
    logger.info(f"AUDIT_LOG | {json.dumps(audit_data)}")


@router.get("/{file_name}", response_model=None)
async def get_certificate(
    file_name: str,
    request: Request,
    token: str = Query(..., description="API authentication token"),
    download: bool = Query(False, description="Force download mode"),
) -> FileResponse | JSONResponse:
    """
    Get or download a certificate file.

    This endpoint handles both update checks and file downloads:
    - If `download=True`: Returns the file directly
    - If `download=False`: Compares timestamps and returns file if update available

    Args:
        file_name: Certificate file name (format: {name}_{timestamp} or {name}_{timestamp}.zip)
        request: FastAPI request object
        token: API authentication token
        download: If True, force download the file

    Returns:
        FileResponse with the certificate file, or JSON error response.
    """
    settings = get_server_settings()
    client_ip = _get_client_ip(request)

    logger.info(
        f"Certificate request: client={client_ip}, "
        f"file={file_name}, download={download}, "
        f"token={sanitize_log_token(token)}"
    )

    # Check whitelist
    if _whitelist_manager and settings.domain_list:
        if not await _whitelist_manager.is_whitelisted(client_ip):
            logger.warning(f"Client {client_ip} not in whitelist")
            _log_audit(request, file_name, "denied", token, "client_not_whitelisted")
            return JSONResponse(
                status_code=403,
                content={"status": "error", "message": "Client IP not in whitelist"},
            )

    # Validate token
    if _token_validator:
        if _token_validator.is_blocked(client_ip):
            logger.warning(
                f"Client {client_ip} is blocked due to too many failed attempts"
            )
            _log_audit(request, file_name, "denied", token, "client_blocked")
            return JSONResponse(
                status_code=429,
                content={
                    "status": "error",
                    "message": "Too many failed authentication attempts",
                },
            )

        # Validate token with filename for permission check
        # We need to parse filename first to check permissions against it
        try:
            remote_name_check, _ = _parse_cert_filename(file_name)
            # Use the original filename for pattern matching
            target_file = file_name
        except ValueError:
            # Even if invalid filename, we pass it to validate to check if token exists at least
            target_file = file_name

        if not _token_validator.validate(token, target_file, client_ip):
            logger.warning(
                f"Invalid token or unauthorized access from client {client_ip} for {file_name}"
            )
            _log_audit(
                request, file_name, "denied", token, "unauthorized_or_invalid_token"
            )
            return JSONResponse(
                status_code=403,
                content={"status": "error", "message": "Unauthorized access"},
            )

    # Find local certificate file
    local_cert = _find_local_cert_file(settings.targets_dir)

    if not local_cert:
        logger.error("No certificate file found in targets directory")
        _log_audit(request, file_name, "error", token, "server_no_local_cert_file")
        return JSONResponse(
            status_code=404,
            content={"status": "error", "message": "No certificate file available"},
        )

    # Parse local and remote filenames
    try:
        local_name, local_timestamp = _parse_cert_filename(local_cert.name)
    except ValueError as e:
        logger.error(f"Invalid local cert filename: {e}")
        _log_audit(request, file_name, "error", token, "server_invalid_local_filename")
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": "Server configuration error"},
        )

    try:
        remote_name, remote_timestamp = _parse_cert_filename(file_name)
    except ValueError as e:
        logger.warning(f"Invalid remote filename from {client_ip}: {e}")
        _log_audit(
            request, file_name, "denied", token, "client_invalid_filename_format"
        )
        return JSONResponse(
            status_code=400,
            content={"status": "error", "message": "Invalid filename format"},
        )

    # Handle download mode (first time download)
    if download:
        if local_name == remote_name:
            logger.info(f"First time download for {client_ip}: {local_cert.name}")
            _log_audit(request, file_name, "success_download", token, "forced_download")
            return FileResponse(
                path=local_cert, filename=local_cert.name, media_type="application/zip"
            )
        else:
            logger.warning(
                f"File name mismatch for download: {local_name} != {remote_name}"
            )
            _log_audit(
                request,
                file_name,
                "denied",
                token,
                f"download_name_mismatch_expected_{local_name}",
            )
            return JSONResponse(
                status_code=404,
                content={"status": "error", "message": "Certificate not found"},
            )

    # Handle update check mode
    if local_name != remote_name:
        logger.info(f"File name mismatch: {local_name} != {remote_name}")
        _log_audit(
            request,
            file_name,
            "denied",
            token,
            f"update_check_name_mismatch_expected_{local_name}",
        )
        return JSONResponse(
            status_code=400,
            content={"status": "error", "message": "Certificate name mismatch"},
        )

    if local_timestamp == remote_timestamp:
        logger.info(f"Certificate up to date for {client_ip}")
        _log_audit(request, file_name, "success_up_to_date", token)
        return JSONResponse(
            status_code=200,
            content={"status": "ok", "message": "Certificate is up to date"},
        )

    if local_timestamp > remote_timestamp:
        # Server has newer version, send it
        logger.info(f"Sending updated certificate to {client_ip}: {local_cert.name}")
        return FileResponse(
            path=local_cert, filename=local_cert.name, media_type="application/zip"
        )

    # Remote timestamp is newer than local (shouldn't happen normally)
    logger.warning(
        f"Remote timestamp newer than local: {remote_timestamp} > {local_timestamp}"
    )
    return JSONResponse(
        status_code=400, content={"status": "error", "message": "Invalid timestamp"}
    )
