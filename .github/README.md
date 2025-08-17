# GitHub Actions for kode-kronical

This directory contains GitHub Actions workflows for automated testing and publishing.

## Workflows

### 🚀 `publish.yml` - Build and Publish
**Triggers**: Push to `main` or `test` branch
**What it does**:
1. **Tests** - Runs tests across Python 3.8-3.12
2. **Version bump** - Auto-increments version using your `build_package.py`
3. **Build** - Creates wheel and source distribution
4. **Publish** - 
   - `main` branch → **PyPI** (production)
   - `test` branch → **Test PyPI** (testing)
5. **Release** - Creates GitHub release (main branch only)
6. **Commit** - Pushes version bump back to repo (main branch only)

### 🧪 `test.yml` - Run Tests Only
**Triggers**: Pull requests to `main` or `test`
**What it does**:
1. **Code quality** - Runs black, isort, flake8
2. **Import tests** - Verifies package imports correctly
3. **Functionality tests** - Tests core features and enhanced exceptions
4. **Build test** - Ensures package builds correctly

## Setup Required

1. **PyPI API Tokens** - Follow instructions in `SETUP_PYPI_TOKENS.md`
2. **GitHub Secrets** - Add `PYPI_API_TOKEN` and `TEST_PYPI_API_TOKEN`

## Usage

### For Development
1. Create feature branch
2. Make changes
3. Open pull request → triggers `test.yml`
4. Review and merge → triggers `publish.yml`

### For Testing
Push to `test` branch:
- ✅ Run all tests
- ✅ Auto-increment version
- ✅ Build package  
- ✅ Publish to **Test PyPI**

### For Production Releases
Push to `main` branch:
- ✅ Run all tests
- ✅ Auto-increment version
- ✅ Build package  
- ✅ Publish to **PyPI**
- ✅ Create GitHub release
- ✅ Update version in repo

## Features

- 🔄 **Auto-versioning** - Uses your existing `version_manager.py`
- 🛡️ **Multi-Python testing** - Tests Python 3.8 through 3.12
- 📦 **Dual publishing** - Test PyPI and production PyPI
- 🏷️ **GitHub releases** - Auto-created with changelog
- 🧹 **Clean workflow** - Handles version conflicts gracefully
- 🔒 **Secure** - Uses API tokens, not passwords

## Manual Override

Your existing scripts still work:
```bash
python build_package.py  # Still works
./upload_package.sh      # Still works
```

The GitHub Actions complement but don't replace your local workflow.