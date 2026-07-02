"""Shared fixtures for modelctl-orch tests."""

from __future__ import annotations

from unittest.mock import MagicMock, create_autospec

import docker
import pytest


@pytest.fixture
def mock_docker_client() -> MagicMock:
    """Return a fully mocked ``docker.DockerClient``.

    All sub-attributes (``containers``, ``containers.run``, etc.) are
    auto-created mocks so tests can assert calls without setting up
    each one individually.
    """
    return create_autospec(docker.DockerClient, instance=True)


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
