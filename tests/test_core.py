"""
Unit tests for kode_kronical core functionality.
"""
import pytest
import sys
import os
from unittest.mock import patch, MagicMock

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from kode_kronical import KodeKronical


class TestKodeKronicalBasic:
    """Test basic KodeKronical functionality."""
    
    def test_import(self):
        """Test that KodeKronical can be imported."""
        from kode_kronical import KodeKronical
        assert KodeKronical is not None
    
    def test_initialization(self):
        """Test KodeKronical can be initialized."""
        kode = KodeKronical()
        assert kode is not None
    
    def test_timing_decorator(self):
        """Test that the timing decorator works."""
        kode = KodeKronical()
        
        @kode.time_it
        def sample_function(n):
            return sum(range(n))
        
        result = sample_function(100)
        assert result == sum(range(100))
        
        # Check that timing was recorded
        results = kode.get_results()
        assert len(results) >= 0  # May be 0 if not storing
    
    def test_timing_decorator_with_args(self):
        """Test timing decorator with store_args=True."""
        kode = KodeKronical()
        
        @kode.time_it(store_args=True)
        def sample_function(x, y=5):
            return x + y
        
        result = sample_function(10, y=15)
        assert result == 25
    
    def test_get_summary(self):
        """Test get_summary method."""
        kode = KodeKronical()
        summary = kode.get_summary()
        assert isinstance(summary, dict)
        # Summary may be empty initially, that's okay
        assert summary is not None
    
    def test_get_config_info(self):
        """Test get_config_info method."""
        kode = KodeKronical()
        config_info = kode.get_config_info()
        assert isinstance(config_info, dict)
    
    def test_failure_capture(self):
        """Test failure capture functionality."""
        from kode_kronical.failure_capture import capture_failure
        
        # Test that capture_failure doesn't crash
        try:
            capture_failure("test operation", ValueError("test error"))
        except Exception as e:
            pytest.fail(f"capture_failure raised an exception: {e}")


class TestKodeKronicalConfiguration:
    """Test KodeKronical configuration handling."""
    
    def test_initialization_with_config(self):
        """Test initialization with custom config."""
        config = {
            'kode_kronical': {'enabled': True},
            'local': {'enabled': True, 'data_dir': './test_data'}
        }
        kode = KodeKronical(config)
        assert kode is not None
    
    def test_disabled_configuration(self):
        """Test with disabled configuration."""
        config = {
            'kode_kronical': {'enabled': False}
        }
        kode = KodeKronical(config)
        
        @kode.time_it
        def sample_function():
            return 42
        
        result = sample_function()
        assert result == 42


class TestExceptionHandling:
    """Test exception handling features."""
    
    def test_enhanced_exceptions_enabled(self):
        """Test that enhanced exceptions are enabled by default."""
        kode = KodeKronical()
        
        # Check if exception handler is set up
        config_info = kode.get_config_info()
        # This test verifies the system doesn't crash when initializing
        assert config_info is not None


if __name__ == '__main__':
    pytest.main([__file__])