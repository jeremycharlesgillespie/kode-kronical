#!/bin/bash
# Script to start kode-kronical-daemon with proper error handling and restart capability

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG_FILE="/Users/gman/.config/kode-kronical/daemon.yaml"
DAEMON_CMD="$SCRIPT_DIR/kode-kronical-daemon"

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')] $1${NC}"
}

error() {
    echo -e "${RED}[ERROR] $1${NC}" >&2
}

warning() {
    echo -e "${YELLOW}[WARNING] $1${NC}"
}

# Function to check if daemon is running
is_daemon_running() {
    if "$DAEMON_CMD" -c "$CONFIG_FILE" status >/dev/null 2>&1; then
        return 0
    else
        return 1
    fi
}

# Function to start daemon
start_daemon() {
    log "Starting kode-kronical-daemon..."
    
    if is_daemon_running; then
        log "Daemon is already running"
        return 0
    fi
    
    # Clean up any stale PID files
    if [ -f "/Users/gman/.local/share/kode-kronical/daemon.pid" ]; then
        warning "Removing stale PID file"
        rm -f "/Users/gman/.local/share/kode-kronical/daemon.pid"
    fi
    
    # Start the daemon
    "$DAEMON_CMD" -c "$CONFIG_FILE" start
    
    # Wait a moment and verify it started
    sleep 3
    
    if is_daemon_running; then
        log "Daemon started successfully"
        "$DAEMON_CMD" -c "$CONFIG_FILE" status
        return 0
    else
        error "Failed to start daemon"
        return 1
    fi
}

# Function to stop daemon
stop_daemon() {
    log "Stopping kode-kronical-daemon..."
    
    if ! is_daemon_running; then
        log "Daemon is not running"
        return 0
    fi
    
    "$DAEMON_CMD" -c "$CONFIG_FILE" stop
    
    # Wait for shutdown
    sleep 2
    
    if ! is_daemon_running; then
        log "Daemon stopped successfully"
        return 0
    else
        error "Failed to stop daemon gracefully"
        return 1
    fi
}

# Function to restart daemon
restart_daemon() {
    log "Restarting kode-kronical-daemon..."
    stop_daemon
    sleep 2
    start_daemon
}

# Function to show status
show_status() {
    if is_daemon_running; then
        log "Daemon status:"
        "$DAEMON_CMD" -c "$CONFIG_FILE" status
        
        # Show recent activity
        echo ""
        log "Recent activity (last 5 lines):"
        tail -5 "/Users/gman/.local/share/kode-kronical/daemon.log" 2>/dev/null || echo "No log file found"
        
        # Show recent metrics files
        echo ""
        log "Recent metrics files:"
        ls -la "/Users/gman/.local/share/kode-kronical/metrics_"*.json 2>/dev/null | tail -3 || echo "No metrics files found"
        
    else
        warning "Daemon is not running"
        return 1
    fi
}

# Main script logic
case "${1:-status}" in
    start)
        start_daemon
        ;;
    stop)
        stop_daemon
        ;;
    restart)
        restart_daemon
        ;;
    status)
        show_status
        ;;
    *)
        echo "Usage: $0 {start|stop|restart|status}"
        echo ""
        echo "Commands:"
        echo "  start   - Start the daemon"
        echo "  stop    - Stop the daemon"
        echo "  restart - Restart the daemon"
        echo "  status  - Show daemon status and recent activity"
        exit 1
        ;;
esac