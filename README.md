# Kode Kronical

High-performance Python library for automated performance monitoring and system metrics collection.

## Overview

Kode Kronical provides automated performance monitoring for Python applications with:

- **Function Performance Tracking**: Automatic timing and profiling of Python functions
- **System Metrics Collection**: Real-time CPU, memory, and process monitoring  
- **Enhanced Exception Handling**: Detailed error context with system correlation
- **AWS Integration**: Automatic DynamoDB uploads with 30-day TTL
- **Web Dashboard**: Comprehensive visualization via kode-kronical-viewer
- **Zero Configuration**: Works out-of-the-box with sensible defaults

## Installation

```bash
pip install kode-kronical
```

## Quick Start

### 1. Basic Usage

```python
from kode_kronical import KodeKronical
import time

# Initialize the performance tracker
kode = KodeKronical()

# Use as decorator
@kode.time_it
def slow_function(n):
    time.sleep(0.1)
    return sum(range(n))

@kode.time_it(store_args=True)
def process_data(data, multiplier=2):
    return [x * multiplier for x in data]

# Call your functions - performance data is automatically collected
result1 = slow_function(1000)
result2 = process_data([1, 2, 3, 4, 5])
```

### 2. Configuration (Optional)

Create a `.kode-kronical.yaml` file in your project directory:

```yaml
kode_kronical:
  enabled: true
  min_execution_time: 0.001

local:
  enabled: true
  data_dir: "./perf_data"

filters:
  exclude_modules:
    - "requests"
    - "boto3"
```

### 3. View Results

**Automatic Data Collection:**
- **Local Mode**: Performance data saved to `./perf_data/` as JSON files
- **AWS Mode**: Data uploaded to DynamoDB on program exit

**Web Dashboard:**
Use the [kode-kronical-viewer](https://github.com/jeremycharlesgillespie/kode-kronical-viewer) for visualization:
- Performance overview and metrics
- Function-by-function analysis  
- Historical trends and comparisons
- System correlation analysis

## Key Features

### Enhanced Exception Handling
Kode Kronical captures detailed error context including system state when exceptions occur. See [Exception Handling Guide](docs/exception-handling.md) for examples and configuration.

### System Monitoring Daemon
Background daemon for continuous system monitoring that correlates with application performance. See [Daemon Guide](docs/daemon-guide.md) for complete setup and troubleshooting.

### AWS Integration
Automatic upload to DynamoDB with optimized schema:
- 1-minute data intervals for production efficiency
- 30-day TTL for automatic cleanup
- Real-time dashboard updates

## API Summary

```python
from kode_kronical import KodeKronical

kode = KodeKronical()

# Decorator usage
@kode.time_it                           # Basic timing
@kode.time_it(store_args=True)         # Store function arguments
@kode.time_it(tags=["critical"])       # Add custom tags

# Programmatic access
summary = kode.get_summary()            # Get performance summary
results = kode.get_timing_results()     # Get detailed results
config = kode.get_config_info()         # Get configuration info
```

## REST API

When using with kode-kronical-viewer, these endpoints are available:

- `GET /api/performance/` - Performance data with filtering
- `GET /api/hostnames/` - Available hostnames
- `GET /api/functions/` - Function analysis data

## Documentation

- **[Daemon Guide](docs/daemon-guide.md)** - Complete system monitoring setup and troubleshooting
- **[Exception Handling Guide](docs/exception-handling.md)** - Enhanced error context and debugging
- **[AWS Setup Guide](docs/aws-setup.md)** - DynamoDB configuration and deployment

## License

MIT License - see LICENSE file for details.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests: `pytest tests/`
5. Submit a pull request

## Support

- [GitHub Issues](https://github.com/jeremycharlesgillespie/kode-kronical/issues)
- [Documentation](https://github.com/jeremycharlesgillespie/kode-kronical)