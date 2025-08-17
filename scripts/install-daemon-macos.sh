#!/bin/bash
# kode-kronical-daemon installation script for macOS
# Supports both Intel and Apple Silicon Macs

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
INSTALL_DIR="/usr/local/bin"
CONFIG_DIR="/usr/local/etc/kode-kronical"
DATA_DIR="/usr/local/var/kode-kronical"
LOG_DIR="/usr/local/var/log/kode-kronical"
PLIST_FILE="/Library/LaunchDaemons/com.kodekronical.daemon.plist"
SERVICE_NAME="com.kodekronical.daemon"

# User installation paths (for non-root)
USER_INSTALL_DIR="$HOME/.local/bin"
USER_CONFIG_DIR="$HOME/.config/kode-kronical"
USER_DATA_DIR="$HOME/.local/share/kode-kronical"
USER_LOG_DIR="$HOME/.local/share/kode-kronical/logs"
USER_PLIST_FILE="$HOME/Library/LaunchAgents/com.kodekronical.daemon.plist"

# Logging functions
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
check_privileges() {
    if [[ $EUID -eq 0 ]]; then
        SYSTEM_INSTALL=true
        log "Running system installation (root privileges detected)"
    else
        SYSTEM_INSTALL=false
        log "Running user installation (no root privileges)"
        # Update paths for user installation
        INSTALL_DIR="$USER_INSTALL_DIR"
        CONFIG_DIR="$USER_CONFIG_DIR"
        DATA_DIR="$USER_DATA_DIR"
        LOG_DIR="$USER_LOG_DIR"
        PLIST_FILE="$USER_PLIST_FILE"
    fi
}

# Check macOS version
check_macos_version() {
    local version=$(sw_vers -productVersion)
    local major=$(echo $version | cut -d. -f1)
    local minor=$(echo $version | cut -d. -f2)
    
    log "Detected macOS version: $version"
    
    if [[ $major -lt 10 ]] || [[ $major -eq 10 && $minor -lt 15 ]]; then
        warning "macOS 10.15 (Catalina) or later is recommended"
    fi
}

# Check and install Homebrew
install_homebrew() {
    if command -v brew >/dev/null 2>&1; then
        log "Homebrew already installed"
        return
    fi
    
    log "Installing Homebrew..."
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
    
    # Add Homebrew to PATH for Apple Silicon Macs
    if [[ -f "/opt/homebrew/bin/brew" ]]; then
        export PATH="/opt/homebrew/bin:$PATH"
        echo 'export PATH="/opt/homebrew/bin:$PATH"' >> ~/.zshrc
    fi
}

# Install Python via Homebrew
install_python() {
    log "Checking Python installation..."
    
    if command -v python3 >/dev/null 2>&1; then
        local python_version=$(python3 --version 2>&1)
        if [[ $python_version =~ Python\ ([0-9]+)\.([0-9]+) ]]; then
            local major=${BASH_REMATCH[1]}
            local minor=${BASH_REMATCH[2]}
            if [[ $major -ge 3 && $minor -ge 8 ]]; then
                log "Found suitable Python: $python_version"
                return
            fi
        fi
    fi
    
    log "Installing Python via Homebrew..."
    install_homebrew
    brew install python@3.11
    
    # Create symlinks if needed
    if [[ ! -L "/usr/local/bin/python3" ]]; then
        if $SYSTEM_INSTALL; then
            ln -sf "$(brew --prefix)/bin/python3.11" /usr/local/bin/python3
            ln -sf "$(brew --prefix)/bin/pip3.11" /usr/local/bin/pip3
        fi
    fi
}

