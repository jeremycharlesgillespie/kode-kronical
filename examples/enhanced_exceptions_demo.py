#!/usr/bin/env python3
"""
Demo script showing kode-kronical's enhanced exception handling feature.

This script demonstrates how importing kode-kronical automatically enables 
detailed stack traces with local and global variable values.
"""

import sys
import os

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from kode_kronical import KodeKronical

# Global configuration that will be shown in the exception trace
API_CONFIG = {
    "base_url": "https://api.example.com",
    "timeout": 30,
    "max_retries": 3
}

DEBUG_MODE = True
APP_VERSION = "2.1.0"


def process_user_data(user_info):
    """Process user data with potential for errors."""
    
    # Local variables that will be shown in the trace
    processing_status = "active"
    items_processed = 0
    error_count = 0
    
    # Simulate processing that goes wrong
    for item in user_info.get("items", []):
        items_processed += 1
        
        # This will cause a TypeError when we hit the problematic item
        if item == "bad_data":
            result = item / API_CONFIG["timeout"]  # Can't divide string by int!
            
    return {"processed": items_processed, "errors": error_count}


def main():
    """Demonstrate the enhanced exception handling."""
    
    print("kode-kronical Enhanced Exception Handler Demo")
    print("=" * 55)
    print()
    print("This demo shows how kode-kronical automatically captures:")
    print("• Complete stack traces with all frames")
    print("• Local variables in each function")
    print("• Global variables accessible from each frame")
    print("• Smart formatting for different data types")
    print()
    
    # Initialize KodeKronical - this automatically enables enhanced exception handling
    perf = KodeKronical()
    print("KodeKronical initialized - enhanced exception handling is now active")
    print()
    print("Current global variables:")
    print(f"   API_CONFIG = {API_CONFIG}")
    print(f"   DEBUG_MODE = {DEBUG_MODE}")
    print(f"   APP_VERSION = {APP_VERSION}")
    print()
    print("Triggering exception to demonstrate enhanced trace...")
    print()
    
    # Set up data that will cause an exception
    user_data = {
        "user_id": 12345,
        "username": "demo_user",
        "items": ["item1", "item2", "bad_data", "item4"]
    }
    
    # This will trigger the enhanced exception handler
    process_user_data(user_data)


if __name__ == "__main__":
    main()