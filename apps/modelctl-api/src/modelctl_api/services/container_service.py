"""Container orchestration service — wraps modelctl_orch for the API."""

from __future__ import annotations

import os
import logging
from pathlib import Path

import docker

import docker

from modelctl_core import registry
from modelctl_orch.container_manager import ContainerManager
from modelctl_orch.models import (
    ContainerInfo,
    ContainerState,
    ResourceProfile,
)

log = logging.getLogger(__name__)


class ContainerServiceError(Exception):
    """Base exception for container service operations."""


class ContainerNotFoundError(ContainerServiceError):
    """Requested container does not exist."""


class DockerUnavailableError(ContainerServiceError):
    """Docker is not available — cannot manage containers."""


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
        self._manager: ContainerManager | None = None
        self._init_docker()

    def _init_docker(self) -> None:
        """Try connecting to Docker — non-fatal if unavailable."""
        try:
            self._manager = ContainerManager()
        except docker.errors.DockerException as e:
            log.warning(
                "Docker not available — container management disabled: %s", e)

    def _require_docker(self) -> ContainerManager:
        """Raise ``DockerUnavailableError`` if Docker is not connected."""
        if self._manager is None:
            raise DockerUnavailableError(
                "Docker is not available in this environment. "
                "Container management requires the Docker socket to be mounted."
            )
        return self._manager

    # ── list ─────────────────────────────────────────────────────────

    def list_containers(self) -> list[dict]:
        """Return all managed containers."""
        mgr = self._require_docker()
        containers = mgr.list()
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

        # Start the container (no host port — internal network only)
        mgr = self._require_docker()
        info = mgr.start(
            capability=capability,
            model_id=model_id,
            model_path=model_path,
            storage_root=storage_root,
            profile=profile,
        )
        log.info(
            "Started container %s for model %s (%s)",
            info.id, model_id, capability,
        )
        return self._info_to_dict(info)

    # ── stop ─────────────────────────────────────────────────────────

    def stop_container(self, container_id: str, timeout: int = 10) -> dict:
        """Stop and remove a managed container."""
        mgr = self._require_docker()
        info = mgr.inspect(container_id)
        if info is None:
            raise ContainerNotFoundError(
                f"Container not found: {container_id}"
            )

        mgr.stop(container_id, timeout=timeout)
        log.info("Stopped container %s", container_id)
        return {"status": "stopped", "container_id": container_id}

    # ── inspect ──────────────────────────────────────────────────────

    def inspect_container(self, container_id: str) -> dict:
        """Get detailed info for a single container."""
        mgr = self._require_docker()
        info = mgr.inspect(container_id)
        if info is None:
            raise ContainerNotFoundError(
                f"Container not found: {container_id}"
            )
        return self._info_to_dict(info)

    # ── logs ─────────────────────────────────────────────────────────

    def get_logs(self, container_id: str, tail: int = 50) -> dict:
        """Return recent logs for a container."""
        mgr = self._require_docker()
        info = mgr.inspect(container_id)
        if info is None:
            raise ContainerNotFoundError(
                f"Container not found: {container_id}"
            )
        logs = mgr.logs(container_id, tail=tail)
        return {"container_id": container_id, "logs": logs}

    # ── restart ──────────────────────────────────────────────────────

    def restart_container(self, container_id: str, timeout: int = 10) -> dict:
        """Restart a managed container."""
        mgr = self._require_docker()
        info = mgr.inspect(container_id)
        if info is None:
            raise ContainerNotFoundError(
                f"Container not found: {container_id}"
            )
        mgr.restart(container_id, timeout=timeout)
        log.info("Restarted container %s", container_id)
        return self._info_to_dict(mgr.inspect(container_id))

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
