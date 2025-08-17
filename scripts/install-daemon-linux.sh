#!/bin/bash
# kode-kronical-daemon installation script for Linux
# Supports Ubuntu/Debian, CentOS/RHEL/Fedora, and Arch Linux

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
INSTALL_USER="kode-kronical"
INSTALL_DIR="/usr/local/bin"
CONFIG_DIR="/etc/kode-kronical"
DATA_DIR="/var/lib/kode-kronical"
LOG_DIR="/var/log/kode-kronical"
SERVICE_FILE="/etc/systemd/system/kode-kronical-daemon.service"

# Logging function
log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')] $1${NC}"
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

# Detect Linux distribution
detect_distro() {
    if [[ -f /etc/os-release ]]; then
        . /etc/os-release
        DISTRO=$ID
        VERSION=$VERSION_ID
    elif [[ -f /etc/redhat-release ]]; then
        DISTRO="rhel"
    elif [[ -f /etc/debian_version ]]; then
        DISTRO="debian"
    else
        DISTRO="unknown"
    fi
    
    log "Detected distribution: $DISTRO"
}

# Install Python and pip based on distribution
install_python() {
    log "Installing Python and pip..."
    
    case $DISTRO in
        ubuntu|debian)
            apt-get update
            apt-get install -y python3 python3-pip python3-venv
            ;;
        centos|rhel|fedora)
            if command -v dnf >/dev/null 2>&1; then
                dnf install -y python3 python3-pip
            else
                yum install -y python3 python3-pip
            fi
            ;;
        arch|manjaro)
            pacman -Sy --noconfirm python python-pip
            ;;
        *)
            error "Unsupported distribution: $DISTRO"
            exit 1
            ;;
    esac
}

# Install system dependencies
install_system_deps() {
    log "Installing system dependencies..."
    
    case $DISTRO in
        ubuntu|debian)
            apt-get install -y build-essential python3-dev
            ;;
        centos|rhel|fedora)
            if command -v dnf >/dev/null 2>&1; then
                dnf groupinstall -y "Development Tools"
                dnf install -y python3-devel
            else
                yum groupinstall -y "Development Tools"
                yum install -y python3-devel
            fi
            ;;
        arch|manjaro)
            pacman -S --noconfirm base-devel
            ;;
    esac
}

# Install Python requirements
install_requirements() {
    log "Installing Python requirements..."
    
    # Install core requirements
    if [[ -f "requirements.txt" ]]; then
        pip3 install -r requirements.txt
    else
        warning "requirements.txt not found, installing basic dependencies"
        pip3 install omegaconf
    fi
    
    # Install psutil for system monitoring
    log "Installing psutil..."
    pip3 install psutil
    
    # Install additional dependencies for daemon
    pip3 install pyyaml
}

# Create system user
create_user() {
    log "Creating system user: $INSTALL_USER"
    
    if id "$INSTALL_USER" &>/dev/null; then
        info "User $INSTALL_USER already exists"
    else
        useradd -r -s /bin/false -d "$DATA_DIR" "$INSTALL_USER"
        log "Created user: $INSTALL_USER"
    fi
}

# Create directories
create_directories() {
    log "Creating directories..."
    
    mkdir -p "$CONFIG_DIR" "$DATA_DIR" "$LOG_DIR"
    chown "$INSTALL_USER:$INSTALL_USER" "$DATA_DIR" "$LOG_DIR"
    chmod 755 "$CONFIG_DIR"
    chmod 750 "$DATA_DIR" "$LOG_DIR"
    
    log "Created directories: $CONFIG_DIR, $DATA_DIR, $LOG_DIR"
}

# Install daemon executable
install_daemon() {
    log "Installing kode-kronical-daemon..."
    
    # Get the directory where this script is located
    local script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    local project_root="$(dirname "$script_dir")"
    local daemon_path="$project_root/kode-kronical-daemon"
    
    # Check for daemon executable in project root
    if [[ ! -f "$daemon_path" ]]; then
        error "kode-kronical-daemon executable not found at: $daemon_path"
        error "Please run this script from the kode-kronical project directory or ensure kode-kronical-daemon exists"
        exit 1
    fi
    
    cp "$daemon_path" "$INSTALL_DIR/"
    chmod +x "$INSTALL_DIR/kode-kronical-daemon"
    chown root:root "$INSTALL_DIR/kode-kronical-daemon"
    
    log "Installed daemon to: $INSTALL_DIR/kode-kronical-daemon"
}

