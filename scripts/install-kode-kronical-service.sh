#!/bin/bash
# Quick systemd service installer for kode-kronical-daemon
# This script creates and enables the systemd service for automatic boot startup

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log() {
    echo -e "${GREEN}[$(date +'%H:%M:%S')] $1${NC}"
}

error() {
    echo -e "${RED}[ERROR] $1${NC}" >&2
}

warning() {
    echo -e "${YELLOW}[WARNING] $1${NC}"
}

info() {
    echo -e "${BLUE}[INFO] $1${NC}"
}

# Check if running as root
check_root() {
    if [[ $EUID -ne 0 ]]; then
        error "This script must be run as root (use sudo)"
        exit 1
    fi
}

# Find kode-kronical-daemon executable
find_daemon() {
    log "Locating kode-kronical-daemon executable..."
    
    # Try common locations
    DAEMON_PATH=""
    
    # Search common virtual environment locations first (preferred)
    for venv_path in "/home/$SUDO_USER/.venv" "/home/$SUDO_USER/venv" "/opt/venv"; do
        if [[ -f "$venv_path/bin/kode-kronical-daemon" ]]; then
            # Use the venv's kode-kronical-daemon directly
            DAEMON_PATH="$venv_path/bin/kode-kronical-daemon"
            info "Found daemon in venv: $DAEMON_PATH"
            break
        fi
    done
    
    # Check if it's in PATH as fallback
    if [[ -z "$DAEMON_PATH" ]] && command -v kode-kronical-daemon >/dev/null 2>&1; then
        DAEMON_PATH=$(which kode-kronical-daemon)
        info "Found daemon in PATH: $DAEMON_PATH"
        
        # Search user's home directory
        if [[ -z "$DAEMON_PATH" && -n "$SUDO_USER" ]]; then
            SEARCH_PATH=$(find "/home/$SUDO_USER" -name "kode-kronical-daemon" -type f -executable 2>/dev/null | head -1)
            if [[ -n "$SEARCH_PATH" ]]; then
                DAEMON_PATH="$SEARCH_PATH"
                info "Found daemon via search: $DAEMON_PATH"
            fi
        fi
    fi
    
    if [[ -z "$DAEMON_PATH" ]]; then
        error "Could not find kode-kronical-daemon executable"
        error "Please ensure kode-kronical is installed and accessible"
        exit 1
    fi
    
    # Verify it's executable
    if [[ ! -x "$DAEMON_PATH" ]]; then
        error "Daemon found but not executable: $DAEMON_PATH"
        exit 1
    fi
    
    log "Using daemon at: $DAEMON_PATH"
}

# Create necessary directories
create_directories() {
    log "Creating necessary directories..."
    
    # Create config directory
    mkdir -p /etc/kode-kronical
    chmod 755 /etc/kode-kronical
    
    # Always use user data directory to avoid permission issues
    DATA_DIR="/home/$SUDO_USER/.local/share/kode-kronical"
    mkdir -p "$DATA_DIR"
    chown "$SUDO_USER:$SUDO_USER" "$DATA_DIR"
    chmod 755 "$DATA_DIR"
    info "Created user data directory: $DATA_DIR"
    
    # Create PID directory
    mkdir -p /var/run
    chmod 755 /var/run
}

# Stop existing daemon if running
stop_existing_daemon() {
    log "Stopping any existing daemon processes..."
    
    # Try to stop via daemon command
    if sudo -u "$SUDO_USER" "$DAEMON_PATH" stop 2>/dev/null; then
        info "Stopped daemon via command"
    else
        info "No daemon was running via command"
    fi
    
    # Kill any remaining processes
    if pgrep -f "kode-kronical-daemon" >/dev/null; then
        warning "Killing remaining daemon processes..."
        pkill -f "kode-kronical-daemon" || true
        sleep 1
    fi
}

