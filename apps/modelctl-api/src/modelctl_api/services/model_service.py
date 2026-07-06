"""Model management service — delegates to modelctl_core registry."""

from __future__ import annotations

import datetime
import os
import threading
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
        """Install a model — validate and start background download.

        Returns immediately with the model in 'downloading' status.
        The actual download runs in a background thread.
        """
        # Check if already installed
        for m in registry.load_models():
            if m.repo_id == repo_id and any(a.name == filename for a in m.artifacts):
                if m.status == "installed" or m.status == "active":
                    raise ModelctlError(
                        f"Already installed: {repo_id} / {filename}"
                    )

        # Inspect repo (synchronous — fast API call)
        info = hf.inspect(repo_id)
        if not info:
            raise ModelctlError(f"Repository not found: {repo_id}")
        if filename not in info["all_files"]:
            raise ModelctlError(
                f"File '{filename}' not found in repository. "
                f"Available GGUF files: {', '.join(info['gguf_files'])}"
            )

        # Build model object and register immediately
        model = hf.build_model_from_repo(
            repo_id, filename, model_type or "", repo_info=info
        )
        model.status = "downloading"
        registry.add_model(model)

        # Prepare storage directory
        storage_dir = registry.resolve_storage(model.type, model.id)
        files_dir = storage_dir / "files"
        if files_dir.exists():
            import shutil
            shutil.rmtree(files_dir)
        files_dir.mkdir(parents=True, exist_ok=True)

        # Register download entry with total size from repo info
        url = f"https://huggingface.co/{repo_id}/resolve/main/{filename}"
        # Try to find file size from siblings
        total_size = 0
        for sib in info.get("siblings", []):
            if sib.get("rfilename") == filename:
                total_size = sib.get("size", 0)
                break

        dl = Download(
            url=url,
            destination=str(files_dir / filename),
            total_bytes=total_size,
            status="downloading",
            started_at=datetime.datetime.now(
                datetime.timezone.utc).isoformat(),
        )
        registry.add_download(dl)

        # Start background download
        model_id = model.id
        thread = threading.Thread(
            target=self._run_install,
            args=(model_id, repo_id, filename, files_dir, url, info),
            daemon=True,
        )
        thread.start()

        return self.get_model(model_id)

    def _run_install(
        self,
        model_id: str,
        repo_id: str,
        filename: str,
        files_dir: Path,
        url: str,
        info: dict,
    ):
        """Background thread: download, validate, finalize."""
        last_update = [time.time()]

        def on_progress(current: int, total: int):
            now = time.time()
            if now - last_update[0] > 0.5 or current >= total:
                last_update[0] = now
                registry.update_download(
                    url, downloaded_bytes=current, total_bytes=max(total, current))

        try:
            dest = hf.download_file(
                repo_id, filename, files_dir, on_progress=on_progress)
        except Exception as e:
            registry.update_download(url, status="failed", error=str(e))
            registry.update_model(model_id, status="error")
            return

        # Validate
        issues = validator.validate_file(dest)
        if issues:
            registry.update_model(model_id, status="error")
            registry.update_download(
                url, status="failed", error=f"Validation: {'; '.join(issues)}")
            return

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
            model_id,
            status="installed",
            storage_path=f"{info.get('type', 'experimental')}/{model_id}",
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

    def get_download_progress(self, model_id: str) -> dict | None:
        """Get download progress for a model, or None if not found."""
        m = registry.find_model(model_id)
        if not m:
            return None

        # Find the download entry for this model
        dls = registry.load_downloads()
        dl = None
        for d in dls:
            # Match by destination containing the model id
            if model_id in d.destination:
                dl = d
                break

        if not dl:
            return {
                "model_id": model_id,
                "status": m.status,
                "downloaded_bytes": 0,
                "total_bytes": 0,
                "progress_pct": 0,
            }

        progress_pct = 0
        if dl.total_bytes > 0:
            progress_pct = round(dl.downloaded_bytes * 100 / dl.total_bytes)

        return {
            "model_id": model_id,
            "repo_id": m.repo_id,
            "filename": m.artifacts[0].name if m.artifacts else "unknown",
            "status": m.status,
            "downloaded_bytes": dl.downloaded_bytes,
            "total_bytes": dl.total_bytes,
            "progress_pct": progress_pct,
            "error": dl.error,
        }

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

        # Remove from registry
        result = _model_to_dict(m)
        registry.remove_model(model_id)
        return result
