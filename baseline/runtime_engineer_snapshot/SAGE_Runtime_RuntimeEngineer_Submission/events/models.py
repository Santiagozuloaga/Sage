"""
Event data models for SAGE OS Event Bus.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Callable, Optional, Union, Awaitable
from enum import Enum


class EventType(Enum):
    """System event types."""
    BOOT = "boot"
    SHUTDOWN = "shutdown"
    COMMAND_RECEIVED = "command_received"
    COMMAND_EXECUTED = "command_executed"
    COMMAND_FAILED = "command_failed"
    STATE_CHANGED = "state_changed"
    MEMORY_SAVED = "memory_saved"
    MEMORY_LOADED = "memory_loaded"
    AGENT_SPAWNED = "agent_spawned"
    AGENT_COMPLETED = "agent_completed"
    ERROR = "error"
    CHECKPOINT = "checkpoint"
    PR_CREATED = "pr_created"
    PR_UPDATED = "pr_updated"
    RFC_SUBMITTED = "rfc_submitted"


@dataclass
class Event:
    """A system event."""
    event_type: EventType
    data: dict
    timestamp: datetime
    source: str
    correlation_id: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            'event_type': self.event_type.value,
            'data': self.data,
            'timestamp': self.timestamp.isoformat(),
            'source': self.source,
            'correlation_id': self.correlation_id
        }


# FIX E-14: the original `Callable[[Event], None]` was wrong — the bus
# explicitly supports async handlers (it checks `iscoroutinefunction` and
# awaits them). The correct type is "sync returning None OR async returning
# Awaitable[None]". This keeps static analyzers and IDE hints accurate
# without changing runtime behavior.
EventHandler = Callable[[Event], Optional[Awaitable[None]]]
