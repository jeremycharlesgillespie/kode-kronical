# System Monitoring Integration Guide

This document describes the data format and integration details for the system monitoring feature in kode-kronical.

## Data Format

The system monitoring data is saved as JSON with the following structure:

```json
{
  "system": [
    {
      "timestamp": 1234567890.123,
      "cpu_percent": 45.2,
      "memory_percent": 62.1,
      "memory_available_mb": 8192.5,
      "memory_used_mb": 12288.3,
      "load_avg_1m": 2.4,        // Linux only
      "load_avg_5m": 2.1,        // Linux only
      "load_avg_15m": 1.8        // Linux only
    }
  ],
  "processes": {
    "12345": [  // PID as key
      {
        "timestamp": 1234567890.123,
        "pid": 12345,
        "name": "python",
        "cpu_percent": 25.5,
        "memory_rss_mb": 128.4,
        "memory_vms_mb": 256.8,
        "num_threads": 4,
        "status": "running",
        "create_time": 1234567000.0,
        "cmdline": "python my_script.py"
      }
    ]
  },
  "metadata": {
    "platform": "Darwin",  // or "Linux", "Windows"
    "sample_interval": 0.5,
    "start_time": 1234567890.0,
    "end_time": 1234567900.0
  }
}
```

## Integration with KodeKronical Function Timings

When using `KodeKronicalSystemMonitor`, function timings are enhanced with system context:

```json
{
  "session_id": "uuid-here",
  "function_timings": [
    {
      "function_name": "my_function",
      "wall_time": 1.234,
      "cpu_time": 1.100,
      "timestamp": 1234567890.567,
      "system_context": {
        "timestamp": 1234567890.5,
        "cpu_percent": 78.5,
        "memory_percent": 45.2
      }
    }
  ],
  "system_timeline": {
    // Full system monitoring data as shown above
  }
}
```

## Usage in kode-kronical

```python
from kode_kronical import SystemMonitor, ProcessTracker

# Create monitor
monitor = SystemMonitor(
    sample_interval=0.5,  # seconds
    max_samples=3600,     # keep 1 hour of data
    data_dir="./perf_data"
)

# Start monitoring
monitor.start_monitoring()

# Track Python processes
tracker = ProcessTracker(monitor)
tracker.track_current_process()  # Current process
tracker.track_process(pid)       # Specific PID

# ... do work ...

# Stop and save
monitor.stop_monitoring()
timeline_data = monitor.get_timeline_data()
filepath = monitor.save_timeline_data("filename.json")
```

## Visualization Requirements

For the timeline visualization:

1. **System Load Background**: 
   - Light blue shaded area (#ADD8E6) 
   - Shows `cpu_percent` or `memory_percent` from system metrics
   - Y-axis: 0-100%

2. **Process Usage Foreground**:
   - Line plot overlaid on system load
   - Shows `cpu_percent` or `memory_percent` from process metrics
   - Different color (e.g., crimson #DC143C)
   - Y-axis: 0-100%

3. **X-axis**: 
   - Time based on timestamps
   - Format: HH:MM:SS or relative time

4. **Correlation**:
   - Match process metrics to system metrics by timestamp
   - Show why Python code might be slow when system is under load

## File Locations

- System monitor code: `src/kode_kronical/system_monitor.py`
- Examples: 
  - `example_system_collection.py`
  - `example_kodekronical_with_system.py`
- Output data: `./perf_data/*.json` (configurable)

## API Endpoints for Viewer

If the viewer needs to fetch data via API, consider these endpoints:

- `GET /api/system-metrics/` - Latest system metrics
- `GET /api/system-timeline/?start=<timestamp>&end=<timestamp>` - Historical data
- `GET /api/process-metrics/<pid>/` - Process-specific metrics
- `GET /api/performance-summary/<session_id>/` - Combined KodeKronical + system data