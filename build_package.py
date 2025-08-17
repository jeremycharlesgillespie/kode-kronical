#!/usr/bin/env python3
"""
Build script for kode-kronical PyPI package.
This script helps build and test the package before publishing.
"""

import subprocess
import sys
import shutil
from pathlib import Path
from version_manager import get_current_version, increment_version, update_version_in_files

def run_command(cmd, description):
    """Run a command and print the result."""
    print(f"\n🔹 {description}")
    print(f"Running: {cmd}")
    try:
        result = subprocess.run(cmd, shell=True, check=True, capture_output=True, text=True)
        if result.stdout:
            print(result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Error: {e}")
        if e.stdout:
            print(f"STDOUT: {e.stdout}")
        if e.stderr:
            print(f"STDERR: {e.stderr}")
        return False

def clean_build_dirs():
    """Clean build directories."""
    print("\n🧹 Cleaning build directories...")
    dirs_to_clean = ["build", "dist", "src/kode_kronical.egg-info"]
    for dir_name in dirs_to_clean:
        dir_path = Path(dir_name)
        if dir_path.exists():
            shutil.rmtree(dir_path)
            print(f"Removed {dir_path}")

def main():
    """Main build process."""
    print("🚀 Building kode-kronical PyPI package")
    print("=" * 50)
    
    # Check if we're in the right directory
    if not Path("pyproject.toml").exists():
        print("❌ Error: pyproject.toml not found. Run this script from the project root.")
        sys.exit(1)
    
    # Increment version
    try:
        current_version = get_current_version()
        new_version = increment_version(current_version)
        files_updated = update_version_in_files(new_version)
        
        print(f"📈 Version updated: {current_version} → {new_version}")
        print(f"📝 Files updated: {', '.join(files_updated)}")
    except Exception as e:
        print(f"⚠️  Warning: Could not update version: {e}")
        new_version = get_current_version() if 'get_current_version' in globals() else "unknown"
    
    # Clean previous builds
    clean_build_dirs()
    
    # Install build dependencies
    if not run_command("pip install build twine", "Installing build dependencies"):
        sys.exit(1)
    
    # Build the package
    if not run_command("python -m build", "Building the package"):
        sys.exit(1)
    
    # Check the built package
    if not run_command("python -m twine check dist/*", "Checking package validity"):
        sys.exit(1)
    
    print("\n✅ Package built successfully!")
    print("\nNext steps:")
    print("1. Test the package locally:")
    print("   pip install dist/kode_kronical-0.1.0-py3-none-any.whl")
    print("\n2. Upload to Test PyPI:")
    print("   python -m twine upload --repository testpypi dist/*")
    print("\n3. Upload to PyPI:")
    print("   python -m twine upload dist/*")
    
    # Show package contents
    print("\n📦 Package contents:")
    dist_files = list(Path("dist").glob("*"))
    for file in dist_files:
        print(f"  - {file}")

if __name__ == "__main__":
    main()