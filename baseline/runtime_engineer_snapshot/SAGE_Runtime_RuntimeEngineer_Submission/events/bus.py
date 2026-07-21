"""
SAGE OS Event Bus

System-wide event communication infrastructure for decoupled component interaction.
"""

import asyncio
import logging
import uuid
from datetime import datetime
from typing import Dict, List, Callable, Set, Optional, Tuple, Any
from collections import defaultdict, deque

from .models import Event, EventType, EventHandler


logger = logging.getLogger(__name__)


class EventBus:
    """
    Event Bus for system-wide event communication.

    Features:
    - Publish-subscribe pattern
    - Event filtering by type
    - Async event handling
    - Event history (bounded ring buffer)
    - Correlation tracking
    - Dead-letter queue for failed handlers
    """

    def __init__(self, max_history: int = 1000, max_dlq: int = 100):
        self._handlers: Dict[EventType, List[EventHandler]] = defaultdict(list)
        self._wildcard_handlers: List[EventHandler] = []
        # FIX E-10: deque gives O(1) popleft and automatic bound; previous list+pop(0) was O(n).
        self._history: deque = deque(maxlen=max_history)
        self._max_history = max_history
        # FIX DLQ-1: minimal dead-letter queue for handler failures.
        # Stores (event_dict, error_str, failed_at_iso) tuples so callers can
        # inspect / replay without holding live Event objects.
        self._dlq: deque = deque(maxlen=max_dlq)
        self._max_dlq = max_dlq
        self._running = False
        self._event_queue: Optional[asyncio.Queue] = None
        self._processor_task: Optional[asyncio.Task] = None

    async def start(self):
        """Start the event bus processor. Idempotent."""
        # FIX E-8: previously, calling start() twice silently spawned a second
        # _process_events task. Both tasks would race on the same queue, causing
        # duplicated or missing event delivery. Guard against re-entry.
        if self._running:
            logger.debug("[EVENT_BUS] start() called while already running — no-op")
            return
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
            self._processor_task = None
        # Release the queue reference so a future start() can build a fresh one.
        self._event_queue = None
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
        """Publish an event.

        FIX E-1: previously, calling publish() before start() crashed with
        AttributeError: 'NoneType' object has no attribute 'put' — a confusing
        error for callers. Now raises a clear RuntimeError so the misuse is
        immediately diagnosable.
        """
        if not self._running or self._event_queue is None:
            raise RuntimeError(
                "EventBus.publish() called before start() — event would be lost. "
                "Ensure the kernel has initialized the event bus before publishing."
            )

        event = Event(
            event_type=event_type,
            data=data,
            timestamp=datetime.now(),
            source=source,
            correlation_id=correlation_id or str(uuid.uuid4())
        )

        await self._event_queue.put(event)
        logger.debug(f"[EVENT_BUS] Published {event_type.value} from {source} (corr={event.correlation_id[:8]})")

    async def _process_events(self):
        """Process events from the queue."""
        while self._running:
            try:
                event = await asyncio.wait_for(self._event_queue.get(), timeout=0.1)
                await self._handle_event(event)
                self._add_to_history(event)
            except asyncio.TimeoutError:
                continue
            except asyncio.CancelledError:
                raise
            except Exception as e:
                logger.error(f"[EVENT_BUS] Error processing event: {e}")

    async def _handle_event(self, event: Event):
        """Handle an event by calling all subscribed handlers.

        FIX E-13 + DLQ-1: handler failures now include the event's type,
        source, and correlation_id in the log line, and the failed event is
        appended to the dead-letter queue for later inspection / replay.
        """
        # Call wildcard handlers first
        for handler in list(self._wildcard_handlers):
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(event)
                else:
                    handler(event)
            except Exception as e:
                logger.error(
                    f"[EVENT_BUS] Wildcard handler error for "
                    f"type={event.event_type.value} source={event.source} "
                    f"corr={event.correlation_id[:8]}: {e}"
                )
                self._push_dlq(event, f"wildcard: {e}")

        # Call type-specific handlers
        for handler in list(self._handlers[event.event_type]):
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(event)
                else:
                    handler(event)
            except Exception as e:
                logger.error(
                    f"[EVENT_BUS] Handler error for type={event.event_type.value} "
                    f"source={event.source} corr={event.correlation_id[:8]}: {e}"
                )
                self._push_dlq(event, f"typed: {e}")

    def _add_to_history(self, event: Event):
        """Add event to history. Bounded via deque(maxlen=...)."""
        # FIX E-10: deque handles the bound automatically — no manual pop(0) needed.
        self._history.append(event)

    def _push_dlq(self, event: Event, error: str):
        """Push a failed event onto the dead-letter queue."""
        self._dlq.append({
            'event': event.to_dict(),
            'error': error,
            'failed_at': datetime.now().isoformat()
        })

    def get_history(self, event_type: Optional[EventType] = None, limit: int = 100) -> List[Event]:
        """Get event history."""
        if event_type:
            filtered = [e for e in self._history if e.event_type == event_type]
            return list(filtered)[-limit:]
        return list(self._history)[-limit:]

    def clear_history(self):
        """Clear event history."""
        self._history.clear()
        logger.debug("[EVENT_BUS] History cleared")

    # ---- Dead-letter queue API ------------------------------------------------
    # FIX DLQ-1: minimal DLQ surface. These methods are additive — they do not
    # alter existing behavior. Cascade can wire them to a REST endpoint later
    # if desired; they are safe to leave uncalled.

    def get_dlq(self, limit: int = 100) -> List[dict]:
        """Return dead-letter entries (events whose handlers raised)."""
        return list(self._dlq)[-limit:]

    def clear_dlq(self):
        """Clear the dead-letter queue."""
        self._dlq.clear()
        logger.debug("[EVENT_BUS] DLQ cleared")

    async def replay_dlq(self) -> int:
        """Re-emit every DLQ entry through the bus and clear it on success.

        Returns the number of entries replayed. Each replay gets a fresh
        correlation_id so it can be tracked independently of the original.
        Failed replays are logged but do not block subsequent replays; they
        remain in a fresh DLQ entry if they fail again.
        """
        if not self._dlq:
            return 0
        entries = list(self._dlq)
        self._dlq.clear()
        replayed = 0
        for entry in entries:
            evt_dict = entry['event']
            try:
                evt_type = EventType(evt_dict['event_type'])
            except (KeyError, ValueError):
                logger.warning(f"[EVENT_BUS] DLQ replay skipped malformed entry: {entry}")
                continue
            try:
                await self.publish(
                    event_type=evt_type,
                    data=evt_dict.get('data', {}),
                    source=f"dlq_replay:{evt_dict.get('source', 'unknown')}",
                )
                replayed += 1
            except Exception as e:
                logger.error(f"[EVENT_BUS] DLQ replay failed for {evt_dict}: {e}")
        logger.info(f"[EVENT_BUS] DLQ replayed {replayed}/{len(entries)} entries")
        return replayed
