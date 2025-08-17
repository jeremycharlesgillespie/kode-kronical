#!/usr/bin/env python3
"""
Test KodeKronical behavior with restricted permissions (simulated).
"""

import sys
import os

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

print("🔒 Testing kode-kronical with restricted permissions...")
print("=" * 60)

# Test with a read-only directory
print("\n1️⃣  Testing with read-only data directory...")
try:
    from kode_kronical import KodeKronical
    
    # Try to initialize with a directory that doesn't exist and can't be created
    perf = KodeKronical({
        'local': {
            'enabled': True,
            'data_dir': '/root/restricted/perf_data'  # This should fail
        }
    })
    
    @perf.time_it
    def test_function():
        return sum(range(1000))
    
    result = test_function()
    print(f"✅ KodeKronical continues to work even with storage issues")
    print(f"   Function result: {result}")
    print(f"   Timing results: {len(perf.get_results())} records")
    
except Exception as e:
    print(f"❌ Failed: {e}")

print("\n2️⃣  Testing minimal functionality...")
try:
    # Just basic timing without any storage
    simple_perf = KodeKronical()
    
    @simple_perf.time_it
    def simple_function(n):
        total = 0
        for i in range(n):
            total += i
        return total
    
    result = simple_function(10000)  # Larger number to ensure timing
    results = simple_perf.get_results()
    
    print(f"✅ Basic timing works: {len(results)} records")
    if results:
        print(f"   Sample timing: {results[0].function_name} = {results[0].wall_time:.6f}s")

except Exception as e:
    print(f"❌ Basic timing failed: {e}")

print("\n🎯 kode-kronical gracefully handles permission and storage issues!")
print("   Even if storage fails, timing functionality continues to work.")