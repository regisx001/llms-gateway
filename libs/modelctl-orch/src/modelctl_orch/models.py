"""Pydantic schemas and constants for container orchestration."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Literal


class ContainerState(str, Enum):
    """Lifecycle states for a managed inference container."""

    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    FAILED = "failed"


Capability = Literal["chat", "embedding", "reranker", "vision", "experimental"]


@dataclass
class ResourceProfile:
    """Hardware constraints for a single container."""

    memory_limit: str = "4g"
    cpu_count: float = 2.0
    gpu_device: str | None = "0"
    gpu_count: int = 1


# Default port per capability — matches IMPL_SPEC §2.3
CAPABILITY_PORTS: dict[str, int] = {
    "chat": 30001,
    "embedding": 30002,
    "reranker": 30003,
    "vision": 30004,
    "experimental": 30005,
}

# Env variable names for port overrides
CAPABILITY_PORT_ENV_VARS: dict[str, str] = {
    "chat": "MODELCTL_CHAT_PORT",
    "embedding": "MODELCTL_EMBEDDING_PORT",
    "reranker": "MODELCTL_RERANKER_PORT",
    "vision": "MODELCTL_VISION_PORT",
    "experimental": "MODELCTL_EXPERIMENTAL_PORT",
}

# Default resource profiles — matches IMPL_SPEC §3.3
DEFAULT_PROFILES: dict[str, ResourceProfile] = {
    "chat": ResourceProfile(memory_limit="8g", cpu_count=4.0, gpu_device="0", gpu_count=1),
    "embedding": ResourceProfile(memory_limit="2g", cpu_count=2.0, gpu_device="0", gpu_count=1),
    "reranker": ResourceProfile(memory_limit="4g", cpu_count=2.0, gpu_device="0", gpu_count=1),
    "vision": ResourceProfile(memory_limit="8g", cpu_count=4.0, gpu_device="0", gpu_count=1),
    "experimental": ResourceProfile(memory_limit="4g", cpu_count=2.0, gpu_device="0", gpu_count=1),
}


@dataclass
class ContainerInfo:
    """Full state record for a single managed container."""

    id: str = ""
    capability: Capability = "chat"
    model_id: str = ""
    model_name: str = ""
    port: int = 0
    status: ContainerState = ContainerState.STOPPED
    error: str | None = None
    started_at: str | None = None
    uptime_seconds: int | None = None
    resource_profile: ResourceProfile | None = None


@dataclass
class StartContainerRequest:
    """Payload for requesting a new container."""

    capability: Capability = "chat"
    model_id: str = ""
    resource_profile: ResourceProfile | None = None
