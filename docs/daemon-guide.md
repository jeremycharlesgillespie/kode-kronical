# Kode Kronical System Monitoring Daemon

The Kode Kronical daemon is a background service that continuously monitors system metrics (CPU, memory, network) and makes them available for correlation with your application's performance data.

## Quick Start (2 Minutes)

### Installation
```bash
pip install kode-kronical
```

### Basic Setup
```bash
# 1. Generate configuration
kode-kronical-daemon config

# 2. Start daemon  
kode-kronical-daemon start

# 3. Verify it's working
kode-kronical-daemon status
```

That's it! The daemon is now collecting system metrics locally.

### Install as System Service (Linux)
For production use, install as a systemd service that starts at boot:
```bash
# Install and enable systemd service
sudo install-kode-kronical-service

# The service is now running and will start automatically at boot!
```

### Enable AWS Upload (Optional)
```bash
# Setup AWS credentials
aws configure

# Enable DynamoDB uploads
sed -i '' 's/enable_dynamodb_upload: false/enable_dynamodb_upload: true/' ~/.config/kode-kronical/daemon.yaml

# Restart daemon
kode-kronical-daemon restart
# OR if using systemd service:
sudo systemctl restart kode-kronical-daemon
```

## What the Daemon Does

The daemon provides:
- **Continuous System Monitoring**: Real-time CPU, memory, network metrics
- **Process Tracking**: Automatic monitoring of Python processes  
- **Performance Correlation**: Integration with KodeKronical timing data
- **AWS Integration**: Optional upload to DynamoDB for centralized monitoring
- **Cross-Platform**: Support for Windows, macOS, and Linux

## File Locations

### User Installation (Recommended)
- **Configuration**: `~/.config/kode-kronical/daemon.yaml`
- **Data**: `~/.local/share/kode-kronical/`
- **Logs**: `~/.local/share/kode-kronical/daemon.log`

### System Installation
- **Linux**: `/etc/kode-kronical/daemon.yaml`, `~/.local/share/kode-kronical/`
- **macOS**: `/etc/kode-kronical/daemon.yaml`, `~/.local/share/kode-kronical/`
- **Windows**: `C:\ProgramData\kode-kronical\`

## Platform-Specific Installation

### Windows
```bash
# Basic installation
pip install kode-kronical
kode-kronical-daemon config
kode-kronical-daemon start

# Auto-start: Use Task Scheduler (service support coming soon)
```

### macOS
```bash
# Basic installation  
pip install kode-kronical
kode-kronical-daemon config
kode-kronical-daemon start

# Install as service
kode-kronical-daemon install              # User service
sudo kode-kronical-daemon install --system  # System service
```

### Linux
```bash
# Basic installation
pip install kode-kronical
kode-kronical-daemon config  
kode-kronical-daemon start

# Install as systemd service (recommended for production)
sudo install-kode-kronical-service

# Service management commands
sudo systemctl status kode-kronical-daemon   # Check service status
sudo systemctl stop kode-kronical-daemon     # Stop service
sudo systemctl start kode-kronical-daemon    # Start service
sudo systemctl restart kode-kronical-daemon  # Restart service
sudo systemctl disable kode-kronical-daemon  # Disable boot startup
sudo journalctl -u kode-kronical-daemon -f   # View live logs
```

## Configuration

### Basic Configuration
```yaml
# ~/.config/kode-kronical/daemon.yaml
daemon:
  sample_interval: 1.0                    # Collect data every second
  data_retention_hours: 24                # Keep 24 hours of data
  enable_network_monitoring: true         # Monitor network usage
  
  # DynamoDB upload (optional)
  enable_dynamodb_upload: false           # Set to true for AWS
  dynamodb_table_name: "kode-kronical-system"
  dynamodb_region: "us-east-1"
```

### Advanced Configuration
```yaml
daemon:
  sample_interval: 1.0
  max_samples: 3600
  data_retention_hours: 168               # 1 week
  
  # Process monitoring
  track_processes: [python, node, java]
  
  # Alert thresholds
  cpu_alert_threshold: 90
  memory_alert_threshold: 85

# AWS configuration
aws:
  profile: "default" 
  region: "us-east-1"
```

## AWS DynamoDB Integration

### Setup AWS Credentials
```bash
# Option 1: AWS CLI
aws configure

# Option 2: Environment variables
export AWS_ACCESS_KEY_ID=your_key
export AWS_SECRET_ACCESS_KEY=your_secret
export AWS_DEFAULT_REGION=us-east-1

# Option 3: Instance profiles (for EC2) - no additional setup needed
```

### Enable Upload
```bash
# Quick enable
sed -i '' 's/enable_dynamodb_upload: false/enable_dynamodb_upload: true/' ~/.config/kode-kronical/daemon.yaml

# Restart daemon
kode-kronical-daemon restart
```

### Required AWS Permissions
Your AWS user needs permissions for:
- `dynamodb:CreateTable`, `dynamodb:DescribeTable`
- `dynamodb:PutItem`, `dynamodb:BatchWriteItem`
- `dynamodb:GetItem`, `dynamodb:Scan`, `dynamodb:Query`

On tables: `kode-kronical-system` and `kode-kronical-systems-registry`

The daemon automatically creates tables if they don't exist.

For advanced AWS setup including IAM policies and CDK deployment, see the [AWS Setup Guide](aws-setup.md).

## Troubleshooting

### Daemon Won't Start
```bash
# Check if already running
kode-kronical-daemon status

