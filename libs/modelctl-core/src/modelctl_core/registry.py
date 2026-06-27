"""Registry — persistence abstraction for models, downloads, and active state.

This module acts as a thin proxy over a pluggable `RegistryStore` backend.
Set ``MODELCTL_STORE_BACKEND`` to ``"sqlite"`` to use SQLite instead of the
default JSON-file store.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

from .models import Model, Download


# ── backend selection ─────────────────────────────────────────────────
# The store singleton is created at import time based on env var.
# Switching backends at runtime is not supported (restart required).

_BACKEND = os.environ.get("MODELCTL_STORE_BACKEND", "json").strip().lower()

if _BACKEND == "sqlite":
    from .sqlite_store import SqliteStore as _StoreClass  # noqa: E402
else:
    from .json_store import JsonStore as _StoreClass  # noqa: E402

_store = _StoreClass()

# Re-export directories for backward-compatibility
REGISTRY_DIR: Path = _store.registry_dir
STORAGE_DIR: Path = _store.storage_dir
MODELS_PATH: Path = REGISTRY_DIR / "models.json"
DOWNLOADS_PATH: Path = REGISTRY_DIR / "downloads.json"
ACTIVE_PATH: Path = REGISTRY_DIR / "active.json"


# ── models ────────────────────────────────────────────────────────────

def load_models() -> list[Model]:
    return _store.load_models()


def save_models(models: list[Model]) -> None:
    _store.save_models(models)


def find_model(model_id: str, models: Optional[list[Model]] = None) -> Optional[Model]:
    return _store.find_model(model_id, models)


def update_model(model_id: str, **kwargs) -> bool:
    return _store.update_model(model_id, **kwargs)


def is_registered(repo_id: str, artifact_name: str) -> bool:
    return _store.is_registered(repo_id, artifact_name)


def add_model(model: Model) -> None:
    _store.add_model(model)


def remove_model(model_id: str) -> bool:
    return _store.remove_model(model_id)


# ── downloads ─────────────────────────────────────────────────────────

def load_downloads() -> list[Download]:
    return _store.load_downloads()


def save_downloads(downloads: list[Download]) -> None:
    _store.save_downloads(downloads)


def add_download(download: Download) -> None:
    _store.add_download(download)


def update_download(url: str, **kwargs) -> None:
    _store.update_download(url, **kwargs)


# ── active ────────────────────────────────────────────────────────────

def load_active() -> dict:
    return _store.load_active()


def set_active(model_id: str, type_: str) -> None:
    _store.set_active(model_id, type_)


def clear_active(model_id: str) -> None:
    _store.clear_active(model_id)


# ── storage paths ─────────────────────────────────────────────────────

def resolve_storage(model_type: str, model_id: str) -> Path:
    return _store.resolve_storage(model_type, model_id)
