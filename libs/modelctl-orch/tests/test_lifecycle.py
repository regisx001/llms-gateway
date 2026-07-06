"""Tests for modelctl_orch.lifecycle — state machine transitions."""

from __future__ import annotations

import pytest

from modelctl_orch.lifecycle import TransitionError, transition
from modelctl_orch.models import ContainerState

# ── All allowed transitions ──────────────────────────────────────────────


class TestValidTransitions:
    """Every transition listed in _ALLOWED must succeed."""

    def test_stopped_to_starting(self):
        assert transition(ContainerState.STOPPED,
                          ContainerState.STARTING) == ContainerState.STARTING

    def test_stopped_to_failed(self):
        assert transition(ContainerState.STOPPED,
                          ContainerState.FAILED) == ContainerState.FAILED

    def test_starting_to_running(self):
        assert transition(ContainerState.STARTING,
                          ContainerState.RUNNING) == ContainerState.RUNNING

    def test_starting_to_failed(self):
        assert transition(ContainerState.STARTING,
                          ContainerState.FAILED) == ContainerState.FAILED

    def test_running_to_stopping(self):
        assert transition(ContainerState.RUNNING,
                          ContainerState.STOPPING) == ContainerState.STOPPING

    def test_running_to_failed(self):
        assert transition(ContainerState.RUNNING,
                          ContainerState.FAILED) == ContainerState.FAILED

    def test_stopping_to_stopped(self):
        assert transition(ContainerState.STOPPING,
                          ContainerState.STOPPED) == ContainerState.STOPPED

    def test_stopping_to_failed(self):
        assert transition(ContainerState.STOPPING,
                          ContainerState.FAILED) == ContainerState.FAILED

    def test_failed_to_starting_retry(self):
        assert transition(ContainerState.FAILED,
                          ContainerState.STARTING) == ContainerState.STARTING


# ── All disallowed transitions ──────────────────────────────────────────


class TestInvalidTransitions:
    """Transitions not in _ALLOWED must raise TransitionError."""

    @pytest.mark.parametrize(
        "current, target",
        [
            # Can't skip STARTING
            (ContainerState.STOPPED, ContainerState.RUNNING),
            (ContainerState.STOPPED, ContainerState.STOPPING),
            # Can't go backwards
            (ContainerState.RUNNING, ContainerState.STARTING),
            (ContainerState.RUNNING, ContainerState.STOPPED),
            (ContainerState.STOPPING, ContainerState.RUNNING),
            (ContainerState.STOPPING, ContainerState.STARTING),
            (ContainerState.FAILED, ContainerState.RUNNING),
            (ContainerState.FAILED, ContainerState.STOPPING),
            (ContainerState.FAILED, ContainerState.STOPPED),
            # Already there
            (ContainerState.STOPPED, ContainerState.STOPPED),
            (ContainerState.RUNNING, ContainerState.RUNNING),
            (ContainerState.FAILED, ContainerState.FAILED),
        ],
    )
    def test_invalid_transition_raises(self, current, target):
        with pytest.raises(TransitionError) as exc:
            transition(current, target)
        assert "cannot transition" in str(exc.value).lower()

    def test_error_message_includes_states(self):
        with pytest.raises(TransitionError) as exc:
            transition(ContainerState.STOPPED, ContainerState.RUNNING)
        msg = str(exc.value)
        assert "stopped" in msg
        assert "running" in msg


# ── Round-trip: full lifecycle ──────────────────────────────────────────


class TestLifecycle:
    """End-to-end lifecycle sequence."""

    def test_full_lifecycle(self):
        state = ContainerState.STOPPED

        state = transition(state, ContainerState.STARTING)
        assert state == ContainerState.STARTING

        state = transition(state, ContainerState.RUNNING)
        assert state == ContainerState.RUNNING

        state = transition(state, ContainerState.STOPPING)
        assert state == ContainerState.STOPPING

        state = transition(state, ContainerState.STOPPED)
        assert state == ContainerState.STOPPED

    def test_crash_at_runtime(self):
        state = ContainerState.STOPPED
        state = transition(state, ContainerState.STARTING)
        state = transition(state, ContainerState.RUNNING)
        state = transition(state, ContainerState.FAILED)
        assert state == ContainerState.FAILED

    def test_startup_failure(self):
        state = ContainerState.STOPPED
        state = transition(state, ContainerState.STARTING)
        state = transition(state, ContainerState.FAILED)
        assert state == ContainerState.FAILED

    def test_retry_after_failure(self):
        state = ContainerState.FAILED
        state = transition(state, ContainerState.STARTING)
        assert state == ContainerState.STARTING
