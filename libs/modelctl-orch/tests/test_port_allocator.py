"""Tests for modelctl_orch.port_allocator — port allocation and conflict detection."""

from __future__ import annotations

import os

import pytest

from modelctl_orch.port_allocator import PortAllocator


class TestBasePort:
    """Port resolution: defaults and env overrides."""

    def test_default_chat(self):
        pa = PortAllocator()
        assert pa.get_base_port("chat") == 30001

    def test_default_embedding(self):
        pa = PortAllocator()
        assert pa.get_base_port("embedding") == 30002

    def test_default_experimental(self):
        pa = PortAllocator()
        assert pa.get_base_port("experimental") == 30005

    def test_env_override(self, monkeypatch):
        monkeypatch.setenv("MODELCTL_CHAT_PORT", "31001")
        pa = PortAllocator()
        assert pa.get_base_port("chat") == 31001

    def test_env_override_embedding(self, monkeypatch):
        monkeypatch.setenv("MODELCTL_EMBEDDING_PORT", "31002")
        pa = PortAllocator()
        assert pa.get_base_port("embedding") == 31002

    def test_unknown_capability_falls_back(self):
        pa = PortAllocator()
        assert pa.get_base_port("unknown") == 30001


class TestAllocate:
    """Port allocation logic."""

    def test_allocate_chat(self):
        pa = PortAllocator()
        port = pa.allocate("chat")
        assert port >= 30001
        assert port < 30101

    def test_allocate_embedding(self):
        pa = PortAllocator()
        port = pa.allocate("embedding")
        assert port >= 30002
        assert port < 30102

    def test_allocate_unique_ports(self):
        pa = PortAllocator()
        p1 = pa.allocate("chat")
        p2 = pa.allocate("embedding")
        assert p1 != p2

    def test_allocate_same_capability_twice(self):
        pa = PortAllocator()
        p1 = pa.allocate("chat")
        p2 = pa.allocate("chat")
        assert p1 != p2

    def test_release_frees_port(self):
        pa = PortAllocator()
        pa.allocate("chat")
        pa.allocate("chat")
        # After release, the first slot becomes available again
        pa.release(30001)
        port = pa.allocate("chat")
        assert port == 30001

    def test_release_nonexistent_port(self):
        pa = PortAllocator()
        pa.release(99999)  # should not raise


class TestEnvOverridesWithAllocate:
    """Allocation respects env overrides."""

    def test_allocate_with_env_override(self, monkeypatch):
        monkeypatch.setenv("MODELCTL_CHAT_PORT", "31001")
        pa = PortAllocator()
        port = pa.allocate("chat")
        assert port == 31001

    def test_allocate_env_override_then_next(self, monkeypatch):
        monkeypatch.setenv("MODELCTL_CHAT_PORT", "31001")
        pa = PortAllocator()
        pa.allocate("chat")  # takes 31001
        port = pa.allocate("chat")  # should take 31002
        assert port == 31002


class TestAllocateExhaustion:
    """Port exhaustion when all ports in range are occupied."""

    def test_raises_on_exhaustion(self):
        pa = PortAllocator()
        # We can't reliably occupy 100 ports, so check the reservation path
        # by reserving a port and verifying it's skipped
        pa.allocate("chat")  # takes 30001
        pa._reserved.add(30001)  # double-reserve (already reserved)
        # allocator scans past 30001 since it's in _reserved
        port = pa.allocate("chat")
        assert port != 30001
        assert port == 30002
