__version__ = "0.3.2"
__author__ = "Jeremy Gillespie"
__email__ = "metalgear386@googlemail.com"

from .core import KodeKronical
from .system_monitor import SystemMonitor, ProcessTracker, KodeKronicalSystemMonitor
from .exception_handler import enable_enhanced_exceptions, disable_enhanced_exceptions
from .failure_capture import capture_failure, log_failure, get_failure_stats

__all__ = ["KodeKronical", "SystemMonitor", "ProcessTracker", "KodeKronicalSystemMonitor", 
           "enable_enhanced_exceptions", "disable_enhanced_exceptions",
           "capture_failure", "log_failure", "get_failure_stats"]

# Automatically enable enhanced exceptions when the module is imported
enable_enhanced_exceptions()