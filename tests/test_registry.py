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


# ── edge-case / error-catching tests ───────────────────────────────────

class TestRegistryEdgeCases:
    def test_is_registered_with_no_models(self, tmp_registry_backend):
        """is_registered should return False cleanly when no models exist."""
        assert reg.is_registered("any/repo", "any.gguf") is False

    def test_update_model_multiple_fields(self, tmp_registry_backend):
        """Updating multiple fields at once should all stick."""
        reg.add_model(Model(id="m", name="Old", status="registered",
                            metadata={"key": "val"}))
        reg.update_model("m", name="New", status="installed",
                         metadata={"key": "updated"})
        m = reg.find_model("m")
        assert m.name == "New"
        assert m.status == "installed"
        assert m.metadata == {"key": "updated"}

    def test_find_model_with_cached_list(self, tmp_registry_backend):
        """find_model with a pre-fetched models list should not hit disk."""
        m = Model(id="x", name="X")
        reg.add_model(m)
        models = reg.load_models()
        # Add another model to disk but NOT to the cached list
        reg.add_model(Model(id="y", name="Y"))
        # find with cached list should only see x
        found = reg.find_model("x", models=models)
        assert found is not None
        found_y = reg.find_model("y", models=models)
        assert found_y is None  # y is on disk but not in the cached list

    def test_remove_then_re_add(self, tmp_registry_backend):
        """Removing a model then adding it back should work."""
        m = Model(id="z", name="Z")
        reg.add_model(m)
        assert reg.remove_model("z")
        reg.add_model(Model(id="z", name="Z-V2"))
        assert reg.find_model("z").name == "Z-V2"

    def test_save_models_overwrites_existing(self, tmp_registry_backend):
        """Saving a models list replaces whatever was there before."""
        reg.add_model(Model(id="a"))
        reg.add_model(Model(id="b"))
        reg.save_models([Model(id="c")])
        models = reg.load_models()
        assert len(models) == 1
        assert models[0].id == "c"

    def test_update_download_nonexistent_url(self, tmp_registry_backend):
        """update_download on a URL not in the list should not crash."""
        reg.update_download("http://nonexistent.com/x.gguf", status="completed")
        assert reg.load_downloads() == []

    def test_multiple_downloads_persistence(self, tmp_registry_backend):
        """Multiple downloads should all be saved and reloaded."""
        d1 = Download(url="http://a.com/1.gguf", destination="/tmp/1.gguf")
        d2 = Download(url="http://a.com/2.gguf", destination="/tmp/2.gguf")
        reg.add_download(d1)
        reg.add_download(d2)
        dls = reg.load_downloads()
        assert len(dls) == 2
        urls = {d.url for d in dls}
        assert "http://a.com/1.gguf" in urls
        assert "http://a.com/2.gguf" in urls

    def test_save_downloads_overwrites(self, tmp_registry_backend):
        """Saving downloads directly replaces the list."""
        reg.add_download(Download(url="http://a.com/old.gguf",
                                   destination="/tmp/old.gguf"))
        reg.save_downloads([Download(url="http://a.com/new.gguf",
                                      destination="/tmp/new.gguf")])
        dls = reg.load_downloads()
        assert len(dls) == 1
        assert dls[0].url == "http://a.com/new.gguf"

    def test_set_active_displaces_status(self, tmp_registry_backend):
        """When a same-type model is displaced, its status becomes 'installed'.
        The newly-activated model keeps its original status."""
        reg.add_model(Model(id="old", status="active"))
        reg.add_model(Model(id="new", status="installed"))

        reg.set_active("old", "chat")
        # Now activate 'new' — 'old' should be displaced to 'installed'
        reg.set_active("new", "chat")

        old = reg.find_model("old")
        assert old.status == "installed"
        new = reg.find_model("new")
        assert new.status == "installed"  # set_active doesn't change new model's status

    def test_set_active_same_model_twice(self, tmp_registry_backend):
        """Setting the same model active twice should not duplicate entries."""
        reg.add_model(Model(id="m", status="installed"))
        reg.set_active("m", "chat")
        reg.set_active("m", "chat")
        data = reg.load_active()
        assert len(data["active"]) == 1

    def test_clear_active_nonexistent_model(self, tmp_registry_backend):
        """clear_active on a model not in active list should not crash."""
        reg.clear_active("nonexistent")
        assert reg.load_active() == {"active": []}

    def test_model_with_installed_at_field(self, tmp_registry_backend):
        """Models with installed_at should persist correctly."""
        m = Model(id="timed", installed_at="2024-06-01T12:00:00+00:00")
        reg.add_model(m)
        found = reg.find_model("timed")
        assert found.installed_at == "2024-06-01T12:00:00+00:00"

    def test_add_model_with_full_metadata(self, tmp_registry_backend):
        """Model with rich metadata should round-trip cleanly."""
        m = Model(id="rich", name="Rich Model", type="embedding",
                  metadata={"pipeline_tag": "sentence-similarity",
                            "library_name": "sentence-transformers",
                            "tags": ["embedding", "gguf"]})
        reg.add_model(m)
        found = reg.find_model("rich")
        assert found.metadata["pipeline_tag"] == "sentence-similarity"
        assert found.metadata["library_name"] == "sentence-transformers"
        assert found.type == "embedding"
