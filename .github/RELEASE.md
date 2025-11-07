# Release Process

This document describes how to create a new release of YAFT.

## Automated Release Process

YAFT uses GitHub Actions to automatically build and release executables for Windows, macOS, and Linux.

### Creating a New Release

1. **Update Version Number**
   - Update the version in `pyproject.toml`:
     ```toml
     [project]
     version = "0.2.0"  # Update this
     ```
   - Update the version in `src/yaft/__init__.py`:
     ```python
     __version__ = "0.2.0"  # Update this
     ```

2. **Commit and Tag**
   ```bash
   git add pyproject.toml src/yaft/__init__.py
   git commit -m "chore: bump version to 0.2.0"
   git tag v0.2.0
   git push origin main
   git push origin v0.2.0
   ```

3. **Automatic Build and Release**
   - GitHub Actions will automatically:
     - Build executables for Windows, macOS, and Linux
     - Run all tests on all platforms
     - Create a GitHub Release with the executables attached
     - Publish the package to PyPI (if configured)

4. **Verify Release**
   - Go to: https://github.com/YOUR_USERNAME/yaft/releases
   - Download and test the executables

## Manual Release (if needed)

If you need to trigger a release manually:

1. Go to: https://github.com/YOUR_USERNAME/yaft/actions
2. Select "Build and Release" workflow
3. Click "Run workflow"
4. Select the branch/tag
5. Click "Run workflow"

## Release Artifacts

Each release includes:

- **yaft-windows-x64.exe** - Windows executable
- **yaft-linux-x64** - Linux executable
- **yaft-macos-x64** - macOS executable
- **Source code** - ZIP and tar.gz archives
- **Python package** - Published to PyPI (if configured)

## Version Numbering

YAFT uses [Semantic Versioning](https://semver.org/):

- **MAJOR.MINOR.PATCH** (e.g., 1.2.3)
  - **MAJOR**: Breaking changes
  - **MINOR**: New features (backward compatible)
  - **PATCH**: Bug fixes (backward compatible)

## PyPI Publishing

To enable automatic PyPI publishing:

1. Create an account on [PyPI](https://pypi.org/)
2. Configure trusted publishing:
   - Go to PyPI Account Settings → Publishing
   - Add GitHub as a trusted publisher
   - Repository: `YOUR_USERNAME/yaft`
   - Workflow: `release.yml`
   - Environment: leave blank
3. Push a new version tag - it will automatically publish to PyPI

## Troubleshooting

### Build Fails

- Check the GitHub Actions logs for errors
- Ensure all tests pass locally: `pytest`
- Verify PyInstaller can build locally: `pyinstaller src/yaft/cli.py`

### Release Not Created

- Ensure the tag follows the pattern `v*.*.*` (e.g., `v0.1.0`)
- Check that the workflow has permission to create releases
- Verify the `GITHUB_TOKEN` has write permissions

### PyPI Publishing Fails

- Ensure trusted publishing is configured on PyPI
- Check that the version number was updated
- Verify the package builds successfully: `python -m build`
