# YAFT Release Checklist

This checklist ensures that YAFT executable distributions are complete, tested, and ready for plugin developers.

---

## Pre-Build Checklist

### Code & Dependencies

- [ ] All tests pass: `pytest --cov=src/yaft`
- [ ] No linting errors: `ruff check src/ tests/ plugins/`
- [ ] Code formatted: `ruff format src/ tests/ plugins/`
- [ ] Type checking passes: `mypy src/`
- [ ] All dependencies up to date in `requirements.txt`
- [ ] Development dependencies current in `requirements-dev.txt`
- [ ] Virtual environment clean: `uv pip list` shows expected packages only

### Version & Documentation

- [ ] Version bumped in:
  - [ ] `src/yaft/__init__.py`
  - [ ] `pyproject.toml`
  - [ ] `CHANGELOG.md` (if exists)
- [ ] `CLAUDE.md` updated with new features
- [ ] `README.md` reflects current features
- [ ] All documentation files reviewed for accuracy

### Plugin System

- [ ] All production plugins tested:
  - [ ] `iOSDeviceInfoExtractorPlugin`
  - [ ] `iOSCallLogAnalyzerPlugin`
  - [ ] `iOSCellularInfoExtractorPlugin`
  - [ ] `AndroidDeviceInfoExtractorPlugin`
  - [ ] `AndroidAppInfoExtractorPlugin`
  - [ ] `AndroidAppPermissionsExtractorPlugin`
  - [ ] `AndroidCallLogAnalyzerPlugin`
- [ ] Plugin manifest updated: `plugins_manifest.json`
- [ ] Example/test plugins removed from `plugins/` directory

### Git Repository

- [ ] All changes committed
- [ ] Branch is up to date with `main`
- [ ] No uncommitted changes: `git status`
- [ ] Git tags match version (if tagging releases)

---

## Build Process

### Environment Setup

- [ ] Clean virtual environment:
  ```bash
  rm -rf .venv
  uv venv
  uv pip install -e ".[dev]"
  ```
- [ ] Verify `mypy` installed: `uv pip list | grep mypy`
- [ ] Verify `pyinstaller` installed: `uv pip list | grep pyinstaller`

### Clean Build

- [ ] Remove previous build artifacts:
  ```bash
  python build_exe.py --clean
  ```
- [ ] Verify build directories cleaned:
  - [ ] `build/` directory removed
  - [ ] `dist/` directory removed

### Execute Build

- [ ] Run build script:
  ```bash
  python build_exe.py
  ```
- [ ] Build completed without errors
- [ ] All success messages displayed:
  - [ ] `[OK] Type stubs generated`
  - [ ] `[OK] Created Pylance config`
  - [ ] `[OK] Created VS Code settings`
  - [ ] `[OK] Created plugin README`

---

## Post-Build Verification

### Distribution Structure

Verify the following structure exists in `dist/yaft/`:

#### Core Files
- [ ] `yaft.exe` (Windows) or `yaft` (Linux/macOS)
- [ ] `_internal/` directory with PyInstaller runtime files

#### Plugin Development Files
- [ ] `plugins/` directory exists
- [ ] `plugins/README.md` with IntelliSense instructions
- [ ] No test/example plugins in `plugins/` (unless intentional)

#### IntelliSense Support Files
- [ ] `yaft-stubs/` directory exists
- [ ] `yaft-stubs/yaft/core/__init__.pyi`
- [ ] `yaft-stubs/yaft/core/api.pyi` (~54 KB)
- [ ] `yaft-stubs/yaft/core/plugin_base.pyi`
- [ ] `yaft-stubs/yaft/core/plugin_manager.pyi`
- [ ] `yaft-stubs/yaft/core/plugin_updater.pyi`

#### Configuration Files
- [ ] `pyrightconfig.json` in root
- [ ] `.vscode/settings.json` created

#### Documentation Files (Optional)
- [ ] `INTELLISENSE_VERIFICATION.md` (for verification)
- [ ] Can be removed before distribution if desired

### Stub File Quality

- [ ] Check `api.pyi` has complete signatures:
  ```bash
  grep "def log_info" dist/yaft/yaft-stubs/yaft/core/api.pyi
  grep "def generate_report" dist/yaft/yaft-stubs/yaft/core/api.pyi
  ```
