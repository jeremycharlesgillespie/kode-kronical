# kode-kronical-daemon Installation and Setup Guide

This guide covers installing and configuring the kode-kronical-daemon for continuous system monitoring.

## Overview

The kode-kronical-daemon is a background service that continuously collects system metrics (CPU, memory, network) and makes them available for correlation with kode-kronical function timing data. This enables you to understand how system load affects your application performance.

## Quick Start

### 1. Install kode-kronical with daemon support

```bash
cd kode-kronical
pip3 install -r requirements.txt
pip3 install psutil  # Required for system monitoring
```

### 2. Test the daemon locally

```bash
# Start daemon in foreground for testing
python3 kode-kronical-daemon start

# In another terminal, check status
python3 kode-kronical-daemon status

# Stop the daemon
python3 kode-kronical-daemon stop
```

## Production Installation

### Linux (systemd)

#### 1. Install the daemon

```bash
# Copy daemon executable
sudo cp kode-kronical-daemon /usr/local/bin/
sudo chmod +x /usr/local/bin/kode-kronical-daemon

# Copy systemd service file
sudo cp scripts/kode-kronical-daemon.service /etc/systemd/system/

# Create user and directories
sudo useradd -r -s /bin/false kode-kronical
sudo mkdir -p /var/lib/kode-kronical /var/log/kode-kronical
sudo chown kode-kronical:kode-kronical /var/lib/kode-kronical /var/log/kode-kronical

# Copy configuration
sudo mkdir -p /etc/kode-kronical
sudo cp config/daemon.yaml.example /etc/kode-kronical/daemon.yaml
sudo chown kode-kronical:kode-kronical /etc/kode-kronical/daemon.yaml
```

#### 2. Configure the daemon

Edit `/etc/kode-kronical/daemon.yaml`:

```yaml
daemon:
  # Use system paths
  pid_file: /var/run/kode-kronical-daemon.pid
  log_file: /var/log/kode-kronical/daemon.log
  data_dir: /var/lib/kode-kronical
  sample_interval: 1.0
  data_retention_hours: 168  # 1 week
  enable_network_monitoring: true

monitoring:
  auto_track_python: true
  cpu_alert_threshold: 90
  memory_alert_threshold: 85
```

#### 3. Start and enable the service

```bash
# Reload systemd
sudo systemctl daemon-reload

# Start the service
sudo systemctl start kode-kronical-daemon

# Enable auto-start on boot
sudo systemctl enable kode-kronical-daemon

# Check status
sudo systemctl status kode-kronical-daemon

# View logs
sudo journalctl -u kode-kronical-daemon -f
```

### macOS (launchd)

#### 1. Install the daemon

```bash
# Copy daemon executable
sudo cp kode-kronical-daemon /usr/local/bin/
sudo chmod +x /usr/local/bin/kode-kronical-daemon

# Create directories
sudo mkdir -p /var/lib/kode-kronical /var/log/kode-kronical
```

#### 2. Install launchd service

```bash
# Copy plist file
sudo cp scripts/com.pyperf.daemon.plist /Library/LaunchDaemons/

# Load the service
sudo launchctl load /Library/LaunchDaemons/com.pyperf.daemon.plist

# Start the service
sudo launchctl start com.pyperf.daemon
```

#### 3. Check status

```bash
# Check if running
python3 /usr/local/bin/kode-kronical-daemon status

# View logs
tail -f /var/log/kode-kronical/daemon.log
```

## User Installation (Non-root)

For development or single-user installations:

### 1. Setup directories

```bash
mkdir -p ~/.kode-kronical/data ~/.kode-kronical/logs
```

### 2. Copy configuration

```bash
cp config/daemon.yaml.example ~/.kode-kronical/daemon.yaml
```

### 3. Edit configuration for user paths

```yaml
daemon:
  pid_file: ~/.kode-kronical/daemon.pid
  log_file: ~/.kode-kronical/logs/daemon.log
  data_dir: ~/.kode-kronical/data
  sample_interval: 1.0
  data_retention_hours: 24
```

### 4. Start daemon

```bash
# Start with custom config
./kode-kronical-daemon -c ~/.kode-kronical/daemon.yaml start

# Check status
./kode-kronical-daemon -c ~/.kode-kronical/daemon.yaml status
```

## Verifying Installation

### 1. Check daemon is running

```bash
# Using the daemon command
kode-kronical-daemon status

# Or check process list
ps aux | grep kode-kronical-daemon
```

### 2. Verify data collection

```bash
# Check data directory
ls -la /var/lib/kode-kronical/  # or ~/.kode-kronical/data/

# Look for metrics files
find /var/lib/kode-kronical -name "metrics_*.json" -mtime -1
```

