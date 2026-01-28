"""
Utilities for handling certificates and extraction.
"""

import logging
import zipfile
from datetime import datetime, timezone
from pathlib import Path

from cryptography import x509
from cryptography.hazmat.backends import default_backend

logger = logging.getLogger(__name__)


def get_cert_expiry_date(cert_data: bytes) -> datetime | None:
    """
    Parse certificate data and extract expiration date.

    Args:
        cert_data: PEM encoded certificate data.

    Returns:
        Expiration datetime or None if parsing fails.
    """
    try:
        from typing import cast

        cert = x509.load_pem_x509_certificate(cert_data, default_backend())
        # Use not_valid_after_utc for newer cryptography versions, fall back to not_valid_after
        try:
            return cast(datetime, cert.not_valid_after_utc)
        except AttributeError:
            # Older versions return naive datetime in UTC
            expiry = cert.not_valid_after
            if expiry.tzinfo is None:
                expiry = expiry.replace(tzinfo=timezone.utc)
            return cast(datetime, expiry)
    except Exception as e:
        logger.error(f"Failed to parse certificate: {e}")
        return None


def get_zip_cert_expiry(zip_path: Path) -> datetime | None:
    """
    Open a ZIP archive and find the first .crt file to get its expiry date.

    Args:
        zip_path: Path to the .zip archive.

    Returns:
        Expiration datetime or None if no .crt found or error occurred.
    """
    if not zip_path.exists():
        return None

    try:
        with zipfile.ZipFile(zip_path, "r") as z:
            for name in z.namelist():
                if name.endswith(".crt") or name.endswith(".pem"):
                    # Avoid reading fullchain or other files if possible, usually cert.pem or cert.crt
                    # But for now, take the first one that seems like a cert
                    with z.open(name) as f:
                        data = f.read()
                        # Basic check if it's PEM
                        if b"-----BEGIN CERTIFICATE-----" in data:
                            expiry = get_cert_expiry_date(data)
                            if expiry:
                                return expiry
    except Exception as e:
        logger.error(f"Error reading ZIP {zip_path}: {e}")

    return None