- [ ] Verify docstrings preserved:
  ```bash
  grep '"""' dist/yaft/yaft-stubs/yaft/core/api.pyi | head -5
  ```
- [ ] Check file sizes are reasonable:
  ```bash
  ls -lh dist/yaft/yaft-stubs/yaft/core/
  ```

### Configuration File Validation

- [ ] `pyrightconfig.json` is valid JSON:
  ```bash
  python -m json.tool dist/yaft/pyrightconfig.json
  ```
- [ ] `.vscode/settings.json` is valid JSON:
  ```bash
  python -m json.tool dist/yaft/.vscode/settings.json
  ```

---

## Functional Testing

### Basic Executable Tests

- [ ] Executable runs without errors:
  ```bash
  cd dist/yaft
  ./yaft.exe --help
  ```
- [ ] List plugins command works:
  ```bash
  ./yaft.exe list-plugins
  ```
- [ ] Plugin info command works (if any plugins present):
  ```bash
  ./yaft.exe info PluginName
  ```

### Plugin Execution Tests

Test with sample forensic ZIP files:

#### iOS Plugin Tests
- [ ] Test with Cellebrite iOS extraction:
  ```bash
  ./yaft.exe run iOSDeviceInfoExtractorPlugin --zip ios_cellebrite.zip
  ```
- [ ] Test with GrayKey iOS extraction:
  ```bash
  ./yaft.exe run iOSDeviceInfoExtractorPlugin --zip ios_graykey.zip
  ```
- [ ] Verify report generated in `yaft_output/`
- [ ] Verify JSON export created

#### Android Plugin Tests
- [ ] Test with Cellebrite Android extraction:
  ```bash
  ./yaft.exe run AndroidDeviceInfoExtractorPlugin --zip android_cellebrite.zip
  ```
- [ ] Test with GrayKey Android extraction:
  ```bash
  ./yaft.exe run AndroidDeviceInfoExtractorPlugin --zip android_graykey.zip
  ```
- [ ] Verify report generated in `yaft_output/`
- [ ] Verify JSON export created

#### Profile Execution Tests
- [ ] Test iOS full analysis profile:
  ```bash
  ./yaft.exe run --zip ios.zip --profile ../../../profiles/ios_full_analysis.toml
  ```
- [ ] Test Android full analysis profile:
  ```bash
  ./yaft.exe run --zip android.zip --profile ../../../profiles/android_full_analysis.toml
  ```

### Report Generation Tests
- [ ] Markdown reports generated correctly
- [ ] PDF export works (if `--pdf` flag used):
  ```bash
  ./yaft.exe run PluginName --zip test.zip --pdf
  ```
- [ ] HTML export works (if `--html` flag used):
  ```bash
  ./yaft.exe run PluginName --zip test.zip --html
  ```
- [ ] Reports include case identifiers when prompted

### Plugin Update System Tests
- [ ] Check for updates works:
  ```bash
  ./yaft.exe update-plugins --check-only
  ```
- [ ] List available plugins works:
  ```bash
  ./yaft.exe list-available-plugins
  ```

---

## IntelliSense Testing

### VS Code Setup Test

- [ ] Open `dist/yaft/` folder in VS Code
- [ ] Select Python 3.12+ interpreter
- [ ] Create test plugin: `plugins/test.py`

### IntelliSense Feature Tests

Test the following in VS Code:

#### Import Resolution
- [ ] No red squiggles on:
  ```python
  from yaft.core.api import CoreAPI
  from yaft.core.plugin_base import PluginBase, PluginMetadata
  ```

#### Autocomplete
- [ ] Type `self.core_api.` → autocomplete menu appears
- [ ] Shows `log_info`, `print_success`, `get_current_zip`, etc.
- [ ] Method signatures shown in autocomplete

#### Hover Information
- [ ] Hover over `CoreAPI` → shows class docstring
- [ ] Hover over `log_info` → shows method signature and docstring
- [ ] Hover over `generate_report` → shows full parameter list

#### Go to Definition (F12)
- [ ] F12 on `CoreAPI` → jumps to `api.pyi`
- [ ] F12 on `PluginBase` → jumps to `plugin_base.pyi`
- [ ] F12 on method → jumps to method definition in stub

