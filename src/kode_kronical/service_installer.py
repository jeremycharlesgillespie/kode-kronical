#!/usr/bin/env python3
"""
Service installer for kode-kronical-daemon
Installs the daemon as a systemd service on Linux systems.
"""

import os
import sys
import subprocess
import platform
import shutil
from pathlib import Path


class ServiceInstaller:
    def __init__(self):
        self.service_name = "kode-kronical-daemon"
        self.service_file = f"/etc/systemd/system/{self.service_name}.service"
        self.daemon_path = None
        self.config_path = None
        self.pid_file = None
        self.user = os.environ.get('SUDO_USER', 'root')
        self.create_default_config = False
        
    def log(self, message, color='32'):
        """Print colored log message."""
        timestamp = subprocess.run(['date', '+%H:%M:%S'], capture_output=True, text=True).stdout.strip()
        print(f"\033[{color}m[{timestamp}] {message}\033[0m")
    
    def error(self, message):
        """Print error message."""
        print(f"\033[31m[ERROR] {message}\033[0m", file=sys.stderr)
    
    def warning(self, message):
        """Print warning message."""
        print(f"\033[33m[WARNING] {message}\033[0m")
    
    def info(self, message):
        """Print info message."""
        print(f"\033[34m[INFO] {message}\033[0m")
    
    def check_root(self):
        """Check if running as root."""
        if os.geteuid() != 0:
            self.error("This script must be run as root (use sudo)")
            sys.exit(1)
    
    def check_platform(self):
        """Check if running on Linux."""
        if platform.system() != "Linux":
            self.error("Service installation is currently only supported on Linux")
            self.error("For other platforms, run: kode-kronical-daemon start")
            sys.exit(1)
    
    def find_daemon(self):
        """Find kode-kronical-daemon executable."""
        self.log("Locating kode-kronical-daemon executable...")
        
        # Search common virtual environment locations first
        venv_paths = [
            f"/home/{self.user}/.venv",
            f"/home/{self.user}/venv",
            "/opt/venv"
        ]
        
        for venv_dir in venv_paths:
            daemon_path = os.path.join(venv_dir, "bin", "kode-kronical-daemon")
            if os.path.isfile(daemon_path) and os.access(daemon_path, os.X_OK):
                # Store the venv daemon path directly - will be run by venv's Python
                self.daemon_path = daemon_path
                self.info(f"Found daemon in venv: {self.daemon_path}")
                return
        
        # Try which command as fallback
        result = subprocess.run(['which', 'kode-kronical-daemon'], capture_output=True, text=True)
        if result.returncode == 0:
            self.daemon_path = result.stdout.strip()
            self.info(f"Found daemon in PATH: {self.daemon_path}")
            return
        
        # Search user's home directory
        try:
            result = subprocess.run([
                'find', f'/home/{self.user}', '-name', 'kode-kronical-daemon', 
                '-type', 'f', '-executable'
            ], capture_output=True, text=True, stderr=subprocess.DEVNULL)
            
            if result.stdout.strip():
                self.daemon_path = result.stdout.strip().split('\n')[0]
                self.info(f"Found daemon via search: {self.daemon_path}")
                return
        except:
            pass
        
        self.error("Could not find kode-kronical-daemon executable")
        self.error("Please ensure kode-kronical is installed and accessible")
        sys.exit(1)
    
    def find_config_file(self):
        """Find daemon configuration file."""
        self.log("Locating daemon configuration file...")
        
        # Common config locations
        config_paths = [
            f"/home/{self.user}/.config/kode-kronical/daemon.yaml",
            f"/home/{self.user}/.kode-kronical.yaml",
            "/etc/kode-kronical/daemon.yaml",
            "./daemon.yaml",
            "./config/daemon.yaml"
        ]
        
        for path in config_paths:
            if os.path.isfile(path):
                self.config_path = path
                self.info(f"Found config file: {self.config_path}")
                return
        
        # If no config file found, we'll create a default one
        self.warning("No config file found, will create default at /etc/kode-kronical/daemon.yaml")
        self.config_path = "/etc/kode-kronical/daemon.yaml"
        self.create_default_config = True
    
    def read_config_values(self):
        """Read PID file path and other values from config."""
        if not self.config_path:
            # Use defaults if no config file
            self.pid_file = f"/home/{self.user}/.local/share/kode-kronical/daemon.pid"
            self.info(f"Using default PID file: {self.pid_file}")
            return
        
        try:
            import yaml
            with open(self.config_path, 'r') as f:
                config = yaml.safe_load(f)
            
            # Extract PID file path from config
            daemon_config = config.get('daemon', {})
            self.pid_file = daemon_config.get('pid_file', f"/home/{self.user}/.local/share/kode-kronical/daemon.pid")
            self.info(f"Using PID file from config: {self.pid_file}")
            
        except ImportError:
            self.warning("PyYAML not available, trying OmegaConf...")
            try:
                from omegaconf import OmegaConf
                config = OmegaConf.load(self.config_path)
                self.pid_file = config.get('daemon', {}).get('pid_file', f"/home/{self.user}/.local/share/kode-kronical/daemon.pid")
                self.info(f"Using PID file from config (OmegaConf): {self.pid_file}")
            except Exception as e:
                self.warning(f"Could not read config file ({e}), using defaults")
                self.pid_file = f"/home/{self.user}/.local/share/kode-kronical/daemon.pid"
        except Exception as e:
            self.warning(f"Could not read config file ({e}), using defaults")
            self.pid_file = f"/home/{self.user}/.local/share/kode-kronical/daemon.pid"
    
    def create_data_directory(self):
        """Create the data directory with proper permissions."""
        # Always use user directory to avoid permission issues
        data_dir = f"/home/{self.user}/.local/share/kode-kronical"
        
        # Create the directory if it doesn't exist
        if not os.path.exists(data_dir):
            os.makedirs(data_dir, mode=0o755, exist_ok=True)
            # Set ownership to the user who will run the daemon
            import pwd
            uid = pwd.getpwnam(self.user).pw_uid
            gid = pwd.getpwnam(self.user).pw_gid
            os.chown(data_dir, uid, gid)
            self.info(f"Created data directory: {data_dir}")
        
        return data_dir
    
    def ensure_config_exists(self):
        """Ensure a config file exists, creating a default if needed."""
        if self.create_default_config and self.config_path:
            config_dir = os.path.dirname(self.config_path)
            if not os.path.exists(config_dir):
                os.makedirs(config_dir, mode=0o755, exist_ok=True)
                self.info(f"Created config directory: {config_dir}")
            
            if not os.path.exists(self.config_path):
                # Create data directory first and use it in config
                data_dir = self.create_data_directory()
                
                default_config = f"""daemon:
  sample_interval: 1.0
  data_dir: {data_dir}
  enable_network_monitoring: true
  data_retention_hours: 24
  pid_file: /var/run/kode-kronical-daemon.pid
"""
                with open(self.config_path, 'w') as f:
                    f.write(default_config)
                os.chmod(self.config_path, 0o644)
                self.info(f"Created default config file: {self.config_path}")
    
    def stop_existing_daemon(self):
        """Stop any existing daemon processes."""
        self.log("Stopping any existing daemon processes...")
        
        # Try to stop via daemon command
        try:
            subprocess.run(['sudo', '-u', self.user, self.daemon_path, 'stop'], 
                          check=False, capture_output=True)
            self.info("Stopped daemon via command")
        except:
            self.info("No daemon was running via command")
        
        # Kill any remaining processes
        try:
            result = subprocess.run(['pgrep', '-f', 'kode-kronical-daemon'], 
                                  capture_output=True, text=True)
            if result.returncode == 0:
                self.warning("Killing remaining daemon processes...")
                subprocess.run(['pkill', '-f', 'kode-kronical-daemon'], check=False)
                import time
                time.sleep(1)
        except:
            pass
    
    def create_service_file(self):
        """Create systemd service file."""
        self.log("Creating systemd service file...")
        
        # Always use config file - we ensure one exists
        # Use Type=simple - systemd will track the final process after double-fork
        exec_start = f"{self.daemon_path} -c {self.config_path} start"
        exec_stop = f"{self.daemon_path} -c {self.config_path} stop"
        exec_reload = f"{self.daemon_path} -c {self.config_path} restart"
        
        # Ensure PID file directory exists
        pid_dir = os.path.dirname(self.pid_file)
        if not os.path.exists(pid_dir):
            os.makedirs(pid_dir, exist_ok=True)
            try:
                uid = int(subprocess.run(['id', '-u', self.user], capture_output=True, text=True).stdout.strip())
                gid = int(subprocess.run(['id', '-g', self.user], capture_output=True, text=True).stdout.strip())
                os.chown(pid_dir, uid, gid)
            except:
                self.warning(f"Could not set ownership for {pid_dir}")
        
        service_content = f"""[Unit]
Description=kode-kronical System Monitoring Daemon
Documentation=https://github.com/jeremycharlesgillespie/kode-kronical
After=network.target

[Service]
Type=simple
ExecStart={exec_start}
ExecStop={exec_stop}
ExecReload={exec_reload}
Restart=on-failure
RestartSec=10
User={self.user}
Environment=HOME=/home/{self.user}
WorkingDirectory=/home/{self.user}

[Install]
WantedBy=multi-user.target
"""
        
        with open(self.service_file, 'w') as f:
            f.write(service_content)
        
        os.chmod(self.service_file, 0o644)
        self.log(f"Created service file: {self.service_file}")
    
    def install_service(self):
        """Install and start the service."""
        self.log("Installing and starting systemd service...")
        
        # Reload systemd
        subprocess.run(['systemctl', 'daemon-reload'], check=True)
        self.info("Reloaded systemd configuration")
        
        # Enable service (start at boot)
        subprocess.run(['systemctl', 'enable', self.service_name], check=True)
        self.info("Enabled service for automatic startup")
        
        # Start service now
        subprocess.run(['systemctl', 'start', self.service_name], check=True)
        self.info("Started kode-kronical-daemon service")
        
        # Wait and check status
        import time
        time.sleep(2)
        
        result = subprocess.run(['systemctl', 'is-active', '--quiet', self.service_name])
        if result.returncode == 0:
            self.log("✓ Service started successfully")
        else:
            self.error("✗ Service failed to start")
            subprocess.run(['systemctl', 'status', self.service_name])
            sys.exit(1)
    
    def verify_service(self):
        """Verify service installation."""
        self.log("Verifying service installation...")
        
        # Check if enabled
        result = subprocess.run(['systemctl', 'is-enabled', '--quiet', self.service_name])
        if result.returncode == 0:
            self.info("✓ Service enabled for boot startup")
        else:
            self.warning("✗ Service not enabled")
        
        # Check if active
        result = subprocess.run(['systemctl', 'is-active', '--quiet', self.service_name])
        if result.returncode == 0:
            self.info("✓ Service is running")
            print()
            self.info("Service Status:")
            subprocess.run(['systemctl', 'status', self.service_name, '--no-pager', '-l'])
        else:
            self.warning("✗ Service is not running")
    
    def print_usage(self):
        """Print usage information."""
        print()
        self.log("Installation complete!")
        print()
        self.info("The kode-kronical-daemon is now installed as a systemd service and will:")
        print("  • Start automatically at boot")
        print("  • Restart automatically if it crashes")
        print("  • Run in the background collecting system metrics")
        print()
        self.info("Useful commands:")
        print("  sudo systemctl status kode-kronical-daemon    # Check status")
        print("  sudo systemctl stop kode-kronical-daemon      # Stop service")
        print("  sudo systemctl start kode-kronical-daemon     # Start service")
        print("  sudo systemctl restart kode-kronical-daemon   # Restart service")
        print("  sudo systemctl disable kode-kronical-daemon   # Disable boot startup")
        print("  sudo journalctl -u kode-kronical-daemon -f    # View live logs")
        print()
    
    def install(self):
        """Main installation process."""
        self.log("Starting kode-kronical-daemon systemd service installation...")
        
        self.check_root()
        self.check_platform()
        self.find_daemon()
        self.find_config_file()
        self.ensure_config_exists()  # Create default config if needed
        self.read_config_values()
        self.create_data_directory()  # Ensure data directory exists with proper permissions
        self.stop_existing_daemon()
        self.create_service_file()
        self.install_service()
        self.verify_service()
        self.print_usage()
        
        self.log("Installation completed successfully!")
    
    def uninstall(self):
        """Uninstall the service."""
        self.log("Uninstalling kode-kronical-daemon service...")
        
        subprocess.run(['systemctl', 'stop', self.service_name], check=False)
        subprocess.run(['systemctl', 'disable', self.service_name], check=False)
        
        if os.path.exists(self.service_file):
            os.remove(self.service_file)
        
        subprocess.run(['systemctl', 'daemon-reload'], check=True)
        self.log("Service uninstalled")


def main():
    """Main entry point."""
    if len(sys.argv) > 1 and sys.argv[1] in ['-h', '--help', 'help']:
        print("""
install-kode-kronical-service - Install kode-kronical-daemon as a systemd service

This tool installs kode-kronical-daemon as a system service that automatically
starts at boot and restarts on failure.

Usage:
    sudo install-kode-kronical-service           # Install service
    sudo install-kode-kronical-service uninstall # Remove service
    
Requirements:
  - Linux with systemd
  - kode-kronical package installed
  - Root privileges (sudo)

After installation, the daemon will:
  • Start automatically at boot
  • Restart automatically if it crashes  
  • Run in the background collecting system metrics
  
Management commands:
  sudo systemctl status kode-kronical-daemon     # Check status
  sudo systemctl stop kode-kronical-daemon       # Stop service
  sudo systemctl start kode-kronical-daemon      # Start service
  sudo systemctl restart kode-kronical-daemon    # Restart service
  sudo journalctl -u kode-kronical-daemon -f     # View live logs
        """)
        return
    
    installer = ServiceInstaller()
    
    if len(sys.argv) > 1 and sys.argv[1] == 'uninstall':
        installer.uninstall()
    else:
        installer.install()


if __name__ == "__main__":
    main()