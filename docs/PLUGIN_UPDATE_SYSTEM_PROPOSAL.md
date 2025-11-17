# Plugin Update System - Research and Recommendations

## Executive Summary

This document presents research findings and recommendations for implementing an automatic plugin update system for YAFT that synchronizes with a GitHub repository.

**Recommended Approach**: **Option 3 - Hybrid Approach with Manifest File**

---

## Requirements Analysis

### Core Requirements
1. Check if `plugins/` directory exists
2. Compare local plugins with GitHub repository plugins
3. Download missing plugins from GitHub
4. If directory doesn't exist, download all plugins
5. Maintain compatibility with existing YAFT architecture

### Additional Considerations
- Security (don't execute arbitrary code)
- Rate limiting (GitHub API limits)
- Offline capability (forensics tools often run offline)
- Version control (plugin compatibility)
- User control (opt-in vs automatic)

---

## Research Findings

### GitHub API Options

#### 1. **GitHub REST API - Contents Endpoint**
- **URL**: `https://api.github.com/repos/{owner}/{repo}/contents/{path}`
- **Pros**:
  - No authentication required for public repos
  - Returns file list with metadata (size, SHA hash)
  - Direct download URLs provided
- **Cons**:
  - Rate limited (60 requests/hour unauthenticated, 5000/hour authenticated)
  - 1,000 file limit per directory
  - Each file requires separate API call

#### 2. **Raw Content Downloads**
- **URL**: `https://raw.githubusercontent.com/{owner}/{repo}/{branch}/{path}`
- **Pros**:
  - Simple HTTP GET request
  - No API rate limits
  - Fast downloads
- **Cons**:
  - Need to know exact file paths
  - No file listing capability
  - No metadata (can't check if changed)

#### 3. **Git Trees API**
- **URL**: `https://api.github.com/repos/{owner}/{repo}/git/trees/{branch}?recursive=1`
- **Pros**:
  - Can get entire tree in one request
  - No 1,000 file limit
  - Includes SHA hashes for change detection
- **Cons**:
  - Still rate limited
  - More complex to parse
  - Large repositories can be slow

#### 4. **GitHub Releases API**
- **URL**: `https://api.github.com/repos/{owner}/{repo}/releases/latest`
- **Pros**:
  - Designed for distributing versioned artifacts
  - Can attach plugin bundles as assets
  - Good for versioned releases
- **Cons**:
  - Requires creating releases for each update
  - Additional workflow overhead
  - Doesn't reflect real-time development

### Python Libraries

#### 1. **PyGithub**
```python
from github import Github

g = Github()  # or Github(access_token)
repo = g.get_repo("owner/repo")
contents = repo.get_contents("plugins")
```
- **Pros**: High-level API, well-maintained, popular
- **Cons**: Additional dependency, rate limiting still applies

#### 2. **requests** (Standard Library Approach)
```python
import requests

url = "https://api.github.com/repos/owner/repo/contents/plugins"
response = requests.get(url)
files = response.json()
```
- **Pros**: Minimal dependencies, full control
- **Cons**: Manual implementation required

---

## Recommended Solutions

### **Option 1: Simple Raw File Download (Easiest)**

**Best for**: Quick implementation, minimal complexity

**Implementation**:
1. Maintain a `plugins_manifest.json` file in the repository
2. Download manifest from raw.githubusercontent.com
3. Parse manifest to get list of plugins
4. Download each plugin file using raw URLs
5. Compare with local plugins directory

**Advantages**:
- ✅ No API rate limits
- ✅ No authentication required
- ✅ Simple to implement
- ✅ Works offline (after initial download)
- ✅ No external dependencies

**Disadvantages**:
- ❌ Requires maintaining manifest file
- ❌ No automatic change detection
- ❌ Manual manifest updates

**Code Structure**:
```python
# plugins_manifest.json
{
  "version": "1.0.0",
  "last_updated": "2025-01-17",
  "plugins": [
    {
      "name": "iOSDeviceInfoExtractorPlugin",
      "file": "ios_device_info_extractor.py",
      "version": "1.0.0",
      "sha256": "abc123...",
      "required": true
    },
    ...
  ]
}
```

**Implementation Difficulty**: ⭐⭐☆☆☆ (Easy)

---

### **Option 2: GitHub Contents API (Standard)**

**Best for**: Dynamic updates, GitHub-native approach

**Implementation**:
1. Query GitHub Contents API for `plugins/` directory
2. Get list of `.py` files with SHA hashes
3. Compare with local files (hash comparison)
4. Download updated/missing files

**Advantages**:
- ✅ No manifest maintenance
- ✅ SHA hash for change detection
- ✅ GitHub-native solution
- ✅ Metadata included (size, type)

**Disadvantages**:
- ❌ Rate limiting (60 requests/hour without auth)
- ❌ Requires API calls
- ❌ Needs internet connection
- ❌ Potential for throttling

**Rate Limit Mitigation**:
```python
import os

# Option A: Use personal access token (5000 requests/hour)
token = os.environ.get('GITHUB_TOKEN')  # Optional

# Option B: Cache API responses
# Option C: Only check on user request, not every startup
```

**Implementation Difficulty**: ⭐⭐⭐☆☆ (Medium)

---

### **Option 3: Hybrid Approach with Manifest (RECOMMENDED)**

**Best for**: Balance of reliability, performance, and maintainability

**Implementation**:
1. Maintain `plugins_manifest.json` in repository
2. Use GitHub Contents API to check if manifest changed (1 API call)
3. If manifest unchanged, use cached data
4. If changed, download new manifest and update plugins
5. Download plugins via raw URLs (no rate limits)

**Advantages**:
- ✅ Minimal API calls (just manifest check)
- ✅ Fast plugin downloads (raw URLs)
- ✅ SHA hash verification
- ✅ Offline-friendly (cache manifest)
- ✅ Version tracking
- ✅ User control (check only when requested)

**Disadvantages**:
- ❌ Requires manifest maintenance (can be automated with GitHub Actions)
- ❌ Small additional complexity

**Workflow**:
```
Startup → Check cache → Manifest outdated? → Download manifest → Compare → Download plugins
           ↓                    ↓
      Use cache           Do nothing
```

**Implementation Difficulty**: ⭐⭐⭐☆☆ (Medium)

---

### **Option 4: Separate Plugin Repository (Advanced)**

**Best for**: Large-scale, enterprise deployment

**Implementation**:
1. Create separate `yaft-plugins` repository
2. Use GitHub Releases for versioned plugin bundles
3. YAFT checks releases API for updates
4. Download plugin bundle (ZIP)
5. Verify signature/checksum
6. Extract to `plugins/`

**Advantages**:
- ✅ Clean separation of concerns
- ✅ Versioned releases
- ✅ Can bundle multiple plugins
- ✅ Easy to manage permissions
- ✅ Professional distribution model

**Disadvantages**:
- ❌ Requires separate repository
- ❌ Release workflow overhead
- ❌ More complex infrastructure

**Implementation Difficulty**: ⭐⭐⭐⭐☆ (Hard)

---

## Detailed Recommendation: Option 3 Implementation

### Architecture

```
yaft/
├── src/yaft/
│   └── plugin_updater.py      # New module
├── plugins/
│   └── (plugin files)
├── .plugin_cache/
│   ├── manifest.json          # Cached manifest
│   └── last_check.txt         # Timestamp
└── plugins_manifest.json      # In repository
```

### Plugin Manifest Format

```json
{
  "manifest_version": "1.0.0",
  "last_updated": "2025-01-17T10:00:00Z",
  "repository": "RedRockerSE/yaft2",
  "branch": "main",
  "plugins": [
    {
      "name": "iOSDeviceInfoExtractorPlugin",
      "filename": "ios_device_info_extractor.py",
      "version": "1.0.0",
      "description": "Extract comprehensive device information",
      "sha256": "abc123def456...",
      "size": 20940,
      "required": true,
      "os_target": ["ios"],
      "dependencies": []
    },
    {
      "name": "AndroidDeviceInfoExtractorPlugin",
      "filename": "android_device_info_extractor.py",
      "version": "1.0.0",
      "description": "Extract Android device information",
      "sha256": "def789ghi012...",
      "size": 30580,
      "required": true,
      "os_target": ["android"],
      "dependencies": []
    }
  ]
}
```

### Core API Extension

Add to `src/yaft/core/plugin_updater.py`:

```python
class PluginUpdater:
    """Handle plugin updates from GitHub repository."""

    def __init__(self,
                 repo: str = "RedRockerSE/yaft2",
                 branch: str = "main",
                 plugins_dir: Path = Path("plugins")):
        self.repo = repo
        self.branch = branch
        self.plugins_dir = plugins_dir
        self.cache_dir = Path(".plugin_cache")

    def check_for_updates(self, force: bool = False) -> Dict[str, Any]:
        """Check if plugin updates are available."""

    def download_plugins(self, plugin_list: List[str]) -> bool:
        """Download specified plugins."""

    def update_all_plugins(self) -> Dict[str, Any]:
        """Update all plugins to latest version."""

    def verify_plugin(self, filename: str, expected_sha256: str) -> bool:
        """Verify downloaded plugin integrity."""
```

### CLI Integration

Add to `src/yaft/cli.py`:

```python
@app.command()
def update_plugins(
    force: bool = typer.Option(False, "--force", help="Force update check"),
    plugin: Optional[str] = typer.Option(None, "--plugin", help="Update specific plugin"),
):
    """Update plugins from GitHub repository."""

@app.command()
def list_available_plugins():
    """List all available plugins in repository."""
```

### User Experience

```bash
# Check for plugin updates
python -m yaft.cli update-plugins

# Force check (ignore cache)
python -m yaft.cli update-plugins --force

# Update specific plugin
python -m yaft.cli update-plugins --plugin iOSDeviceInfoExtractorPlugin

# List available plugins
python -m yaft.cli list-available-plugins

# Automatic check on startup (configurable)
python -m yaft.cli run MyPlugin --zip evidence.zip --check-updates
```

### Configuration

Add to user config file (`.yaft/config.toml`):

```toml
[updates]
auto_check = true              # Check on startup
check_interval_hours = 24      # How often to check
auto_download = false          # Prompt user
repository = "RedRockerSE/yaft2"
branch = "main"
github_token = ""              # Optional, for higher rate limits
```

### Security Considerations

1. **SHA256 Verification**: Always verify downloaded files
2. **HTTPS Only**: Use secure connections
3. **No Code Execution**: Don't execute during download
4. **User Confirmation**: Prompt before updating
5. **Backup**: Keep backup of old plugins
6. **Signature Verification**: (Optional) GPG signatures

### Manifest Automation

Create GitHub Actions workflow (`.github/workflows/update-manifest.yml`):

```yaml
name: Update Plugin Manifest

on:
  push:
    paths:
      - 'plugins/*.py'
  workflow_dispatch:

jobs:
  update-manifest:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Generate Plugin Manifest
        run: python scripts/generate_manifest.py
      - name: Commit Changes
        run: |
          git config user.name "GitHub Actions"
          git add plugins_manifest.json
          git commit -m "chore: update plugin manifest" || exit 0
          git push
```

---

## Alternative: Keep Plugins in Same Repository

### Pros
- ✅ Single source of truth
- ✅ Synchronized versioning
- ✅ Simpler for developers
- ✅ Git history preserved
- ✅ No additional infrastructure

### Cons
- ❌ Larger repository size
- ❌ Core updates affect plugins
- ❌ Users download entire repo

**Recommendation**: **Keep in same repository** for simplicity.

---

## Alternative: Separate Plugin Repository

### Pros
- ✅ Clean separation
- ✅ Independent versioning
- ✅ Smaller YAFT core
- ✅ Easier to manage permissions
- ✅ Professional appearance

### Cons
- ❌ Additional repository to maintain
- ❌ Synchronization complexity
- ❌ Two places for issues/PRs
- ❌ More overhead for contributors

**Recommendation**: **Not recommended** unless YAFT becomes very large.

---

## Implementation Phases

### Phase 1: Foundation (Week 1)
- Create `PluginUpdater` class
- Implement manifest parsing
- Add basic download functionality
- Write tests

### Phase 2: CLI Integration (Week 2)
- Add CLI commands
- Implement user prompts
- Add configuration options
- Create documentation

### Phase 3: Automation (Week 3)
- GitHub Actions for manifest
- Auto-check on startup (optional)
- Cache management
- Error handling

### Phase 4: Polish (Week 4)
- SHA256 verification
- Progress indicators
- Better error messages
- User guide

---

## Estimated Effort

| Component | Effort | Priority |
|-----------|--------|----------|
| Plugin Updater Class | 8 hours | High |
| Manifest System | 4 hours | High |
| CLI Commands | 4 hours | High |
| Testing | 6 hours | High |
| GitHub Actions | 2 hours | Medium |
| Documentation | 3 hours | High |
| Configuration | 2 hours | Medium |
| **Total** | **29 hours** | |

---

## Risk Analysis

| Risk | Probability | Impact | Mitigation |
|------|------------|--------|------------|
| GitHub API rate limiting | Medium | Medium | Use manifest + caching, optional token |
| Network unavailable | High | Low | Cache manifests, offline mode |
| Malicious plugins | Low | High | SHA256 verification, code review |
| Breaking changes | Medium | High | Version compatibility checking |
| Corrupted downloads | Low | Medium | Integrity checks, retry logic |

---

## Conclusion

### Final Recommendation

**Implement Option 3: Hybrid Approach with Manifest**

**Repository Structure**: Keep plugins in main repository

**Key Features**:
1. Manifest-based plugin discovery
2. Raw URL downloads (fast, no rate limits)
3. SHA256 verification
4. Offline-friendly caching
5. User-controlled updates
6. GitHub Actions automation

**First Steps**:
1. Create `plugins_manifest.json` with current plugins
2. Implement `PluginUpdater` class in Core API
3. Add `update-plugins` CLI command
4. Write tests
5. Document user workflow

**Timeline**: 4 weeks for full implementation

**Dependencies**:
- `requests` (already in requirements)
- `hashlib` (standard library)
- No new external dependencies required

This approach balances simplicity, performance, security, and maintainability while respecting the offline nature of forensic work.
