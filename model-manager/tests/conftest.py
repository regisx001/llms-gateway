"""Shared fixtures for modelctl tests."""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Generator

import pytest


@pytest.fixture
def tmp_registry(monkeypatch) -> Generator[Path, None, None]:
    """Replace registry paths with temp dir so tests don't touch real files."""
    tmp = Path(tempfile.mkdtemp())
    reg_dir = tmp / "registry"
    sto_dir = tmp / "storage"
    reg_dir.mkdir(parents=True)
    sto_dir.mkdir(parents=True)

    # Point registry module at temp paths
    import modelctl.registry as reg
    monkeypatch.setattr(reg, "REGISTRY_DIR", reg_dir)
    monkeypatch.setattr(reg, "STORAGE_DIR", sto_dir)
    monkeypatch.setattr(reg, "MODELS_PATH", reg_dir / "models.json")
    monkeypatch.setattr(reg, "DOWNLOADS_PATH", reg_dir / "downloads.json")
    monkeypatch.setattr(reg, "ACTIVE_PATH", reg_dir / "active.json")

    # Write empty state files
    for name, default in [("models.json", {"models": []}),
                          ("downloads.json", {"downloads": []}),
                          ("active.json", {"active": []})]:
        (reg_dir / name).write_text(json.dumps(default))

    yield tmp

    # Cleanup
    import shutil
    shutil.rmtree(tmp, ignore_errors=True)


@pytest.fixture
def sample_model_data() -> dict:
    return {
        "id": "test-model",
        "name": "Test Model",
        "type": "chat",
        "provider": "huggingface",
        "repo_id": "test/test-model",
        "storage_path": "chat/test-model",
        "status": "installed",
        "artifacts": [
            {"name": "model.gguf", "role": "primary", "path": "files/model.gguf",
             "size": 1024, "file_type": "gguf", "sha256": "abc123"},
        ],
    }
