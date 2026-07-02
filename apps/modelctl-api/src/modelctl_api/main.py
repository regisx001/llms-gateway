"""FastAPI application factory."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from modelctl_api import __version__
from modelctl_api.config import settings
from modelctl_api.services.container_service import ContainerService
from modelctl_api.services.model_service import ModelService
from modelctl_api.services.search_service import SearchService
from modelctl_api.services.system_service import SystemService


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Startup and shutdown lifecycle."""
    # ── startup ──────────────────────────────────────────────────────
    log_level = getattr(logging, settings.log_level.upper(), logging.INFO)
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
    )
    logger = logging.getLogger("modelctl-api")
    logger.info("Starting modelctl-api v%s", __version__)

    app.state.model_service = ModelService()
    app.state.search_service = SearchService()
    app.state.system_service = SystemService(version=__version__)
    app.state.container_service = ContainerService(
        image=settings.llamacpp_image,
        network=settings.docker_network,
    )

    if settings.registry_dir:
        import os
        os.environ.setdefault("MODELCTL_REGISTRY_DIR", settings.registry_dir)
    if settings.storage_dir:
        import os
        os.environ.setdefault("MODELCTL_STORAGE_DIR", settings.storage_dir)
    if settings.hf_token:
        import os
        os.environ["HF_TOKEN"] = settings.hf_token

    yield

    # ── shutdown ─────────────────────────────────────────────────────
    logger.info("Shutting down modelctl-api")


def create_app() -> FastAPI:
    """Build and return the FastAPI application."""
    app = FastAPI(
        title="Modelctl API",
        description="REST API for managing GGUF models — search, install, activate, and serve via llama.cpp",
        version=__version__,
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # CORS — allow all origins for development
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── exception handlers ──────────────────────────────────────────
    from fastapi import Request
    from fastapi.responses import JSONResponse
    from modelctl_api.services.container_service import (
        ContainerNotFoundError,
        ContainerServiceError,
        ModelNotInstalledError,
    )
    from modelctl_api.services.model_service import (
        ModelctlError,
        ModelNotFoundError,
    )

    @app.exception_handler(ModelNotFoundError)
    async def not_found_handler(request: Request, exc: ModelNotFoundError):
        return JSONResponse(status_code=404, content={"detail": str(exc)})

    @app.exception_handler(ContainerNotFoundError)
    async def container_not_found_handler(
        request: Request, exc: ContainerNotFoundError
    ):
        return JSONResponse(status_code=404, content={"detail": str(exc)})

    @app.exception_handler(ModelNotInstalledError)
    async def model_not_installed_handler(
        request: Request, exc: ModelNotInstalledError
    ):
        return JSONResponse(status_code=409, content={"detail": str(exc)})

    @app.exception_handler(ModelctlError)
    async def modelctl_error_handler(request: Request, exc: ModelctlError):
        return JSONResponse(status_code=400, content={"detail": str(exc)})

    @app.exception_handler(ContainerServiceError)
    async def container_service_error_handler(
        request: Request, exc: ContainerServiceError
    ):
        return JSONResponse(status_code=400, content={"detail": str(exc)})

    # ── register routers (API routes take precedence) ────────────────
    from modelctl_api.routers import containers, health, models, search, system

    app.include_router(health.router)
    app.include_router(containers.router, prefix="/api/v1")
    app.include_router(models.router, prefix="/api/v1")
    app.include_router(search.router, prefix="/api/v1")
    app.include_router(system.router, prefix="/api/v1")

    # ── serve SPA frontend (optional — built by the web/ project) ────
    import os
    from pathlib import Path
    from fastapi.staticfiles import StaticFiles

    # Resolve static directory — check env var, container path, then source tree
    static_dir = None
    env_dir = os.environ.get("MODELCTL_API_STATIC_DIR")
    if env_dir:
        static_dir = Path(env_dir)
    else:
        candidates = [
            # container path
            Path("/opt/modelctl-api/static"),
            Path(__file__).resolve().parent.parent.parent /
            "static",  # source tree
        ]
        for candidate in candidates:
            if candidate.is_dir():
                static_dir = candidate
                break

    if static_dir and static_dir.is_dir():
        app.mount(
            "/",
            StaticFiles(directory=str(static_dir), html=True),
            name="frontend",
        )

    return app


app = create_app()
