"""
Event Dispatcher - System event distribution and async message handling
Manages event subscriptions and notifications across the system
"""
import asyncio
from datetime import datetime
from typing import Dict, List, Callable, Any, Optional
from collections import defaultdict
import uuid

from utils.trace_logger import trace, trace_async_calls


class EventType:
    """Event type constants"""
    SYSTEM_START = "system.start"
    SYSTEM_STOP = "system.stop"
    WORKFLOW_START = "workflow.start"
    WORKFLOW_COMPLETE = "workflow.complete"
    WORKFLOW_FAIL = "workflow.fail"
    AGENT_REGISTER = "agent.register"
    AGENT_UNREGISTER = "agent.unregister"
    DATA_RECEIVED = "data.received"
    DATA_PROCESSED = "data.processed"
    ALERT_RAISED = "alert.raised"
    HEALTH_CHECK = "health.check"
    STATE_CHANGE = "state.change"


class Event:
    """Event data structure"""

    def __init__(
        self,
        event_type: str,
        payload: Dict[str, Any],
        source: str = "system",
        priority: int = 0
    ):
        self.event_id = str(uuid.uuid4())
        self.event_type = event_type
        self.payload = payload
        self.source = source
        self.priority = priority
        self.timestamp = datetime.now()
        self.processed = False


