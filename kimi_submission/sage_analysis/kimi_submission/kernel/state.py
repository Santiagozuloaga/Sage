"""
Kernel State Management

Defines the state machine states and transitions for the SAGE OS kernel.
"""

import logging
from enum import Enum
from dataclasses import dataclass
from typing import Optional, Dict, Set
from datetime import datetime


logger = logging.getLogger(__name__)


class KernelState(Enum):
    """Kernel states following the SAGE OS v4.5 architecture."""
    BOOT = "BOOT"
    KERNEL_READY = "KERNEL_READY"
    COMMAND_MODE = "COMMAND_MODE"
    WAITING_FOR_USER_COMMAND = "WAITING_FOR_USER_COMMAND"
    COMMAND_EXECUTION = "COMMAND_EXECUTION"
    ERROR = "ERROR"
    SHUTDOWN = "SHUTDOWN"


# FIX S-1: Previously KernelContext.transition_to() accepted any target
# state, so a coding mistake (e.g., transitioning from BOOT straight to
# COMMAND_EXECUTION) would silently corrupt the FSM invariant. This map
# declares the legal forward transitions; transition_to() now logs a
# WARNING on illegal transitions but does NOT raise — that keeps the fix
# non-breaking for existing callers (including any wiring Cascade adds)
# while making FSM violations visible in logs for diagnosis.
# 
# Ported from Runtime Engineer's S-1 fix and applied to the current
# codebase (which includes Claude A's _init_optional() boot pattern).
# ERROR and SHUTDOWN are reachable from any state (terminal recovery states).
_ALLOWED_TRANSITIONS: Dict[KernelState, Set[KernelState]] = {
    KernelState.BOOT: {
        KernelState.KERNEL_READY,
        KernelState.ERROR,
        KernelState.SHUTDOWN,
    },
    KernelState.KERNEL_READY: {
        KernelState.COMMAND_MODE,
        KernelState.ERROR,
        KernelState.SHUTDOWN,
    },
    KernelState.COMMAND_MODE: {
        KernelState.WAITING_FOR_USER_COMMAND,
        KernelState.ERROR,
        KernelState.SHUTDOWN,
    },
    KernelState.WAITING_FOR_USER_COMMAND: {
        KernelState.COMMAND_EXECUTION,
        KernelState.ERROR,
        KernelState.SHUTDOWN,
    },
    KernelState.COMMAND_EXECUTION: {
        KernelState.WAITING_FOR_USER_COMMAND,
        KernelState.ERROR,
        KernelState.SHUTDOWN,
    },
    KernelState.ERROR: {
        KernelState.WAITING_FOR_USER_COMMAND,  # recovery path
        KernelState.SHUTDOWN,
    },
    KernelState.SHUTDOWN: set(),  # terminal — no outgoing transitions
}


@dataclass
class StateTransition:
    """Represents a state transition with metadata."""
    from_state: KernelState
    to_state: KernelState
    timestamp: datetime
    reason: Optional[str] = None


@dataclass
class KernelContext:
    """Runtime context maintained by the kernel.

    FIX S-2: Previously the context tracked only `error_count` — there
    was no field to record *what* the last error actually was, making
    post-mortem debugging of an ERROR-state kernel essentially blind.
    `last_error` is now populated by `record_error()` and survives until
    the next error or a manual clear. The field is optional and defaults
    to None, so existing construction sites remain compatible.
    
    Ported from Runtime Engineer's S-2 fix.
    """
    current_state: KernelState
    session_id: str
    boot_time: datetime
    last_transition: Optional[StateTransition] = None
    error_count: int = 0
    command_count: int = 0
    # FIX S-2: New field for last error tracking
    last_error: Optional[str] = None

    @classmethod
    def is_valid_transition(cls, from_state: KernelState, to_state: KernelState) -> bool:
        """
        Return True if transitioning from_state -> to_state is legal.
        
        Self-transitions are allowed (idempotent re-entry into the same
        state — used by some shutdown paths).
        """
        if from_state == to_state:
            return True
        return to_state in _ALLOWED_TRANSITIONS.get(from_state, set())

    def transition_to(self, new_state: KernelState, reason: Optional[str] = None) -> StateTransition:
        """
        Record a state transition.

        FIX S-1: Logs a WARNING when the transition is not in the legal
        set per _ALLOWED_TRANSITIONS, but still performs it — this keeps
        the fix non-breaking for existing callers (including any future
        wiring Cascade adds) while making FSM violations visible in logs
        for diagnosis.
        """
        if not self.is_valid_transition(self.current_state, new_state):
            logger.warning(
                f"[KERNEL_FSM] Illegal transition {self.current_state.value} -> "
                f"{new_state.value} (reason: {reason!r}). Proceeding anyway — "
                f"this indicates a bug in the caller."
            )
        transition = StateTransition(
            from_state=self.current_state,
            to_state=new_state,
            timestamp=datetime.now(),
            reason=reason
        )
        self.current_state = new_state
        self.last_transition = transition
        return transition

    def record_error(self, error_msg: str) -> None:
        """
        Record a runtime error in the kernel context.

        FIX S-2: Populates last_error and increments error_count so the
        kernel's exception handlers can leave a breadcrumb for post-mortem
        debugging. Existing code that only reads error_count is unaffected.
        """
        self.last_error = error_msg
        self.error_count += 1

    def clear_error(self) -> None:
        """
        Clear the last_error field.
        
        Does NOT reset error_count — the historical count is preserved.
        """
        self.last_error = None
