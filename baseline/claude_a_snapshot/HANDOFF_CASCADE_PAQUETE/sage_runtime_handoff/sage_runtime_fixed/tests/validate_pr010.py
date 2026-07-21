"""
PR-010 Validation Script

Validates the File Processing Layer implementation.
"""

import sys
import asyncio
from pathlib import Path

# Add sage_runtime to path
sys.path.insert(0, str(Path(__file__).parent.parent))


def test_imports():
    """Test that all file processor modules can be imported."""
    print("[VALIDATION] Testing imports...")
    
    try:
        from file_processor.processor import FileProcessor, ProcessedFile, FileType
        print("  ✓ processor imported")
    except Exception as e:
        print(f"  ✗ processor import failed: {e}")
        return False
    
    try:
        from file_processor.parsers.pdf_parser import PDFParser
        print("  ✓ pdf_parser imported")
    except Exception as e:
        print(f"  ✗ pdf_parser import failed: {e}")
        return False
    
    try:
        from file_processor.parsers.docx_parser import DocxParser
        print("  ✓ docx_parser imported")
    except Exception as e:
        print(f"  ✗ docx_parser import failed: {e}")
        return False
    
    try:
        from file_processor.parsers.text_parser import TextParser
        print("  ✓ text_parser imported")
    except Exception as e:
        print(f"  ✗ text_parser import failed: {e}")
        return False
    
    try:
        from file_processor.parsers.zip_parser import ZipParser
        print("  ✓ zip_parser imported")
    except Exception as e:
        print(f"  ✗ zip_parser import failed: {e}")
        return False
    
    try:
        from file_processor.parsers.image_parser import ImageParser
        print("  ✓ image_parser imported")
    except Exception as e:
        print(f"  ✗ image_parser import failed: {e}")
        return False
    
    try:
        from file_processor.parsers.code_parser import CodeParser
        print("  ✓ code_parser imported")
    except Exception as e:
        print(f"  ✗ code_parser import failed: {e}")
        return False
    
    return True


def test_file_processor():
    """Test FileProcessor initialization and methods."""
    print("\n[VALIDATION] Testing FileProcessor...")
    
    from file_processor.processor import FileProcessor
    import tempfile
    
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            processor = FileProcessor(Path(tmpdir))
            print("  ✓ FileProcessor instantiated")
    except Exception as e:
        print(f"  ✗ FileProcessor instantiation failed: {e}")
        return False
    
    # Check methods
    required_methods = [
        'process_file',
        'process_file_path',
        'detect_file_type',
        'get_supported_types',
        'cleanup_old_files'
    ]
    
    for method in required_methods:
        if hasattr(processor, method):
            print(f"  ✓ {method} exists")
        else:
            print(f"  ✗ {method} missing")
            return False
    
    return True


def test_file_type_detection():
    """Test file type detection."""
    print("\n[VALIDATION] Testing file type detection...")
    
    from file_processor.processor import FileProcessor, FileType
    import tempfile
    
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            processor = FileProcessor(Path(tmpdir))
            
            test_cases = [
                ("test.pdf", FileType.PDF),
                ("test.docx", FileType.DOCX),
                ("test.txt", FileType.TXT),
                ("test.md", FileType.MARKDOWN),
                ("test.zip", FileType.ZIP),
                ("test.jpg", FileType.IMAGE),
                ("test.py", FileType.CODE),
                ("test.js", FileType.CODE),
            ]
            
            for filename, expected_type in test_cases:
                detected = processor.detect_file_type(filename)
                if detected == expected_type:
                    print(f"  ✓ {filename} -> {detected.value}")
                else:
                    print(f"  ✗ {filename} -> {detected.value} (expected {expected_type.value})")
                    return False
            
    except Exception as e:
        print(f"  ✗ File type detection test failed: {e}")
        return False
    
    return True