# Install Python requirements
install_requirements() {
    log "Installing Python requirements..."
    
    # Ensure we have the latest pip
    python3 -m pip install --upgrade pip
    
    # Install core requirements
    if [[ -f "requirements.txt" ]]; then
        python3 -m pip install -r requirements.txt
    else
        warning "requirements.txt not found, installing basic dependencies"
        python3 -m pip install omegaconf
    fi
    
    # Install psutil for system monitoring
    log "Installing psutil..."
    python3 -m pip install psutil
    
    # Install additional dependencies
    python3 -m pip install pyyaml
    
    log "Python requirements installed successfully"
}

# Create directories
create_directories() {
    log "Creating directories..."
    
    mkdir -p "$INSTALL_DIR" "$CONFIG_DIR" "$DATA_DIR" "$LOG_DIR"
    
    if $SYSTEM_INSTALL; then
        chmod 755 "$CONFIG_DIR" "$DATA_DIR" "$LOG_DIR"
    fi
    
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
    
    if $SYSTEM_INSTALL; then
        chown root:wheel "$INSTALL_DIR/kode-kronical-daemon"
    fi
    
    log "Installed daemon to: $INSTALL_DIR/kode-kronical-daemon"
}

# Install launchd service
install_service() {
    log "Installing launchd service..."
    
    # Create plist content
    local plist_dir=$(dirname "$PLIST_FILE")
    mkdir -p "$plist_dir"
    
    cat > "$PLIST_FILE" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>$SERVICE_NAME</string>
    
    <key>ProgramArguments</key>
    <array>
        <string>$(which python3)</string>
        <string>$INSTALL_DIR/kode-kronical-daemon</string>
        <string>-c</string>
        <string>$CONFIG_DIR/daemon.yaml</string>
        <string>start</string>
    </array>
    
    <key>RunAtLoad</key>
    <true/>
    
    <key>KeepAlive</key>
    <dict>
        <key>SuccessfulExit</key>
        <false/>
        <key>Crashed</key>
        <true/>
    </dict>
    
    <key>ThrottleInterval</key>
    <integer>10</integer>
    
    <key>StandardOutPath</key>
    <string>$LOG_DIR/daemon.log</string>
    
    <key>StandardErrorPath</key>
    <string>$LOG_DIR/daemon-error.log</string>
    
    <key>WorkingDirectory</key>
    <string>$DATA_DIR</string>
    
    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key>
        <string>/usr/local/bin:/opt/homebrew/bin:/usr/bin:/bin</string>
        <key>PYTHONPATH</key>
        <string>/usr/local/lib/python3.11/site-packages:/opt/homebrew/lib/python3.11/site-packages</string>
    </dict>
    
    <key>ProcessType</key>
    <string>Background</string>
    
    <key>Nice</key>
    <integer>10</integer>
    
    <key>LowPriorityIO</key>
    <true/>
    
    <key>SoftResourceLimits</key>
    <dict>
        <key>NumberOfFiles</key>
        <integer>4096</integer>
    </dict>
</dict>
</plist>
EOF
    
    if $SYSTEM_INSTALL; then
        chmod 644 "$PLIST_FILE"
        chown root:wheel "$PLIST_FILE"
    else
        chmod 644 "$PLIST_FILE"
    fi
    
    log "Installed launchd service: $PLIST_FILE"
}

# Install configuration
install_config() {
    log "Installing configuration..."
    
    local config_file="$CONFIG_DIR/daemon.yaml"
    
    # Get the directory where this script is located
    local script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    local project_root="$(dirname "$script_dir")"
    local example_config="$project_root/config/daemon.yaml.example"
    
    if [[ -f "$example_config" ]]; then
        cp "$example_config" "$config_file"
    else
        # Create basic config
        cat > "$config_file" << EOF
daemon:
  pid_file: $DATA_DIR/daemon.pid
  log_file: $LOG_DIR/daemon.log
  data_dir: $DATA_DIR/data
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
    
    if $SYSTEM_INSTALL; then
        chmod 644 "$config_file"
        chown root:wheel "$config_file"
    else
        chmod 644 "$config_file"
    fi
    
    log "Installed configuration to: $config_file"
}

