"""
PR-011 Validation Script

Validates the Repository Scanner implementation.
"""

import sys
import asyncio
from pathlib import Path

# Add sage_runtime to path
sys.path.insert(0, str(Path(__file__).parent.parent))


def test_imports():
    """Test that all repository scanner modules can be imported."""
    print("[VALIDATION] Testing imports...")
    
    try:
        from repository_scanner.scanner import RepositoryScanner, ScanResult, FileAnalysis
        print("  ✓ scanner imported")
    except Exception as e:
        print(f"  ✗ scanner import failed: {e}")
        return False
    
    try:
        from repository_scanner.language_detector import LanguageDetector
        print("  ✓ language_detector imported")
    except Exception as e:
        print(f"  ✗ language_detector import failed: {e}")
        return False
    
    try:
        from repository_scanner.ast_parser import ASTParser
        print("  ✓ ast_parser imported")
    except Exception as e:
        print(f"  ✗ ast_parser import failed: {e}")
        return False
    
    try:
        from repository_scanner.dependency_graph import DependencyGraph
        print("  ✓ dependency_graph imported")
    except Exception as e:
        print(f"  ✗ dependency_graph import failed: {e}")
        return False
    
    return True


def test_repository_scanner():
    """Test RepositoryScanner initialization and methods."""
    print("\n[VALIDATION] Testing RepositoryScanner...")
    
    from repository_scanner.scanner import RepositoryScanner
    
    try:
        scanner = RepositoryScanner()
        print("  ✓ RepositoryScanner instantiated")
    except Exception as e:
        print(f"  ✗ RepositoryScanner instantiation failed: {e}")
        return False
    
    # Check methods
    required_methods = [
        'scan_repository',
        '_analyze_file',
        '_generate_summary'
    ]
    
    for method in required_methods:
        if hasattr(scanner, method):
            print(f"  ✓ {method} exists")
        else:
            print(f"  ✗ {method} missing")
            return False
    
    return True


def test_language_detector():
    """Test language detection."""
    print("\n[VALIDATION] Testing LanguageDetector...")
    
    from repository_scanner.language_detector import LanguageDetector
    
    try:
        detector = LanguageDetector()
        print("  ✓ LanguageDetector instantiated")
    except Exception as e:
        print(f"  ✗ LanguageDetector instantiation failed: {e}")
        return False
    
    # Test detection
    test_cases = [
        ("test.py", "python"),
        ("test.js", "javascript"),
        ("test.ts", "typescript"),
        ("test.java", "java"),
        ("test.go", "go"),
        ("test.rs", "rust"),
        ("test.cpp", "cpp"),
        ("test.md", "markdown"),
    ]
    
    for filename, expected_lang in test_cases:
        detected = detector.detect(Path(filename))
        if detected == expected_lang:
            print(f"  ✓ {filename} -> {detected}")
        else:
            print(f"  ✗ {filename} -> {detected} (expected {expected_lang})")
            return False
    
    return True


def test_ast_parser():
    """Test AST parser."""
    print("\n[VALIDATION] Testing ASTParser...")
    
    from repository_scanner.ast_parser import ASTParser
    
    try:
        parser = ASTParser()
        print("  ✓ ASTParser instantiated")
    except Exception as e:
        print(f"  ✗ ASTParser instantiation failed: {e}")
        return False
    
    # Test parsing
    test_code = "def test():\n    pass"
    try:
        result = parser.parse(test_code, "python")
        if "functions" in result:
            print("  ✓ Python parsing works")
        else:
            print("  ✗ Python parsing failed")
            return False
    except Exception as e:
        print(f"  ✗ Parsing failed: {e}")
        return False
    
    return True


def test_dependency_graph():
    """Test dependency graph."""
    print("\n[VALIDATION] Testing DependencyGraph...")
    
    from repository_scanner.dependency_graph import DependencyGraph
    
    try:
        dep_graph = DependencyGraph()
        print("  ✓ DependencyGraph instantiated")
    except Exception as e:
        print(f"  ✗ DependencyGraph instantiation failed: {e}")
        return False
    
    # Check methods
    required_methods = ['build_graph']
    
    for method in required_methods:
        if hasattr(dep_graph, method):
            print(f"  ✓ {method} exists")
        else:
            print(f"  ✗ {method} missing")
            return False
    
    return True


def test_kernel_integration():
    """Test that Kernel can initialize RepositoryScanner."""
    print("\n[VALIDATION] Testing Kernel integration...")
    
    try:
        from kernel.core import SageKernel
        from pathlib import Path
        import tempfile
        
        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir)
            kernel = SageKernel(config_dir=config_dir)
            print("  ✓ Kernel instantiated")
            
            if hasattr(kernel, '_init_repository_scanner'):
                print("  ✓ _init_repository_scanner method exists")
            else:
                print("  ✗ _init_repository_scanner method missing")
                return False
            
    except Exception as e:
        print(f"  ✗ Kernel integration test failed: {e}")
        return False
    
    return True


def test_web_api_endpoints():
    """Test that web server has repository scan endpoint."""
    print("\n[VALIDATION] Testing Web API endpoints...")
    
    try:
        server_file = Path(__file__).parent.parent / "web" / "server.py"
        content = server_file.read_text()
        
        if "/api/repository/scan" in content:
            print("  ✓ /api/repository/scan endpoint exists")
        else:
            print("  ✗ /api/repository/scan endpoint missing")
            return False
        
        if "repository_scanner" in content:
            print("  ✓ repository_scanner integration exists")
        else:
            print("  ✗ repository_scanner integration missing")
            return False
        
    except Exception as e:
        print(f"  ✗ Web API test failed: {e}")
        return False
    
    return True


def main():
    """Run all validation tests."""
    print("="*70)
    print("PR-011 Repository Scanner Validation")
    print("="*70)
    
    tests = [
        ("Imports", test_imports),
        ("RepositoryScanner", test_repository_scanner),
        ("LanguageDetector", test_language_detector),
        ("ASTParser", test_ast_parser),
        ("DependencyGraph", test_dependency_graph),
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
        print("✓ ALL TESTS PASSED - PR-011 VALIDATED")
        print("="*70)
        return 0
    else:
        print("✗ SOME TESTS FAILED - PR-011 NOT VALIDATED")
        print("="*70)
        return 1


if __name__ == "__main__":
    sys.exit(main())
