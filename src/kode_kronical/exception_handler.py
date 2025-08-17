"""
Enhanced exception handler that captures full stack traces with variable values.
"""

import sys
import traceback
import inspect
import types
from typing import Any, Dict, List, Optional, Type
import logging

logger = logging.getLogger(__name__)


class EnhancedExceptionHandler:
    """Handles unhandled exceptions with detailed variable inspection."""
    
    def __init__(self, max_value_length: int = 1000, max_collection_items: int = 10, 
                 show_globals: bool = True):
        """
        Initialize the exception handler.
        
        Args:
            max_value_length: Maximum length for string representations of values
            max_collection_items: Maximum number of items to show from collections
            show_globals: Whether to show global variables in traces
        """
        self.max_value_length = max_value_length
        self.max_collection_items = max_collection_items
        self.show_globals = show_globals
        self.original_excepthook = None
        self.enabled = False
    
    def format_value(self, value: Any) -> str:
        """
        Format a value for display, handling various types safely.
        
        Args:
            value: The value to format
            
        Returns:
            String representation of the value
        """
        try:
            # Handle None
            if value is None:
                return 'None'
            
            # Handle basic types
            if isinstance(value, (int, float, bool)):
                return str(value)
            
            # Handle strings
            if isinstance(value, str):
                if len(value) > self.max_value_length:
                    return f'"{value[:self.max_value_length]}..." (truncated, {len(value)} chars total)'
                return f'"{value}"'
            
            # Handle bytes
            if isinstance(value, bytes):
                if len(value) > 100:
                    return f'<bytes, length={len(value)}>'
                try:
                    return f'b{value!r}'
                except:
                    return f'<bytes, length={len(value)}>'
            
            # Handle lists and tuples
            if isinstance(value, (list, tuple)):
                type_name = 'list' if isinstance(value, list) else 'tuple'
                if len(value) == 0:
                    return f'<empty {type_name}>'
                elif len(value) > self.max_collection_items:
                    items = [self.format_value(v) for v in value[:self.max_collection_items]]
                    return f'[{", ".join(items)}, ... ({len(value)} items total)]'
                else:
                    items = [self.format_value(v) for v in value]
                    if isinstance(value, tuple):
                        return f'({", ".join(items)})'
                    return f'[{", ".join(items)}]'
            
            # Handle dictionaries
            if isinstance(value, dict):
                if len(value) == 0:
                    return '<empty dict>'
                elif len(value) > self.max_collection_items:
                    items = []
                    for i, (k, v) in enumerate(value.items()):
                        if i >= self.max_collection_items:
                            break
                        items.append(f'{self.format_value(k)}: {self.format_value(v)}')
                    return f'{{{", ".join(items)}, ... ({len(value)} items total)}}'
                else:
                    items = [f'{self.format_value(k)}: {self.format_value(v)}' for k, v in value.items()]
                    return f'{{{", ".join(items)}}}'
            
            # Handle sets
            if isinstance(value, set):
                if len(value) == 0:
                    return '<empty set>'
                elif len(value) > self.max_collection_items:
                    items = [self.format_value(v) for v in list(value)[:self.max_collection_items]]
                    return f'{{{", ".join(items)}, ... ({len(value)} items total)}}'
                else:
                    items = [self.format_value(v) for v in value]
                    return f'{{{", ".join(items)}}}'
            
            # Handle functions and methods
            if callable(value):
                if inspect.isfunction(value) or inspect.ismethod(value):
                    return f'<function {value.__name__}>'
                elif inspect.isclass(value):
                    return f'<class {value.__name__}>'
                else:
                    return f'<callable {type(value).__name__}>'
            
            # Handle modules
            if isinstance(value, types.ModuleType):
                return f'<module {value.__name__}>'
            
            # Handle objects with __dict__
            if hasattr(value, '__dict__'):
                class_name = value.__class__.__name__
                try:
                    attrs = vars(value)
                    if len(attrs) > 5:  # Limit attribute display
                        attr_str = ', '.join(f'{k}=...' for k in list(attrs.keys())[:5])
                        return f'<{class_name} object with {attr_str}, ... ({len(attrs)} attrs total)>'
                    else:
                        attr_str = ', '.join(f'{k}={self.format_value(v)}' for k, v in attrs.items())
                        return f'<{class_name} object with {attr_str}>'
                except:
                    return f'<{class_name} object>'
            
            # Default representation
            str_repr = str(value)
            if len(str_repr) > self.max_value_length:
                return f'{str_repr[:self.max_value_length]}... (truncated)'
            return str_repr
            
        except Exception as e:
            # If all else fails, return a safe representation
            try:
                return f'<{type(value).__name__} object (error formatting: {e})>'
            except:
                return '<unknown object>'
    
    def get_frame_locals(self, frame) -> Dict[str, str]:
        """
        Get local variables from a frame, formatted safely.
        
        Args:
            frame: The frame object
            
        Returns:
            Dictionary of variable names to formatted values
        """
        local_vars = {}
        
        try:
            # Get frame locals
            frame_locals = frame.f_locals.copy()
            
            # Remove some internal variables that are not useful
            excluded_vars = {'__builtins__', '__cached__', '__file__', '__loader__', 
                           '__name__', '__package__', '__spec__', '__doc__'}
            
            for var_name, var_value in frame_locals.items():
                if var_name not in excluded_vars:
                    try:
                        local_vars[var_name] = self.format_value(var_value)
                    except Exception as e:
                        local_vars[var_name] = f'<error getting value: {e}>'
                        
        except Exception as e:
            logger.warning(f"Error getting frame locals: {e}")
            
        return local_vars
    
    def get_frame_globals(self, frame) -> Dict[str, str]:
        """
        Get global variables from a frame, formatted safely.
        
        Args:
            frame: The frame object
            
        Returns:
            Dictionary of global variable names to formatted values
        """
        global_vars = {}
        
        try:
            # Get frame globals
            frame_globals = frame.f_globals.copy()
            
            # Remove built-in and module-level variables that are not useful
            excluded_vars = {
                '__builtins__', '__cached__', '__file__', '__loader__', 
                '__name__', '__package__', '__spec__', '__doc__', '__annotations__',
                '__path__', '__version__', '__author__', '__email__'
            }
            
            # Also exclude imported modules and functions that are likely imports
            import_indicators = {'import', 'from', 'module', 'function', 'class'}
            
            for var_name, var_value in frame_globals.items():
                # Skip excluded variables
                if var_name in excluded_vars:
                    continue
                    
                # Skip variables that start with underscore (usually private/internal)
                if var_name.startswith('_'):
                    continue
                
                # Skip if it's a module (common import)
                if hasattr(var_value, '__file__') and hasattr(var_value, '__name__'):
                    continue
                    
                # Skip if it's the same as a local variable (avoid duplication)
                if var_name in frame.f_locals:
                    continue
                
                try:
                    global_vars[var_name] = self.format_value(var_value)
                except Exception as e:
                    global_vars[var_name] = f'<error getting value: {e}>'
                        
        except Exception as e:
            logger.warning(f"Error getting frame globals: {e}")
            
        return global_vars
    
    def format_traceback_with_variables(self, exc_type: Type[BaseException], 
                                       exc_value: BaseException, 
                                       exc_traceback: traceback) -> str:
        """
        Format a traceback with local variables for each frame.
        
        Args:
            exc_type: Exception type
            exc_value: Exception value
            exc_traceback: Traceback object
            
        Returns:
            Formatted string with full traceback and variables
        """
        output = []
        output.append("=" * 80)
        output.append("ENHANCED EXCEPTION TRACE WITH VARIABLES")
        output.append("=" * 80)
        output.append("")
        
        # Get the traceback frames
        tb_frames = []
        tb = exc_traceback
        while tb is not None:
            tb_frames.append(tb.tb_frame)
            tb = tb.tb_next
        
        # Format each frame
        for i, frame in enumerate(tb_frames):
            # Get frame info
            frame_info = inspect.getframeinfo(frame)
            filename = frame_info.filename
            line_num = frame_info.lineno
            func_name = frame_info.function
            
            output.append(f"Function Call #{i + 1}:")
            output.append(f"  File: {filename}")
            output.append(f"  Function: {func_name}")
            output.append(f"  Line {line_num}: {frame_info.code_context[0].strip() if frame_info.code_context else 'N/A'}")
            
            # Get local variables
            local_vars = self.get_frame_locals(frame)
            
            if local_vars:
                output.append("  Local Variables:")
                # Sort variables for consistent output
                for var_name in sorted(local_vars.keys()):
                    var_value = local_vars[var_name]
                    output.append(f"    {var_name} = {var_value}")
            else:
                output.append("  Local Variables: <none>")
            
            # Get global variables if enabled
            if self.show_globals:
                global_vars = self.get_frame_globals(frame)
                
                if global_vars:
                    output.append("  Global Variables:")
                    # Sort variables for consistent output
                    for var_name in sorted(global_vars.keys()):
                        var_value = global_vars[var_name]
                        output.append(f"    {var_name} = {var_value}")
                else:
                    output.append("  Global Variables: <none>")
            
            output.append("")
        
        # Add the exception details
        output.append("-" * 80)
        output.append(f"Exception Type: {exc_type.__name__}")
        output.append(f"Exception Value: {exc_value}")
        output.append("-" * 80)
        
        # Add the standard traceback at the end for reference
        output.append("")
        output.append("Standard Traceback:")
        output.append("-" * 40)
        tb_lines = traceback.format_exception(exc_type, exc_value, exc_traceback)
        output.extend(line.rstrip() for line in tb_lines)
        
        # Add plain-language summary
        output.append("")
        output.append("=" * 80)
        output.append("BRIEF SUMMARY")
        output.append("=" * 80)
        
        summary = self._generate_plain_summary(exc_type, exc_value, tb_frames)
        output.extend(summary)
        
        output.append("=" * 80)
        
        return '\n'.join(output)
    
    def _generate_plain_summary(self, exc_type: Type[BaseException], 
                               exc_value: BaseException, 
                               tb_frames: List) -> List[str]:
        """Generate a plain-language summary of the exception."""
        summary = []
        
        try:
            # Get the failing frame (last frame where the exception occurred)
            if not tb_frames:
                summary.append("[ERROR] The code crashed, but no detailed information is available.")
                return summary
            
            failing_frame = tb_frames[-1]
            frame_info = inspect.getframeinfo(failing_frame)
            
            # Get basic info
            filename = frame_info.filename
            line_num = frame_info.lineno
            func_name = frame_info.function
            code_line = frame_info.code_context[0].strip() if frame_info.code_context else "N/A"
            
            # Start summary
            summary.append(f"[STATUS] THE CODE FAILED")
            summary.append("")
            
            # Where it failed
            if func_name == "<module>":
                summary.append(f"[LOCATION] Line {line_num} in the main script")
            else:
                summary.append(f"[LOCATION] Line {line_num} in function '{func_name}'")
            
            summary.append(f"[FILE] {filename}")
            summary.append("")
            
            # What failed
            summary.append(f"[ERROR TYPE] {exc_type.__name__}")
            
            # Explain common error types in plain language
            error_explanation = self._explain_error_type(exc_type.__name__, str(exc_value))
            summary.append(f"[EXPLANATION] {error_explanation}")
            summary.append("")
            
            # The problematic code
            summary.append(f"[CODE] The problematic code line:")
            summary.append(f"   {code_line}")
            summary.append("")
            
            # Show all local variables
            local_vars = self.get_frame_locals(failing_frame)
            if local_vars:
                summary.append("[VARIABLES] All local variables:")
                
                # Show ALL local variables, sorted alphabetically
                for var_name, var_value in sorted(local_vars.items()):
                    summary.append(f"   - {var_name} = {var_value}")
                summary.append("")
            
            # Add suggestion for next steps
            summary.append("[SUGGESTION] To fix this:")
            suggestion = self._get_fix_suggestion(exc_type.__name__, code_line, local_vars)
            summary.append(f"   {suggestion}")
            summary.append("")
            
            # Add call chain if there are multiple frames
            if len(tb_frames) > 1:
                summary.append("[CALL CHAIN] How we got here:")
                for i, frame in enumerate(tb_frames):
                    frame_info = inspect.getframeinfo(frame)
                    func_name = frame_info.function
                    if func_name == "<module>":
                        summary.append(f"   {i+1}. Started running the script")
                    else:
                        summary.append(f"   {i+1}. Called function '{func_name}'")
                summary.append("")
                
        except Exception as e:
            summary.append(f"[ERROR] The code failed with a {exc_type.__name__} error.")
            summary.append(f"[MESSAGE] Error message: {exc_value}")
            summary.append(f"[WARNING] Could not generate detailed summary: {e}")
        
        return summary
    
    def _explain_error_type(self, error_type: str, error_message: str) -> str:
        """Explain common error types in plain language, including library-specific errors."""
        
        # Check for library-specific errors first
        library_explanation = self._get_library_specific_explanation(error_type, error_message)
        if library_explanation:
            return library_explanation
        
        # Standard Python error explanations
        explanations = {
            'TypeError': 'You tried to use two different types of data together in a way that doesn\'t work (like adding text to a number).',
            'ZeroDivisionError': 'You tried to divide a number by zero, which is mathematically impossible.',
            'NameError': 'You used a variable or function name that Python doesn\'t recognize.',
            'AttributeError': 'You tried to use a method or property that doesn\'t exist on this type of object.',
            'IndexError': 'You tried to access an item in a list using a position that doesn\'t exist.',
            'KeyError': 'You tried to access a dictionary key that doesn\'t exist.',
            'ValueError': 'You provided a value that has the right type but an inappropriate value.',
            'FileNotFoundError': 'Python couldn\'t find a file you\'re trying to open or access.',
            'ImportError': 'Python couldn\'t import a module or package you\'re trying to use.',
            'IndentationError': 'Your code has incorrect spacing/indentation.',
            'SyntaxError': 'Your code has a grammar/syntax error that Python can\'t understand.',
            'ConnectionError': 'There was a problem connecting to a remote service or database.',
            'TimeoutError': 'An operation took too long and was cancelled.',
            'PermissionError': 'You don\'t have permission to access this file or resource.',
            'OSError': 'The operating system reported an error (usually file or network related).',
            'RuntimeError': 'Something went wrong during program execution.',
            'RecursionError': 'A function called itself too many times, creating an infinite loop.',
            'MemoryError': 'Your program ran out of memory.',
            'KeyboardInterrupt': 'The program was stopped by pressing Ctrl+C.',
            'UnicodeError': 'There was a problem with text encoding/decoding.',
            'AssertionError': 'A condition that was expected to be true turned out to be false.',
            'StopIteration': 'An iterator ran out of items to process.',
            'SystemExit': 'The program is trying to exit.',
            'GeneratorExit': 'A generator function was closed before finishing.',
            'NotImplementedError': 'This feature hasn\'t been implemented yet.',
            'OverflowError': 'A number became too large for Python to handle.',
            'UnboundLocalError': 'You tried to use a local variable before giving it a value.',
            'ReferenceError': 'An object was deleted while still being referenced.',
            'BufferError': 'There was a problem with a buffer object.',
            'ArithmeticError': 'There was a mathematical calculation error.',
            'LookupError': 'There was a problem looking up a value (like in a list or dictionary).',
            'EnvironmentError': 'There was a problem with the system environment.',
            'EOFError': 'The program tried to read input but reached the end of the file.',
            'FloatingPointError': 'There was an error in floating point calculation.',
            'Warning': 'This is a warning message, not necessarily an error.'
        }
        
        explanation = explanations.get(error_type, f'Something went wrong in your code ({error_type}).')
        
        # Add specific details for some common cases
        if error_type == 'TypeError' and 'unsupported operand' in error_message:
            if '/' in error_message:
                explanation += ' Specifically, you tried to divide two incompatible types.'
            elif '+' in error_message:
                explanation += ' Specifically, you tried to add two incompatible types.'
            elif '*' in error_message:
                explanation += ' Specifically, you tried to multiply two incompatible types.'
            elif '-' in error_message:
                explanation += ' Specifically, you tried to subtract two incompatible types.'
        
        elif error_type == 'ValueError':
            if 'invalid literal' in error_message:
                explanation += ' You tried to convert text to a number, but the text doesn\'t represent a valid number.'
            elif 'not enough values to unpack' in error_message:
                explanation += ' You tried to assign multiple variables from something that doesn\'t have enough values.'
            elif 'too many values to unpack' in error_message:
                explanation += ' You tried to assign variables from something that has too many values.'
        
        elif error_type == 'AttributeError':
            if '\'NoneType\'' in error_message:
                explanation += ' This often happens when a function returns None instead of an expected object.'
        
        elif error_type == 'ImportError':
            if 'No module named' in error_message:
                explanation += ' Make sure the module is installed (try: pip install module-name).'
        
        elif error_type == 'FileNotFoundError':
            explanation += ' Check that the file path is correct and the file exists.'
        
        elif error_type == 'KeyError':
            explanation += ' Check that the key exists in the dictionary before accessing it.'
        
        elif error_type == 'IndexError':
            explanation += ' Make sure the index is within the valid range for your list/array.'
        
        return explanation
    
    def _get_library_specific_explanation(self, error_type: str, error_message: str) -> Optional[str]:
        """Get library-specific error explanations."""
        
        # Python-oracledb errors (detect by keywords or ORA- error codes)
        if (any(keyword in error_message.lower() for keyword in ['oracledb', 'oracle', 'cx_oracle']) or
            'ora-' in error_message.lower() or 'tns:' in error_message.lower()):
            return self._explain_oracledb_error(error_type, error_message)
        
        # Requests library errors
        if any(keyword in error_message.lower() for keyword in ['requests', 'urllib', 'http']):
            return self._explain_requests_error(error_type, error_message)
        
        # Pandas library errors
        if any(keyword in error_message.lower() for keyword in ['pandas', 'dataframe', 'series']):
            return self._explain_pandas_error(error_type, error_message)
        
        # NumPy library errors
        if any(keyword in error_message.lower() for keyword in ['numpy', 'ndarray', 'array']):
            return self._explain_numpy_error(error_type, error_message)
        
        # SQL-related errors (general)
        if any(keyword in error_message.lower() for keyword in ['sql', 'database', 'cursor', 'connection']):
            return self._explain_sql_error(error_type, error_message)
        
        # JSON errors
        if any(keyword in error_message.lower() for keyword in ['json', 'decode', 'expecting']):
            return self._explain_json_error(error_type, error_message)
        
        # File/IO errors
        if any(keyword in error_message.lower() for keyword in ['file', 'directory', 'path']):
            return self._explain_file_error(error_type, error_message)
        
        return None  # No library-specific explanation found
    
    def _explain_oracledb_error(self, error_type: str, error_message: str) -> str:
        """Explain Oracle database specific errors."""
        
        # ORA- error codes (most common Oracle errors)
        if 'ORA-00001' in error_message:
            return 'Unique constraint violation: You\'re trying to insert a duplicate value into a column that must be unique (like a primary key).'
        
        elif 'ORA-00904' in error_message:
            return 'Invalid identifier: You\'re referencing a column or table name that doesn\'t exist in the database.'
        
        elif 'ORA-00933' in error_message:
            return 'SQL command not properly ended: Your SQL statement has a syntax error, usually missing semicolon or incorrect SQL structure.'
        
        elif 'ORA-00942' in error_message:
            return 'Table or view does not exist: The table/view you\'re trying to access doesn\'t exist or you don\'t have permission to access it.'
        
        elif 'ORA-01017' in error_message:
            return 'Invalid username/password: Your database credentials are incorrect.'
        
        elif 'ORA-01031' in error_message:
            return 'Insufficient privileges: Your database user doesn\'t have permission to perform this operation.'
        
        elif 'ORA-01400' in error_message:
            return 'Cannot insert NULL into column: You\'re trying to insert a NULL value into a column that requires a value.'
        
        elif 'ORA-01722' in error_message:
            return 'Invalid number: You\'re trying to convert text to a number, but the text doesn\'t represent a valid number.'
        
        elif 'ORA-01843' in error_message:
            return 'Not a valid month: There\'s an error in date formatting or an invalid date value.'
        
        elif 'ORA-12154' in error_message:
            return 'TNS:could not resolve the connect identifier: The database connection string (TNS name) is not found or configured incorrectly.'
        
        elif 'ORA-12541' in error_message:
            return 'TNS:no listener: The database listener is not running, or you\'re trying to connect to the wrong host/port.'
        
        elif 'ORA-12545' in error_message:
            return 'Connect failed because target host or object does not exist: The database server hostname is wrong or the server is not accessible.'
        
        elif 'ORA-28000' in error_message:
            return 'Account is locked: Your database user account has been locked due to too many failed login attempts.'
        
        # Connection-related errors
        elif error_type == 'ConnectionError' or 'connection' in error_message.lower():
            return 'Database connection failed: Check your connection string, database server status, and network connectivity.'
        
        elif error_type == 'TimeoutError' or 'timeout' in error_message.lower():
            return 'Database operation timed out: The query took too long to execute. Try optimizing your query or increasing the timeout.'
        
        elif 'cursor' in error_message.lower():
            return 'Database cursor error: There\'s a problem with executing or fetching results from your SQL query.'
        
        elif 'transaction' in error_message.lower():
            return 'Database transaction error: There\'s a problem with committing or rolling back your database changes.'
        
        # General Oracle/database errors
        elif error_type in ['DatabaseError', 'IntegrityError', 'OperationalError']:
            return f'Oracle database error: {error_message}. Check your SQL syntax, data constraints, and database connectivity.'
        
        else:
            return f'Oracle database error: {error_message}. This is likely related to SQL syntax, data constraints, or connectivity issues.'
    
    def _explain_requests_error(self, error_type: str, error_message: str) -> str:
        """Explain HTTP/requests library errors."""
        
        if 'ConnectionError' in error_type or 'connection' in error_message.lower():
            return 'Network connection failed: Cannot reach the server. Check your internet connection and the URL.'
        
        elif 'Timeout' in error_type or 'timeout' in error_message.lower():
            return 'Request timed out: The server took too long to respond. Try increasing the timeout or check if the server is overloaded.'
        
        elif 'HTTPError' in error_type or any(code in error_message for code in ['400', '401', '403', '404', '500']):
            return 'HTTP error: The server returned an error status. Check the URL and your request parameters.'
        
        elif 'SSLError' in error_type or 'ssl' in error_message.lower():
            return 'SSL/HTTPS error: There\'s a problem with the secure connection. The server\'s SSL certificate might be invalid.'
        
        else:
            return 'HTTP request error: There was a problem making the web request. Check the URL and your internet connection.'
    
    def _explain_pandas_error(self, error_type: str, error_message: str) -> str:
        """Explain pandas library errors."""
        
        if 'KeyError' in error_type and any(word in error_message for word in ['column', 'key']):
            return 'Pandas KeyError: You\'re trying to access a column that doesn\'t exist in your DataFrame. Check the column names.'
        
        elif 'ValueError' in error_type and 'length' in error_message:
            return 'Pandas length mismatch: You\'re trying to assign data of different lengths. Make sure arrays/lists have the same size.'
        
        elif 'TypeError' in error_type and 'dataframe' in error_message.lower():
            return 'Pandas type error: You\'re using the wrong data type with a DataFrame operation. Check your data types.'
        
        else:
            return 'Pandas error: There\'s a problem with your data manipulation. Check your DataFrame structure and the operation you\'re trying to perform.'
    
    def _explain_numpy_error(self, error_type: str, error_message: str) -> str:
        """Explain NumPy library errors."""
        
        if 'ValueError' in error_type and 'shape' in error_message:
            return 'NumPy shape error: Your arrays have incompatible shapes for this operation. Check the dimensions of your arrays.'
        
        elif 'IndexError' in error_type:
            return 'NumPy index error: You\'re trying to access an array element that doesn\'t exist. Check your array bounds.'
        
        elif 'TypeError' in error_type and 'array' in error_message:
            return 'NumPy type error: There\'s a data type incompatibility with your array operation.'
        
        else:
            return 'NumPy error: There\'s a problem with your array operations. Check array shapes, data types, and indices.'
    
    def _explain_sql_error(self, error_type: str, error_message: str) -> str:
        """Explain general SQL/database errors."""
        
        if 'syntax' in error_message.lower():
            return 'SQL syntax error: Your SQL query has incorrect syntax. Check for typos, missing commas, or incorrect keywords.'
        
        elif 'permission' in error_message.lower() or 'privilege' in error_message.lower():
            return 'Database permission error: You don\'t have the required permissions to perform this database operation.'
        
        elif 'connection' in error_message.lower():
            return 'Database connection error: Cannot connect to the database. Check connection settings and database availability.'
        
        else:
            return 'Database error: There\'s a problem with your database operation. Check your SQL syntax and database connectivity.'
    
    def _explain_json_error(self, error_type: str, error_message: str) -> str:
        """Explain JSON parsing errors."""
        
        if 'JSONDecodeError' in error_type or 'decode' in error_message:
            return 'JSON parsing error: The text you\'re trying to parse is not valid JSON format. Check for missing quotes, commas, or brackets.'
        
        elif 'expecting' in error_message.lower():
            return 'JSON format error: The JSON structure is incomplete or malformed. Check that all brackets and quotes are properly closed.'
        
        else:
            return 'JSON error: There\'s a problem parsing JSON data. Make sure the data is in correct JSON format.'
    
    def _explain_file_error(self, error_type: str, error_message: str) -> str:
        """Explain file and path related errors."""
        
        if 'FileNotFoundError' in error_type:
            return 'File not found: The file you\'re trying to access doesn\'t exist. Check the file path and make sure the file is in the correct location.'
        
        elif 'PermissionError' in error_type:
            return 'File permission error: You don\'t have permission to access this file. Check file permissions or run as administrator.'
        
        elif 'IsADirectoryError' in error_type:
            return 'Directory error: You\'re trying to open a directory as if it were a file. Make sure you\'re pointing to a file, not a folder.'
        
        elif 'OSError' in error_type and 'path' in error_message:
            return 'Path error: There\'s a problem with the file path. Check that the path is correct and accessible.'
        
        else:
            return 'File system error: There\'s a problem accessing files or directories. Check paths and permissions.'
    
    def _find_variables_in_code(self, code_line: str, local_vars: Dict[str, str]) -> Dict[str, str]:
        """Find variables from local_vars that appear in the code line."""
        variables_in_line = {}
        
        # Simple approach: check if variable names appear in the code line
        for var_name in local_vars:
            # Skip very short variable names to avoid false matches
            if len(var_name) < 2:
                continue
                
            # Check if variable name appears as a word boundary in the code
            import re
            if re.search(r'\b' + re.escape(var_name) + r'\b', code_line):
                variables_in_line[var_name] = local_vars[var_name]
        
        return variables_in_line
    
    def _get_fix_suggestion(self, error_type: str, code_line: str, local_vars: Dict[str, str]) -> str:
        """Provide a helpful suggestion for fixing the error."""
        suggestions = {
            'TypeError': 'Check that you\'re using compatible data types. Convert between types if needed (e.g., str() to make text, int() to make numbers).',
            'ZeroDivisionError': 'Make sure the value you\'re dividing by is not zero. Add a check like "if divisor != 0:" before dividing.',
            'NameError': 'Check the spelling of your variable or function name. Make sure it\'s defined before you use it.',
            'AttributeError': 'Check that the object has the method or property you\'re trying to use. Use dir(object) to see available options.',
            'IndexError': 'Check that your list index is within the valid range. Lists start at 0 and end at len(list)-1.',
            'KeyError': 'Check that the dictionary key exists. Use dict.get(key) or "key in dict" to check first.',
            'ValueError': 'Check that the value you\'re providing is in the expected format or range.',
            'FileNotFoundError': 'Check that the file path is correct and the file exists.',
            'ImportError': 'Make sure the module is installed and the import name is correct.'
        }
        
        base_suggestion = suggestions.get(error_type, 'Review the error message and check your code logic.')
        
        # Add specific suggestions based on the code
        if error_type == 'TypeError' and '/' in code_line:
            base_suggestion += ' In this case, make sure both values can be divided (both should be numbers).'
        elif error_type == 'ZeroDivisionError':
            base_suggestion += ' In this case, check why the divisor became zero.'
            
        return base_suggestion
    
    def exception_hook(self, exc_type: Type[BaseException], 
                      exc_value: BaseException, 
                      exc_traceback: traceback) -> None:
        """
        Custom exception hook that prints detailed information.
        
        Args:
            exc_type: Exception type
            exc_value: Exception value
            exc_traceback: Traceback object
        """
        # Skip KeyboardInterrupt to allow clean exit
        if issubclass(exc_type, KeyboardInterrupt):
            if self.original_excepthook:
                self.original_excepthook(exc_type, exc_value, exc_traceback)
            else:
                sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return
        
        try:
            # Format and print the enhanced traceback
            enhanced_tb = self.format_traceback_with_variables(exc_type, exc_value, exc_traceback)
            print(enhanced_tb, file=sys.stderr)
            
        except Exception as e:
            # If there's an error in our handler, fall back to default
            print(f"Error in enhanced exception handler: {e}", file=sys.stderr)
            if self.original_excepthook:
                self.original_excepthook(exc_type, exc_value, exc_traceback)
            else:
                sys.__excepthook__(exc_type, exc_value, exc_traceback)
    
    def enable(self) -> None:
        """Enable the enhanced exception handler."""
        if not self.enabled:
            self.original_excepthook = sys.excepthook
            sys.excepthook = self.exception_hook
            self.enabled = True
            logger.debug("Enhanced exception handler enabled")
    
    def disable(self) -> None:
        """Disable the enhanced exception handler and restore the original."""
        if self.enabled and self.original_excepthook:
            sys.excepthook = self.original_excepthook
            self.enabled = False
            logger.debug("Enhanced exception handler disabled")


# Global instance
_handler = EnhancedExceptionHandler()


def enable_enhanced_exceptions(max_value_length: int = 1000, 
                              max_collection_items: int = 10,
                              show_globals: bool = True) -> None:
    """
    Enable enhanced exception handling with variable inspection.
    
    Args:
        max_value_length: Maximum length for string representations
        max_collection_items: Maximum items to show from collections
        show_globals: Whether to show global variables in traces
    """
    global _handler
    _handler.max_value_length = max_value_length
    _handler.max_collection_items = max_collection_items
    _handler.show_globals = show_globals
    _handler.enable()


def disable_enhanced_exceptions() -> None:
    """Disable enhanced exception handling."""
    global _handler
    _handler.disable()