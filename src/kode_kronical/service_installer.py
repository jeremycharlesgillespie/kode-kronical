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
    def __init__(self, user_service=True):
        self.service_name = "kode-kronical-daemon"
        self.user_service = user_service
        self.daemon_path = None
        self.config_path = None
        self.pid_file = None
        self.user = os.environ.get('SUDO_USER') if not user_service else os.environ.get('USER')
        self.create_default_config = False
        
        if user_service:
            # User service configuration
            self.service_file = f"{os.path.expanduser('~')}/.config/systemd/user/{self.service_name}.service"
            self.config_dir = f"{os.path.expanduser('~')}/.config/kode-kronical"
            self.data_dir = f"{os.path.expanduser('~')}/.local/share/kode-kronical"
        else:
            # System service configuration
            self.service_file = f"/etc/systemd/system/{self.service_name}.service"
            self.config_dir = "/etc/kode-kronical"
            self.data_dir = f"/home/{self.user}/.local/share/kode-kronical"
        
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
        """Check if running as root (only for system services)."""
        if not self.user_service and os.geteuid() != 0:
            self.error("System service installation must be run as root (use sudo)")
            self.error("For user service installation (default), run without --system flag")
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
        
        if self.user_service:
            # For user service, check user's home directory first
            home_dir = os.path.expanduser('~')
            venv_paths = [
                f"{home_dir}/.venv",
                f"{home_dir}/venv"
            ]
        else:
            # For system service, check user and system locations
            venv_paths = [
                f"/home/{self.user}/.venv",
                f"/home/{self.user}/venv",
                "/opt/venv"
            ]
        
        for venv_dir in venv_paths:
            daemon_path = os.path.join(venv_dir, "bin", "kode-kronical-daemon")
            if os.path.isfile(daemon_path) and os.access(daemon_path, os.X_OK):
                self.daemon_path = daemon_path
                self.info(f"Found daemon in venv: {self.daemon_path}")
                return
        
        # Try which command as fallback
        result = subprocess.run(['which', 'kode-kronical-daemon'], capture_output=True, text=True)
        if result.returncode == 0:
            self.daemon_path = result.stdout.strip()
            self.info(f"Found daemon in PATH: {self.daemon_path}")
            return
        
        self.error("Could not find kode-kronical-daemon executable")
        self.error("Please ensure kode-kronical is installed and accessible")
        sys.exit(1)
    
    def find_config_file(self):
        """Find daemon configuration file."""
        self.log("Locating daemon configuration file...")
        
        if self.user_service:
            # User service config locations
            home_dir = os.path.expanduser('~')
            config_paths = [
                f"{home_dir}/.config/kode-kronical/daemon.yaml",
                f"{home_dir}/.kode-kronical.yaml",
                "./daemon.yaml",
                "./config/daemon.yaml"
            ]
            default_config_path = f"{home_dir}/.config/kode-kronical/daemon.yaml"
        else:
            # System service config locations
            config_paths = [
                f"/home/{self.user}/.config/kode-kronical/daemon.yaml",
                f"/home/{self.user}/.kode-kronical.yaml",
                "/etc/kode-kronical/daemon.yaml",
                "./daemon.yaml",
                "./config/daemon.yaml"
            ]
            default_config_path = "/etc/kode-kronical/daemon.yaml"
        
        for path in config_paths:
            if os.path.isfile(path):
                self.config_path = path
                self.info(f"Found config file: {self.config_path}")
                return
        
        # If no config file found, we'll create a default one
        service_type = "user service" if self.user_service else "system service"
        self.warning(f"No config file found, will create default for {service_type}")
        self.config_path = default_config_path
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
  pid_file: ~/.local/share/kode-kronical/daemon.pid
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
        service_type = "user service" if self.user_service else "system service"
        self.log(f"Creating systemd {service_type} file...")
        
        # Ensure service file directory exists
        service_dir = os.path.dirname(self.service_file)
        if not os.path.exists(service_dir):
            os.makedirs(service_dir, exist_ok=True)
            self.info(f"Created service directory: {service_dir}")
        
        # Use --foreground flag for both user and system services
        exec_start = f"{self.daemon_path} -c {self.config_path} start --foreground"
        exec_stop = f"{self.daemon_path} -c {self.config_path} stop"
        exec_reload = f"{self.daemon_path} -c {self.config_path} restart"
        
        if self.user_service:
            # User service configuration
            home_dir = os.path.expanduser('~')
            service_content = f"""[Unit]
Description=kode-kronical System Monitoring Daemon (User Service)
Documentation=https://github.com/jeremycharlesgillespie/kode-kronical
After=graphical-session.target

[Service]
Type=simple
ExecStart={exec_start}
Restart=on-failure
RestartSec=10
StandardOutput=journal
StandardError=journal
Environment=HOME={home_dir}
Environment=USER={os.environ.get('USER', 'user')}
WorkingDirectory={home_dir}

[Install]
WantedBy=default.target
"""
        else:
            # System service configuration
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
StandardOutput=journal
StandardError=journal
User={self.user}
Environment=HOME=/home/{self.user}
Environment=USER={self.user}
WorkingDirectory=/home/{self.user}

