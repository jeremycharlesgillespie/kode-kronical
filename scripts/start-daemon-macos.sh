#!/bin/bash
# Start kode-kronical-daemon on macOS
# Handles both system and user installations

set -e

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Service configuration
SYSTEM_PLIST="/Library/LaunchDaemons/com.pyperf.daemon.plist"
USER_PLIST="$HOME/Library/LaunchAgents/com.pyperf.daemon.plist"
SERVICE_NAME="com.pyperf.daemon"

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
        PLIST_FILE="$SYSTEM_PLIST"
        log "Managing system service (root privileges detected)"
    else
        SYSTEM_INSTALL=false
        PLIST_FILE="$USER_PLIST"
        log "Managing user service (no root privileges)"
    fi
}

# Check if service is installed
check_service_exists() {
    if [[ ! -f "$PLIST_FILE" ]]; then
        error "Service not found at: $PLIST_FILE"
        error "Please install kode-kronical-daemon first using install-daemon-macos.sh"
        exit 1
    fi
}

# Check if service is already running
is_service_running() {
    if launchctl list | grep -q "$SERVICE_NAME"; then
        return 0  # Running
    else
        return 1  # Not running
    fi
}

# Start the service
start_service() {
    log "Starting kode-kronical-daemon service..."
    
    if is_service_running; then
        warning "Service is already running"
        info "Use 'launchctl list | grep pyperf' to check status"
        return 0
    fi
    
    # Load the service
    if $SYSTEM_INSTALL; then
        launchctl load "$PLIST_FILE"
    else
        launchctl load "$PLIST_FILE"
    fi
    
    # Wait a moment for startup
    sleep 2
    
    # Verify it started
    if is_service_running; then
        log "✓ Service started successfully"
        
        # Show some status info
        show_service_status
    else
        error "✗ Service failed to start"
        error "Check logs for details:"
        if $SYSTEM_INSTALL; then
            error "  tail -f /usr/local/var/log/kode-kronical/daemon.log"
        else
            error "  tail -f ~/.local/share/kode-kronical/logs/daemon.log"
        fi
        exit 1
    fi
}

# Show service status
show_service_status() {
    info "Service Status:"
    
    # Check if service is in launchctl list
    if launchctl list | grep -q "$SERVICE_NAME"; then
        local status_line=$(launchctl list | grep "$SERVICE_NAME")
        info "  $status_line"
    else
        warning "  Service not found in launchctl list"
    fi
    
    # Check for recent data files
    if $SYSTEM_INSTALL; then
        local data_dir="/usr/local/var/kode-kronical/data"
    else
        local data_dir="$HOME/.local/share/kode-kronical/data"
    fi
    
    if [[ -d "$data_dir" ]]; then
        local recent_files=$(find "$data_dir" -name "metrics_*.json" -mtime -5m 2>/dev/null | wc -l)
        if [[ $recent_files -gt 0 ]]; then
            info "  ✓ Found $recent_files recent data files"
        else
            warning "  ✗ No recent data files found"
        fi
    else
        warning "  ✗ Data directory not found: $data_dir"
    fi
}

# Show usage information
show_usage() {
    echo
    log "kode-kronical-daemon started successfully!"
    echo
    info "Service Management:"
    if $SYSTEM_INSTALL; then
        echo "  sudo launchctl unload $PLIST_FILE  # Stop service"
        echo "  sudo launchctl load $PLIST_FILE    # Start service"
        echo "  launchctl list | grep pyperf                # Check status"
        echo "  tail -f /usr/local/var/log/kode-kronical/daemon.log  # View logs"
    else
        echo "  launchctl unload $PLIST_FILE       # Stop service"
        echo "  launchctl load $PLIST_FILE         # Start service"
        echo "  launchctl list | grep pyperf                # Check status"
        echo "  tail -f ~/.local/share/kode-kronical/logs/daemon.log  # View logs"
    fi
    echo
    info "Quick Commands:"
    echo "  ./scripts/start-daemon-macos.sh     # Start service"
    echo "  ./scripts/stop-daemon-macos.sh      # Stop service"
    echo "  ./scripts/status-daemon-macos.sh    # Check status"
    echo
}

# Main function
main() {
    check_privileges
    check_service_exists
    start_service
    show_usage
}

# Handle command line arguments
case "${1:-start}" in
    start)
        main
        ;;
    --help|-h|help)
        echo "Usage: $0 [start]"
        echo
        echo "Start the kode-kronical-daemon service on macOS"
        echo
        echo "This script automatically detects system vs user installation"
        echo "based on whether you run it with sudo or not."
        echo
        echo "Examples:"
        echo "  sudo $0        # Start system service"
        echo "  $0             # Start user service"
        ;;
    *)
        error "Invalid argument: $1"
        echo "Use '$0 --help' for usage information"
        exit 1
        ;;
esac