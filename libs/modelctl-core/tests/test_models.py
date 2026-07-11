"""Tests for data models."""

from modelctl_core.models import Model, Artifact, Download


class TestArtifact:
    def test_minimal(self):
        a = Artifact(name="model.gguf")
        assert a.name == "model.gguf"
        assert a.role == "primary"
        assert a.path == "files/model.gguf"  # auto-derived
        assert a.file_type == "gguf"
        assert a.size == 0

    def test_custom_path(self):
        a = Artifact(name="model.gguf", path="sub/dir/model.gguf")
        assert a.path == "sub/dir/model.gguf"

    def test_custom_role(self):
        a = Artifact(name="tokenizer.json",
                     role="tokenizer", file_type="config")
        assert a.role == "tokenizer"
        assert a.file_type == "config"


class TestDownload:
    def test_minimal(self):
        d = Download(url="https://example.com/model.gguf",
                     destination="/tmp/model.gguf")
        assert d.status == "pending"
        assert d.error is None

    def test_to_dict_omits_none(self):
        d = Download(url="u", destination="d", status="completed")
        result = d.to_dict()
        assert "error" not in result
        assert "started_at" not in result
        assert "completed_at" not in result
        assert result["url"] == "u"
        assert result["status"] == "completed"

    def test_to_dict_includes_set_fields(self):
        d = Download(url="u", destination="d", total_bytes=100,
                     downloaded_bytes=50, status="downloading",
                     started_at="2024-01-01T00:00:00Z")
        result = d.to_dict()
        assert result["total_bytes"] == 100
        assert result["downloaded_bytes"] == 50
        assert result["started_at"] == "2024-01-01T00:00:00Z"


class TestModel:
    def test_minimal(self):
        m = Model()
        assert m.status == "registered"
        assert m.provider == "huggingface"
        assert m.type == "chat"

    def test_auto_id_from_name(self):
        m = Model(name="My Test Model")
        assert m.id.startswith("my-test-model-")
        assert len(m.id) > len("my-test-model-")

    def test_auto_storage_path(self):
        m = Model(name="X", type="embedding")
        assert m.storage_path == f"embedding/{m.id}"

    def test_explicit_id(self):
        m = Model(id="my-custom-id")
        assert m.id == "my-custom-id"

    def test_artifacts_from_dicts(self):
        m = Model(artifacts=[{"name": "w.gguf"}, {"name": "t.json"}])
        assert len(m.artifacts) == 2
        assert isinstance(m.artifacts[0], Artifact)
        assert m.artifacts[0].name == "w.gguf"

    def test_to_dict(self):
        m = Model(id="x", name="X", type="chat",
                  artifacts=[Artifact(name="w.gguf")])
        d = m.to_dict()
        assert d["id"] == "x"
        assert isinstance(d["artifacts"], list)
        assert d["artifacts"][0]["name"] == "w.gguf"

    def test_status_lifecycle(self):
        m = Model(id="test")
        assert m.status == "registered"
        m.status = "downloading"
        assert m.status == "downloading"
        m.status = "installed"
        assert m.status == "installed"

    def test_long_name_truncated_id(self):
        """Names longer than 64 chars produce a truncated id prefix."""
        long_name = "A" * 80 + " Model"
        m = Model(name=long_name)
        # The id prefix is lowercased name, capped at 64 chars
        assert len(m.id) <= 64 + 13  # prefix max 64 + '-' + 12-char uuid
        assert m.id.startswith("a" * 56)  # "aaaa...a-model" → truncated

    def test_empty_name_no_auto_id(self):
        """Model with empty name gets empty id (auto-id requires non-empty name)."""
        m = Model(name="")
        assert m.id == ""  # __post_init__ only generates id when name is non-empty

    def test_all_model_types(self):
        """All MODEL_TYPES values should be accepted."""
        for t in ("chat", "embedding", "reranker", "vision", "experimental", "tool-calling"):
            m = Model(id="x", type=t)
            assert m.type == t

    def test_artifact_all_fields(self):
        """Artifact with all fields explicitly set."""
        a = Artifact(name="model.gguf", role="primary",
                     path="sub/model.gguf", size=12345,
                     file_type="gguf", sha256="abcdef1234567890")
        assert a.name == "model.gguf"
        assert a.role == "primary"
        assert a.size == 12345
        assert a.sha256 == "abcdef1234567890"

    def test_artifact_minimal_fields(self):
        """Artifact with only name — defaults should be sane."""
        a = Artifact(name="x.gguf")
        assert a.role == "primary"
        assert a.path == "files/x.gguf"
        assert a.file_type == "gguf"
        assert a.size == 0
        assert a.sha256 == ""

    def test_download_with_error(self):
        """Download with error field."""
        d = Download(url="u", destination="d", status="failed",
                     error="Connection reset")
        result = d.to_dict()
        assert result["status"] == "failed"
        assert result["error"] == "Connection reset"

    def test_download_with_all_timestamps(self):
        """Download with both started_at and completed_at."""
        d = Download(url="u", destination="d", status="completed",
                     started_at="2024-01-01T00:00:00Z",
                     completed_at="2024-01-01T01:00:00Z")
        result = d.to_dict()
        assert result["started_at"] == "2024-01-01T00:00:00Z"
        assert result["completed_at"] == "2024-01-01T01:00:00Z"

    def test_model_to_dict_includes_metadata(self):
        """to_dict should include the metadata dict."""
        m = Model(id="x", metadata={"a": 1, "b": [2, 3]})
        d = m.to_dict()
        assert d["metadata"] == {"a": 1, "b": [2, 3]}

    def test_model_with_multiple_artifacts(self):
        """Model with multiple artifacts should serialize all of them."""
        m = Model(id="m", artifacts=[
            Artifact(name="model.gguf"),
            Artifact(name="tokenizer.json",
                     role="tokenizer", file_type="config"),
            Artifact(name="README.md", role="documentation",
                     file_type="documentation"),
        ])
        d = m.to_dict()
        assert len(d["artifacts"]) == 3
        assert d["artifacts"][1]["role"] == "tokenizer"

    def test_model_explicit_storage_path_respected(self):
        """If storage_path is provided, it should not be overwritten."""
        m = Model(id="x", name="X", storage_path="custom/path/x")
        assert m.storage_path == "custom/path/x"

    def test_model_artifacts_already_instantiated(self):
        """When artifacts are already Artifact instances, they stay as-is."""
        m = Model(id="x", artifacts=[Artifact(
            name="a.gguf"), Artifact(name="b.gguf")])
        assert len(m.artifacts) == 2
        assert all(isinstance(a, Artifact) for a in m.artifacts)
