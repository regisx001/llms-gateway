"""Tests for system endpoints."""

from __future__ import annotations

from fastapi.testclient import TestClient


class TestSystemInfo:
    def test_system_info_shape(self, client: TestClient):
        resp = client.get("/api/v1/system/info")
        assert resp.status_code == 200
        data = resp.json()
        assert "version" in data
        assert "storage_used" in data
        assert "storage_free" in data
        assert "models_count" in data
        assert "active_models" in data
        assert data["models_count"] == 0
        assert data["active_models"] == []

    def test_system_info_with_active(self, seeded_client: TestClient):
        # Activate a model first
        seeded_client.post("/api/v1/models/test-model-001/activate")
        resp = seeded_client.get("/api/v1/system/info")
        data = resp.json()
        assert data["models_count"] >= 1
        assert "test-model-001" in data["active_models"]


class TestSystemReload:
    def test_reload_no_pid(self, client: TestClient):
        """When no PID file exists, reload should not crash."""
        resp = client.post("/api/v1/system/reload")
        assert resp.status_code == 200
        data = resp.json()
        # Either no_pid_file or error is acceptable
        assert "status" in data
