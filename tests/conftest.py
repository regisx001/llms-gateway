"""Shared fixtures for modelctl tests — supports JSON and SQLite backends."""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Generator

import pytest


def _create_store(backend: str, reg_dir: Path, sto_dir: Path):
    """Create a store instance of the given backend pointing at temp dirs."""
    if backend == "sqlite":
        from modelctl_core.sqlite_store import SqliteStore
        return SqliteStore(registry_dir=reg_dir)
    else:
        from modelctl_core.json_store import JsonStore
        return JsonStore(registry_dir=reg_dir)


def _setup_registry_env(reg_dir: Path, sto_dir: Path) -> None:
    """Configure env vars so the stores locate the temp directories."""
    os.environ["MODELCTL_REGISTRY_DIR"] = str(reg_dir)
    os.environ["MODELCTL_STORAGE_DIR"] = str(sto_dir)


def _clear_registry_env() -> None:
    """Remove test env overrides."""
    os.environ.pop("MODELCTL_REGISTRY_DIR", None)
    os.environ.pop("MODELCTL_STORAGE_DIR", None)
    os.environ.pop("MODELCTL_STORE_BACKEND", None)


def _make_tmp_registry(monkeypatch, backend: str = "json") -> Path:
    """Core logic: create temp dirs, build a fresh store, monkeypatch registry."""
    tmp = Path(tempfile.mkdtemp())
    reg_dir = tmp / "registry"
    sto_dir = tmp / "storage"
    reg_dir.mkdir(parents=True)
    sto_dir.mkdir(parents=True)

    _setup_registry_env(reg_dir, sto_dir)
    os.environ["MODELCTL_STORE_BACKEND"] = backend

    store = _create_store(backend, reg_dir, sto_dir)

    # Monkeypatch the registry module so all functions use the temp store
    import modelctl_core.registry as reg
    monkeypatch.setattr(reg, "_store", store)
    monkeypatch.setattr(reg, "REGISTRY_DIR", reg_dir)
    monkeypatch.setattr(reg, "STORAGE_DIR", sto_dir)
    monkeypatch.setattr(reg, "MODELS_PATH", reg_dir / "models.json")
    monkeypatch.setattr(reg, "DOWNLOADS_PATH", reg_dir / "downloads.json")
    monkeypatch.setattr(reg, "ACTIVE_PATH", reg_dir / "active.json")

    return tmp


# ── fixtures ──────────────────────────────────────────────────────────

@pytest.fixture
def tmp_registry(monkeypatch) -> Generator[Path, None, None]:
    """Replace registry store with JSON backend pointed at temp dirs."""
    tmp = _make_tmp_registry(monkeypatch, backend="json")
    yield tmp
    _clear_registry_env()
    import shutil
    shutil.rmtree(tmp, ignore_errors=True)


@pytest.fixture(params=["json", "sqlite"])
def tmp_registry_backend(request, monkeypatch) -> Generator[Path, None, None]:
    """Parametrized fixture: runs tests once with JSON, once with SQLite."""
    backend = request.param
    tmp = _make_tmp_registry(monkeypatch, backend=backend)
    yield tmp
    _clear_registry_env()
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
