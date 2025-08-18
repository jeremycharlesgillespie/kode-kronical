"""
Daemon client for kode-kronical to communicate with the system monitoring daemon.
"""

import json
import time
import glob
import logging
from pathlib import Path
from typing import Optional, Dict, List, Any
from dataclasses import dataclass


@dataclass
class SystemMetrics:
    """System metrics data structure."""
    timestamp: float
    cpu_percent: float
    memory_percent: float
    memory_available_mb: float
    memory_used_mb: float
    load_avg_1m: Optional[float] = None
    load_avg_5m: Optional[float] = None
    load_avg_15m: Optional[float] = None
    network: Optional[Dict[str, Any]] = None


class DaemonClient:
    """Client for communicating with kode-kronical-daemon."""
    
    def __init__(self, data_dir: Optional[str] = None):
        """Initialize daemon client.
        
        Args:
            data_dir: Directory where daemon stores data files.
                     Defaults to /var/lib/kode-kronical or ~/.kode-kronical/data
        """
        self.logger = logging.getLogger(__name__)
        
        # Default data directories to check
        if data_dir:
            self.data_dirs = [Path(data_dir)]
        else:
            self.data_dirs = [
                Path('/var/lib/kode-kronical'),
                Path.home() / '.local' / 'share' / 'kode-kronical',  # New standard location
                Path.home() / '.kode-kronical' / 'data',  # Legacy location
                Path('./perf_data'),  # Fallback for development
            ]
        
        self.active_data_dir = self._find_active_data_dir()
        
    def _find_active_data_dir(self) -> Optional[Path]:
        """Find the active data directory with daemon data."""
        for data_dir in self.data_dirs:
            if data_dir.exists() and list(data_dir.glob('metrics_*.json')):
                self.logger.debug(f"Found daemon data in: {data_dir}")
                return data_dir
        
        self.logger.debug("No daemon data found in any directory")
        return None
    
    def is_daemon_running(self) -> bool:
        """Check if the daemon is running by looking for recent data."""
        if not self.active_data_dir:
            return False
        
        # Look for recent data files (within last 5 minutes)
        cutoff_time = time.time() - 300  # 5 minutes ago
        
        for metrics_file in self.active_data_dir.glob('metrics_*.json'):
            if metrics_file.stat().st_mtime > cutoff_time:
                return True
        
        return False
    
    def get_latest_metrics(self) -> Optional[SystemMetrics]:
        """Get the most recent system metrics from daemon data."""
        if not self.active_data_dir:
            return None
        
        # Find the most recent metrics file
        metrics_files = sorted(
            self.active_data_dir.glob('metrics_*.json'),
            key=lambda f: f.stat().st_mtime,
            reverse=True
        )
        
        if not metrics_files:
            return None
        
        try:
            with open(metrics_files[0], 'r') as f:
                data = json.load(f)
            
            # Get the latest system metric from the file
            if data and isinstance(data, list) and data[-1].get('system'):
                system_data = data[-1]['system']
                return SystemMetrics(
                    timestamp=system_data['timestamp'],
                    cpu_percent=system_data['cpu_percent'],
                    memory_percent=system_data['memory_percent'],
                    memory_available_mb=system_data['memory_available_mb'],
                    memory_used_mb=system_data['memory_used_mb'],
                    load_avg_1m=system_data.get('load_avg_1m'),
                    load_avg_5m=system_data.get('load_avg_5m'),
                    load_avg_15m=system_data.get('load_avg_15m'),
                    network=data[-1].get('network')
                )
        except Exception as e:
            self.logger.error(f"Failed to read daemon metrics: {e}")
        
        return None
    
    def get_metrics_at_time(self, timestamp: float, tolerance: float = 2.0) -> Optional[SystemMetrics]:
        """Get system metrics closest to a specific timestamp.
        
        Args:
            timestamp: Target timestamp
            tolerance: Maximum time difference in seconds
        
        Returns:
            SystemMetrics object or None if no suitable metrics found
        """
        if not self.active_data_dir:
            return None
        
        best_match = None
        best_diff = float('inf')
        
        # Search through recent metrics files
        for metrics_file in self.active_data_dir.glob('metrics_*.json'):
            try:
                with open(metrics_file, 'r') as f:
                    data = json.load(f)
                
                if not data or not isinstance(data, list):
                    continue
                
                for entry in data:
                    if not entry.get('system'):
                        continue
                    
                    system_data = entry['system']
                    entry_time = system_data['timestamp']
                    time_diff = abs(entry_time - timestamp)
                    
                    if time_diff < best_diff and time_diff <= tolerance:
                        best_diff = time_diff
                        best_match = SystemMetrics(
                            timestamp=system_data['timestamp'],
                            cpu_percent=system_data['cpu_percent'],
                            memory_percent=system_data['memory_percent'],
                            memory_available_mb=system_data['memory_available_mb'],
                            memory_used_mb=system_data['memory_used_mb'],
                            load_avg_1m=system_data.get('load_avg_1m'),
                            load_avg_5m=system_data.get('load_avg_5m'),
                            load_avg_15m=system_data.get('load_avg_15m'),
                            network=entry.get('network')
                        )
            except Exception as e:
                self.logger.debug(f"Error reading {metrics_file}: {e}")
                continue
        
        return best_match
    
    def get_metrics_range(self, start_time: float, end_time: float) -> List[SystemMetrics]:
        """Get system metrics within a time range.
        
        Args:
            start_time: Start timestamp
            end_time: End timestamp
        
        Returns:
            List of SystemMetrics objects
        """
        if not self.active_data_dir:
            return []
        
        metrics = []
        
        for metrics_file in self.active_data_dir.glob('metrics_*.json'):
            try:
                with open(metrics_file, 'r') as f:
                    data = json.load(f)
                
                if not data or not isinstance(data, list):
                    continue
                
                for entry in data:
                    if not entry.get('system'):
                        continue
                    
                    system_data = entry['system']
                    entry_time = system_data['timestamp']
                    
                    if start_time <= entry_time <= end_time:
                        metrics.append(SystemMetrics(
                            timestamp=system_data['timestamp'],
                            cpu_percent=system_data['cpu_percent'],
                            memory_percent=system_data['memory_percent'],
                            memory_available_mb=system_data['memory_available_mb'],
                            memory_used_mb=system_data['memory_used_mb'],
                            load_avg_1m=system_data.get('load_avg_1m'),
                            load_avg_5m=system_data.get('load_avg_5m'),
                            load_avg_15m=system_data.get('load_avg_15m'),
                            network=entry.get('network')
                        ))
            except Exception as e:
                self.logger.debug(f"Error reading {metrics_file}: {e}")
                continue
        
        # Sort by timestamp
        return sorted(metrics, key=lambda m: m.timestamp)
    
    def get_daemon_status(self) -> Dict[str, Any]:
        """Get daemon status information.
        
        Returns:
            Dictionary with daemon status information
        """
        status = {
            'running': self.is_daemon_running(),
            'data_directory': str(self.active_data_dir) if self.active_data_dir else None,
            'last_update': None,
            'metrics_files_count': 0,
        }
        
        if self.active_data_dir:
            metrics_files = list(self.active_data_dir.glob('metrics_*.json'))
            status['metrics_files_count'] = len(metrics_files)
            
            if metrics_files:
                latest_file = max(metrics_files, key=lambda f: f.stat().st_mtime)
                status['last_update'] = latest_file.stat().st_mtime
        
        return status


