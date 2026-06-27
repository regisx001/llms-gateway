"""JSON-file persistence backend for the registry."""

from __future__ import annotations

import json
from pathlib import Path

from .store import RegistryStore
from .models import Model, Download
from ._locations import find_registry_root, find_storage_root


def _ensure(path: Path, default):
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w") as f:
            json.dump(default, f, indent=2)
            f.write("\n")


def _load_json(path: Path) -> list | dict:
    try:
        with open(path) as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return [] if path.name != "active.json" else {"active": []}


def _save_json(path: Path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")


class JsonStore(RegistryStore):
    """JSON-file based registry storage.

    Uses three files in the registry directory:
      - models.json
      - downloads.json
      - active.json
    """

    def __init__(self, registry_dir: str | Path | None = None) -> None:
        if registry_dir:
            self._registry_dir = Path(registry_dir)
        else:
            self._registry_dir = find_registry_root()

        self._storage_dir = find_storage_root()
        self._models_path = self._registry_dir / "models.json"
        self._downloads_path = self._registry_dir / "downloads.json"
        self._active_path = self._registry_dir / "active.json"

        # Auto-create files on first access
        _ensure(self._models_path, {"models": []})
        _ensure(self._downloads_path, {"downloads": []})
        _ensure(self._active_path, {"active": []})

    # ── directories ─────────────────────────────────────────────────

    @property
    def registry_dir(self) -> Path:
        return self._registry_dir

    @property
    def storage_dir(self) -> Path:
        return self._storage_dir

    # ── models ──────────────────────────────────────────────────────

    def load_models(self) -> list[Model]:
        raw = _load_json(self._models_path)
        if isinstance(raw, dict):
            raw = raw.get("models", [])
        return [Model(**m) if not isinstance(m, Model) else m for m in raw]

    def save_models(self, models: list[Model]) -> None:
        _save_json(self._models_path, {
                   "models": [m.to_dict() for m in models]})

    # ── downloads ───────────────────────────────────────────────────

    def load_downloads(self) -> list[Download]:
        raw = _load_json(self._downloads_path)
        if isinstance(raw, dict):
            raw = raw.get("downloads", [])
        return [Download(**d) for d in raw]

    def save_downloads(self, downloads: list[Download]) -> None:
        _save_json(self._downloads_path, {
                   "downloads": [d.to_dict() for d in downloads]})

    # ── active ──────────────────────────────────────────────────────

    def load_active(self) -> dict:
        return _load_json(self._active_path)

    def save_active(self, data: dict) -> None:
        _save_json(self._active_path, data)
