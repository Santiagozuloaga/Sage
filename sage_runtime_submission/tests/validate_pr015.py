"""
PR-015 Validation Script

Validates the Mission Dashboard implementation.
"""

import sys
import asyncio
from pathlib import Path

# Add sage_runtime to path
sys.path.insert(0, str(Path(__file__).parent.parent))


def test_dashboard_models():
    """Test that dashboard models are available."""
    print("[VALIDATION] Testing dashboard models...")
    
    try:
        from dashboard.models import AgentStatus, AgentInfo, MissionInfo
        print("  ✓ AgentStatus imported")
        print("  ✓ AgentInfo imported")
        print("  ✓ MissionInfo imported")
    except Exception as e:
        print(f"  ✗ Dashboard models import failed: {e}")
        return False
    
    return True


def test_dashboard_monitor():
    """Test DashboardMonitor has new methods."""
    print("\n[VALIDATION] Testing DashboardMonitor...")
    
    from dashboard.monitor import DashboardMonitor
    
    try:
        monitor = DashboardMonitor()
        print("  ✓ DashboardMonitor instantiated")
    except Exception as e:
        print(f"  ✗ DashboardMonitor instantiation failed: {e}")
        return False
    
    # Check new methods
    required_methods = [
        'update_agent_status',
        'set_current_mission',
        'update_mission_progress',
        'get_agent_statuses'
    ]
    
    for method in required_methods:
        if hasattr(monitor, method):
            print(f"  ✓ {method} exists")
        else:
            print(f"  ✗ {method} missing")
            return False
    
    return True


def test_agent_status_update():
    """Test agent status update functionality."""
    print("\n[VALIDATION] Testing agent status update...")
    
    from dashboard.monitor import DashboardMonitor
    from dashboard.models import AgentStatus
    
    try:
        monitor = DashboardMonitor()
        asyncio.run(monitor.initialize())
        
        # Test agent status update
        monitor.update_agent_status(
            name="test_agent",
            status=AgentStatus.BUSY,
            current_task="test_task",
            tasks_completed=5
        )
        
        agent_statuses = monitor.get_agent_statuses()
        
        if len(agent_statuses) > 0:
            print(f"  ✓ Agent status updated: {agent_statuses[0]['name']} - {agent_statuses[0]['status']}")
        else:
            print("  ✗ No agent statuses returned")
            return False
        
    except Exception as e:
        print(f"  ✗ Agent status update failed: {e}")
        return False
    
    return True


def test_mission_tracking():
    """Test mission tracking functionality."""
    print("\n[VALIDATION] Testing mission tracking...")
    
    from dashboard.monitor import DashboardMonitor
    
    try:
        monitor = DashboardMonitor()
        asyncio.run(monitor.initialize())
        
        # Test mission setting
        monitor.set_current_mission(
            mission_id="mission_001",
            name="Test Mission",
            status="in_progress",
            progress=50.0,
            current_pr="PR-015"
        )
        
        status = monitor.get_system_status()
        
        if status.current_mission:
            print(f"  ✓ Mission set: {status.current_mission['name']} ({status.current_mission['progress']}%)")
        else:
            print("  ✗ No current mission set")
            return False
        
    except Exception as e:
        print(f"  ✗ Mission tracking failed: {e}")
        return False
    
    return True


def test_system_status():
    """Test that SystemStatus includes agent and mission data."""
    print("\n[VALIDATION] Testing SystemStatus...")
    
    from dashboard.monitor import DashboardMonitor
    from dashboard.models import AgentStatus
    
    try:
        monitor = DashboardMonitor()
        asyncio.run(monitor.initialize())
        
        # Add some data
        monitor.update_agent_status("agent1", AgentStatus.IDLE)
        monitor.set_current_mission("m1", "Mission 1", "active", 25.0)
        
        status = monitor.get_system_status()
        
        if "agent_statuses" in status.to_dict():
            print(f"  ✓ SystemStatus includes agent_statuses")
        else:
            print("  ✗ SystemStatus missing agent_statuses")
            return False
        
        if "current_mission" in status.to_dict():
            print(f"  ✓ SystemStatus includes current_mission")
        else:
            print("  ✗ SystemStatus missing current_mission")
            return False
        
    except Exception as e:
        print(f"  ✗ SystemStatus test failed: {e}")
        return False
    
    return True


def test_kernel_integration():
    """Test that Kernel can initialize Dashboard."""
    print("\n[VALIDATION] Testing Kernel integration...")
    
    try:
        from kernel.core import SageKernel
        from pathlib import Path
        import tempfile
        
        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir)
            kernel = SageKernel(config_dir=config_dir)
            print("  ✓ Kernel instantiated")
            
            if hasattr(kernel, '_init_dashboard'):
                print("  ✓ _init_dashboard method exists")
            else:
                print("  ✗ _init_dashboard method missing")
                return False
            
    except Exception as e:
        print(f"  ✗ Kernel integration test failed: {e}")
        return False
    
    return True


def test_web_api_endpoints():
    """Test that web server has dashboard endpoints."""
    print("\n[VALIDATION] Testing Web API endpoints...")
    
    try:
        server_file = Path(__file__).parent.parent / "web" / "server.py"
        content = server_file.read_text()
        
        if "/api/dashboard/status" in content:
            print("  ✓ /api/dashboard/status endpoint exists")
        else:
            print("  ✗ /api/dashboard/status endpoint missing")
            return False
        
        if "/api/dashboard/mission" in content:
            print("  ✓ /api/dashboard/mission endpoint exists")
        else:
            print("  ✗ /api/dashboard/mission endpoint missing")
            return False
        
        if "/api/dashboard/agent" in content:
            print("  ✓ /api/dashboard/agent endpoint exists")
        else:
            print("  ✗ /api/dashboard/agent endpoint missing")
            return False
        
    except Exception as e:
        print(f"  ✗ Web API test failed: {e}")
        return False
    
    return True


def main():
    """Run all validation tests."""
    print("="*70)
    print("PR-015 Mission Dashboard Validation")
    print("="*70)
    
    tests = [
        ("Dashboard Models", test_dashboard_models),
        ("Dashboard Monitor", test_dashboard_monitor),
        ("Agent Status Update", test_agent_status_update),
        ("Mission Tracking", test_mission_tracking),
        ("SystemStatus", test_system_status),
        ("Kernel Integration", test_kernel_integration),
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
        print("✓ ALL TESTS PASSED - PR-015 VALIDATED")
        print("="*70)
        return 0
    else:
        print("✗ SOME TESTS FAILED - PR-015 NOT VALIDATED")
        print("="*70)
        return 1


if __name__ == "__main__":
    sys.exit(main())
