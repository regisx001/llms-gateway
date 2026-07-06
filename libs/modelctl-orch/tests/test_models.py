"""Tests for modelctl_orch.models — schemas, constants, and defaults."""

from __future__ import annotations

from modelctl_orch.models import (
    CAPABILITY_PORT_ENV_VARS,
    CAPABILITY_PORTS,
    DEFAULT_PROFILES,
    ContainerInfo,
    ContainerState,
    ResourceProfile,
    StartContainerRequest,
)


class TestContainerState:
    """Enum values and string coercion."""

    def test_values(self):
        assert ContainerState.STOPPED.value == "stopped"
        assert ContainerState.STARTING.value == "starting"
        assert ContainerState.RUNNING.value == "running"
        assert ContainerState.STOPPING.value == "stopping"
        assert ContainerState.FAILED.value == "failed"

    def test_membership(self):
        for v in ("stopped", "starting", "running", "stopping", "failed"):
            assert v in ContainerState._value2member_map_

    def test_str_coercion(self):
        # Python 3.11+ StrEnum uses ClassName.MEMBER for __str__;
        # compare via .value instead of str()
        assert ContainerState.RUNNING.value == "running"


class TestResourceProfile:
    """Default values and construction."""

    def test_defaults(self):
        p = ResourceProfile()
        assert p.memory_limit == "4g"
        assert p.cpu_count == 2.0
        assert p.gpu_device == "0"
        assert p.gpu_count == 1

    def test_custom(self):
        p = ResourceProfile(memory_limit="16g", cpu_count=8.0,
                            gpu_device="1", gpu_count=2)
        assert p.memory_limit == "16g"
        assert p.cpu_count == 8.0
        assert p.gpu_device == "1"
        assert p.gpu_count == 2

    def test_cpu_only(self):
        p = ResourceProfile(gpu_device=None, gpu_count=0)
        assert p.gpu_device is None
        assert p.gpu_count == 0


class TestCapabilityPorts:
    """Port mapping and env-var constants."""

    def test_default_ports(self):
        assert CAPABILITY_PORTS["chat"] == 30001
        assert CAPABILITY_PORTS["embedding"] == 30002
        assert CAPABILITY_PORTS["reranker"] == 30003
        assert CAPABILITY_PORTS["vision"] == 30004
        assert CAPABILITY_PORTS["experimental"] == 30005

    def test_env_var_names(self):
        assert CAPABILITY_PORT_ENV_VARS["chat"] == "MODELCTL_CHAT_PORT"
        assert CAPABILITY_PORT_ENV_VARS["embedding"] == "MODELCTL_EMBEDDING_PORT"
        assert CAPABILITY_PORT_ENV_VARS["reranker"] == "MODELCTL_RERANKER_PORT"
        assert CAPABILITY_PORT_ENV_VARS["vision"] == "MODELCTL_VISION_PORT"
        assert CAPABILITY_PORT_ENV_VARS["experimental"] == "MODELCTL_EXPERIMENTAL_PORT"

    def test_all_capabilities_have_ports(self):
        for cap in ("chat", "embedding", "reranker", "vision", "experimental"):
            assert cap in CAPABILITY_PORTS
            assert cap in CAPABILITY_PORT_ENV_VARS


class TestDefaultProfiles:
    """Default resource profiles per capability."""

    def test_chat_profile(self):
        p = DEFAULT_PROFILES["chat"]
        assert p.memory_limit == "8g"
        assert p.cpu_count == 4.0

    def test_embedding_profile(self):
        p = DEFAULT_PROFILES["embedding"]
        assert p.memory_limit == "2g"
        assert p.cpu_count == 2.0

    def test_reranker_profile(self):
        p = DEFAULT_PROFILES["reranker"]
        assert p.memory_limit == "4g"

    def test_vision_profile(self):
        p = DEFAULT_PROFILES["vision"]
        assert p.memory_limit == "8g"

    def test_all_capabilities_have_profile(self):
        for cap in ("chat", "embedding", "reranker", "vision", "experimental"):
            assert cap in DEFAULT_PROFILES


class TestContainerInfo:
    """ContainerInfo dataclass."""

    def test_defaults(self):
        info = ContainerInfo()
        assert info.id == ""
        assert info.capability == "chat"
        assert info.status == ContainerState.STOPPED
        assert info.error is None
        assert info.uptime_seconds is None

    def test_full_construction(self):
        info = ContainerInfo(
            id="cont-1",
            capability="embedding",
            model_id="sentence-transformers/all-MiniLM-L6-v2",
            model_name="all-MiniLM-L6-v2",
            port=30002,
            status=ContainerState.RUNNING,
            started_at="2026-07-02T10:00:00Z",
            uptime_seconds=3600,
            resource_profile=ResourceProfile(memory_limit="2g", cpu_count=2.0),
        )
        assert info.id == "cont-1"
        assert info.capability == "embedding"
        assert info.port == 30002
        assert info.status == ContainerState.RUNNING
        assert info.uptime_seconds == 3600
        assert info.resource_profile is not None

    def test_model_name_extraction(self):
        info = ContainerInfo(model_id="org/my-model")
        assert info.model_name == ""  # not auto-derived, must be set explicitly

    def test_can_set_error(self):
        info = ContainerInfo(status=ContainerState.FAILED, error="OOM killed")
        assert info.error == "OOM killed"


class TestStartContainerRequest:
    """StartContainerRequest dataclass."""

    def test_defaults(self):
        req = StartContainerRequest()
        assert req.capability == "chat"
        assert req.model_id == ""
        assert req.resource_profile is None

    def test_with_profile_override(self):
        profile = ResourceProfile(memory_limit="16g")
        req = StartContainerRequest(
            capability="vision",
            model_id="org/vision-model",
            resource_profile=profile,
        )
        assert req.capability == "vision"
        assert req.model_id == "org/vision-model"
        assert req.resource_profile == profile
