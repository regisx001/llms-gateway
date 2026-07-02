"""Shared fixtures for modelctl-orch tests."""

from __future__ import annotations

from unittest.mock import MagicMock, create_autospec

import docker
import pytest
from docker.errors import NotFound


@pytest.fixture
def mock_docker_client() -> MagicMock:
    """Return a fully mocked ``docker.DockerClient``.

    The ``networks`` sub-attribute is pre-wired so that
    ``networks.get()`` raises ``NotFound`` — triggering automatic
    network creation in ``_ensure_network()`` — unless overridden.
    """
    client = create_autospec(docker.DockerClient, instance=True)

    # Wire networks.get to raise NotFound by default (auto-create path)
    client.networks.get.side_effect = NotFound("network not found")

    # Mock the created network object returned by networks.create
    network_mock = MagicMock()
    network_mock.name = "modelctl-net"
    client.networks.create.return_value = network_mock

    return client


@pytest.fixture
def mock_container() -> MagicMock:
    """Return a mocked ``docker.models.containers.Container``."""
    c = MagicMock()
    c.id = "abc123def456"
    c.labels = {
        "modelctl.managed": "true",
        "modelctl.capability": "chat",
        "modelctl.model_id": "org/my-model",
        "modelctl.port": "30001",
    }
    c.status = "running"
    c.attrs = {"State": {"StartedAt": "2026-07-02T12:00:00Z"}}
    c.name = "modelctl-chat-org-my-model"
    return c


@pytest.fixture
def mock_container_stopped() -> MagicMock:
    """Return a mocked container in exited state."""
    c = MagicMock()
    c.id = "xyz789"
    c.labels = {
        "modelctl.managed": "true",
        "modelctl.capability": "embedding",
        "modelctl.model_id": "other/model",
        "modelctl.port": "30002",
    }
    c.status = "exited"
    c.attrs = {"State": {"StartedAt": "2026-07-01T10:00:00Z"}}
    c.name = "modelctl-embedding-other-model"
    return c
