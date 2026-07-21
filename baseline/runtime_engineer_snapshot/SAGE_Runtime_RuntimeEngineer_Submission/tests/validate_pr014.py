"""
PR-014 Validation Script

Validates the Multi-Agent Execution implementation.
"""

import sys
import asyncio
from pathlib import Path

# Add sage_runtime to path
sys.path.insert(0, str(Path(__file__).parent.parent))


def test_dispatcher_methods():
    """Test that TaskDispatcher has multi-agent methods."""
    print("[VALIDATION] Testing TaskDispatcher multi-agent methods...")
    
    from dispatcher.engine import TaskDispatcher
    
    try:
        dispatcher = TaskDispatcher()
        print("  ✓ TaskDispatcher instantiated")
    except Exception as e:
        print(f"  ✗ TaskDispatcher instantiation failed: {e}")
        return False
    
    # Check multi-agent methods
    required_methods = [
        'dispatch_multi_agent',
        'delegate_to_agent',
        'aggregate_results',
        '_summarize_results'
    ]
    
    for method in required_methods:
        if hasattr(dispatcher, method):
            print(f"  ✓ {method} exists")
        else:
            print(f"  ✗ {method} missing")
            return False
    
    return True


def test_multi_agent_dispatch():
    """Test multi-agent dispatch functionality."""
    print("\n[VALIDATION] Testing multi-agent dispatch...")
    
    from dispatcher.engine import TaskDispatcher
    from dispatcher.models import TaskPriority
    
    try:
        dispatcher = TaskDispatcher()
        
        # Test dispatch
        task_id = asyncio.run(dispatcher.dispatch_multi_agent(
            command="test command",
            agents=["agent1", "agent2"],
            priority=TaskPriority.MEDIUM
        ))
        
        if task_id:
            print(f"  ✓ Multi-agent dispatch returned task_id: {task_id}")
        else:
            print("  ✗ Multi-agent dispatch returned None")
            return False
        
    except Exception as e:
        print(f"  ✗ Multi-agent dispatch failed: {e}")
        return False
    
    return True


def test_agent_delegation():
    """Test agent delegation functionality."""
    print("\n[VALIDATION] Testing agent delegation...")
    
    from dispatcher.engine import TaskDispatcher
    
    try:
        dispatcher = TaskDispatcher()
        
        # Test delegation
        subtask_id = asyncio.run(dispatcher.delegate_to_agent(
            task_id="parent_task",
            agent_name="test_agent",
            subtask="test subtask"
        ))
        
        if subtask_id:
            print(f"  ✓ Agent delegation returned subtask_id: {subtask_id}")
        else:
            print("  ✗ Agent delegation returned None")
            return False
        
    except Exception as e:
        print(f"  ✗ Agent delegation failed: {e}")
        return False
    
    return True


def test_result_aggregation():
    """Test result aggregation functionality."""
    print("\n[VALIDATION] Testing result aggregation...")
    
    from dispatcher.engine import TaskDispatcher
    
    try:
        dispatcher = TaskDispatcher()
        
        # Test aggregation
        agent_results = {
            "agent1": {"success": True, "data": "result1"},
            "agent2": {"success": False, "error": "error"},
            "agent3": {"success": True, "data": "result3"}
        }
        
        aggregated = asyncio.run(dispatcher.aggregate_results(
            task_id="test_task",
            agent_results=agent_results
        ))
        
        if aggregated and "summary" in aggregated:
            print(f"  ✓ Result aggregation returned summary: {aggregated['summary']}")
        else:
            print("  ✗ Result aggregation missing summary")
            return False
        
    except Exception as e:
        print(f"  ✗ Result aggregation failed: {e}")
        return False
    
    return True


def test_web_api_endpoints():
    """Test that web server has multi-agent endpoint."""
    print("\n[VALIDATION] Testing Web API endpoints...")
    
    try:
        server_file = Path(__file__).parent.parent / "web" / "server.py"
        content = server_file.read_text()
        
        if "/api/agents/multi" in content:
            print("  ✓ /api/agents/multi endpoint exists")
        else:
            print("  ✗ /api/agents/multi endpoint missing")
            return False
        
        if "dispatch_multi_agent" in content:
            print("  ✓ dispatch_multi_agent integration exists")
        else:
            print("  ✗ dispatch_multi_agent integration missing")
            return False
        
    except Exception as e:
        print(f"  ✗ Web API test failed: {e}")
        return False
    
    return True


def main():
    """Run all validation tests."""
    print("="*70)
    print("PR-014 Multi-Agent Execution Validation")
    print("="*70)
    
    tests = [
        ("Dispatcher Methods", test_dispatcher_methods),
        ("Multi-Agent Dispatch", test_multi_agent_dispatch),
        ("Agent Delegation", test_agent_delegation),
        ("Result Aggregation", test_result_aggregation),
        ("Web API Endpoints", test_web_api_endpoints)
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"\n✗ {test_name} raised exception: {e}")
            results.append((test_name, False))
    
    print("\n" + "="*70)
    print("VALIDATION SUMMARY")
    print("="*70)
    
    for test_name, result in results:
        status = "PASS" if result else "FAIL"
        print(f"{test_name}: {status}")
    
    all_passed = all(result for _, result in results)
    
    print("\n" + "="*70)
    if all_passed:
        print("✓ ALL TESTS PASSED - PR-014 VALIDATED")
        print("="*70)
        return 0
    else:
        print("✗ SOME TESTS FAILED - PR-014 NOT VALIDATED")
        print("="*70)
        return 1


if __name__ == "__main__":
    sys.exit(main())
