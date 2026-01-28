"""
CertDeliver Client - Certificate Downloader.
Downloads and installs SSL certificates from CertDeliver server.
"""

import logging
import shutil
import subprocess
import sys
import time
import zipfile
from pathlib import Path

import httpx

from ..config import get_client_settings, setup_logging

logger = logging.getLogger(__name__)


class CertificateDownloader:
    """
    Downloads and manages SSL certificates from CertDeliver server.

    This class handles:
    - Checking for certificate updates
    - Downloading new certificates
    - Installing certificates to the target location
    - Running post-update commands
    """

    def __init__(
        self,
        server_url: str,
        token: str,
        cert_name: str,
        cert_dest_path: Path,
        local_cache_dir: Path,
        post_update_command: str | None = None,
        timeout: int = 30,
        verify_ssl: bool = True,
    ):
        """
        Initialize the certificate downloader.

        Args:
            server_url: CertDeliver server URL (e.g., https://cert.example.com/api/v1/)
            token: API authentication token
            cert_name: Certificate name (matches certbot --cert-name)
            cert_dest_path: Destination path for extracted certificates
            local_cache_dir: Local cache directory for downloaded certs
            post_update_command: Optional command to run after update
            timeout: Request timeout in seconds
            verify_ssl: Whether to verify SSL certificates
        """
        self.server_url = server_url.rstrip("/")
        self.token = token
        self.cert_name = cert_name
        self.cert_dest_path = Path(cert_dest_path)
        self.local_cache_dir = Path(local_cache_dir)
        self.post_update_command = post_update_command
        self.timeout = timeout
        self.verify_ssl = verify_ssl

        # HTTP client
        self._client: httpx.Client | None = None

    @property
    def client(self) -> httpx.Client:
        """Get or create HTTP client."""
        if self._client is None:
            self._client = httpx.Client(
                timeout=self.timeout,
                verify=self.verify_ssl,
            )
        return self._client

    def close(self) -> None:
        """Close HTTP client."""
        if self._client:
            self._client.close()
            self._client = None

    def __enter__(self) -> "CertificateDownloader":
        return self

    def __exit__(self, exc_type: object, exc_val: object, exc_tb: object) -> None:
        self.close()

    def _ensure_directories(self) -> None:
        """Ensure required directories exist."""
        self.local_cache_dir.mkdir(parents=True, exist_ok=True)

    def _get_local_cert_file(self) -> Path | None:
        """
        Find the local cached certificate file.

        Returns:
            Path to the cached certificate file, or None if not found.
        """
        if not self.local_cache_dir.exists():
            return None

        cert_files = list(self.local_cache_dir.glob(f"{self.cert_name}_*.zip"))

        if not cert_files:
            return None

        # Return the newest one if multiple exist
        return max(cert_files, key=lambda f: f.stat().st_mtime)

    def _parse_filename(self, filename: str) -> tuple[str, int]:
        """Parse certificate filename to extract name and timestamp."""
        base_name = filename.replace(".zip", "")
        parts = base_name.rsplit("_", 1)
        return parts[0], int(parts[1])

    def _download_certificate(
        self, remote_filename: str, download_mode: bool = False
    ) -> bytes | None:
        """
        Download certificate from server.

        Args:
            remote_filename: Filename to request from server
            download_mode: Whether to force download mode

        Returns:
            Certificate file content, or None if not available.
        """
        url = f"{self.server_url}/{remote_filename}"
        params = {
            "token": self.token,
            "download": str(download_mode).lower(),
        }

        retries = 3
        backoff_factor = 2

        for attempt in range(retries):
            try:
                logger.info(
                    f"Requesting certificate: {url} (Attempt {attempt + 1}/{retries})"
                )
                response = self.client.get(url, params=params)

                if response.status_code == 200:
                    # Check if response is a file or JSON
                    content_type = response.headers.get("content-type", "")

                    if (
                        "application/zip" in content_type
                        or "application/octet-stream" in content_type
                        or "content-disposition" in response.headers
                    ):
                        logger.info("Certificate download successful")
                        return response.content
                    else:
                        # JSON response (no update needed or error)
                        try:
                            data = response.json()
                            if data.get("status") == "ok":
                                logger.info("Certificate is up to date")
                            else:
                                logger.info(f"Server response: {data}")
                        except Exception:
                            logger.warning(
                                f"Unexpected response: {response.text[:200]}"
                            )
                        return None
                else:
                    logger.error(
                        f"Server returned error: {response.status_code} - {response.text[:200]}"
                    )
                    # Don't retry on client errors (4xx), only server errors (5xx)
                    if 400 <= response.status_code < 500:
                        return None

            except httpx.RequestError as e:
                logger.warning(f"Request failed: {e}")

            # Exponential backoff if not the last attempt
            if attempt < retries - 1:
                sleep_time = backoff_factor**attempt
                logger.info(f"Retrying in {sleep_time} seconds...")
                time.sleep(sleep_time)

        logger.error(f"Failed to download certificate after {retries} attempts")
        return None

    def _extract_filename_from_response(self, response: httpx.Response) -> str | None:
        """Extract filename from Content-Disposition header."""
        cd = response.headers.get("content-disposition", "")
        if "filename=" in cd:
            # Parse filename from header
            for part in cd.split(";"):
                if "filename=" in part:
                    return str(part.split("=")[1].strip().strip('"'))
        return None

    def _install_certificate(self, cert_zip_path: Path) -> bool:
        """
        Install certificate from zip file.

        Args:
            cert_zip_path: Path to the certificate zip file.

        Returns:
            True if successful, False otherwise.
        """
        timestamp = int(time.time())
        tmp_dir = Path(f"/tmp/certdeliver_{timestamp}")

        try:
            # Create temp directory
            tmp_dir.mkdir(parents=True, exist_ok=True)

            # Extract certificate
            logger.info(f"Extracting certificate to {tmp_dir}")
            with zipfile.ZipFile(cert_zip_path, "r") as zip_ref:
                zip_ref.extractall(tmp_dir)

            # Backup existing certificates
            if self.cert_dest_path.exists():
                backup_path = self.cert_dest_path.with_suffix(".bak")
                if backup_path.exists():
                    shutil.rmtree(backup_path)
                logger.info(f"Backing up existing certificates to {backup_path}")
                shutil.move(str(self.cert_dest_path), str(backup_path))

            # Create destination directory
            self.cert_dest_path.mkdir(parents=True, exist_ok=True)

            # Move certificate files
            cert_files = ["fullchain.pem", "privkey.pem", "chain.pem", "cert.pem"]
            installed_files = []

            for cert_file in cert_files:
                src = tmp_dir / cert_file
                if src.exists():
                    dst = self.cert_dest_path / cert_file
                    shutil.copy2(str(src), str(dst))
                    installed_files.append(cert_file)
                    logger.info(f"Installed: {cert_file}")

            if not installed_files:
                logger.error("No certificate files found in archive")
                return False

            logger.info(f"Certificate installation complete: {installed_files}")
            return True

        except Exception as e:
            logger.error(f"Failed to install certificate: {e}")
            return False

        finally:
            # Cleanup temp directory
            if tmp_dir.exists():
                shutil.rmtree(tmp_dir, ignore_errors=True)

    def _run_post_update_command(self) -> bool:
        """
        Run post-update command if configured.

        Returns:
            True if successful or no command configured, False on error.
        """
        if not self.post_update_command:
            return True

        logger.info(f"Running post-update command: {self.post_update_command}")

        try:
            result = subprocess.run(
                self.post_update_command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=60,
            )

            if result.returncode == 0:
                logger.info("Post-update command completed successfully")
                if result.stdout:
                    logger.debug(f"Command output: {result.stdout}")
                return True
            else:
                logger.error(
                    f"Post-update command failed with code {result.returncode}"
                )
                if result.stderr:
                    logger.error(f"Error output: {result.stderr}")
                return False

        except subprocess.TimeoutExpired:
            logger.error("Post-update command timed out")
            return False
        except Exception as e:
            logger.error(f"Failed to run post-update command: {e}")
            return False

    def update(self) -> bool:
        """
        Check for and apply certificate updates.

        Returns:
            True if update was applied successfully, False otherwise.
        """
        self._ensure_directories()

        local_cert = self._get_local_cert_file()

        if local_cert is None:
            # First time download
            logger.info("No local certificate found, downloading...")
            timestamp = int(time.time())
            remote_filename = f"{self.cert_name}_{timestamp}"

            content = self._download_certificate(remote_filename, download_mode=True)
        else:
            # Check for updates
            logger.info(f"Checking for updates (local: {local_cert.name})")
            remote_filename = local_cert.name.replace(".zip", "")

            content = self._download_certificate(remote_filename, download_mode=False)

        if content is None:
            logger.info("No update available or download failed")
            return False

        # Determine new filename from response or generate one
        # For simplicity, we'll parse it from content-disposition or use timestamp
        timestamp = int(time.time())
        new_filename = f"{self.cert_name}_{timestamp}.zip"
        new_cert_path = self.local_cache_dir / new_filename

        # Save downloaded certificate
        logger.info(f"Saving certificate to {new_cert_path}")
        new_cert_path.write_bytes(content)

        # Remove old cached cert if exists
        if local_cert and local_cert.exists() and local_cert != new_cert_path:
            local_cert.unlink()

        # Install certificate
        if not self._install_certificate(new_cert_path):
            logger.error("Certificate installation failed")
            return False

        # Run post-update command
        if not self._run_post_update_command():
            logger.warning("Post-update command failed, but certificate was installed")

        return True


def main() -> None:
    """
    Main entry point for the certificate downloader.
    """
    settings = get_client_settings()

    # Setup logging
    setup_logging(component="certdeliver.client")

    # Validate configuration
    if not settings.token:
        logger.error("CERTDELIVER_CLIENT_TOKEN environment variable is not set!")
        sys.exit(1)

    if not settings.server_url:
        logger.error("CERTDELIVER_CLIENT_SERVER_URL environment variable is not set!")
        sys.exit(1)

    logger.info("CertDeliver Client starting...")
    logger.info(f"Server: {settings.server_url}")
    logger.info(f"Certificate name: {settings.cert_name}")
    logger.info(f"Destination: {settings.cert_dest_path}")

    with CertificateDownloader(
        server_url=settings.server_url,
        token=settings.token,
        cert_name=settings.cert_name,
        cert_dest_path=settings.cert_dest_path,
        local_cache_dir=settings.local_cache_dir,
        post_update_command=settings.post_update_command,
        timeout=settings.timeout,
        verify_ssl=settings.verify_ssl,
    ) as downloader:
        success = downloader.update()

        if success:
            logger.info("Certificate update completed successfully")
        else:
            logger.info("No update applied")

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
