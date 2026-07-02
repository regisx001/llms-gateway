"""Tests for HuggingFace provider with mocked HTTP."""

from __future__ import annotations

from unittest.mock import patch, MagicMock

import pytest
import requests

from modelctl_core import huggingface as hf


def _mock_response(data, status=200):
    resp = MagicMock(spec=requests.Response)
    resp.status_code = status
    resp.json.return_value = data
    resp.headers = {"content-length": "1000"}
    resp.iter_content.return_value = [b"x" * 1000]
    resp.raise_for_status = MagicMock()
    return resp


class TestSearch:
    @patch("modelctl_core.huggingface.requests.get")
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

    @patch("modelctl_core.huggingface.requests.get")
    def test_search_handles_empty(self, mock_get):
        mock_get.return_value = _mock_response([])
        assert hf.search("nothing") == []

    @patch("modelctl_core.huggingface.requests.get")
    def test_search_sets_user_agent(self, mock_get):
        mock_get.return_value = _mock_response([])
        hf.search("query")
        headers = mock_get.call_args[1]["headers"]
        assert "modelctl" in headers["User-Agent"]

    @pytest.mark.skipif(not __import__("os").environ.get("HF_TOKEN"),
                        reason="HF_TOKEN not set")
    @patch("modelctl_core.huggingface.requests.get")
    def test_search_uses_token_when_set(self, mock_get):
        mock_get.return_value = _mock_response([])
        hf.search("query")
        headers = mock_get.call_args[1]["headers"]
        assert "Bearer" in headers.get("Authorization", "")


class TestInspect:
    @patch("modelctl_core.huggingface.requests.get")
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

    @patch("modelctl_core.huggingface.requests.get")
    def test_inspect_returns_none_on_404(self, mock_get):
        resp = _mock_response({"error": "Not found"}, status=404)
        resp.raise_for_status.side_effect = requests.exceptions.HTTPError(
            "404", response=resp)
        mock_get.return_value = resp
        assert hf.inspect("test/nonexistent") is None


class TestInferType:
    def test_chat(self):
        assert hf._infer_type({"pipeline_tag": "text-generation"}) == "chat"
        assert hf._infer_type({"pipeline_tag": "text2text-generation"}) == "chat"

    def test_embedding(self):
        assert hf._infer_type({"pipeline_tag": "feature-extraction"}) == "embedding"
        assert hf._infer_type({"pipeline_tag": "sentence-similarity"}) == "embedding"

    def test_vision(self):
        assert hf._infer_type({"pipeline_tag": "image-to-text"}) == "vision"
        assert hf._infer_type({"pipeline_tag": "image-classification"}) == "vision"

    def test_reranker(self):
        assert hf._infer_type({"id": "some-reranker-model"}) == "reranker"
        assert hf._infer_type({"id": "Rerank-v1"}) == "reranker"

    def test_experimental_fallback(self):
        assert hf._infer_type({"id": "unknown-model"}) == "experimental"


class TestFilterGGUF:
    def test_filters_gguf_only(self):
        siblings = [
            {"rfilename": "model.gguf"},
            {"rfilename": "config.json"},
            {"rfilename": "model-q4.gguf"},
            {"rfilename": "README.md"},
        ]
        result = hf._filter_gguf_files(siblings)
        assert result == ["model-q4.gguf", "model.gguf"]

    def test_sorts_by_quantization(self):
        siblings = [
            {"rfilename": "model-Q8.gguf"},
            {"rfilename": "model-Q2.gguf"},
            {"rfilename": "model-Q4.gguf"},
        ]
        result = hf._filter_gguf_files(siblings)
        assert result == ["model-Q2.gguf", "model-Q4.gguf", "model-Q8.gguf"]

    def test_no_gguf_files(self):
        assert hf._filter_gguf_files([{"rfilename": "config.json"}]) == []


class TestBuildModelFromRepo:
    @patch("modelctl_core.huggingface.requests.get")
    def test_build_model(self, mock_get):
        mock_get.return_value = _mock_response({
            "modelId": "test/MyModel-GGUF",
            "pipeline_tag": "text-generation",
            "downloads": 1000,
            "likes": 50,
            "library_name": "transformers",
            "cardData": {"license": "apache-2.0"},
            "siblings": [
                {"rfilename": "model.gguf"},
                {"rfilename": "config.json"},
            ],
        })
        model = hf.build_model_from_repo("test/MyModel-GGUF", "model.gguf")
        assert model.repo_id == "test/MyModel-GGUF"
        assert model.type == "chat"
        assert model.name == "MyModel-GGUF"
        assert len(model.artifacts) == 1
        assert model.artifacts[0].name == "model.gguf"

    @patch("modelctl_core.huggingface.requests.get")
    def test_build_model_with_repo_info(self, mock_get):
        info = {
            "repo_id": "test/Model",
            "type": "chat",
            "pipeline_tag": "text-generation",
            "library_name": "transformers",
            "siblings": [],
        }
        # mock won't be called since we pass repo_info
        model = hf.build_model_from_repo("test/Model", "model.gguf", repo_info=info)
        assert model.repo_id == "test/Model"
        mock_get.assert_not_called()


