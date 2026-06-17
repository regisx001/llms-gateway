"""Tests for model CRUD and lifecycle endpoints."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient


class TestListModels:
    def test_list_empty(self, client: TestClient):
        resp = client.get("/api/v1/models")
        assert resp.status_code == 200
        data = resp.json()
        assert data["models"] == []
        assert data["total"] == 0

    def test_list_with_data(self, seeded_client: TestClient):
        resp = seeded_client.get("/api/v1/models")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        assert data["models"][0]["id"] == "test-model-001"

    def test_list_filter_by_type(self, seeded_client: TestClient):
        resp = seeded_client.get("/api/v1/models?type=chat")
        assert resp.status_code == 200
        assert resp.json()["total"] == 1

        resp = seeded_client.get("/api/v1/models?type=embedding")
        assert resp.status_code == 200
        assert resp.json()["total"] == 0

    def test_list_filter_by_status(self, seeded_client: TestClient):
        resp = seeded_client.get("/api/v1/models?status=installed")
        assert resp.status_code == 200
        assert resp.json()["total"] == 1

        resp = seeded_client.get("/api/v1/models?status=downloading")
        assert resp.status_code == 200
        assert resp.json()["total"] == 0


class TestGetModel:
    def test_get_existing(self, seeded_client: TestClient):
        resp = seeded_client.get("/api/v1/models/test-model-001")
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == "test-model-001"
        assert data["name"] == "Test Model"
        assert data["type"] == "chat"
        assert data["status"] == "installed"
        assert len(data["artifacts"]) == 1
        assert data["artifacts"][0]["name"] == "model.gguf"

    def test_get_nonexistent(self, client: TestClient):
        resp = client.get("/api/v1/models/nonexistent")
        assert resp.status_code == 404
        assert "detail" in resp.json()


class TestInstallModel:
    @patch("modelctl_api.services.model_service.hf.inspect")
    @patch("modelctl_api.services.model_service.hf.download_file")
    @patch("modelctl_api.services.model_service.hf.build_model_from_repo")
    @patch("modelctl_api.services.model_service.validator.validate_file")
    @patch("modelctl_api.services.model_service.validator.sha256")
    def test_install_success(
        self,
        mock_sha256,
        mock_validate,
        mock_build,
        mock_download,
        mock_inspect,
        client: TestClient,
    ):
        mock_inspect.return_value = {
            "repo_id": "test/MyModel-GGUF",
            "type": "chat",
            "description": "A test model",
            "downloads": 100,
            "likes": 10,
            "license": "mit",
            "pipeline_tag": "text-generation",
            "library_name": "transformers",
            "gguf_files": ["model-q4.gguf"],
            "all_files": ["model-q4.gguf", "config.json"],
            "siblings": [],
        }
        mock_build.return_value = __import__(
            "modelctl_core.models", fromlist=["Model"]
        ).Model(
            id="mymodel-gguf",
            name="MyModel-GGUF",
            type="chat",
            provider="huggingface",
            repo_id="test/MyModel-GGUF",
            status="registered",
            artifacts=[__import__("modelctl_core.models", fromlist=["Artifact"]).Artifact(
                name="model-q4.gguf", role="primary", file_type="gguf")],
        )

        import tempfile
        tmp_file = Path(tempfile.mktemp(suffix=".gguf"))
        tmp_file.write_bytes(b"\x47\x47\x55\x46" + b"\x00" * 1000)
        mock_download.return_value = tmp_file
        mock_validate.return_value = []
        mock_sha256.return_value = "aabbccdd"

        try:
            resp = client.post(
                "/api/v1/models/install",
                json={"repo_id": "test/MyModel-GGUF",
                      "filename": "model-q4.gguf"},
            )
            assert resp.status_code == 202
            data = resp.json()
            assert data["status"] == "installed"
        finally:
            tmp_file.unlink(missing_ok=True)

    def test_install_missing_fields(self, client: TestClient):
        resp = client.post("/api/v1/models/install", json={})
        assert resp.status_code == 422

    def test_install_missing_filename(self, client: TestClient):
        resp = client.post(
            "/api/v1/models/install", json={"repo_id": "test/repo"}
        )
        assert resp.status_code == 422

    @patch("modelctl_api.services.model_service.hf.inspect")
    def test_install_repo_not_found(self, mock_inspect, client: TestClient):
        mock_inspect.return_value = None
        resp = client.post(
            "/api/v1/models/install",
            json={"repo_id": "test/nonexistent", "filename": "model.gguf"},
        )
        assert resp.status_code == 400
        assert "not found" in resp.json()["detail"].lower()


class TestRemoveModel:
    def test_remove_existing(self, seeded_client: TestClient):
        resp = seeded_client.delete("/api/v1/models/test-model-001")
        assert resp.status_code == 200

        # Verify it's gone
        resp = seeded_client.get("/api/v1/models/test-model-001")
        assert resp.status_code == 404

    def test_remove_nonexistent(self, client: TestClient):
        resp = client.delete("/api/v1/models/nonexistent")
        assert resp.status_code == 404


class TestActivateDeactivate:
    def test_activate_success(self, seeded_client: TestClient):
        resp = seeded_client.post("/api/v1/models/test-model-001/activate")
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == "test-model-001"

    def test_activate_nonexistent(self, client: TestClient):
        resp = client.post("/api/v1/models/nonexistent/activate")
        assert resp.status_code == 404

    def test_deactivate_success(self, seeded_client: TestClient):
        resp = seeded_client.post("/api/v1/models/test-model-001/deactivate")
        assert resp.status_code == 200

    def test_deactivate_nonexistent(self, client: TestClient):
        resp = client.post("/api/v1/models/nonexistent/deactivate")
        assert resp.status_code == 404

    def test_activate_twice(self, seeded_client: TestClient):
        seeded_client.post("/api/v1/models/test-model-001/activate")
        resp = seeded_client.post("/api/v1/models/test-model-001/activate")
        assert resp.status_code == 200  # idempotent
