import time
import threading
import platform
import psutil
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from collections import deque
import logging


class SystemMonitor:
    """Monitors system and process performance metrics."""
    
    def __init__(self, 
                 sample_interval: float = 1.0,
                 max_samples: int = 3600,
                 data_dir: str = "./perf_data"):
        """
        Initialize the system monitor.
        
        Args:
            sample_interval: Time in seconds between samples
            max_samples: Maximum number of samples to keep in memory
            data_dir: Directory to store performance data
        """
        self.sample_interval = sample_interval
        self.max_samples = max_samples
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # Data storage
        self.system_metrics = deque(maxlen=max_samples)
        self.process_metrics = {}  # pid -> deque of metrics
        
        # Monitoring state
        self.monitoring = False
        self.monitor_thread = None
        self.tracked_pids = set()
        
        # Platform info
        self.platform = platform.system()
        self.logger = logging.getLogger(__name__)
        
    def start_monitoring(self):
        """Start the monitoring thread."""
        if self.monitoring:
            return
            
        self.monitoring = True
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()
        self.logger.info("System monitoring started")
        
    def stop_monitoring(self):
        """Stop the monitoring thread."""
        self.monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=self.sample_interval * 2)
        self.logger.info("System monitoring stopped")
        
    def track_process(self, pid: int):
        """Add a process to track by PID."""
        self.tracked_pids.add(pid)
        if pid not in self.process_metrics:
            self.process_metrics[pid] = deque(maxlen=self.max_samples)
        self.logger.info(f"Tracking process PID: {pid}")
        
    def untrack_process(self, pid: int):
        """Remove a process from tracking."""
        self.tracked_pids.discard(pid)
        self.logger.info(f"Untracked process PID: {pid}")
        
    def _monitor_loop(self):
        """Main monitoring loop."""
        while self.monitoring:
            try:
                timestamp = time.time()
                
                # Collect system metrics
                system_data = self._collect_system_metrics(timestamp)
                self.system_metrics.append(system_data)
                
                # Collect process metrics
                for pid in list(self.tracked_pids):
                    try:
                        process_data = self._collect_process_metrics(pid, timestamp)
                        if process_data:
                            self.process_metrics[pid].append(process_data)
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        self.logger.warning(f"Process {pid} no longer accessible")
                        self.tracked_pids.discard(pid)
                        
                # Sleep until next sample
                time.sleep(self.sample_interval)
                
            except Exception as e:
                self.logger.error(f"Error in monitoring loop: {e}")
                time.sleep(self.sample_interval)
                
    def _collect_system_metrics(self, timestamp: float) -> Dict:
        """Collect system-wide metrics."""
        cpu_percent = psutil.cpu_percent(interval=None)
        memory = psutil.virtual_memory()
        
        metrics = {
            "timestamp": timestamp,
            "cpu_percent": cpu_percent,
            "memory_percent": memory.percent,
            "memory_available_mb": memory.available / (1024 * 1024),
            "memory_used_mb": memory.used / (1024 * 1024),
        }
        
        # Platform-specific metrics
        if self.platform == "Linux":
            try:
                load_avg = psutil.getloadavg()
                metrics["load_avg_1m"] = load_avg[0]
                metrics["load_avg_5m"] = load_avg[1]
                metrics["load_avg_15m"] = load_avg[2]
            except AttributeError:
                pass
                
        return metrics
        
    def _collect_process_metrics(self, pid: int, timestamp: float) -> Optional[Dict]:
        """Collect metrics for a specific process."""
        try:
            process = psutil.Process(pid)
            
            # Get process info
            with process.oneshot():
                cpu_percent = process.cpu_percent(interval=None)
                memory_info = process.memory_info()
                
                metrics = {
                    "timestamp": timestamp,
                    "pid": pid,
                    "name": process.name(),
                    "cpu_percent": cpu_percent,
                    "memory_rss_mb": memory_info.rss / (1024 * 1024),
                    "memory_vms_mb": memory_info.vms / (1024 * 1024),
                    "num_threads": process.num_threads(),
                    "status": process.status(),
                }
                
                # Try to get additional info
                try:
                    metrics["create_time"] = process.create_time()
                    metrics["cmdline"] = " ".join(process.cmdline())
                except (psutil.AccessDenied, psutil.NoSuchProcess):
                    pass
                    
            return metrics
            
        except (psutil.NoSuchProcess, psutil.AccessDenied) as e:
            self.logger.debug(f"Cannot access process {pid}: {e}")
            return None
            
    def get_timeline_data(self, 
                         start_time: Optional[float] = None,
                         end_time: Optional[float] = None) -> Dict:
        """
        Get timeline data for visualization.
        
        Args:
            start_time: Start timestamp (uses all data if None)
            end_time: End timestamp (uses current time if None)
            
        Returns:
            Dictionary with system and process timeline data
        """
        if end_time is None:
            end_time = time.time()
            
        # Filter system metrics
        system_data = []
        for metric in self.system_metrics:
            ts = metric["timestamp"]
            if start_time and ts < start_time:
                continue
            if ts > end_time:
                break
            system_data.append(metric)
            
        # Filter process metrics
        process_data = {}
        for pid, metrics in self.process_metrics.items():
            filtered = []
            for metric in metrics:
                ts = metric["timestamp"]
                if start_time and ts < start_time:
                    continue
                if ts > end_time:
                    break
                filtered.append(metric)
            if filtered:
                process_data[pid] = filtered
                
        return {
            "system": system_data,
            "processes": process_data,
            "metadata": {
                "platform": self.platform,
                "sample_interval": self.sample_interval,
                "start_time": start_time or (system_data[0]["timestamp"] if system_data else None),
                "end_time": end_time,
            }
        }
        
    def save_timeline_data(self, filename: Optional[str] = None) -> str:
        """Save timeline data to a JSON file."""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"timeline_{timestamp}.json"
            
        filepath = self.data_dir / filename
        data = self.get_timeline_data()
        
        with open(filepath, "w") as f:
            json.dump(data, f, indent=2)
            
        self.logger.info(f"Saved timeline data to {filepath}")
        return str(filepath)
        
    def get_current_metrics(self) -> Dict:
        """Get the most recent metrics."""
        result = {
            "system": self.system_metrics[-1] if self.system_metrics else None,
            "processes": {}
        }
        
        for pid, metrics in self.process_metrics.items():
            if metrics:
                result["processes"][pid] = metrics[-1]
                
        return result


