# Setting Up PyPI Tokens for Automated Publishing

This guide explains how to set up PyPI API tokens for the GitHub Actions workflow to automatically publish your package.

## Step 1: Get PyPI API Tokens

### For Test PyPI (Optional but Recommended)
1. Go to [Test PyPI](https://test.pypi.org/account/login/)
2. Login or create an account
3. Go to [Account Settings > API tokens](https://test.pypi.org/manage/account/#api-tokens)
4. Click "Add API token"
5. Give it a name like "kode-kronical-github-actions"
6. Select "Entire account" scope (or specific project if it exists)
7. Copy the token (starts with `pypi-`)

### For Production PyPI
1. Go to [PyPI](https://pypi.org/account/login/)
2. Login or create an account
3. Go to [Account Settings > API tokens](https://pypi.org/manage/account/#api-tokens)
4. Click "Add API token"
5. Give it a name like "kode-kronical-github-actions"
6. Select "Entire account" scope (or specific project if it exists)
7. Copy the token (starts with `pypi-`)

## Step 2: Add Tokens to GitHub Secrets

1. Go to your GitHub repository
2. Click on "Settings" tab
3. Click on "Secrets and variables" > "Actions" in the left sidebar
4. Click "New repository secret"

### Add Test PyPI Token
- **Name**: `TEST_PYPI_API_TOKEN`
- **Value**: Your Test PyPI token (including the `pypi-` prefix)

### Add Production PyPI Token
- **Name**: `PYPI_API_TOKEN`
- **Value**: Your PyPI token (including the `pypi-` prefix)

## Step 3: Verify Setup

1. Make any small change to your code
2. Commit and push to the `main` branch
3. Check the "Actions" tab in your GitHub repository
4. The workflow should run automatically

## Security Notes

- ✅ **API tokens are secure** - they're scoped to your account/project
- ✅ **GitHub Secrets are encrypted** - only the workflow can access them
- ✅ **Tokens can be revoked** - you can disable them anytime in PyPI settings
- ⚠️ **Keep tokens private** - never commit them to code or share them

## Troubleshooting

### If the workflow fails:
1. Check the "Actions" tab for error details
2. Verify tokens are correctly set in GitHub Secrets
3. Make sure token names match exactly (`PYPI_API_TOKEN`, `TEST_PYPI_API_TOKEN`)

### If upload fails with "already exists":
- This is normal - PyPI doesn't allow re-uploading the same version
- The workflow uses `continue-on-error: true` to handle this gracefully
- The version manager should auto-increment to avoid conflicts

### Test the workflow:
1. Create a test branch
2. Make a small change
3. Create a pull request - this runs tests only
4. Merge to main - this runs tests + builds + publishes

## Manual Override

If you need to publish manually, you can still use:
```bash
python build_package.py
./upload_package.sh
```

The GitHub Actions workflow complements but doesn't replace your existing scripts.