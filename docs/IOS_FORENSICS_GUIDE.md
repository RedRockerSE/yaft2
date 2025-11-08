# iOS Forensics Analysis with YaFT

Quick guide for using YaFT's iOS forensic analysis plugins.

## Prerequisites

1. Install YaFT dependencies:
```bash
cd C:\Users\Forensic\Desktop\dev\yaft
uv pip install -e ".[dev]"
```

2. Activate virtual environment:
```bash
# Windows
.venv\Scripts\activate
```

## Available iOS Plugins

YaFT includes two specialized iOS forensic analysis plugins:

### 1. iOSAppGUIDExtractorPlugin
Extracts application metadata, bundle IDs, and container GUIDs from iOS filesystem extractions.

### 2. iOSAppPermissionsExtractorPlugin
Extracts application permissions, usage statistics, and privacy data with risk scoring.

## Usage

**IMPORTANT:** Plugin names must use the full class name (ending with "Plugin").

### List Available Plugins

```bash
python -m yaft.cli list-plugins
```

### Extract iOS App Metadata

```bash
python -m yaft.cli run iOSAppGUIDExtractorPlugin --zip path\to\ios_extraction.zip
```

**What it does:**
- Parses MobileInstallation.plist for app data
- Queries applicationState.db for bundle IDs
- Enumerates filesystem for .app bundles
- Extracts bundle identifiers, container GUIDs, versions, display names
- Auto-detects Cellebrite extraction format

**Output:**
- `yaft_output/reports/iOSAppGUIDExtractorPlugin_YYYYMMDD_HHMMSS.md` - Markdown report
- `yaft_output/ios_extractions/[zipname]_apps.json` - JSON export with all app data
- Console output with summary tables

### Extract iOS App Permissions & Privacy Data

```bash
python -m yaft.cli run iOSAppPermissionsExtractorPlugin --zip path\to\ios_extraction.zip
```

**What it does:**
- Parses TCC.db for permission grants (Camera, Location, Contacts, etc.)
- Analyzes knowledgeC.db for app usage statistics
- Extracts notification settings from applicationState.plist
- Calculates risk scores based on permission types
- Identifies high-risk applications

**Output:**
- `yaft_output/reports/iOSAppPermissionsExtractorPlugin_YYYYMMDD_HHMMSS.md` - Analysis report
- `yaft_output/ios_extractions/[zipname]_permissions.json` - JSON export with permissions
- Console output with risk analysis tables

## Supported Extraction Formats

Both plugins support:
- **Standard iOS extractions** - Direct filesystem structure
- **Cellebrite UFED format** - Auto-detects `filesystem1/` or `filesystem/` prefix

The plugins automatically detect and adapt to the extraction format.

## Example Workflow

```bash
# 1. List available plugins to verify installation
python -m yaft.cli list-plugins

# 2. Extract app metadata from iOS extraction
python -m yaft.cli run iOSAppGUIDExtractorPlugin --zip cellebrite_iphone.zip

# 3. Extract permissions and privacy data
python -m yaft.cli run iOSAppPermissionsExtractorPlugin --zip cellebrite_iphone.zip

# 4. Check the output directory
dir yaft_output\reports
dir yaft_output\ios_extractions
```

## Output Files

### App Metadata JSON Structure
```json
[
  {
    "bundle_identifier": "com.example.app",
    "bundle_container_guid": "ABC123...",
    "data_container_guid": "XYZ789...",
    "display_name": "My App",
    "version": "1.0.0",
    "app_store_id": "123456789",
    "source": "MobileInstallation.plist"
  }
]
```

