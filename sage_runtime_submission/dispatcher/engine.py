"""
SAGE OS Task Dispatcher Engine

Command and task execution dispatcher with priority queuing.
"""

import asyncio
import logging
import uuid
from datetime import datetime
from typing import Dict, Optional, Any, Callable
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
        
        heapq.heappush(self._task_queue, (-priority_value, task.created_at.timestamp(), task))
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
        
        heapq.heappush(self._task_queue, (-priority_value, task.created_at.timestamp(), task))
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
        """Execute a command (placeholder for actual implementation)."""
        # This is a placeholder - actual implementation would route to appropriate handlers
        await asyncio.sleep(0.1)  # Simulate work
        return f"Executed: {command}"

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
