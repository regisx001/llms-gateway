"""Shared fixtures for modelctl-api tests."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
from typing import Generator

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def tmp_registry(monkeypatch) -> Generator[Path, None, None]:
    """Replace registry paths with temp dir so tests don't touch real files."""
    tmp = Path(tempfile.mkdtemp())
    reg_dir = tmp / "registry"
    sto_dir = tmp / "storage"
    reg_dir.mkdir(parents=True)
    sto_dir.mkdir(parents=True)

    # Set env vars so any new store instances resolve to the temp dirs
    monkeypatch.setenv("MODELCTL_REGISTRY_DIR", str(reg_dir))
    monkeypatch.setenv("MODELCTL_STORAGE_DIR", str(sto_dir))

    import modelctl_core.registry as reg
    monkeypatch.setattr(reg, "REGISTRY_DIR", reg_dir)
    monkeypatch.setattr(reg, "STORAGE_DIR", sto_dir)
    monkeypatch.setattr(reg, "MODELS_PATH", reg_dir / "models.json")
    monkeypatch.setattr(reg, "DOWNLOADS_PATH", reg_dir / "downloads.json")
    monkeypatch.setattr(reg, "ACTIVE_PATH", reg_dir / "active.json")

    # Replace the _store singleton so all registry functions use the temp dir
    from modelctl_core.json_store import JsonStore
    monkeypatch.setattr(reg, "_store", JsonStore(registry_dir=reg_dir))

    for name, default in [
        ("models.json", {"models": []}),
        ("downloads.json", {"downloads": []}),
        ("active.json", {"active": []}),
    ]:
        (reg_dir / name).write_text(json.dumps(default))

    yield tmp

    import shutil
    shutil.rmtree(tmp, ignore_errors=True)


@pytest.fixture
def client(tmp_registry, monkeypatch) -> Generator[TestClient, None, None]:
    """FastAPI TestClient with isolated registry."""
    from modelctl_api.main import app
    with TestClient(app) as c:
        yield c


@pytest.fixture
def seeded_client(client, tmp_registry) -> Generator[TestClient, None, None]:
    """TestClient pre-seeded with a sample model in the registry."""
    from modelctl_core.models import Model, Artifact
    from modelctl_core import registry as reg

    model = Model(
        id="test-model-001",
        name="Test Model",
        type="chat",
        provider="huggingface",
        repo_id="test/test-model",
        storage_path="chat/test-model-001",
        status="installed",
        installed_at="2026-01-01T00:00:00+00:00",
        artifacts=[
            Artifact(
                name="model.gguf",
                role="primary",
                path="files/model.gguf",
                size=1024,
                file_type="gguf",
                sha256="abc123def456",
            )
        ],
    )
    reg.add_model(model)
    yield client
