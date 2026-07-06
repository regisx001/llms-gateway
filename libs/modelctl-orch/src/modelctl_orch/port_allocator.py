"""Port allocation for per-capability inference containers.

With nginx as reverse proxy, inference containers run on the internal
Docker network only — no host ports are exposed. Each container uses
the same internal port (8080) and is reachable by its fixed name
(modelctl-chat, modelctl-embedding, etc.).

This module now simply tracks which capabilities are active and
returns the internal port for each.
"""

from __future__ import annotations

from typing import Set

from modelctl_orch.models import (
    CAPABILITY_PORTS,
    Capability,
)

# Internal port used by all inference containers
INTERNAL_CONTAINER_PORT = 8080


class PortAllocator:
    """Tracks active capabilities — no host port scanning needed."""

    def __init__(self) -> None:
        self._reserved: Set[str] = set()

    def allocate(self, capability: Capability) -> int:
        """Mark *capability* as active and return the internal port."""
        self._reserved.add(capability)
        return INTERNAL_CONTAINER_PORT

    def release(self, capability: Capability | int) -> None:
        """Release a capability (accepts capability string or port int)."""
        if isinstance(capability, int):
            # Backward compat: port int — find by internal port (always 8080)
            # No-op since we track by capability string
            return
        self._reserved.discard(capability)

    def is_active(self, capability: Capability) -> bool:
        """Check whether *capability* is currently allocated."""
        return capability in self._reserved
