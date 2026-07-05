"""Docker SDK wrapper for per-capability inference containers."""

from __future__ import annotations

import asyncio
import logging
import os
import time
from typing import List, Optional

import docker
import httpx
from docker.errors import NotFound
from docker.models.containers import Container

from modelctl_orch.models import (
    Capability,
    ContainerInfo,
    ContainerState,
    DEFAULT_PROFILES,
    ResourceProfile,
)

log = logging.getLogger(__name__)

# Inference image used for all capabilities
# Override via the LLAMACPP_IMAGE env var
CONTAINER_IMAGE = os.environ.get(
    "LLAMACPP_IMAGE", "ghcr.io/ggml-org/llama.cpp:server")

# Docker network for inference containers
NETWORK_NAME = os.environ.get("MODELCTL_NETWORK", "modelctl-net")


class ContainerManager:
    """Controls per-capability inference containers via the Docker SDK."""

    def __init__(self, docker_client: docker.DockerClient | None = None) -> None:
        self._client = docker_client or docker.from_env()
        self._gpu_available = self._check_gpu_available()

    @staticmethod
    def _check_gpu_available() -> bool:
        """Detect whether the Docker host has GPU support (nvidia-container-toolkit)."""
        try:
            client = docker.from_env()
            info = client.info()
            # Check for NVIDIA GPUs in Docker info
            runtimes = info.get("Runtimes", {})
            if "nvidia" in runtimes:
                return True
            # Also check via nvidia-smi as a fallback
            import subprocess
            result = subprocess.run(
                ["nvidia-smi"], capture_output=True, timeout=5
            )
            return result.returncode == 0
        except Exception:
            return False

    # ------------------------------------------------------------------
    # Network management
    # ------------------------------------------------------------------

    def _ensure_network(self) -> str:
        """Return ``NETWORK_NAME``, creating it first if it does not exist."""
        try:
            self._client.networks.get(NETWORK_NAME)
            log.debug("Network '%s' already exists", NETWORK_NAME)
        except NotFound:
            log.info("Creating Docker network '%s' ...", NETWORK_NAME)
            self._client.networks.create(NETWORK_NAME, driver="bridge")
        return NETWORK_NAME

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def start(
        self,
        capability: Capability,
        model_id: str,
        model_path: str,
        storage_root: str = "",
        profile: ResourceProfile | None = None,
    ) -> ContainerInfo:
        """Start a new inference container for *capability*.

        The container is named ``modelctl-{capability}`` (fixed per
        capability) and runs on the internal Docker network
        (``modelctl-net``) only — no ports are exposed to the host.
        Nginx routes requests to it by container name.

        If a container for the same capability already exists, it is
        stopped and removed first.

        Parameters
        ----------
        capability:
            One of ``chat``, ``embedding``, ``reranker``, ``vision``, ``experimental``.
        model_id:
            Identifier used by the registry (for metadata / labels).
        model_path:
            Absolute path to the GGUF model file on the host.
        storage_root:
            Host path to the storage root — mounted inside the container so
            the model can be loaded from its real storage location.
        profile:
            Resource constraints. Falls back to ``DEFAULT_PROFILES[capability]``.

        Returns
        -------
        A ``ContainerInfo`` reflecting the started container.
        """
        profile = profile or DEFAULT_PROFILES.get(
            capability, ResourceProfile()
        )

        container_port = 8080
        container_name = f"modelctl-{capability}"

        labels = {
            "modelctl.managed": "true",
            "modelctl.capability": capability,
            "modelctl.model_id": model_id,
            "modelctl.port": str(container_port),
        }

        # ── resolve container paths ─────────────────────────────────
        # Mount the storage root to /storage, then compute the model
        # path relative to it so llama-server can find the GGUF file.
        storage_root = storage_root or os.path.dirname(model_path)
        model_mount_path = os.path.normpath(
            f"/storage/{os.path.relpath(model_path, storage_root)}"
        )

        # ── Stop any existing container for this capability ─────────
        self._stop_by_name(container_name)

        env = {
            "MODEL_PATH": model_mount_path,
            "CAPABILITY": capability,
            "SERVER_PORT": str(container_port),
        }

        device_requests: list = []
        if (
            profile.gpu_count > 0
            and profile.gpu_device is not None
            and self._gpu_available
        ):
            device_requests.append(
                docker.types.DeviceRequest(
                    device_ids=[profile.gpu_device],
                    capabilities=[["gpu"]],
                    count=profile.gpu_count,
                )
            )
        elif profile.gpu_count > 0 and not self._gpu_available:
            log.warning(
                "GPU requested but no NVIDIA runtime detected — falling back to CPU"
            )

        # ── build capability-specific flags ────────────────────────
        extra_flags: list[str] = []
        if capability == "embedding":
            extra_flags = ["--embeddings", "--pooling", "last"]

        # ── run llama-server CLI directly ───────────────────────────
        # No host port binding — the container is reachable on the
        # internal Docker network by its fixed name (modelctl-chat, etc.).
        container: Container = self._client.containers.run(
            image=CONTAINER_IMAGE,
            name=container_name,
            detach=True,
            volumes={
                storage_root: {
                    "bind": "/storage",
                    "mode": "ro",
                },
            },
            environment=env,
            entrypoint=[],
            command=[
                "/app/llama-server",
                "-m", model_mount_path,
                "--host", "0.0.0.0",
                "--port", str(container_port),
                *extra_flags,
            ],
            mem_limit=profile.memory_limit,
            nano_cpus=int(profile.cpu_count * 1e9),
            device_requests=device_requests,
            labels=labels,
            network=self._ensure_network(),
        )

        return ContainerInfo(
            id=container.id,
            capability=capability,
            model_id=model_id,
            model_name=model_id.split(
                "/")[-1] if "/" in model_id else model_id,
            port=container_port,
            status=ContainerState.STARTING,
            resource_profile=profile,
        )

    def _stop_by_name(self, container_name: str) -> None:
        """Stop and remove a container by name if it exists."""
        try:
            existing = self._client.containers.get(container_name)
            log.info(
                "Stopping existing container '%s' (%s) — replacing with new model",
                container_name, existing.short_id,
            )
            existing.stop(timeout=10)
            existing.remove()
        except NotFound:
            pass  # no existing container — nothing to do

    def stop(self, container_id: str, timeout: int = 10) -> None:
        """Gracefully stop and remove a container."""
        try:
            c = self._client.containers.get(container_id)
            c.stop(timeout=timeout)
            c.remove()
        except NotFound:
            log.warning(
                "container %s not found (already removed)", container_id)

    def list(self) -> List[ContainerInfo]:
        """Return info for all managed containers."""
        containers = self._client.containers.list(
            all=True,
            filters={"label": "modelctl.managed"},
        )
        return [self._build_info(c) for c in containers]

    def inspect(self, container_id: str) -> ContainerInfo | None:
        """Return detailed info for a single managed container."""
        try:
            c = self._client.containers.get(container_id)
            return self._build_info(c)
        except NotFound:
            return None

    def logs(self, container_id: str, tail: int = 50) -> str:
        """Return the last *tail* lines of container logs."""
        try:
            c = self._client.containers.get(container_id)
            raw = c.logs(tail=tail, timestamps=False)
            return raw.decode("utf-8") if isinstance(raw, bytes) else raw
        except NotFound:
            return ""

    def restart(self, container_id: str, timeout: int = 10) -> None:
        """Restart a managed container."""
        try:
            c = self._client.containers.get(container_id)
            c.restart(timeout=timeout)
        except NotFound:
            log.warning(
                "container %s not found — cannot restart", container_id)

    # ------------------------------------------------------------------
    # Health check
    # ------------------------------------------------------------------

    @staticmethod
    async def wait_for_healthy(host: str, port: int, timeout: int = 30) -> bool:
        """Poll ``/health`` until status OK or *timeout* expires."""
        start = time.monotonic()
        url = f"http://{host}:{port}/health"
        async with httpx.AsyncClient() as client:
            while time.monotonic() - start < timeout:
                try:
                    resp = await client.get(url, timeout=2)
                    if resp.status_code == 200:
                        return True
                except (httpx.ConnectError, httpx.TimeoutException):
                    pass
                await asyncio.sleep(1)
        return False

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    @staticmethod
    def _build_info(container: Container) -> ContainerInfo:
        """Convert a Docker ``Container`` object into a ``ContainerInfo``."""
        labels = container.labels or {}
        docker_status = container.status

        # Map Docker status strings to our domain states
        status_map = {
            "running": ContainerState.RUNNING,
            "created": ContainerState.STARTING,
            "exited": ContainerState.STOPPED,
            "paused": ContainerState.STOPPED,
            "restarting": ContainerState.STARTING,
            "removing": ContainerState.STOPPING,
            "dead": ContainerState.FAILED,
        }
        state = status_map.get(docker_status, ContainerState.FAILED)
        port_str = labels.get("modelctl.port", "0")
        model_id = labels.get("modelctl.model_id", "")
        model_name = model_id.split("/")[-1] if "/" in model_id else model_id
        started_at = container.attrs.get("State", {}).get("StartedAt", "")

        return ContainerInfo(
            id=container.id,
            capability=labels.get("modelctl.capability", "chat"),
            model_id=model_id,
            model_name=model_name,
            port=int(port_str) if port_str.isdigit() else 0,
            status=state,
            resource_profile=DEFAULT_PROFILES.get(
                labels.get("modelctl.capability", "chat")),
            started_at=started_at,
        )
