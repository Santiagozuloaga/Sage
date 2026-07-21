"""
Dashboard data models for SAGE OS Dashboard.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Any, Optional
from enum import Enum


class ComponentStatus(Enum):
    """Component status."""
    RUNNING = "running"
    STOPPED = "stopped"
    ERROR = "error"
    INITIALIZING = "initializing"


@dataclass
class SystemStatus:
    """Overall system status."""
    uptime_seconds: float
    kernel_state: str
    component_statuses: Dict[str, str]
    active_tasks: int
    completed_tasks: int
    error_count: int
    last_checkpoint: Optional[datetime]
    memory_usage_mb: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            'uptime_seconds': self.uptime_seconds,
            'kernel_state': self.kernel_state,
            'component_statuses': self.component_statuses,
            'active_tasks': self.active_tasks,
            'completed_tasks': self.completed_tasks,
            'error_count': self.error_count,
            'last_checkpoint': self.last_checkpoint.isoformat() if self.last_checkpoint else None,
            'memory_usage_mb': self.memory_usage_mb
        }
