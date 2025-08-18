#!/bin/bash
# Check status of kode-kronical-daemon on macOS
# Handles both system and user installations

set -e

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

# Service configuration
SYSTEM_PLIST="/Library/LaunchDaemons/com.kodekronical.daemon.plist"
USER_PLIST="$HOME/Library/LaunchAgents/com.kodekronical.daemon.plist"
SERVICE_NAME="com.kodekronical.daemon"

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

status_info() {
    echo -e "${CYAN}$1${NC}"
}

# Check installation type
check_installation() {
    local system_installed=false
    local user_installed=false
    
    if [[ -f "$SYSTEM_PLIST" ]]; then
        system_installed=true
    fi
    
    if [[ -f "$USER_PLIST" ]]; then
        user_installed=true
    fi
    
    if $system_installed && $user_installed; then
        warning "Both system and user installations found!"
        info "System plist: $SYSTEM_PLIST"
        info "User plist: $USER_PLIST"
        echo
        status_info "Checking both installations..."
        return 2  # Both installed
    elif $system_installed; then
        info "System installation detected"
        PLIST_FILE="$SYSTEM_PLIST"
        SYSTEM_INSTALL=true
        return 0  # System only
    elif $user_installed; then
        info "User installation detected"
        PLIST_FILE="$USER_PLIST"
        SYSTEM_INSTALL=false
        return 1  # User only
    else
        error "No kode-kronical-daemon installation found"
        error "Please install using install-daemon-macos.sh first"
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

# Get service PID if running
get_service_pid() {
    local pid_line=$(launchctl list | grep "$SERVICE_NAME" || echo "")
    if [[ -n "$pid_line" ]]; then
        echo "$pid_line" | awk '{print $1}'
    else
        echo ""
    fi
}

# Show service status
show_service_status() {
    local installation_type="$1"
    
    echo
    status_info "=== $installation_type Installation Status ==="
    
    # Check launchctl status
    if is_service_running; then
        local pid=$(get_service_pid)
        if [[ "$pid" != "-" && -n "$pid" ]]; then
            status_info "✓ Service: RUNNING (PID: $pid)"
            
            # Get process details if available
            if ps -p "$pid" >/dev/null 2>&1; then
                local process_info=$(ps -p "$pid" -o pid,ppid,cpu,rss,start,command | tail -n 1)
                info "  Process: $process_info"
            fi
        else
            warning "⚠ Service: LOADED but not running"
        fi
    else
        error "✗ Service: NOT RUNNING"
    fi
    
    # Check configuration file
    if [[ "$installation_type" == "System" ]]; then
        local config_file="/usr/local/etc/kode-kronical/daemon.yaml"
        local data_dir="/usr/local/var/kode-kronical/data"
        local log_file="/usr/local/var/log/kode-kronical/daemon.log"
    else
        local config_file="$HOME/.config/kode-kronical/daemon.yaml"
        local data_dir="$HOME/.local/share/kode-kronical/data"
        local log_file="$HOME/.local/share/kode-kronical/logs/daemon.log"
    fi
    
    # Check configuration
    if [[ -f "$config_file" ]]; then
        status_info "✓ Configuration: $config_file"
    else
        warning "✗ Configuration missing: $config_file"
    fi
    
    # Check data directory and files
    if [[ -d "$data_dir" ]]; then
        local total_files=$(find "$data_dir" -name "metrics_*.json" 2>/dev/null | wc -l)
        local recent_files=$(find "$data_dir" -name "metrics_*.json" -mtime -5m 2>/dev/null | wc -l)
        
        if [[ $recent_files -gt 0 ]]; then
            status_info "✓ Data Collection: Active ($recent_files recent files, $total_files total)"
        elif [[ $total_files -gt 0 ]]; then
            warning "⚠ Data Collection: Inactive ($total_files total files, none recent)"
        else
            warning "✗ Data Collection: No data files found"
        fi
        
        # Show disk usage
        local disk_usage=$(du -sh "$data_dir" 2>/dev/null | cut -f1)
        info "  Data usage: $disk_usage in $data_dir"
    else
        error "✗ Data directory missing: $data_dir"
    fi
    
    # Check log file
    if [[ -f "$log_file" ]]; then
        local log_size=$(ls -lh "$log_file" | awk '{print $5}')
        local log_modified=$(stat -f "%Sm" -t "%Y-%m-%d %H:%M:%S" "$log_file" 2>/dev/null || echo "unknown")
        status_info "✓ Log file: $log_file ($log_size, modified: $log_modified)"
        
        # Show last few log entries
        info "  Recent log entries:"
        tail -n 3 "$log_file" 2>/dev/null | sed 's/^/    /' || info "    (no recent entries)"
    else
        warning "✗ Log file missing: $log_file"
    fi
}

# Show overall system status
show_system_status() {
    echo
    status_info "=== System Overview ==="
    
    # Check for any kode-kronical processes
    local pyperf_processes=$(ps aux | grep -E "(kode-kronical|pyperf)" | grep -v grep | wc -l)
    if [[ $pyperf_processes -gt 0 ]]; then
        status_info "✓ kode-kronical processes: $pyperf_processes running"
        ps aux | grep -E "(kode-kronical|pyperf)" | grep -v grep | while read line; do
            info "  $line"
        done
    else
        warning "✗ No kode-kronical processes found"
    fi
    
    # Show system resources
    local cpu_usage=$(top -l 1 -n 0 | grep "CPU usage" | awk '{print $3}')
    local memory_usage=$(top -l 1 -n 0 | grep "PhysMem" | awk '{print $2}')
    info "System CPU: $cpu_usage"
    info "System Memory: $memory_usage"
    
    # Check for KodeKronical integration
    echo
    status_info "=== KodeKronical Integration Test ==="
    local python_test=$(python3 -c "
try:
    import sys
    sys.path.insert(0, '$(pwd)/src')
    from kode_kronical import KodeKronical
    kode = KodeKronical()
    config_info = kode.get_config_info()
    daemon_status = config_info.get('daemon', {})
    if daemon_status.get('running', False):
        print('✓ KodeKronical can connect to daemon')
        print(f'  Data directory: {daemon_status.get(\"data_directory\", \"unknown\")}')
        print(f'  Last update: {daemon_status.get(\"last_update\", \"unknown\")}')
        print(f'  Metrics files: {daemon_status.get(\"metrics_files_count\", 0)}')
    else:
        print('✗ KodeKronical cannot connect to daemon')
        print('  Daemon may not be running or data directory not accessible')
except ImportError:
    print('⚠ KodeKronical library not found in current directory')
except Exception as e:
    print(f'⚠ KodeKronical integration test failed: {e}')
" 2>/dev/null || echo "⚠ Python test failed")
    
    echo "$python_test" | sed 's/^/  /'
}

# Show usage help
show_usage() {
    echo
    info "Service Management Commands:"
    echo "  ./scripts/start-daemon-macos.sh      # Start service"
    echo "  ./scripts/stop-daemon-macos.sh       # Stop service"
    echo "  ./scripts/status-daemon-macos.sh     # This status check"
    echo
    info "Manual launchctl Commands:"
    if [[ -f "$SYSTEM_PLIST" ]]; then
        echo "  sudo launchctl load $SYSTEM_PLIST    # Start system service"
        echo "  sudo launchctl unload $SYSTEM_PLIST  # Stop system service"
    fi
    if [[ -f "$USER_PLIST" ]]; then
        echo "  launchctl load $USER_PLIST           # Start user service"
        echo "  launchctl unload $USER_PLIST         # Stop user service"
    fi
    echo "  launchctl list | grep pyperf                   # Check launchctl status"
    echo
}

# Main function
main() {
    log "Checking kode-kronical-daemon status on macOS..."
    
    local install_status
    check_installation
    install_status=$?
    
    case $install_status in
        0)  # System only
            show_service_status "System"
            ;;
        1)  # User only
            show_service_status "User"
            ;;
        2)  # Both
            show_service_status "System"
            show_service_status "User"
            ;;
    esac
    
    show_system_status
    show_usage
}

# Handle command line arguments
case "${1:-status}" in
    status)
        main
        ;;
    --help|-h|help)
        echo "Usage: $0 [status]"
        echo
        echo "Check the status of kode-kronical-daemon service on macOS"
        echo
        echo "This script automatically detects both system and user"
        echo "installations and shows comprehensive status information."
        echo
        echo "Information shown:"
        echo "  - Service running status"
        echo "  - Configuration file status"
        echo "  - Data collection activity"
        echo "  - Log file information"
        echo "  - System resource usage"
        echo "  - KodeKronical integration test"
        ;;
    *)
        error "Invalid argument: $1"
        echo "Use '$0 --help' for usage information"
        exit 1
        ;;
esac