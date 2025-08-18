#!/usr/bin/env python3
"""
Quick test to see the plain language summary with different error types.
"""

import sys
import os

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from kode_kronical import KodeKronical

# Global settings
MAX_RETRIES = 3
TIMEOUT_SECONDS = 30

def calculate_average(numbers):
    """Calculate average that will fail."""
    total = sum(numbers)
    count = len([n for n in numbers if n > 0])  # This will be 0
    
    average = total / count  # Division by zero!
    return average

def main():
    """Test with a different error type."""
    print("Testing plain language summary with ZeroDivisionError...")
    
    kode = KodeKronical()
    
    # Data that will cause division by zero
    test_numbers = [-1, -2, -3]  # No positive numbers
    
    calculate_average(test_numbers)

if __name__ == "__main__":
    main()