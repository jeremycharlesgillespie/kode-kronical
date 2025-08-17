#!/usr/bin/env python3
"""
Test script for the enhanced exception handler feature.
"""

import sys
import os

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from kode_kronical.core import KodeKronical


def problematic_function(user_data, settings):
    """A function that will cause an exception with interesting variables."""
    
    # Create some local variables with different types
    counter = 42
    message = "Processing user data..."
    items = ["apple", "banana", "cherry", "date", "elderberry"]
    user_profile = {
        "name": "John Doe",
        "age": 30,
        "email": "john.doe@example.com",
        "preferences": {
            "theme": "dark",
            "language": "en",
            "notifications": True
        }
    }
    
    # A nested function to show frame variables
    def process_items():
        processed_count = 0
        current_item = None
        
        for item in items:
            current_item = item
            processed_count += 1
            
            # Create a problem that will raise an exception
            if item == "cherry":
                # This will cause a TypeError
                result = item + counter  # Can't add string and int
                
        return processed_count
    
    return process_items()


def another_function():
    """Another function to show multiple stack frames."""
    
    config = {
        "debug": True,
        "max_retries": 3,
        "timeout": 30.0
    }
    
    user_data = {
        "id": 12345,
        "username": "testuser",
        "last_login": "2025-08-14T22:30:00Z"
    }
    
    # Call the problematic function
    return problematic_function(user_data, config)


def main():
    """Main function to test enhanced exception handling."""
    
    print("Testing kode-kronical enhanced exception handling...")
    print("=" * 60)
    
    # Initialize KodeKronical - this should automatically enable enhanced exceptions
    perf = KodeKronical()
    
    print("KodeKronical initialized. Enhanced exception handling should be active.")
    print("Now triggering an unhandled exception to demonstrate the feature...\n")
    
    # This will cause an unhandled exception that should be caught by our global handler
    another_function()


if __name__ == "__main__":
    main()