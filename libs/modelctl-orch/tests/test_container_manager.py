"""Tests for modelctl_orch.container_manager — Docker SDK wrapper."""

from __future__ import annotations

from unittest.mock import MagicMock, call

import docker
import pytest
from docker.errors import NotFound

from modelctl_orch.container_manager import CONTAINER_IMAGE, ContainerManager
from modelctl_orch.models import ContainerState, ResourceProfile


# ── start() ─────────────────────────────────────────────────────────────


class TestStart:
    """ContainerManager.start() — Docker run invocation."""

    def test_start_calls_docker_run(self, mock_docker_client, mock_container):
        mock_docker_client.containers.run.return_value = mock_container
        mgr = ContainerManager(docker_client=mock_docker_client)

        info = mgr.start(
            capability="chat",
            model_id="org/my-model",
            model_path="/home/storage/models/my-model.gguf",
            port=30001,
        )

        mock_docker_client.containers.run.assert_called_once()
        _assert_run_kwargs(mock_docker_client.containers.run.call_args)

        assert info.capability == "chat"
        assert info.model_id == "org/my-model"
        assert info.model_name == "my-model"
        assert info.port == 30001
        assert info.status == ContainerState.STARTING
        assert info.id == "abc123def456"

    def test_start_with_profile_override(self, mock_docker_client, mock_container):
        mock_docker_client.containers.run.return_value = mock_container
        mgr = ContainerManager(docker_client=mock_docker_client)
        profile = ResourceProfile(memory_limit="16g", cpu_count=8.0)

        info = mgr.start("chat", "org/m", "/p/m.gguf", 30001, profile=profile)

        kwargs = mock_docker_client.containers.run.call_args.kwargs
        assert kwargs["mem_limit"] == "16g"
        assert kwargs["nano_cpus"] == int(8.0 * 1e9)
        assert info.resource_profile == profile

    def test_start_cpu_only_no_device_request(self, mock_docker_client, mock_container):
        mock_docker_client.containers.run.return_value = mock_container
        mgr = ContainerManager(docker_client=mock_docker_client)
        cpu_profile = ResourceProfile(gpu_device=None, gpu_count=0)

        mgr.start("embedding", "org/m", "/p/m.gguf",
                  30002, profile=cpu_profile)

        kwargs = mock_docker_client.containers.run.call_args.kwargs
        assert kwargs.get("device_requests") == []

    def test_start_creates_expected_name(self, mock_docker_client, mock_container):
        mock_docker_client.containers.run.return_value = mock_container
        mgr = ContainerManager(docker_client=mock_docker_client)

        mgr.start("chat", "org/my-model", "/p/m.gguf", 30001)

        kwargs = mock_docker_client.containers.run.call_args.kwargs
        assert kwargs["name"] == "modelctl-chat-org-my-model"

    def test_start_maps_port_8080(self, mock_docker_client, mock_container):
        """Host port should be mapped to container port 8080."""
        mock_docker_client.containers.run.return_value = mock_container
        mgr = ContainerManager(docker_client=mock_docker_client)

        mgr.start("chat", "org/m", "/p/m.gguf", 30001)

        kwargs = mock_docker_client.containers.run.call_args.kwargs
        assert kwargs["ports"] == {8080: 30001}

    def test_start_sets_command_and_entrypoint(self, mock_docker_client, mock_container):
        """Should clear entrypoint and use llama-server CLI directly."""
        mock_docker_client.containers.run.return_value = mock_container
        mgr = ContainerManager(docker_client=mock_docker_client)

        mgr.start("chat", "org/m", "/p/m.gguf", 30001)

        kwargs = mock_docker_client.containers.run.call_args.kwargs
        assert kwargs["entrypoint"] == []
        assert kwargs["command"] == [
            "/app/llama-server",
            "-m", "/storage/m.gguf",
            "--host", "0.0.0.0",
            "--port", "8080",
        ]


# ── stop() ──────────────────────────────────────────────────────────────


class TestStop:
    """ContainerManager.stop() — Docker stop + remove."""

    def test_stop_calls_stop_and_remove(self, mock_docker_client, mock_container):
        mock_docker_client.containers.get.return_value = mock_container
        mgr = ContainerManager(docker_client=mock_docker_client)

        mgr.stop("abc123def456")

        mock_docker_client.containers.get.assert_called_once_with(
            "abc123def456")
        mock_container.stop.assert_called_once_with(timeout=10)
        mock_container.remove.assert_called_once()

    def test_stop_not_found_logs_warning(self, mock_docker_client, caplog):
        mock_docker_client.containers.get.side_effect = NotFound("missing")
        mgr = ContainerManager(docker_client=mock_docker_client)

        with caplog.at_level("WARNING"):
            mgr.stop("nonexistent")

        assert "not found" in caplog.text


# ── list() ──────────────────────────────────────────────────────────────


class TestList:
    """ContainerManager.list() — list managed containers."""

    def test_list_returns_infos(self, mock_docker_client, mock_container):
        mock_docker_client.containers.list.return_value = [mock_container]
        mgr = ContainerManager(docker_client=mock_docker_client)

        results = mgr.list()

        mock_docker_client.containers.list.assert_called_once_with(
            all=True,
            filters={"label": "modelctl.managed"},
        )
        assert len(results) == 1
        assert results[0].id == "abc123def456"
        assert results[0].status == ContainerState.RUNNING

    def test_list_empty(self, mock_docker_client):
        mock_docker_client.containers.list.return_value = []
        mgr = ContainerManager(docker_client=mock_docker_client)

        assert mgr.list() == []


