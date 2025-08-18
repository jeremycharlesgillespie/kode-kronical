#!/usr/bin/env python3
"""
Demo script showing Oracle-specific error explanations.
"""

import sys
import os

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from kode_kronical import KodeKronical

def main():
    """Demonstrate Oracle error explanation."""
    print("🔍 Oracle Database Error Explanation Demo")
    print("=" * 50)
    
    # Initialize KodeKronical - this enables enhanced exception handling
    kode = KodeKronical()
    
    print("✅ Enhanced exception handling enabled")
    print("\n🚨 Simulating Oracle connection error...")
    print()
    
    # Set up some context variables
    database_host = "prod-oracle.company.com"
    connection_timeout = 30
    username = "app_user"
    
    # This will trigger the enhanced exception handler with Oracle-specific explanation
    raise Exception("ORA-12154: TNS:could not resolve the connect identifier specified")

if __name__ == "__main__":
    main()