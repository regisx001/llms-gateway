"""SQLite persistence backend for the registry."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from .store import RegistryStore
from .models import Model, Download
from ._locations import find_registry_root, find_storage_root


_SQL_SCHEMA = """
CREATE TABLE IF NOT EXISTS models (
    id          TEXT PRIMARY KEY,
    data        TEXT NOT NULL,
    created_at  TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at  TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS downloads (
    url         TEXT PRIMARY KEY,
    data        TEXT NOT NULL,
    created_at  TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at  TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS active (
    model_id     TEXT NOT NULL,
    type         TEXT NOT NULL DEFAULT '',
    activated_at TEXT NOT NULL
);
"""


class SqliteStore(RegistryStore):
    """SQLite-based registry storage.

    Stores model and download metadata as JSON blobs in SQLite tables.
    The active state is stored as plain rows.

    Database location: ``{registry_dir}/registry.db``
    """

    def __init__(self, registry_dir: str | Path | None = None) -> None:
        if registry_dir:
            self._registry_dir = Path(registry_dir)
        else:
            self._registry_dir = find_registry_root()

        self._storage_dir = find_storage_root()
        self._db_path = self._registry_dir / "registry.db"
        self._db_path.parent.mkdir(parents=True, exist_ok=True)

        self._conn = sqlite3.connect(
            str(self._db_path), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.executescript(_SQL_SCHEMA)
        self._conn.commit()

    # ── directories ─────────────────────────────────────────────────

    @property
    def registry_dir(self) -> Path:
        return self._registry_dir

    @property
    def storage_dir(self) -> Path:
        return self._storage_dir

    # ── models ──────────────────────────────────────────────────────

    def load_models(self) -> list[Model]:
        rows = self._conn.execute(
            "SELECT data FROM models ORDER BY created_at"
        ).fetchall()
        return [Model(**json.loads(row["data"])) for row in rows]

    def save_models(self, models: list[Model]) -> None:
        # Track which IDs are present so we can delete removed ones
        current_ids = {m.id for m in models}
        existing_ids = {
            row["id"] for row in
            self._conn.execute("SELECT id FROM models").fetchall()
        }

        # Upsert each model
        for m in models:
            data = json.dumps(m.to_dict(), ensure_ascii=False)
            self._conn.execute(
                """INSERT INTO models (id, data, updated_at)
                   VALUES (?, ?, datetime('now'))
                   ON CONFLICT(id) DO UPDATE SET
                       data = excluded.data,
                       updated_at = excluded.updated_at""",
                (m.id, data),
            )

        # Delete removed models
        for removed_id in existing_ids - current_ids:
            self._conn.execute(
                "DELETE FROM models WHERE id = ?", (removed_id,))

        self._conn.commit()

    # ── downloads ───────────────────────────────────────────────────

    def load_downloads(self) -> list[Download]:
        rows = self._conn.execute(
            "SELECT data FROM downloads ORDER BY created_at"
        ).fetchall()
        return [Download(**json.loads(row["data"])) for row in rows]

    def save_downloads(self, downloads: list[Download]) -> None:
        current_urls = {d.url for d in downloads}
        existing_urls = {
            row["url"] for row in
            self._conn.execute("SELECT url FROM downloads").fetchall()
        }

        for d in downloads:
            data = json.dumps(d.to_dict(), ensure_ascii=False)
            self._conn.execute(
                """INSERT INTO downloads (url, data, updated_at)
                   VALUES (?, ?, datetime('now'))
                   ON CONFLICT(url) DO UPDATE SET
                       data = excluded.data,
                       updated_at = excluded.updated_at""",
                (d.url, data),
            )

        for removed_url in existing_urls - current_urls:
            self._conn.execute(
                "DELETE FROM downloads WHERE url = ?", (removed_url,))

        self._conn.commit()

    # ── active ──────────────────────────────────────────────────────

    def load_active(self) -> dict:
        rows = self._conn.execute(
            "SELECT model_id, type, activated_at FROM active ORDER BY activated_at"
        ).fetchall()
        return {
            "active": [
                {"model_id": r["model_id"], "type": r["type"],
                 "activated_at": r["activated_at"]}
                for r in rows
            ]
        }

    def save_active(self, data: dict) -> None:
        self._conn.execute("DELETE FROM active")
        for entry in data.get("active", []):
            self._conn.execute(
                "INSERT INTO active (model_id, type, activated_at) VALUES (?, ?, ?)",
                (entry["model_id"], entry.get("type", ""),
                 entry.get("activated_at", "")),
            )
        self._conn.commit()