### Permissions JSON Structure
```json
{
  "extraction_metadata": {
    "extraction_date": "2025-11-05 12:00:00",
    "total_apps_analyzed": 150,
    "total_permissions": 450
  },
  "apps": {
    "com.example.app": {
      "bundle_id": "com.example.app",
      "permissions": [
        {
          "service_name": "Camera",
          "auth_status": "Allowed",
          "last_modified": "2025-10-01 10:30:00",
          "is_high_risk": true
        }
      ],
      "usage_stats": {
        "total_launches": 100,
        "total_duration_seconds": 36000,
        "first_used": "2025-09-01 08:00:00",
        "last_used": "2025-10-31 18:00:00"
      },
      "risk_score": 5.5,
      "permission_count": 8,
      "high_risk_permission_count": 3
    }
  }
}
```

## Troubleshooting

### Plugin Not Found Error

**Error:**
```
ERROR Plugin iOSAppGUIDExtractor is not loaded
```

**Solution:**
Use the full plugin class name ending with "Plugin":
```bash
# ❌ Wrong
python -m yaft.cli run iOSAppGUIDExtractor --zip file.zip

# ✅ Correct
python -m yaft.cli run iOSAppGUIDExtractorPlugin --zip file.zip
```

### ModuleNotFoundError: No module named 'yaft'

**Solution:**
Install dependencies and ensure you're in the correct directory:
```bash
cd C:\Users\Forensic\Desktop\dev\yaft
uv pip install -e ".[dev]"
```

### No ZIP file loaded

**Error:**
```
No ZIP file loaded. Use --zip option to specify an iOS extraction ZIP.
```

**Solution:**
Always use the `--zip` option:
```bash
python -m yaft.cli run iOSAppGUIDExtractorPlugin --zip path\to\extraction.zip
```

### TCC.db or knowledgeC.db not found

This is expected for incomplete extractions. The plugins will:
- Log a warning
- Continue with available data sources
- Generate reports with whatever data was found

## Key Files in iOS Extractions

The plugins look for these key forensic artifacts:

| File | Location | Plugin | Contains |
|------|----------|--------|----------|
| MobileInstallation.plist | private/var/mobile/Library/MobileInstallation/ | GUID | App metadata, container paths |
| applicationState.db | private/var/mobile/Library/FrontBoard/ | GUID | Bundle identifiers |
| Info.plist | private/var/containers/Bundle/Application/[GUID]/[App].app/ | GUID | App bundle information |
| TCC.db | private/var/mobile/Library/TCC/ | Permissions | Permission grants |
| knowledgeC.db | private/var/mobile/Library/CoreDuet/Knowledge/ | Permissions | App usage statistics |
| applicationState.plist | private/var/mobile/Library/SpringBoard/ | Permissions | Notification settings |

## High-Risk Permissions

The permissions plugin identifies these as high-risk:

- **Location Services** (Weight: 3.0)
- **Camera** (Weight: 2.5)
- **Microphone** (Weight: 2.5)
- **Contacts** (Weight: 2.0)
- **Photos** (Weight: 2.0)
- **Health** (Weight: 3.0)
- **Calendar** (Weight: 1.5)

Risk scores are calculated based on:
1. Permission types granted (weighted)
2. Total number of permissions (excessive permissions increase risk)
3. App usage frequency (frequently used apps have reduced risk)

## Integration with Other Tools

The JSON exports can be used with other forensic tools:

```bash
# Parse JSON with jq
cat yaft_output\ios_extractions\extraction_apps.json | jq '.[] | select(.app_store_id != "")'

# Import into analysis tools
python your_analysis_script.py --apps-json yaft_output\ios_extractions\extraction_apps.json
```

## Tips for Forensic Analysis

1. **Run both plugins** - App metadata and permissions provide complementary data
2. **Check risk scores** - Focus on apps with high risk scores first
3. **Review high-risk permissions** - Pay special attention to Location, Camera, Microphone
4. **Cross-reference with timeline** - Use knowledgeC.db usage data for timeline analysis
5. **Export JSON** - Use JSON exports for further analysis and correlation

## Support

For issues or questions:
- Check CLAUDE.md for technical details
- Review README.md for general YaFT usage
- See source code comments for implementation details

---

**Happy iOS forensic analysis!** 🔍📱
