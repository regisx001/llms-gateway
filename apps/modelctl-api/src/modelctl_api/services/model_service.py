"""Model management service — delegates to modelctl_core registry."""

from __future__ import annotations

import datetime
import os
import time
from pathlib import Path

from modelctl_core import registry
from modelctl_core.models import Model, Artifact, Download
from modelctl_core import huggingface as hf
from modelctl_core import validator


# ── domain exceptions ────────────────────────────────────────────────

class ModelctlError(Exception):
    """Base exception for modelctl operations."""


class ModelNotFoundError(ModelctlError):
    """Requested model does not exist in the registry."""


# ── helpers ──────────────────────────────────────────────────────────

def _size_str(n: int) -> str:
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if n < 1024:
            return f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} PB"


def _model_to_dict(m: Model) -> dict:
    """Convert a core Model dataclass to the API response shape."""
    return {
        "id": m.id,
        "name": m.name,
        "type": m.type,
        "provider": m.provider,
        "repo_id": m.repo_id,
        "status": m.status,
        "installed_at": m.installed_at,
        "storage_path": m.storage_path,
        "artifacts": [
            {
                "name": a.name,
                "role": a.role,
                "path": a.path,
                "size": a.size,
                "file_type": a.file_type,
                "sha256": a.sha256,
            }
            for a in m.artifacts
        ],
        "metadata": m.metadata,
    }


def _storage_path(model: Model) -> Path:
    rel = model.storage_path
    if rel.startswith("storage/"):
        rel = rel[len("storage/"):]
    return registry.STORAGE_DIR / rel


# ── service ──────────────────────────────────────────────────────────

class ModelService:
    """Business logic for model CRUD and lifecycle."""

    def list_models(
        self,
        type_filter: str | None = None,
        status_filter: str | None = None,
    ) -> list[dict]:
        """Return all models, optionally filtered by type and/or status."""
        models = registry.load_models()
        if type_filter:
            models = [m for m in models if m.type == type_filter]
        if status_filter:
            models = [m for m in models if m.status == status_filter]
        return [_model_to_dict(m) for m in models]

    def get_model(self, model_id: str) -> dict:
        """Return a single model by ID."""
        m = registry.find_model(model_id)
        if not m:
            raise ModelNotFoundError(f"Model not found: {model_id}")
        return _model_to_dict(m)

    def install_model(
        self,
        repo_id: str,
        filename: str,
        model_type: str | None = None,
    ) -> dict:
        """Install a model: inspect repo, download file, register in registry."""
        # Check if already installed
        for m in registry.load_models():
            if m.repo_id == repo_id and any(a.name == filename for a in m.artifacts):
                if m.status == "installed":
                    raise ModelctlError(
                        f"Already installed: {repo_id} / {filename}"
                    )

        # Inspect repo
        info = hf.inspect(repo_id)
        if not info:
            raise ModelctlError(f"Repository not found: {repo_id}")
        if filename not in info["all_files"]:
            raise ModelctlError(
                f"File '{filename}' not found in repository. "
                f"Available GGUF files: {', '.join(info['gguf_files'])}"
            )

        # Build model object
        model = hf.build_model_from_repo(
            repo_id, filename, model_type or "", repo_info=info
        )
        model.status = "downloading"
        registry.add_model(model)

        storage_dir = registry.resolve_storage(model.type, model.id)
        files_dir = storage_dir / "files"
        if files_dir.exists():
            import shutil
            shutil.rmtree(files_dir)
        files_dir.mkdir(parents=True, exist_ok=True)

        # Register download
        url = f"https://huggingface.co/{repo_id}/resolve/main/{filename}"
        dl = Download(url=url, destination=str(
            files_dir / filename), status="downloading")
        registry.add_download(dl)

        # Download with progress
        last_update = [time.time()]

        def on_progress(current: int, total: int):
            now = time.time()
            if now - last_update[0] > 0.3 or current >= total:
                last_update[0] = now
                registry.update_download(
                    url, downloaded_bytes=current, total_bytes=total)

        try:
            dest = hf.download_file(
                repo_id, filename, files_dir, on_progress=on_progress)
        except Exception as e:
            registry.update_download(url, status="failed", error=str(e))
            registry.update_model(model.id, status="error")
            raise ModelctlError(f"Download failed: {e}") from e

        # Validate
        issues = validator.validate_file(dest)
        if issues:
            registry.update_model(model.id, status="error")
            raise ModelctlError(f"Validation failed: {'; '.join(issues)}")

        # Finalize
        actual_size = dest.stat().st_size
        artifact = Artifact(
            name=filename,
            role="primary",
            path=f"files/{filename}",
            size=actual_size,
            file_type="gguf",
            sha256=validator.sha256(dest),
        )
        installed_at = datetime.datetime.now(datetime.timezone.utc).isoformat()
        registry.update_model(
            model.id,
            status="installed",
            storage_path=f"{model.type}/{model.id}",
            artifacts=[artifact],
            installed_at=installed_at,
        )
        registry.update_download(
            url,
            status="completed",
            downloaded_bytes=actual_size,
            total_bytes=actual_size,
            completed_at=installed_at,
        )

        return self.get_model(model.id)

    def remove_model(self, model_id: str) -> dict:
        """Remove a model and its files from disk."""
        m = registry.find_model(model_id)
        if not m:
            raise ModelNotFoundError(f"Model not found: {model_id}")

        # Remove from disk
        storage_dir = _storage_path(m)
        if storage_dir.exists():
            import shutil
            shutil.rmtree(storage_dir)

        # Clear active state
        registry.clear_active(model_id)

        # Remove symlink
        symlink = registry.STORAGE_DIR / f"{m.id}.gguf"
        if symlink.is_symlink() or symlink.exists():
            symlink.unlink()

        # Remove from registry
        result = _model_to_dict(m)
        registry.remove_model(model_id)
        return result

    def activate_model(self, model_id: str) -> dict:
        """Activate a model: create symlink, update active.json."""
        m = registry.find_model(model_id)
        if not m:
            raise ModelNotFoundError(f"Model not found: {model_id}")
        if m.status != "installed":
            raise ModelctlError(
                f"Model status is '{m.status}', must be 'installed'"
            )

        primary = next(
            (a for a in m.artifacts if a.role == "primary"),
            m.artifacts[0] if m.artifacts else None,
        )
        if not primary:
            raise ModelctlError(f"No artifacts found for {model_id}")

        # Remove existing .gguf symlinks, then create the new one
        storage_dir = registry.STORAGE_DIR
        storage_dir.mkdir(exist_ok=True)
        for p in storage_dir.glob("*.gguf"):
            if p.is_symlink() or p.exists():
                p.unlink()

        symlink = storage_dir / f"{m.id}.gguf"
        target = _storage_path(m) / primary.path
        relative_target = os.path.relpath(target, storage_dir)
        symlink.symlink_to(relative_target)

        registry.set_active(model_id, m.type)

        return self.get_model(model_id)

    def deactivate_model(self, model_id: str) -> dict:
        """Deactivate a model: remove from active.json, remove symlink."""
        m = registry.find_model(model_id)
        if not m:
            raise ModelNotFoundError(f"Model not found: {model_id}")

        registry.clear_active(model_id)
        symlink = registry.STORAGE_DIR / f"{m.id}.gguf"
        if symlink.is_symlink() or symlink.exists():
            symlink.unlink()

        return self.get_model(model_id)
