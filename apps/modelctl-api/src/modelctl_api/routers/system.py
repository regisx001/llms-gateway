"""System endpoints — version, storage info, server reload."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from modelctl_api.dependencies import get_system_service
from modelctl_api.models.common import SystemInfoResponse
from modelctl_api.services.system_service import SystemService

router = APIRouter(tags=["System"])


@router.get("/system/info", response_model=SystemInfoResponse)
async def system_info(
    svc: SystemService = Depends(get_system_service),
):
    """System information: version, storage usage, model counts."""
    return svc.info()


@router.post("/system/reload")
async def system_reload(
    svc: SystemService = Depends(get_system_service),
):
    """Trigger llama-server to reload with the current active model."""
    return svc.reload()
