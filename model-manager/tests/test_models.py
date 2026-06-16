"""Tests for data models."""

from modelctl.models import Model, Artifact, Download


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
        assert m.storage_path == f"storage/embedding/{m.id}"

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
