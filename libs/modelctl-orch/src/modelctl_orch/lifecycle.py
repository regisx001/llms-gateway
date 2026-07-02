"""State machine for container lifecycle transitions.

``stopped → starting → running → stopping → stopped``
Each transition is validated; invalid moves raise ``TransitionError``.
"""

from __future__ import annotations

from modelctl_orch.models import ContainerState

# Valid transitions: (from, to)
_ALLOWED: set[tuple[ContainerState, ContainerState]] = {
    (ContainerState.STOPPED, ContainerState.STARTING),
    (ContainerState.STARTING, ContainerState.RUNNING),
    (ContainerState.STARTING, ContainerState.FAILED),
    (ContainerState.RUNNING, ContainerState.STOPPING),
    (ContainerState.RUNNING, ContainerState.FAILED),
    (ContainerState.STOPPING, ContainerState.STOPPED),
    (ContainerState.STOPPING, ContainerState.FAILED),
    (ContainerState.FAILED, ContainerState.STARTING),  # retry
    (ContainerState.STOPPED, ContainerState.FAILED),   # immediate fail
}


class TransitionError(Exception):
    """Raised when a state transition is not allowed."""


def transition(current: ContainerState, target: ContainerState) -> ContainerState:
    """Validate and apply *target* transition from *current*.

    Returns the new state on success.
    Raises ``TransitionError`` if the transition is not permitted.
    """
    if (current, target) not in _ALLOWED:
        raise TransitionError(
            f"cannot transition from {current.value!r} to {target.value!r}"
        )
    return target
