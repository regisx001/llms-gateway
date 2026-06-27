"""Abstract storage backend for model registry metadata.

Provides the `RegistryStore` ABC that defines the contract for persisting
models, downloads, and active state. Concrete backends (JSON, SQLite, etc.)
implement this interface.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional

from .models import Model, Download


class RegistryStore(ABC):
    """Abstract base for registry persistence backends.

    Implementations must provide CRUD operations for three collections:
      - models (list of Model)
      - downloads (list of Download)
      - active state (dict with an "active" key)
    """

    # ── directories ─────────────────────────────────────────────────

    @property
    @abstractmethod
    def registry_dir(self) -> Path: ...

    @property
    @abstractmethod
    def storage_dir(self) -> Path: ...

    # ── models ──────────────────────────────────────────────────────

    @abstractmethod
    def load_models(self) -> list[Model]: ...

    @abstractmethod
    def save_models(self, models: list[Model]) -> None: ...

    def add_model(self, model: Model) -> None:
        models = self.load_models()
        models.append(model)
        self.save_models(models)

    def remove_model(self, model_id: str) -> bool:
        models = self.load_models()
        filtered = [m for m in models if m.id != model_id]
        if len(filtered) == len(models):
            return False
        self.save_models(filtered)
        return True

    def find_model(self, model_id: str, models: Optional[list[Model]] = None) -> Optional[Model]:
        if models is None:
            models = self.load_models()
        for m in models:
            if m.id == model_id:
                return m
        return None

    def update_model(self, model_id: str, **kwargs) -> bool:
        models = self.load_models()
        for m in models:
            if m.id == model_id:
                for k, v in kwargs.items():
                    setattr(m, k, v)
                self.save_models(models)
                return True
        return False

    def is_registered(self, repo_id: str, artifact_name: str) -> bool:
        for m in self.load_models():
            if m.repo_id == repo_id:
                for a in m.artifacts:
                    if a.name == artifact_name:
                        return True
        return False

    # ── downloads ───────────────────────────────────────────────────

    @abstractmethod
    def load_downloads(self) -> list[Download]: ...

    @abstractmethod
    def save_downloads(self, downloads: list[Download]) -> None: ...

    def add_download(self, download: Download) -> None:
        dls = self.load_downloads()
        dls.append(download)
        self.save_downloads(dls)

    def update_download(self, url: str, **kwargs) -> None:
        dls = self.load_downloads()
        for d in dls:
            if d.url == url:
                for k, v in kwargs.items():
                    setattr(d, k, v)
                break
        self.save_downloads(dls)

    # ── active ──────────────────────────────────────────────────────

    @abstractmethod
    def load_active(self) -> dict: ...

    @abstractmethod
    def save_active(self, data: dict) -> None: ...

    def set_active(self, model_id: str, type_: str) -> None:
        import datetime
        data = self.load_active()
        entries = data.get("active", [])

        # Displace any currently-active model of the same type
        displaced = [
            e["model_id"] for e in entries
            if e.get("type") == type_ and e.get("model_id") != model_id
        ]

        # Preserve entries with different types; replace same-type entry
        other_types = [e for e in entries if e.get("type") != type_]
        other_types.append({
            "model_id": model_id,
            "type": type_,
            "activated_at": datetime.datetime.now(
                datetime.timezone.utc).isoformat(),
        })
        data["active"] = other_types
        self.save_active(data)

        for displaced_id in displaced:
            self.update_model(displaced_id, status="installed")

    def clear_active(self, model_id: str) -> None:
        data = self.load_active()
        data["active"] = [e for e in data.get(
            "active", []) if e.get("model_id") != model_id]
        self.save_active(data)
        self.update_model(model_id, status="installed")

    # ── storage paths ───────────────────────────────────────────────

    def resolve_storage(self, model_type: str, model_id: str) -> Path:
        return self.storage_dir / model_type / model_id
