# Quick Start: Setting up GitHub

This guide will help you get YAFT set up on GitHub with automated CI/CD.

## Step 1: Create GitHub Repository

1. Go to [GitHub](https://github.com) and sign in
2. Click the "+" icon → "New repository"
3. Repository name: `yaft`
4. Description: "Yet Another Forensic Tool - Plugin-based forensic analysis tool"
5. Choose "Public" or "Private"
6. **Do NOT initialize** with README, .gitignore, or license (we already have these)
7. Click "Create repository"

## Step 2: Push Your Code

```bash
# Initialize git (if not already done)
git init

# Add all files
git add .

# Create initial commit
git commit -m "feat: initial commit with full system requirements implementation"

# Add GitHub as remote (replace YOUR_USERNAME)
git remote add origin https://github.com/YOUR_USERNAME/yaft.git

# Push to GitHub
git branch -M main
git push -u origin main
```

## Step 3: Update README Badges

1. Open `README.md`
2. Find these lines at the top:
   ```markdown
   [![CI](https://github.com/YOUR_USERNAME/yaft/actions/workflows/ci.yml/badge.svg)](https://github.com/YOUR_USERNAME/yaft/actions/workflows/ci.yml)
   [![Release](https://github.com/YOUR_USERNAME/yaft/actions/workflows/release.yml/badge.svg)](https://github.com/YOUR_USERNAME/yaft/actions/workflows/release.yml)
   ```
3. Replace `YOUR_USERNAME` with your actual GitHub username
4. Commit and push:
   ```bash
   git add README.md
   git commit -m "docs: update GitHub username in badges"
   git push
   ```

## Step 4: Verify CI Pipeline

1. Go to: `https://github.com/YOUR_USERNAME/yaft/actions`
2. You should see the "CI" workflow running
3. Wait for it to complete (usually 3-5 minutes)
4. Verify all checks pass ✅

## Step 5: Create Your First Release

1. **Update version numbers**:

   Edit `pyproject.toml`:
   ```toml
   version = "0.1.0"  # Change to your desired version
   ```

   Edit `src/yaft/__init__.py`:
   ```python
   __version__ = "0.1.0"  # Change to your desired version
   ```

2. **Commit and tag**:
   ```bash
   git add pyproject.toml src/yaft/__init__.py
   git commit -m "chore: bump version to 0.1.0"
   git tag v0.1.0
   git push origin main
   git push origin v0.1.0
   ```

3. **Watch the magic happen**:
   - Go to: `https://github.com/YOUR_USERNAME/yaft/actions`
   - The "Build and Release" workflow will start automatically
   - After 5-10 minutes, you'll have:
     - ✅ Windows executable (`yaft-windows-x64.exe`)
     - ✅ macOS executable (`yaft-macos-x64`)
     - ✅ Linux executable (`yaft-linux-x64`)
     - ✅ GitHub Release with all executables attached

4. **Download and test**:
   - Go to: `https://github.com/YOUR_USERNAME/yaft/releases`
   - Download the executable for your platform
   - Test it:
     ```bash
     # Windows
     yaft-windows-x64.exe --version

     # macOS/Linux
     chmod +x yaft-macos-x64  # or yaft-linux-x64
     ./yaft-macos-x64 --version
     ```

## Step 6: Optional - Setup PyPI Publishing

If you want to publish to PyPI (so users can `pip install yaft`):

1. **Create PyPI account**:
   - Go to [PyPI](https://pypi.org)
   - Click "Register"
   - Verify your email

2. **Setup Trusted Publishing**:
   - Go to PyPI Account Settings → Publishing
   - Click "Add a new publisher"
   - Fill in:
     - PyPI Project Name: `yaft`
     - Owner: `YOUR_USERNAME`
     - Repository name: `yaft`
     - Workflow name: `release.yml`
     - Environment name: (leave blank)
   - Click "Add"

3. **Create next release**:
   ```bash
   # Update version to 0.1.1
   # ... edit files ...
   git commit -m "chore: bump version to 0.1.1"
   git tag v0.1.1
   git push origin main
   git push origin v0.1.1
   ```

4. **Verify PyPI upload**:
   - After the release workflow completes
   - Check: `https://pypi.org/project/yaft/`
   - Test installation: `pip install yaft`

## Troubleshooting

### CI Fails

**Problem**: Tests fail on GitHub but pass locally

**Solution**:
1. Check the error logs in GitHub Actions
2. Common issues:
   - Missing dependencies
   - Path differences (Windows vs Unix)
   - Python version differences
3. Fix the issue and push again

### Release Build Fails

**Problem**: PyInstaller fails to build executable

**Solution**:
1. Test PyInstaller locally first:
   ```bash
   # Windows
   pyinstaller --onefile --console --add-data "plugins;plugins" src/yaft/cli.py

   # macOS/Linux
   pyinstaller --onefile --console --add-data "plugins:plugins" src/yaft/cli.py
   ```
2. If it fails locally, fix the issue
3. If it works locally but fails on GitHub, check the workflow logs

### PyPI Publishing Fails

**Problem**: "Invalid or non-existent authentication information"

**Solution**:
1. Verify trusted publishing is configured correctly on PyPI
2. Check that the repository name and workflow name match exactly
3. Ensure the version number was bumped (can't republish same version)

## What Happens Automatically

### On Every Push to `main`/`develop`

✅ Linting with ruff
✅ Type checking with mypy
✅ Tests on Windows, macOS, and Linux
✅ Coverage reporting

### On Every Version Tag (`v*.*.*`)

✅ All CI checks
✅ Build executables for all platforms
✅ Create GitHub Release with executables
✅ Publish to PyPI (if configured)

### Weekly (via Dependabot)

✅ Check for dependency updates
✅ Create PRs for outdated packages
✅ Update GitHub Actions versions

## Next Steps

- ✅ Repository created and code pushed
- ✅ CI pipeline running
- ✅ First release created
- 📝 Consider adding:
  - Repository description and topics
  - `About` section with website and tags
  - Repository banner image
  - Wiki documentation
  - Discussions for user support

## Support

- 📝 Documentation: See `README.md` and `CONTRIBUTING.md`
- 🐛 Issues: `https://github.com/YOUR_USERNAME/yaft/issues`
- 💬 Discussions: `https://github.com/YOUR_USERNAME/yaft/discussions`

---

**Congratulations!** 🎉

You now have a fully automated CI/CD pipeline for YAFT. Every time you push a version tag, GitHub Actions will automatically build and release executables for all platforms.
