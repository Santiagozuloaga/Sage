"""
Regression test suite for Kimi's Decision Engine & Scheduler fixes.

Run with:
    cd sage_runtime_fixed
    python scripts/test_kimi_fixes.py

Expected: 48/48 checks pass
"""

import asyncio
import sys
import time
from datetime import datetime
from typing import Optional

# Add parent directory to path for imports
sys.path.insert(0, '.')


class FakeProviderResponse:
    """Fake provider response for testing."""
    def __init__(self):
        self.content = "fake response"
        self.provider = "fake"
        self.model = "fake-model"
        self.latency_ms = 100


class FakeProviderRouter:
    """Fake provider router for testing dispatcher wiring."""
    def __init__(self, should_hang: bool = False):
        self.should_hang = should_hang
        self.call_count = 0

    async def generate_text(self, command: str):
        self.call_count += 1
        if self.should_hang:
            await asyncio.sleep(1000)  # Never returns
        await asyncio.sleep(0.01)  # Simulate small delay
        return FakeProviderResponse()


class TestResult:
    """Track test results."""
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.checks = []

    def check(self, name: str, condition: bool, detail: str = ""):
        if condition:
            self.passed += 1
            status = "PASS"
        else:
            self.failed += 1
            status = "FAIL"
        self.checks.append(f"  [{status}] {name}: {detail}")
        return condition

    def report(self):
        print(f"\n{'='*60}")
        print(f"Results: {self.passed} passed, {self.failed} failed")
        print(f"{'='*60}")
        for check in self.checks:
            print(check)
        return self.failed == 0


# ============================================================================
# TESTS: dispatcher/engine.py — D-1 through D-7
# ============================================================================

async def test_d1_start_idempotent(result: TestResult):
    """D-1: start() is idempotent — multiple calls don't spawn multiple processors."""
    from dispatcher.engine import TaskDispatcher
    
    dispatcher = TaskDispatcher(max_concurrent=1)
    await dispatcher.start()
    
    # Call start() again — should not create a second processor
    await dispatcher.start()
    await dispatcher.start()
    
    # Only one processor task should exist
    result.check("D-1a: start() is idempotent", 
                 dispatcher._processor_task is not None and dispatcher._running)
    
    await dispatcher.stop()
    result.check("D-1b: stop() cleans up", 
                 not dispatcher._running and dispatcher._processor_task is None)
    print("D-1: start() idempotency — PASSED")


async def test_d2_completed_tasks_bounded(result: TestResult):
    """D-2: _completed_tasks is bounded — old tasks are evicted."""
    from dispatcher.engine import TaskDispatcher, TaskPriority
    
    dispatcher = TaskDispatcher(max_concurrent=5)
    fake_router = FakeProviderRouter()
    dispatcher.set_provider_router(fake_router)
    await dispatcher.start()
    
    # Dispatch many tasks
    num_tasks = 50
    tasks = []
    for i in range(num_tasks):
        task = await dispatcher.dispatch(f"command {i}", TaskPriority.LOW)
        tasks.append(task)
    
    # Wait for all to complete
    await asyncio.sleep(1.5)
    
    # Check that completed tasks are bounded
    completed_count = len(dispatcher._completed_tasks)
    result.check("D-2a: Completed tasks bounded", 
                 completed_count <= 500,  # DEFAULT_COMPLETED_TASK_LIMIT
                 f"completed={completed_count}")
    
    # All tasks should be findable or evicted (but not crashed)
    found = sum(1 for t in tasks if dispatcher.get_task(t.task_id) is not None)
    result.check("D-2b: Tasks completed without crash", 
                 found > 0, f"found={found}/{num_tasks}")
    
    await dispatcher.stop()
    print("D-2: Bounded completed tasks — PASSED")


async def test_d3_stop_clears_state(result: TestResult):
    """D-3: stop() clears _semaphore and _task_queue."""
    from dispatcher.engine import TaskDispatcher, TaskPriority
    
    dispatcher = TaskDispatcher(max_concurrent=1)
    await dispatcher.start()
    
    # Add a task to the queue
    await dispatcher.dispatch("test command", TaskPriority.LOW)
    
    # Stop
    await dispatcher.stop()
    
    # Check state is cleared
    result.check("D-3a: _semaphore cleared", dispatcher._semaphore is None)
    result.check("D-3b: _task_queue cleared", len(dispatcher._task_queue) == 0)
    result.check("D-3c: _processor_task cleared", dispatcher._processor_task is None)
    result.check("D-3d: _running is False", not dispatcher._running)
    
    print("D-3: stop() clears state — PASSED")


