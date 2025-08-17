#!/usr/bin/env python3
"""
Version manager for kode-kronical package.
Handles automatic version incrementing.
"""

import re
from pathlib import Path


def get_current_version():
    """Get current version from pyproject.toml"""
    pyproject_file = Path("pyproject.toml")
    if not pyproject_file.exists():
        raise FileNotFoundError("pyproject.toml not found")
    
    content = pyproject_file.read_text()
    version_match = re.search(r'version = "([^"]+)"', content)
    
    if not version_match:
        raise ValueError("Version not found in pyproject.toml")
    
    return version_match.group(1)


def increment_version(version_str, increment=0.01):
    """Increment version by specified amount"""
    # Parse version (assume X.Y.Z format)
    parts = version_str.split('.')
    
    if len(parts) != 3:
        raise ValueError(f"Invalid version format: {version_str}")
    
    major, minor, patch = map(int, parts)
    
    # Convert to float for increment calculation
    current_version_float = major + minor * 0.1 + patch * 0.01
    new_version_float = current_version_float + increment
    
    # Extract new major, minor, patch
    new_major = int(new_version_float)
    remaining = new_version_float - new_major
    new_minor = int(remaining * 10)
    new_patch = int(round((remaining * 10 - new_minor) * 10))
    
    return f"{new_major}.{new_minor}.{new_patch}"


def update_version_in_files(new_version):
    """Update version in pyproject.toml and __init__.py"""
    files_updated = []
    
    # Update pyproject.toml
    pyproject_file = Path("pyproject.toml")
    content = pyproject_file.read_text()
    updated_content = re.sub(
        r'version = "[^"]+"',
        f'version = "{new_version}"',
        content
    )
    pyproject_file.write_text(updated_content)
    files_updated.append("pyproject.toml")
    
    # Update src/kode_kronical/__init__.py
    init_file = Path("src/kode_kronical/__init__.py")
    if init_file.exists():
        content = init_file.read_text()
        updated_content = re.sub(
            r'__version__ = "[^"]+"',
            f'__version__ = "{new_version}"',
            content
        )
        init_file.write_text(updated_content)
        files_updated.append("src/kode_kronical/__init__.py")
    
    return files_updated


def main():
    """Main function for standalone usage"""
    try:
        current_version = get_current_version()
        new_version = increment_version(current_version)
        files_updated = update_version_in_files(new_version)
        
        print(f"✅ Version updated: {current_version} → {new_version}")
        print(f"📝 Files updated: {', '.join(files_updated)}")
        
        return new_version
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return None


if __name__ == "__main__":
    main()