"""Container orchestration service — wraps modelctl_orch for the API."""

from __future__ import annotations

import os
import logging
from pathlib import Path

import docker

from modelctl_core import registry
from modelctl_orch.container_manager import ContainerManager
from modelctl_orch.models import (
    ContainerInfo,
    ContainerState,
    ResourceProfile,
)
from modelctl_orch.port_allocator import PortAllocator

log = logging.getLogger(__name__)


class ContainerServiceError(Exception):
    """Base exception for container service operations."""


class ContainerNotFoundError(ContainerServiceError):
    """Requested container does not exist."""


class ModelNotInstalledError(ContainerServiceError):
    """Model must be installed before starting a container."""


class ContainerService:
    """Business logic for container lifecycle exposed through the API."""

    def __init__(
        self,
        image: str | None = None,
        network: str | None = None,
    ) -> None:
        self._image = image or os.environ.get(
            "LLAMACPP_IMAGE", "ghcr.io/ggml-org/llama.cpp:server"
        )
        self._network = network or os.environ.get(
            "MODELCTL_NETWORK", "modelctl-net"
        )
        self._manager = ContainerManager()
        self._allocator = PortAllocator()

    # ── list ─────────────────────────────────────────────────────────

    def list_containers(self) -> list[dict]:
        """Return all managed containers."""
        containers = self._manager.list()
        return [self._info_to_dict(c) for c in containers]

    # ── start ────────────────────────────────────────────────────────

    def start_container(
        self,
        capability: str,
        model_id: str,
        memory_limit: str | None = None,
        cpu_count: float | None = None,
        gpu_device: str | None = None,
        gpu_count: int | None = None,
    ) -> dict:
        """Start a new inference container for the given model.

        The model must already be installed in the registry.
        """
        # Resolve the model in the registry
        model = registry.find_model(model_id)
        if not model:
            raise ModelNotInstalledError(
                f"Model '{model_id}' is not installed. "
                f"Install it first via POST /api/v1/models/install"
            )

        # Find the GGUF artifact path
        gguf = next(
            (a for a in model.artifacts if a.file_type == "gguf" and a.path),
            None,
        )
        if not gguf:
            raise ModelNotInstalledError(
                f"Model '{model_id}' has no GGUF artifact available"
            )

        model_path = str(registry.STORAGE_DIR / model.storage_path / gguf.path)
        storage_root = str(registry.STORAGE_DIR)

        # Build an optional resource profile override
        profile: ResourceProfile | None = None
        if any(x is not None for x in [memory_limit, cpu_count, gpu_device, gpu_count]):
            profile = ResourceProfile(
                memory_limit=memory_limit or "4g",
                cpu_count=cpu_count or 2.0,
                gpu_device=gpu_device,
                gpu_count=gpu_count or 1,
            )

        # Allocate a port
        port = self._allocator.allocate(capability)

        # Start the container
        info = self._manager.start(
            capability=capability,
            model_id=model_id,
            model_path=model_path,
            storage_root=storage_root,
            port=port,
            profile=profile,
        )
        log.info(
            "Started container %s for model %s (%s) on port %d",
            info.id, model_id, capability, port,
        )
        return self._info_to_dict(info)

    # ── stop ─────────────────────────────────────────────────────────

    def stop_container(self, container_id: str, timeout: int = 10) -> dict:
        """Stop and remove a managed container."""
        info = self._manager.inspect(container_id)
        if info is None:
            raise ContainerNotFoundError(
                f"Container not found: {container_id}"
            )

        self._manager.stop(container_id, timeout=timeout)
        self._allocator.release(info.port)
        log.info("Stopped container %s", container_id)
        return {"status": "stopped", "container_id": container_id}

    # ── inspect ──────────────────────────────────────────────────────

    def inspect_container(self, container_id: str) -> dict:
        """Get detailed info for a single container."""
        info = self._manager.inspect(container_id)
        if info is None:
            raise ContainerNotFoundError(
                f"Container not found: {container_id}"
            )
        return self._info_to_dict(info)

    # ── logs ─────────────────────────────────────────────────────────

    def get_logs(self, container_id: str, tail: int = 50) -> dict:
        """Return recent logs for a container."""
        info = self._manager.inspect(container_id)
        if info is None:
            raise ContainerNotFoundError(
                f"Container not found: {container_id}"
            )
        logs = self._manager.logs(container_id, tail=tail)
        return {"container_id": container_id, "logs": logs}

    # ── restart ──────────────────────────────────────────────────────

    def restart_container(self, container_id: str, timeout: int = 10) -> dict:
        """Restart a managed container."""
        info = self._manager.inspect(container_id)
        if info is None:
            raise ContainerNotFoundError(
                f"Container not found: {container_id}"
            )
        self._manager.restart(container_id, timeout=timeout)
        log.info("Restarted container %s", container_id)
        return self._info_to_dict(self._manager.inspect(container_id))

    # ── helpers ──────────────────────────────────────────────────────

    @staticmethod
    def _info_to_dict(info: ContainerInfo) -> dict:
        """Convert a ContainerInfo dataclass to an API response dict."""
        return {
            "id": info.id,
            "capability": info.capability,
            "model_id": info.model_id,
            "model_name": info.model_name,
            "port": info.port,
            "status": info.status.value if isinstance(
                info.status, ContainerState) else str(info.status),
            "error": info.error,
            "started_at": info.started_at,
            "uptime_seconds": info.uptime_seconds,
            "resource_profile": {
                "memory_limit": info.resource_profile.memory_limit,
                "cpu_count": info.resource_profile.cpu_count,
                "gpu_device": info.resource_profile.gpu_device,
                "gpu_count": info.resource_profile.gpu_count,
            } if info.resource_profile else None,
        }
