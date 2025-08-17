#!/bin/bash
# Stop kode-kronical-daemon on macOS
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

# Check if service is running
is_service_running() {
    if launchctl list | grep -q "$SERVICE_NAME"; then
        return 0  # Running
    else
        return 1  # Not running
    fi
}

# Stop the service
stop_service() {
    log "Stopping kode-kronical-daemon service..."
    
    if ! is_service_running; then
        warning "Service is not currently running"
        info "Use 'launchctl list | grep pyperf' to check status"
        return 0
    fi
    
    # Unload the service
    if $SYSTEM_INSTALL; then
        launchctl unload "$PLIST_FILE" 2>/dev/null || true
    else
        launchctl unload "$PLIST_FILE" 2>/dev/null || true
    fi
    
    # Wait a moment for shutdown
    sleep 2
    
    # Verify it stopped
    if ! is_service_running; then
        log "✓ Service stopped successfully"
        
        # Show final status
        show_final_status
    else
        warning "Service may still be running"
        warning "Try checking with: launchctl list | grep pyperf"
        
        # Sometimes launchctl takes a moment
        sleep 3
        if ! is_service_running; then
            log "✓ Service stopped successfully (delayed)"
        else
            error "✗ Service failed to stop cleanly"
            error "You may need to manually kill the process"
        fi
    fi
}

# Show final status after stopping
show_final_status() {
    info "Final Status:"
    
    # Check if any kode-kronical processes are still running
    local pyperf_processes=$(ps aux | grep -E "(kode-kronical|pyperf)" | grep -v grep | wc -l)
    if [[ $pyperf_processes -eq 0 ]]; then
        info "  ✓ No kode-kronical processes running"
    else
        warning "  ⚠ Found $pyperf_processes kode-kronical related processes still running"
        info "  Run 'ps aux | grep kode-kronical' to see details"
    fi
    
    # Check data directory
    if $SYSTEM_INSTALL; then
        local data_dir="/usr/local/var/kode-kronical/data"
    else
        local data_dir="$HOME/.local/share/kode-kronical/data"
    fi
    
    if [[ -d "$data_dir" ]]; then
        local total_files=$(find "$data_dir" -name "metrics_*.json" 2>/dev/null | wc -l)
        info "  Data files preserved: $total_files files in $data_dir"
    fi
}

# Show usage information
show_usage() {
    echo
    log "kode-kronical-daemon stopped successfully!"
    echo
    info "Service Management:"
    if $SYSTEM_INSTALL; then
        echo "  sudo launchctl load $PLIST_FILE      # Start service"
        echo "  sudo launchctl unload $PLIST_FILE    # Stop service"
        echo "  launchctl list | grep pyperf                  # Check status"
    else
        echo "  launchctl load $PLIST_FILE           # Start service"
        echo "  launchctl unload $PLIST_FILE         # Stop service"
        echo "  launchctl list | grep pyperf                  # Check status"
    fi
    echo
    info "Quick Commands:"
    echo "  ./scripts/start-daemon-macos.sh      # Start service"
    echo "  ./scripts/stop-daemon-macos.sh       # Stop service"
    echo "  ./scripts/status-daemon-macos.sh     # Check status"
    echo
    info "Data Preservation:"
    echo "  Your performance data has been preserved and will be"
    echo "  available when you restart the service."
}

# Force stop option
force_stop() {
    log "Force stopping kode-kronical-daemon..."
    
    # Kill any kode-kronical processes
    local killed_processes=0
    for pid in $(ps aux | grep -E "(kode-kronical|pyperf)" | grep -v grep | awk '{print $2}'); do
        if kill -TERM "$pid" 2>/dev/null; then
            info "Terminated process: $pid"
            killed_processes=$((killed_processes + 1))
        fi
    done
    
    # Wait for graceful shutdown
    sleep 2
    
    # Force kill if needed
    for pid in $(ps aux | grep -E "(kode-kronical|pyperf)" | grep -v grep | awk '{print $2}'); do
        if kill -KILL "$pid" 2>/dev/null; then
            warning "Force killed process: $pid"
            killed_processes=$((killed_processes + 1))
        fi
    done
    
    if [[ $killed_processes -gt 0 ]]; then
        log "Stopped $killed_processes kode-kronical processes"
    else
        info "No kode-kronical processes were running"
    fi
    
    # Also unload the service
    if [[ -f "$PLIST_FILE" ]]; then
        launchctl unload "$PLIST_FILE" 2>/dev/null || true
    fi
}

# Main function
main() {
    check_privileges
    check_service_exists
    stop_service
    show_usage
}

# Handle command line arguments
case "${1:-stop}" in
    stop)
        main
        ;;
    force|--force|-f)
        check_privileges
        force_stop
        show_usage
        ;;
    --help|-h|help)
        echo "Usage: $0 [stop|force]"
        echo
        echo "Stop the kode-kronical-daemon service on macOS"
        echo
        echo "Options:"
        echo "  stop    Normal service stop (default)"
        echo "  force   Force kill all kode-kronical processes"
        echo
        echo "This script automatically detects system vs user installation"
        echo "based on whether you run it with sudo or not."
        echo
        echo "Examples:"
        echo "  sudo $0           # Stop system service"
        echo "  $0                # Stop user service"
        echo "  $0 force          # Force stop all processes"
        ;;
    *)
        error "Invalid argument: $1"
        echo "Use '$0 --help' for usage information"
        exit 1
        ;;
esac