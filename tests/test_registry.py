"""Tests for registry persistence layer."""

from pathlib import Path

from modelctl_core import registry as reg
from modelctl_core.models import Model, Artifact, Download


class TestRegistry:
    def test_load_models_empty(self, tmp_registry_backend):
        assert reg.load_models() == []

    def test_add_and_load_model(self, tmp_registry_backend, sample_model_data):
        m = Model(**sample_model_data)
        reg.add_model(m)
        models = reg.load_models()
        assert len(models) == 1
        assert models[0].id == "test-model"
        assert models[0].status == "installed"

    def test_find_model(self, tmp_registry_backend, sample_model_data):
        reg.add_model(Model(**sample_model_data))
        m = reg.find_model("test-model")
        assert m is not None
        assert m.name == "Test Model"
        assert reg.find_model("nonexistent") is None

    def test_update_model(self, tmp_registry_backend, sample_model_data):
        reg.add_model(Model(**sample_model_data))
        ok = reg.update_model("test-model", status="active", name="Updated")
        assert ok
        m = reg.find_model("test-model")
        assert m.status == "active"
        assert m.name == "Updated"

    def test_update_nonexistent(self, tmp_registry_backend):
        assert reg.update_model("nope") is False

    def test_remove_model(self, tmp_registry_backend, sample_model_data):
        reg.add_model(Model(**sample_model_data))
        assert reg.remove_model("test-model") is True
        assert reg.find_model("test-model") is None

    def test_remove_nonexistent(self, tmp_registry_backend):
        assert reg.remove_model("nope") is False

    def test_is_registered(self, tmp_registry_backend, sample_model_data):
        reg.add_model(Model(**sample_model_data))
        assert reg.is_registered("test/test-model", "model.gguf") is True
        assert reg.is_registered("test/test-model", "other.gguf") is False
        assert reg.is_registered("other/repo", "model.gguf") is False

    def test_multiple_models(self, tmp_registry_backend):
        reg.add_model(Model(id="a", name="A"))
        reg.add_model(Model(id="b", name="B"))
        assert len(reg.load_models()) == 2

    def test_persistence_across_loads(self, tmp_registry_backend):
        reg.add_model(Model(id="persist", name="Persist"))
        # Fresh load() reads from file
        m = reg.find_model("persist")
        assert m is not None

    def test_artifact_update(self, tmp_registry_backend):
        m = Model(id="test", artifacts=[Artifact(name="old.gguf")])
        reg.add_model(m)
        reg.update_model("test", artifacts=[Artifact(name="new.gguf")])
        m = reg.find_model("test")
        assert m.artifacts[0].name == "new.gguf"

    def test_save_empty_models(self, tmp_registry_backend):
        reg.save_models([])
        assert reg.load_models() == []


class TestDownloads:
    def test_add_and_load(self, tmp_registry_backend):
        dl = Download(url="https://example.com/m.gguf",
                      destination="/tmp/m.gguf")
        reg.add_download(dl)
        dls = reg.load_downloads()
        assert len(dls) == 1
        assert dls[0].url == "https://example.com/m.gguf"
        assert dls[0].status == "pending"

    def test_update_download(self, tmp_registry_backend):
        dl = Download(url="https://example.com/m.gguf",
                      destination="/tmp/m.gguf")
        reg.add_download(dl)
        reg.update_download("https://example.com/m.gguf", status="completed",
                            downloaded_bytes=500, total_bytes=1000)
        dls = reg.load_downloads()
        assert dls[0].status == "completed"
        assert dls[0].downloaded_bytes == 500

    def test_empty_downloads(self, tmp_registry_backend):
        assert reg.load_downloads() == []


class TestActive:
    def test_load_active_empty(self, tmp_registry_backend):
        assert reg.load_active() == {"active": []}

    def test_set_active(self, tmp_registry_backend):
        reg.set_active("model-a", "chat")
        data = reg.load_active()
        assert len(data["active"]) == 1
        assert data["active"][0]["model_id"] == "model-a"
        assert data["active"][0]["type"] == "chat"

    def test_set_active_replaces_same_type(self, tmp_registry_backend):
        reg.set_active("model-a", "chat")
        reg.set_active("model-b", "chat")
        data = reg.load_active()
        assert len(data["active"]) == 1
        assert data["active"][0]["model_id"] == "model-b"

    def test_set_active_preserves_different_types(self, tmp_registry_backend):
        reg.set_active("chat-model", "chat")
        reg.set_active("emb-model", "embedding")
        data = reg.load_active()
        assert len(data["active"]) == 2

    def test_clear_active(self, tmp_registry_backend):
        reg.set_active("model-a", "chat")
        reg.clear_active("model-a")
        assert reg.load_active() == {"active": []}

    def test_clear_active_only_removes_target(self, tmp_registry_backend):
        reg.set_active("chat-model", "chat")
        reg.set_active("emb-model", "embedding")
        reg.clear_active("chat-model")
        data = reg.load_active()
        assert len(data["active"]) == 1
        assert data["active"][0]["model_id"] == "emb-model"


class TestResolveStorage:
    def test_resolve_storage(self, tmp_registry_backend):
        path = reg.resolve_storage("chat", "my-model")
        assert path.name == "my-model"
        assert path.parent.name == "chat"
