# kode-kronical-jg

A lightweight Python performance tracking library with automatic data collection and visualization.

## Quick Start

### Installation

```bash
# Install from PyPI
pip install kode-kronical-jg

# For test installations from Test PyPI
pip install --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple/ kode-kronical-jg
```

### Basic Usage

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

# Method 2: Use as decorator with argument tracking
@perf.time_it(store_args=True)
def process_data(data, multiplier=2):
    return [x * multiplier for x in data]

# Call your functions
result1 = slow_function(1000)
result2 = process_data([1, 2, 3, 4, 5])

# Performance data is automatically collected and saved:
# - Local mode: Saved to ./perf_data/ as JSON files
# - AWS mode: Uploaded to DynamoDB on program exit

# Optional: Get timing results programmatically
summary = perf.get_summary()
print(f"Tracked {summary['call_count']} function calls")
```

### Configuration

Create a `.kode-kronical.yaml` file in your project directory:

```yaml
kode_kronical:
  enabled: true
  min_execution_time: 0.001

# For local development (no AWS required)
local:
  enabled: true
  data_dir: "./perf_data"
  format: "json"

# For production with AWS DynamoDB
# aws:
#   region: "us-east-1"
#   table_name: "kode-kronical-data"

filters:
  exclude_modules:
    - "boto3"
    - "requests"
    - "urllib3"
  track_arguments: false
```

## Features

- **Zero-configuration**: Works out of the box with sensible defaults
- **Flexible storage**: Local JSON files or AWS DynamoDB
- **Smart filtering**: Exclude libraries and focus on your code
- **Automatic collection**: Data is saved automatically when your program exits
- **Lightweight**: Minimal performance overhead
- **Easy configuration**: YAML-based configuration files
- **Web dashboard support**: Integrates with [kode-kronical-viewer](https://github.com/jeremycharlesgillespie/kode-kronical-viewer) for data visualization

## Storage Options

### Local Storage (Default)
Perfect for development and testing:
- No external dependencies
- Human-readable JSON format
- Automatic cleanup of old files

### AWS DynamoDB
For production environments:
- Scalable cloud storage
- Real-time data access
- Built-in redundancy

Configure AWS mode in your `.kode-kronical.yaml`:

```yaml
kode_kronical:
  enabled: true

aws:
  region: "us-east-1"
  table_name: "kode-kronical-data"
  auto_create_table: true

local:
  enabled: false  # Disable local storage when using AWS
```

## Configuration File Locations

KodeKronical searches for configuration files in this order:

1. `./kode-kronical.yaml` (current directory)
2. `./.kode-kronical.yaml` (current directory, hidden file)
3. `~/.kode-kronical.yaml` (home directory)
4. `~/.config/kode-kronical/config.yaml` (XDG config directory)

## API Reference

### KodeKronical Class

```python
from kode_kronical import KodeKronical

# Initialize with default configuration
perf = KodeKronical()

# Initialize with custom configuration
perf = KodeKronical({
    "local": {"enabled": True},
    "kode_kronical": {"debug": True}
})
```

### Decorators and Context Managers

```python
# As decorator
@perf.time_it
def my_function():
    pass

# As decorator with argument tracking
@perf.time_it(store_args=True)
def my_function_with_args(x, y):
    pass

# As context manager
with perf.time_it():
    # code to time
    pass
```

### Data Access

```python
# Get all results
results = perf.get_results()

# Get results for specific function
results = perf.get_results("my_function")

# Get summary statistics
summary = perf.get_summary()
summary = perf.get_summary("my_function")

# Manual data export
perf.save_to_local_storage()  # Force save to local files
perf.upload_to_dynamodb()    # Force upload to AWS
```

## License

MIT License - see LICENSE file for details.

## Web Dashboard

For visualizing and analyzing performance data, use the companion [kode-kronical-viewer](https://github.com/jeremycharlesgillespie/kode-kronical-viewer) Django dashboard:

```bash
# Install the viewer dashboard
pip install kode-kronical-viewer

# Or run the standalone project
git clone https://github.com/jeremycharlesgillespie/kode-kronical-viewer
cd kode-kronical-viewer
pip install -r requirements.txt
python start_viewer.py
```

The dashboard provides:
- **Performance Overview**: Key metrics, slowest functions, most active hosts
- **Advanced Filtering**: Filter by hostname, date range, function name, session ID
- **Function Analysis**: Detailed performance analysis for specific functions
- **REST API**: Programmatic access to performance data
- **Real-time Data**: Automatically displays latest performance data

## Package Development

### Building and Publishing

This package uses automated version management:

```bash
# Build and upload to PyPI (increments version automatically)
./upload_package.sh

# Build only (increments version)
python build_package.py

# Check current version
python -c "from version_manager import get_current_version; print(get_current_version())"
```

### Related Projects

- **[kode-kronical-viewer](https://github.com/jeremycharlesgillespie/kode-kronical-viewer)** - Django web dashboard for data visualization
- **[kode-kronical on PyPI](https://pypi.org/project/kode-kronical-jg/)** - Published package on PyPI

## Contributing

This is a standalone PyPI package. For development setup and contribution guidelines, see the main repository at [github.com/jeremycharlesgillespie/kode-kronical](https://github.com/jeremycharlesgillespie/kode-kronical).