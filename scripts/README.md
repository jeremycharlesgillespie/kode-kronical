# kode-kronical-daemon Installation Scripts

This directory contains automated installation scripts for setting up the kode-kronical system monitoring daemon on different operating systems.

## Quick Start

### Linux
```bash
# Run from the kode-kronical project root directory
cd kode-kronical

# Run as root for system-wide installation
sudo ./scripts/install-daemon-linux.sh

# Or for uninstallation
sudo ./scripts/install-daemon-linux.sh uninstall
```

### Windows
```powershell
# Run from the kode-kronical project root directory
cd kode-kronical

# Run PowerShell as Administrator
.\scripts\install-daemon-windows.ps1

# Or specify custom paths
.\scripts\install-daemon-windows.ps1 -InstallPath "C:\kode-kronical" -DataPath "C:\kode-kronical-data"

# Other actions
.\scripts\install-daemon-windows.ps1 -Action uninstall
.\scripts\install-daemon-windows.ps1 -Action start
.\scripts\install-daemon-windows.ps1 -Action stop
.\scripts\install-daemon-windows.ps1 -Action status
```

### macOS
```bash
# Run from the kode-kronical project root directory
cd kode-kronical

# System installation (requires sudo)
sudo ./scripts/install-daemon-macos.sh

# User installation (no sudo required)
./scripts/install-daemon-macos.sh

# Other operations
./scripts/install-daemon-macos.sh start
./scripts/install-daemon-macos.sh stop
./scripts/install-daemon-macos.sh status
./scripts/install-daemon-macos.sh uninstall
```

## What These Scripts Do

All installation scripts perform the following operations:

1. **Check Prerequisites**: Verify Python 3.8+ is installed
2. **Install Dependencies**: Install required Python packages (psutil, pyyaml, etc.)
3. **Create Directories**: Set up data, configuration, and log directories
4. **Install Daemon**: Copy executable and configuration files
5. **Setup Service**: Configure system service (systemd/launchd/Windows Service)
6. **Start Monitoring**: Begin collecting system metrics
7. **Verify Installation**: Check that everything is working correctly

## Platform-Specific Details

### Linux (`install-daemon-linux.sh`)

**Supported Distributions:**
- Ubuntu/Debian (apt)
- CentOS/RHEL/Fedora (yum/dnf)
- Arch Linux (pacman)

**Features:**
- Automatic distribution detection
- Creates dedicated `kode-kronical` system user
- Installs systemd service with security restrictions
- Configures proper file permissions
- Supports both installation and uninstallation

**Requirements:**
- Linux with systemd
- Root privileges (sudo)
- Internet connection for package installation

**Installation Paths:**
- Executable: `/usr/local/bin/kode-kronical-daemon`
- Configuration: `/etc/kode-kronical/daemon.yaml`
- Data: `~/.local/share/kode-kronical/`
- Logs: `/var/log/kode-kronical/`
- Service: `/etc/systemd/system/kode-kronical-daemon.service`

### Windows (`install-daemon-windows.ps1`)

**Supported Versions:**
- Windows 10/11
- Windows Server 2016+

**Features:**
- Automatic Python installation via Chocolatey (if available)
- Creates Windows Service with proper wrapper
- Configurable installation paths
- PowerShell execution policy handling
- Event log integration

**Requirements:**
- PowerShell 5.0+
- Administrator privileges
- .NET Framework 4.7.2+ (usually pre-installed)

**Default Installation Paths:**
- Executable: `C:\Program Files\kode-kronical\`
- Configuration: `C:\ProgramData\kode-kronical\config\`
- Data: `C:\ProgramData\kode-kronical\data\`
- Logs: `C:\ProgramData\kode-kronical\logs\`
- Service: Windows Services (services.msc)

### macOS (`install-daemon-macos.sh`)

**Supported Versions:**
- macOS 10.15 (Catalina) and later
- Both Intel and Apple Silicon Macs

**Features:**
- Automatic Homebrew installation
- Both system and user installation modes
- launchd service configuration
- PATH configuration for user installations
- Apple Silicon compatibility

**Requirements:**
- macOS 10.15+
- For system install: Administrator privileges (sudo)
- Internet connection for Homebrew/Python installation

**System Installation Paths:**
- Executable: `/usr/local/bin/kode-kronical-daemon`
- Configuration: `/usr/local/etc/kode-kronical/`
- Data: `/usr/local/var/kode-kronical/`
- Logs: `/usr/local/var/log/kode-kronical/`
- Service: `/Library/LaunchDaemons/com.kodekronical.daemon.plist`

**User Installation Paths:**
- Executable: `~/.local/bin/kode-kronical-daemon`
- Configuration: `~/.config/kode-kronical/`
- Data: `~/.local/share/kode-kronical/`
- Logs: `~/.local/share/kode-kronical/logs/`
- Service: `~/Library/LaunchAgents/com.kodekronical.daemon.plist`

## Configuration

All scripts install with sensible defaults but can be customized by editing the configuration file after installation:

### Common Configuration Options

```yaml
daemon:
  sample_interval: 1.0              # How often to collect metrics (seconds)
  data_retention_hours: 168         # How long to keep data (1 week)
  enable_network_monitoring: true   # Include network metrics
  