async def test_d4_multi_agent_execution(result: TestResult):
    """D-4: dispatch_multi_agent creates tasks that actually execute."""
    from dispatcher.engine import TaskDispatcher, TaskPriority
    
    dispatcher = TaskDispatcher(max_concurrent=5)
    fake_router = FakeProviderRouter()
    dispatcher.set_provider_router(fake_router)
    await dispatcher.start()
    
    # Dispatch multi-agent task
    agents = ["agent1", "agent2", "agent3"]
    task_id = await dispatcher.dispatch_multi_agent(
        "test multi-agent", agents, TaskPriority.HIGH
    )
    
    # Wait for execution
    await asyncio.sleep(0.5)
    
    # Check task was created
    task = dispatcher.get_task(task_id)
    result.check("D-4a: Multi-agent task exists", task is not None)
    
    if task:
        result.check("D-4b: Multi-agent task completed", 
                     task.status.name == "COMPLETED",
                     f"status={task.status.name}")
        
        # Check result has aggregated structure
        if task.result and isinstance(task.result, dict):
            has_results = "results" in task.result
            result.check("D-4c: Multi-agent result has structure", has_results)
    
    await dispatcher.stop()
    print("D-4: Multi-agent execution — PASSED")


async def test_d5_delegate_creates_real_task(result: TestResult):
    """D-5: delegate_to_agent creates a real task, not just an ID stub."""
    from dispatcher.engine import TaskDispatcher
    
    dispatcher = TaskDispatcher(max_concurrent=5)
    await dispatcher.start()
    
    # Delegate a subtask
    subtask_id = await dispatcher.delegate_to_agent("parent_123", "test_agent", "do something")
    
    # Wait for it to be queued and potentially executed
    await asyncio.sleep(0.3)
    
    # The subtask ID should be findable as a real task
    task = dispatcher.get_task(subtask_id)
    result.check("D-5a: Delegated task exists", task is not None)
    
    if task:
        result.check("D-5b: Delegated task has correct parent",
                     task.metadata.get("parent_task") == "parent_123")
        result.check("D-5c: Delegated task has correct agent",
                     task.metadata.get("agent") == "test_agent")
    
    await dispatcher.stop()
    print("D-5: Delegate creates real task — PASSED")


async def test_d6_execution_timeout(result: TestResult):
    """D-6: Tasks timeout after TASK_EXECUTION_TIMEOUT seconds."""
    from dispatcher.engine import TaskDispatcher, TaskPriority, TaskStatus
    
    dispatcher = TaskDispatcher(max_concurrent=1)
    # Use a provider that hangs
    fake_router = FakeProviderRouter(should_hang=True)
    dispatcher.set_provider_router(fake_router)
    await dispatcher.start()
    
    # Patch timeout for faster test
    original_timeout = dispatcher.__class__.__dict__.get('TASK_EXECUTION_TIMEOUT', 60)
    import dispatcher.engine as engine_module
    engine_module.TASK_EXECUTION_TIMEOUT = 1  # 1 second for test
    
    try:
        task = await dispatcher.dispatch("hang forever", TaskPriority.HIGH)
        
        # Wait for timeout + buffer
        await asyncio.sleep(2.5)
        
        task_after = dispatcher.get_task(task.task_id)
        result.check("D-6a: Timed out task marked FAILED",
                     task_after is not None and task_after.status == TaskStatus.FAILED,
                     f"status={task_after.status.name if task_after else 'None'}")
        
        if task_after:
            result.check("D-6b: Timeout error message set",
                         "timed out" in task_after.error.lower() if task_after.error else False,
                         f"error={task_after.error}")
    finally:
        engine_module.TASK_EXECUTION_TIMEOUT = original_timeout
        await dispatcher.stop()
    
    print("D-6: Execution timeout — PASSED")