# ── inspect() ───────────────────────────────────────────────────────────


class TestInspect:
    """ContainerManager.inspect() — get single container."""

    def test_inspect_returns_info(self, mock_docker_client, mock_container):
        mock_docker_client.containers.get.return_value = mock_container
        mgr = ContainerManager(docker_client=mock_docker_client)

        info = mgr.inspect("abc123def456")

        assert info is not None
        assert info.id == "abc123def456"
        assert info.status == ContainerState.RUNNING

    def test_inspect_not_found(self, mock_docker_client):
        mock_docker_client.containers.get.side_effect = NotFound("missing")
        mgr = ContainerManager(docker_client=mock_docker_client)

        assert mgr.inspect("nonexistent") is None


# ── logs() ──────────────────────────────────────────────────────────────


class TestLogs:
    """ContainerManager.logs() — fetch container logs."""

    def test_logs_returns_text(self, mock_docker_client, mock_container):
        mock_container.logs.return_value = b"INFO: started\nINFO: loaded model\n"
        mock_docker_client.containers.get.return_value = mock_container
        mgr = ContainerManager(docker_client=mock_docker_client)

        text = mgr.logs("abc123def456", tail=10)

        mock_container.logs.assert_called_once_with(tail=10, timestamps=False)
        assert text == "INFO: started\nINFO: loaded model\n"

    def test_logs_not_found(self, mock_docker_client):
        mock_docker_client.containers.get.side_effect = NotFound("missing")
        mgr = ContainerManager(docker_client=mock_docker_client)

        assert mgr.logs("nonexistent") == ""


# ── restart() ───────────────────────────────────────────────────────────


class TestRestart:
    """ContainerManager.restart() — restart container."""

    def test_restart_calls_docker(self, mock_docker_client, mock_container):
        mock_docker_client.containers.get.return_value = mock_container
        mgr = ContainerManager(docker_client=mock_docker_client)

        mgr.restart("abc123def456")

        mock_container.restart.assert_called_once_with(timeout=10)

    def test_restart_not_found_logs_warning(self, mock_docker_client, caplog):
        mock_docker_client.containers.get.side_effect = NotFound("missing")
        mgr = ContainerManager(docker_client=mock_docker_client)

        with caplog.at_level("WARNING"):
            mgr.restart("nonexistent")

        assert "not found" in caplog.text


# ── _build_info (internal) ──────────────────────────────────────────────


class TestBuildInfo:
    """ContainerManager._build_info() — Docker container → ContainerInfo."""

    def test_running_container(self, mock_container):
        from modelctl_orch.container_manager import ContainerManager

        info = ContainerManager._build_info(mock_container)

        assert info.id == "abc123def456"
        assert info.capability == "chat"
        assert info.model_id == "org/my-model"
        assert info.model_name == "my-model"
        assert info.port == 30001
        assert info.status == ContainerState.RUNNING
        assert info.started_at == "2026-07-02T12:00:00Z"

    def test_exited_container(self, mock_container_stopped):
        from modelctl_orch.container_manager import ContainerManager

        info = ContainerManager._build_info(mock_container_stopped)

        assert info.status == ContainerState.STOPPED
        assert info.capability == "embedding"
        assert info.port == 30002

    def test_container_without_labels(self):
        from modelctl_orch.container_manager import ContainerManager

        c = MagicMock()
        c.id = "no-labels"
        c.labels = {}
        c.status = "running"
        c.attrs = {"State": {"StartedAt": ""}}
        c.name = "plain-container"

        info = ContainerManager._build_info(c)

        assert info.id == "no-labels"
        assert info.capability == "chat"  # fallback default
        assert info.port == 0
        assert info.status == ContainerState.RUNNING


# ── Helpers ─────────────────────────────────────────────────────────────


def _assert_run_kwargs(call_args) -> None:
    """Assert common kwargs are present in the Docker run call.

    *call_args* is a ``call`` object from ``unittest.mock.call_args``.
    Access named arguments via ``call_args.kwargs``.
    """
    kw = call_args.kwargs if hasattr(call_args, "kwargs") else call_args[1]
    assert kw.get("image") == CONTAINER_IMAGE
    assert kw.get("detach") is True
    assert kw.get("mem_limit") is not None
    assert kw.get("nano_cpus") is not None
    assert kw.get("network") == "modelctl-net"
    # Entrypoint is cleared — we run llama-server CLI directly
    assert kw.get("entrypoint") == []
    # Storage root is mounted to /storage, model is at /storage/<relative>
    volume_bind = list(kw.get("volumes", {}).values())[0]
    assert volume_bind["bind"] == "/storage"
    # Command is a full llama-server CLI invocation
    assert kw.get("command", [])[:1] == ["/app/llama-server"]
    assert "-m" in kw["command"]
    model_idx = kw["command"].index("-m") + 1
    assert kw["command"][model_idx] == "/storage/my-model.gguf"
    assert "--host" in kw["command"]
    assert "--port" in kw["command"]
    # Environment should use container paths
    env = kw.get("environment", {})
    assert env.get("MODEL_PATH") == "/storage/my-model.gguf"
    # Port mapping: host port → container port 8080
    assert kw.get("ports") == {8080: 30001}
    assert "labels" in kw
    assert kw["labels"]["modelctl.managed"] == "true"
    assert kw["labels"]["modelctl.capability"] == "chat"
