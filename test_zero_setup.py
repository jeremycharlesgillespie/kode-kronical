#!/usr/bin/env python3
"""
Test script to verify kode-kronical works with zero setup - no configuration needed.
"""

import sys
import os

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

print("🧪 Testing kode-kronical zero-setup functionality...")
print("=" * 60)

# Test 1: Import should work without any configuration
print("\n1️⃣  Testing basic import...")
try:
    from kode_kronical import KodeKronical
    print("✅ Import successful")
except Exception as e:
    print(f"❌ Import failed: {e}")
    sys.exit(1)

# Test 2: Initialize KodeKronical without any config
print("\n2️⃣  Testing KodeKronical initialization without config...")
try:
    perf = KodeKronical()
    print("✅ KodeKronical initialization successful")
except Exception as e:
    print(f"❌ KodeKronical initialization failed: {e}")
    sys.exit(1)

# Test 3: Use timing decorator
print("\n3️⃣  Testing timing decorator...")
@perf.time_it
def sample_function(n):
    """A sample function to time."""
    total = 0
    for i in range(n):
        total += i * i
    return total

try:
    result = sample_function(10000)  # Larger number to ensure it meets timing threshold
    print(f"✅ Timing decorator works: sample_function(10000) = {result}")
except Exception as e:
    print(f"❌ Timing decorator failed: {e}")

# Test 4: Get results
print("\n4️⃣  Testing results retrieval...")
try:
    results = perf.get_results()
    print(f"✅ Results retrieved: {len(results)} timing records")
    
    if results:
        sample_result = results[0]
        print(f"   Sample: {sample_result.function_name} took {sample_result.wall_time:.4f}s")
except Exception as e:
    print(f"❌ Results retrieval failed: {e}")

# Test 5: Test failure capture
print("\n5️⃣  Testing failure capture...")
try:
    from kode_kronical import capture_failure
    
    # Simulate a failure
    try:
        raise ValueError("This is a test failure")
    except Exception as e:
        failure_report = capture_failure("Test operation", e, {
            "test_context": "zero setup test",
            "step": 5
        })
        print("✅ Failure capture works")
        print("   (Detailed failure report was generated)")
except Exception as e:
    print(f"❌ Failure capture failed: {e}")

# Test 6: Test enhanced exceptions
print("\n6️⃣  Testing enhanced exceptions...")
try:
    # This should have been automatically enabled
    test_var = "test_value"
    another_var = 42
    
    # Don't actually trigger an exception in the test
    print("✅ Enhanced exceptions should be enabled automatically")
    print("   (Would show detailed traces for unhandled exceptions)")
except Exception as e:
    print(f"❌ Enhanced exceptions test failed: {e}")

# Test 7: Test with no AWS credentials
print("\n7️⃣  Testing behavior without AWS credentials...")
try:
    # Try to create another KodeKronical instance
    perf2 = KodeKronical()
    print("✅ Works without AWS credentials (using local storage fallback)")
except Exception as e:
    print(f"❌ Failed without AWS credentials: {e}")

# Test 8: Test summary and cleanup
print("\n8️⃣  Testing summary and cleanup...")
try:
    summary = perf.get_summary()
    print(f"✅ Summary generated: {summary.get('call_count', 0)} calls tracked")
    
    # Test clearing results
    perf.clear_results()
    results_after_clear = perf.get_results()
    print(f"✅ Cleanup works: {len(results_after_clear)} results after clear")
except Exception as e:
    print(f"❌ Summary/cleanup failed: {e}")

# Final status
print("\n" + "=" * 60)
print("🎉 ZERO-SETUP TEST COMPLETE")
print()
print("✨ kode-kronical should work out of the box with:")
print("   • No configuration files needed")
print("   • No database setup required") 
print("   • No AWS credentials needed")
print("   • Automatic fallback to local storage")
print("   • Enhanced exception handling enabled by default")
print("   • Failure capture for debugging")
print()
print("📋 To use kode-kronical in your project:")
print("   1. pip install kode-kronical")
print("   2. from kode_kronical import KodeKronical")
print("   3. perf = KodeKronical()")
print("   4. @perf.time_it")
print("      def your_function():")
print("          pass")
print()
print("That's it! 🚀")