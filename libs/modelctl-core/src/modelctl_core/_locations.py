"""Shared location-resolution helpers for registry and storage directories.

Used by both JSON and SQLite store backends so that directory discovery
logic lives in a single place.
"""

from __future__ import annotations

import os
from pathlib import Path


def find_registry_root() -> Path:
    """Find the registry/ directory via env var, container path, or tree walk."""
    env_root = os.environ.get("MODELCTL_REGISTRY_DIR")
    if env_root:
        return Path(env_root)

    # Tree-walk from the package location up to the project root
    current = Path(__file__).resolve().parent
    for _ in range(8):
        candidate = current / "registry"
        if candidate.is_dir():
            return candidate
        if current.parent == current:
            break
        current = current.parent

    # Container fallback — checked after tree-walk so dev mode prefers project dirs
    fallback_container = Path("/opt/model-manager/registry")
    if fallback_container.exists():
        return fallback_container

    fallback = Path(__file__).resolve(
    ).parent.parent.parent.parent.parent / "registry"
    return fallback


def find_storage_root() -> Path:
    """Find the storage/ directory via env var, container path, or tree walk."""
    env_root = os.environ.get("MODELCTL_STORAGE_DIR")
    if env_root:
        return Path(env_root)

    # Tree-walk from the package location up to the project root
    current = Path(__file__).resolve().parent
    for _ in range(8):
        candidate = current / "storage"
        if candidate.is_dir():
            return candidate
        if current.parent == current:
            break
        current = current.parent

    # Container fallback — checked after tree-walk so dev mode prefers project dirs
    fallback_container = Path("/home/regisx001/LLMGateway-Models/storage")
    if fallback_container.exists():
        return fallback_container

    fallback = Path(__file__).resolve(
    ).parent.parent.parent.parent.parent / "storage"
    return fallback
