"""Container lifecycle endpoints — start, stop, inspect, logs."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Path, Query

from modelctl_api.dependencies import get_container_service
from modelctl_api.models.containers import (
    ContainerInfoResponse,
    ContainerListResponse,
    ContainerLogsResponse,
    StartContainerRequest,
    StartContainerResponse,
)
from modelctl_api.services.container_service import ContainerService

router = APIRouter(tags=["Containers"])


@router.get("/containers", response_model=ContainerListResponse)
async def list_containers(
    svc: ContainerService = Depends(get_container_service),
):
    """List all managed inference containers."""
    containers = svc.list_containers()
    return {"containers": containers, "total": len(containers)}


@router.post(
    "/containers",
    response_model=StartContainerResponse,
    status_code=201,
)
async def start_container(
    body: StartContainerRequest,
    svc: ContainerService = Depends(get_container_service),
):
    """Start a new inference container for an installed model.

    The model must already be installed in the registry (via
    ``POST /api/v1/models/install``). The container runs llama.cpp
    server inside Docker, exposing the model on an allocated port.
    """
    info = svc.start_container(
        capability=body.capability,
        model_id=body.model_id,
        memory_limit=body.resource_profile.memory_limit if body.resource_profile else None,
        cpu_count=body.resource_profile.cpu_count if body.resource_profile else None,
        gpu_device=body.resource_profile.gpu_device if body.resource_profile else None,
        gpu_count=body.resource_profile.gpu_count if body.resource_profile else None,
        server_args=body.server_args,
    )
    return {"container": info}


@router.get("/containers/{container_id}", response_model=ContainerInfoResponse)
async def inspect_container(
    container_id: str = Path(..., description="Docker container ID"),
    svc: ContainerService = Depends(get_container_service),
):
    """Get detailed information about a managed container."""
    return svc.inspect_container(container_id)


@router.delete(
    "/containers/{container_id}",
    status_code=200,
)
async def stop_container(
    container_id: str = Path(..., description="Docker container ID"),
    timeout: int = Query(
        10, ge=1, le=120, description="Grace period before force kill"),
    svc: ContainerService = Depends(get_container_service),
):
    """Stop and remove a managed inference container."""
    return svc.stop_container(container_id, timeout=timeout)


@router.post(
    "/containers/{container_id}/restart",
    response_model=ContainerInfoResponse,
)
async def restart_container(
    container_id: str = Path(..., description="Docker container ID"),
    timeout: int = Query(
        10, ge=1, le=120, description="Grace period before force kill"),
    svc: ContainerService = Depends(get_container_service),
):
    """Restart a managed inference container."""
    return svc.restart_container(container_id, timeout=timeout)


@router.get(
    "/containers/{container_id}/logs",
    response_model=ContainerLogsResponse,
)
async def container_logs(
    container_id: str = Path(..., description="Docker container ID"),
    tail: int = Query(
        50, ge=10, le=500, description="Number of log lines to return"),
    svc: ContainerService = Depends(get_container_service),
):
    """Get recent logs from a managed container."""
    return svc.get_logs(container_id, tail=tail)