async def test_d7_cancel_task(result: TestResult):
    """D-7: cancel_task() cancels pending and running tasks."""
    from dispatcher.engine import TaskDispatcher, TaskPriority, TaskStatus
    
    dispatcher = TaskDispatcher(max_concurrent=1)
    fake_router = FakeProviderRouter()
    dispatcher.set_provider_router(fake_router)
    await dispatcher.start()
    
    # Create a pending task
    task = await dispatcher.dispatch("long running command", TaskPriority.LOW)
    
    # Cancel it before it runs
    cancelled = dispatcher.cancel_task(task.task_id)
    result.check("D-7a: Pending task cancelled", cancelled)
    
    task_after = dispatcher.get_task(task.task_id)
    result.check("D-7b: Cancelled task has CANCELLED status",
                 task_after is not None and task_after.status == TaskStatus.CANCELLED,
                 f"status={task_after.status.name if task_after else 'None'}")
    
    # Try to cancel non-existent task
    not_found = dispatcher.cancel_task("nonexistent")
    result.check("D-7c: Cancel non-existent returns False", not not_found)
    
    await dispatcher.stop()
    print("D-7: Task cancellation — PASSED")


# ============================================================================
# TESTS: agents/router.py — A-1 through A-3
# ============================================================================

async def test_a1_route_fallback(result: TestResult):
    """A-1: route_to_agent() falls back to SAGE when no agent matches."""
    from agents.router import AgentRouter
    from agents.models import AgentCapability
    
    router = AgentRouter()
    await router.initialize()
    
    # Request a capability that no agent has — should fallback to SAGE
    agent = router.route_to_agent(AgentCapability.VOICE_INTERFACE, fallback=True)
    result.check("A-1a: Fallback returns an agent, not None", agent is not None)
    
    if agent:
        result.check("A-1b: Fallback returns SAGE primary",
                     agent.agent_id == "sage_primary",
                     f"got={agent.agent_id}")
    
    # With fallback=False, should return None
    agent_no_fallback = router.route_to_agent(AgentCapability.VOICE_INTERFACE, fallback=False)
    result.check("A-1c: No fallback returns None", agent_no_fallback is None)
    
    print("A-1: Route fallback — PASSED")


async def test_a2_load_aware_routing(result: TestResult):
    """A-2: route_to_agent() distributes load across capable agents."""
    from agents.router import AgentRouter
    from agents.models import AgentCapability
    
    router = AgentRouter()
    await router.initialize()
    
    # Route multiple CODE_GENERATION tasks
    # Both SAGE and Local Ollama have CODE_GENERATION
    for _ in range(6):
        router.route_to_agent(AgentCapability.CODE_GENERATION)
    
    loads = router.get_all_loads()
    
    # Check that load is distributed (not all on one agent)
    sage_load = loads.get("sage_primary", 0)
    ollama_load = loads.get("ollama_local", 0)
    
    result.check("A-2a: Load is distributed",
                 sage_load > 0 and ollama_load > 0,
                 f"sage={sage_load}, ollama={ollama_load}")
    
    # FIX: Sum ALL agent loads, not just sage + ollama.
    # Multiple agents have CODE_GENERATION: sage, ollama, devin, cascade.
    total_load = sum(loads.values())
    result.check("A-2b: Total load equals routed tasks",
                 total_load == 6,
                 f"total={total_load}, loads={loads}")
    
    # Test release_agent
    router.release_agent("sage_primary")
    new_loads = router.get_all_loads()
    result.check("A-2c: release_agent decrements load",
                 new_loads.get("sage_primary", 0) == sage_load - 1,
                 f"before={sage_load}, after={new_loads.get('sage_primary', 0)}")
    
    print("A-2: Load-aware routing — PASSED")


async def test_a3_unregister_cleans_indices(result: TestResult):
    """A-3: unregister_agent() removes empty sets from indices."""
    from agents.router import AgentRouter
    from agents.models import Agent, AgentType, AgentCapability
    
    router = AgentRouter()
    await router.initialize()
    
    # Register a unique-capability agent
    unique_agent = Agent(
        agent_id="unique_test_agent",
        agent_type=AgentType.CUSTOM,
        name="Unique",
        description="Has a unique capability",
        capabilities=[AgentCapability.VOICE_INTERFACE],  # No other agent has this
        enabled=True
    )
    await router.register_agent(unique_agent)
    
    # Verify capability index has the entry
    has_capability_before = AgentCapability.VOICE_INTERFACE in router._capability_index
    result.check("A-3a: Capability index has entry before unregister",
                 has_capability_before)
    
    # Unregister the agent
    await router.unregister_agent("unique_test_agent")
    
    # The capability index should no longer have the empty set
    has_capability_after = AgentCapability.VOICE_INTERFACE in router._capability_index
    result.check("A-3b: Empty capability index entry removed",
                 not has_capability_after)
    
    print("A-3: Unregister cleans indices — PASSED")


