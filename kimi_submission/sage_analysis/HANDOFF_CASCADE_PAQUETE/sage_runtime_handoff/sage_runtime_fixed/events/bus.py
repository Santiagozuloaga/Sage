"""
SAGE OS Event Bus

System-wide event communication infrastructure for decoupled component interaction.
"""

import asyncio
import logging
import uuid
from datetime import datetime
from typing import Dict, List, Callable, Set, Optional
from collections import defaultdict

from .models import Event, EventType, EventHandler


logger = logging.getLogger(__name__)


class EventBus:
    """
    Event Bus for system-wide event communication.
    
    Features:
    - Publish-subscribe pattern
    - Event filtering by type
    - Async event handling
    - Event history
    - Correlation tracking
    """

    def __init__(self, max_history: int = 1000):
        self._handlers: Dict[EventType, List[EventHandler]] = defaultdict(list)
        self._wildcard_handlers: List[EventHandler] = []
        self._history: List[Event] = []
        self._max_history = max_history
        self._running = False
        self._event_queue: Optional[asyncio.Queue] = None
        self._processor_task: Optional[asyncio.Task] = None

    async def start(self):
        """Start the event bus processor."""
        self._running = True
        self._event_queue = asyncio.Queue()
        self._processor_task = asyncio.create_task(self._process_events())
        logger.info("[EVENT_BUS] Started")

    async def stop(self):
        """Stop the event bus processor."""
        self._running = False
        if self._processor_task:
            self._processor_task.cancel()
            try:
                await self._processor_task
            except asyncio.CancelledError:
                pass
        logger.info("[EVENT_BUS] Stopped")

    def subscribe(self, event_type: EventType, handler: EventHandler):
        """Subscribe to a specific event type."""
        self._handlers[event_type].append(handler)
        logger.debug(f"[EVENT_BUS] Subscribed to {event_type.value}")

    def subscribe_wildcard(self, handler: EventHandler):
        """Subscribe to all events."""
        self._wildcard_handlers.append(handler)
        logger.debug("[EVENT_BUS] Subscribed to all events")

    def unsubscribe(self, event_type: EventType, handler: EventHandler):
        """Unsubscribe from a specific event type."""
        if handler in self._handlers[event_type]:
            self._handlers[event_type].remove(handler)
            logger.debug(f"[EVENT_BUS] Unsubscribed from {event_type.value}")

    async def publish(self, event_type: EventType, data: dict, source: str, correlation_id: Optional[str] = None):
        """Publish an event."""
        event = Event(
            event_type=event_type,
            data=data,
            timestamp=datetime.now(),
            source=source,
            correlation_id=correlation_id or str(uuid.uuid4())
        )
        
        await self._event_queue.put(event)
        logger.debug(f"[EVENT_BUS] Published {event_type.value}")

    async def _process_events(self):
        """Process events from the queue."""
        while self._running:
            try:
                event = await asyncio.wait_for(self._event_queue.get(), timeout=0.1)
                await self._handle_event(event)
                self._add_to_history(event)
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error(f"[EVENT_BUS] Error processing event: {e}")

    async def _handle_event(self, event: Event):
        """Handle an event by calling all subscribed handlers."""
        # Call wildcard handlers first
        for handler in self._wildcard_handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(event)
                else:
                    handler(event)
            except Exception as e:
                logger.error(f"[EVENT_BUS] Wildcard handler error: {e}")

        # Call type-specific handlers
        for handler in self._handlers[event.event_type]:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(event)
                else:
                    handler(event)
            except Exception as e:
                logger.error(f"[EVENT_BUS] Handler error for {event.event_type.value}: {e}")

    def _add_to_history(self, event: Event):
        """Add event to history."""
        self._history.append(event)
        if len(self._history) > self._max_history:
            self._history.pop(0)

    def get_history(self, event_type: Optional[EventType] = None, limit: int = 100) -> List[Event]:
        """Get event history."""
        if event_type:
            filtered = [e for e in self._history if e.event_type == event_type]
            return filtered[-limit:]
        return self._history[-limit:]

    def clear_history(self):
        """Clear event history."""
        self._history.clear()
        logger.debug("[EVENT_BUS] History cleared")
