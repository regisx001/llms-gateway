"""Tests for modelctl_orch.port_allocator — capability tracking for internal containers."""

from __future__ import annotations

import pytest

from modelctl_orch.port_allocator import INTERNAL_CONTAINER_PORT, PortAllocator


class TestAllocate:
    """Capability allocation — always returns the internal container port."""

    def test_allocate_chat(self):
        pa = PortAllocator()
        port = pa.allocate("chat")
        assert port == INTERNAL_CONTAINER_PORT  # 8080

    def test_allocate_embedding(self):
        pa = PortAllocator()
        port = pa.allocate("embedding")
        assert port == INTERNAL_CONTAINER_PORT

    def test_allocate_experimental(self):
        pa = PortAllocator()
        port = pa.allocate("experimental")
        assert port == INTERNAL_CONTAINER_PORT

    def test_allocate_same_capability_twice(self):
        pa = PortAllocator()
        p1 = pa.allocate("chat")
        p2 = pa.allocate("chat")
        assert p1 == p2 == INTERNAL_CONTAINER_PORT

    def test_is_active(self):
        pa = PortAllocator()
        assert not pa.is_active("chat")
        pa.allocate("chat")
        assert pa.is_active("chat")

    def test_release_by_capability(self):
        pa = PortAllocator()
        pa.allocate("chat")
        assert pa.is_active("chat")
        pa.release("chat")
        assert not pa.is_active("chat")

    def test_release_by_port_int_is_noop(self):
        pa = PortAllocator()
        pa.allocate("chat")
        pa.release(8080)  # backward compat — no-op, shouldn't crash
        assert pa.is_active("chat")  # still active

    def test_release_unknown_capability(self):
        pa = PortAllocator()
        pa.release("unknown")  # should not raise

    def test_multiple_capabilities(self):
        pa = PortAllocator()
        pa.allocate("chat")
        pa.allocate("embedding")
        assert pa.is_active("chat")
        assert pa.is_active("embedding")
        pa.release("chat")
        assert not pa.is_active("chat")
        assert pa.is_active("embedding")
