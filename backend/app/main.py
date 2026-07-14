"""FastAPI application entry point."""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app import __version__
from app.api.router import api_router
from app.core.logging import configure_logging

configure_logging()
logger = logging.getLogger("evidencegraph.app")


@asynccontextmanager
async def lifespan(application: FastAPI) -> AsyncIterator[None]:
    """Expose readiness only after startup and revoke it before shutdown."""
    application.state.ready = False
    logger.info("application_starting")

    application.state.ready = True
    logger.info("application_ready")
    try:
        yield
    finally:
        application.state.ready = False
        logger.info("application_stopped")


def create_app() -> FastAPI:
    """Create and configure an EvidenceGraph API instance."""
    application = FastAPI(
        title="EvidenceGraph API",
        description="Research intelligence API",
        version=__version__,
        lifespan=lifespan,
    )
    application.state.ready = False
    application.include_router(api_router)
    return application


app = create_app()
