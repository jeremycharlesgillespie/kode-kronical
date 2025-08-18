#!/usr/bin/env python3
"""
Test script to demonstrate global variables in enhanced exception handling.
"""

import sys
import os

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from kode_kronical.core import KodeKronical

# Define some global variables to test
GLOBAL_CONFIG = {
    "environment": "development",
    "debug": True,
    "max_connections": 100
}

DATABASE_URL = "postgresql://localhost:5432/myapp"
API_KEY = "secret-api-key-12345"
VERSION = "1.2.3"

def helper_function():
    """A helper function that will access global variables."""
    
    local_data = {
        "processed_items": 42,
        "errors": [],
        "status": "processing"
    }
    
    # Try to use global variables
    print(f"Using global config: {GLOBAL_CONFIG}")
    print(f"Database URL: {DATABASE_URL}")
    
    # Create a problem that will show both local and global variables
    if GLOBAL_CONFIG["debug"]:
        # This will cause an exception
        return local_data / VERSION  # Can't divide dict by string


def main_function():
    """Main function that calls helper."""
    
    session_data = {
        "user_id": 12345,
        "session_token": "abc123def456",
        "login_time": "2025-08-14T22:00:00Z"
    }
    
    current_operation = "user_authentication"
    retry_count = 3
    
    return helper_function()


def main():
    """Initialize KodeKronical and trigger exception."""
    
    print("Testing global variables in enhanced exception handling...")
    print("=" * 70)
    
    # Initialize KodeKronical - this enables enhanced exception handling
    kode = KodeKronical()
    
    print("Global variables defined:")
    print(f"  GLOBAL_CONFIG = {GLOBAL_CONFIG}")
    print(f"  DATABASE_URL = {DATABASE_URL}")
    print(f"  API_KEY = {API_KEY}")
    print(f"  VERSION = {VERSION}")
    print()
    print("Now triggering an exception to see both local and global variables...")
    print()
    
    # This will cause an exception that should show global variables
    main_function()


if __name__ == "__main__":
    main()