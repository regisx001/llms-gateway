"""Tests for HuggingFace provider with mocked HTTP."""

from __future__ import annotations

from unittest.mock import patch, MagicMock

import pytest
import requests

from modelctl import huggingface as hf


def _mock_response(data, status=200):
    resp = MagicMock(spec=requests.Response)
    resp.status_code = status
    resp.json.return_value = data
    resp.headers = {"content-length": "1000"}
    resp.iter_content.return_value = [b"x" * 1000]
    resp.raise_for_status = MagicMock()
    return resp


class TestSearch:
    @patch("modelctl.huggingface.requests.get")
    def test_search_returns_results(self, mock_get):
        mock_get.return_value = _mock_response([
            {
                "modelId": "test/MyModel-GGUF",
                "pipeline_tag": "text-generation",
                "downloads": 5000,
                "likes": 100,
                "tags": ["transformers", "gguf"],
                "cardData": {"license": "mit"},
            },
        ])
        results = hf.search("mymodel")
        assert len(results) == 1
        assert results[0]["repo_id"] == "test/MyModel-GGUF"
        assert results[0]["type"] == "chat"
        assert results[0]["downloads"] == 5000

    @patch("modelctl.huggingface.requests.get")
    def test_search_handles_empty(self, mock_get):
        mock_get.return_value = _mock_response([])
        assert hf.search("nothing") == []

    @patch("modelctl.huggingface.requests.get")
    def test_search_sets_user_agent(self, mock_get):
        mock_get.return_value = _mock_response([])
        hf.search("query")
        headers = mock_get.call_args[1]["headers"]
        assert "modelctl" in headers["User-Agent"]

    @pytest.mark.skipif(not __import__("os").environ.get("HF_TOKEN"),
                        reason="HF_TOKEN not set")
    @patch("modelctl.huggingface.requests.get")
    def test_search_uses_token_when_set(self, mock_get):
        mock_get.return_value = _mock_response([])
        hf.search("query")
        headers = mock_get.call_args[1]["headers"]
        assert "Bearer" in headers.get("Authorization", "")


class TestInspect:
    @patch("modelctl.huggingface.requests.get")
    def test_inspect_returns_repo_info(self, mock_get):
        mock_get.return_value = _mock_response({
            "modelId": "test/MyModel-GGUF",
            "pipeline_tag": "text-generation",
            "downloads": 1000,
            "likes": 50,
            "library_name": "transformers",
            "cardData": {"license": "apache-2.0", "description": "A model"},
            "siblings": [
                {"rfilename": "model-q4.gguf"},
                {"rfilename": "model-q8.gguf"},
                {"rfilename": "config.json"},
                {"rfilename": "README.md"},
            ],
        })
        info = hf.inspect("test/MyModel-GGUF")
        assert info is not None
        assert info["repo_id"] == "test/MyModel-GGUF"
        assert info["type"] == "chat"
        assert len(info["gguf_files"]) == 2
        assert "model-q4.gguf" in info["gguf_files"]

    @patch("modelctl.huggingface.requests.get")
    def test_inspect_returns_none_on_404(self, mock_get):
        resp = _mock_response({"error": "Not found"}, status=404)
        resp.raise_for_status.side_effect = requests.exceptions.HTTPError(
            "404", response=resp)
        mock_get.return_value = resp
        assert hf.inspect("test/nonexistent") is None


class TestInferType:
    def test_chat(self):
        assert hf._infer_type({"pipeline_tag": "text-generation"}) == "chat"
        assert hf._infer_type(
            {"pipeline_tag": "text2text-generation"}) == "chat"

    def test_embedding(self):
        assert hf._infer_type(
            {"pipeline_tag": "feature-extraction"}) == "embedding"
        assert hf._infer_type(
            {"pipeline_tag": "sentence-similarity"}) == "embedding"

    def test_vision(self):
        assert hf._infer_type({"pipeline_tag": "image-to-text"}) == "vision"
        assert hf._infer_type(
            {"pipeline_tag": "image-classification"}) == "vision"

    def test_reranker(self):
        assert hf._infer_type({"id": "cohere/rerank-v2"}) == "reranker"

    def test_experimental_fallback(self):
        assert hf._infer_type(
            {"pipeline_tag": "unknown-tag"}) == "experimental"


class TestFilterGGUFFiles:
    def test_filters_and_sorts(self):
        siblings = [
            {"rfilename": "README.md"},
            {"rfilename": "model-Q8_0.gguf"},
            {"rfilename": "model-Q2_K.gguf"},
            {"rfilename": "config.json"},
            {"rfilename": "model-Q4_K_M.gguf"},
        ]
        result = hf._filter_gguf_files(siblings)
        # Sorted by quantization number: Q2 < Q4 < Q8
        assert result == ["model-Q2_K.gguf",
                          "model-Q4_K_M.gguf", "model-Q8_0.gguf"]

    def test_empty(self):
        assert hf._filter_gguf_files([{"rfilename": "README.md"}]) == []


class TestBuildModelFromRepo:
    @patch("modelctl.huggingface.requests.get")
    def test_build_model(self, mock_get):
        mock_get.return_value = _mock_response({
            "modelId": "test/MyModel-GGUF",
            "pipeline_tag": "text-generation",
            "downloads": 100,
            "likes": 10,
            "library_name": "transformers",
            "cardData": {},
            "siblings": [{"rfilename": "model.gguf"}, {"rfilename": "config.json"}],
        })
        model = hf.build_model_from_repo("test/MyModel-GGUF", "model.gguf")
        assert model.repo_id == "test/MyModel-GGUF"
        assert model.name == "MyModel-GGUF"
        assert model.type == "chat"
        assert model.provider == "huggingface"
        assert model.artifacts[0].name == "model.gguf"
