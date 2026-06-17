"""Health check endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from modelctl_api.dependencies import get_system_service
from modelctl_api.models.common import HealthResponse
from modelctl_api.services.system_service import SystemService

router = APIRouter(tags=["Health"])


@router.get("/health", response_model=HealthResponse)
async def health(
    svc: SystemService = Depends(get_system_service),
):
    """Liveness probe — returns ok if the API is running."""
    return svc.health()


@router.get("/ready", response_model=HealthResponse)
async def ready(
    svc: SystemService = Depends(get_system_service),
):
    """Readiness probe — verifies the registry is writable."""
    return svc.ready()
