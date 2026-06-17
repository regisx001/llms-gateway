"""Tests for search and inspect endpoints."""

from __future__ import annotations

from unittest.mock import patch

from fastapi.testclient import TestClient


class TestSearch:
    @patch("modelctl_api.services.search_service.hf.search")
    def test_search_returns_results(self, mock_search, client: TestClient):
        mock_search.return_value = [
            {
                "repo_id": "test/MyModel-GGUF",
                "type": "chat",
                "downloads": 5000,
                "likes": 100,
                "tags": ["transformers", "gguf"],
                "license": "mit",
            }
        ]
        resp = client.get("/api/v1/search", params={"q": "mymodel"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        assert data["results"][0]["repo_id"] == "test/MyModel-GGUF"

    @patch("modelctl_api.services.search_service.hf.search")
    def test_search_handles_empty(self, mock_search, client: TestClient):
        mock_search.return_value = []
        resp = client.get("/api/v1/search", params={"q": "nothing"})
        assert resp.status_code == 200
        assert resp.json()["total"] == 0

    def test_search_missing_query(self, client: TestClient):
        resp = client.get("/api/v1/search")
        assert resp.status_code == 422  # missing required query param


class TestInspect:
    @patch("modelctl_api.services.search_service.hf.inspect")
    def test_inspect_returns_repo_info(self, mock_inspect, client: TestClient):
        mock_inspect.return_value = {
            "repo_id": "test/MyModel-GGUF",
            "type": "chat",
            "description": "A test model",
            "downloads": 1000,
            "likes": 50,
            "license": "apache-2.0",
            "pipeline_tag": "text-generation",
            "library_name": "transformers",
            "gguf_files": ["model-q4.gguf", "model-q8.gguf"],
            "all_files": ["model-q4.gguf", "model-q8.gguf", "config.json", "README.md"],
            "siblings": [],
        }
        resp = client.get("/api/v1/search/inspect",
                          params={"repo_id": "test/MyModel-GGUF"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["repo_id"] == "test/MyModel-GGUF"
        assert data["type"] == "chat"
        assert len(data["gguf_files"]) == 2
        assert data["total_files"] == 4

    @patch("modelctl_api.services.search_service.hf.inspect")
    def test_inspect_returns_404(self, mock_inspect, client: TestClient):
        mock_inspect.return_value = None
        resp = client.get("/api/v1/search/inspect",
                          params={"repo_id": "test/nonexistent"})
        assert resp.status_code == 404

    def test_inspect_missing_repo_id(self, client: TestClient):
        resp = client.get("/api/v1/search/inspect")
        assert resp.status_code == 422