[Install]
WantedBy=multi-user.target
"""
        
        with open(self.service_file, 'w') as f:
            f.write(service_content)
        
        os.chmod(self.service_file, 0o644)
        self.log(f"Created {service_type} file: {self.service_file}")
    
    def install_service(self):
        """Install and start the service."""
        service_type = "user service" if self.user_service else "system service"
        self.log(f"Installing and starting systemd {service_type}...")
        
        if self.user_service:
            # User service commands
            systemctl_cmd = ['systemctl', '--user']
            
            # Enable lingering so service can start without user login
            try:
                subprocess.run(['sudo', 'loginctl', 'enable-linger', os.environ.get('USER')], 
                              check=False, capture_output=True)
                self.info("Enabled user lingering (service can start without login)")
            except:
                self.warning("Could not enable lingering (service requires login to start)")
        else:
            # System service commands
            systemctl_cmd = ['systemctl']
        
        # Reload systemd
        subprocess.run(systemctl_cmd + ['daemon-reload'], check=True)
        self.info(f"Reloaded systemd configuration")
        
        # Enable service (start at boot/login)
        subprocess.run(systemctl_cmd + ['enable', self.service_name], check=True)
        startup_msg = "automatic startup at login" if self.user_service else "automatic startup at boot"
        self.info(f"Enabled service for {startup_msg}")
        
        # Start service now
        subprocess.run(systemctl_cmd + ['start', self.service_name], check=True)
        self.info(f"Started kode-kronical-daemon {service_type}")
        
        # Wait and check status
        import time
        time.sleep(2)
        
        result = subprocess.run(systemctl_cmd + ['is-active', '--quiet', self.service_name])
        if result.returncode == 0:
            self.log(f"✓ {service_type.capitalize()} started successfully")
        else:
            self.error(f"✗ {service_type.capitalize()} failed to start")
            subprocess.run(systemctl_cmd + ['status', self.service_name])
            sys.exit(1)
    
    def verify_service(self):
        """Verify service installation."""
        service_type = "user service" if self.user_service else "system service"
        self.log(f"Verifying {service_type} installation...")
        
        systemctl_cmd = ['systemctl', '--user'] if self.user_service else ['systemctl']
        
        # Check if enabled
        result = subprocess.run(systemctl_cmd + ['is-enabled', '--quiet', self.service_name])
        startup_msg = "login startup" if self.user_service else "boot startup"
        if result.returncode == 0:
            self.info(f"✓ Service enabled for {startup_msg}")
        else:
            self.warning(f"✗ Service not enabled for {startup_msg}")
        
        # Check if active
        result = subprocess.run(systemctl_cmd + ['is-active', '--quiet', self.service_name])
        if result.returncode == 0:
            self.info(f"✓ {service_type.capitalize()} is running")
            print()
            self.info("Service Status:")
            subprocess.run(systemctl_cmd + ['status', self.service_name, '--no-pager', '-l'])
        else:
            self.warning(f"✗ {service_type.capitalize()} is not running")
    
    def print_usage(self):
        """Print usage information."""
        print()
        self.log("Installation complete!")
        print()
        self.info("The kode-kronical-daemon is now installed as a systemd service and will:")
        
        if self.user_service:
            print("  • Start automatically at login")
        else:
            print("  • Start automatically at boot")
        
        print("  • Restart automatically if it crashes")
        print("  • Run in the background collecting system metrics")
        print()
        self.info("Useful commands:")
        
        if self.user_service:
            # User service commands (no sudo needed)
            print("  systemctl --user status kode-kronical-daemon    # Check status")
            print("  systemctl --user stop kode-kronical-daemon      # Stop service")
            print("  systemctl --user start kode-kronical-daemon     # Start service")
            print("  systemctl --user restart kode-kronical-daemon   # Restart service")
            print("  systemctl --user disable kode-kronical-daemon   # Disable login startup")
            print("  journalctl --user -u kode-kronical-daemon -f    # View live logs")
        else:
            # System service commands (need sudo)
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
        service_type = "user service" if self.user_service else "system service"
        self.log(f"Uninstalling kode-kronical-daemon {service_type}...")
        
        systemctl_cmd = ['systemctl', '--user'] if self.user_service else ['systemctl']
        
        subprocess.run(systemctl_cmd + ['stop', self.service_name], check=False)
        subprocess.run(systemctl_cmd + ['disable', self.service_name], check=False)
        
        if os.path.exists(self.service_file):
            os.remove(self.service_file)
            self.info(f"Removed service file: {self.service_file}")
        
        subprocess.run(systemctl_cmd + ['daemon-reload'], check=True)
        self.log(f"{service_type.capitalize()} uninstalled")


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Install kode-kronical-daemon as a systemd service",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  install-kode-kronical-service                   # Install user service (default, no sudo needed)
  install-kode-kronical-service --system          # Install system service (requires sudo)
  install-kode-kronical-service uninstall         # Remove user service
  sudo install-kode-kronical-service --system uninstall  # Remove system service

User service (DEFAULT):
  • Starts when you log in
  • No sudo required
  • Uses ~/.config/systemd/user/
  • Managed with: systemctl --user <command> kode-kronical-daemon

System service:
  • Starts at boot
  • Requires sudo
  • Uses /etc/systemd/system/
  • Managed with: sudo systemctl <command> kode-kronical-daemon
        """
    )
    
    parser.add_argument('command', nargs='?', default='install',
                       choices=['install', 'uninstall'],
                       help='Command to execute (default: install)')
    parser.add_argument('--system', action='store_true',
                       help='Install as system service instead of user service (requires sudo)')
    parser.add_argument('--user', action='store_true',
                       help='Install as user service (default behavior, kept for compatibility)')
    
    args = parser.parse_args()
    
    # Determine service type: system service only if --system is explicitly specified
    # Default is user service (user_service=True)
    user_service = not args.system  # User service unless --system is specified
    
    installer = ServiceInstaller(user_service=user_service)
    
    if args.command == 'uninstall':
        installer.uninstall()
    else:
        installer.install()


if __name__ == "__main__":
    main()