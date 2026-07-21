"""
PR-009 Validation Script

Validates the Provider Layer implementation without requiring API keys.
Checks architecture, interfaces, and integration.
"""

import sys
import asyncio
from pathlib import Path

# Add sage_runtime to path
sys.path.insert(0, str(Path(__file__).parent.parent))


def test_imports():
    """Test that all provider modules can be imported."""
    print("[VALIDATION] Testing imports...")
    
    try:
        from providers.base_provider import BaseProvider, ProviderResponse, ProviderConfig, ProviderStatus
        print("  ✓ base_provider imported")
    except Exception as e:
        print(f"  ✗ base_provider import failed: {e}")
        return False
    
    try:
        from providers.gemini_provider import GeminiProvider
        print("  ✓ gemini_provider imported")
    except Exception as e:
        print(f"  ✗ gemini_provider import failed: {e}")
        return False
    
    try:
        from providers.grok_provider import GrokProvider
        print("  ✓ grok_provider imported")
    except Exception as e:
        print(f"  ✗ grok_provider import failed: {e}")
        return False
    
    try:
        from providers.provider_router import ProviderRouter, ProviderSelection
        print("  ✓ provider_router imported")
    except Exception as e:
        print(f"  ✗ provider_router import failed: {e}")
        return False
    
    try:
        from config.provider_config import ProviderConfig as ProviderConfigManager
        print("  ✓ provider_config imported")
    except Exception as e:
        print(f"  ✗ provider_config import failed: {e}")
        return False
    
    return True


def test_base_provider_interface():
    """Test that BaseProvider has required abstract methods."""
    print("\n[VALIDATION] Testing BaseProvider interface...")
    
    from providers.base_provider import BaseProvider
    import inspect
    
    required_methods = [
        'generate_text',
        'chat',
        'analyze_image',
        'health_check',
        'list_models',
        'provider_name'
    ]
    
    for method in required_methods:
        if hasattr(BaseProvider, method):
            print(f"  ✓ {method} exists")
        else:
            print(f"  ✗ {method} missing")
            return False
    
    return True


def test_provider_router():
    """Test ProviderRouter initialization and methods."""
    print("\n[VALIDATION] Testing ProviderRouter...")
    
    from providers.provider_router import ProviderRouter
    
    try:
        router = ProviderRouter(default_provider="grok")
        print("  ✓ ProviderRouter instantiated")
    except Exception as e:
        print(f"  ✗ ProviderRouter instantiation failed: {e}")
        return False
    
    # Check methods
    required_methods = [
        'initialize',
        'get_provider',
        'get_available_providers',
        'select_provider',
        'generate_text',
        'chat',
        'analyze_image',
        'get_health_status'
    ]
    
    for method in required_methods:
        if hasattr(router, method):
            print(f"  ✓ {method} exists")
        else:
            print(f"  ✗ {method} missing")
            return False
    
    return True


def test_kernel_integration():
    """Test that Kernel can initialize ProviderRouter."""
    print("\n[VALIDATION] Testing Kernel integration...")
    
    try:
        from kernel.core import SageKernel
        from pathlib import Path
        import tempfile
        
        # Create temporary config directory
        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir)
            
            # Initialize kernel
            kernel = SageKernel(config_dir=config_dir)
            print("  ✓ Kernel instantiated")
            
            # Check if _init_provider_router exists
            if hasattr(kernel, '_init_provider_router'):
                print("  ✓ _init_provider_router method exists")
            else:
                print("  ✗ _init_provider_router method missing")
                return False
            
    except Exception as e:
        print(f"  ✗ Kernel integration test failed: {e}")
        return False
    
    return True


def test_web_api_endpoints():
    """Test that web server has provider endpoints."""
    print("\n[VALIDATION] Testing Web API endpoints...")
    
    try:
        from web.server import WebServer
        import inspect
        
        # Check if the route setup includes provider endpoints
        # We can't easily test this without running the server,
        # but we can check the file was modified
        server_file = Path(__file__).parent.parent / "web" / "server.py"
        content = server_file.read_text()
        
        if "/api/providers" in content:
            print("  ✓ /api/providers endpoint exists")
        else:
            print("  ✗ /api/providers endpoint missing")
            return False
        
        if "/api/chat" in content:
            print("  ✓ /api/chat endpoint exists")
        else:
            print("  ✗ /api/chat endpoint missing")
            return False
        
        if "provider_router" in content:
            print("  ✓ provider_router integration exists")
        else:
            print("  ✗ provider_router integration missing")
            return False
        
    except Exception as e:
        print(f"  ✗ Web API test failed: {e}")
        return False
    
    return True


def test_requirements():
    """Test that requirements.txt includes provider dependencies."""
    print("\n[VALIDATION] Testing requirements.txt...")
    
    requirements_file = Path(__file__).parent.parent / "requirements.txt"
    content = requirements_file.read_text()
    
    if "openai" in content:
        print("  ✓ openai dependency present")
    else:
        print("  ✗ openai dependency missing")
        return False
    
    if "google-generativeai" in content:
        print("  ✓ google-generativeai dependency present")
    else:
        print("  ✗ google-generativeai dependency missing")
        return False
    
    return True


def test_architecture_compliance():
    """Test that architecture is not modified."""
    print("\n[VALIDATION] Testing architecture compliance...")
    
    # Check that existing modules are not modified
    # We'll check that the kernel still has all expected components
    
    try:
        from kernel.core import SageKernel
        from pathlib import Path
        import tempfile
        
        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir)
            kernel = SageKernel(config_dir=config_dir)
            
            # Check expected initialization methods exist
            expected_inits = [
                '_init_config',
                '_init_memory',
                '_init_event_bus',
                '_init_agent_router',
                '_init_task_dispatcher',
                '_init_auditor',
                '_init_provider_router'  # New addition
            ]
            
            for method in expected_inits:
                if hasattr(kernel, method):
                    print(f"  ✓ {method} exists")
                else:
                    print(f"  ✗ {method} missing")
                    return False
            
    except Exception as e:
        print(f"  ✗ Architecture compliance test failed: {e}")
        return False
    
    return True


def main():
    """Run all validation tests."""
    print("="*70)
    print("PR-009 Provider Layer Validation")
    print("="*70)
    
    tests = [
        ("Imports", test_imports),
        ("BaseProvider Interface", test_base_provider_interface),
        ("ProviderRouter", test_provider_router),
        ("Kernel Integration", test_kernel_integration),
        ("Web API Endpoints", test_web_api_endpoints),
        ("Requirements", test_requirements),
        ("Architecture Compliance", test_architecture_compliance)
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
        print("✓ ALL TESTS PASSED - PR-009 VALIDATED")
        print("="*70)
        return 0
    else:
        print("✗ SOME TESTS FAILED - PR-009 NOT VALIDATED")
        print("="*70)
        return 1


if __name__ == "__main__":
    sys.exit(main())
