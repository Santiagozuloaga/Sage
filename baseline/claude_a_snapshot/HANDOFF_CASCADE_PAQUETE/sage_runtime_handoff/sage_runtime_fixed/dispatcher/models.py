"""
Task data models for SAGE OS Task Dispatcher.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Dict, Any
from enum import Enum


class TaskStatus(Enum):
    """Task execution status."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TaskPriority(Enum):
    """Task priority levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class Task:
    """A task to be executed."""
    task_id: str
    command: str
    status: TaskStatus
    priority: TaskPriority
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    result: Optional[Any] = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            'task_id': self.task_id,
            'command': self.command,
            'status': self.status.value,
            'priority': self.priority.value,
            'created_at': self.created_at.isoformat(),
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'result': self.result,
            'error': self.error,
            'metadata': self.metadata or {}
        }