monitoring:
  auto_track_python: true           # Automatically track Python processes
  cpu_alert_threshold: 90           # Log warnings above this CPU %
  memory_alert_threshold: 85        # Log warnings above this memory %
  
export:
  format: json                      # Data export format
  compress: true                    # Compress data files
  batch_size: 1000                  # Metrics per file
```

## Post-Installation

### Verification

After installation, verify the daemon is working:

**Linux:**
```bash
sudo systemctl status kode-kronical-daemon
ls -la ~/.local/share/kode-kronical/
```

**Windows:**
```powershell
Get-Service kode-kronical-daemon
Get-ChildItem "C:\ProgramData\kode-kronical\data"
```

**macOS:**
```bash
launchctl list | grep kodekronical
ls -la /usr/local/var/kode-kronical/  # or ~/.local/share/kode-kronical/ for user install
```

### Testing KodeKronical Integration

Create a test script to verify integration:

```python
from kode_kronical import KodeKronical
import time

# Initialize KodeKronical
kode = KodeKronical()

# Check daemon connection
config_info = kode.get_config_info()
print("Daemon status:", config_info.get('daemon'))

@kode.time_it
def test_function():
    time.sleep(0.1)
    return "test"

# Run function
result = test_function()

# Get enhanced summary with system context
summary = kode.get_enhanced_summary()
print("System monitoring enabled:", summary.get('system_monitoring_enabled'))
```

## Service Management

### Linux (systemd)
```bash
sudo systemctl start kode-kronical-daemon     # Start
sudo systemctl stop kode-kronical-daemon      # Stop
sudo systemctl restart kode-kronical-daemon   # Restart
sudo systemctl status kode-kronical-daemon    # Status
sudo journalctl -u kode-kronical-daemon -f    # View logs
```

### Windows (Services)
```powershell
Start-Service kode-kronical-daemon           # Start
Stop-Service kode-kronical-daemon            # Stop
Restart-Service kode-kronical-daemon         # Restart
Get-Service kode-kronical-daemon             # Status
Get-EventLog -LogName Application -Source "kode-kronical-daemon" -Newest 10  # Logs
```

### macOS (Easy Scripts)
```bash
# Easy service management (recommended)
./scripts/start-daemon-macos.sh      # Start service
./scripts/stop-daemon-macos.sh       # Stop service  
./scripts/status-daemon-macos.sh     # Detailed status

# Force stop if needed
./scripts/stop-daemon-macos.sh force

# Use sudo for system installations
sudo ./scripts/start-daemon-macos.sh
sudo ./scripts/stop-daemon-macos.sh
```

### macOS (Manual launchctl)
```bash
# System service
sudo launchctl load /Library/LaunchDaemons/com.kodekronical.daemon.plist    # Start
sudo launchctl unload /Library/LaunchDaemons/com.kodekronical.daemon.plist  # Stop

# User service
launchctl load ~/Library/LaunchAgents/com.kodekronical.daemon.plist          # Start
launchctl unload ~/Library/LaunchAgents/com.kodekronical.daemon.plist        # Stop

launchctl list | grep kodekronical                                           # Status
tail -f /usr/local/var/log/kode-kronical/daemon.log                         # Logs
```

## Troubleshooting

### Common Issues

1. **Python not found**:
   - Linux: Install python3 and python3-pip packages
   - Windows: Install Python from python.org or use Chocolatey
   - macOS: Install via Homebrew or python.org

2. **Permission denied**:
   - Ensure you're running with appropriate privileges (sudo/Administrator)
   - Check file permissions in data directories

3. **Service won't start**:
   - Check logs for error messages
   - Verify Python dependencies are installed
   - Ensure configuration file is valid YAML

4. **No data files**:
   - Wait a few minutes after installation
   - Check service is actually running
   - Verify write permissions to data directory

5. **KodeKronical not detecting daemon**:
   - Ensure daemon is running and creating data files
   - Check data directory permissions
   - Verify KodeKronical and daemon are using same data paths

### Getting Help

1. **Check service logs** (see Service Management section above)
2. **Run daemon in foreground** for debugging:
   ```bash
   # Stop service first, then run manually
   python3 /path/to/kode-kronical-daemon -c /path/to/config.yaml start --no-daemon
   ```
3. **Enable debug logging** in configuration:
   ```yaml
   daemon:
     log_level: DEBUG
   ```

## Security Considerations

- **Linux**: Runs as dedicated user with minimal privileges
- **Windows**: Runs as Windows Service with restricted permissions  
- **macOS**: System install runs as daemon, user install runs as user
- **Network**: No external network connections, only local system monitoring
- **Data**: Only system metrics collected, no application data
- **Resources**: CPU and memory limits configured via service definitions

## Performance Impact

- **CPU Usage**: ~0.1-0.5% with default 1-second sampling
- **Memory Usage**: ~10-50MB depending on buffer size and processes tracked
- **Disk I/O**: Minimal, periodic batch writes every 60 seconds
- **Network**: No network usage for the monitoring itself

The daemon is designed to have minimal impact on system performance while providing valuable system context for performance analysis.