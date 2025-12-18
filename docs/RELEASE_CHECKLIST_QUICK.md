# YAFT Release Checklist - Quick Reference

**Quick checklist for experienced maintainers. See `RELEASE_CHECKLIST.md` for detailed instructions.**

---

## Pre-Build (5 min)
```bash
□ pytest --cov=src/yaft
□ ruff check src/ tests/ plugins/
□ mypy src/
□ Update version in __init__.py, pyproject.toml
□ git status (clean)
```

---

## Build (2 min)
```bash
□ python build_exe.py --clean
□ Verify: [OK] Type stubs generated
□ Verify: [OK] Created Pylance config
□ Verify: [OK] Created VS Code settings
```

---

## Verify Distribution (3 min)
```bash
cd dist/yaft

□ Check structure:
  ✓ yaft.exe
  ✓ plugins/README.md
  ✓ yaft-stubs/yaft/core/*.pyi (5 files)
  ✓ pyrightconfig.json
  ✓ .vscode/settings.json

□ Test executable:
  ./yaft.exe list-plugins
  ./yaft.exe run PluginName --zip test.zip
```

---

## Test IntelliSense (3 min)
```bash
□ code dist/yaft
□ Select Python interpreter
□ Create test.py in plugins/
□ Type: from yaft.core.api import CoreAPI
□ Type: self.core_api. → see autocomplete
□ Hover over methods → see docs
□ F12 on CoreAPI → jumps to api.pyi
```

---

## Package (2 min)
```bash
cd dist
□ zip -r yaft-windows-x64-v0.5.0.zip yaft/
□ sha256sum *.zip > SHA256SUMS.txt
□ cat SHA256SUMS.txt
```

---

## Release (5 min)
```bash
□ Create GitHub release (tag: v0.5.0)
□ Upload: yaft-windows-x64-v0.5.0.zip
□ Upload: SHA256SUMS.txt
□ Paste release notes
□ Publish release
```

---

## Critical Checks ✅

**MUST HAVE:**
- [ ] Executable runs
- [ ] 5 stub files present (~67 KB total)
- [ ] pyrightconfig.json exists
- [ ] IntelliSense works in VS Code
- [ ] Checksums generated

**SHOULD HAVE:**
- [ ] All plugins tested
- [ ] Release notes written
- [ ] Documentation updated

---

## Quick Troubleshooting

**Stub generation fails:** `uv pip install mypy`
**IntelliSense not working:** Check pyrightconfig.json exists, open folder (not files)
**Unicode errors:** Fixed in build script (uses [OK] not ✓)

---

## Distribution Size Reference

**v0.5.0 with IntelliSense:**
- Executable: ~12 MB
- Stubs: 67 KB
- Total ZIP: ~12.5 MB

---

**Total Time: ~20 minutes**

Print this checklist and check off items during release!
