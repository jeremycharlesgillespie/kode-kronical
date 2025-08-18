#!/usr/bin/env python3
"""
KodeKronical System Monitoring Daemon

This daemon runs in the background to continuously collect system metrics
that can be correlated with performance timing data from KodeKronical.
"""

import os
import sys
import time
import json
import signal
import logging
import argparse
import psutil
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Optional, Any

# Import kode_kronical modules
try:
    # Package import
    from .config import get_config
    from .system_monitor import SystemMonitor
    from .system_dynamodb import SystemDynamoDBService
    from .systems_registry import SystemsRegistryService
    from .hostname_utils import get_normalized_hostname
except ImportError:
    # Direct script execution
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent))
    from config import get_config
    from system_monitor import SystemMonitor
    from system_dynamodb import SystemDynamoDBService
    from systems_registry import SystemsRegistryService
    from hostname_utils import get_normalized_hostname


class KodeKronicalDaemon:
    """System monitoring daemon for KodeKronical."""
    
    def __init__(self, config_path: Optional[str] = None):
        """Initialize daemon with configuration."""
        # Load configuration
        if config_path and os.path.exists(config_path):
            self.config = self._load_config(config_path)
        else:
            self.config = self._get_default_config()
        
        # Set up paths based on config
        daemon_config = self.config.get('daemon', {})
        
        # Determine if we're running as root/system or user
        self.is_system_daemon = os.geteuid() == 0 if hasattr(os, 'geteuid') else False
        
        # Set default paths based on daemon type
        if self.is_system_daemon:
            # System daemon paths
            default_pid_file = '/var/run/kode-kronical-daemon.pid'
            default_log_file = '/var/log/kode-kronical-daemon.log'
            default_data_dir = '/var/lib/kode-kronical'
        else:
            # User daemon paths
            home = Path.home()
            default_pid_file = str(home / '.local/share/kode-kronical/daemon.pid')
            default_log_file = str(home / '.local/share/kode-kronical/daemon.log')
            default_data_dir = str(home / '.local/share/kode-kronical')
        
        self.pid_file = Path(daemon_config.get('pid_file', default_pid_file))
        self.log_file = Path(daemon_config.get('log_file', default_log_file))
        self.data_dir = Path(daemon_config.get('data_dir', default_data_dir))
        
        # Create directories if they don't exist
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.log_file.parent.mkdir(parents=True, exist_ok=True)
        self.pid_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Set up logging
        logging.basicConfig(
            filename=str(self.log_file),
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger('kode-kronical-daemon')
        
        # Initialize system monitor
        self.monitor = SystemMonitor(
            sample_interval=daemon_config.get('sample_interval', 1.0),
            max_samples=daemon_config.get('max_samples', 3600)
        )
        
        # Initialize DynamoDB service if enabled
        self.dynamodb_service = None
        self.registry_service = None
        if daemon_config.get('enable_dynamodb_upload', False):
            try:
                table_name = daemon_config.get('dynamodb_table_name', 'kode-kronical-system')
                region = daemon_config.get('dynamodb_region', 'us-east-1')
                self.dynamodb_service = SystemDynamoDBService(table_name, region)
                
                # Initialize systems registry
                registry_table = daemon_config.get('registry_table_name', 'kode-kronical-systems-registry')
                self.registry_service = SystemsRegistryService(registry_table, region)
                
                self.logger.info(f"DynamoDB upload enabled to table: {table_name}")
            except Exception as e:
                self.logger.error(f"Failed to initialize DynamoDB service: {e}")
        
        # Data retention settings
        self.data_retention_hours = daemon_config.get('data_retention_hours', 24)
        self.last_cleanup = time.time()
        
        # Running flag
        self.running = False
        
    def _load_config(self, config_path: str) -> Dict[str, Any]:
        """Load configuration from YAML file."""
        try:
            import yaml
            with open(config_path, 'r') as f:
                return yaml.safe_load(f) or {}
        except Exception as e:
            print(f"Error loading config from {config_path}: {e}")
            return self._get_default_config()
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Get default configuration."""
        home = Path.home()
        return {
            'daemon': {
                'sample_interval': 1.0,
                'max_samples': 3600,
                'data_retention_hours': 24,
                'enable_network_monitoring': True,
                'enable_dynamodb_upload': False
            }
        }
    
    def start(self):
        """Start the daemon."""
        # Check if already running
        if self.is_running():
            print(f"Daemon already running with PID {self.get_pid()}")
            return
        
        print("Starting kode-kronical-daemon...")
        
        # Fork and daemonize
        if os.name != 'nt':  # Unix/Linux/macOS
            self._daemonize()
        
        # Write PID file
        with open(self.pid_file, 'w') as f:
            f.write(str(os.getpid()))
        
        # Set up signal handlers
        signal.signal(signal.SIGTERM, self._signal_handler)
        signal.signal(signal.SIGINT, self._signal_handler)
        
        # Start monitoring
        self.running = True
        self.monitor.start_monitoring()
        
        self.logger.info(f"Daemon started with PID {os.getpid()}")
        
        # Register this system in the registry
        if self.registry_service:
            try:
                import platform
                hostname = get_normalized_hostname()
                self.registry_service.register_system(
                    hostname=hostname,
                    platform_info=platform.system()
                )
                self.logger.info(f"Registered system {hostname} in registry")
            except Exception as e:
                self.logger.error(f"Failed to register system: {e}")
        
        # Main loop
        metrics_buffer = []
        last_save = time.time()
        save_interval = 60  # Save every minute
        
        while self.running:
            try:
                # Get current metrics
                metrics = self.monitor.get_current_metrics()
                if metrics:
                    metrics_buffer.append(metrics)
                
                # Save periodically
                if time.time() - last_save >= save_interval:
                    if metrics_buffer:
                        self._save_metrics(metrics_buffer)
                        metrics_buffer = []
                    last_save = time.time()
                    
                    # Cleanup old files
                    self._cleanup_old_files()
                
                time.sleep(1)
                
            except Exception as e:
                self.logger.error(f"Error in daemon main loop: {e}")
                time.sleep(5)
        
        # Clean up
        self.monitor.stop_monitoring()
        
        # Mark system as offline in registry
        if self.registry_service:
            try:
                hostname = get_normalized_hostname()
                self.registry_service.mark_system_offline(hostname)
            except Exception as e:
                self.logger.error(f"Failed to mark system offline: {e}")
        
        os.unlink(self.pid_file)
        self.logger.info("Daemon stopped")
    
    def stop(self):
        """Stop the daemon."""
        pid = self.get_pid()
        if not pid:
            print("Daemon not running")
            return
        
        print(f"Stopping daemon with PID {pid}...")
        try:
            os.kill(pid, signal.SIGTERM)
            time.sleep(2)
            
            # Check if still running
            if self.is_running():
                print("Daemon didn't stop gracefully, forcing...")
                os.kill(pid, signal.SIGKILL)
        except ProcessLookupError:
            print("Daemon already stopped")
        except Exception as e:
            print(f"Error stopping daemon: {e}")
        
        # Clean up PID file if it exists
        if self.pid_file.exists():
            os.unlink(self.pid_file)
    
    def status(self):
        """Get daemon status."""
        pid = self.get_pid()
        if not pid:
            print("Daemon not running")
            return False
        
        if not self.is_running():
            print("Daemon not running (stale PID file)")
            return False
        
        try:
            process = psutil.Process(pid)
            cpu_percent = process.cpu_percent(interval=0.1)
            memory_info = process.memory_info()
            create_time = datetime.fromtimestamp(process.create_time())
            uptime = datetime.now() - create_time
            
            print(f"Daemon running with PID {pid}")
            print(f"  CPU: {cpu_percent}%")
            print(f"  Memory: {memory_info.rss / 1024 / 1024:.1f} MB")
            print(f"  Uptime: {uptime}")
            return True
        except Exception as e:
            print(f"Error getting daemon status: {e}")
            return False
    
    def get_pid(self) -> Optional[int]:
        """Get daemon PID from file."""
        if not self.pid_file.exists():
            return None
        
        try:
            with open(self.pid_file, 'r') as f:
                return int(f.read().strip())
        except:
            return None
    
    def is_running(self) -> bool:
        """Check if daemon is running."""
        pid = self.get_pid()
        if not pid:
            return False
        
        try:
            os.kill(pid, 0)
            return True
        except ProcessLookupError:
            return False
        except PermissionError:
            # Process exists but we can't send signal (different user)
            return True
    
    def _daemonize(self):
        """Fork and become a daemon."""
        # First fork
        pid = os.fork()
        if pid > 0:
            sys.exit(0)
        
        # Decouple from parent
        os.setsid()
        
        # Second fork
        pid = os.fork()
        if pid > 0:
            sys.exit(0)
        
        # Redirect standard file descriptors
        sys.stdout.flush()
        sys.stderr.flush()
        
        # Close file descriptors
        null = os.open('/dev/null', os.O_RDWR)
        os.dup2(null, 0)
        os.dup2(null, 1)
        os.dup2(null, 2)
        os.close(null)
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals."""
        self.logger.info(f"Received signal {signum}, shutting down...")
        self.running = False
    
    def _save_metrics(self, metrics_buffer):
        """Save metrics to file and optionally upload to DynamoDB."""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = self.data_dir / f"metrics_{timestamp}.json"
        
        try:
            # Save to local file
            with open(filename, 'w') as f:
                json.dump(metrics_buffer, f, indent=2)
            
            self.logger.info(f"Saved {len(metrics_buffer)} metrics to {filename}")
            
            # Upload to DynamoDB if enabled
            if self.dynamodb_service:
                try:
                    hostname = get_normalized_hostname()
                    success = self.dynamodb_service.upload_system_metrics(
                        metrics_buffer, hostname
                    )
                    if success:
                        self.logger.info(f"Successfully uploaded {len(metrics_buffer)} metrics to DynamoDB")
                        
                        # Update system metrics in registry
                        if self.registry_service and metrics_buffer:
                            latest_metrics = metrics_buffer[-1].get('system', {})
                            self.registry_service.update_system_metrics(
                                hostname=hostname,
                                cpu_percent=latest_metrics.get('cpu_percent', 0),
                                memory_percent=latest_metrics.get('memory_percent', 0)
                            )
                    else:
                        self.logger.error("Failed to upload metrics to DynamoDB")
                except Exception as e:
                    self.logger.error(f"Error uploading to DynamoDB: {e}")
            
        except Exception as e:
            self.logger.error(f"Error saving metrics: {e}")
    
    def _cleanup_old_files(self):
        """Remove old metrics files."""
        if time.time() - self.last_cleanup < 3600:  # Clean up hourly
            return
        
        cutoff_time = datetime.now() - timedelta(hours=self.data_retention_hours)
        
        for file in self.data_dir.glob("metrics_*.json"):
            try:
                file_time = datetime.fromtimestamp(file.stat().st_mtime)
                if file_time < cutoff_time:
                    file.unlink()
                    self.logger.info(f"Deleted old metrics file: {file}")
            except Exception as e:
                self.logger.error(f"Error deleting {file}: {e}")
        
        self.last_cleanup = time.time()


def main():
    """Main entry point for daemon command."""
    parser = argparse.ArgumentParser(
        description='KodeKronical System Monitoring Daemon',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  kode-kronical-daemon start           # Start daemon with default config
  kode-kronical-daemon stop            # Stop running daemon
  kode-kronical-daemon status          # Check daemon status
  kode-kronical-daemon restart         # Restart daemon
  kode-kronical-daemon install         # Install service (system/user)
  kode-kronical-daemon config          # Generate config file
  
Config file locations (searched in order):
  1. Specified with -c flag
  2. ~/.config/kode-kronical/daemon.yaml (user)
  3. /etc/kode-kronical/daemon.yaml (system)
  4. Built-in defaults
        """
    )
    
    parser.add_argument('command', 
                       choices=['start', 'stop', 'restart', 'status', 'install', 'config'],
                       help='Daemon command')
    
    parser.add_argument('-c', '--config',
                       help='Path to configuration file')
    
    parser.add_argument('--user', action='store_true',
                       help='Install as user service (no root required)')
    
    parser.add_argument('--system', action='store_true',
                       help='Install as system service (requires root)')
    
    args = parser.parse_args()
    
    # Handle special commands
    if args.command == 'config':
        generate_config(args)
        return
    
    if args.command == 'install':
        install_service(args)
        return
    
    # Find config file
    config_path = args.config
    if not config_path:
        # Search default locations
        home = Path.home()
        search_paths = [
            home / '.config/kode-kronical/daemon.yaml',
            Path('/etc/kode-kronical/daemon.yaml')
        ]
        for path in search_paths:
            if path.exists():
                config_path = str(path)
                break
    
    # Create daemon instance
    daemon = KodeKronicalDaemon(config_path)
    
    # Execute command
    if args.command == 'start':
        daemon.start()
    elif args.command == 'stop':
        daemon.stop()
    elif args.command == 'restart':
        daemon.stop()
        time.sleep(2)
        daemon.start()
    elif args.command == 'status':
        daemon.status()


def generate_config(args):
    """Generate a configuration file template."""
    home = Path.home()
    
    if args.user or not args.system:
        # User config
        config_dir = home / '.config/kode-kronical'
        config_file = config_dir / 'daemon.yaml'
        data_dir = home / '.local/share/kode-kronical'
        log_file = data_dir / 'daemon.log'
        pid_file = data_dir / 'daemon.pid'
    else:
        # System config
        config_dir = Path('/etc/kode-kronical')
        config_file = config_dir / 'daemon.yaml'
        data_dir = Path('/var/lib/kode-kronical')
        log_file = Path('/var/log/kode-kronical-daemon.log')
        pid_file = Path('/var/run/kode-kronical-daemon.pid')
    
    config_template = f"""# KodeKronical Daemon Configuration
daemon:
  # Sampling interval in seconds
  sample_interval: 1.0
  
  # Maximum samples to keep in memory
  max_samples: 3600
  
  # Data retention in hours (for local files)
  data_retention_hours: 24
  
  # Enable network monitoring
  enable_network_monitoring: true
  
  # File paths
  data_dir: "{data_dir}"
  log_file: "{log_file}"
  pid_file: "{pid_file}"
  
  # DynamoDB upload settings (optional)
  enable_dynamodb_upload: false
  dynamodb_table_name: "kode-kronical-system"
  dynamodb_region: "us-east-1"
  registry_table_name: "kode-kronical-systems-registry"

# Optional AWS configuration
# aws:
#   profile: "default"  # AWS profile to use
#   region: "us-east-1"
"""
    
    # Create config directory
    config_dir.mkdir(parents=True, exist_ok=True)
    
    # Check if config already exists
    if config_file.exists():
        print(f"Config file already exists: {config_file}")
        response = input("Overwrite? (y/N): ")
        if response.lower() != 'y':
            return
    
    # Write config file
    with open(config_file, 'w') as f:
        f.write(config_template)
    
    print(f"Configuration file created: {config_file}")
    print("\nEdit this file to customize daemon settings.")
    print(f"\nTo start the daemon: kode-kronical-daemon -c {config_file} start")


def install_service(args):
    """Install daemon as a system service."""
    import platform
    system = platform.system()
    
    if system == "Darwin":
        install_macos_service(args)
    elif system == "Linux":
        install_linux_service(args)
    elif system == "Windows":
        install_windows_service(args)
    else:
        print(f"Service installation not supported on {system}")


def install_macos_service(args):
    """Install launchd service on macOS."""
    home = Path.home()
    
    if args.user or not args.system:
        # User service
        plist_dir = home / 'Library/LaunchAgents'
        plist_file = plist_dir / 'com.kodekronical.daemon.plist'
        config_file = home / '.config/kode-kronical/daemon.yaml'
    else:
        # System service
        plist_dir = Path('/Library/LaunchDaemons')
        plist_file = plist_dir / 'com.kodekronical.daemon.plist'
        config_file = Path('/etc/kode-kronical/daemon.yaml')
    
    # Find kode-kronical-daemon command
    import shutil
    daemon_cmd = shutil.which('kode-kronical-daemon')
    if not daemon_cmd:
        print("Error: kode-kronical-daemon command not found in PATH")
        print("Make sure kode-kronical is installed: pip install kode-kronical")
        return
    
    plist_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.kodekronical.daemon</string>
    
    <key>ProgramArguments</key>
    <array>
        <string>{daemon_cmd}</string>
        <string>-c</string>
        <string>{config_file}</string>
        <string>start</string>
    </array>
    
    <key>RunAtLoad</key>
    <true/>
    
    <key>KeepAlive</key>
    <true/>
    
    <key>StandardErrorPath</key>
    <string>/tmp/kode-kronical-daemon.err</string>
    
    <key>StandardOutPath</key>
    <string>/tmp/kode-kronical-daemon.out</string>
</dict>
</plist>"""
    
    # Create plist directory if needed
    plist_dir.mkdir(parents=True, exist_ok=True)
    
    # Generate config if it doesn't exist
    if not config_file.exists():
        print("Generating configuration file...")
        generate_config(args)
    
    # Write plist file
    with open(plist_file, 'w') as f:
        f.write(plist_content)
    
    print(f"Service file created: {plist_file}")
    
    # Load the service
    if args.user or not args.system:
        print("\nTo start the service:")
        print(f"  launchctl load {plist_file}")
        print("\nTo stop the service:")
        print(f"  launchctl unload {plist_file}")
    else:
        print("\nTo start the service:")
        print(f"  sudo launchctl load {plist_file}")
        print("\nTo stop the service:")
        print(f"  sudo launchctl unload {plist_file}")


def install_linux_service(args):
    """Install systemd service on Linux."""
    if args.user:
        # User service
        service_dir = Path.home() / '.config/systemd/user'
        service_file = service_dir / 'kode-kronical-daemon.service'
        config_file = Path.home() / '.config/kode-kronical/daemon.yaml'
    else:
        # System service
        service_dir = Path('/etc/systemd/system')
        service_file = service_dir / 'kode-kronical-daemon.service'
        config_file = Path('/etc/kode-kronical/daemon.yaml')
    
    # Find kode-kronical-daemon command
    import shutil
    daemon_cmd = shutil.which('kode-kronical-daemon')
    if not daemon_cmd:
        print("Error: kode-kronical-daemon command not found in PATH")
        print("Make sure kode-kronical is installed: pip install kode-kronical")
        return
    
    service_content = f"""[Unit]
Description=KodeKronical System Monitoring Daemon
After=network.target

[Service]
Type=forking
ExecStart={daemon_cmd} -c {config_file} start
ExecStop={daemon_cmd} -c {config_file} stop
ExecReload={daemon_cmd} -c {config_file} restart
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
"""
    
    # Create service directory if needed
    service_dir.mkdir(parents=True, exist_ok=True)
    
    # Generate config if it doesn't exist
    if not config_file.exists():
        print("Generating configuration file...")
        generate_config(args)
    
    # Write service file
    with open(service_file, 'w') as f:
        f.write(service_content)
    
    print(f"Service file created: {service_file}")
    
    if args.user:
        print("\nTo enable and start the service:")
        print("  systemctl --user daemon-reload")
        print("  systemctl --user enable kode-kronical-daemon")
        print("  systemctl --user start kode-kronical-daemon")
    else:
        print("\nTo enable and start the service:")
        print("  sudo systemctl daemon-reload")
        print("  sudo systemctl enable kode-kronical-daemon")
        print("  sudo systemctl start kode-kronical-daemon")


def install_windows_service(args):
    """Install Windows service."""
    print("Windows service installation is not yet implemented.")
    print("For now, you can run the daemon manually:")
    print("  kode-kronical-daemon start")


if __name__ == '__main__':
    main()