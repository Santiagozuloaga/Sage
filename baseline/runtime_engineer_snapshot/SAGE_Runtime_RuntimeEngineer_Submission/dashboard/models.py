"""
Dashboard data models for SAGE OS Dashboard.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Any, Optional, List
from enum import Enum


class ComponentStatus(Enum):
    """Component status."""
    RUNNING = "running"
    STOPPED = "stopped"
    ERROR = "error"
    INITIALIZING = "initializing"


class AgentStatus(Enum):
    """Agent status."""
    IDLE = "idle"
    BUSY = "busy"
    ERROR = "error"
    DISABLED = "disabled"


@dataclass
class AgentInfo:
    """Agent information."""
    name: str
    status: AgentStatus
    current_task: Optional[str]
    tasks_completed: int
    last_active: datetime

    def to_dict(self) -> Dict[str, Any]:
        return {
            'name': self.name,
            'status': self.status.value,
            'current_task': self.current_task,
            'tasks_completed': self.tasks_completed,
            'last_active': self.last_active.isoformat()
        }


@dataclass
class MissionInfo:
    """Mission tracking information."""
    mission_id: str
    name: str
    status: str
    progress: float
    current_pr: Optional[str]
    started_at: datetime
    estimated_completion: Optional[datetime]

    def to_dict(self) -> Dict[str, Any]:
        return {
            'mission_id': self.mission_id,
            'name': self.name,
            'status': self.status,
            'progress': self.progress,
            'current_pr': self.current_pr,
            'started_at': self.started_at.isoformat(),
            'estimated_completion': self.estimated_completion.isoformat() if self.estimated_completion else None
        }


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
    agent_statuses: List[Dict[str, Any]]
    current_mission: Optional[Dict[str, Any]]

    def to_dict(self) -> Dict[str, Any]:
        return {
            'uptime_seconds': self.uptime_seconds,
            'kernel_state': self.kernel_state,
            'component_statuses': self.component_statuses,
            'active_tasks': self.active_tasks,
            'completed_tasks': self.completed_tasks,
            'error_count': self.error_count,
            'last_checkpoint': self.last_checkpoint.isoformat() if self.last_checkpoint else None,
            'memory_usage_mb': self.memory_usage_mb,
            'agent_statuses': self.agent_statuses,
            'current_mission': self.current_mission
        }
