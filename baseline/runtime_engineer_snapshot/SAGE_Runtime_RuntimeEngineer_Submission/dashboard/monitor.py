"""
SAGE OS Dashboard Monitor

System monitoring and dashboard data collection.
"""

import asyncio
import logging
import psutil
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List

from .models import SystemStatus, ComponentStatus, AgentInfo, AgentStatus, MissionInfo


logger = logging.getLogger(__name__)


class DashboardMonitor:
    """
    Dashboard Monitor for SAGE OS.
    
    Collects system metrics, component statuses,
    agent statuses, mission tracking, and provides dashboard data.
    """

    def __init__(self):
        self._start_time: Optional[datetime] = None
        self._component_statuses: Dict[str, ComponentStatus] = {}
        self._task_stats = {'active': 0, 'completed': 0}
        self._error_count = 0
        self._last_checkpoint: Optional[datetime] = None
        self._agent_infos: Dict[str, AgentInfo] = {}
        self._current_mission: Optional[MissionInfo] = None

    async def initialize(self):
        """Initialize the monitor."""
        self._start_time = datetime.now()
        logger.info("[DASHBOARD] Monitor initialized")

    def set_component_status(self, component: str, status: ComponentStatus):
        """Set component status."""
        self._component_statuses[component] = status
        logger.debug(f"[DASHBOARD] {component}: {status.value}")

    def update_task_stats(self, active: int, completed: int):
        """Update task statistics."""
        self._task_stats = {'active': active, 'completed': completed}

    def increment_error_count(self):
        """Increment error counter."""
        self._error_count += 1

    def record_checkpoint(self):
        """Record a checkpoint event."""
        self._last_checkpoint = datetime.now()

    def update_agent_status(
        self,
        name: str,
        status: AgentStatus,
        current_task: Optional[str] = None,
        tasks_completed: int = 0
    ):
        """Update agent status."""
        if name not in self._agent_infos:
            self._agent_infos[name] = AgentInfo(
                name=name,
                status=status,
                current_task=current_task,
                tasks_completed=tasks_completed,
                last_active=datetime.now()
            )
        else:
            agent = self._agent_infos[name]
            agent.status = status
            agent.current_task = current_task
            agent.tasks_completed = tasks_completed
            agent.last_active = datetime.now()
        
        logger.debug(f"[DASHBOARD] Agent {name}: {status.value}")

    def set_current_mission(
        self,
        mission_id: str,
        name: str,
        status: str,
        progress: float,
        current_pr: Optional[str] = None
    ):
        """Set current mission information."""
        self._current_mission = MissionInfo(
            mission_id=mission_id,
            name=name,
            status=status,
            progress=progress,
            current_pr=current_pr,
            started_at=datetime.now(),
            estimated_completion=None
        )
        logger.info(f"[DASHBOARD] Mission set: {name} ({progress}%)")

    def update_mission_progress(self, progress: float, current_pr: Optional[str] = None):
        """Update current mission progress."""
        if self._current_mission:
            self._current_mission.progress = progress
            if current_pr:
                self._current_mission.current_pr = current_pr

    def get_agent_statuses(self) -> List[Dict[str, Any]]:
        """Get all agent statuses as dict."""
        return [agent.to_dict() for agent in self._agent_infos.values()]

    def get_system_status(self) -> SystemStatus:
        """Get current system status."""
        uptime = (datetime.now() - self._start_time).total_seconds() if self._start_time else 0
        
        component_statuses_dict = {
            name: status.value for name, status in self._component_statuses.items()
        }
        
        memory_usage = psutil.Process().memory_info().rss / 1024 / 1024  # MB
        
        return SystemStatus(
            uptime_seconds=uptime,
            kernel_state="RUNNING",
            component_statuses=component_statuses_dict,
            active_tasks=self._task_stats['active'],
            completed_tasks=self._task_stats['completed'],
            error_count=self._error_count,
            last_checkpoint=self._last_checkpoint,
            memory_usage_mb=memory_usage,
            agent_statuses=self.get_agent_statuses(),
            current_mission=self._current_mission.to_dict() if self._current_mission else None
        )

    async def shutdown(self):
        """Shutdown the monitor."""
        logger.info("[DASHBOARD] Monitor shutdown")