class ProcessTracker:
    """Helper class to track Python processes automatically."""
    
    def __init__(self, monitor: SystemMonitor):
        self.monitor = monitor
        self.current_pid = os.getpid()
        
    def track_current_process(self):
        """Track the current Python process."""
        self.monitor.track_process(self.current_pid)
        
    def track_python_processes(self):
        """Find and track all Python processes."""
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                # Check if it's a Python process
                if proc.info['name'] and 'python' in proc.info['name'].lower():
                    self.monitor.track_process(proc.info['pid'])
                elif proc.info['cmdline']:
                    cmdline = ' '.join(proc.info['cmdline'])
                    if 'python' in cmdline.lower():
                        self.monitor.track_process(proc.info['pid'])
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass


# Integration with KodeKronical
class KodeKronicalSystemMonitor:
    """Helper class to integrate system monitoring with KodeKronical timing results."""
    
    def __init__(self, pyperf_instance, monitor: SystemMonitor):
        self.pyperf = pyperf_instance
        self.monitor = monitor
        self._original_timing_results = []
        
    def enhance_timing_results(self):
        """
        Enhance KodeKronical timing results with system context.
        
        This correlates KodeKronical timing data with system metrics based on timestamps.
        """
        if not hasattr(self.pyperf, 'timing_results'):
            return
            
        timeline_data = self.monitor.get_timeline_data()
        system_metrics = timeline_data.get("system", [])
        
        if not system_metrics:
            return
            
        # Create a map of timestamps to system metrics for efficient lookup
        system_map = {m["timestamp"]: m for m in system_metrics}
        
        # Enhance each timing result with system context
        for timing_result in self.pyperf.timing_results:
            if hasattr(timing_result, 'timestamp'):
                # Find closest system metric
                closest_time = min(system_map.keys(), 
                                 key=lambda t: abs(t - timing_result.timestamp))
                
                if abs(closest_time - timing_result.timestamp) < 1.0:  # Within 1 second
                    timing_result.system_context = system_map[closest_time]
                    
    def get_performance_summary(self) -> Dict:
        """
        Get a summary combining KodeKronical timing data with system metrics.
        
        Returns a dictionary with correlated performance data.
        """
        self.enhance_timing_results()
        
        summary = {
            "session_id": getattr(self.pyperf, 'session_id', None),
            "function_timings": [],
            "system_timeline": self.monitor.get_timeline_data()
        }
        
        if hasattr(self.pyperf, 'timing_results'):
            for result in self.pyperf.timing_results:
                entry = {
                    "function_name": result.function_name,
                    "wall_time": result.wall_time,
                    "cpu_time": result.cpu_time,
                    "timestamp": result.timestamp
                }
                
                if hasattr(result, 'system_context'):
                    entry["system_context"] = result.system_context
                    
                summary["function_timings"].append(entry)
                
        return summary