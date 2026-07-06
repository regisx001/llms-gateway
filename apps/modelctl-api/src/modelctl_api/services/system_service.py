"""System service — health, info, reload."""

from __future__ import annotations

import shutil
from pathlib import Path

from modelctl_core import registry


def _get_disk_usage(path: Path) -> tuple[str, str]:
    """Return (used, free) as human-readable strings."""
    try:
        usage = shutil.disk_usage(path)
        used = _size_str(usage.used)
        free = _size_str(usage.free)
        return used, free
    except OSError:
        return "unknown", "unknown"


def _size_str(n: int) -> str:
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if n < 1024:
            return f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} PB"


class SystemService:
    """Business logic for system-level operations."""

    def __init__(self, version: str = "0.1.0") -> None:
        self._version = version

    def health(self) -> dict:
        """Liveness check."""
        return {"status": "ok", "version": self._version}

    def ready(self) -> dict:
        """Readiness check — verify registry is writable."""
        try:
            registry.REGISTRY_DIR.mkdir(parents=True, exist_ok=True)
            test_file = registry.REGISTRY_DIR / ".write_test"
            test_file.write_text("ok")
            test_file.unlink()
            return {"status": "ok", "version": self._version}
        except OSError:
            return {"status": "degraded", "version": self._version}

    def info(self) -> dict:
        """System info: version, storage usage, model count."""
        models = registry.load_models()
        used, free = _get_disk_usage(registry.STORAGE_DIR)

        return {
            "version": self._version,
            "storage_used": used,
            "storage_free": free,
            "models_count": len(models),
            "active_models": [],
        }
