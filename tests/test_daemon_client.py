"""
Unit tests for daemon client functionality.
"""
import pytest
import sys
import os
from unittest.mock import patch, MagicMock
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from kode_kronical.daemon_client import DaemonClient, SystemMetrics


class TestDaemonClient:
    """Test DaemonClient functionality."""
    
    def test_initialization(self):
        """Test DaemonClient can be initialized."""
        client = DaemonClient()
        assert client is not None
    
    def test_initialization_with_data_dir(self):
        """Test DaemonClient with custom data directory."""
        client = DaemonClient(data_dir="/tmp/test")
        assert client is not None
        assert len(client.data_dirs) == 1
        assert client.data_dirs[0] == Path("/tmp/test")
    
    def test_find_active_data_dir_none(self):
        """Test finding active data directory when none exists."""
        client = DaemonClient(data_dir="/nonexistent/path")
        # Should return None when directory doesn't exist
        assert client.active_data_dir is None
    
    def test_get_latest_metrics_no_daemon(self):
        """Test get_latest_metrics when no daemon is running."""
        client = DaemonClient(data_dir="/nonexistent")
        metrics = client.get_latest_metrics()
        # Should return None when no daemon/data available
        assert metrics is None
    
    def test_system_metrics_dataclass(self):
        """Test SystemMetrics dataclass."""
        metrics = SystemMetrics(
            timestamp=1234567890.0,
            cpu_percent=25.5,
            memory_percent=60.2,
            memory_available_mb=8192.0,
            memory_used_mb=4096.0
        )
        assert metrics.timestamp == 1234567890.0
        assert metrics.cpu_percent == 25.5
        assert metrics.memory_percent == 60.2


if __name__ == '__main__':
    pytest.main([__file__])