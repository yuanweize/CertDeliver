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

from ..config import get_server_settings, setup_logging
from .routes import init_routes, router

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Application lifespan handler for startup and shutdown events.
    """
    settings = get_server_settings()

    # Initialize routes with settings
    init_routes(token=settings.token, domains=settings.domain_list)

    logger.info("CertDeliver server starting...")
    logger.info(f"Targets directory: {settings.targets_dir}")
    logger.info(f"Whitelisted domains: {len(settings.domain_list)}")

    yield

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
    if not settings.token:
        logger.error("CERTDELIVER_TOKEN environment variable is not set!")
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
        return JSONResponse(
            {
                "status": "healthy",
                "service": "certdeliver-server",
            }
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
