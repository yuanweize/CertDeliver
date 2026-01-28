"""
Certbot Hook for CertDeliver.
Packages renewed certificates for distribution.
"""

import logging
import shutil
import sys
import time
import zipfile
from pathlib import Path

from ..config import get_hook_settings, setup_logging

logger = logging.getLogger(__name__)


class CertificatePackager:
    """
    Packages Let's Encrypt certificates for distribution.

    This hook is designed to be run by certbot's post-renewal hook.
    It compresses the certificate files into a timestamped zip archive
    for distribution via CertDeliver server.
    """

    def __init__(
        self,
        letsencrypt_live_dir: Path,
        output_dir: Path,
        cert_name: str,
    ):
        """
        Initialize the certificate packager.

        Args:
            letsencrypt_live_dir: Path to Let's Encrypt live directory
            output_dir: Output directory for packaged certificates
            cert_name: Certificate name to package
        """
        self.letsencrypt_live_dir = Path(letsencrypt_live_dir)
        self.output_dir = Path(output_dir)
        self.cert_name = cert_name

    @property
    def cert_source_dir(self) -> Path:
        """Get the source directory for the certificate."""
        return self.letsencrypt_live_dir / self.cert_name

    def _validate_paths(self) -> bool:
        """
        Validate that required paths exist and are accessible.

        Returns:
            True if validation passes, False otherwise.
        """
        # Check source directory
        if not self.cert_source_dir.exists():
            logger.error(f"Certificate directory not found: {self.cert_source_dir}")
            return False

        if not self.cert_source_dir.is_dir():
            logger.error(f"Certificate path is not a directory: {self.cert_source_dir}")
            return False

        # Check for required certificate files
        required_files = ["fullchain.pem", "privkey.pem"]
        for file_name in required_files:
            file_path = self.cert_source_dir / file_name
            if not file_path.exists():
                logger.error(f"Required certificate file not found: {file_path}")
                return False

        return True

    def _prepare_output_dir(self) -> bool:
        """
        Prepare the output directory.

        Clears existing files and creates fresh directory.

        Returns:
            True if successful, False otherwise.
        """
        try:
            # Remove existing directory if it exists
            if self.output_dir.exists():
                logger.info(f"Cleaning output directory: {self.output_dir}")
                shutil.rmtree(self.output_dir)

            # Create fresh directory
            self.output_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"Output directory ready: {self.output_dir}")
            return True

        except PermissionError:
            logger.error(f"Permission denied accessing: {self.output_dir}")
            return False
        except Exception as e:
            logger.error(f"Failed to prepare output directory: {e}")
            return False

    def _create_zip_archive(self) -> Path | None:
        """
        Create timestamped zip archive of certificate files.

        Returns:
            Path to created zip file, or None on failure.
        """
        timestamp = int(time.time())
        output_filename = f"{self.cert_name}_{timestamp}.zip"
        output_path = self.output_dir / output_filename

        logger.info(f"Creating certificate archive: {output_path}")

        try:
            with zipfile.ZipFile(
                output_path, "w", compression=zipfile.ZIP_DEFLATED
            ) as zip_file:
                # Walk through certificate directory and add files
                for file_path in self.cert_source_dir.iterdir():
                    if file_path.is_file():
                        # Add file to zip, storing only the filename
                        arc_name = file_path.name
                        zip_file.write(file_path, arc_name)
                        logger.info(f"Added to archive: {arc_name}")

            # Verify the archive was created
            if output_path.exists():
                size_kb = output_path.stat().st_size / 1024
                logger.info(
                    f"Archive created successfully: {output_filename} ({size_kb:.1f} KB)"
                )
                return output_path
            else:
                logger.error("Archive file was not created")
                return None

        except Exception as e:
            logger.error(f"Failed to create archive: {e}")
            return None

    def package(self) -> Path | None:
        """
        Package the certificate for distribution.

        Returns:
            Path to the created archive, or None on failure.
        """
        logger.info(f"Packaging certificate: {self.cert_name}")
        logger.info(f"Source: {self.cert_source_dir}")
        logger.info(f"Output: {self.output_dir}")

        # Validate paths
        if not self._validate_paths():
            return None

        # Prepare output directory
        if not self._prepare_output_dir():
            return None

        # Create archive
        archive_path = self._create_zip_archive()

        if archive_path:
            logger.info("Certificate packaging completed successfully")
        else:
            logger.error("Certificate packaging failed")

        return archive_path


def main() -> None:
    """
    Main entry point for certbot hook.
    """
    settings = get_hook_settings()

    # Setup logging
    log_file = settings.output_dir.parent / "log_hook"
    setup_logging(log_file=log_file, component="certdeliver.hook")

    logger.info("=" * 50)
    logger.info("CertDeliver certbot hook starting...")

    packager = CertificatePackager(
        letsencrypt_live_dir=settings.letsencrypt_live_dir,
        output_dir=settings.output_dir,
        cert_name=settings.cert_name,
    )

    result = packager.package()

    if result:
        logger.info(f"Success! Certificate packaged to: {result}")
        sys.exit(0)
    else:
        logger.error("Failed to package certificate")
        sys.exit(1)


if __name__ == "__main__":
    main()
