# Kode Kronical

High-performance Python library for automated performance monitoring and system metrics collection.

## Overview

Kode Kronical provides automated performance monitoring for Python applications with:

- **Function Performance Tracking**: Automatic timing and profiling of Python functions
- **System Metrics Collection**: Real-time CPU, memory, and process monitoring  
- **1-minute Data Intervals**: Optimized for production with efficient 1-minute sampling
- **AWS Integration**: Automatic DynamoDB uploads with 30-day TTL
- **Web Dashboard**: Comprehensive visualization via kode-kronical-viewer
- **Zero Configuration**: Works out-of-the-box with sensible defaults

## Quick Start

### 1. Create Configuration File

Create a `.kode-kronical.yaml` file in your project directory:

```yaml
kode_kronical:
  enabled: true
  min_execution_time: 0.001

local:
  enabled: true
  data_dir: "./perf_data"
  format: "json"

filters:
  exclude_modules:
    - "requests"
    - "boto3"
```

### 2. Use in Your Code

```python
from kode_kronical import KodeKronical
import time

# Initialize the performance tracker (loads .kode-kronical.yaml automatically)
perf = KodeKronical()

# Method 1: Use as decorator
@perf.time_it
def slow_function(n):
    time.sleep(0.1)
    return sum(range(n))

# Method 2: Use as decorator with arguments
@perf.time_it(store_args=True)
def process_data(data, multiplier=2):
    return [x * multiplier for x in data]

# Call your functions
result1 = slow_function(1000)
result2 = process_data([1, 2, 3, 4, 5])

# Performance data is automatically collected and uploaded
# - Local mode: Saved to ./perf_data/ as JSON files
# - AWS mode: Uploaded to DynamoDB on program exit
# - View data using the web dashboard at http://localhost:8000

# Optional: Get timing results programmatically
summary = perf.get_summary()
print(f"Tracked {summary['call_count']} function calls")
```

### 3. View Results

**Automatic Data Collection:**
- **Local Mode**: Performance data is automatically saved to `./perf_data/` as JSON files
- **AWS Mode**: Data is automatically uploaded to DynamoDB when your program exits

