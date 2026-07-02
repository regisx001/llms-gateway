"""Tests for _locations.py — registry and storage directory resolution."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

from modelctl_core._locations import find_registry_root, find_storage_root


def test_env_var_takes_priority(monkeypatch):
    """MODELCTL_REGISTRY_DIR env var should be used first."""
    tmp = tempfile.mkdtemp()
    monkeypatch.setenv("MODELCTL_REGISTRY_DIR", tmp)
    assert find_registry_root() == Path(tmp)

    monkeypatch.setenv("MODELCTL_STORAGE_DIR", tmp)
    assert find_storage_root() == Path(tmp)


def test_returns_path_type():
    """Both functions should return Path objects."""
    assert isinstance(find_registry_root(), Path)
    assert isinstance(find_storage_root(), Path)


def test_find_registry_root_finds_project():
    """From within the project tree, should find the real registry/ dir."""
    root = find_registry_root()
    assert root.name == "registry"
    assert root.is_dir()


def test_find_storage_root_finds_project():
    """From within the project tree, should find the real storage/ dir.

    Note: storage/ is gitignored (large model files), so it may not
    exist in CI. The name assertion validates resolution; the existence
    check only applies when the directory is present.
    """
    root = find_storage_root()
    assert root.name == "storage"
    if root.exists():
        assert root.is_dir()
