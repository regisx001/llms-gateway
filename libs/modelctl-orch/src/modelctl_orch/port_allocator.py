"""Port allocation for per-capability inference containers.

Manages the default port ranges defined in CAPABILITY_PORTS and
scans for the next available port within each range if the default
is already taken.
"""

from __future__ import annotations

import os
import socket
from typing import Set

from modelctl_orch.models import (
    CAPABILITY_PORT_ENV_VARS,
    CAPABILITY_PORTS,
    Capability,
)


class PortAllocator:
    """Reserves and tracks ports for inference containers."""

    def __init__(self) -> None:
        self._reserved: Set[int] = set()

    def get_base_port(self, capability: Capability) -> int:
        """Return the configured base port for *capability*.

        Respects environment overrides (e.g. ``MODELCTL_CHAT_PORT``).
        """
        env_var = CAPABILITY_PORT_ENV_VARS.get(capability)
        if env_var and (override := os.environ.get(env_var)):
            return int(override)
        return CAPABILITY_PORTS.get(capability, 30001)

    def allocate(self, capability: Capability) -> int:
        """Return an available port for *capability*.

        Starts at the base port and scans upward within a 100-port range
        until it finds one that is free (not reserved and not in use).
        """
        base = self.get_base_port(capability)
        for offset in range(100):
            port = base + offset
            if port in self._reserved:
                continue
            if not self._port_in_use(port):
                self._reserved.add(port)
                return port
        raise RuntimeError(
            f"no available port found for capability '{capability}' "
            f"(scanned {base}-{base + 99})"
        )

    def release(self, port: int) -> None:
        """Release a previously allocated port."""
        self._reserved.discard(port)

    @staticmethod
    def _port_in_use(port: int) -> bool:
        """Check if *port* is already bound on the host."""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            return s.connect_ex(("127.0.0.1", port)) == 0