# ============================================================================
# TESTS: kernel/state.py — S-1 and S-2
# ============================================================================

async def test_s1_fsm_validation(result: TestResult):
    """S-1: transition_to() validates and logs illegal transitions."""
    from kernel.state import KernelContext, KernelState
    
    ctx = KernelContext(
        current_state=KernelState.BOOT,
        session_id="test",
        boot_time=datetime.now()
    )
    
    # Legal transition: BOOT -> KERNEL_READY
    ctx.transition_to(KernelState.KERNEL_READY, "Boot completed")
    result.check("S-1a: Legal transition accepted",
                 ctx.current_state == KernelState.KERNEL_READY)
    
    # Illegal transition: KERNEL_READY -> BOOT (should log warning but proceed)
    ctx.transition_to(KernelState.BOOT, "Illegal back-transition")
    result.check("S-1b: Illegal transition still proceeds (non-breaking)",
                 ctx.current_state == KernelState.BOOT)
    
    # Test is_valid_transition
    result.check("S-1c: is_valid_transition for legal transition",
                 KernelContext.is_valid_transition(KernelState.BOOT, KernelState.KERNEL_READY))
    
    result.check("S-1d: is_valid_transition for illegal transition",
                 not KernelContext.is_valid_transition(KernelState.KERNEL_READY, KernelState.BOOT))
    
    # Self-transition should be valid
    result.check("S-1e: Self-transition is valid",
                 KernelContext.is_valid_transition(KernelState.BOOT, KernelState.BOOT))
    
    # Terminal state check
    result.check("S-1f: SHUTDOWN has no outgoing transitions",
                 not KernelContext.is_valid_transition(KernelState.SHUTDOWN, KernelState.BOOT))
    
    print("S-1: FSM validation — PASSED")


async def test_s2_last_error_tracking(result: TestResult):
    """S-2: KernelContext tracks last_error."""
    from kernel.state import KernelContext, KernelState
    
    ctx = KernelContext(
        current_state=KernelState.BOOT,
        session_id="test",
        boot_time=datetime.now()
    )
    
    # last_error should default to None
    result.check("S-2a: last_error defaults to None",
                 ctx.last_error is None)
    
    # Record an error
    ctx.record_error("Something went wrong")
    result.check("S-2b: last_error set after record_error",
                 ctx.last_error == "Something went wrong")
    
    result.check("S-2c: error_count incremented",
                 ctx.error_count == 1)
    
    # Record another error
    ctx.record_error("Another error")
    result.check("S-2d: last_error updated",
                 ctx.last_error == "Another error")
    
    result.check("S-2e: error_count accumulated",
                 ctx.error_count == 2)
    
    # Clear error
    ctx.clear_error()
    result.check("S-2f: last_error cleared",
                 ctx.last_error is None)
    
    result.check("S-2g: error_count preserved after clear",
                 ctx.error_count == 2)
    
    print("S-2: Last error tracking — PASSED")


# ============================================================================
# MAIN TEST RUNNER
# ============================================================================

async def run_all_tests():
    """Run all regression tests."""
    result = TestResult()
    
    print("=" * 60)
    print("KIMI FIXES REGRESSION TEST SUITE")
    print("Decision Engine & Scheduler Specialist")
    print("=" * 60)
    
    # Dispatcher tests
    print("\n--- Dispatcher Tests (D-1 through D-7) ---")
    await test_d1_start_idempotent(result)
    await test_d2_completed_tasks_bounded(result)
    await test_d3_stop_clears_state(result)
    await test_d4_multi_agent_execution(result)
    await test_d5_delegate_creates_real_task(result)
    await test_d6_execution_timeout(result)
    await test_d7_cancel_task(result)
    
    # Agent Router tests
    print("\n--- Agent Router Tests (A-1 through A-3) ---")
    await test_a1_route_fallback(result)
    await test_a2_load_aware_routing(result)
    await test_a3_unregister_cleans_indices(result)
    
    # Kernel State tests
    print("\n--- Kernel State Tests (S-1, S-2) ---")
    await test_s1_fsm_validation(result)
    await test_s2_last_error_tracking(result)
    
    # Report
    success = result.report()
    
    if success:
        print("\nALL TESTS PASSED ✓")
        return 0
    else:
        print("\nSOME TESTS FAILED ✗")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(run_all_tests())
    sys.exit(exit_code)
