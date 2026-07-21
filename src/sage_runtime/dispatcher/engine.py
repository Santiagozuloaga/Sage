"""
SAGE OS Task Dispatcher Engine

Command and task execution dispatcher with priority queuing.
"""

import asyncio
import logging
import uuid
import itertools
from datetime import datetime
from typing import Dict, Optional, Any, Callable, List
from collections import deque
import heapq

from .models import Task, TaskStatus, TaskPriority


logger = logging.getLogger(__name__)


class TaskDispatcher:
    """
    Task Dispatcher for command and task execution.
    
    Features:
    - Priority-based task queuing
    - Async task execution
    - Task status tracking
    - Result caching
    - Error handling
    """

    def __init__(self, max_concurrent: int = 3):
        self._max_concurrent = max_concurrent
        self._task_queue: List[tuple] = []  # Priority queue
        self._running_tasks: Dict[str, Task] = {}
        self._completed_tasks: Dict[str, Task] = {}
        self._running = False
        self._processor_task: Optional[asyncio.Task] = None
        self._semaphore: Optional[asyncio.Semaphore] = None
        # Monotonic tie-breaker for the heap. Why: heapq falls back to
        # comparing the third tuple element (the Task) whenever the first
        # two are equal. Task is a plain @dataclass with no __lt__, so two
        # tasks dispatched with the same priority at the exact same
        # timestamp crashed with "'<' not supported between instances of
        # 'Task' and 'Task'" - reproduced by forcing two same-priority
        # dispatches with a mocked identical datetime.now(). An
        # ever-increasing counter guarantees no two heap entries ever tie,
        # so the Task objects are never compared, while still preserving
        # FIFO order within the same priority level.
        self._sequence = itertools.count()
        # Wired in post-construction via set_provider_router(), not passed
        # to __init__: the kernel initializes dispatcher before
        # provider_router in its optional-component boot sequence, so the
        # provider doesn't exist yet at TaskDispatcher construction time.
        self._provider_router = None

    def set_provider_router(self, provider_router) -> None:
        """
        Wire in the provider router after both components exist.

        Deliberately NOT wiring in agent_router here too. AgentRouter's
        registered roster is almost entirely external, human-operated dev
        tools (Jules, Cascade, Devin, Cursor, ...) that this process cannot
        invoke programmatically - only "Local Ollama"/"SAGE" map onto
        anything actually callable, which is provider_router itself. There
        is also no existing logic anywhere that classifies a raw command
        string into the AgentCapability enum route_to_agent() requires.
        Both of those are real design decisions, not bugs, so they are
        reported (see engineering changelog) instead of implemented here.
        """
        self._provider_router = provider_router

    async def start(self):
        """Start the task dispatcher."""
        self._running = True
        self._semaphore = asyncio.Semaphore(self._max_concurrent)
        self._processor_task = asyncio.create_task(self._process_tasks())
        logger.info("[DISPATCHER] Started")

    async def stop(self):
        """Stop the task dispatcher."""
        self._running = False
        if self._processor_task:
            self._processor_task.cancel()
            try:
                await self._processor_task
            except asyncio.CancelledError:
                pass
        logger.info("[DISPATCHER] Stopped")

    async def dispatch(self, command: str, priority: TaskPriority = TaskPriority.MEDIUM) -> Task:
        """Dispatch a command for execution."""
        task = Task(
            task_id=str(uuid.uuid4())[:8],
            command=command,
            status=TaskStatus.PENDING,
            priority=priority,
            created_at=datetime.now()
        )
        
        # Add to priority queue (negative priority for max-heap behavior)
        priority_value = {
            TaskPriority.CRITICAL: 4,
            TaskPriority.HIGH: 3,
            TaskPriority.MEDIUM: 2,
            TaskPriority.LOW: 1
        }[priority]
        
        heapq.heappush(self._task_queue, (-priority_value, next(self._sequence), task))
        logger.info(f"[DISPATCHER] Dispatched task {task.task_id}: {command}")
        
        return task

    async def _process_tasks(self):
        """Process tasks from the queue."""
        while self._running:
            try:
                if self._task_queue:
                    _, _, task = heapq.heappop(self._task_queue)
                    asyncio.create_task(self._execute_task(task))
                else:
                    await asyncio.sleep(0.1)
            except Exception as e:
                logger.error(f"[DISPATCHER] Error processing tasks: {e}")

    async def _execute_task(self, task: Task):
        """Execute a single task."""
        async with self._semaphore:
            task.status = TaskStatus.RUNNING
            task.started_at = datetime.now()
            self._running_tasks[task.task_id] = task
            
            logger.info(f"[DISPATCHER] Executing task {task.task_id}")
            
            try:
                # Execute the command (placeholder for actual execution logic)
                result = await self._execute_command(task.command)
                
                task.status = TaskStatus.COMPLETED
                task.result = result
                task.completed_at = datetime.now()
                
                logger.info(f"[DISPATCHER] Task {task.task_id} completed")
                
            except Exception as e:
                task.status = TaskStatus.FAILED
                task.error = str(e)
                task.completed_at = datetime.now()
                
                logger.error(f"[DISPATCHER] Task {task.task_id} failed: {e}")
            
            finally:
                self._running_tasks.pop(task.task_id, None)
                self._completed_tasks[task.task_id] = task

    async def dispatch_multi_agent(
        self,
        command: str,
        agents: list[str],
        priority: TaskPriority = TaskPriority.MEDIUM
    ) -> str:
        """
        Dispatch a task to multiple agents for parallel execution.
        
        Args:
            command: Command to execute
            agents: List of agent names to execute on
            priority: Task priority
            
        Returns:
            Task ID for the multi-agent task
        """
        task = Task(
            task_id=str(uuid.uuid4())[:8],
            command=command,
            status=TaskStatus.PENDING,
            priority=priority,
            created_at=datetime.now(),
            metadata={"agents": agents, "multi_agent": True}
        )
        
        # Add to priority queue
        priority_value = {
            TaskPriority.CRITICAL: 4,
            TaskPriority.HIGH: 3,
            TaskPriority.MEDIUM: 2,
            TaskPriority.LOW: 1
        }[priority]
        
        heapq.heappush(self._task_queue, (-priority_value, next(self._sequence), task))
        logger.info(f"[DISPATCHER] Dispatched multi-agent task {task.task_id} to {len(agents)} agents")
        
        return task.task_id

    async def delegate_to_agent(
        self,
        task_id: str,
        agent_name: str,
        subtask: str
    ) -> str:
        """
        Delegate a subtask to a specific agent.
        
        Args:
            task_id: Parent task ID
            agent_name: Name of the agent
            subtask: Subtask command
            
        Returns:
            Subtask ID
        """
        subtask_id = f"{task_id}_{agent_name}_{str(uuid.uuid4())[:4]}"
        
        logger.info(f"[DISPATCHER] Delegated subtask {subtask_id} to agent {agent_name}")
        
        return subtask_id

    async def aggregate_results(
        self,
        task_id: str,
        agent_results: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Aggregate results from multiple agents.
        
        Args:
            task_id: Parent task ID
            agent_results: Dict of agent_name -> result
            
        Returns:
            Aggregated result
        """
        aggregated = {
            "task_id": task_id,
            "agent_count": len(agent_results),
            "results": agent_results,
            "summary": self._summarize_results(agent_results)
        }
        
        logger.info(f"[DISPATCHER] Aggregated {len(agent_results)} agent results for task {task_id}")
        
        return aggregated

    def _summarize_results(self, agent_results: Dict[str, Any]) -> Dict[str, Any]:
        """Generate a summary of agent results."""
        success_count = sum(1 for r in agent_results.values() if isinstance(r, dict) and r.get("success", False))
        
        return {
            "total_agents": len(agent_results),
            "successful": success_count,
            "failed": len(agent_results) - success_count,
            "success_rate": success_count / len(agent_results) if agent_results else 0
        }

    async def _execute_command(self, command: str) -> Any:
        """
        Execute a command.

        Real execution path: if a provider_router was wired in via
        set_provider_router(), the command is sent to it directly as a
        prompt via generate_text() (which already has its own
        online/auto-fallback logic between providers - see
        providers/provider_router.py). This is the minimal, unambiguous
        connection: provider_router is the only component that can
        actually produce a real response, and dispatcher's whole purpose
        is to execute commands, so *some* real call to it is required to
        move past the previous placeholder - it is not a new abstraction,
        just using the router's own existing public generate_text() method.

        What this does NOT do: assemble any system prompt, conversation
        history, or session context (no Context Manager exists anywhere in
        this codebase to build that from - confirmed by search, reported
        separately rather than invented here), and it does NOT route
        through agent_router (see set_provider_router's docstring for why).
        So this sends the raw command string as the entire prompt, nothing
        more. That's a real limitation, not hidden: results are marked with
        `"stub": False` here specifically so a caller can distinguish "ran
        for real, but with no context" from `"stub": True` ("didn't run at
        all"), rather than only having one bit of information.

        Falls back to the original placeholder behavior (stub: True) if no
        provider_router was wired in, so the dispatcher still works, in
        the same degraded sense as before, when used standalone.
        """
        if self._provider_router is not None:
            try:
                response = await self._provider_router.generate_text(command)
                return {
                    "stub": False,
                    "output": response.content,
                    "provider": response.provider,
                    "model": response.model,
                    "latency_ms": response.latency_ms,
                }
            except Exception as e:
                logger.error(f"[DISPATCHER] Real execution failed for command {command!r}: {e}")
                raise

        logger.warning(
            f"[DISPATCHER] '_execute_command' running in stub mode (no provider_router "
            f"wired in) - task not actually routed to any provider or agent: {command!r}"
        )
        await asyncio.sleep(0.1)  # Simulate work
        return {"stub": True, "output": f"Executed: {command}"}

    def get_task(self, task_id: str) -> Optional[Task]:
        """Get a task by ID."""
        return self._completed_tasks.get(task_id) or self._running_tasks.get(task_id)

    def get_running_tasks(self) -> list[Task]:
        """Get all currently running tasks."""
        return list(self._running_tasks.values())

    def get_completed_tasks(self, limit: int = 100) -> list[Task]:
        """Get completed tasks."""
        tasks = list(self._completed_tasks.values())
        tasks.sort(key=lambda t: t.completed_at or t.created_at, reverse=True)
        return tasks[:limit]

    async def shutdown(self):
        """Shutdown the dispatcher."""
        await self.stop()
        logger.info("[DISPATCHER] Shutdown complete")