### 3. Test KodeKronical integration

```python
from kode_kronical import KodeKronical
import time

# Initialize KodeKronical
perf = KodeKronical()

# Check daemon connection
config_info = perf.get_config_info()
print("Daemon status:", config_info.get('daemon'))

@perf.time_it
def test_function():
    time.sleep(0.1)
    return "test"

# Run function
result = test_function()

# Get enhanced summary with system context
summary = perf.get_enhanced_summary()
print("System monitoring enabled:", summary.get('system_monitoring_enabled'))

# Get system correlation report
correlation = perf.get_system_correlation_report()
print("Correlation report:", correlation)
```

## Configuration Options

### Daemon Configuration (`/etc/kode-kronical/daemon.yaml`)

```yaml
daemon:
  sample_interval: 1.0           # Sampling frequency (seconds)
  max_samples: 3600              # Memory buffer size
  data_retention_hours: 168      # How long to keep data files
  enable_network_monitoring: true # Include network metrics

monitoring:
  auto_track_python: true        # Auto-track Python processes
  track_processes:               # Additional processes to monitor
    - node
    - java
  cpu_alert_threshold: 90        # Log warnings above this CPU %
  memory_alert_threshold: 85     # Log warnings above this memory %

export:
  format: json                   # Export format
  compress: true                 # Compress exported files
  batch_size: 1000              # Samples per file
```

### KodeKronical Configuration (`.kode-kronical.yaml`)

```yaml
kode_kronical:
  enabled: true
  enable_system_monitoring: true  # Enable daemon integration

local:
  enabled: true
  data_dir: "./perf_data"
```

## Troubleshooting

### Daemon not starting

1. **Check permissions**:
   ```bash
   sudo chown kode-kronical:kode-kronical /var/lib/kode-kronical /var/log/kode-kronical
   ```

2. **Check Python dependencies**:
   ```bash
   python3 -c "import psutil; print('psutil OK')"
   ```

3. **Run in foreground for debugging**:
   ```bash
   # Skip daemonization for debugging
   python3 kode-kronical-daemon start --no-daemon
   ```

### KodeKronical not connecting to daemon

1. **Check daemon is running**:
   ```bash
   kode-kronical-daemon status
   ```

2. **Check data directory permissions**:
   ```bash
   ls -la /var/lib/kode-kronical/
   ```

3. **Enable debug logging**:
   ```python
   import logging
   logging.basicConfig(level=logging.DEBUG)
   
   from kode_kronical import KodeKronical
   perf = KodeKronical()
   ```

### High resource usage

1. **Increase sample interval**:
   ```yaml
   daemon:
     sample_interval: 5.0  # Sample every 5 seconds instead of 1
   ```

2. **Disable network monitoring**:
   ```yaml
   daemon:
     enable_network_monitoring: false
   ```

3. **Reduce data retention**:
   ```yaml
   daemon:
     data_retention_hours: 24  # Keep only 1 day of data
   ```

## Uninstallation

### Linux (systemd)

```bash
# Stop and disable service
sudo systemctl stop kode-kronical-daemon
sudo systemctl disable kode-kronical-daemon

# Remove files
sudo rm /etc/systemd/system/kode-kronical-daemon.service
sudo rm /usr/local/bin/kode-kronical-daemon
sudo rm -rf /etc/kode-kronical
sudo rm -rf /var/lib/kode-kronical
sudo rm -rf /var/log/kode-kronical

# Remove user
sudo userdel kode-kronical

# Reload systemd
sudo systemctl daemon-reload
```

### macOS (launchd)

```bash
# Stop and unload service
sudo launchctl stop com.pyperf.daemon
sudo launchctl unload /Library/LaunchDaemons/com.pyperf.daemon.plist

# Remove files
sudo rm /Library/LaunchDaemons/com.pyperf.daemon.plist
sudo rm /usr/local/bin/kode-kronical-daemon
sudo rm -rf /var/lib/kode-kronical
sudo rm -rf /var/log/kode-kronical
```

## Security Considerations

1. **File Permissions**: Daemon runs as dedicated user with minimal permissions
2. **Network Access**: Only local system monitoring, no external connections
3. **Data Privacy**: Only system metrics collected, no application data
4. **Resource Limits**: Configured CPU and memory limits via systemd/launchd

## Performance Impact

- **CPU Usage**: ~0.1-0.5% with 1-second sampling
- **Memory Usage**: ~10-50MB depending on buffer size
- **Disk I/O**: Minimal, periodic batch writes
- **Network**: No network usage for monitoring