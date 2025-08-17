"""
Hostname utilities for consistent hostname collection and normalization across kode-kronical components.

IMPORTANT: Always use get_normalized_hostname() instead of raw socket.gethostname() or os.uname().nodename
to prevent duplicate hostnames in the systems registry and dashboard.

Common duplicate hostname scenarios:
- Network config changes: "Mac.local" vs "Mac.home.local" 
- Domain changes: "hostname" vs "hostname.company.com"
- OS reconfigurations: "gmans-MacBook-Pro-14.local" vs "Mac.home.local"

This module provides consistent hostname detection and normalization to prevent these issues.
"""

import socket
import os
import logging

logger = logging.getLogger(__name__)


def get_normalized_hostname() -> str:
    """
    Get the normalized hostname for this system.
    
    Uses a consistent method and applies normalization to prevent duplicate entries.
    Priority: socket.gethostname() -> os.uname().nodename -> 'unknown'
    
    Returns:
        str: Normalized hostname
    """
    hostname = None
    
    # Try socket.gethostname() first (preferred method)
    try:
        hostname = socket.gethostname()
        logger.debug(f"Using socket.gethostname(): {hostname}")
    except Exception as e:
        logger.warning(f"socket.gethostname() failed: {e}")
    
    # Fallback to os.uname().nodename
    if not hostname:
        try:
            if hasattr(os, 'uname'):
                hostname = os.uname().nodename
                logger.debug(f"Using os.uname().nodename: {hostname}")
            else:
                logger.warning("os.uname() not available on this platform")
        except Exception as e:
            logger.warning(f"os.uname().nodename failed: {e}")
    
    # Final fallback
    if not hostname:
        hostname = 'unknown'
        logger.warning("All hostname detection methods failed, using 'unknown'")
    
    # Normalize the hostname
    normalized = normalize_hostname(hostname)
    
    if normalized != hostname:
        logger.info(f"Hostname normalized: '{hostname}' -> '{normalized}'")
    
    return normalized


def normalize_hostname(hostname: str) -> str:
    """
    Normalize a hostname to ensure consistency.
    
    Args:
        hostname: Raw hostname string
        
    Returns:
        str: Normalized hostname
    """
    if not hostname:
        return 'unknown'
    
    # Convert to string and strip whitespace
    normalized = str(hostname).strip()
    
    # Remove any null bytes or control characters
    normalized = ''.join(char for char in normalized if ord(char) >= 32 and ord(char) != 127)
    
    # Limit length to reasonable size
    if len(normalized) > 253:  # DNS hostname limit
        normalized = normalized[:253]
        logger.warning(f"Hostname truncated to 253 characters: {normalized}")
    
    # If empty after normalization, use unknown
    if not normalized:
        normalized = 'unknown'
    
    return normalized


def are_hostnames_equivalent(hostname1: str, hostname2: str) -> bool:
    """
    Check if two hostnames should be considered equivalent (same system).
    
    This can be used to detect potential duplicates before they're stored.
    
    Args:
        hostname1: First hostname
        hostname2: Second hostname
        
    Returns:
        bool: True if hostnames are equivalent
    """
    if not hostname1 or not hostname2:
        return False
    
    norm1 = normalize_hostname(hostname1)
    norm2 = normalize_hostname(hostname2)
    
    # Exact match after normalization
    if norm1 == norm2:
        return True
    
    # Check for common variations
    # Example: "Mac.home.local" vs "Mac.local" 
    # or "hostname.domain.com" vs "hostname"
    base1 = norm1.split('.')[0].lower()
    base2 = norm2.split('.')[0].lower()
    
    # If base names are the same but one has domain suffix, consider equivalent
    if base1 == base2 and len(base1) > 3:  # Avoid matching very short names
        logger.info(f"Hostnames considered equivalent: '{norm1}' <-> '{norm2}' (same base: '{base1}')")
        return True
    
    return False


def log_hostname_info():
    """Log detailed hostname information for debugging."""
    print("Hostname Collection Debug Info:")
    print("=" * 50)
    
    try:
        socket_name = socket.gethostname()
        print(f"socket.gethostname(): '{socket_name}' (len={len(socket_name)})")
    except Exception as e:
        print(f"socket.gethostname(): FAILED - {e}")
    
    try:
        if hasattr(os, 'uname'):
            uname_name = os.uname().nodename
            print(f"os.uname().nodename: '{uname_name}' (len={len(uname_name)})")
        else:
            print("os.uname().nodename: NOT AVAILABLE")
    except Exception as e:
        print(f"os.uname().nodename: FAILED - {e}")
    
    normalized = get_normalized_hostname()
    print(f"get_normalized_hostname(): '{normalized}' (len={len(normalized)})")
    
    print("=" * 50)


if __name__ == "__main__":
    log_hostname_info()