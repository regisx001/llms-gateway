"""Tests that exercise store backends directly — JSON corruption, SQLite schema,
explicit directory injection, and edge cases that the registry-layer tests
can't easily reach.
"""

from __future__ import annotations

import json
import sqlite3
import tempfile
from pathlib import Path

import pytest

from modelctl_core.models import Model, Artifact, Download


# ── JSON store edge cases ──────────────────────────────────────────────

class TestJsonStoreEdgeCases:
    def test_load_corrupted_models_json(self, monkeypatch, tmp_path):
        """Corrupted models.json should return empty list, not crash."""
        from modelctl_core.json_store import JsonStore

        reg = tmp_path / "registry"
        reg.mkdir()
        (reg / "models.json").write_text("{{{ not json")

        store = JsonStore(registry_dir=reg)
        assert store.load_models() == []

    def test_load_corrupted_active_json(self, monkeypatch, tmp_path):
        """Corrupted active.json should return {'active': []}, not crash."""
        from modelctl_core.json_store import JsonStore

        reg = tmp_path / "registry"
        reg.mkdir()
        (reg / "active.json").write_text("garbage")

        store = JsonStore(registry_dir=reg)
        assert store.load_active() == {"active": []}

    def test_load_missing_files_auto_creates(self, tmp_path):
        """First access to a fresh dir auto-creates json files with defaults."""
        from modelctl_core.json_store import JsonStore

        reg = tmp_path / "registry"
        store = JsonStore(registry_dir=reg)

        assert store.load_models() == []
        assert store.load_downloads() == []
        assert store.load_active() == {"active": []}

        # Files should now exist
        assert (reg / "models.json").exists()
        assert (reg / "downloads.json").exists()
        assert (reg / "active.json").exists()

    def test_save_then_reload_preserves_all_data(self, tmp_path):
        """Full round-trip: save models + downloads + active, reload, verify."""
        from modelctl_core.json_store import JsonStore

        store = JsonStore(registry_dir=tmp_path / "registry")

        m = Model(id="m1", name="Test", type="chat",
                  artifacts=[Artifact(name="a.gguf", sha256="abc")])
        d = Download(url="http://x.com/a.gguf", destination="/tmp/a.gguf",
                     status="completed", total_bytes=100, downloaded_bytes=100)

        store.save_models([m])
        store.save_downloads([d])
        store.save_active({"active": [{"model_id": "m1", "type": "chat",
                                       "activated_at": "2024-01-01T00:00:00Z"}]})

        # Fresh store instance reads from disk
        from modelctl_core.json_store import JsonStore
        store2 = JsonStore(registry_dir=tmp_path / "registry")
        assert len(store2.load_models()) == 1
        assert store2.load_models()[0].id == "m1"
        assert len(store2.load_downloads()) == 1
        assert store2.load_downloads()[0].url == "http://x.com/a.gguf"
        assert len(store2.load_active()["active"]) == 1

    def test_explicit_storage_dir(self, tmp_path):
        """JsonStore with explicit registry_dir uses that path."""
        from modelctl_core.json_store import JsonStore

        reg = tmp_path / "custom-reg"
        store = JsonStore(registry_dir=str(reg))
        assert store.registry_dir == reg

    def test_load_models_handles_list_format(self, tmp_path):
        """If models.json contains a bare list (not dict), handle it."""
        from modelctl_core.json_store import JsonStore

        reg = tmp_path / "registry"
        reg.mkdir()
        (reg / "models.json").write_text(json.dumps([
            {"id": "m1", "name": "M1", "type": "chat",
             "provider": "huggingface", "repo_id": "x/y",
             "storage_path": "chat/m1", "status": "installed",
             "artifacts": []},
        ]))

        store = JsonStore(registry_dir=reg)
        models = store.load_models()
        assert len(models) == 1
        assert models[0].id == "m1"

    def test_load_active_handles_list_format(self, tmp_path):
        """If active.json contains a bare list, it's returned as-is (valid JSON)."""
        from modelctl_core.json_store import JsonStore

        reg = tmp_path / "registry"
        reg.mkdir()
        (reg / "active.json").write_text("[]")

        store = JsonStore(registry_dir=reg)
        assert store.load_active() == []  # valid JSON, parsed as bare list


