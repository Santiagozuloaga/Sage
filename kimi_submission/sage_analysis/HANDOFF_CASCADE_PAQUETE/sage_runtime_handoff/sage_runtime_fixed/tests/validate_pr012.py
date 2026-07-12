"""
PR-012 Validation Script

Validates the Engineering Auditor implementation.
"""

import sys
import asyncio
from pathlib import Path

# Add sage_runtime to path
sys.path.insert(0, str(Path(__file__).parent.parent))


def test_imports():
    """Test that auditor modules can be imported."""
    print("[VALIDATION] Testing imports...")
    
    try:
        from auditor.engine import IntegrityAuditor
        print("  ✓ IntegrityAuditor imported")
    except Exception as e:
        print(f"  ✗ IntegrityAuditor import failed: {e}")
        return False
    
    try:
        from auditor.models import AuditReport, AuditIssue, AuditSeverity
        print("  ✓ auditor models imported")
    except Exception as e:
        print(f"  ✗ auditor models import failed: {e}")
        return False
    
    return True


def test_auditor_methods():
    """Test that IntegrityAuditor has required methods."""
    print("\n[VALIDATION] Testing IntegrityAuditor methods...")
    
    from auditor.engine import IntegrityAuditor
    
    try:
        auditor = IntegrityAuditor()
        print("  ✓ IntegrityAuditor instantiated")
    except Exception as e:
        print(f"  ✗ IntegrityAuditor instantiation failed: {e}")
        return False
    
    # Check methods
    required_methods = [
        'initialize',
        'run_full_audit',
        'audit_code_quality',
        'audit_security',
        'audit_dependencies',
        'audit_architecture',
        'audit_with_llm',
        'get_audit_history'
    ]
    
    for method in required_methods:
        if hasattr(auditor, method):
            print(f"  ✓ {method} exists")
        else:
            print(f"  ✗ {method} missing")
            return False
    
    return True


def test_code_quality_audit():
    """Test code quality audit."""
    print("\n[VALIDATION] Testing code quality audit...")
    
    from auditor.engine import IntegrityAuditor
    
    try:
        auditor = IntegrityAuditor()
        
        # Test with long line
        test_code = "def test():\n    return 'this is a very long line that exceeds 120 characters and should trigger a warning because it is way too long for the codebase'"
        issues = asyncio.run(auditor.audit_code_quality("test.py", test_code))
        
        if len(issues) > 0:
            print(f"  ✓ Code quality audit found {len(issues)} issues")
        else:
            print("  ✗ Code quality audit found no issues (expected at least one)")
            return False
        
    except Exception as e:
        print(f"  ✗ Code quality audit failed: {e}")
        return False
    
    return True


def test_security_audit():
    """Test security audit."""
    print("\n[VALIDATION] Testing security audit...")
    
    from auditor.engine import IntegrityAuditor
    
    try:
        auditor = IntegrityAuditor()
        
        # Test with hardcoded secret
        test_code = "password = \"secret123\""
        issues = asyncio.run(auditor.audit_security("test.py", test_code))
        
        if len(issues) > 0:
            print(f"  ✓ Security audit found {len(issues)} issues")
        else:
            print("  ✗ Security audit found no issues (expected at least one)")
            return False
        
    except Exception as e:
        print(f"  ✗ Security audit failed: {e}")
        return False
    
    return True


def test_dependency_audit():
    """Test dependency audit."""
    print("\n[VALIDATION] Testing dependency audit...")
    
    from auditor.engine import IntegrityAuditor
    
    try:
        auditor = IntegrityAuditor()
        
        # Test with vulnerable dependency
        imports = ["requests", "urllib3"]
        issues = asyncio.run(auditor.audit_dependencies("test.py", imports))
        
        print(f"  ✓ Dependency audit completed (found {len(issues)} issues)")
        
    except Exception as e:
        print(f"  ✗ Dependency audit failed: {e}")
        return False
    
    return True


def test_architecture_audit():
    """Test architecture audit."""
    print("\n[VALIDATION] Testing architecture audit...")
    
    from auditor.engine import IntegrityAuditor
    
    try:
        auditor = IntegrityAuditor()
        
        # Test with correct extension
        issues = asyncio.run(auditor.audit_architecture("test.py", "python"))
        
        print(f"  ✓ Architecture audit completed (found {len(issues)} issues)")
        
    except Exception as e:
        print(f"  ✗ Architecture audit failed: {e}")
        return False
    
    return True


def test_web_api_endpoints():
    """Test that web server has audit endpoints."""
    print("\n[VALIDATION] Testing Web API endpoints...")
    
    try:
        server_file = Path(__file__).parent.parent / "web" / "server.py"
        content = server_file.read_text()
        
        if "/api/audit/run" in content:
            print("  ✓ /api/audit/run endpoint exists")
        else:
            print("  ✗ /api/audit/run endpointmissing")
            return False
        
        if "/api/audit/history" in content:
            print("  ✓ /api/audit/history endpoint exists")
        else:
            print("  ✗ /api/audit/history endpoint missing")
            return False
        
        if "auditor" in content:
            print("  ✓ auditor integration exists")
        else:
            print("  ✗ auditor integration missing")
            return False
        
    except Exception as e:
        print(f"  ✗ Web API test failed: {e}")
        return False
    
    return True


def main():
    """Run all validation tests."""
    print("="*70)
    print("PR-012 Engineering Auditor Validation")
    print("="*70)
    
    tests = [
        ("Imports", test_imports),
        ("Auditor Methods", test_auditor_methods),
        ("Code Quality Audit", test_code_quality_audit),
        ("Security Audit", test_security_audit),
        ("Dependency Audit", test_dependency_audit),
        ("Architecture Audit", test_architecture_audit),
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
        print("✓ ALL TESTS PASSED - PR-012 VALIDATED")
        print("="*70)
        return 0
    else:
        print("✗ SOME TESTS FAILED - PR-012 NOT VALIDATED")
        print("="*70)
        return 1


if __name__ == "__main__":
    sys.exit(main())