#### Parameter Hints
- [ ] Type `self.core_api.generate_report(` → parameter hints appear
- [ ] Shows required and optional parameters
- [ ] Shows parameter types

#### Type Checking
- [ ] Type error shown for: `self.core_api.log_info(123)`
- [ ] No error for: `self.core_api.log_info("test")`

### Pylance/Pyright Status
- [ ] No Pylance errors in Output panel
- [ ] Stub path recognized in Pylance logs
- [ ] Type checking mode set to "basic"

---

## Distribution Preparation

### Clean Up Distribution

#### Remove Verification Files (Optional)
- [ ] Remove `INTELLISENSE_VERIFICATION.md` (if not distributing)
- [ ] Remove test plugins (if any)
- [ ] Keep `plugins/README.md`

#### Remove Build Artifacts
- [ ] Remove `.pyc` files: `find dist/yaft -name "*.pyc" -delete`
- [ ] Remove `__pycache__` directories: `find dist/yaft -type d -name "__pycache__" -delete`

### Create Distribution Archive

#### Windows Distribution
- [ ] Create ZIP archive:
  ```bash
  cd dist
  zip -r yaft-windows-x64-v0.5.0.zip yaft/
  ```
- [ ] Verify archive contains all files:
  ```bash
  unzip -l yaft-windows-x64-v0.5.0.zip | grep -E "(yaft.exe|pyrightconfig|yaft-stubs)"
  ```

#### Linux Distribution (if applicable)
- [ ] Create tar.gz archive:
  ```bash
  cd dist
  tar -czf yaft-linux-x64-v0.5.0.tar.gz yaft/
  ```
- [ ] Verify archive:
  ```bash
  tar -tzf yaft-linux-x64-v0.5.0.tar.gz | grep -E "(yaft$|pyrightconfig|yaft-stubs)"
  ```

### Generate Checksums
- [ ] Generate SHA256 checksums:
  ```bash
  sha256sum dist/*.zip > dist/SHA256SUMS.txt
  sha256sum dist/*.tar.gz >> dist/SHA256SUMS.txt
  ```
- [ ] Verify checksums:
  ```bash
  cat dist/SHA256SUMS.txt
  ```

---

## Documentation Package

### Required Documentation Files

Create a `docs/` folder in the distribution (optional but recommended):

- [ ] `GETTING_STARTED.md` - Quick start guide
- [ ] `PLUGIN_DEVELOPMENT_SE.md` - IntelliSense setup guide
- [ ] `API_REFERENCE.md` - CoreAPI method reference (generated via `api-docs`)
- [ ] `CHANGELOG.md` - Version history
- [ ] `LICENSE` - Software license

### Documentation Verification

- [ ] All file paths in documentation are correct for distribution
- [ ] No references to development environment paths
- [ ] Screenshots up to date (if any)
- [ ] Examples tested and working

---

## Release Notes

### Create Release Notes Document

- [ ] Document new features
- [ ] Document bug fixes
- [ ] Document breaking changes (if any)
- [ ] Include upgrade instructions (if applicable)
- [ ] List known issues (if any)

### Sample Release Notes Template

```markdown
# YAFT v0.5.0 Release Notes

**Release Date:** December 18, 2025

## New Features

### VS Code IntelliSense Support
- Full autocomplete for CoreAPI methods (100+ methods)
- Type hints on hover
- Go-to-definition support (F12)
- Parameter hints during method calls
- Type error detection before runtime

**Benefits for Plugin Developers:**
- Professional development experience
- Faster plugin development
- Fewer runtime errors
- Better code quality

### Other Features
- [List other new features]

## Bug Fixes
- [List bug fixes]

## Breaking Changes
- [List breaking changes, if any]

## Known Issues
- [List known issues, if any]

## Upgrade Instructions
- [Provide upgrade instructions if needed]

## Distribution Files
- `yaft-windows-x64-v0.5.0.zip` (12.5 MB)
- `yaft-linux-x64-v0.5.0.tar.gz` (11.8 MB)
- `SHA256SUMS.txt`
```

---

## Distribution Channels

### GitHub Release (if using GitHub)

