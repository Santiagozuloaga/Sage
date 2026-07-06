"""
Kernel State Management

Defines the state machine states and transitions for the SAGE OS kernel.
"""

from enum import Enum
from dataclasses import dataclass
from typing import Optional
from datetime import datetime


class KernelState(Enum):
    """Kernel states following the SAGE OS v4.5 architecture."""
    BOOT = "BOOT"
    KERNEL_READY = "KERNEL_READY"
    COMMAND_MODE = "COMMAND_MODE"
    WAITING_FOR_USER_COMMAND = "WAITING_FOR_USER_COMMAND"
    COMMAND_EXECUTION = "COMMAND_EXECUTION"
    ERROR = "ERROR"
    SHUTDOWN = "SHUTDOWN"


@dataclass
class StateTransition:
    """Represents a state transition with metadata."""
    from_state: KernelState
    to_state: KernelState
    timestamp: datetime
    reason: Optional[str] = None


@dataclass
class KernelContext:
    """Runtime context maintained by the kernel."""
    current_state: KernelState
    session_id: str
    boot_time: datetime
    last_transition: Optional[StateTransition] = None
    error_count: int = 0
    command_count: int = 0

    def transition_to(self, new_state: KernelState, reason: Optional[str] = None) -> StateTransition:
        """Record a state transition."""
        transition = StateTransition(
            from_state=self.current_state,
            to_state=new_state,
            timestamp=datetime.now(),
            reason=reason
        )
        self.current_state = new_state
        self.last_transition = transition
        return transition