class EnhancedTimingResult:
    """Enhanced timing result with system context from daemon."""
    
    def __init__(self, function_name: str, wall_time: float, cpu_time: float,
                 args: tuple = (), kwargs: dict = None, timestamp: float = None):
        self.function_name = function_name
        self.wall_time = wall_time
        self.cpu_time = cpu_time
        self.args = args
        self.kwargs = kwargs or {}
        self.timestamp = timestamp or time.time()
        self.system_context: Optional[SystemMetrics] = None
        
    def add_system_context(self, daemon_client: DaemonClient):
        """Add system context from daemon data."""
        self.system_context = daemon_client.get_metrics_at_time(self.timestamp)
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        result = {
            'function_name': self.function_name,
            'wall_time': self.wall_time,
            'cpu_time': self.cpu_time,
            'timestamp': self.timestamp,
            'args': self.args if self.args else None,
            'kwargs': self.kwargs if self.kwargs else None,
        }
        
        if self.system_context:
            result['system_context'] = {
                'timestamp': self.system_context.timestamp,
                'cpu_percent': self.system_context.cpu_percent,
                'memory_percent': self.system_context.memory_percent,
                'memory_available_mb': self.system_context.memory_available_mb,
                'memory_used_mb': self.system_context.memory_used_mb,
                'load_avg_1m': self.system_context.load_avg_1m,
                'load_avg_5m': self.system_context.load_avg_5m,
                'load_avg_15m': self.system_context.load_avg_15m,
                'network': self.system_context.network,
            }
        
        return result