**Web Dashboard:**
For visualizing performance data, use the separate [kode-kronical-viewer](https://github.com/jeremycharlesgillespie/kode-kronical-viewer) Django dashboard that provides:
- Performance overview and metrics
- Function-by-function analysis  
- Historical trends and comparisons
- Advanced filtering and search

For AWS integration and production setup, see the Configuration section below.


## Building and Publishing

This project includes automated scripts for building and publishing the package with automatic version incrementing.

### Quick Build & Upload

```bash
# Build and upload in one step (recommended)
./upload_package.sh
```

This script will:
- Automatically increment the version (0.1.4 → 0.1.5)
- Build the package
- Validate the package
- Give you options to upload to Test PyPI or Production PyPI
- Use your configured API tokens from `.pypirc`

### Build Only

```bash
# Just build the package (increments version)
python3 build_package.py
```

This script will:
- Automatically increment the version
- Clean previous builds
- Build both wheel and source distribution
- Validate the package

### Manual Build (Advanced)

```bash
# Traditional manual build (no version increment)
python -m build

# Manual upload to PyPI
pip install twine
twine upload dist/*
```

### Version Management

- **Automatic**: Both scripts automatically increment version by 0.01 each run
- **Current version**: Check with `python3 -c "from version_manager import get_current_version; print(get_current_version())"`
- **Manual increment**: Run `python3 version_manager.py`

### PyPI Configuration

Create a `.pypirc` file in the project root with your API tokens:

```ini
[distutils]
index-servers =
    pypi
    testpypi

[pypi]
username = __token__
password = your-pypi-api-token

[testpypi]
repository = https://test.pypi.org/legacy/
username = __token__
password = your-testpypi-api-token
```

### Testing Your Package

Test on Test PyPI first (recommended):
1. Run `./upload_package.sh` and choose option 1 (Test PyPI)
2. Install and test: `pip install --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple/ kode-kronical`
3. If everything works, upload to production PyPI


# Kode Kronical

This library is used to track and represent the performance of Python code that is executed via an easy to install and configure Python library.

## Installation

```bash
pip install kode-kronical
```

## Development

### Setup Development Environment

```bash
# Clone the repository
git clone https://github.com/jeremycharlesgillespie/kode-kronical.git
cd kode-kronical

# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate  # On macOS/Linux
# or
venv\Scripts\activate     # On Windows

# Install dependencies
pip install -r requirements.txt

# For development (includes testing tools)
pip install -r requirements-dev.txt

# Install pre-commit hooks (optional)
pre-commit install
```

## Configuration

KodeKronical uses YAML configuration files for flexible and easy setup. Configuration sources are loaded in priority order:

1. **Default configuration** (built-in defaults)
2. **User configuration files** (`.kode-kronical.yaml`, `kode-kronical.yaml`)
3. **Runtime overrides** (passed to KodeKronical constructor)

### Quick Start - Local Mode (No AWS Required)

Create a `.kode-kronical.yaml` file in your project directory:

```yaml
kode_kronical:
  enabled: true
  debug: false
  min_execution_time: 0.001

local:
  enabled: true  # Use local storage, no AWS required
  data_dir: "./perf_data"
  format: "json"
  max_records: 1000

filters:
  exclude_modules:
    - "boto3"
    - "requests"
    - "urllib3"
  track_arguments: false
```

### AWS DynamoDB Mode

For production AWS usage:

```yaml
kode_kronical:
  enabled: true
  min_execution_time: 0.001

aws:
  region: "us-east-1"
  table_name: "kode-kronical-data"
  auto_create_table: true

upload:
  strategy: "on_exit"  # on_exit, real_time, batch, manual

local:
  enabled: false  # Disable local storage
```

### Advanced Configuration

See `.kode-kronical.yaml.example` for all configuration options including:

- **Performance filtering** (modules, functions, execution time thresholds)
- **Upload strategies** (real-time, batch, manual)
- **Logging configuration**
- **Dashboard settings**

### Runtime Configuration

You can also configure KodeKronical programmatically:

```python
from kode_kronical import KodeKronical

# Local-only mode
perf = KodeKronical({
    "local": {"enabled": True},
    "kode_kronical": {"debug": True}
})

# AWS mode with custom settings
perf = KodeKronical({
    "aws": {
        "region": "us-east-1",
        "table_name": "my-perf-data"
    },
    "local": {"enabled": False}
})
```

### Configuration File Locations

KodeKronical searches for configuration files in this order:

1. `./kode-kronical.yaml` (current directory)
2. `./.kode-kronical.yaml` (current directory, hidden file)
3. `~/.kode-kronical.yaml` (home directory)
4. `~/.config/kode-kronical/config.yaml` (XDG config directory)

### AWS Setup

For AWS mode:
1. Configure AWS CLI: `aws configure`
2. Create your `.kode-kronical.yaml` with AWS settings
3. KodeKronical will automatically create DynamoDB tables if needed

See `AWS_SETUP.md` for detailed AWS configuration instructions.

### Virtual Environment Usage

Always activate the virtual environment before running KodeKronical:

```bash
# Activate virtual environment
source venv/bin/activate

# Run your KodeKronical application
python3 tester.py

# Deactivate when done
deactivate
```

## Web Dashboard

For a comprehensive web dashboard to visualize and analyze your kode-kronical performance data, use the separate [kode-kronical-viewer](https://github.com/jeremycharlesgillespie/kode-kronical-viewer) project.

### kode-kronical-viewer Features

- **Performance Overview**: Key metrics, slowest functions, most active hosts
- **Advanced Filtering**: Filter by hostname, date range, function name, session ID
- **Sorting**: Sort records by timestamp, hostname, total calls, wall time, etc.
- **Function Analysis**: Detailed performance analysis for specific functions
- **REST API**: Programmatic access to performance data
- **Real-time Data**: Automatically displays latest performance data from DynamoDB

### Installation

```bash
# Install the dashboard separately
pip install kode-kronical-viewer

# Or clone and run the standalone project
git clone https://github.com/jeremycharlesgillespie/kode-kronical-viewer
cd kode-kronical-viewer
pip install -r requirements.txt
python start_viewer.py
```

Visit the [kode-kronical-viewer repository](https://github.com/jeremycharlesgillespie/kode-kronical-viewer) for detailed setup and usage instructions.

### Dashboard Screenshots

Here's what you can expect when using the kode-kronical-viewer web dashboard to visualize your kode-kronical performance data:

#### Main Dashboard Overview
![Dashboard Home](https://raw.githubusercontent.com/jeremycharlesgillespie/kode-kronical-viewer/main/screenshots/01_dashboard_home.png)
*Complete performance overview with key metrics, slowest functions, and recent activity*

#### Performance Records Browser
![Performance Records](https://raw.githubusercontent.com/jeremycharlesgillespie/kode-kronical-viewer/main/screenshots/02_performance_records.png)
*Browse and filter all performance records with advanced search capabilities*

#### Detailed Record Analysis
![Record Detail](https://raw.githubusercontent.com/jeremycharlesgillespie/kode-kronical-viewer/main/screenshots/03_record_detail.png)
*Detailed breakdown of individual performance records showing function-level metrics*

#### Function Performance Analysis
![Function Analysis](https://raw.githubusercontent.com/jeremycharlesgillespie/kode-kronical-viewer/main/screenshots/04_function_analysis.png)
*Cross-record analysis of specific functions with performance trends over time*

### REST API Endpoints

The dashboard also provides JSON API endpoints for programmatic access:

#### Performance Metrics API
`GET /api/metrics/` - Summary performance metrics in JSON format

```json
{
    "total_records": 2,
    "total_sessions": 2,
    "unique_hostnames": ["Mac.home.local"],
    "unique_functions": [
        "slow_io_operation",
        "cpu_intensive_task", 
        "check_aws_credentials",
        "mixed_workload",
        "fast_calculation",
        "variable_duration"
    ],
    "avg_session_duration": 0.0,
    "slowest_functions": [
        ["check_aws_credentials", 0.294],
        ["slow_io_operation", 0.105],
        ["mixed_workload", 0.055]
    ],
    "most_active_hosts": [
        ["Mac.home.local", 14]
    ]
}
```

#### Hostnames API
`GET /api/hostnames/` - List of unique hostnames for filtering

```json
{
    "hostnames": ["Mac.home.local"]
}
```

#### Functions API
`GET /api/functions/` - List of unique function names for analysis

```json
{
    "functions": [
        "check_aws_credentials",
        "cpu_intensive_task",
        "fast_calculation",
        "mixed_workload", 
        "slow_io_operation",
        "variable_duration"
    ]
}
```

## System Monitoring Daemon

kode-kronical includes a background daemon for continuous system monitoring:

### Installation

```bash
# Install the daemon
sudo cp kode-kronical-daemon /usr/local/bin/
sudo chmod +x /usr/local/bin/kode-kronical-daemon

# Create configuration directory
mkdir -p ~/.config/kode-kronical/
cp config/daemon.yaml.example ~/.config/kode-kronical/daemon.yaml

# Edit configuration (set AWS region, table name, etc.)
nano ~/.config/kode-kronical/daemon.yaml
```

### Configuration

The daemon configuration supports:

```yaml
daemon:
  sample_interval: 60.0  # Collect data every minute
  max_samples: 1        # Upload immediately (no batching)
  enable_dynamodb_upload: true
  dynamodb_table_name: kode-kronical-system-v2  # Optimized table structure
  dynamodb_region: us-east-1

monitoring:
  auto_track_python: true
  cpu_alert_threshold: 90
  memory_alert_threshold: 85
```

### Running the Daemon

```bash
# Start daemon (foreground)
kode-kronical-daemon -c ~/.config/kode-kronical/daemon.yaml start

# Check status
kode-kronical-daemon -c ~/.config/kode-kronical/daemon.yaml status

# Stop daemon  
kode-kronical-daemon -c ~/.config/kode-kronical/daemon.yaml stop
```

### Optimized Data Collection

The system now uses:
- **1-minute intervals**: Efficient sampling every 60 seconds
- **Optimized storage**: Frontend-ready format with hour-based partitioning
- **Automatic TTL**: Data expires after 30 days
- **Real-time access**: Sub-minute latency for dashboard updates

### Code Formatting

```bash
# Activate virtual environment
source venv/bin/activate

# Format code (if dev dependencies installed)
black src tests
isort src tests
flake8 src tests
mypy src
```

## License

MIT License - see LICENSE file for details.