def test_kernel_integration():
    """Test that Kernel can initialize FileProcessor."""
    print("\n[VALIDATION] Testing Kernel integration...")
    
    try:
        from kernel.core import SageKernel
        from pathlib import Path
        import tempfile
        
        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir)
            kernel = SageKernel(config_dir=config_dir)
            print("  ✓ Kernel instantiated")
            
            if hasattr(kernel, '_init_file_processor'):
                print("  ✓ _init_file_processor method exists")
            else:
                print("  ✗ _init_file_processor method missing")
                return False
            
    except Exception as e:
        print(f"  ✗ Kernel integration test failed: {e}")
        return False
    
    return True


def test_web_api_endpoints():
    """Test that web server has file upload endpoint."""
    print("\n[VALIDATION] Testing Web API endpoints...")
    
    try:
        server_file = Path(__file__).parent.parent / "web" / "server.py"
        content = server_file.read_text()
        
        if "/api/files/upload" in content:
            print("  ✓ /api/files/upload endpoint exists")
        else:
            print("  ✗ /api/files/upload endpoint missing")
            return False
        
        if "file_processor" in content:
            print("  ✓ file_processor integration exists")
        else:
            print("  ✗ file_processor integration missing")
            return False
        
        if "UploadFile" in content:
            print("  ✓ UploadFile import exists")
        else:
            print("  ✗ UploadFile import missing")
            return False
        
    except Exception as e:
        print(f"  ✗ Web API test failed: {e}")
        return False
    
    return True


def test_requirements():
    """Test that requirements.txt includes file processing dependencies."""
    print("\n[VALIDATION] Testing requirements.txt...")
    
    requirements_file = Path(__file__).parent.parent / "requirements.txt"
    content = requirements_file.read_text()
    
    if "PyPDF2" in content:
        print("  ✓ PyPDF2 dependency present")
    else:
        print("  ✗ PyPDF2 dependency missing")
        return False
    
    if "python-docx" in content:
        print("  ✓ python-docx dependency present")
    else:
        print("  ✗ python-docx dependency missing")
        return False
    
    if "Pillow" in content:
        print("  ✓ Pillow dependency present")
    else:
        print("  ✗ Pillow dependency missing")
        return False
    
    return True


def test_parsers():
    """Test that all parsers have required methods."""
    print("\n[VALIDATION] Testing parsers...")
    
    from file_processor.parsers.pdf_parser import PDFParser
    from file_processor.parsers.docx_parser import DocxParser
    from file_processor.parsers.text_parser import TextParser
    from file_processor.parsers.zip_parser import ZipParser
    from file_processor.parsers.image_parser import ImageParser
    from file_processor.parsers.code_parser import CodeParser
    
    parsers = [
        ("PDFParser", PDFParser),
        ("DocxParser", DocxParser),
        ("TextParser", TextParser),
        ("ZipParser", ZipParser),
        ("ImageParser", ImageParser),
        ("CodeParser", CodeParser)
    ]
    
    for parser_name, parser_class in parsers:
        try:
            parser = parser_class()
            if hasattr(parser, 'parse'):
                print(f"  ✓ {parser_name} has parse method")
            else:
                print(f"  ✗ {parser_name} missing parse method")
                return False
        except Exception as e:
            print(f"  ✗ {parser_name} instantiation failed: {e}")
            return False
    
    return True


def main():
    """Run all validation tests."""
    print("="*70)
    print("PR-010 File Processing Layer Validation")
    print("="*70)
    
    tests = [
        ("Imports", test_imports),
        ("FileProcessor", test_file_processor),
        ("File Type Detection", test_file_type_detection),
        ("Kernel Integration", test_kernel_integration),
        ("Web API Endpoints", test_web_api_endpoints),
        ("Requirements", test_requirements),
        ("Parsers", test_parsers)
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
        print("✓ ALL TESTS PASSED - PR-010 VALIDATED")
        print("="*70)
        return 0
    else:
        print("✗ SOME TESTS FAILED - PR-010 NOT VALIDATED")
        print("="*70)
        return 1


if __name__ == "__main__":
    sys.exit(main())
