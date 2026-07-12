"""
Contract Validator Integration Tests

Tests for ContractValidator integration with kernel and API endpoints.
"""

import sys
import asyncio
from pathlib import Path

# Add sage_runtime to path
sys.path.insert(0, str(Path(__file__).parent.parent))


async def test_contract_validator():
    """Test ContractValidator basic functionality."""
    print("[TEST] Testing ContractValidator...")
    
    from contracts.validator import ContractValidator
    
    validator = ContractValidator()
    await validator.initialize()
    print("  ✓ ContractValidator initialized")
    
    # Test contract creation
    contract = await validator.create_contract(
        title="Test Contract",
        description="A test contract",
        content={"key": "value"},
        author="test_author"
    )
    
    assert contract.contract_id is not None
    assert contract.title == "Test Contract"
    print("  ✓ Contract creation works")
    
    # Test contract validation
    is_valid = await validator.validate_contract(contract.contract_id)
    assert is_valid == True
    print("  ✓ Contract validation works")
    
    # Test contract approval
    approved = await validator.approve_contract(contract.contract_id, "reviewer")
    assert approved == True
    print("  ✓ Contract approval works")
    
    # Test RFC creation
    rfc = await validator.create_rfc(
        title="Test RFC",
        description="A test RFC",
        author="test_author"
    )
    
    assert rfc.rfc_id is not None
    assert rfc.title == "Test RFC"
    print("  ✓ RFC creation works")
    
    # Test RFC submission
    submitted = await validator.submit_rfc(rfc.rfc_id)
    assert submitted == True
    print("  ✓ RFC submission works")
    
    # Test listing
    contracts = validator.list_contracts()
    assert len(contracts) > 0
    print("  ✓ Contract listing works")
    
    rfcs = validator.list_rfcs()
    assert len(rfcs) > 0
    print("  ✓ RFC listing works")
    
    await validator.shutdown()
    print("  ✓ ContractValidator shutdown works")
    
    return True


async def test_kernel_integration():
    """Test ContractValidator integration with kernel."""
    print("\n[TEST] Testing Kernel integration...")
    
    from kernel.core import SageKernel
    import tempfile
    
    with tempfile.TemporaryDirectory() as tmpdir:
        config_dir = Path(tmpdir)
        kernel = SageKernel(config_dir=config_dir)
        
        # Boot kernel
        context = await kernel.boot()
        print("  ✓ Kernel booted")
        
        # Check if contract validator is registered
        validator = kernel.get_component('contract_validator')
        assert validator is not None
        print("  ✓ ContractValidator registered in kernel")
        
        # Test contract creation through kernel
        contract = await validator.create_contract(
            title="Kernel Test Contract",
            description="Test via kernel",
            content={"test": True},
            author="kernel_test"
        )
        
        assert contract.contract_id is not None
        print("  ✓ Contract creation via kernel works")
        
        # Test listing through kernel
        contracts = validator.list_contracts()
        assert len(contracts) > 0
        print("  ✓ Contract listing via kernel works")
        
        # Shutdown kernel
        await kernel.shutdown()
        print("  ✓ Kernel shutdown works")
    
    return True


async def main():
    """Run all contract validator tests."""
    print("="*70)
    print("Contract Validator Integration Tests")
    print("="*70)
    
    tests = [
        ("ContractValidator", test_contract_validator),
        ("Kernel Integration", test_kernel_integration)
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
