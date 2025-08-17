import time
import functools
import json
import atexit
import uuid
import os
import re
import logging
from pathlib import Path
from typing import Any, Optional, Dict, List, Callable

try:
    import boto3
    from botocore.exceptions import ClientError, NoCredentialsError
    BOTO3_AVAILABLE = True
except ImportError:
    BOTO3_AVAILABLE = False

# Import our configuration system
from .config import get_config, KodeKronicalConfig
from .daemon_client import DaemonClient, EnhancedTimingResult
from .exception_handler import enable_enhanced_exceptions, disable_enhanced_exceptions
from .failure_capture import capture_failure, log_failure


class TimingResult:
    """Stores timing information for a function call."""
    
    def __init__(self, function_name: str, wall_time: float, cpu_time: float, 
                 args: tuple = (), kwargs: dict = None):
        self.function_name = function_name
        self.wall_time = wall_time
        self.cpu_time = cpu_time
        self.args = args
        self.kwargs = kwargs or {}
        self.timestamp = time.time()


class KodeKronical:
    """Performance tracking library for Python functions with OmegaConf configuration."""
    
    def __init__(self, config_override: Optional[Dict[str, Any]] = None) -> None:
        """Initialize the KodeKronical instance.
        
        Args:
            config_override: Optional configuration overrides (will be merged with default config)
        """
        # Load configuration using OmegaConf
        self.config: KodeKronicalConfig = get_config(config_override)
        self.logger = logging.getLogger(__name__)
        
        # Initialize core state
        self.timing_results: List[TimingResult] = []
        self.session_id = str(uuid.uuid4())
        
        # Initialize daemon client for system metrics
        self.daemon_client = None
        if self.config.get("kode_kronical.enable_system_monitoring", True):
            self.daemon_client = DaemonClient()
            if self.daemon_client.is_daemon_running():
                self.logger.info("Connected to kode-kronical-daemon for system metrics")
            else:
                self.logger.debug("kode-kronical-daemon not running, system metrics disabled")
        
        # Check if KodeKronical is enabled
        if not self.config.is_enabled():
            self.logger.info("KodeKronical is disabled via configuration")
            return
        
        # Validate configuration
        try:
            issues = self.config.validate()
            if issues:
                self.logger.warning(f"Configuration issues found: {issues}")
        except Exception as e:
            capture_failure("Configuration validation", e, {
                "config_override": config_override
            })
        
        # Initialize storage backend
        self._init_storage()
        
        # Initialize enhanced exception handling if enabled
        try:
            self._init_exception_handling()
        except Exception as e:
            capture_failure("Enhanced exception handling initialization", e)
            # Continue without enhanced exceptions if it fails
        
        # Register exit handler for automatic upload
        try:
            upload_strategy = self.config.get("upload.strategy", "on_exit")
            if upload_strategy == "on_exit":
                atexit.register(self._upload_results)
        except Exception as e:
            capture_failure("Exit handler registration", e, {
                "upload_strategy": upload_strategy
            })
        
        self.logger.debug(f"KodeKronical initialized with session_id: {self.session_id}")
    
    def _init_exception_handling(self) -> None:
        """Initialize enhanced exception handling if enabled."""
        if self.config.get("kode_kronical.enable_enhanced_exceptions", True):
            max_value_length = self.config.get("kode_kronical.exception_max_value_length", 1000)
            max_collection_items = self.config.get("kode_kronical.exception_max_collection_items", 10)
            show_globals = self.config.get("kode_kronical.exception_show_globals", True)
            
            enable_enhanced_exceptions(
                max_value_length=max_value_length,
                max_collection_items=max_collection_items,
                show_globals=show_globals
            )
            self.logger.debug("Enhanced exception handling enabled")
        else:
            self.logger.debug("Enhanced exception handling disabled by configuration")
    
    def _init_storage(self) -> None:
        """Initialize storage backend (DynamoDB or local) with zero-setup fallback."""
        self.dynamodb_client = None
        self.local_storage = None
        
        try:
            if self.config.is_local_only():
                self._init_local_storage()
            else:
                # Try DynamoDB first, fall back to local if it fails
                try:
                    self._init_dynamodb()
                except Exception as e:
                    capture_failure("DynamoDB initialization", e, {
                        "fallback": "local storage",
                        "aws_config": self.config.get_aws_config() if hasattr(self.config, 'get_aws_config') else None
                    })
                    self.logger.info("Falling back to local storage due to DynamoDB initialization failure")
                    self._init_local_storage()
        except Exception as e:
            capture_failure("Storage initialization", e)
            # Continue without storage if all else fails
            self.logger.warning("KodeKronical will continue without persistent storage")
    
    def _init_local_storage(self) -> None:
        """Initialize local storage with error handling."""
        try:
            data_dir = Path(self.config.get("local.data_dir", "./perf_data"))
            data_dir.mkdir(parents=True, exist_ok=True)
            
            storage_format = self.config.get("local.format", "json")
            self.local_storage = {
                "data_dir": data_dir,
                "format": storage_format
            }
            
            self.logger.debug(f"Local storage initialized: {data_dir}")
        except Exception as e:
            capture_failure("Local storage initialization", e, {
                "data_dir": self.config.get("local.data_dir", "./perf_data"),
                "format": self.config.get("local.format", "json")
            })
            # Continue without local storage if directory creation fails
            self.local_storage = None
    
    def _init_dynamodb(self) -> None:
        """Initialize DynamoDB client with comprehensive error handling."""
        if not BOTO3_AVAILABLE:
            raise ImportError("boto3 not available - install with 'pip install boto3' or use local storage")
        
        try:
            aws_config = self.config.get_aws_config()
            region = aws_config.get("region")
            profile = aws_config.get("profile")
            
            session_kwargs = {"region_name": region}
            if profile:
                session_kwargs["profile_name"] = profile
            
            session = boto3.Session(**session_kwargs)
            self.dynamodb_client = session.client('dynamodb')
            
            # Test connection
            self.dynamodb_client.describe_table(TableName=aws_config["table_name"])
            self.logger.debug(f"DynamoDB client initialized for table: {aws_config['table_name']}")
            
        except ClientError as e:
            if e.response['Error']['Code'] == 'ResourceNotFoundException':
                if self.config.get("aws.auto_create_table", True):
                    self._create_dynamodb_table()
                else:
                    self.logger.error(f"DynamoDB table not found: {aws_config['table_name']}")
                    self.dynamodb_client = None
            else:
                self.logger.error(f"DynamoDB connection failed: {e}")
                self.dynamodb_client = None
        except Exception as e:
            self.logger.error(f"Could not initialize DynamoDB client: {e}")
            self.dynamodb_client = None
    
    def _get_normalized_hostname(self) -> str:
        """Get normalized hostname for consistent system identification."""
        from .hostname_utils import get_normalized_hostname
        return get_normalized_hostname()
    
    def _create_dynamodb_table(self) -> None:
        """Create DynamoDB table with proper schema."""
        try:
            aws_config = self.config.get_aws_config()
            table_name = aws_config["table_name"]
            
            self.dynamodb_client.create_table(
                TableName=table_name,
                KeySchema=[
                    {'AttributeName': 'id', 'KeyType': 'HASH'}
                ],
                AttributeDefinitions=[
                    {'AttributeName': 'id', 'AttributeType': 'N'}
                ],
                BillingMode='PROVISIONED',
                ProvisionedThroughput={
                    'ReadCapacityUnits': aws_config.get("read_capacity", 5),
                    'WriteCapacityUnits': aws_config.get("write_capacity", 5)
                }
            )
            
            # Wait for table to be active
            waiter = self.dynamodb_client.get_waiter('table_exists')
            waiter.wait(TableName=table_name)
            
            self.logger.info(f"Created DynamoDB table: {table_name}")
            
        except Exception as e:
            self.logger.error(f"Failed to create DynamoDB table: {e}")
            self.dynamodb_client = None
    
    def time_it(self, func: Callable = None, *, store_args: bool = None) -> Callable:
        """Decorator to time function execution.
        
        Args:
            func: Function to decorate (when used as @time_it)
            store_args: Whether to store function arguments in results (uses config default if None)
            
        Returns:
            Decorated function or decorator
        """
        def decorator(f: Callable) -> Callable:
            @functools.wraps(f)
            def wrapper(*args, **kwargs):
                # Check if KodeKronical is enabled
                if not self.config.is_enabled():
                    return f(*args, **kwargs)
                
                # Check if this function should be tracked based on filters
                if not self._should_track_function(f.__name__, f.__module__):
                    return f(*args, **kwargs)
                
                wall_start = time.perf_counter()
                cpu_start = time.process_time()
                
                try:
                    result = f(*args, **kwargs)
                finally:
                    wall_time = time.perf_counter() - wall_start
                    cpu_time = time.process_time() - cpu_start
                    
                    # Check minimum execution time threshold
                    min_time = self.config.get("kode_kronical.min_execution_time", 0.001)
                    if wall_time < min_time:
                        return result  # Return the result, don't track timing
                    
                    # Check if we should store arguments
                    should_store_args = store_args
                    if should_store_args is None:
                        should_store_args = self.config.get("filters.track_arguments", False)
                    
                    # Create enhanced timing result with potential system context
                    if self.daemon_client and self.daemon_client.is_daemon_running():
                        timing_result = EnhancedTimingResult(
                            function_name=f.__name__,
                            wall_time=wall_time,
                            cpu_time=cpu_time,
                            args=args if should_store_args else (),
                            kwargs=kwargs if should_store_args else {},
                            timestamp=wall_start + wall_time  # End time of function execution
                        )
                        # Add system context from daemon
                        timing_result.add_system_context(self.daemon_client)
                    else:
                        timing_result = TimingResult(
                            function_name=f.__name__,
                            wall_time=wall_time,
                            cpu_time=cpu_time,
                            args=args if should_store_args else (),
                            kwargs=kwargs if should_store_args else {}
                        )
                    
                    # Check max tracked calls limit
                    max_calls = self.config.get("kode_kronical.max_tracked_calls", 10000)
                    if len(self.timing_results) < max_calls:
                        self.timing_results.append(timing_result)
                    else:
                        self.logger.warning(f"Max tracked calls limit ({max_calls}) reached")
                
                return result  # Return the function result
            
            return wrapper
        
        if func is None:
            return decorator
        else:
            return decorator(func)
    
    def _should_track_function(self, func_name: str, module_name: str) -> bool:
        """Check if function should be tracked based on configuration filters."""
        
        # Check exclude modules
        exclude_modules = self.config.get("filters.exclude_modules", [])
        for pattern in exclude_modules:
            if module_name and pattern in module_name:
                return False
        
        # Check include modules (if specified, only track these)
        include_modules = self.config.get("filters.include_modules", [])
        if include_modules:
            included = False
            for pattern in include_modules:
                if module_name and pattern in module_name:
                    included = True
                    break
            if not included:
                return False
        
        # Check exclude functions
        exclude_functions = self.config.get("filters.exclude_functions", [])
        for pattern in exclude_functions:
            if re.match(pattern, func_name):
                return False
        
        # Check include functions (if specified, only track these)
        include_functions = self.config.get("filters.include_functions", [])
        if include_functions:
            included = False
            for pattern in include_functions:
                if re.match(pattern, func_name):
                    included = True
                    break
            if not included:
                return False
        
        return True
    
    def get_results(self, function_name: Optional[str] = None) -> List[TimingResult]:
        """Get timing results.
        
        Args:
            function_name: Filter by function name, or None for all results
            
        Returns:
            List of timing results
        """
        if function_name:
            return [r for r in self.timing_results if r.function_name == function_name]
        return self.timing_results.copy()
    
    def get_summary(self, function_name: Optional[str] = None) -> Dict[str, Any]:
        """Get summary statistics for timing results.
        
        Args:
            function_name: Filter by function name, or None for all results
            
        Returns:
            Dictionary with summary statistics
        """
        results = self.get_results(function_name)
        if not results:
            return {}
        
        wall_times = [r.wall_time for r in results]
        cpu_times = [r.cpu_time for r in results]
        
        return {
            'function_name': function_name or 'all_functions',
            'call_count': len(results),
            'wall_time': {
                'total': sum(wall_times),
                'average': sum(wall_times) / len(wall_times),
                'min': min(wall_times),
                'max': max(wall_times)
            },
            'cpu_time': {
                'total': sum(cpu_times),
                'average': sum(cpu_times) / len(cpu_times),
                'min': min(cpu_times),
                'max': max(cpu_times)
            }
        }
    
    def clear_results(self) -> None:
        """Clear all timing results."""
        self.timing_results.clear()
    
    def enable(self) -> None:
        """Enable timing collection."""
        self.config.set("kode_kronical.enabled", True)
    
    def disable(self) -> None:
        """Disable timing collection."""
        self.config.set("kode_kronical.enabled", False)
    
    def get_unique_function_names(self) -> List[str]:
        """Get list of unique function names that have been timed."""
        return list(set(result.function_name for result in self.timing_results))
    
    def get_functions_with_stored_args(self) -> List[str]:
        """Get list of function names that have stored arguments."""
        functions_with_args = set()
        for result in self.timing_results:
            if result.args or result.kwargs:
                functions_with_args.add(result.function_name)
        return list(functions_with_args)
    
    def build_json_results(self) -> Dict[str, Any]:
        """Build complete JSON results automatically."""
        if not self.timing_results:
            return {
                "message": "No timing data collected",
                "overall_summary": {},
                "function_summaries": {},
                "detailed_results": {}
            }
        
        results = {
            "overall_summary": self.get_summary(),
            "function_summaries": {},
            "detailed_results": {}
        }
        
        # Get summary for each function
        for func_name in self.get_unique_function_names():
            summary = self.get_summary(func_name)
            if summary:
                results["function_summaries"][func_name] = summary
        
        # Get detailed results for functions with stored arguments
        for func_name in self.get_functions_with_stored_args():
            function_results = self.get_results(func_name)
            if function_results:
                results["detailed_results"][func_name] = []
                for result in function_results:
                    results["detailed_results"][func_name].append({
                        "args": result.args,
                        "kwargs": result.kwargs,
                        "wall_time": result.wall_time,
                        "cpu_time": result.cpu_time,
                        "timestamp": result.timestamp
                    })
        
        return results
    
    def _upload_to_dynamodb(self, results: Dict[str, Any]) -> bool:
        """Upload results to DynamoDB table."""
        if not self.dynamodb_client:
            self.logger.error("DynamoDB client not available")
            return False
            
        try:
            aws_config = self.config.get_aws_config()
            table_name = aws_config["table_name"]
            
            # Generate a unique ID for this session's data
            record_id = int(time.time() * 1000000)  # microsecond timestamp as ID
            
            # Prepare the item for DynamoDB
            item = {
                'id': {'N': str(record_id)},
                'session_id': {'S': self.session_id},
                'timestamp': {'N': str(time.time())},
                'hostname': {'S': self._get_normalized_hostname()},
                'data': {'S': json.dumps(results)}
            }
            
            # Add metadata if available
            if results.get('overall_summary'):
                summary = results['overall_summary']
                item['total_calls'] = {'N': str(summary.get('call_count', 0))}
                item['total_wall_time'] = {'N': str(summary.get('wall_time', {}).get('total', 0))}
                item['total_cpu_time'] = {'N': str(summary.get('cpu_time', {}).get('total', 0))}
            
            # Upload to DynamoDB
            timeout = self.config.get("upload.timeout", 30)
            self.dynamodb_client.put_item(
                TableName=table_name,
                Item=item
            )
            
            self.logger.debug(f"Successfully uploaded timing data to DynamoDB (ID: {record_id})")
            return True
            
        except ClientError as e:
            self.logger.error(f"DynamoDB upload failed: {e.response['Error']['Message']}")
            return False
        except NoCredentialsError:
            self.logger.error("DynamoDB upload failed: AWS credentials not found")
            return False
        except Exception as e:
            self.logger.error(f"DynamoDB upload failed: {e}")
            return False
    
    def _save_to_local_storage(self, results: Dict[str, Any]) -> bool:
        """Save results to local storage."""
        if not self.local_storage:
            self.logger.error("Local storage not available")
            return False
        
        try:
            data_dir = self.local_storage["data_dir"]
            storage_format = self.local_storage["format"]
            
            # Generate filename with timestamp and session ID
            timestamp = int(time.time())
            filename = f"perf_data_{timestamp}_{self.session_id[:8]}"
            
            if storage_format == "json":
                filepath = data_dir / f"{filename}.json"
                with open(filepath, 'w') as f:
                    json.dump({
                        "id": timestamp * 1000000,
                        "session_id": self.session_id,
                        "timestamp": time.time(),
                        "hostname": self._get_normalized_hostname(),
                        "data": results
                    }, f, indent=2)
            
            elif storage_format == "csv":
                # TODO: Implement CSV format
                self.logger.warning("CSV format not yet implemented, using JSON")
                return self._save_to_local_storage({**results, "format": "json"})
            
            elif storage_format == "sqlite":
                # TODO: Implement SQLite format
                self.logger.warning("SQLite format not yet implemented, using JSON")
                return self._save_to_local_storage({**results, "format": "json"})
            
            self.logger.info(f"Successfully saved timing data to local storage: {filepath}")
            
            # Clean up old files if needed
            self._cleanup_local_storage()
            
            return True
            
        except Exception as e:
            self.logger.error(f"Local storage save failed: {e}")
            return False
    
    def _cleanup_local_storage(self) -> None:
        """Clean up old local storage files based on max_records setting."""
        try:
            max_records = self.config.get("local.max_records", 1000)
            data_dir = self.local_storage["data_dir"]
            
            # Get all perf data files
            pattern = "perf_data_*.json"
            files = list(data_dir.glob(pattern))
            
            # Sort by modification time (newest first)
            files.sort(key=lambda f: f.stat().st_mtime, reverse=True)
            
            # Remove excess files
            if len(files) > max_records:
                for f in files[max_records:]:
                    f.unlink()
                    self.logger.debug(f"Removed old performance data file: {f}")
                    
        except Exception as e:
            self.logger.warning(f"Failed to cleanup local storage: {e}")
    
    def _upload_results(self) -> None:
        """Internal method to upload results automatically based on configuration."""
        if not self.timing_results:
            return
            
        try:
            results = self.build_json_results()
            
            # Upload based on configuration
            uploaded = False
            try:
                if self.config.is_local_only() or not self.dynamodb_client:
                    uploaded = self._save_to_local_storage(results)
                else:
                    uploaded = self._upload_to_dynamodb(results)
            except Exception as e:
                capture_failure("Results upload", e, {
                    "local_only": self.config.is_local_only(),
                    "has_dynamodb_client": bool(self.dynamodb_client),
                    "results_count": len(self.timing_results)
                })
                # Try fallback storage if primary fails
                if not uploaded and self.local_storage:
                    try:
                        uploaded = self._save_to_local_storage(results)
                        self.logger.info("Used local storage fallback for results upload")
                    except Exception as fallback_error:
                        capture_failure("Fallback local storage upload", fallback_error)
            
            # Log results if debug mode is enabled
            if self.config.is_debug():
                self.logger.debug(f"Performance results: {json.dumps(results, indent=2)}")
                
        except Exception as e:
            capture_failure("Results processing", e, {
                "timing_results_count": len(self.timing_results)
            })
    
    def output_results(self) -> None:
        """Manually output/upload results based on configuration."""
        self._upload_results()
    
    def upload_to_dynamodb(self) -> bool:
        """Manually upload current results to DynamoDB."""
        if not self.timing_results:
            self.logger.info("No timing data to upload")
            return False
            
        results = self.build_json_results()
        return self._upload_to_dynamodb(results)
    
    def save_to_local_storage(self) -> bool:
        """Manually save current results to local storage."""
        if not self.timing_results:
            self.logger.info("No timing data to save")
            return False
            
        results = self.build_json_results()
        return self._save_to_local_storage(results)
    
    def get_config_info(self) -> Dict[str, Any]:
        """Get current configuration information for debugging."""
        config_info = {
            "enabled": self.config.is_enabled(),
            "debug": self.config.is_debug(),
            "local_only": self.config.is_local_only(),
            "upload_strategy": self.config.get("upload.strategy"),
            "min_execution_time": self.config.get("kode_kronical.min_execution_time"),
            "max_tracked_calls": self.config.get("kode_kronical.max_tracked_calls"),
            "storage_type": "local" if self.config.is_local_only() else "dynamodb",
            "session_id": self.session_id,
            "current_tracked_calls": len(self.timing_results)
        }
        
        # Add daemon information
        if self.daemon_client:
            daemon_status = self.daemon_client.get_daemon_status()
            config_info["daemon"] = daemon_status
        
        return config_info
    
    def get_enhanced_summary(self) -> Dict[str, Any]:
        """Get enhanced summary with system context from daemon."""
        summary = self.get_summary()
        
        if not self.daemon_client or not self.daemon_client.is_daemon_running():
            return summary
        
        # Add system metrics correlation
        enhanced_calls = []
        for result in self.timing_results:
            if hasattr(result, 'to_dict'):
                # Enhanced timing result with system context
                enhanced_calls.append(result.to_dict())
            else:
                # Regular timing result
                enhanced_calls.append({
                    'function_name': result.function_name,
                    'wall_time': result.wall_time,
                    'cpu_time': result.cpu_time,
                    'timestamp': result.timestamp,
                })
        
        summary['enhanced_calls'] = enhanced_calls
        summary['system_monitoring_enabled'] = True
        
        return summary
    
    def get_system_correlation_report(self) -> Dict[str, Any]:
        """Generate a report correlating function performance with system metrics."""
        if not self.daemon_client or not self.daemon_client.is_daemon_running():
            return {"error": "System monitoring daemon not available"}
        
        if not self.timing_results:
            return {"error": "No timing data available"}
        
        # Get time range for system metrics
        timestamps = [getattr(r, 'timestamp', 0) for r in self.timing_results]
        if not timestamps:
            return {"error": "No timestamps available"}
        
        start_time = min(timestamps)
        end_time = max(timestamps)
        
        # Get system metrics for the time range
        system_metrics = self.daemon_client.get_metrics_range(start_time, end_time)
        
        if not system_metrics:
            return {"error": "No system metrics available for time range"}
        
        # Analyze correlations
        high_cpu_functions = []
        high_memory_functions = []
        
        for result in self.timing_results:
            if hasattr(result, 'system_context') and result.system_context:
                ctx = result.system_context
                if ctx.cpu_percent > 80:  # High CPU usage
                    high_cpu_functions.append({
                        'function_name': result.function_name,
                        'wall_time': result.wall_time,
                        'cpu_percent': ctx.cpu_percent,
                        'timestamp': result.timestamp
                    })
                
                if ctx.memory_percent > 80:  # High memory usage
                    high_memory_functions.append({
                        'function_name': result.function_name,
                        'wall_time': result.wall_time,
                        'memory_percent': ctx.memory_percent,
                        'timestamp': result.timestamp
                    })
        
        return {
            'time_range': {
                'start': start_time,
                'end': end_time,
                'duration': end_time - start_time
            },
            'system_metrics_count': len(system_metrics),
            'high_cpu_functions': high_cpu_functions,
            'high_memory_functions': high_memory_functions,
            'avg_system_cpu': sum(m.cpu_percent for m in system_metrics) / len(system_metrics),
            'avg_system_memory': sum(m.memory_percent for m in system_metrics) / len(system_metrics),
            'system_monitoring_enabled': True
        }
    
    def enable_enhanced_exceptions(self, max_value_length: int = 1000, 
                                  max_collection_items: int = 10,
                                  show_globals: bool = True) -> None:
        """Manually enable enhanced exception handling with variable inspection.
        
        Args:
            max_value_length: Maximum length for string representations
            max_collection_items: Maximum items to show from collections
            show_globals: Whether to show global variables in traces
        """
        enable_enhanced_exceptions(max_value_length, max_collection_items, show_globals)
        self.logger.info("Enhanced exception handling manually enabled")
    
    def disable_enhanced_exceptions(self) -> None:
        """Manually disable enhanced exception handling."""
        disable_enhanced_exceptions()
        self.logger.info("Enhanced exception handling manually disabled")