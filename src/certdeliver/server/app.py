"""
CertDeliver Server Application.
FastAPI-based certificate delivery server.
"""

import logging
import sys
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from prometheus_client import Gauge

from ..config import get_server_settings, setup_logging
from .routes import init_routes, router

logger = logging.getLogger(__name__)

# Prometheus metrics
# Labels: cert_name
expiry_gauge = Gauge(
    "certdeliver_certificate_expiry_days",
    "Number of days until the certificate expires",
    ["cert_name"],
)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Application lifespan handler for startup and shutdown events.
    """
    settings = get_server_settings()

    # Initialize routes with settings
    domains = settings.domain_list
    if isinstance(domains, str):
        domains = [d.strip() for d in domains.split(",") if d.strip()]

    init_routes(token=settings.token, domains=domains, tokens=settings.tokens)

    logger.info("CertDeliver server starting...")

    # Start background certificate monitoring
    import asyncio
    from datetime import datetime, timezone

    from ..utils.cert_utils import get_zip_cert_expiry

    async def monitor_certs() -> None:
        while True:
            try:
                if settings.targets_dir.exists():
                    for zip_file in settings.targets_dir.glob("*.zip"):
                        expiry: datetime | None = get_zip_cert_expiry(zip_file)
                        if expiry:
                            now: datetime = datetime.now(timezone.utc)
                            days_remaining: float = (expiry - now).total_seconds() / (
                                24 * 3600
                            )
                            cert_name: str = zip_file.stem.split("_")[0]
                            expiry_gauge.labels(cert_name=cert_name).set(days_remaining)
                            logger.debug(
                                f"Monitored cert {cert_name}: {days_remaining:.2f} days remaining"
                            )
            except Exception as e:
                logger.error(f"Error in cert monitoring task: {e}")

            # Run every hour
            await asyncio.sleep(3600)

    monitor_task = asyncio.create_task(monitor_certs())

    yield

    monitor_task.cancel()
    logger.info("CertDeliver server shutting down...")


def create_app() -> FastAPI:
    """
    Create and configure the FastAPI application.

    Returns:
        Configured FastAPI application instance.
    """
    settings = get_server_settings()

    # Setup logging
    setup_logging(log_file=settings.log_file, component="certdeliver.server")

    # Validate configuration
    # Validate configuration
    if not settings.token and not settings.tokens:
        logger.error(
            "No authentication tokens configured (CERTDELIVER_TOKEN or CERTDELIVER_TOKENS)!"
        )
        sys.exit(1)

    if not settings.domain_list:
        logger.warning("No domains configured for whitelist. All IPs will be accepted.")

    # Create app with disabled docs in production
    app = FastAPI(
        title="CertDeliver",
        description="SSL Certificate Delivery Service",
        version="2.0.0",
        docs_url=None,  # Disable in production
        redoc_url=None,
        openapi_url=None,
        lifespan=lifespan,
    )

    # Initialize Prometheus metrics
    try:
        from prometheus_fastapi_instrumentator import Instrumentator

        Instrumentator().instrument(app).expose(app)
        logger.info("Prometheus metrics enabled at /metrics")
    except ImportError:
        logger.warning(
            "prometheus-fastapi-instrumentator not installed, metrics disabled"
        )

    # Add root endpoint
    @app.get("/")
    async def root(request: Request) -> JSONResponse:
        """Root endpoint with welcome message."""
        client_ip = request.client.host if request.client else "unknown"
        return JSONResponse(
            {
                "service": "CertDeliver",
                "version": "2.0.0",
                "message": "Welcome to CertDeliver Certificate Delivery Service",
                "client_ip": client_ip,
            }
        )

    # Add health check endpoint
    @app.get("/health")
    async def health_check() -> JSONResponse:
        """Health check endpoint for monitoring."""
        status = "healthy"
        details: dict[str, object] = {"service": "certdeliver-server"}

        # Check targets directory
        if settings.targets_dir.exists():
            try:
                cert_count = len(list(settings.targets_dir.glob("*.zip")))
                details["targets_dir"] = str(settings.targets_dir)
                details["available_certs"] = cert_count
            except Exception as e:
                details["storage_error"] = str(e)
                status = "degraded"
        else:
            status = "degraded"
            details["error"] = "Targets directory not found"

        return JSONResponse(
            {"status": status, **details},
            status_code=200 if status == "healthy" else 503,
        )

    # Include API routes
    app.include_router(router)

    return app


def main() -> None:
    """
    Main entry point for running the server.
    """
    settings = get_server_settings()

    app = create_app()

    uvicorn.run(
        app,
        host=settings.host,
        port=settings.port,
        proxy_headers=True,
        forwarded_allow_ips="*",
        access_log=True,
    )


# For backwards compatibility and direct uvicorn usage
try:
    app = create_app()
except SystemExit:
    # Allow import to succeed even if config is bad (e.g. during tests)
    app = FastAPI()


if __name__ == "__main__":
    main()