# Install systemd service
install_service() {
    log "Installing systemd service..."
    
    # Get the directory where this script is located
    local script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    local service_file="$script_dir/kode-kronical-daemon.service"
    
    if [[ ! -f "$service_file" ]]; then
        error "Service file not found: $service_file"
        exit 1
    fi
    
    cp "$service_file" "$SERVICE_FILE"
    chmod 644 "$SERVICE_FILE"
    
    systemctl daemon-reload
    log "Installed systemd service"
}

# Install configuration
install_config() {
    log "Installing configuration..."
    
    # Get the directory where this script is located
    local script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    local project_root="$(dirname "$script_dir")"
    local example_config="$project_root/config/daemon.yaml.example"
    
    if [[ -f "$example_config" ]]; then
        cp "$example_config" "$CONFIG_DIR/daemon.yaml"
    else
        # Create basic config if example doesn't exist
        cat > "$CONFIG_DIR/daemon.yaml" << EOF
daemon:
  pid_file: /var/run/kode-kronical-daemon.pid
  log_file: $LOG_DIR/daemon.log
  data_dir: $DATA_DIR
  sample_interval: 1.0
  data_retention_hours: 168
  enable_network_monitoring: true

monitoring:
  auto_track_python: true
  cpu_alert_threshold: 90
  memory_alert_threshold: 85

export:
  format: json
  compress: true
  batch_size: 1000
EOF
    fi
    
    chown "$INSTALL_USER:$INSTALL_USER" "$CONFIG_DIR/daemon.yaml"
    chmod 640 "$CONFIG_DIR/daemon.yaml"
    
    log "Installed configuration to: $CONFIG_DIR/daemon.yaml"
}

# Start and enable service
start_service() {
    log "Starting kode-kronical-daemon service..."
    
    systemctl enable kode-kronical-daemon
    systemctl start kode-kronical-daemon
    
    # Wait a moment and check status
    sleep 2
    if systemctl is-active --quiet kode-kronical-daemon; then
        log "kode-kronical-daemon started successfully"
    else
        error "Failed to start kode-kronical-daemon"
        systemctl status kode-kronical-daemon
        exit 1
    fi
}

# Verify installation
verify_installation() {
    log "Verifying installation..."
    
    # Check if daemon is running
    if systemctl is-active --quiet kode-kronical-daemon; then
        info "✓ Service is running"
    else
        warning "✗ Service is not running"
    fi
    
    # Check if data files are being created
    sleep 3
    if ls "$DATA_DIR"/metrics_*.json >/dev/null 2>&1; then
        info "✓ Data files are being created"
    else
        warning "✗ No data files found yet (this is normal for new installations)"
    fi
    
    # Test daemon status
    if "$INSTALL_DIR/kode-kronical-daemon" status >/dev/null 2>&1; then
        info "✓ Daemon status command works"
    else
        warning "✗ Daemon status command failed"
    fi
}

# Print usage information
print_usage() {
    echo
    log "Installation complete!"
    echo
    info "Usage:"
    echo "  sudo systemctl status kode-kronical-daemon    # Check status"
    echo "  sudo systemctl stop kode-kronical-daemon      # Stop daemon"
    echo "  sudo systemctl start kode-kronical-daemon     # Start daemon"
    echo "  sudo systemctl restart kode-kronical-daemon   # Restart daemon"
    echo "  sudo journalctl -u kode-kronical-daemon -f    # View logs"
    echo
    info "Configuration:"
    echo "  Config file: $CONFIG_DIR/daemon.yaml"
    echo "  Data directory: $DATA_DIR"
    echo "  Log directory: $LOG_DIR"
    echo
    info "KodeKronical Integration:"
    echo "  The daemon is now running and collecting system metrics."
    echo "  Your KodeKronical applications will automatically detect and use it."
    echo
}

# Main installation function
main() {
    log "Starting kode-kronical-daemon installation for Linux..."
    
    check_root
    detect_distro
    install_python
    install_system_deps
    install_requirements
    create_user
    create_directories
    install_daemon
    install_service
    install_config
    start_service
    verify_installation
    print_usage
    
    log "Installation completed successfully!"
}

# Handle command line arguments
case "${1:-install}" in
    install)
        main
        ;;
    uninstall)
        log "Uninstalling kode-kronical-daemon..."
        systemctl stop kode-kronical-daemon 2>/dev/null || true
        systemctl disable kode-kronical-daemon 2>/dev/null || true
        rm -f "$SERVICE_FILE"
        rm -f "$INSTALL_DIR/kode-kronical-daemon"
        rm -rf "$CONFIG_DIR" "$DATA_DIR" "$LOG_DIR"
        userdel "$INSTALL_USER" 2>/dev/null || true
        systemctl daemon-reload
        log "Uninstallation complete"
        ;;
    *)
        echo "Usage: $0 [install|uninstall]"
        exit 1
        ;;
esac