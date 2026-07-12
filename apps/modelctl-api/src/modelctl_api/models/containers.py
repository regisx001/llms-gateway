"""Pydantic schemas for container orchestration endpoints."""

from __future__ import annotations

from pydantic import BaseModel


class ResourceProfileResponse(BaseModel):
    memory_limit: str = "4g"
    cpu_count: float = 2.0
    gpu_device: str | None = "0"
    gpu_count: int = 1


class ContainerInfoResponse(BaseModel):
    id: str = ""
    capability: str = "chat"
    model_id: str = ""
    model_name: str = ""
    port: int = 0
    status: str = "stopped"
    error: str | None = None
    started_at: str | None = None
    uptime_seconds: int | None = None
    resource_profile: ResourceProfileResponse | None = None


class ContainerListResponse(BaseModel):
    containers: list[ContainerInfoResponse]
    total: int


class StartContainerRequest(BaseModel):
    capability: str = "chat"
    model_id: str = ""
    resource_profile: ResourceProfileResponse | None = None
    server_args: list[str] = []


class StartContainerResponse(BaseModel):
    container: ContainerInfoResponse


class ContainerLogsResponse(BaseModel):
    container_id: str
    logs: str
