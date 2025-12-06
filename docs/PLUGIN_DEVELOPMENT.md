# Plugin Development Guide

This guide covers everything you need to know to develop plugins for YAFT.

## Table of Contents

1. [Plugin Basics](#plugin-basics)
2. [Plugin Interface](#plugin-interface)
3. [Plugin Metadata](#plugin-metadata)
4. [Plugin Lifecycle](#plugin-lifecycle)
5. [Using Core API](#using-core-api)
6. [Best Practices](#best-practices)
7. [Advanced Topics](#advanced-topics)
8. [Testing Plugins](#testing-plugins)

## Plugin Basics

### What is a Plugin?

A plugin is a Python module that extends YAFT's functionality. Plugins are:
- **Dynamically loadable**: Discovered and loaded at runtime
- **Self-contained**: Include all their logic and dependencies
- **Loosely coupled**: Only depend on the PluginBase interface
- **Lifecycle-managed**: Have clear initialization, execution, and cleanup phases

### File Structure

```
plugins/
└── my_plugin.py       # Your plugin file
```

Each plugin file should contain one class that inherits from `PluginBase`.

## Plugin Interface

### Required Methods

Every plugin must implement these methods:

```python
from typing import Any
from yaft.core.api import CoreAPI
from yaft.core.plugin_base import PluginBase, PluginMetadata


class MyPlugin(PluginBase):
    """Your plugin description."""

    def __init__(self, core_api: CoreAPI) -> None:
        """Initialize with CoreAPI access."""
        super().__init__(core_api)
        # Your initialization here

    @property
    def metadata(self) -> PluginMetadata:
        """Return plugin metadata."""
        return PluginMetadata(
            name="MyPlugin",
            version="1.0.0",
            description="What your plugin does",
            author="Your Name",
        )

    def initialize(self) -> None:
        """Setup resources, validate dependencies."""
        pass

    def execute(self, *args: Any, **kwargs: Any) -> Any:
        """Main plugin logic."""
        pass

    def cleanup(self) -> None:
        """Release resources, save state."""
        pass
```

## Plugin Metadata

### PluginMetadata Fields

```python
PluginMetadata(
    name="MyPlugin",                    # Required: Unique identifier
    version="1.0.0",                    # Required: Semantic version
    description="Plugin description",   # Required: What it does
    author="Your Name",                 # Optional: Your name
    requires_core_version=">=0.1.0",   # Optional: Min core version
    dependencies=[],                    # Optional: Other plugins needed
    enabled=True,                       # Optional: Enable/disable
)
```

### Version Format

Use semantic versioning (MAJOR.MINOR.PATCH):
- MAJOR: Breaking changes
- MINOR: New features (backward compatible)
- PATCH: Bug fixes

### Dependencies

List other plugins your plugin needs:

```python
PluginMetadata(
    name="DataProcessor",
    version="1.0.0",
    description="Processes data from other plugins",
    dependencies=["DataLoader", "DataValidator"],
)
```

## Plugin Lifecycle

### 1. Instantiation

```python
def __init__(self, core_api: CoreAPI) -> None:
    super().__init__(core_api)
    # Initialize instance variables
    self._counter = 0
    self._cache: dict[str, Any] = {}
```

**Do:**
- Initialize instance variables
- Store CoreAPI reference
- Set default values

**Don't:**
- Access external resources
- Perform I/O operations
- Validate dependencies (use initialize() for this)

### 2. Initialization

```python
def initialize(self) -> None:
    """Setup phase - called once after plugin is loaded."""
    self.core_api.log_info(f"Initializing {self.metadata.name}")

    # Load configuration
    config_path = self.core_api.get_config_path("my_plugin.toml")
    if config_path.exists():
        self._load_config(config_path)

    # Validate dependencies
    if not self._check_dependencies():
        raise RuntimeError("Dependencies not met")

    # Setup resources
    self._setup_resources()
```

**Do:**
- Load configuration files
- Validate dependencies
- Allocate resources
- Register event handlers
- Raise exceptions if setup fails

**Don't:**
- Perform the main plugin work (use execute() for this)
- Start long-running processes
- Assume resources exist (check first)

### 3. Execution

```python
def execute(self, *args: Any, **kwargs: Any) -> Any:
    """Main plugin logic - called when plugin runs."""
    # Parse arguments
    input_data = args[0] if args else kwargs.get("data")

    # Validate input
    if not self._validate_input(input_data):
        self.core_api.print_error("Invalid input")
        return None

    # Process
    result = self._process(input_data)

    # Display results
    self._display_results(result)

    return result
```

**Do:**
- Implement main plugin functionality
- Handle arguments gracefully
- Validate input
- Return meaningful results
- Use CoreAPI for output
- Handle errors gracefully

**Don't:**
- Rely on specific arguments without checking
- Print directly (use CoreAPI)
- Exit the application
- Leave resources open (close them)

### 4. Cleanup

```python
def cleanup(self) -> None:
    """Teardown phase - called when plugin unloads."""
    self.core_api.log_info(f"Cleaning up {self.metadata.name}")

    # Close file handles
    if hasattr(self, "_file_handle"):
        self._file_handle.close()

    # Save state
    self._save_state()

    # Clear cache
    self._cache.clear()

    # Release resources
    self._release_resources()
```

**Do:**
- Close file handles
- Release network connections
- Save state if needed
- Clear caches
- Log cleanup actions

**Don't:**
- Raise exceptions (log errors instead)
- Perform long operations
- Access already-cleaned resources

## Using Core API

The Core API provides a comprehensive set of methods for plugin development. This section covers all available functionality.

### Logging

```python
# Different log levels
self.core_api.log_debug("Detailed diagnostic information")
self.core_api.log_info("General information")
self.core_api.log_warning("Warning messages")
self.core_api.log_error("Error messages")
```

### Colored Output

```python
# Status messages with colors
self.core_api.print_success("Operation completed")
self.core_api.print_error("Operation failed")
self.core_api.print_warning("Be careful")
self.core_api.print_info("For your information")
```

### User Input

```python
# Get text input
name = self.core_api.get_user_input("Enter your name")

# Get confirmation
if self.core_api.confirm("Delete all files?"):
    delete_files()
```

### File Operations

```python
from pathlib import Path

# Read file
try:
    content = self.core_api.read_file(Path("input.txt"))
except FileNotFoundError:
    self.core_api.log_error("File not found")

# Write file
self.core_api.write_file(Path("output.txt"), "content")
```

### Configuration Files

```python
# Get config path
config_path = self.core_api.get_config_path("my_plugin.toml")

# Read config
if config_path.exists():
    import toml
    config = toml.load(config_path)
```

### Shared Data (Inter-Plugin Communication)

```python
# Store data for other plugins
self.core_api.set_shared_data("user_preferences", preferences)

# Read data from other plugins
preferences = self.core_api.get_shared_data(
    "user_preferences",
    default={"theme": "dark"}
)

# Clear data
self.core_api.clear_shared_data("user_preferences")
```

### Rich Console (Advanced Formatting)

```python
from rich.table import Table
from rich.panel import Panel

# Create a table
table = Table(title="Results")
table.add_column("Name", style="cyan")
table.add_column("Value", style="magenta")
table.add_row("Item 1", "100")
self.core_api.console.print(table)

# Create a panel
panel = Panel("Important message", title="Alert", border_style="red")
self.core_api.console.print(panel)

# Rich formatting
self.core_api.console.print("[bold blue]Bold blue text[/bold blue]")
```

### ZIP File Operations

YAFT provides comprehensive ZIP file handling for forensic analysis. All ZIP operations are managed by the Core API.

#### Loading and Basic Operations

```python
from pathlib import Path

def execute(self, *args, **kwargs) -> Any:
    # Check if ZIP is loaded
    current_zip = self.core_api.get_current_zip()
    if not current_zip:
        self.core_api.print_error("No ZIP file loaded")
        return None

    # List all files in ZIP
    files = self.core_api.list_zip_contents()
    # Returns: List[str] of all file paths in ZIP

    # Display formatted table of ZIP contents
    self.core_api.display_zip_contents()

    # Get ZIP file statistics
    stats = self.core_api.get_zip_statistics()
    # Returns: dict with 'total_files', 'total_size', 'compression_ratio'
```

#### Reading Files from ZIP

```python
# Read file as bytes
content = self.core_api.read_zip_file("path/to/file.bin")
# Returns: bytes

# Read file as text
text = self.core_api.read_zip_file_text("path/to/file.txt")
# Returns: str (UTF-8 decoded)

# Check if file exists in ZIP
if self.core_api.file_exists_in_zip("path/to/file"):
    data = self.core_api.read_zip_file("path/to/file")
```

#### Extracting Files from ZIP

```python
from pathlib import Path

# Extract single file
output_dir = Path("extracted_files")
self.core_api.extract_zip_file("file.txt", output_dir)
# Extracts to: output_dir/file.txt

# Extract all files
self.core_api.extract_all_zip(output_dir)
# Extracts all files maintaining directory structure
```

#### Searching ZIP Files

```python
# Find files with wildcard patterns
db_files = self.core_api.find_files_in_zip("*.db")
# Returns: List[str] of all .db files

plist_files = self.core_api.find_files_in_zip("*.plist")
# Returns: List[str] of all .plist files

# Complex pattern matching
call_logs = self.core_api.find_files_in_zip("**/CallHistory.storedata")
# Returns: List[str] matching pattern (supports ** for recursive search)

# Find specific database
tcc_db = self.core_api.find_files_in_zip("**/TCC/TCC.db")
if tcc_db:
    rows = self.core_api.query_sqlite_from_zip(tcc_db[0], "SELECT * FROM access")
```

**Supported Patterns:**
- `*.ext` - All files with extension
- `**/filename` - Recursive search for filename
- `prefix*` - Files starting with prefix
- `*suffix` - Files ending with suffix
- `**/*.ext` - Recursive search for all files with extension

### Forensic ZIP Format Detection

YAFT automatically detects the extraction format from forensic tools (Cellebrite, GrayKey) and handles path prefixes.

```python
def execute(self, *args, **kwargs) -> Any:
    # Detect ZIP format
    extraction_type, zip_prefix = self.core_api.detect_zip_format()
    # Returns: ("cellebrite_ios", "filesystem1/") or ("graykey_android", "") etc.

    self.core_api.print_info(f"Detected format: {extraction_type}")
    self.core_api.print_info(f"Path prefix: {zip_prefix or 'none'}")

    # Normalize paths for ZIP access
    normalized_path = self.core_api.normalize_zip_path(
        "data/data/com.example.app/databases/app.db",
        zip_prefix
    )
    # Cellebrite Android: "Dump/data/data/com.example.app/databases/app.db"
    # GrayKey Android: "data/data/com.example.app/databases/app.db"

    # Read file with normalized path
    content = self.core_api.read_zip_file(normalized_path)
```

**Supported Formats:**

| Format Type | OS | Tool | Root Folders | Path Prefix |
|-------------|-----|------|--------------|-------------|
| `cellebrite_ios` | iOS | Cellebrite | `filesystem1/` or `filesystem/` | `filesystem1/` or `filesystem/` |
| `cellebrite_android` | Android | Cellebrite | `Dump/` and `extra/` | `Dump/` |
| `cellebrite_android` | Android | Cellebrite (legacy) | `fs/` | `fs/` |
| `graykey_ios` | iOS | GrayKey | `private/`, `System/`, `Library/`, etc. | (no prefix) |
| `graykey_android` | Android | GrayKey | `apex/`, `data/`, `system/`, `cache/`, etc. | (no prefix) |
| `unknown` | Any | Unknown | Various | (no prefix) |

### OS Detection

```python
# Detect operating system from ZIP structure
os_type = self.core_api.detect_os_from_zip()
# Returns: "ios", "android", or "unknown"

if os_type == "ios":
    # iOS-specific processing
    plist_data = self.core_api.read_plist_from_zip("System/Library/CoreServices/SystemVersion.plist")
elif os_type == "android":
    # Android-specific processing
    build_prop = self.core_api.read_zip_file_text("system/build.prop")
```

### Plist Parsing (iOS Forensics)

```python
# Parse plist from ZIP
data = self.core_api.read_plist_from_zip("path/to/file.plist")
# Returns: dict or list (parsed plist content)

# Example: iOS system version
version_data = self.core_api.read_plist_from_zip(
    "System/Library/CoreServices/SystemVersion.plist"
)
product_version = version_data.get("ProductVersion")

# Or parse plist from bytes
raw_content = self.core_api.read_zip_file("file.plist")
data = self.core_api.parse_plist(raw_content)
```

### XML Parsing (Android Forensics)

```python
# Parse XML from ZIP
root = self.core_api.read_xml_from_zip("path/to/file.xml")
# Returns: xml.etree.ElementTree.Element (root element)

# Example: Android packages.xml
packages_root = self.core_api.read_xml_from_zip("data/system/packages.xml")
for package in packages_root.findall(".//package"):
    name = package.get("name")
    code_path = package.get("codePath")

# Or parse XML from bytes/string
content = self.core_api.read_zip_file("file.xml")
root = self.core_api.parse_xml(content)
```

### SQLite Database Querying

```python
# Query database from ZIP (returns list of tuples)
rows = self.core_api.query_sqlite_from_zip(
    "path/to/database.db",
    "SELECT name, value FROM settings WHERE id = ?",
    params=(123,)
)

for row in rows:
    name, value = row
    print(f"{name}: {value}")

# Query with fallback for schema differences
rows = self.core_api.query_sqlite_from_zip(
    "TCC.db",
    "SELECT service, client, auth_value, last_modified FROM access",
    fallback_query="SELECT service, client, auth_value, NULL FROM access"
)

# Query and get results as dictionaries
dicts = self.core_api.query_sqlite_from_zip_dict(
    "database.db",
    "SELECT * FROM apps WHERE bundle_id LIKE ?",
    params=("com.apple.%",)
)

for row in dicts:
    # Access by column name
    bundle_id = row["bundle_id"]
    app_name = row["app_name"]
```

**Benefits:**
- Automatic temporary file management (created and cleaned up automatically)
- Support for fallback queries (useful for iOS/Android version differences)
- No need to import `sqlite3`, `tempfile`, or manage temp directories
- Consistent error handling

### BLOB Field Handling

The Core API provides comprehensive support for extracting and handling BLOB (Binary Large Object) fields from SQLite databases. This is essential for forensic analysis when dealing with images, attachments, binary plists, and other binary data stored in mobile app databases.

#### Common Forensic Use Cases

- **Images/Avatars**: Profile pictures, contact photos (WhatsApp, Skype, Contacts)
- **Attachments**: Message attachments, media files (WhatsApp, Signal, messaging apps)
- **Binary Plists**: iOS app preferences, settings stored as binary property lists
- **Thumbnails**: Photo thumbnails in gallery databases
- **Cached Data**: Binary cached data from apps and browsers

#### BLOB Type Detection

```python
# Detect BLOB type based on magic bytes
blob_data = self.core_api.read_zip_file("some_file.blob")
blob_type = self.core_api.detect_blob_type(blob_data)
# Returns: 'jpeg', 'png', 'gif', 'bmp', 'ico', 'tiff', 'plist', or 'unknown'

# Supported types: JPEG, PNG, GIF, BMP, ICO, TIFF, Binary Plist
```

#### Extracting BLOBs from SQLite Databases

```python
# Extract single BLOB from database
avatar = self.core_api.extract_blob_from_zip(
    "data/data/com.android.providers.contacts/databases/contacts2.db",
    "SELECT photo FROM contacts WHERE _id = ?",
    params=(123,)
)
# Returns: bytes or None

# Extract multiple BLOBs (batch extraction)
photos = self.core_api.extract_blobs_from_zip(
    "contacts2.db",
    "SELECT photo FROM contacts WHERE photo IS NOT NULL"
)
# Returns: list[bytes] (NULLs automatically excluded)

# Extract iOS Photo thumbnails
thumbnail = self.core_api.extract_blob_from_zip(
    "filesystem1/private/var/mobile/Media/PhotoData/Photos.sqlite",
    "SELECT thumbnailImage FROM ZGENERICASSET WHERE ZUUID = ?",
    params=("ABC123-DEF456",)
)
```

#### Saving BLOBs to Files

```python
# Save BLOB with automatic extension detection
blob = self.core_api.extract_blob_from_zip(
    "db.db",
    "SELECT photo FROM users WHERE id=1"
)

if blob:
    # Auto-detect type and correct file extension
    saved_path = self.core_api.save_blob_as_file(
        blob,
        self.core_api.get_case_output_dir("avatars") / "user_avatar.dat",
        auto_extension=True  # Automatically detects type and corrects extension
    )
    # If blob is JPEG: saved as user_avatar.jpg
    # If blob is PNG: saved as user_avatar.png

# Save without extension modification
saved_path = self.core_api.save_blob_as_file(
    blob,
    output_path,
    auto_extension=False
)

# Batch extraction and save
photos = self.core_api.extract_blobs_from_zip(
    "photos.db",
    "SELECT image FROM gallery"
)

output_dir = self.core_api.get_case_output_dir("extracted_photos")
for i, photo in enumerate(photos):
    self.core_api.save_blob_as_file(
        photo,
        output_dir / f"photo_{i}.dat",
        auto_extension=True
    )
```

#### Parsing Binary Plists from BLOBs

Binary plists are commonly stored in iOS database BLOB fields:

```python
# Extract and parse binary plist BLOB
rows = self.core_api.query_sqlite_from_zip(
    "filesystem1/Library/Preferences/com.apple.Preferences.db",
    "SELECT value FROM preferences WHERE key = ?",
    params=("app_settings",)
)

if rows and rows[0][0]:
    plist_data = self.core_api.parse_blob_as_plist(rows[0][0])
    # Returns: dict or list with parsed plist data
    app_version = plist_data["app_version"]
    settings = plist_data["settings"]

# Or use extract_blob_from_zip + parse_blob_as_plist
plist_blob = self.core_api.extract_blob_from_zip(
    "prefs.db",
    "SELECT data FROM preferences WHERE key = 'config'"
)

if plist_blob:
    config = self.core_api.parse_blob_as_plist(plist_blob)
```

#### Complete BLOB Workflow Example

```python
def execute(self, *args, **kwargs):
    # Detect ZIP format
    extraction_type, prefix = self.core_api.detect_zip_format()

    # Find database
    db_path = self.core_api.normalize_zip_path(
        "data/data/com.whatsapp/databases/wa.db",
        prefix
    )

    # Extract all contact avatars
    avatars = self.core_api.extract_blobs_from_zip(
        db_path,
        "SELECT jid, photo FROM wa_contacts WHERE photo IS NOT NULL"
    )

    # Save avatars with automatic type detection
    output_dir = self.core_api.get_case_output_dir("whatsapp_avatars")
    for i, photo_blob in enumerate(avatars):
        # Detect type
        blob_type = self.core_api.detect_blob_type(photo_blob)

        # Save with proper extension
        filename = f"contact_{i}"
        saved_path = self.core_api.save_blob_as_file(
            photo_blob,
            output_dir / f"{filename}.dat",
            auto_extension=True
        )

        self.core_api.print_success(f"Extracted {blob_type} avatar: {saved_path.name}")
```

**Benefits:**
- Automatic BLOB type detection based on magic bytes
- Support for both regular SQLite and encrypted databases
- Automatic file extension correction when saving
- Binary plist parsing for iOS forensics
- Batch extraction capabilities
- NULL value filtering
- No need for manual file type inspection

### Base64 Encoding/Decoding

The Core API provides comprehensive base64 encoding and decoding functionality for handling binary data in text-safe formats. This is useful for embedding binary data (images, BLOBs, files) in JSON exports, reports, or transmitting over text-based protocols.

#### Common Forensic Use Cases

- **Embedding Images in JSON**: Include photos, avatars, or thumbnails in JSON exports
- **Binary Data Storage**: Store binary artifacts in text-based formats
- **Data Transmission**: Safely transmit binary evidence over text protocols
- **Report Attachments**: Embed small binary files directly in reports

#### Basic Encoding/Decoding

```python
# Encode bytes to base64 string
data = b"Hello, World!"
encoded = self.core_api.base64_encode(data)
# Returns: "SGVsbG8sIFdvcmxkIQ=="

# Decode base64 string to bytes
decoded = self.core_api.base64_decode("SGVsbG8sIFdvcmxkIQ==")
# Returns: b"Hello, World!"
```

#### File Encoding

```python
# Encode file from ZIP archive
encoded_image = self.core_api.base64_encode_file("path/to/avatar.png")

# Encode local file
encoded_doc = self.core_api.base64_encode_file(Path("evidence/document.pdf"))

# Encode BLOB from database and store as base64
blob = self.core_api.extract_blob_from_zip(
    "contacts.db",
    "SELECT photo FROM contacts WHERE id = ?",
    params=(123,)
)

if blob:
    encoded_photo = self.core_api.base64_encode(blob)
    # Store in JSON or text report
```

#### File Decoding

```python
# Decode base64 string and save to file
encoded_data = "SGVsbG8sIFdvcmxkIQ=="
output_path = self.core_api.base64_decode_to_file(
    encoded_data,
    self.core_api.get_case_output_dir("decoded") / "file.dat"
)
# Saves decoded file and returns path
```

#### Complete Base64 Workflow Example

```python
def execute(self, *args, **kwargs):
    # Extract contact photos from database
    photos = self.core_api.extract_blobs_from_zip(
        "data/data/com.whatsapp/databases/wa.db",
        "SELECT jid, photo FROM wa_contacts WHERE photo IS NOT NULL"
    )

    # Prepare data for JSON export with base64-encoded images
    contacts_data = []
    for jid, photo in photos:
        contacts_data.append({
            "jid": jid,
            "photo_base64": self.core_api.base64_encode(photo),
            "photo_type": self.core_api.detect_blob_type(photo)
        })

    # Export to JSON with embedded base64 images
    output_dir = self.core_api.get_case_output_dir("whatsapp_contacts")

    import json
    json_path = output_dir / "contacts_with_photos.json"
    self.core_api.write_file(
        json_path,
        json.dumps({"contacts": contacts_data}, indent=2)
    )

    # Later: decode and save images from JSON
    for contact in contacts_data:
        photo_path = output_dir / f"{contact['jid']}.{contact['photo_type']}"
        self.core_api.base64_decode_to_file(
            contact["photo_base64"],
            photo_path
        )
```

#### Error Handling

```python
try:
    decoded = self.core_api.base64_decode(encoded_string)
except ValueError as e:
    self.core_api.print_error(f"Invalid base64 data: {e}")
```

**Benefits:**
- Text-safe representation of binary data
- JSON-compatible format for binary artifacts
- Automatic file I/O handling
- Works with both ZIP files and local files
- Consistent error handling

### CSV Data Export

The Core API provides CSV export functionality similar to JSON export, allowing plugins to export structured data in CSV format for analysis in spreadsheet applications like Excel, LibreOffice Calc, or forensic analysis tools.

#### Common Forensic Use Cases

- **Call Logs**: Export call history for timeline analysis
- **Contact Lists**: Export contact information in tabular format
- **Message Logs**: Export chat messages for review
- **App Permissions**: Export app permission matrices
- **Timeline Analysis**: Export timestamped events for correlation

#### Basic CSV Export

```python
# Export list of dictionaries to CSV
data = [
    {"name": "John Doe", "phone": "+1234567890", "email": "john@example.com"},
    {"name": "Jane Smith", "phone": "+0987654321", "email": "jane@example.com"},
]

output_path = self.core_api.get_case_output_dir("contacts") / "contacts.csv"

self.core_api.export_plugin_data_to_csv(
    output_path,
    plugin_name=self.metadata.name,
    plugin_version=self.metadata.version,
    data=data,
    extraction_type="cellebrite_ios",
    include_metadata=True  # Include metadata header rows (default)
)
```

#### CSV Format

With `include_metadata=True` (default), the CSV includes metadata rows at the top:

```csv
Plugin Name,MyPlugin
Plugin Version,1.0.0
Extraction Source,cellebrite_ios
Processing Timestamp,2025-01-17T14:30:00Z

name,phone,email
John Doe,+1234567890,john@example.com
Jane Smith,+0987654321,jane@example.com
```

#### Export Without Metadata

```python
# Export data-only CSV (no metadata header)
self.core_api.export_plugin_data_to_csv(
    output_path,
    plugin_name=self.metadata.name,
    plugin_version=self.metadata.version,
    data=data,
    extraction_type="cellebrite_ios",
    include_metadata=False  # Data only
)
```

#### Handling Complex Data Types

The CSV export automatically handles complex data types:

```python
data = [
    {
        "name": "John",
        "phones": ["+1234567890", "+0987654321"],  # List → JSON string
        "metadata": {"last_seen": "2025-01-17"},    # Dict → JSON string
        "active": True,                              # Boolean → "True"
        "score": 42,                                 # Integer → "42"
        "missing": None,                             # None → ""
    }
]

# Lists and dicts are automatically converted to JSON strings
# CSV output:
# name,phones,metadata,active,score,missing
# John,"['+1234567890', '+0987654321']","{""last_seen"": ""2025-01-17""}",True,42,
```

#### Complete CSV Workflow Example

```python
def execute(self, *args, **kwargs):
    # Extract call logs from database
    rows = self.core_api.query_sqlite_from_zip_dict(
        "Library/CallHistory/CallHistory.storedata",
        "SELECT ZADDRESS as number, ZDATE as timestamp, ZDURATION as duration, "
        "ZCALLTYPE as call_type FROM ZCALLRECORD ORDER BY ZDATE DESC"
    )

    # Process and format data
    from datetime import datetime, timedelta

    call_logs = []
    for row in rows:
        # Convert Core Data timestamp (seconds since 2001-01-01)
        timestamp = datetime(2001, 1, 1) + timedelta(seconds=row["timestamp"])

        call_logs.append({
            "Number": row["number"],
            "Date": timestamp.strftime("%Y-%m-%d %H:%M:%S"),
            "Duration (seconds)": int(row["duration"]),
            "Type": {1: "Outgoing", 2: "Incoming", 3: "Missed"}.get(
                row["call_type"], "Unknown"
            ),
        })

    # Export to CSV
    output_dir = self.core_api.get_case_output_dir("call_logs")
    csv_path = output_dir / "call_history.csv"

    self.core_api.export_plugin_data_to_csv(
        csv_path,
        plugin_name=self.metadata.name,
        plugin_version=self.metadata.version,
        data=call_logs,
        extraction_type=self.extraction_type,
    )

    self.core_api.print_success(f"Exported {len(call_logs)} call records to CSV")

    return {
        "success": True,
        "csv_path": str(csv_path),
        "record_count": len(call_logs),
    }
```

#### CSV vs JSON Export Comparison

| Feature | JSON Export | CSV Export |
|---------|-------------|------------|
| **Format** | Hierarchical, nested | Flat, tabular |
| **Best For** | Complex nested data | Simple tabular data |
| **Readability** | Moderate | High (spreadsheets) |
| **Tool Support** | APIs, scripts | Excel, Calc, analysis tools |
| **Data Types** | Native types | Strings (complex → JSON) |

#### Error Handling

```python
# Empty data handling
if not data:
    self.core_api.print_warning("No data to export")
    return

try:
    self.core_api.export_plugin_data_to_csv(output_path, ...)
except Exception as e:
    self.core_api.print_error(f"CSV export failed: {e}")
```

**Benefits:**
- Compatible with Excel, LibreOffice Calc, and forensic tools
- Automatic handling of complex data types (lists, dicts → JSON)
- Optional metadata header for audit trail
- Comprehensive column detection (union of all keys)
- UTF-8 encoding for international character support
- Consistent format with JSON export

### Case Identifier Management

YAFT provides built-in support for forensic case identifier management. The CLI automatically prompts for case identifiers before plugin execution.

#### Validation Methods

```python
# Validate examiner ID (alphanumeric with underscores/hyphens, 2-50 chars)
if self.core_api.validate_examiner_id("john_doe"):
    self.core_api.print_success("Valid examiner ID")

# Validate case ID (any alphanumeric string)
if self.core_api.validate_case_id("CASE2024-01"):
    self.core_api.print_success("Valid case ID")

# Validate evidence ID (any alphanumeric string)
if self.core_api.validate_evidence_id("EV123456-1"):
    self.core_api.print_success("Valid evidence ID")
```

#### Setting and Getting Case Identifiers

```python
# Set case identifiers programmatically (rarely needed - CLI handles this)
self.core_api.set_case_identifiers("john_doe", "CASE2024-01", "EV123456-1")

# Get current case identifiers
examiner, case, evidence = self.core_api.get_case_identifiers()
# Returns: tuple of (str | None, str | None, str | None)

if case and evidence:
    self.core_api.print_info(f"Working on case {case}, evidence {evidence}")
```

#### Case-Based Output Directories

```python
# Get case-based output directory (recommended for all file outputs)
output_dir = self.core_api.get_case_output_dir("ios_extractions")
# With case IDs: yaft_output/CASE2024-01/EV123456-1/ios_extractions
# Without: yaft_output/ios_extractions

output_dir.mkdir(parents=True, exist_ok=True)

# Write output files to case-organized directory
json_path = output_dir / "data.json"
self.core_api.write_file(json_path, json.dumps(data, indent=2))
```

**Best Practice:** Always use `get_case_output_dir()` for plugin outputs to ensure proper organization.

### Report Generation

All plugins should use the unified report generation system for consistent markdown reports.

```python
# Generate a comprehensive report
sections = [
    {
        "heading": "Executive Summary",
        "content": "Brief overview of findings...",
        "level": 2,  # Optional, default 2
    },
    {
        "heading": "Key Findings",
        "content": [
            "Finding 1: Lorem ipsum",
            "Finding 2: Dolor sit amet",
            "Finding 3: Consectetur adipiscing",
        ],
        "style": "list",  # Options: text, list, table, code
    },
    {
        "heading": "Statistics",
        "content": {
            "Total Files Analyzed": 1543,
            "Suspicious Items": 12,
            "Clean Items": 1531,
            "Analysis Duration": "5.2 seconds",
        },
        "style": "table",
    },
    {
        "heading": "Raw Data Sample",
        "content": '{"example": "json data", "count": 42}',
        "style": "code",
    },
]

metadata = {
    "Analysis Type": "Forensic ZIP Analysis",
    "OS Type": "iOS",
    "Tool Used": "Cellebrite",
}

report_path = self.core_api.generate_report(
    plugin_name=self.metadata.name,
    title="iOS Device Analysis Report",
    sections=sections,
    metadata=metadata,
)
# Returns: Path to generated markdown report

self.core_api.print_success(f"Report generated: {report_path}")
```

**Report Features:**
- Automatic metadata (plugin name, timestamp, source ZIP, case identifiers)
- Consistent formatting across all plugins
- Multiple content styles (text, list, table, code)
- Timestamped filenames (won't overwrite)
- Standard location: `yaft_output/<case_id>/<evidence_id>/reports/PluginName_YYYYMMDD_HHMMSS.md`

#### PDF Export

```python
# Enable automatic PDF generation for all reports
self.core_api.enable_pdf_export(True)

# Generate report (PDF created automatically if enabled)
report_path = self.core_api.generate_report(
    plugin_name=self.metadata.name,
    title="Analysis Report",
    sections=sections,
)
# Creates both: report.md and report.pdf

# Manually convert a markdown file to PDF
pdf_path = self.core_api.convert_markdown_to_pdf(markdown_path)

# Batch export all generated reports to PDF
pdf_paths = self.core_api.export_all_reports_to_pdf()
```

**PDF Features:**
- Professional styling (blue color scheme, proper typography)
- Full markdown support (tables, code blocks, lists, headings)
- A4 page format with margins
- Graceful degradation if PDF packages aren't installed

### Plugin Update System

Access the plugin update system programmatically to check for and download plugin updates.

```python
# Get plugin updater instance
updater = self.core_api.get_plugin_updater(
    repo="RedRockerSE/yaft2",
    branch="main",
    plugins_dir=None,  # Uses default plugins/ directory
)

# Check for updates
check_result = updater.check_for_updates(force=False)

if check_result.updates_available:
    self.core_api.print_info(f"New plugins: {check_result.new_plugins}")
    self.core_api.print_info(f"Updated plugins: {check_result.updated_plugins}")

    # Download updates
    download_result = updater.download_plugins(
        plugin_list=check_result.new_plugins + check_result.updated_plugins,
        verify=True,
        backup=True,
    )

    if download_result.success:
        self.core_api.print_success(f"Downloaded: {download_result.downloaded}")
    else:
        self.core_api.print_error(f"Failed: {download_result.failed}")

# List available plugins from manifest
available = updater.list_available_plugins()
for plugin in available:
    print(f"{plugin['name']} v{plugin['version']} - {plugin['description']}")

# Update all plugins at once
result = updater.update_all_plugins(force=False, auto_download=True)
```

### Plugin Profiles

Load and use plugin profiles to run multiple plugins together.

```python
from pathlib import Path

# Load a plugin profile
profile = self.core_api.load_plugin_profile(
    Path("profiles/ios_full_analysis.toml")
)

# Access profile properties
self.core_api.print_info(f"Profile: {profile.name}")
self.core_api.print_info(f"Description: {profile.description}")

# Get list of plugin class names
for plugin_name in profile.plugins:
    self.core_api.print_info(f"  - {plugin_name}")
```

**Profile Structure:**
```toml
[profile]
name = "Profile Name"
description = "Optional description"

plugins = [
    "PluginClassName1",
    "PluginClassName2",
]
```

## Best Practices

### 1. Error Handling

```python
def execute(self, *args: Any, **kwargs: Any) -> Any:
    try:
        result = self._risky_operation()
        return result
    except ValueError as e:
        self.core_api.log_error(f"Invalid value: {e}")
        return None
    except Exception as e:
        self.core_api.log_error(f"Unexpected error: {e}")
        self.status = PluginStatus.ERROR
        raise
```

### 2. Type Hints

```python
from typing import Any, Optional
from pathlib import Path

def execute(self, *args: Any, **kwargs: Any) -> dict[str, Any]:
    filepath: Optional[Path] = None

    if args:
        filepath = Path(args[0])

    result: dict[str, Any] = {
        "success": True,
        "filepath": str(filepath) if filepath else None,
    }

    return result
```

### 3. Docstrings

```python
class MyPlugin(PluginBase):
    """
    A plugin that processes data files.

    This plugin reads data files, validates their format,
    and generates statistical summaries.

    Example usage:
        yaft run MyPlugin input.csv
    """

    def execute(self, *args: Any, **kwargs: Any) -> dict[str, Any]:
        """
        Process a data file and return statistics.

        Args:
            *args: First argument should be the file path
            **kwargs: Optional 'format' key for file format

        Returns:
            Dictionary containing processing statistics

        Raises:
            FileNotFoundError: If input file doesn't exist
            ValueError: If file format is invalid
        """
        pass
```

### 4. Resource Management

```python
from pathlib import Path

def initialize(self) -> None:
    """Initialize with resource management."""
    self._temp_dir = Path("temp")
    self._temp_dir.mkdir(exist_ok=True)

def cleanup(self) -> None:
    """Clean up temporary resources."""
    import shutil
    if self._temp_dir.exists():
        shutil.rmtree(self._temp_dir)
```

### 5. Configuration

```python
from pathlib import Path
import toml

def initialize(self) -> None:
    """Load configuration."""
    config_path = self.core_api.get_config_path("my_plugin.toml")

    # Create default config if doesn't exist
    if not config_path.exists():
        default_config = {
            "max_retries": 3,
            "timeout": 30,
            "enabled_features": ["feature1", "feature2"],
        }
        self.core_api.write_file(
            config_path,
            toml.dumps(default_config)
        )

    # Load config
    content = self.core_api.read_file(config_path)
    self.config = toml.loads(content)
```

## Advanced Topics

### Progress Bars

```python
from rich.progress import track

def execute(self, *args: Any, **kwargs: Any) -> Any:
    items = range(100)

    for item in track(items, description="Processing..."):
        process_item(item)
```

### Live Display

```python
from rich.live import Live
from rich.table import Table
import time

def execute(self, *args: Any, **kwargs: Any) -> Any:
    with Live(auto_refresh=False) as live:
        for i in range(10):
            table = Table(title=f"Progress: {i}/10")
            table.add_column("Step")
            table.add_column("Status")
            table.add_row(f"Step {i}", "Complete")

            live.update(table, refresh=True)
            time.sleep(0.5)
```

### Async Execution

```python
import asyncio

def execute(self, *args: Any, **kwargs: Any) -> Any:
    """Execute async operations."""
    return asyncio.run(self._async_execute(*args, **kwargs))

async def _async_execute(self, *args: Any, **kwargs: Any) -> Any:
    """Async implementation."""
    result = await self._fetch_data()
    return result
```

### Plugin State Persistence

```python
import json
from pathlib import Path

def cleanup(self) -> None:
    """Save plugin state."""
    state = {
        "counter": self._counter,
        "last_run": datetime.now().isoformat(),
        "cache": self._cache,
    }

    state_path = self.core_api.get_config_path("my_plugin_state.json")
    self.core_api.write_file(
        state_path,
        json.dumps(state, indent=2)
    )

def initialize(self) -> None:
    """Restore plugin state."""
    state_path = self.core_api.get_config_path("my_plugin_state.json")

    if state_path.exists():
        content = self.core_api.read_file(state_path)
        state = json.loads(content)
        self._counter = state.get("counter", 0)
        self._cache = state.get("cache", {})
```

## Testing Plugins

### Unit Tests

```python
# tests/test_my_plugin.py
import pytest
from pathlib import Path
from plugins.my_plugin import MyPlugin
from yaft.core.api import CoreAPI


def test_plugin_initialization(core_api):
    """Test plugin initializes correctly."""
    plugin = MyPlugin(core_api)
    plugin.initialize()

    assert plugin.metadata.name == "MyPlugin"
    assert plugin.status.value == "initialized"


def test_plugin_execution(core_api):
    """Test plugin executes correctly."""
    plugin = MyPlugin(core_api)
    plugin.initialize()

    result = plugin.execute("test_arg")

    assert result is not None
    assert isinstance(result, dict)


def test_plugin_cleanup(core_api):
    """Test plugin cleans up resources."""
    plugin = MyPlugin(core_api)
    plugin.initialize()
    plugin.cleanup()

    # Verify resources are released
    assert not hasattr(plugin, "_open_file")
```

### Integration Tests

```python
def test_plugin_integration(core_api, tmp_path):
    """Test plugin with actual files."""
    # Setup
    test_file = tmp_path / "test.txt"
    test_file.write_text("test content")

    # Execute
    plugin = MyPlugin(core_api)
    plugin.initialize()
    result = plugin.execute(str(test_file))

    # Verify
    assert result["success"] is True
    plugin.cleanup()
```

### Manual Testing

```bash
# Test plugin discovery
python -m yaft.cli list-plugins --all

# Test plugin loading
python -m yaft.cli load MyPlugin

# Test plugin execution
python -m yaft.cli run MyPlugin arg1 arg2

# Test plugin info
python -m yaft.cli info MyPlugin
```

## Common Patterns

### Command Pattern

```python
class CommandPlugin(PluginBase):
    """Plugin that executes commands."""

    def execute(self, *args: Any, **kwargs: Any) -> Any:
        command = args[0] if args else "help"

        commands = {
            "help": self._show_help,
            "status": self._show_status,
            "process": self._process_data,
        }

        if command in commands:
            return commands[command](*args[1:], **kwargs)
        else:
            self.core_api.print_error(f"Unknown command: {command}")
            return None
```

### Menu Pattern

```python
def execute(self, *args: Any, **kwargs: Any) -> Any:
    """Display interactive menu."""
    while True:
        self.core_api.console.print("\n[bold]Menu:[/bold]")
        self.core_api.console.print("1. Option 1")
        self.core_api.console.print("2. Option 2")
        self.core_api.console.print("0. Exit")

        choice = self.core_api.get_user_input("Choose option")

        if choice == "0":
            break
        elif choice == "1":
            self._option1()
        elif choice == "2":
            self._option2()
```

## Troubleshooting

### Plugin Not Discovered

- File must be in `plugins/` directory
- File must not start with underscore
- Class must inherit from `PluginBase`
- Check for syntax errors

### Import Errors

- Ensure all imports are available
- Check requirements.txt for dependencies
- Verify imports work in Python environment

### Plugin Fails to Load

- Check `initialize()` method for exceptions
- Review logs for error messages
- Verify dependencies are loaded
- Check configuration files exist

## Resources

- Main README: `../README.md`
- Example plugins: `../plugins/`
- Core API source: `../src/yaft/core/api.py`
- Plugin base source: `../src/yaft/core/plugin_base.py`

## Getting Help

- Review example plugins
- Check test files for patterns
- Read the main documentation
- Open an issue on GitHub
