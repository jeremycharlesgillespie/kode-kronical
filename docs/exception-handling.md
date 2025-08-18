# Detailed Python Exception Explanations

Kode Kronical provides enhanced exception handling that automatically captures detailed error context, including local variables, system state, and performance correlation when exceptions occur.

## Overview

When an unhandled exception occurs in your Python application, Kode Kronical automatically:

- **Captures local variables** in each stack frame
- **Records system metrics** at the time of the exception
- **Correlates with performance data** to show system load during the error
- **Provides enhanced stack traces** with variable values
- **Maintains standard Python behavior** while adding valuable debugging information

## Automatic Activation

Enhanced exception handling is **automatically enabled** when you initialize KodeKronical:

```python
from kode_kronical import KodeKronical

# This automatically enables enhanced exception handling
kode = KodeKronical()

# Any unhandled exception from this point forward will show detailed information
```

## Basic Example

### Code with Error
```python
from kode_kronical import KodeKronical
import time

kode = KodeKronical()

@kode.time_it
def process_order(order_id, customer_data, items):
    # Simulate some processing
    time.sleep(0.1)
    
    total_cost = 0
    for item in items:
        total_cost += item['price'] * item['quantity']
    
    # This will cause a division by zero error
    discount_rate = customer_data['discount'] / customer_data['orders_count']
    
    return total_cost * (1 - discount_rate)

# This call will trigger an enhanced exception
order_data = {
    'customer_id': 12345,
    'discount': 10,
    'orders_count': 0  # This causes division by zero
}

items = [
    {'name': 'Widget A', 'price': 29.99, 'quantity': 2},
    {'name': 'Widget B', 'price': 19.99, 'quantity': 1}
]

result = process_order(1001, order_data, items)
```

### Enhanced Exception Output

When the exception occurs, you'll see detailed output like this:

```
================================================================================
ENHANCED EXCEPTION TRACE WITH VARIABLES
================================================================================

Exception: ZeroDivisionError: division by zero

System Context (captured at exception time):
  CPU Usage: 15.3%
  Memory Usage: 62.1% (15.2 GB used of 24.0 GB)
  Load Average: 1.2, 1.4, 1.1
  Process Count: 247

Performance Correlation:
  Function: process_order
  Execution Time: 0.102 seconds
  Memory Delta: +2.1 MB
  CPU Delta: +12.3%

Frame #1:
  File: /path/to/your/script.py
  Function: <module>
  Line 24: result = process_order(1001, order_data, items)
  Local Variables:
    order_data = {
      'customer_id': 12345,
      'discount': 10,
      'orders_count': 0
    }
    items = [
      {'name': 'Widget A', 'price': 29.99, 'quantity': 2},
      {'name': 'Widget B', 'price': 19.99, 'quantity': 1}
    ]
    kode = <KodeKronical instance at 0x7f8b8c0d5f40>

Frame #2:
  File: /path/to/your/script.py
  Function: process_order
  Line 15: discount_rate = customer_data['discount'] / customer_data['orders_count']
  Local Variables:
    order_id = 1001
    customer_data = {
      'customer_id': 12345,
      'discount': 10,
      'orders_count': 0  # ← THE PROBLEM!
    }
    items = [
      {'name': 'Widget A', 'price': 29.99, 'quantity': 2},
      {'name': 'Widget B', 'price': 19.99, 'quantity': 1}
    ]
    total_cost = 79.97
    item = {'name': 'Widget B', 'price': 19.99, 'quantity': 1}

================================================================================
STANDARD TRACEBACK (for reference):
Traceback (most recent call last):
  File "/path/to/your/script.py", line 24, in <module>
    result = process_order(1001, order_data, items)
  File "/path/to/your/script.py", line 15, in process_order
    discount_rate = customer_data['discount'] / customer_data['orders_count']
ZeroDivisionError: division by zero
================================================================================
```

## Configuration Options

### Controlling Exception Enhancement

```python
from kode_kronical import KodeKronical

# Disable enhanced exceptions
kode = KodeKronical(config={
    'enhanced_exceptions': {
        'enabled': False
    }
})

# Or configure via YAML
```

### YAML Configuration

Create `.kode-kronical.yaml`:

```yaml
kode_kronical:
  enabled: true

enhanced_exceptions:
  enabled: true
  max_string_length: 200
  max_collection_items: 10
  show_globals: false
  exclude_private: true
  capture_system_state: true
```

### Configuration Parameters

- **`enabled`**: Enable/disable enhanced exception handling (default: `true`)
- **`max_string_length`**: Maximum characters to show for string values (default: `200`)
- **`max_collection_items`**: Maximum items to show in lists/dicts (default: `10`)
- **`show_globals`**: Include global variables in output (default: `false`)
- **`exclude_private`**: Hide variables starting with `_` (default: `true`)
- **`capture_system_state`**: Include system metrics in exception context (default: `true`)

## Advanced Examples

### Exception in Async Code

