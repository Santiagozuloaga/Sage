"""
SAGE OS Mission Control

Mission control and system orchestration.
"""

import logging
from collections import deque
from datetime import datetime
from typing import Dict, Any, Optional, List


logger = logging.getLogger(__name__)


# FIX M-5: previously _mission_history was an unbounded list. A long-running
# kernel would accumulate mission records indefinitely (memory leak). Using a
# bounded deque caps memory usage while preserving the most recent history.
DEFAULT_MISSION_HISTORY_LIMIT = 100


class MissionControl:
    """
    Mission Control for SAGE OS.

    Coordinates high-level system operations,
    manages mission objectives, and provides
    system-level orchestration.
    """

    def __init__(self, history_limit: int = DEFAULT_MISSION_HISTORY_LIMIT):
        self._initialized = False
        self._active_missions: Dict[str, Dict[str, Any]] = {}
        self._mission_history: deque = deque(maxlen=history_limit)
        self._history_limit = history_limit

    async def initialize(self):
        """Initialize mission control."""
        self._initialized = True
        logger.info("[MISSION_CONTROL] Initialized")

    async def start_mission(self, mission_id: str, objective: str, parameters: Dict[str, Any]) -> bool:
        """Start a new mission.

        FIX M-1: previously start_time was set to None — the mission record
        claimed it never started. Callers could not compute mission duration
        or sort missions by start time. Now records the actual start time
        as ISO-8601.
        """
        if mission_id in self._active_missions:
            logger.warning(f"[MISSION_CONTROL] Mission already active: {mission_id}")
            return False

        now_iso = datetime.now().isoformat()
        mission = {
            'mission_id': mission_id,
            'objective': objective,
            'parameters': parameters,
            'status': 'active',
            'start_time': now_iso,
            'end_time': None,
            'duration_seconds': None,
            'result': None,
        }

        self._active_missions[mission_id] = mission
        logger.info(f"[MISSION_CONTROL] Started mission: {mission_id} - {objective}")
        return True

    async def complete_mission(self, mission_id: str, result: Any) -> bool:
        """Complete a mission.

        FIX M-2: previously end_time was never set — the completed mission
        record had start_time (after M-1 fix) but no end_time, so duration
        was uncomputable. Now records end_time and computes duration_seconds
        from the stored start_time.
        """
        if mission_id not in self._active_missions:
            return False

        mission = self._active_missions.pop(mission_id)
        now = datetime.now()
        mission['status'] = 'completed'
        mission['result'] = result
        mission['end_time'] = now.isoformat()

        # Compute duration if start_time was recorded (defensive against
        # missions created before the M-1 fix).
        if mission.get('start_time'):
            try:
                start_dt = datetime.fromisoformat(mission['start_time'])
                mission['duration_seconds'] = (now - start_dt).total_seconds()
            except (ValueError, TypeError):
                logger.warning(
                    f"[MISSION_CONTROL] Could not parse start_time for "
                    f"mission {mission_id}: {mission.get('start_time')!r}"
                )

        self._mission_history.append(mission)
        logger.info(f"[MISSION_CONTROL] Completed mission: {mission_id}")
        return True

    def get_active_missions(self) -> list:
        """Get all active missions."""
        return list(self._active_missions.values())

    def get_mission_history(self, limit: int = 50) -> list:
        """Get mission history (most recent first)."""
        # deque does not support slicing with negative step cleanly; convert
        # to list and reverse so callers get newest-first as before.
        history = list(self._mission_history)
        history.reverse()
        return history[:limit]

    async def shutdown(self):
        """Shutdown mission control."""
        self._initialized = False
        logger.info("[MISSION_CONTROL] Shutdown complete")