# Create systemd service file
create_service_file() {
    log "Creating systemd service file..."
    
    SERVICE_FILE="/etc/systemd/system/kode-kronical-daemon.service"
    
    cat > "$SERVICE_FILE" << EOF
[Unit]
Description=kode-kronical System Monitoring Daemon
Documentation=https://github.com/jeremycharlesgillespie/kode-kronical
After=network.target

[Service]
Type=simple
ExecStart=$DAEMON_PATH -c /etc/kode-kronical/daemon.yaml start --foreground
ExecStop=$DAEMON_PATH -c /etc/kode-kronical/daemon.yaml stop
ExecReload=$DAEMON_PATH -c /etc/kode-kronical/daemon.yaml restart
PIDFile=/var/run/kode-kronical-daemon.pid
Restart=on-failure
RestartSec=10
User=$SUDO_USER
Environment=HOME=/home/$SUDO_USER
WorkingDirectory=/home/$SUDO_USER

# Security settings
NoNewPrivileges=true
PrivateTmp=true
ReadWritePaths=/home/$SUDO_USER/.local /home/$SUDO_USER/.config /var/run

# Resource limits
LimitNOFILE=4096
CPUQuota=20%
MemoryMax=256M

[Install]
WantedBy=multi-user.target
EOF

    chmod 644 "$SERVICE_FILE"
    log "Created service file: $SERVICE_FILE"
}

# Install and start service
install_service() {
    log "Installing and starting systemd service..."
    
    # Reload systemd
    systemctl daemon-reload
    info "Reloaded systemd configuration"
    
    # Enable service (start at boot)
    systemctl enable kode-kronical-daemon
    info "Enabled service for automatic startup"
    
    # Start service now
    systemctl start kode-kronical-daemon
    info "Started kode-kronical-daemon service"
    
    # Wait a moment and check status
    sleep 2
    if systemctl is-active --quiet kode-kronical-daemon; then
        log "✓ Service started successfully"
    else
        error "✗ Service failed to start"
        systemctl status kode-kronical-daemon
        exit 1
    fi
}

# Verify installation
verify_service() {
    log "Verifying service installation..."
    
    # Check if enabled
    if systemctl is-enabled --quiet kode-kronical-daemon; then
        info "✓ Service enabled for boot startup"
    else
        warning "✗ Service not enabled"
    fi
    
    # Check if active
    if systemctl is-active --quiet kode-kronical-daemon; then
        info "✓ Service is running"
        
        # Show status
        echo
        info "Service Status:"
        systemctl status kode-kronical-daemon --no-pager -l
    else
        warning "✗ Service is not running"
    fi
}

# Print usage information
print_usage() {
    echo
    log "Installation complete!"
    echo
    info "The kode-kronical-daemon is now installed as a systemd service and will:"
    echo "  • Start automatically at boot"
    echo "  • Restart automatically if it crashes"
    echo "  • Run in the background collecting system metrics"
    echo
    info "Useful commands:"
    echo "  sudo systemctl status kode-kronical-daemon    # Check status"
    echo "  sudo systemctl stop kode-kronical-daemon      # Stop service"
    echo "  sudo systemctl start kode-kronical-daemon     # Start service"
    echo "  sudo systemctl restart kode-kronical-daemon   # Restart service"
    echo "  sudo systemctl disable kode-kronical-daemon   # Disable boot startup"
    echo "  sudo journalctl -u kode-kronical-daemon -f    # View live logs"
    echo
}

# Main function
main() {
    log "Starting kode-kronical-daemon systemd service installation..."
    
    check_root
    find_daemon
    create_directories  # Create directories early before any daemon operations
    stop_existing_daemon
    create_service_file
    install_service
    verify_service
    print_usage
    
    log "Installation completed successfully!"
}

# Handle command line arguments
case "${1:-install}" in
    install)
        main
        ;;
    uninstall)
        log "Uninstalling kode-kronical-daemon service..."
        systemctl stop kode-kronical-daemon 2>/dev/null || true
        systemctl disable kode-kronical-daemon 2>/dev/null || true
        rm -f /etc/systemd/system/kode-kronical-daemon.service
        systemctl daemon-reload
        log "Service uninstalled"
        ;;
    *)
        echo "Usage: $0 [install|uninstall]"
        echo
        echo "This script installs kode-kronical-daemon as a systemd service"
        echo "that automatically starts at boot and restarts on failure."
        echo
        echo "Examples:"
        echo "  sudo $0 install      # Install and start service"
        echo "  sudo $0 uninstall    # Stop and remove service"
        exit 1
        ;;
esac