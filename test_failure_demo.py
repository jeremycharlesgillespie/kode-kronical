#!/usr/bin/env python3
"""
Demo script to show failure capture in action.
"""

import sys
import os

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from kode_kronical import KodeKronical, capture_failure

def database_operation():
    """Simulate a database operation that fails."""
    connection_string = "postgresql://localhost:5432/nonexistent"
    timeout = 30
    retry_count = 3
    
    # Simulate the failure
    raise ConnectionError("Could not connect to database server")

def file_processing():
    """Simulate file processing that fails."""
    file_path = "/path/to/missing/file.txt"
    batch_size = 100
    
    # Simulate the failure  
    raise FileNotFoundError(f"No such file or directory: '{file_path}'")

def main():
    """Demo failure capture."""
    print("🔍 kode-kronical Failure Capture Demo")
    print("=" * 50)
    
    # Initialize KodeKronical
    perf = KodeKronical()
    
    print("\n📊 Simulating various failure scenarios...\n")
    
    # Test 1: Database connection failure
    print("1️⃣  Database Connection Failure:")
    try:
        database_operation()
    except Exception as e:
        capture_failure("Database connection", e, {
            "connection_string": "postgresql://localhost:5432/nonexistent",
            "timeout": 30,
            "retry_count": 3
        })
    
    print("\n" + "-" * 50 + "\n")
    
    # Test 2: File processing failure
    print("2️⃣  File Processing Failure:")
    try:
        file_processing()
    except Exception as e:
        capture_failure("File processing", e, {
            "file_path": "/path/to/missing/file.txt",
            "batch_size": 100,
            "operation": "batch_process"
        })
    
    print("\n" + "-" * 50 + "\n")
    
    # Test 3: Show failure stats
    print("3️⃣  Failure Statistics:")
    from kode_kronical import get_failure_stats
    stats = get_failure_stats()
    print(f"   Total failures captured: {stats['total_failures']}")
    print(f"   Recent failures: {len(stats['recent_failures'])}")
    
    print("\n🎯 Failure capture provides detailed context for debugging!")

if __name__ == "__main__":
    main()