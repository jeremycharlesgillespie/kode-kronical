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


def increment_version(version_str, bump_type='patch'):
    """Increment version based on bump type: major, minor, or patch"""
    # Parse version (assume X.Y.Z format)
    parts = version_str.split('.')
    
    if len(parts) != 3:
        raise ValueError(f"Invalid version format: {version_str}")
    
    major, minor, patch = map(int, parts)
    
    if bump_type == 'major':
        # X.0.0 - increment major, reset minor and patch
        major += 1
        minor = 0
        patch = 0
    elif bump_type == 'minor':
        # 0.X.0 - increment minor, reset patch
        minor += 1
        patch = 0
    elif bump_type == 'patch':
        # 0.0.X - increment patch only
        patch += 1
    else:
        raise ValueError(f"Invalid bump type: {bump_type}. Use 'major', 'minor', or 'patch'")
    
    return f"{major}.{minor}.{patch}"


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


def get_version_bump_type(current_version):
    """Interactively ask user for version bump type"""
    # Parse current version
    parts = current_version.split('.')
    if len(parts) != 3:
        raise ValueError(f"Invalid version format: {current_version}")
    
    major, minor, patch = map(int, parts)
    
    print(f"\n📊 Current version: {current_version}")
    print("\nSelect version bump type:")
    print(f"  1. Major ({major}.{minor}.{patch} → {major + 1}.0.0)")
    print(f"  2. Minor ({major}.{minor}.{patch} → {major}.{minor + 1}.0)")
    print(f"  3. Patch ({major}.{minor}.{patch} → {major}.{minor}.{patch + 1}) [default]")
    
    choice = input("\nEnter choice (1-3, or press Enter for patch): ").strip()
    
    if choice == '1':
        return 'major'
    elif choice == '2':
        return 'minor'
    elif choice in ['3', '']:
        return 'patch'
    else:
        print("Invalid choice, defaulting to patch")
        return 'patch'


def main(bump_type=None, interactive=True):
    """Main function for standalone usage"""
    try:
        current_version = get_current_version()
        
        # Get bump type interactively if not provided
        if bump_type is None and interactive:
            bump_type = get_version_bump_type(current_version)
        elif bump_type is None:
            bump_type = 'patch'  # default
        
        new_version = increment_version(current_version, bump_type)
        files_updated = update_version_in_files(new_version)
        
        print(f"✅ Version updated: {current_version} → {new_version}")
        print(f"📝 Files updated: {', '.join(files_updated)}")
        
        return new_version
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return None


if __name__ == "__main__":
    main()