# Clean up stale processes
pkill -f kode-kronical-daemon
rm ~/.local/share/kode-kronical/daemon.pid
kode-kronical-daemon start

# Run in debug mode
kode-kronical-daemon start --foreground --debug
```

### No Data Being Collected
```bash
# Check for metrics files
ls -la ~/.local/share/kode-kronical/metrics_*.json

# Monitor real-time logs
tail -f ~/.local/share/kode-kronical/daemon.log
```

### AWS Upload Issues

#### Test AWS Connection
```bash
# Verify credentials
aws sts get-caller-identity

# Test DynamoDB access
aws dynamodb list-tables --region us-east-1
```

#### Check Configuration
```bash
# Verify upload is enabled
grep enable_dynamodb_upload ~/.config/kode-kronical/daemon.yaml

# Check region consistency
echo "Daemon region:" && grep dynamodb_region ~/.config/kode-kronical/daemon.yaml
echo "AWS CLI region:" && aws configure get region
```

#### Common Error Messages
- **Credentials**: `NoCredentialsError: Unable to locate credentials`
- **Network**: `EndpointConnectionError: Could not connect to the endpoint URL`
- **Permissions**: `AccessDenied: User is not authorized to perform: dynamodb:PutItem`
- **Region Mismatch**: `Could not connect to the endpoint URL: "https://dynamodb.wrong-region.amazonaws.com/"`

#### Check Logs for Upload Status
```bash
# Look for upload activity
grep -i "upload\|dynamodb" ~/.local/share/kode-kronical/daemon.log | tail -10

# Monitor real-time uploads
tail -f ~/.local/share/kode-kronical/daemon.log | grep -i dynamodb
```

## Integration with KodeKronical

Once the daemon is running, your KodeKronical timing data automatically includes system context:

```python
from kode_kronical import KodeKronical

kode = KodeKronical()

@kode.time_it
def my_function():
    # Your code here
    pass

# Results include system correlation
summary = kode.get_enhanced_summary()
print(f"System monitoring: {summary.get('system_monitoring_enabled')}")

# Get detailed system correlation
correlation = kode.get_system_correlation_report()
```

## Commands Reference

```bash
# Basic operations
kode-kronical-daemon start           # Start daemon
kode-kronical-daemon stop            # Stop daemon
kode-kronical-daemon restart         # Restart daemon
kode-kronical-daemon status          # Show status and health

# Configuration
kode-kronical-daemon config          # Generate/update config
kode-kronical-daemon config --system # Generate system config (requires sudo)

# Service installation (Linux)
sudo install-kode-kronical-service           # Install systemd service
sudo install-kode-kronical-service uninstall # Remove systemd service
install-kode-kronical-service --help         # Show help

# Advanced daemon options
kode-kronical-daemon start --foreground # Run in foreground
kode-kronical-daemon start --debug      # Enable debug logging
kode-kronical-daemon -c /path/config.yaml start # Use custom config

# Service management (after installing service)
sudo systemctl status kode-kronical-daemon   # Check service status
sudo systemctl stop kode-kronical-daemon     # Stop service
sudo systemctl start kode-kronical-daemon    # Start service
sudo systemctl restart kode-kronical-daemon  # Restart service
sudo journalctl -u kode-kronical-daemon -f   # View live logs
```

## Performance Impact

Typical resource usage:
- **CPU**: 0.1-0.5% with 1-second sampling
- **Memory**: 10-50MB depending on configuration
- **Disk I/O**: Minimal, periodic batch writes
- **Network**: Only for DynamoDB uploads (if enabled)

### Optimization for Low-Resource Systems
```yaml
daemon:
  sample_interval: 5.0                 # Sample every 5 seconds
  max_samples: 720                     # Reduce memory buffer
  data_retention_hours: 12             # Keep less data
  enable_network_monitoring: false     # Disable if not needed
```

## Uninstallation

### Stop and Remove Daemon
```bash
# Stop daemon
kode-kronical-daemon stop

# Remove service (if installed)
# Linux - User service
systemctl --user disable kode-kronical-daemon
systemctl --user stop kode-kronical-daemon
rm ~/.config/systemd/user/kode-kronical-daemon.service

# Linux - System service (requires sudo)
sudo systemctl disable kode-kronical-daemon
sudo systemctl stop kode-kronical-daemon
sudo rm /etc/systemd/system/kode-kronical-daemon.service

# macOS  
launchctl unload ~/Library/LaunchAgents/com.kodekronical.daemon.plist
rm ~/Library/LaunchAgents/com.kodekronical.daemon.plist

# Remove data and configuration
rm -rf ~/.config/kode-kronical/
rm -rf ~/.local/share/kode-kronical/

# Uninstall package
pip uninstall kode-kronical
```

## Support

- [GitHub Issues](https://github.com/jeremycharlesgillespie/kode-kronical/issues)
- [Main Documentation](../README.md)
- [Exception Handling Guide](exception-handling.md)
- [AWS Setup Guide](aws-setup.md)