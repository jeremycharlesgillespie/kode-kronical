"""
Failure capture system that provides detailed context for errors and failures.
Uses similar formatting to the enhanced exception handler.
"""

import sys
import traceback
import inspect
import time
from typing import Any, Dict, List, Optional, Type
import logging

logger = logging.getLogger(__name__)


class FailureCapture:
    """Captures and formats detailed failure information with context."""
    
    def __init__(self, max_value_length: int = 1000, max_collection_items: int = 10):
        """
        Initialize the failure capture system.
        
        Args:
            max_value_length: Maximum length for string representations
            max_collection_items: Maximum items to show from collections
        """
        self.max_value_length = max_value_length
        self.max_collection_items = max_collection_items
        self.failures = []
    
    def format_value(self, value: Any) -> str:
        """
        Format a value for display, handling various types safely.
        Uses same logic as exception handler for consistency.
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
            
            # Handle objects with __dict__
            if hasattr(value, '__dict__'):
                class_name = value.__class__.__name__
                try:
                    attrs = vars(value)
                    if len(attrs) > 3:  # Limit attribute display for failures
                        attr_str = ', '.join(f'{k}=...' for k in list(attrs.keys())[:3])
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
            try:
                return f'<{type(value).__name__} object (error formatting: {e})>'
            except:
                return '<unknown object>'
    
    def get_current_context(self) -> Dict[str, Any]:
        """Get context from the current call frame."""
        try:
            # Get the caller's frame (skip this method and capture_failure)
            frame = inspect.currentframe().f_back.f_back
            
            context = {
                'function': getattr(frame, 'f_code', {}).co_name if frame else '<unknown>',
                'filename': getattr(frame, 'f_code', {}).co_filename if frame else '<unknown>',
                'line_number': frame.f_lineno if frame else 0,
                'local_vars': {},
                'timestamp': time.time()
            }
            
            if frame and frame.f_locals:
                # Get local variables, excluding internal ones
                excluded_vars = {'__builtins__', '__cached__', '__file__', '__loader__', 
                               '__name__', '__package__', '__spec__', '__doc__'}
                
                for var_name, var_value in frame.f_locals.items():
                    if var_name not in excluded_vars and not var_name.startswith('_'):
                        try:
                            context['local_vars'][var_name] = self.format_value(var_value)
                        except Exception as e:
                            context['local_vars'][var_name] = f'<error getting value: {e}>'
            
            return context
            
        except Exception as e:
            logger.warning(f"Error getting current context: {e}")
            return {
                'function': '<unknown>',
                'filename': '<unknown>',
                'line_number': 0,
                'local_vars': {},
                'timestamp': time.time()
            }
    
    def capture_failure(self, operation: str, error: Exception, 
                       additional_context: Optional[Dict[str, Any]] = None) -> str:
        """
        Capture a failure with detailed context and formatting.
        
        Args:
            operation: Description of what was being attempted
            error: The exception that occurred
            additional_context: Additional context information
            
        Returns:
            Formatted failure report string
        """
        try:
            # Get current context
            context = self.get_current_context()
            
            # Build failure report
            output = []
            output.append("=" * 80)
            output.append("FAILURE CAPTURED")
            output.append("=" * 80)
            output.append("")
            
            # What failed
            output.append(f"[OPERATION] {operation}")
            output.append(f"[ERROR TYPE] {type(error).__name__}")
            output.append(f"[ERROR MESSAGE] {str(error)}")
            output.append("")
            
            # Where it failed
            output.append(f"[LOCATION]:")
            output.append(f"  Function: {context['function']}")
            output.append(f"  File: {context['filename']}")
            output.append(f"  Line: {context['line_number']}")
            output.append("")
            
            # Context variables
            if context['local_vars']:
                output.append("[LOCAL VARIABLES]:")
                for var_name in sorted(context['local_vars'].keys()):
                    var_value = context['local_vars'][var_name]
                    output.append(f"  {var_name} = {var_value}")
                output.append("")
            
            # Additional context if provided
            if additional_context:
                output.append("[ADDITIONAL CONTEXT]:")
                for key, value in additional_context.items():
                    formatted_value = self.format_value(value)
                    output.append(f"  {key} = {formatted_value}")
                output.append("")
            
            # Timestamp
            output.append(f"[TIMESTAMP] {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(context['timestamp']))}")
            output.append("")
            
            # Brief summary
            output.append("=" * 80)
            output.append("BRIEF SUMMARY")
            output.append("=" * 80)
            output.append(f"[OPERATION FAILED] {operation}")
            output.append("")
            output.append(f"[ERROR] {type(error).__name__}")
            output.append(f"[EXPLANATION] {self._explain_error(error)}")
            output.append("")
            output.append(f"[LOCATION] {context['function']}() in {context['filename']}:{context['line_number']}")
            output.append("")
            output.append("[NOTE] This failure was captured for debugging purposes.")
            output.append("   The operation will continue with fallback behavior.")
            output.append("=" * 80)
            
            failure_report = '\n'.join(output)
            
            # Store the failure
            self.failures.append({
                'operation': operation,
                'error': error,
                'context': context,
                'additional_context': additional_context,
                'timestamp': context['timestamp'],
                'report': failure_report
            })
            
            return failure_report
            
        except Exception as e:
            # Fallback if failure capture itself fails
            simple_report = f"FAILURE CAPTURE ERROR: Could not capture failure for '{operation}': {e}\nOriginal error: {error}"
            logger.error(simple_report)
            return simple_report
    
    def _explain_error(self, error: Exception) -> str:
        """Provide plain-language explanation of the error."""
        error_type = type(error).__name__
        error_message = str(error)
        
        explanations = {
            'ConnectionError': 'Could not connect to the service or database.',
            'TimeoutError': 'The operation took too long and was cancelled.',
            'FileNotFoundError': 'A required file or resource could not be found.',
            'PermissionError': 'Permission was denied to access a file or resource.',
            'ImportError': 'A required Python module could not be imported.',
            'ModuleNotFoundError': 'A required Python module is not installed.',
            'ValueError': 'An invalid value was provided.',
            'TypeError': 'Incompatible data types were used together.',
            'KeyError': 'A required key was not found in a dictionary.',
            'AttributeError': 'An object does not have the expected property or method.',
            'NameError': 'A variable or function name was not recognized.',
            'OSError': 'An operating system error occurred.',
            'RuntimeError': 'A runtime error occurred during execution.',
        }
        
        base_explanation = explanations.get(error_type, f'An unexpected {error_type} error occurred.')
        
        # Add specific context for common errors
        if 'connection' in error_message.lower():
            base_explanation += ' Check your network connection and service availability.'
        elif 'not found' in error_message.lower():
            base_explanation += ' Verify that all required files and resources exist.'
        elif 'permission' in error_message.lower():
            base_explanation += ' Check file permissions and access rights.'
        elif 'timeout' in error_message.lower():
            base_explanation += ' The service may be slow or unavailable.'
            
        return base_explanation
    
    def get_failure_count(self) -> int:
        """Get the total number of captured failures."""
        return len(self.failures)
    
    def get_recent_failures(self, count: int = 5) -> List[Dict[str, Any]]:
        """Get the most recent failures."""
        return self.failures[-count:] if self.failures else []
    
    def clear_failures(self) -> None:
        """Clear all captured failures."""
        self.failures.clear()
    
    def log_failure(self, operation: str, error: Exception, 
                   additional_context: Optional[Dict[str, Any]] = None,
                   log_level: int = logging.WARNING) -> str:
        """
        Capture failure and log it.
        
        Args:
            operation: Description of what was being attempted
            error: The exception that occurred
            additional_context: Additional context information
            log_level: Logging level to use
            
        Returns:
            Formatted failure report string
        """
        failure_report = self.capture_failure(operation, error, additional_context)
        logger.log(log_level, f"Captured failure in {operation}:\n{failure_report}")
        return failure_report


# Global failure capture instance
_failure_capture = FailureCapture()


def capture_failure(operation: str, error: Exception, 
                   additional_context: Optional[Dict[str, Any]] = None,
                   print_to_stderr: bool = True) -> str:
    """
    Convenience function to capture a failure with detailed context.
    
    Args:
        operation: Description of what was being attempted
        error: The exception that occurred
        additional_context: Additional context information
        print_to_stderr: Whether to print the report to stderr
        
    Returns:
        Formatted failure report string
    """
    failure_report = _failure_capture.capture_failure(operation, error, additional_context)
    
    if print_to_stderr:
        print(failure_report, file=sys.stderr)
    
    return failure_report


def log_failure(operation: str, error: Exception, 
               additional_context: Optional[Dict[str, Any]] = None,
               log_level: int = logging.WARNING) -> str:
    """
    Convenience function to capture and log a failure.
    
    Args:
        operation: Description of what was being attempted
        error: The exception that occurred
        additional_context: Additional context information
        log_level: Logging level to use
        
    Returns:
        Formatted failure report string
    """
    return _failure_capture.log_failure(operation, error, additional_context, log_level)


def get_failure_stats() -> Dict[str, Any]:
    """Get statistics about captured failures."""
    return {
        'total_failures': _failure_capture.get_failure_count(),
        'recent_failures': _failure_capture.get_recent_failures(3)
    }