# ── edge-case / error-catching tests ───────────────────────────────────

class TestInferTypeEdgeCases:
    def test_feature_extraction(self):
        assert hf._infer_type({"pipeline_tag": "feature-extraction"}) == "embedding"

    def test_sentence_similarity(self):
        assert hf._infer_type({"pipeline_tag": "sentence-similarity"}) == "embedding"

    def test_image_classification(self):
        assert hf._infer_type({"pipeline_tag": "image-classification"}) == "vision"

    def test_object_detection(self):
        assert hf._infer_type({"pipeline_tag": "object-detection"}) == "vision"


class TestFilterGGUFEdgeCases:
    def test_f16_and_f32_sort_after_q(self):
        """f16 and f32 (no Q number) sort after all Q-prefixed files."""
        siblings = [
            {"rfilename": "model-f32.gguf"},
            {"rfilename": "model-f16.gguf"},
            {"rfilename": "model-Q4_K_M.gguf"},
        ]
        result = hf._filter_gguf_files(siblings)
        assert result[0] == "model-Q4_K_M.gguf"

    def test_mixed_case_extensions(self):
        """Only lowercase .gguf matches; .GGUF is filtered out (case-sensitive)."""
        siblings = [
            {"rfilename": "model.GGUF"},
            {"rfilename": "model.gguf"},
            {"rfilename": "other.txt"},
        ]
        result = hf._filter_gguf_files(siblings)
        assert result == ["model.gguf"]  # .GGUF does not match .endswith(".gguf")


class TestBuildModelFromRepoEdgeCases:
    @patch("modelctl_core.huggingface.requests.get")
    def test_build_model_from_nonexistent_repo_raises(self, mock_get):
        """When the repo doesn't exist, ValueError is raised."""
        resp = _mock_response({"error": "Not found"}, status=404)
        resp.raise_for_status.side_effect = requests.exceptions.HTTPError(
            "404", response=resp)
        mock_get.return_value = resp
        with pytest.raises(ValueError, match="not found"):
            hf.build_model_from_repo("test/nonexistent", "model.gguf")

    @patch("modelctl_core.huggingface.requests.get")
    def test_build_model_no_gguf_siblings(self, mock_get):
        """Repo with no GGUF siblings still builds correctly."""
        mock_get.return_value = _mock_response({
            "modelId": "test/TokenizerRepo",
            "pipeline_tag": "feature-extraction",
            "downloads": 0,
            "likes": 0,
            "library_name": "tokenizers",
            "cardData": {},
            "siblings": [
                {"rfilename": "tokenizer.json"},
                {"rfilename": "config.json"},
            ],
        })
        model = hf.build_model_from_repo("test/TokenizerRepo", "tokenizer.json")
        assert model.repo_id == "test/TokenizerRepo"
        assert model.artifacts[0].name == "tokenizer.json"

    @patch("modelctl_core.huggingface.requests.get")
    def test_build_model_with_explicit_type(self, mock_get):
        """Providing an explicit model_type overrides inference."""
        mock_get.return_value = _mock_response({
            "modelId": "test/SomeRepo",
            "pipeline_tag": "text-generation",
            "downloads": 0,
            "likes": 0,
            "library_name": "",
            "cardData": {},
            "siblings": [{"rfilename": "model.gguf"}],
        })
        model = hf.build_model_from_repo(
            "test/SomeRepo", "model.gguf", model_type="experimental")
        assert model.type == "experimental"


class TestSearchEdgeCases:
    @patch("modelctl_core.huggingface.requests.get")
    def test_search_with_custom_limit(self, mock_get):
        """Search should pass limit parameter."""
        mock_get.return_value = _mock_response([])
        hf.search("query", limit=5)
        url = mock_get.call_args[0][0]
        assert "limit=5" in url

    @patch("modelctl_core.huggingface.requests.get")
    def test_search_handles_http_error(self, mock_get):
        """Search should propagate HTTP errors."""
        resp = _mock_response({}, status=500)
        resp.raise_for_status.side_effect = requests.exceptions.HTTPError(
            "500", response=resp)
        mock_get.return_value = resp
        with pytest.raises(requests.exceptions.HTTPError):
            hf.search("query")


class TestInspectEdgeCases:
    @patch("modelctl_core.huggingface.requests.get")
    def test_inspect_no_siblings(self, mock_get):
        """Repo with no siblings key should not crash."""
        mock_get.return_value = _mock_response({
            "modelId": "test/BareRepo",
            "pipeline_tag": "text-generation",
            "downloads": 0,
            "likes": 0,
            "library_name": "",
            "cardData": {},
        })
        info = hf.inspect("test/BareRepo")
        assert info is not None
        assert info["gguf_files"] == []
        assert info["all_files"] == []

    @patch("modelctl_core.huggingface.requests.get")
    def test_inspect_no_card_data(self, mock_get):
        """Repo with no cardData should not crash."""
        mock_get.return_value = _mock_response({
            "modelId": "test/Bare",
            "pipeline_tag": "text-generation",
            "downloads": 0,
            "likes": 0,
            "library_name": "",
            "siblings": [],
        })
        info = hf.inspect("test/Bare")
        assert info["license"] == ""
        assert info["description"] == ""
