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
CONTAINER_IMAGE = os.environ.get("LLAMACPP_IMAGE", "llamaserver:latest")


class ContainerManager:
    """Controls per-capability inference containers via the Docker SDK."""

    def __init__(self, docker_client: docker.DockerClient | None = None) -> None:
        self._client = docker_client or docker.from_env()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def start(
        self,
        capability: Capability,
        model_id: str,
        model_path: str,
        port: int,
        profile: ResourceProfile | None = None,
    ) -> ContainerInfo:
        """Start a new inference container for *capability*.

        Parameters
        ----------
        capability:
            One of ``chat``, ``embedding``, ``reranker``, ``vision``, ``experimental``.
        model_id:
            Identifier used by the registry (for metadata / labels).
        model_path:
            Absolute path to the GGUF model file on the host.
        port:
            Host port to bind the container to.
        profile:
            Resource constraints. Falls back to ``DEFAULT_PROFILES[capability]``.

        Returns
        -------
        A ``ContainerInfo`` reflecting the started container.
        """
        profile = profile or DEFAULT_PROFILES.get(
            capability, ResourceProfile()
        )

        labels = {
            "modelctl.managed": "true",
            "modelctl.capability": capability,
            "modelctl.model_id": model_id,
            "modelctl.port": str(port),
        }

        env = {
            "MODEL_PATH": model_path,
            "CAPABILITY": capability,
            "SERVER_PORT": str(port),
        }

        device_requests: list = []
        if profile.gpu_count > 0 and profile.gpu_device is not None:
            device_requests.append(
                docker.types.DeviceRequest(
                    device_ids=[profile.gpu_device],
                    capabilities=[["gpu"]],
                    count=profile.gpu_count,
                )
            )

        container: Container = self._client.containers.run(
            image=CONTAINER_IMAGE,
            name=f"modelctl-{capability}-{model_id.replace('/', '-')}",
            detach=True,
            ports={f"{port}/tcp": port},
            volumes={
                os.path.dirname(model_path): {
                    "bind": "/models",
                    "mode": "ro",
                },
            },
            environment=env,
            mem_limit=profile.memory_limit,
            nano_cpus=int(profile.cpu_count * 1e9),
            device_requests=device_requests,
            labels=labels,
            network="modelctl-net",
        )

        return ContainerInfo(
            id=container.id,
            capability=capability,
            model_id=model_id,
            model_name=model_id.split(
                "/")[-1] if "/" in model_id else model_id,
            port=port,
            status=ContainerState.STARTING,
            resource_profile=profile,
        )

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