# Start service
start_service() {
    log "Starting kode-kronical-daemon service..."
    
    if $SYSTEM_INSTALL; then
        launchctl load "$PLIST_FILE"
    else
        launchctl load "$PLIST_FILE"
    fi
    
    # Wait a moment and check status
    sleep 2
    verify_installation
}

# Stop service
stop_service() {
    log "Stopping kode-kronical-daemon service..."
    
    if $SYSTEM_INSTALL; then
        launchctl unload "$PLIST_FILE" 2>/dev/null || true
    else
        launchctl unload "$PLIST_FILE" 2>/dev/null || true
    fi
    
    log "Service stopped"
}

# Verify installation
verify_installation() {
    log "Verifying installation..."
    
    # Check if service is loaded
    if launchctl list | grep -q "$SERVICE_NAME"; then
        info "✓ Service is loaded"
    else
        warning "✗ Service is not loaded"
    fi
    
    # Check if data files are being created
    sleep 3
    local data_dir="$DATA_DIR/data"
    if ls "$data_dir"/metrics_*.json >/dev/null 2>&1; then
        info "✓ Data files are being created"
    else
        warning "✗ No data files found yet (this is normal for new installations)"
    fi
    
    # Test daemon status
    if "$INSTALL_DIR/kode-kronical-daemon" -c "$CONFIG_DIR/daemon.yaml" status >/dev/null 2>&1; then
        info "✓ Daemon status command works"
    else
        warning "✗ Daemon status command failed"
    fi
}

# Uninstall
uninstall() {
    log "Uninstalling kode-kronical-daemon..."
    
    # Stop and unload service
    stop_service
    
    # Remove files
    rm -f "$PLIST_FILE"
    rm -f "$INSTALL_DIR/kode-kronical-daemon"
    rm -rf "$CONFIG_DIR" "$DATA_DIR" "$LOG_DIR"
    
    if $SYSTEM_INSTALL; then
        info "System installation removed"
    else
        info "User installation removed"
    fi
    
    log "Uninstallation complete"
}

# Print usage information
print_usage() {
    echo
    log "Installation complete!"
    echo
    info "Service Management:"
    if $SYSTEM_INSTALL; then
        echo "  sudo launchctl load $PLIST_FILE      # Load service"
        echo "  sudo launchctl unload $PLIST_FILE    # Unload service"
        echo "  sudo launchctl list | grep kodekronical                # Check status"
    else
        echo "  launchctl load $PLIST_FILE           # Load service"
        echo "  launchctl unload $PLIST_FILE         # Unload service"
        echo "  launchctl list | grep kodekronical                     # Check status"
    fi
    echo
    info "Direct Control:"
    echo "  $INSTALL_DIR/kode-kronical-daemon status      # Check daemon status"
    echo "  tail -f $LOG_DIR/daemon.log             # View logs"
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
    if ! $SYSTEM_INSTALL; then
        warning "User installation: Make sure $USER_INSTALL_DIR is in your PATH"
        echo "  Add this to your ~/.zshrc or ~/.bash_profile:"
        echo "  export PATH=\"$USER_INSTALL_DIR:\$PATH\""
    fi
}

# Main installation function
main() {
    log "Starting kode-kronical-daemon installation for macOS..."
    
    check_privileges
    check_macos_version
    install_python
    install_requirements
    create_directories
    install_daemon
    install_service
    install_config
    start_service
    print_usage
    
    log "Installation completed successfully!"
}

# Handle command line arguments
case "${1:-install}" in
    install)
        main
        ;;
    uninstall)
        check_privileges
        uninstall
        ;;
    start)
        check_privileges
        start_service
        ;;
    stop)
        check_privileges
        stop_service
        ;;
    status)
        check_privileges
        verify_installation
        ;;
    *)
        echo "Usage: $0 [install|uninstall|start|stop|status]"
        exit 1
        ;;
esac