# ── SQLite store edge cases ────────────────────────────────────────────

class TestSqliteStoreEdgeCases:
    def test_schema_created_on_init(self, tmp_path):
        """SqliteStore creates tables on first init."""
        from modelctl_core.sqlite_store import SqliteStore

        reg = tmp_path / "registry"
        store = SqliteStore(registry_dir=reg)

        db = reg / "registry.db"
        assert db.exists()

        # Verify tables exist
        tables = store._conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        ).fetchall()
        table_names = {r["name"] for r in tables}
        assert "models" in table_names
        assert "downloads" in table_names
        assert "active" in table_names

    def test_full_roundtrip(self, tmp_path):
        """Full save + reload cycle through SQLite."""
        from modelctl_core.sqlite_store import SqliteStore

        store = SqliteStore(registry_dir=tmp_path / "registry")

        m = Model(id="m1", name="Test", type="chat",
                  artifacts=[Artifact(name="a.gguf", sha256="abc")])
        d = Download(url="http://x.com/a.gguf", destination="/tmp/a.gguf",
                     status="completed", total_bytes=100, downloaded_bytes=100)

        store.save_models([m])
        store.save_downloads([d])
        store.save_active({"active": [{"model_id": "m1", "type": "chat",
                                       "activated_at": "2024-01-01T00:00:00Z"}]})

        # New connection, same db
        from modelctl_core.sqlite_store import SqliteStore
        store2 = SqliteStore(registry_dir=tmp_path / "registry")
        assert len(store2.load_models()) == 1
        assert store2.load_models()[0].artifacts[0].sha256 == "abc"
        assert len(store2.load_downloads()) == 1
        assert len(store2.load_active()["active"]) == 1

    def test_upsert_replaces_existing(self, tmp_path):
        """Saving a model with same id replaces the old record."""
        from modelctl_core.sqlite_store import SqliteStore

        store = SqliteStore(registry_dir=tmp_path / "registry")

        m1 = Model(id="m1", name="Old")
        store.save_models([m1])

        m2 = Model(id="m1", name="New")
        store.save_models([m2])

        models = store.load_models()
        assert len(models) == 1
        assert models[0].name == "New"

    def test_remove_deletes_from_db(self, tmp_path):
        """Saving fewer models deletes the removed ones from SQLite."""
        from modelctl_core.sqlite_store import SqliteStore

        store = SqliteStore(registry_dir=tmp_path / "registry")

        m1 = Model(id="m1", name="Keep")
        m2 = Model(id="m2", name="Remove")
        store.save_models([m1, m2])

        store.save_models([m1])  # Only keep m1
        models = store.load_models()
        assert len(models) == 1
        assert models[0].id == "m1"

    def test_load_downloads_empty(self, tmp_path):
        from modelctl_core.sqlite_store import SqliteStore
        store = SqliteStore(registry_dir=tmp_path / "registry")
        assert store.load_downloads() == []

    def test_explicit_directory(self, tmp_path):
        from modelctl_core.sqlite_store import SqliteStore
        reg = tmp_path / "custom-reg"
        store = SqliteStore(registry_dir=str(reg))
        assert store.registry_dir == reg
        assert store.storage_dir is not None

    def test_remove_nonexistent_model(self, tmp_path):
        """remove_model on nonexistent id returns False."""
        from modelctl_core.sqlite_store import SqliteStore
        store = SqliteStore(registry_dir=tmp_path / "registry")
        assert store.remove_model("nonexistent") is False

    def test_update_nonexistent_model(self, tmp_path):
        """update_model on nonexistent id returns False."""
        from modelctl_core.sqlite_store import SqliteStore
        store = SqliteStore(registry_dir=tmp_path / "registry")
        assert store.update_model("nonexistent", status="active") is False

    def test_is_registered_no_models(self, tmp_path):
        """is_registered with no models returns False cleanly."""
        from modelctl_core.sqlite_store import SqliteStore
        store = SqliteStore(registry_dir=tmp_path / "registry")
        assert store.is_registered("x/y", "a.gguf") is False
