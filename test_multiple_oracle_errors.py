#!/usr/bin/env python3
"""
Demo multiple Oracle-specific error explanations.
"""

import sys
import os

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from kode_kronical import KodeKronical

def test_ora_errors():
    """Test different Oracle error explanations."""
    
    # Initialize KodeKronical - enables enhanced exception handling
    perf = KodeKronical()
    
    oracle_errors = [
        "ORA-00942: table or view does not exist",
        "ORA-01017: invalid username/password; logon denied", 
        "ORA-01722: invalid number",
        "ORA-01400: cannot insert NULL into (USERS.ID)",
        "ORA-12541: TNS:no listener"
    ]
    
    print("🔍 Testing Multiple Oracle Error Explanations")
    print("=" * 55)
    print("\nTesting Oracle errors one by one...\n")
    
    for i, error_msg in enumerate(oracle_errors, 1):
        print(f"🚨 Test {i}: {error_msg}")
        print("-" * 50)
        
        try:
            # Set up some realistic context variables
            user_id = 12345
            table_name = "users" 
            connection_pool_size = 10
            
            raise Exception(error_msg)
            
        except Exception:
            print("(Enhanced trace shown above)")
            print()

if __name__ == "__main__":
    test_ora_errors()