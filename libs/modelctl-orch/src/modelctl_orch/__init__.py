"""modelctl-orch: Container orchestration layer for modelctl.

Manages per-capability inference container lifecycles via the Docker SDK.
"""

from modelctl_orch.models import (
    Capability,
    ContainerState,
    ResourceProfile,
    ContainerInfo,
    StartContainerRequest,
    DEFAULT_PROFILES,
    CAPABILITY_PORTS,
)
from modelctl_orch.port_allocator import PortAllocator
from modelctl_orch.container_manager import ContainerManager

__all__ = [
    "Capability",
    "ContainerState",
    "ResourceProfile",
    "ContainerInfo",
    "StartContainerRequest",
    "DEFAULT_PROFILES",
    "CAPABILITY_PORTS",
    "PortAllocator",
    "ContainerManager",
]
