#!/usr/bin/env python3
"""
Test script to demonstrate enhanced error explanations with library-specific errors.
"""

import sys
import os

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from kode_kronical import KodeKronical

def test_oracle_errors():
    """Test Oracle database error explanations."""
    print("🔍 Testing Oracle Database Error Explanations")
    print("=" * 55)
    
    # Initialize KodeKronical to enable enhanced exceptions
    kode = KodeKronical()
    
    # Simulate different Oracle errors
    oracle_errors = [
        ("ORA-00942", "ORA-00942: table or view does not exist"),
        ("ORA-01017", "ORA-01017: invalid username/password; logon denied"),
        ("ORA-12154", "ORA-12154: TNS:could not resolve the connect identifier specified"),
        ("ORA-01722", "ORA-01722: invalid number"),
        ("ConnectionError", "oracledb.exceptions.DatabaseError: connection failed"),
    ]
    
    print("\nTesting Oracle error explanations:")
    for error_code, error_msg in oracle_errors:
        try:
            # Simulate the error
            raise Exception(error_msg)
        except Exception as e:
            # Test our explanation system
            from kode_kronical.exception_handler import EnhancedExceptionHandler
            handler = EnhancedExceptionHandler()
            explanation = handler._explain_error_type(type(e).__name__, str(e))
            print(f"\n{error_code}:")
            print(f"  Original: {error_msg}")
            print(f"  Explanation: {explanation}")

def test_requests_errors():
    """Test HTTP/requests library error explanations."""
    print("\n\n🌐 Testing HTTP/Requests Error Explanations")
    print("=" * 55)
    
    http_errors = [
        ("ConnectionError", "requests.exceptions.ConnectionError: Failed to establish a new connection"),
        ("Timeout", "requests.exceptions.Timeout: Read timed out"),
        ("HTTPError", "requests.exceptions.HTTPError: 404 Client Error: Not Found"),
        ("SSLError", "requests.exceptions.SSLError: SSL certificate verification failed"),
    ]
    
    print("\nTesting HTTP/requests error explanations:")
    for error_type, error_msg in http_errors:
        try:
            raise Exception(error_msg)
        except Exception as e:
            from kode_kronical.exception_handler import EnhancedExceptionHandler
            handler = EnhancedExceptionHandler()
            explanation = handler._explain_error_type(error_type, str(e))
            print(f"\n{error_type}:")
            print(f"  Original: {error_msg}")
            print(f"  Explanation: {explanation}")

def test_pandas_errors():
    """Test pandas library error explanations."""
    print("\n\n🐼 Testing Pandas Error Explanations")
    print("=" * 55)
    
    pandas_errors = [
        ("KeyError", "KeyError: 'column_name' not found in DataFrame"),
        ("ValueError", "ValueError: Length of values does not match length of index"),
        ("TypeError", "TypeError: DataFrame operation requires numeric data"),
    ]
    
    print("\nTesting pandas error explanations:")
    for error_type, error_msg in pandas_errors:
        try:
            raise Exception(error_msg)
        except Exception as e:
            from kode_kronical.exception_handler import EnhancedExceptionHandler
            handler = EnhancedExceptionHandler()
            explanation = handler._explain_error_type(error_type, str(e))
            print(f"\n{error_type}:")
            print(f"  Original: {error_msg}")
            print(f"  Explanation: {explanation}")

def test_json_errors():
    """Test JSON parsing error explanations."""
    print("\n\n📄 Testing JSON Error Explanations") 
    print("=" * 55)
    
    json_errors = [
        ("JSONDecodeError", "json.decoder.JSONDecodeError: Expecting ',' delimiter"),
        ("ValueError", "ValueError: Expecting property name enclosed in double quotes"),
    ]
    
    print("\nTesting JSON error explanations:")
    for error_type, error_msg in json_errors:
        try:
            raise Exception(error_msg)
        except Exception as e:
            from kode_kronical.exception_handler import EnhancedExceptionHandler
            handler = EnhancedExceptionHandler()
            explanation = handler._explain_error_type(error_type, str(e))
            print(f"\n{error_type}:")
            print(f"  Original: {error_msg}")
            print(f"  Explanation: {explanation}")

def test_actual_exception():
    """Test with an actual exception to see the full enhanced trace."""
    print("\n\n🚨 Testing Full Enhanced Exception Trace")
    print("=" * 55)
    print("\nTriggering a simulated Oracle connection error...")
    
    # This will trigger the enhanced exception handler
    connection_string = "oracle://user:pass@localhost:1521/xe"
    timeout = 30
    
    # Simulate Oracle connection error
    raise Exception("ORA-12154: TNS:could not resolve the connect identifier specified")

def main():
    """Run all error explanation tests."""
    print("🧪 Enhanced Error Explanations Test Suite")
    print("=" * 60)
    print()
    print("This demonstrates kode-kronical's enhanced error explanations for:")
    print("• Oracle database errors (python-oracledb)")
    print("• HTTP/requests errors")
    print("• Pandas data manipulation errors")
    print("• JSON parsing errors")
    print("• And many more...")
    print()
    
    try:
        test_oracle_errors()
        test_requests_errors()
        test_pandas_errors() 
        test_json_errors()
        
        print("\n\n✅ All explanation tests completed!")
        print("\nNow testing with actual exception handling...")
        
        # This will trigger the full enhanced exception handler
        test_actual_exception()
        
    except Exception as e:
        # This should show the enhanced exception with Oracle-specific explanation
        pass

if __name__ == "__main__":
    main()