- [ ] Create new release on GitHub
- [ ] Tag version: `v0.5.0`
- [ ] Upload distribution archives
- [ ] Upload checksums file
- [ ] Paste release notes
- [ ] Mark as pre-release (if applicable)
- [ ] Publish release

### Documentation Site (if applicable)

- [ ] Update download links
- [ ] Update version number
- [ ] Update documentation
- [ ] Update screenshots (if needed)

### Communication

- [ ] Announce release on relevant channels
- [ ] Update project README with new version
- [ ] Update any external documentation or wikis

---

## Post-Release Verification

### Download & Test

- [ ] Download distributed archive from release location
- [ ] Extract archive in clean directory
- [ ] Verify all files present
- [ ] Run executable to verify it works
- [ ] Test IntelliSense in VS Code from extracted distribution
- [ ] Verify checksums match:
  ```bash
  sha256sum yaft-windows-x64-v0.5.0.zip
  ```

### User Testing (if applicable)

- [ ] Have team member test on clean machine
- [ ] Test on different Windows versions (10, 11)
- [ ] Test on Linux distributions (if Linux build)
- [ ] Collect feedback on IntelliSense experience

---

## Rollback Plan

Document rollback procedures in case issues are found:

- [ ] Previous version archives backed up
- [ ] Rollback procedure documented:
  1. Download previous version
  2. Extract and verify
  3. Update release notes with rollback information
  4. Notify users if necessary

---

## Final Checklist Summary

### Critical Items ✅
- [ ] All tests pass
- [ ] Build completes without errors
- [ ] Executable runs on clean machine
- [ ] Type stubs generated (5 files, ~67 KB)
- [ ] Configuration files present (pyrightconfig.json, .vscode/settings.json)
- [ ] IntelliSense verified in VS Code
- [ ] Distribution archive created
- [ ] Checksums generated
- [ ] Release notes written

### Optional but Recommended 📋
- [ ] Documentation package included
- [ ] Example plugins provided
- [ ] Video tutorial created (if applicable)
- [ ] Migration guide (if breaking changes)

### Post-Release 📢
- [ ] Release announced
- [ ] Documentation updated
- [ ] User feedback collected
- [ ] Issues tracked

---

## Version-Specific Notes

### Version 0.5.0 - IntelliSense Support

**New Distribution Files:**
- `yaft-stubs/` directory (67 KB) - **CRITICAL**
- `pyrightconfig.json` - **CRITICAL**
- `.vscode/settings.json` - **RECOMMENDED**
- Updated `plugins/README.md` with IntelliSense instructions

**Testing Focus:**
- Verify stub generation for all 5 core modules
- Test IntelliSense in VS Code thoroughly
- Ensure Windows console encoding issues resolved (no Unicode errors)

**Documentation Updates:**
- `PLUGIN_DEVELOPMENT_SE.md` - New file explaining IntelliSense setup
- `CLAUDE.md` - Updated with IntelliSense section (if applicable)
- `plugins/README.md` - Updated with VS Code setup instructions

---

## Troubleshooting Common Release Issues

### Issue: Stub Generation Fails

**Symptoms:** `Warning: stubgen not found`

**Fix:**
```bash
uv pip install mypy
python build_exe.py --clean
```

### Issue: Unicode Encoding Errors During Build

**Symptoms:** `UnicodeEncodeError: 'charmap' codec can't encode character`

**Fix:** Ensure all print statements use ASCII-safe characters (no emoji, no ✓)

### Issue: IntelliSense Not Working After Distribution

**Check:**
1. `pyrightconfig.json` present in distribution root
2. `yaft-stubs/` directory present
3. User opened **folder** in VS Code, not individual files
4. Python interpreter selected in VS Code

### Issue: Executable Won't Run on Target Machine

**Check:**
1. Windows Defender/antivirus not blocking
2. All PyInstaller runtime files in `_internal/` present
3. No missing DLL dependencies
4. User has correct permissions

---

## Release Sign-Off

**Release Manager:** _________________
**Date:** _________________
**Version:** _________________

**Approved for Release:** [ ] Yes [ ] No

**Notes:**
_________________________________________________________________
_________________________________________________________________
_________________________________________________________________

---

**End of Release Checklist**

*Keep this checklist for every release. Update as processes evolve.*