class EventDispatcher:
    """
    Manages event distribution and async message processing
    All events are traced to files for debugging
    """

    def __init__(self):
        self.subscribers: Dict[str, List[Callable]] = defaultdict(list)
        self.event_queue: asyncio.Queue = asyncio.Queue()
        self.event_history: List[Event] = []
        self.is_running = False
        self.processing_task: Optional[asyncio.Task] = None

        trace.info("EventDispatcher initialized", module=__name__, function="__init__")

    @trace_async_calls
    async def start(self):
        """Start the event dispatcher"""
        if self.is_running:
            trace.warning(
                "EventDispatcher already running",
                module=__name__,
                function="start"
            )
            return

        self.is_running = True
        self.processing_task = asyncio.create_task(self._process_events())

        trace.info("EventDispatcher started", module=__name__, function="start")

        # Emit system start event
        await self.emit(EventType.SYSTEM_START, {"started_at": datetime.now().isoformat()})

    @trace_async_calls
    async def stop(self):
        """Stop the event dispatcher"""
        if not self.is_running:
            return

        # Emit system stop event
        await self.emit(EventType.SYSTEM_STOP, {"stopped_at": datetime.now().isoformat()})

        self.is_running = False
        if self.processing_task:
            self.processing_task.cancel()
            try:
                await self.processing_task
            except asyncio.CancelledError:
                pass

        trace.info("EventDispatcher stopped", module=__name__, function="stop")

    @trace_async_calls
    async def subscribe(self, event_type: str, handler: Callable):
        """Subscribe to an event type"""
        self.subscribers[event_type].append(handler)

        trace.info(
            f"Subscription added for {event_type}",
            context={
                "event_type": event_type,
                "handler": handler.__name__,
                "total_subscribers": len(self.subscribers[event_type])
            },
            module=__name__,
            function="subscribe"
        )

    @trace_async_calls
    async def unsubscribe(self, event_type: str, handler: Callable):
        """Unsubscribe from an event type"""
        if event_type in self.subscribers and handler in self.subscribers[event_type]:
            self.subscribers[event_type].remove(handler)

            trace.info(
                f"Subscription removed for {event_type}",
                context={
                    "event_type": event_type,
                    "handler": handler.__name__
                },
                module=__name__,
                function="unsubscribe"
            )

    @trace_async_calls
    async def emit(
        self,
        event_type: str,
        payload: Dict[str, Any],
        source: str = "system",
        priority: int = 0
    ) -> str:
        """Emit an event"""

        event = Event(event_type, payload, source, priority)

        trace.debug(
            f"Event emitted: {event_type}",
            context={
                "event_id": event.event_id,
                "event_type": event_type,
                "source": source,
                "priority": priority,
                "payload": payload
            },
            module=__name__,
            function="emit"
        )

        # Add to queue
        await self.event_queue.put(event)

        # Keep history (limit to last 1000 events)
        self.event_history.append(event)
        if len(self.event_history) > 1000:
            self.event_history.pop(0)

        return event.event_id

    async def _process_events(self):
        """Process events from the queue"""
        trace.debug(
            "Event processing loop started",
            module=__name__,
            function="_process_events"
        )

        while self.is_running:
            try:
                # Get event from queue with timeout
                try:
                    event = await asyncio.wait_for(
                        self.event_queue.get(),
                        timeout=1.0
                    )
                except asyncio.TimeoutError:
                    continue

                trace.debug(
                    f"Processing event: {event.event_type}",
                    context={"event_id": event.event_id, "type": event.event_type},
                    module=__name__,
                    function="_process_events"
                )

                # Get subscribers for this event type
                handlers = self.subscribers.get(event.event_type, [])
                wildcard_handlers = self.subscribers.get("*", [])
                all_handlers = handlers + wildcard_handlers

                if not all_handlers:
                    trace.debug(
                        f"No handlers for event {event.event_type}",
                        context={"event_id": event.event_id},
                        module=__name__,
                        function="_process_events"
                    )
                    event.processed = True
                    continue

                # Call all handlers
                tasks = []
                for handler in all_handlers:
                    try:
                        if asyncio.iscoroutinefunction(handler):
                            tasks.append(handler(event))
                        else:
                            # Wrap sync handler in async
                            tasks.append(asyncio.to_thread(handler, event))
                    except Exception as e:
                        trace.error(
                            f"Error creating handler task for {event.event_type}",
                            context={
                                "event_id": event.event_id,
                                "handler": handler.__name__
                            },
                            module=__name__,
                            function="_process_events",
                            exception=e
                        )

                # Wait for all handlers to complete
                if tasks:
                    results = await asyncio.gather(*tasks, return_exceptions=True)

                    # Check for errors
                    for i, result in enumerate(results):
                        if isinstance(result, Exception):
                            trace.error(
                                f"Handler failed for event {event.event_type}",
                                context={
                                    "event_id": event.event_id,
                                    "handler_index": i
                                },
                                module=__name__,
                                function="_process_events",
                                exception=result
                            )

                event.processed = True

                trace.debug(
                    f"Event processed: {event.event_type}",
                    context={
                        "event_id": event.event_id,
                        "handlers_called": len(all_handlers)
                    },
                    module=__name__,
                    function="_process_events"
                )

            except Exception as e:
                trace.error(
                    "Error in event processing loop",
                    module=__name__,
                    function="_process_events",
                    exception=e
                )

    def get_event_history(
        self,
        event_type: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Get event history"""

        events = self.event_history
        if event_type:
            events = [e for e in events if e.event_type == event_type]

        events = events[-limit:]

        return [
            {
                "event_id": e.event_id,
                "event_type": e.event_type,
                "source": e.source,
                "timestamp": e.timestamp.isoformat(),
                "processed": e.processed,
                "payload": e.payload
            }
            for e in events
        ]

    def get_dispatcher_metrics(self) -> Dict[str, Any]:
        """Get dispatcher metrics"""
        total_events = len(self.event_history)
        processed_events = sum(1 for e in self.event_history if e.processed)
        total_subscribers = sum(len(handlers) for handlers in self.subscribers.values())

        event_type_counts = defaultdict(int)
        for event in self.event_history:
            event_type_counts[event.event_type] += 1

        return {
            "is_running": self.is_running,
            "total_events": total_events,
            "processed_events": processed_events,
            "pending_events": self.event_queue.qsize(),
            "total_subscribers": total_subscribers,
            "subscription_types": len(self.subscribers),
            "event_type_distribution": dict(event_type_counts)
        }
