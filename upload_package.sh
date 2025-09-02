#!/bin/bash

# Upload script for kode-kronical package
# This script helps upload the package to PyPI safely

set -e  # Exit on any error

echo "🚀 kode-kronical Package Upload Script"
echo "================================"

# Activate virtual environment
source .venv/bin/activate
pip install -r requirements.txt
# Read current version (no incrementing)
echo "📋 Reading current version from pyproject.toml..."

# Check if .pypirc exists and set up configuration
if [ -f ".pypirc" ]; then
    echo "✅ Found .pypirc configuration file"
    
    # Verify .pypirc contains API tokens (not passwords)
    if grep -q "username = __token__" .pypirc; then
        echo "✅ Using secure API token authentication"
    else
        echo "⚠️  Warning: .pypirc appears to use username/password instead of API tokens"
        echo "   For security, consider using API tokens instead"
    fi
    
    export PYPIRC_PATH="$(pwd)/.pypirc"
    # Copy to home directory for twine to find it
    cp .pypirc ~/.pypirc
    echo "📋 Configured twine to use your credentials"
else
    echo "⚠️  No .pypirc file found. You'll need to enter credentials manually."
fi

# Check if package is built
if [ ! -d "dist" ] || [ -z "$(ls -A dist)" ]; then
    echo "❌ No package found in dist/. Building package first..."
    python -m build
fi

# Validate package
echo "🔍 Validating package..."
python -m twine check dist/*

if [ $? -ne 0 ]; then
    echo "❌ Package validation failed. Please fix errors and try again."
    exit 1
fi

echo "✅ Package validation passed!"

# Get current version from pyproject.toml
CURRENT_VERSION=$(python3 -c "
import tomllib
try:
    with open('pyproject.toml', 'rb') as f:
        data = tomllib.load(f)
        print(data['project']['version'])
except:
    # Fallback for older Python versions without tomllib
    import re
    with open('pyproject.toml', 'r') as f:
        content = f.read()
        match = re.search(r'version\s*=\s*[\"\'](.*?)[\"\']', content)
        if match:
            print(match.group(1))
        else:
            print('unknown')
" 2>/dev/null || echo "unknown")

# Show package information
echo ""
echo "📦 Package Information:"
echo "   Name: kode-kronical"
echo "   Version: $CURRENT_VERSION"
echo "   Built files:"
ls -la dist/

# Ask user which repository to upload to
echo ""
echo "Choose upload destination:"
echo "1) Test PyPI (recommended for first upload)"
echo "2) Production PyPI"
echo "3) Cancel"
read -p "Enter choice (1-3): " choice

case $choice in
    1)
        echo "📤 Uploading to Test PyPI..."
        if [ -f "~/.pypirc" ]; then
            python -m twine upload --repository testpypi --config-file ~/.pypirc dist/*
        else
            python -m twine upload --repository testpypi dist/*
        fi
        echo ""
        echo "✅ Uploaded to Test PyPI!"
        echo "🔗 View at: https://test.pypi.org/project/kode-kronical/"
        echo "📥 Test install with: pip install --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple/ kode-kronical"
        ;;
    2)
        echo "⚠️  This will upload to PRODUCTION PyPI!"
        read -p "Are you sure? (yes/no): " confirm
        if [ "$confirm" = "yes" ]; then
            echo "📤 Uploading to Production PyPI..."
            if [ -f "~/.pypirc" ]; then
                python -m twine upload --repository pypi --config-file ~/.pypirc dist/*
            else
                python -m twine upload --repository pypi dist/*
            fi
            echo ""
            echo "✅ Uploaded to PyPI!"
            echo "🔗 View at: https://pypi.org/project/kode-kronical/"
            echo "📥 Install with: pip install kode-kronical"
        else
            echo "❌ Upload cancelled."
        fi
        ;;
    3)
        echo "❌ Upload cancelled."
        exit 0
        ;;
    *)
        echo "❌ Invalid choice."
        exit 1
        ;;
esac

# Clean up - remove the copied .pypirc from home directory for security
if [ -f "~/.pypirc" ] && [ -f ".pypirc" ]; then
    rm ~/.pypirc
    echo "🧹 Cleaned up temporary configuration file"
fi
