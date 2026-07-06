"""
SAGE OS Command Mode Executor

Command mode execution and management.
"""

import asyncio
import logging
from typing import Dict, Any, Optional, Callable
from datetime import datetime


logger = logging.getLogger(__name__)


class CommandMode:
    """
    Command Mode for SAGE OS.
    
    Manages command execution, command history,
    and command mode state.
    """

    def __init__(self):
        self._active = False
        self._command_history: list = []
        self._command_handlers: Dict[str, Callable] = {}
        self._initialized = False

    async def initialize(self):
        """Initialize command mode."""
        self._active = True
        self._initialized = True
        await self._register_default_handlers()
        logger.info("[COMMAND_MODE] Initialized")

    async def _register_default_handlers(self):
        """Register default command handlers."""
        # Placeholder for default command handlers
        pass

    async def execute(self, command: str, context: Optional[Dict[str, Any]] = None) -> Any:
        """Execute a command in command mode."""
        if not self._active:
            logger.warning("[COMMAND_MODE] Not active")
            return None
        
        # Add to history
        self._command_history.append({
            'command': command,
            'timestamp': datetime.now().isoformat(),
            'context': context or {}
        })
        
        logger.info(f"[COMMAND_MODE] Executing: {command}")
        
        # Check for registered handlers
        for prefix, handler in self._command_handlers.items():
            if command.startswith(prefix):
                try:
                    result = await handler(command, context)
                    return result
                except Exception as e:
                    logger.error(f"[COMMAND_MODE] Handler error: {e}")
                    return f"Error: {e}"
        
        # Default execution
        return await self._default_execute(command, context)

    async def _default_execute(self, command: str, context: Optional[Dict[str, Any]]) -> str:
        """Default command execution."""
        # Placeholder for actual command execution logic
        await asyncio.sleep(0.01)
        return f"Executed: {command}"

    def register_handler(self, prefix: str, handler: Callable):
        """Register a command handler for a specific prefix."""
        self._command_handlers[prefix] = handler
        logger.debug(f"[COMMAND_MODE] Registered handler for: {prefix}")

    def unregister_handler(self, prefix: str):
        """Unregister a command handler."""
        if prefix in self._command_handlers:
            del self._command_handlers[prefix]
            logger.debug(f"[COMMAND_MODE] Unregistered handler for: {prefix}")

    def get_history(self, limit: int = 100) -> list:
        """Get command history."""
        return self._command_history[-limit:]

    def clear_history(self):
        """Clear command history."""
        self._command_history.clear()
        logger.debug("[COMMAND_MODE] History cleared")

    async def activate(self):
        """Activate command mode."""
        self._active = True
        logger.info("[COMMAND_MODE] Activated")

    async def deactivate(self):
        """Deactivate command mode."""
        self._active = False
        logger.info("[COMMAND_MODE] Deactivated")

    @property
    def is_active(self) -> bool:
        """Check if command mode is active."""
        return self._active

    async def shutdown(self):
        """Shutdown command mode."""
        self._active = False
        self._initialized = False
        logger.info("[COMMAND_MODE] Shutdown complete")
