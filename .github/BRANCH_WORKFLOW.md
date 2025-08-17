# Branch-Based Deployment Workflow

This document explains how the GitHub Actions workflows behave differently based on which branch you push to.

## 🌿 **Branch Strategy**

### `main` Branch → Production PyPI
- **Trigger**: `git push origin main`
- **Destination**: [PyPI](https://pypi.org/project/kode-kronical/) (production)
- **Version**: Auto-incremented and committed back
- **Release**: Creates GitHub release with changelog
- **Install**: `pip install kode-kronical`

### `test` Branch → Test PyPI  
- **Trigger**: `git push origin test`
- **Destination**: [Test PyPI](https://test.pypi.org/project/kode-kronical/) (testing)
- **Version**: Auto-incremented but NOT committed back
- **Release**: No GitHub release created
- **Install**: `pip install --index-url https://test.pypi.org/simple/ kode-kronical`

### Pull Requests → Tests Only
- **Trigger**: PR to `main` or `test` branch
- **Action**: Runs tests across Python 3.8-3.12
- **No Publishing**: Just validates the code

## 🔄 **Workflow Examples**

### Testing a New Feature:
```bash
# 1. Create feature branch
git checkout -b feature/my-new-feature

# 2. Make changes
# ... code changes ...

# 3. Test on Test PyPI
git checkout test
git merge feature/my-new-feature
git push origin test  # → Publishes to Test PyPI

# 4. Test the package
pip install --index-url https://test.pypi.org/simple/ kode-kronical

# 5. Deploy to production
git checkout main
git merge feature/my-new-feature  
git push origin main  # → Publishes to PyPI + creates release
```

### Quick Hotfix:
```bash
# 1. Make fix directly on main
git checkout main
# ... fix code ...
git commit -m "Fix critical bug"

# 2. Deploy immediately 
git push origin main  # → Auto-publishes to PyPI
```

## 📋 **What Happens When**

| Action | Tests | Build | Test PyPI | PyPI | Version Commit | GitHub Release |
|--------|-------|-------|-----------|------|----------------|----------------|
| Push to `main` | ✅ | ✅ | ❌ | ✅ | ✅ | ✅ |
| Push to `test` | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ |
| PR to `main`/`test` | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |

## 🔒 **Required Secrets**

Both workflows need these GitHub Secrets:
- `PYPI_API_TOKEN` - For publishing to production PyPI
- `TEST_PYPI_API_TOKEN` - For publishing to Test PyPI

## ⚡ **Quick Commands**

```bash
# Test a change
git push origin test

# Deploy to production  
git push origin main

# Just run tests (via PR)
# Create PR from feature branch → main/test
```

This setup gives you:
- 🧪 **Safe testing** via Test PyPI
- 🚀 **Simple production** deployment  
- 🔄 **Automatic versioning**
- 🛡️ **No accidental** production deployments