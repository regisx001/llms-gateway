"""Registry — JSON file persistence for models, downloads, and active state."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Optional

from .models import Model, Download

ROOT = Path(__file__).resolve().parent.parent
REGISTRY_DIR = ROOT / "registry"
STORAGE_DIR = ROOT / "storage"

MODELS_PATH = REGISTRY_DIR / "models.json"
DOWNLOADS_PATH = REGISTRY_DIR / "downloads.json"
ACTIVE_PATH = REGISTRY_DIR / "active.json"


# ── auto-create registry files on import ───────────────────────────

def _ensure(path: Path, default):
    if not path.exists():
        REGISTRY_DIR.mkdir(parents=True, exist_ok=True)
        with open(path, "w") as f:
            json.dump(default, f, indent=2)
            f.write("\n")


_ensure(MODELS_PATH, {"models": []})
_ensure(DOWNLOADS_PATH, {"downloads": []})
_ensure(ACTIVE_PATH, {"active": []})


# ── helpers ──────────────────────────────────────────────────────────

def _load(path: Path) -> list | dict:
    try:
        with open(path) as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return [] if path.name != "active.json" else {"active": []}


def _save(path: Path, data):
    REGISTRY_DIR.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")


# ── models ────────────────────────────────────────────────────────────

def load_models() -> list[Model]:
    raw = _load(MODELS_PATH)
    if isinstance(raw, dict):
        raw = raw.get("models", [])
    return [Model(**m) if not isinstance(m, Model) else m for m in raw]


def save_models(models: list[Model]):
    _save(MODELS_PATH, {"models": [m.to_dict() for m in models]})


def find_model(model_id: str, models: Optional[list[Model]] = None) -> Optional[Model]:
    if models is None:
        models = load_models()
    for m in models:
        if m.id == model_id:
            return m
    return None


def update_model(model_id: str, **kwargs) -> bool:
    models = load_models()
    for m in models:
        if m.id == model_id:
            for k, v in kwargs.items():
                setattr(m, k, v)
            save_models(models)
            return True
    return False


def is_registered(repo_id: str, artifact_name: str) -> bool:
    for m in load_models():
        if m.repo_id == repo_id:
            for a in m.artifacts:
                if a.name == artifact_name:
                    return True
    return False


def add_model(model: Model):
    models = load_models()
    models.append(model)
    save_models(models)


def remove_model(model_id: str) -> bool:
    models = load_models()
    filtered = [m for m in models if m.id != model_id]
    if len(filtered) == len(models):
        return False
    save_models(filtered)
    return True


# ── downloads ─────────────────────────────────────────────────────────

def load_downloads() -> list[Download]:
    raw = _load(DOWNLOADS_PATH)
    if isinstance(raw, dict):
        raw = raw.get("downloads", [])
    return [Download(**d) for d in raw]


def save_downloads(downloads: list[Download]):
    _save(DOWNLOADS_PATH, {"downloads": [d.to_dict() for d in downloads]})


def add_download(download: Download):
    dls = load_downloads()
    dls.append(download)
    save_downloads(dls)


def update_download(url: str, **kwargs):
    dls = load_downloads()
    for d in dls:
        if d.url == url:
            for k, v in kwargs.items():
                setattr(d, k, v)
            break
    save_downloads(dls)


# ── active ────────────────────────────────────────────────────────────

def load_active() -> dict:
    return _load(ACTIVE_PATH)


def set_active(model_id: str, type_: str):
    data = load_active()
    data["active"] = [e for e in data.get(
        "active", []) if e.get("type") != type_]
    data["active"].append({
        "model_id": model_id,
        "type": type_,
        "activated_at": __import__("datetime").datetime.now(
            __import__("datetime").timezone.utc).isoformat(),
    })
    _save(ACTIVE_PATH, data)


def clear_active(model_id: str):
    data = load_active()
    data["active"] = [e for e in data.get(
        "active", []) if e.get("model_id") != model_id]
    _save(ACTIVE_PATH, data)


# ── storage paths ─────────────────────────────────────────────────────

def resolve_storage(model_type: str, model_id: str) -> Path:
    return STORAGE_DIR / model_type / model_id
