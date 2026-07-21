"""
SAGE OS Dashboard Monitor

System monitoring and dashboard data collection.
"""

import asyncio
import logging
import psutil
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

from .models import SystemStatus, ComponentStatus


logger = logging.getLogger(__name__)


class DashboardMonitor:
    """
    Dashboard Monitor for SAGE OS.
    
    Collects system metrics, component statuses,
    and provides dashboard data.
    """

    def __init__(self):
        self._start_time: Optional[datetime] = None
        self._component_statuses: Dict[str, ComponentStatus] = {}
        self._task_stats = {'active': 0, 'completed': 0}
        self._error_count = 0
        self._last_checkpoint: Optional[datetime] = None

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
            memory_usage_mb=memory_usage
        )

    async def shutdown(self):
        """Shutdown the monitor."""
        logger.info("[DASHBOARD] Monitor shutdown")