```python
import asyncio
from kode_kronical import KodeKronical

kode = KodeKronical()

@kode.time_it
async def fetch_user_data(user_id, timeout=5.0):
    await asyncio.sleep(0.1)  # Simulate API call
    
    # Simulate different error conditions
    if user_id < 0:
        raise ValueError(f"Invalid user ID: {user_id}")
    
    if user_id > 10000:
        users_cache = {}  # Empty cache
        return users_cache[user_id]  # KeyError
    
    return {"id": user_id, "name": f"User {user_id}"}

async def main():
    user_ids = [-1, 5, 15000]
    
    for uid in user_ids:
        try:
            user = await fetch_user_data(uid)
            print(f"Retrieved: {user}")
        except Exception as e:
            print(f"Error processing user {uid}: {e}")
            # Enhanced exception details are automatically captured

asyncio.run(main())
```

### Exception with Performance Context

```python
from kode_kronical import KodeKronical
import time
import random

kode = KodeKronical()

@kode.time_it
def memory_intensive_task(data_size):
    """Simulate a memory-intensive operation that might fail"""
    
    # Create large data structure
    large_data = [random.random() for _ in range(data_size)]
    
    # Simulate processing
    time.sleep(0.2)
    
    # Simulate an error condition based on system state
    import psutil
    memory_percent = psutil.virtual_memory().percent
    
    if memory_percent > 80:
        # This exception will include system metrics showing high memory usage
        raise MemoryError(f"System memory usage too high: {memory_percent}%")
    
    # Simulate another type of error
    if len(large_data) > 1000000:
        processed_data = []
        for i, value in enumerate(large_data):
            if i % 100000 == 0 and value < 0.1:
                # This will show exactly which iteration caused the issue
                raise ValueError(f"Invalid value {value} at position {i}")
            processed_data.append(value * 2)
        
        return processed_data
    
    return [x * 2 for x in large_data]

# Test with different data sizes
for size in [100, 50000, 1500000]:
    try:
        result = memory_intensive_task(size)
        print(f"Successfully processed {size} items")
    except Exception as e:
        print(f"Failed processing {size} items: {e}")
        # Enhanced exception shows:
        # - System memory usage at time of error
        # - Performance metrics for the function
        # - Local variables including 'size', 'large_data', etc.
```

### Exception in Database Operations

```python
from kode_kronical import KodeKronical
import sqlite3

kode = KodeKronical()

@kode.time_it
def process_database_query(db_path, query, params):
    """Database operation that might fail with enhanced context"""
    
    connection_info = {
        'database': db_path,
        'query_type': query.split()[0].upper(),
        'param_count': len(params)
    }
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # This might fail and show all context
        cursor.execute(query, params)
        
        if query.strip().upper().startswith('SELECT'):
            results = cursor.fetchall()
            return results
        else:
            conn.commit()
            return cursor.rowcount
            
    except sqlite3.Error as e:
        # Re-raise to trigger enhanced exception handling
        # Will show connection_info, query, params, etc.
        raise
    finally:
        if 'conn' in locals():
            conn.close()

# Test with invalid query
try:
    results = process_database_query(
        '/tmp/test.db',
        'SELECT * FROM nonexistent_table WHERE id = ?',
        [42]
    )
except Exception as e:
    print(f"Database error: {e}")
    # Enhanced output shows:
    # - connection_info with database details
    # - The exact query and parameters
    # - System state during the database operation
```

## Benefits

### 1. **Faster Debugging**
Immediately see variable values without adding print statements or using a debugger.

### 2. **Production Insights**
Get detailed error context in production environments where debugging tools aren't available.

### 3. **System Correlation**
Understand if errors are related to system resource constraints (high CPU, low memory, etc.).

### 4. **Performance Impact Analysis**
See how exceptions correlate with function performance and system load.

### 5. **Historical Context**
Exception data is stored with performance metrics for later analysis.

## Best Practices

### 1. **Enable in Development**
Always use enhanced exceptions during development for faster debugging.

### 2. **Configure for Production**
In production, consider limiting output size:

```yaml
enhanced_exceptions:
  enabled: true
  max_string_length: 100
  max_collection_items: 5
  show_globals: false
```

### 3. **Sensitive Data**
Be cautious with sensitive data in variables:

```python
# Mark sensitive variables with leading underscore
_password = "secret123"  # Won't be shown if exclude_private: true
```

### 4. **Log Integration**
Enhanced exceptions work well with logging:

```python
import logging
from kode_kronical import KodeKronical

logging.basicConfig(level=logging.ERROR)
kode = KodeKronical()

# Exceptions are automatically logged with full context
```

### 5. **Testing**
Use enhanced exceptions to improve test debugging:

```python
def test_complex_calculation():
    # If this fails, you'll see all intermediate values
    input_data = {"values": [1, 2, 3], "multiplier": 5}
    result = complex_function(input_data)
    assert result == expected_value
```

## Limitations

1. **Performance overhead**: Capturing variables has a small performance cost during exceptions
2. **Memory usage**: Large objects in scope will be displayed (configure limits appropriately)
3. **Security**: Variable values are displayed in output (consider `exclude_private` option)

## Integration with Monitoring

Enhanced exceptions integrate with Kode Kronical's performance monitoring:

- Exception timing is recorded as function performance data
- System metrics at exception time are captured
- Exception frequency can be tracked over time
- Correlation with system load patterns is available

This makes enhanced exceptions not just a debugging tool, but part of your application's observability strategy.