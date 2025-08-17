# Enhanced Exception Handling

KodeKronical includes an enhanced exception handling feature that automatically captures detailed stack traces with variable values for unhandled exceptions. This is extremely useful for debugging as it shows you exactly what values were in scope when an exception occurred.

## Automatic Activation

Enhanced exception handling is **automatically enabled** when you import and initialize KodeKronical:

```python
from kode_kronical import KodeKronical

# This automatically enables enhanced exception handling
perf = KodeKronical()

# Any unhandled exception from this point forward will show detailed information
```

## Features

The enhanced exception handler provides:

- **Complete stack trace** with all frames
- **Local variables** in each frame with their actual values
- **Global variables** accessible from each frame (configurable)
- **Smart value formatting** for different data types
- **Function names and line numbers**
- **The exact code line** that caused the exception
- **Standard traceback** for reference

## Example Output

When an unhandled exception occurs, you'll see output like this:

```
================================================================================
ENHANCED EXCEPTION TRACE WITH VARIABLES
================================================================================

Frame #1:
  File: /path/to/your/script.py
  Function: main
  Line 25: process_data(user_info, settings)
  Local Variables:
    user_info = {"name": "John Doe", "age": 30, "email": "john@example.com"}
    settings = {"debug": True, "max_retries": 3, "timeout": 30.0}

Frame #2:
  File: /path/to/your/script.py
  Function: process_data
  Line 15: result = total / count  # Division by zero!
  Local Variables:
    count = 0
    items = ["apple", "banana", "cherry"]
    total = 100
    user_data = {"name": "John Doe", "age": 30, "email": "john@example.com"}
  Global Variables:
    API_KEY = "secret-key-123"
    DATABASE_URL = "postgresql://localhost/myapp"
    VERSION = "1.2.3"

--------------------------------------------------------------------------------
Exception Type: ZeroDivisionError
Exception Value: division by zero
--------------------------------------------------------------------------------

Standard Traceback:
----------------------------------------
Traceback (most recent call last):
  File "/path/to/your/script.py", line 25, in main
    process_data(user_info, settings)
  File "/path/to/your/script.py", line 15, in process_data
    result = total / count
ZeroDivisionError: division by zero
================================================================================
```

## Smart Value Formatting

The handler intelligently formats different types of values:

- **Strings**: Shown with quotes, truncated if too long
- **Numbers**: Displayed as-is
- **Lists/Tuples**: Shows first few items, indicates total count
- **Dictionaries**: Shows key-value pairs, truncated if large
- **Objects**: Shows class name and key attributes
- **Functions**: Shows function name and type

## Configuration

You can configure the enhanced exception handling behavior:

### Via Configuration File (.kode-kronical.yaml)

```yaml
kode_kronical:
  # Enable/disable enhanced exception handling
  enable_enhanced_exceptions: true
  
  # Maximum length for string representations
  exception_max_value_length: 1000
  
  # Maximum items to show from collections
  exception_max_collection_items: 10
  
  # Whether to show global variables in traces
  exception_show_globals: true
```

### Via Code

```python
from kode_kronical import KodeKronical

# Initialize with custom settings
perf = KodeKronical({
    'kode_kronical': {
        'enable_enhanced_exceptions': True,
        'exception_max_value_length': 500,
        'exception_max_collection_items': 5,
        'exception_show_globals': False  # Disable global variables
    }
})

# Or control manually
perf.enable_enhanced_exceptions(
    max_value_length=500, 
    max_collection_items=5,
    show_globals=False
)
perf.disable_enhanced_exceptions()
```

### Standalone Usage

You can also use the enhanced exception handling without the full KodeKronical setup:

```python
from kode_kronical import enable_enhanced_exceptions, disable_enhanced_exceptions

# Enable manually
enable_enhanced_exceptions(
    max_value_length=800, 
    max_collection_items=8,
    show_globals=True
)

# Your code here...

# Disable when done
disable_enhanced_exceptions()
```

## Safety Features

The enhanced exception handler is designed to be safe and robust:

- **No performance impact** during normal execution
- **Safe value formatting** that won't cause additional exceptions
- **Memory conscious** - limits output for large data structures
- **Preserves original behavior** for KeyboardInterrupt (Ctrl+C)
- **Fallback protection** - falls back to standard traceback if the handler fails

## Disabling Enhanced Exceptions

If you want to disable enhanced exception handling:

### Via Configuration

```yaml
kode_kronical:
  enable_enhanced_exceptions: false
  # Or just disable global variables
  exception_show_globals: false
```

### Via Code

```python
from kode_kronical import KodeKronical

# Disable during initialization
perf = KodeKronical({'kode_kronical': {'enable_enhanced_exceptions': False}})

# Or disable after initialization
perf.disable_enhanced_exceptions()
```

## Use Cases

Enhanced exception handling is particularly useful for:

- **Development and debugging** - See exactly what data caused the problem
- **Production troubleshooting** - Get more context about unexpected errors
- **Data processing scripts** - Understand which data triggered an exception
- **API development** - See request data and intermediate variables
- **Complex algorithms** - Debug issues in multi-step calculations

## Example Scripts

See the `/examples` directory for demonstration scripts:

- `enhanced_exceptions_demo.py` - Comprehensive demo
- `simple_import_test.py` - Shows automatic activation

## Logging

Enhanced exception traces are also logged to the KodeKronical logger at ERROR level, so they can be captured by your logging configuration for later analysis.

---

This feature helps you debug issues faster by providing complete context about the state of your application when exceptions occur.