"""
Infrastructure Tests

Tests for improved ConfigManager, MemoryEngine, and TaskDispatcher.
"""

import sys
import asyncio
import tempfile
from pathlib import Path

# Add sage_runtime to path
sys.path.insert(0, str(Path(__file__).parent.parent))


async def test_config_manager():
    """Test ConfigManager improvements."""
    print("[TEST] Testing ConfigManager...")
    
    from config.manager import ConfigManager
    
    with tempfile.TemporaryDirectory() as tmpdir:
        config_dir = Path(tmpdir)
        config_mgr = ConfigManager(config_dir)
        
        # Test load/save
        await config_mgr.load()
        print("  ✓ Config loaded")
        
        # Test atomic save
        result = await config_mgr.save()
        assert result == True
        print("  ✓ Atomic save works")
        
        # Test locked keys
        result = config_mgr.set("session_id", "test")
        assert result == False
        print("  ✓ Locked keys protected")
        
        # Test merge
        config_mgr.merge({"new_key": "new_value"})
        assert config_mgr.get("new_key") == "new_value"
        print("  ✓ Merge works")
        
        # Test reset to defaults
        config_mgr.set("model", "custom-model")
        config_mgr.reset_to_defaults()
        assert config_mgr.get("model") == "claude-sonnet-4-6"
        print("  ✓ Reset to defaults works")
    
    return True


async def test_memory_engine():
    """Test MemoryEngine error handling."""
    print("\n[TEST] Testing MemoryEngine...")
    
    from memory.engine import MemoryEngine
    from memory.models import MemoryRecord, MemoryType
    from datetime import datetime
    
    # Use a non-temporary directory to avoid Windows file locking issues
    test_dir = Path(__file__).parent.parent / "test_data"
    test_dir.mkdir(exist_ok=True)
    
    db_path = test_dir / "test_infrastructure.db"
    
    # Clean up existing test database
    if db_path.exists():
        db_path.unlink()
    
    engine = MemoryEngine(db_path)
    
    await engine.initialize()
    print("  ✓ Memory engine initialized")
    
    # Test save with error handling
    record = MemoryRecord(
        id=None,
        memory_type=MemoryType.ENGINEERING_DECISION,
        title="Test Record",
        content="Test content",
        tags=["test"],
        created_at=datetime.now(),
        updated_at=datetime.now()
    )
    
    record_id = await engine.save_memory(record)
    assert record_id is not None
    print("  ✓ Save with error handling works")
    
    # Test session save
    from memory.models import SessionRecord
    session = SessionRecord(
        session_id="test_session",
        started_at=datetime.now(),
        ended_at=None,
        messages=[],
        context={}
    )
    
    result = await engine.save_session(session)
    assert result == True
    print("  ✓ Session save with error handling works")
    
    # Shutdown before cleanup
    await engine.shutdown()
    print("  ✓ Shutdown works")
    
    # Clean up test database
    if db_path.exists():
        db_path.unlink()
    
    return True


async def test_dispatcher():
    """Test TaskDispatcher improvements."""
    print("\n[TEST] Testing TaskDispatcher...")
    
    from dispatcher.engine import TaskDispatcher
    from dispatcher.models import TaskPriority
    
    dispatcher = TaskDispatcher(max_concurrent=2)
    
    await dispatcher.start()
    print("  ✓ Dispatcher started")
    
    # Test dispatch with tie-breaker
    task1 = await dispatcher.dispatch("test1", TaskPriority.HIGH)
    task2 = await dispatcher.dispatch("test2", TaskPriority.HIGH)
    
    assert task1.task_id != task2.task_id
    print("  ✓ Tie-breaker prevents duplicate task IDs")
    
    # Test graceful stop
    await dispatcher.stop()
    print("  ✓ Graceful shutdown works")
    
    return True


async def main():
    """Run all infrastructure tests."""
    print("="*70)
    print("Infrastructure Tests")
    print("="*70)
    
    tests = [
        ("ConfigManager", test_config_manager),
        ("MemoryEngine", test_memory_engine),
        ("TaskDispatcher", test_dispatcher)
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = await test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"\n✗ {test_name} raised exception: {e}")
            results.append((test_name, False))
    
    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)
    
    for test_name, result in results:
        status = "PASS" if result else "FAIL"
        print(f"{test_name}: {status}")
    
    all_passed = all(result for _, result in results)
    
    print("\n" + "="*70)
    if all_passed:
        print("✓ ALL TESTS PASSED")
        print("="*70)
        return 0
    else:
        print("✗ SOME TESTS FAILED")
        print("="*70)
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
