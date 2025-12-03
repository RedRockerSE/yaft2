# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**YAFT (Yet Another Forensic Tool)** is a Python-based forensic analysis tool designed for processing and analyzing ZIP archives through a plugin architecture. The tool provides built-in ZIP file handling capabilities that are exposed to plugins through the Core API, enabling forensic analysts to create custom analysis plugins without worrying about low-level ZIP operations.

YaFT includes production-ready forensic analysis plugins for both iOS and Android devices, supporting extraction formats from Cellebrite and GrayKey tools.

## Technology Stack

- **Python Version**: 3.12+ (supports both 3.12 and 3.13)
- **Package Manager**: uv (Astral's ultra-fast Python package installer)
- **CLI Framework**: Typer (type-safe CLI framework)
- **Terminal Output**: Rich (color-coded, formatted output)
- **Validation**: Pydantic v2 (type-safe data validation)
- **Build System**: PyInstaller (Windows and Linux executables)
- **Testing**: pytest with coverage
- **Code Quality**: Ruff (linting and formatting)
- **PDF Generation**: Markdown + WeasyPrint (markdown to PDF conversion)

## Logging Configuration

YAFT provides flexible logging configuration through a TOML configuration file (`config/logging.toml`). The logging system supports multiple output modes (console, file, or both), configurable log levels, and optional log file rotation.

### Configuration File Location

The default logging configuration file is located at:
```
config/logging.toml
```

If the file doesn't exist, YAFT uses sensible defaults (INFO level, console output with Rich formatting).

### Configuration Options

```toml
[logging]
# Log level: DEBUG, INFO, WARNING, ERROR, CRITICAL
level = "INFO"

# Output mode: console, file, both
output = "console"

# Log file path (used when output is "file" or "both")
# Relative paths are relative to yaft_output directory
file_path = "logs/yaft.log"

# Log file rotation settings
max_bytes = 10485760  # 10 MB
backup_count = 5

# Format options
[logging.format]
include_timestamp = true
timestamp_format = "[%Y-%m-%d %H:%M:%S]"
include_level = true
include_name = false
rich_formatting = true     # Rich colored output (console only)
rich_tracebacks = true     # Full tracebacks with syntax highlighting
```

### Configuration Examples

**Console output only (default):**
```toml
[logging]
level = "INFO"
output = "console"
```

**File output only (for production/automation):**
```toml
[logging]
level = "DEBUG"
output = "file"
file_path = "logs/yaft.log"
```

**Both console and file (recommended for forensic analysis):**
```toml
[logging]
level = "INFO"
output = "both"
file_path = "logs/forensic_analysis.log"

[logging.format]
include_timestamp = true
rich_formatting = true
```

**Debug mode with detailed logging:**
```toml
[logging]
level = "DEBUG"
output = "both"
file_path = "logs/yaft_debug.log"

[logging.format]
include_timestamp = true
include_level = true
include_name = true
```

### Log Levels

- **DEBUG**: Detailed diagnostic information (plugin initialization, file operations, etc.)
- **INFO**: General informational messages (default - plugin execution, file processing)
- **WARNING**: Warning messages for potential issues
- **ERROR**: Error messages for serious problems
- **CRITICAL**: Critical errors that may cause program failure

### Output Organization

**Console output**: Displays logs in terminal with Rich formatting (colors, syntax highlighting)

**File output**:
- Logs are written to `yaft_output/logs/yaft.log` (by default)
- Supports automatic log rotation based on file size
- Backup files are numbered (e.g., `yaft.log.1`, `yaft.log.2`)
- Absolute paths can be used: `file_path = "/var/log/yaft/analysis.log"`

### Programmatic Access

Plugins and code can access logging through the Core API:

```python
# In plugin code
self.core_api.log_debug("Detailed diagnostic message")
self.core_api.log_info("General informational message")
self.core_api.log_warning("Warning about potential issue")
self.core_api.log_error("Error message")
```

### Best Practices

1. **Development**: Use `DEBUG` level with console output for immediate feedback
2. **Production**: Use `INFO` level with file output for audit trails
3. **Forensic Analysis**: Use `both` output mode to see progress while maintaining logs
4. **Long-running operations**: Enable file logging with rotation to prevent disk space issues
5. **Sensitive cases**: Store logs in case-specific directories using absolute paths

## Core Architecture

### Layered Architecture
```
CLI (Presentation) → Plugin Manager (Application) → Core API (Service) → Plugin Base (Domain)
```

### Key Components

1. **Plugin Base** (`src/yaft/core/plugin_base.py`)
   - Abstract base class for all plugins
   - Defines plugin interface: metadata, initialize(), execute(), cleanup()
   - Plugin lifecycle state management

2. **Core API** (`src/yaft/core/api.py`)
   - Service layer providing shared functionality
   - **ZIP file handling**: load, read, extract, analyze ZIP archives
   - **Case identifier management**: Forensic case identifiers (Examiner ID, Case ID, Evidence ID)
   - **Plist parsing**: parse plist files from ZIP archives (iOS forensics)
   - **SQLite querying**: execute SQL queries on databases from ZIP archives (iOS/Android forensics)
   - **XML parsing**: parse XML files from ZIP archives (Android forensics)
   - Logging, file I/O, user input, configuration management
   - Inter-plugin communication via shared data store

3. **Plugin Manager** (`src/yaft/core/plugin_manager.py`)
   - Dynamic plugin discovery using importlib
   - Plugin lifecycle management
   - Error isolation (failed plugins don't crash app)

4. **CLI** (`src/yaft/cli.py`)
   - Typer-based command-line interface
   - Commands: list-plugins, info, load, unload, run, reload
   - `run` command accepts `--zip` option for forensic analysis

## Case Identifier Management

YaFT includes built-in support for forensic case identifier management. The CLI automatically prompts for case identifiers when running plugins, and these are included in reports and used to organize output files.

### Case Identifier Formats

- **Examiner ID**: User/investigator identifier (alphanumeric with underscores/hyphens, 2-50 characters - e.g., `john_doe`, `examiner-123`)
- **Case ID**: Case number (any alphanumeric string - e.g., `CASE2024-01`, `Case123`, `MyCase`)
- **Evidence ID**: Evidence number (any alphanumeric string - e.g., `BG123456-1`, `Evidence1`, `Ev-001`)

### Core API Methods

```python
# Validation (returns True/False)
self.core_api.validate_examiner_id("john_doe")
self.core_api.validate_case_id("CASE2024-01")
self.core_api.validate_evidence_id("EV123456-1")

# Set case identifiers programmatically
self.core_api.set_case_identifiers("john_doe", "CASE2024-01", "EV123456-1")

# Get current case identifiers (returns tuple of strings or None values)
examiner, case, evidence = self.core_api.get_case_identifiers()

# Get case-based output directory (automatically uses case identifiers if set)
output_dir = self.core_api.get_case_output_dir("ios_extractions")
# Returns: yaft_output/CASE2024-01/BG123456-1/ios_extractions
# Or falls back to: yaft_output/ios_extractions (if identifiers not set)
```

### Output Organization

When case identifiers are set, all plugin outputs are organized in case-based directories:
```
yaft_output/
├── CASE2024-01/              # Case ID
│   └── EV123456-1/           # Evidence ID
│       ├── reports/          # Generated reports (includes case IDs in metadata)
│       ├── ios_extractions/  # Plugin-specific outputs
│       └── android_extractions/
```

### Plugin Integration

**Recommended approach for plugins:**
```python
def execute(self, *args, **kwargs):
    # Use get_case_output_dir() for all output paths
    output_dir = self.core_api.get_case_output_dir("my_plugin_outputs")
    output_dir.mkdir(parents=True, exist_ok=True)

    # Your plugin logic...

    # Reports automatically include case identifiers in metadata
    report_path = self.core_api.generate_report(
        plugin_name="MyPlugin",
        title="Analysis Report",
        sections=sections,
    )
```

**Note:** The CLI automatically prompts for case identifiers before plugin execution. Plugins don't need to prompt - just use `get_case_output_dir()` and `generate_report()` which handle case identifiers automatically.

## Data Format Support

The Core API exposes comprehensive data format parsing capabilities to plugins for forensic analysis:

### ZIP File Handling

```python
# In plugin execute() method:
current_zip = self.core_api.get_current_zip()  # Get current ZIP path
files = self.core_api.list_zip_contents()  # List all files
content = self.core_api.read_zip_file("file.txt")  # Read as bytes
text = self.core_api.read_zip_file_text("file.txt")  # Read as text
self.core_api.extract_zip_file("file.txt", output_dir)  # Extract single file
self.core_api.extract_all_zip(output_dir)  # Extract all files
self.core_api.display_zip_contents()  # Display formatted table
```

### ZIP File Search

The Core API provides powerful file search capabilities within ZIP archives using glob-style wildcard patterns:

```python
# Find specific file by exact name
files = self.core_api.find_files_in_zip("SystemVersion.plist")
# Returns: ["System/Library/CoreServices/SystemVersion.plist"]

# Find all files with specific extension
files = self.core_api.find_files_in_zip("*.db")
# Returns: All .db files in the entire ZIP archive

# Find files with wildcard name and extension
files = self.core_api.find_files_in_zip("file.*")
# Returns: ["file.txt", "file.db", "file.json", ...]

# Find files matching pattern in name
files = self.core_api.find_files_in_zip("*call*.db")
# Returns: ["calllog.db", "call_history.db", ...]

# Search within specific directory
files = self.core_api.find_files_in_zip("*.db", search_path="data/data/")
# Returns: Only .db files within data/data/ directory

# Case-sensitive search
files = self.core_api.find_files_in_zip("File.TXT", case_sensitive=True)
# Returns: Only exact case matches

# Limit number of results
files = self.core_api.find_files_in_zip("*.log", max_results=10)
# Returns: First 10 matching files

# Complex path patterns
files = self.core_api.find_files_in_zip("*/databases/*.db")
# Returns: All .db files in any databases/ subdirectory

# Wildcard with question mark (single character)
files = self.core_api.find_files_in_zip("file?.txt")
# Returns: ["file1.txt", "fileA.txt", ...] (single char matches)
```

**Supported Pattern Syntax:**
- `*` - Matches zero or more characters
- `?` - Matches exactly one character
- `*.ext` - All files with extension `.ext`
- `name.*` - File with any extension
- `*pattern*` - Files containing pattern in name
- `path/*/file.ext` - Wildcards in path components

**Method Signature:**
```python
def find_files_in_zip(
    pattern: str,
    *,
    case_sensitive: bool = False,
    search_path: str | None = None,
    max_results: int | None = None
) -> list[str]
```

**Common Forensic Use Cases:**
```python
# Find iOS call history
files = self.core_api.find_files_in_zip("*CallHistory*")

# Find Android contact databases
files = self.core_api.find_files_in_zip("*contact*.db", search_path="data/data/")

# Find all plist files in iOS Preferences
files = self.core_api.find_files_in_zip(
    "*.plist",
    search_path="System/Library/Preferences/"
)

# Find app databases for specific package
files = self.core_api.find_files_in_zip(
    "*.db",
    search_path="data/data/com.example.app/"
)

# Find log files
files = self.core_api.find_files_in_zip("*.log")
files = self.core_api.find_files_in_zip("*log*.txt")
```

### Plist Parsing (iOS Forensics)

```python
# Parse plist from ZIP (returns dict or list)
data = self.core_api.read_plist_from_zip("path/to/file.plist")

# Or parse plist from bytes
raw_content = self.core_api.read_zip_file("file.plist")
data = self.core_api.parse_plist(raw_content)
```

### XML Parsing (Android Forensics)

```python
# Parse XML from ZIP (returns ElementTree root)
root = self.core_api.read_xml_from_zip("path/to/file.xml")

# Or parse XML from bytes/string
content = self.core_api.read_zip_file("file.xml")
root = self.core_api.parse_xml(content)

# Use standard ElementTree methods
for elem in root.findall('.//package'):
    name = elem.get('name')
```

### SQLite Querying

```python
# Query database from ZIP (returns list of tuples)
rows = self.core_api.query_sqlite_from_zip(
    "path/to/database.db",
    "SELECT name, value FROM settings WHERE id = ?",
    params=(123,)
)

# Query with fallback for schema differences (e.g., iOS/Android versions)
rows = self.core_api.query_sqlite_from_zip(
    "TCC.db",
    "SELECT service, client, auth_value, last_modified FROM access",
    fallback_query="SELECT service, client, auth_value, NULL FROM access"  # Older schema
)

# Query and get results as dictionaries with column names
dicts = self.core_api.query_sqlite_from_zip_dict(
    "database.db",
    "SELECT * FROM apps WHERE bundle_id LIKE ?",
    params=("com.apple.%",)
)
# Returns: [{"id": 1, "bundle_id": "com.apple.safari", ...}, ...]
```

### SQLCipher Encrypted Database Support

The Core API provides full support for querying and decrypting SQLCipher-encrypted databases, which are commonly used in mobile forensics (WhatsApp, Signal, iOS apps, Android apps).

**Installation:**

SQLCipher support is **optional** and requires the `sqlcipher3` package:

```bash
# Install SQLCipher support
uv pip install sqlcipher3
```

**Querying Encrypted Databases:**

```python
# Query encrypted database from ZIP (returns list of tuples)
rows = self.core_api.query_sqlcipher_from_zip(
    "data/data/com.whatsapp/databases/msgstore.db",
    "encryption_key_here",
    "SELECT key_remote_jid, data, timestamp FROM messages WHERE timestamp > ?",
    params=(1609459200000,)
)

# Query encrypted database with SQLCipher v3 compatibility (older databases)
rows = self.core_api.query_sqlcipher_from_zip(
    "private/var/mobile/Library/SMS/sms.db",
    "ios_backup_password",
    "SELECT * FROM message",
    cipher_version=3  # For older SQLCipher versions
)

# Query and get results as dictionaries
messages = self.core_api.query_sqlcipher_from_zip_dict(
    "data/data/com.whatsapp/databases/msgstore.db",
    "encryption_key",
    "SELECT key_remote_jid, data, timestamp FROM messages ORDER BY timestamp DESC LIMIT 100"
)
# Returns: [{"key_remote_jid": "+1234567890@s.whatsapp.net", "data": "Hello", ...}, ...]

# With fallback query for schema differences
rows = self.core_api.query_sqlcipher_from_zip(
    "encrypted.db",
    "key",
    "SELECT id, name, created_at FROM users",
    fallback_query="SELECT id, name, NULL FROM users"  # Older schema without created_at
)
```

**Decrypting to Plain SQLite:**

```python
# Decrypt encrypted database and save as plain SQLite file
decrypted_path = self.core_api.decrypt_sqlcipher_database(
    "data/data/com.whatsapp/databases/msgstore.db",
    "encryption_key",
    Path("yaft_output/decrypted/whatsapp_msgstore.db")
)
# Now you can use standard SQLite tools on the decrypted database

# Decrypt with SQLCipher v3 compatibility
decrypted_path = self.core_api.decrypt_sqlcipher_database(
    "encrypted_ios_app.db",
    "ios_key",
    Path("yaft_output/decrypted/app.db"),
    cipher_version=3
)
```

**Method Signatures:**

```python
def query_sqlcipher_from_zip(
    db_path: str,
    key: str,
    query: str,
    params: tuple = (),
    fallback_query: str | None = None,
    cipher_version: int | None = None,  # 1-4, for version compatibility
) -> list[tuple]

def query_sqlcipher_from_zip_dict(
    db_path: str,
    key: str,
    query: str,
    params: tuple = (),
    fallback_query: str | None = None,
    cipher_version: int | None = None,
) -> list[dict[str, Any]]

def decrypt_sqlcipher_database(
    db_path: str,
    key: str,
    output_path: Path,
    cipher_version: int | None = None,
) -> Path
```

**Common Forensic Use Cases:**

```python
# WhatsApp message extraction
messages = self.core_api.query_sqlcipher_from_zip_dict(
    "data/data/com.whatsapp/databases/msgstore.db",
    whatsapp_key,
    "SELECT key_remote_jid, data, timestamp FROM messages ORDER BY timestamp"
)

# Signal message extraction
signal_msgs = self.core_api.query_sqlcipher_from_zip_dict(
    "data/data/org.thoughtcrime.securesms/databases/signal.db",
    signal_key,
    "SELECT address, body, date_sent FROM sms ORDER BY date_sent DESC"
)

# iOS app encrypted database
app_data = self.core_api.query_sqlcipher_from_zip_dict(
    "private/var/mobile/Containers/Data/Application/ABC123/Documents/data.db",
    app_key,
    "SELECT * FROM user_activity WHERE timestamp > ?",
    params=(631152000.0,),
    cipher_version=3
)

# Decrypt for external analysis tools
decrypted = self.core_api.decrypt_sqlcipher_database(
    "data/data/com.app/databases/encrypted.db",
    encryption_key,
    self.core_api.get_case_output_dir("decrypted") / "app.db"
)
```

**Error Handling:**

```python
try:
    rows = self.core_api.query_sqlcipher_from_zip(db_path, key, query)
except ImportError:
    # sqlcipher3 package not installed
    self.core_api.print_error("SQLCipher support requires: uv pip install sqlcipher3")
except ValueError as e:
    # Wrong key, corrupted database, or incompatible version
    self.core_api.print_error(f"Decryption failed: {e}")
except KeyError:
    # Database file not found in ZIP
    self.core_api.print_error(f"Database not found: {db_path}")
```

**Key Discovery:**

For forensic analysis, encryption keys are typically obtained through:
- **iOS backups**: Derived from backup password or keychain extraction
- **Android apps**: Extracted from app code, shared preferences, or memory
- **WhatsApp**: Derived from device IMEI/phone number combination
- **Signal**: Stored in app's secure storage (requires root/jailbreak)
- **Rooted/Jailbroken devices**: Keys may be in application files or system keychain

**Benefits:**
- Automatic temporary file management (created and cleaned up automatically)
- Support for fallback queries (useful for iOS/Android version differences)
- SQLCipher version compatibility (v1-v4) for older databases
- No need for `tempfile`, `sqlite3`, `sqlcipher3`, `plistlib`, or `xml.etree.ElementTree` imports in plugins
- Consistent error handling across all plugins
- Graceful degradation if sqlcipher3 not installed

### BLOB Field Handling

The Core API provides comprehensive support for extracting and handling BLOB (Binary Large Object) fields from SQLite and SQLCipher databases. This is essential for forensic analysis when dealing with images, attachments, binary plists, and other binary data stored in mobile app databases.

**Common Forensic BLOB Use Cases:**
- **Images/Avatars**: Profile pictures, contact photos (WhatsApp, Skype, Contacts)
- **Attachments**: Message attachments, media files (WhatsApp, Signal, messaging apps)
- **Binary Plists**: iOS app preferences, settings stored as binary property lists
- **Thumbnails**: Photo thumbnails in gallery databases (Photos.sqlite)
- **Cached Data**: Binary cached data from apps and browsers

**BLOB Type Detection:**

The Core API can automatically detect BLOB types based on magic bytes:

```python
# Detect BLOB type
blob_data = self.core_api.read_zip_file("some_file.blob")
blob_type = self.core_api.detect_blob_type(blob_data)
# Returns: 'jpeg', 'png', 'gif', 'bmp', 'ico', 'tiff', 'plist', or 'unknown'

# Supported types:
# - JPEG (.jpg)
# - PNG (.png)
# - GIF (.gif - both 87a and 89a)
# - BMP (.bmp)
# - ICO (.ico)
# - TIFF (.tiff - both little and big endian)
# - Binary Plist (.plist)
```

**Extracting BLOBs from SQLite Databases:**

```python
# Extract single BLOB from regular SQLite database
avatar = self.core_api.extract_blob_from_zip(
    "data/data/com.android.providers.contacts/databases/contacts2.db",
    "SELECT photo FROM contacts WHERE _id = ?",
    params=(123,)
)

# Extract multiple BLOBs (batch extraction)
photos = self.core_api.extract_blobs_from_zip(
    "contacts2.db",
    "SELECT photo FROM contacts WHERE photo IS NOT NULL"
)
# Returns: list[bytes] (NULLs are automatically excluded)

# Extract iOS Photo thumbnails
thumbnail = self.core_api.extract_blob_from_zip(
    "filesystem1/private/var/mobile/Media/PhotoData/Photos.sqlite",
    "SELECT thumbnailImage FROM ZGENERICASSET WHERE ZUUID = ?",
    params=("ABC123-DEF456",)
)
```

**Extracting BLOBs from Encrypted SQLCipher Databases:**

```python
# Extract single BLOB from encrypted database (WhatsApp example)
avatar = self.core_api.extract_blob_from_sqlcipher_zip(
    "data/data/com.whatsapp/databases/wa.db",
    "whatsapp_encryption_key",
    "SELECT photo FROM wa_contacts WHERE jid = ?",
    params=("+1234567890@s.whatsapp.net",)
)

# Extract multiple BLOBs from encrypted database
attachments = self.core_api.extract_blobs_from_sqlcipher_zip(
    "data/data/com.whatsapp/databases/msgstore.db",
    "encryption_key",
    "SELECT raw_data FROM message_media WHERE media_mime_type LIKE 'image/%'"
)

# Extract Signal attachments with cipher version compatibility
signal_attachments = self.core_api.extract_blobs_from_sqlcipher_zip(
    "data/data/org.thoughtcrime.securesms/databases/signal.db",
    "signal_key",
    "SELECT data FROM part WHERE content_type LIKE 'image/%'",
    cipher_version=3  # For older SQLCipher versions
)
```

**Saving BLOBs to Files:**

```python
# Save BLOB with automatic extension detection
blob = self.core_api.extract_blob_from_zip("db.db", "SELECT photo FROM users WHERE id=1")
if blob:
    saved_path = self.core_api.save_blob_as_file(
        blob,
        self.core_api.get_case_output_dir("avatars") / "user_avatar.dat",
        auto_extension=True  # Automatically detects type and corrects extension
    )
    # If blob is JPEG, saved as: yaft_output/.../avatars/user_avatar.jpg
    # If blob is PNG, saved as: yaft_output/.../avatars/user_avatar.png

# Save without extension modification
saved_path = self.core_api.save_blob_as_file(
    blob,
    output_path,
    auto_extension=False  # Keeps original extension
)

# Batch extraction and save
photos = self.core_api.extract_blobs_from_zip("photos.db", "SELECT image FROM gallery")
output_dir = self.core_api.get_case_output_dir("extracted_photos")
for i, photo in enumerate(photos):
    self.core_api.save_blob_as_file(photo, output_dir / f"photo_{i}.dat")
```

**Parsing Binary Plists from BLOBs:**

Binary plists are commonly stored in iOS database BLOB fields for preferences and settings:

```python
# Extract and parse binary plist BLOB
rows = self.core_api.query_sqlite_from_zip(
    "filesystem1/Library/Preferences/com.apple.Preferences.db",
    "SELECT value FROM preferences WHERE key = ?"
    params=("app_settings",)
)

if rows and rows[0][0]:
    plist_data = self.core_api.parse_blob_as_plist(rows[0][0])
    # Returns: dict or list with parsed plist data
    print(plist_data["app_version"])
    print(plist_data["settings"]["enabled"])

# Or use extract_blob_from_zip + parse_blob_as_plist
plist_blob = self.core_api.extract_blob_from_zip(
    "prefs.db",
    "SELECT data FROM preferences WHERE key = 'config'"
)
if plist_blob:
    config = self.core_api.parse_blob_as_plist(plist_blob)
```

**Complete Workflow Example:**

```python
def execute(self, *args, **kwargs):
    # Detect ZIP format
    extraction_type, prefix = self.core_api.detect_zip_format()

    # Find database
    db_path = self.core_api.normalize_zip_path(
        "data/data/com.whatsapp/databases/wa.db",
        prefix
    )

    # Extract all contact avatars (encrypted)
    avatars = self.core_api.extract_blobs_from_sqlcipher_zip(
        db_path,
        "whatsapp_key",  # In practice, derive from device
        "SELECT jid, photo FROM wa_contacts WHERE photo IS NOT NULL"
    )

    # Save avatars with automatic type detection
    output_dir = self.core_api.get_case_output_dir("whatsapp_avatars")
    for i, (jid, photo) in enumerate(avatars):
        # Detect type
        blob_type = self.core_api.detect_blob_type(photo)

        # Save with proper extension
        filename = f"contact_{i}_{jid.replace('@', '_').replace('.', '_')}"
        saved_path = self.core_api.save_blob_as_file(
            photo,
            output_dir / f"{filename}.dat",
            auto_extension=True
        )

        self.core_api.print_success(f"Extracted {blob_type} avatar: {saved_path.name}")
```

**Method Signatures:**

```python
# BLOB type detection
def detect_blob_type(blob_data: bytes) -> str:
    # Returns: 'jpeg', 'png', 'gif', 'bmp', 'ico', 'tiff', 'plist', 'unknown'

# Save BLOB to file
def save_blob_as_file(
    blob_data: bytes,
    output_path: Path,
    auto_extension: bool = True
) -> Path:

# Parse binary plist
def parse_blob_as_plist(blob_data: bytes) -> Any:

# Extract single BLOB from SQLite
def extract_blob_from_zip(
    db_path: str,
    query: str,
    params: tuple = (),
    fallback_query: str | None = None
) -> bytes | None:

# Extract multiple BLOBs from SQLite
def extract_blobs_from_zip(
    db_path: str,
    query: str,
    params: tuple = (),
    fallback_query: str | None = None
) -> list[bytes]:

# Extract single BLOB from SQLCipher
def extract_blob_from_sqlcipher_zip(
    db_path: str,
    key: str,
    query: str,
    params: tuple = (),
    fallback_query: str | None = None,
    cipher_version: int | None = None
) -> bytes | None:

# Extract multiple BLOBs from SQLCipher
def extract_blobs_from_sqlcipher_zip(
    db_path: str,
    key: str,
    query: str,
    params: tuple = (),
    fallback_query: str | None = None,
    cipher_version: int | None = None
) -> list[bytes]:
```

**Error Handling:**

```python
try:
    blob = self.core_api.extract_blob_from_sqlcipher_zip(
        db_path,
        encryption_key,
        "SELECT data FROM table WHERE id = ?",
        params=(123,)
    )
except ImportError:
    # sqlcipher3 not installed
    self.core_api.print_error("SQLCipher support requires: uv pip install sqlcipher3")
except ValueError as e:
    # Wrong key or corrupted database
    self.core_api.print_error(f"Decryption failed: {e}")
except KeyError:
    # Database file not found in ZIP
    self.core_api.print_error(f"Database not found: {db_path}")
```

**Benefits:**
- Automatic BLOB type detection based on magic bytes
- Support for both regular SQLite and encrypted SQLCipher databases
- Automatic file extension correction when saving
- Binary plist parsing for iOS forensics
- Batch extraction capabilities
- NULL value filtering
- Consistent error handling
- No need for manual file type inspection

### iOS Keychain and Android Keystore Metadata Extraction

The Core API provides methods to extract metadata from iOS Keychain and Android Keystore/locksettings databases. These methods focus on **metadata extraction only** - they do not decrypt encrypted credentials.

**Important Security Note**: Modern iOS devices (iPhone 5s+) use the Secure Enclave, and Android devices (6.0+) use Gatekeeper with hardware-backed encryption. The encryption keys are device-specific and non-exportable, making offline decryption of actual passwords/credentials practically impossible without the physical device. These methods provide valuable forensic intelligence through metadata analysis and inventory.

#### iOS Keychain Parsing

Extract metadata from iOS `keychain-2.db` database:

```python
# Parse iOS keychain database
keychain_data = self.core_api.parse_ios_keychain(
    "private/var/Keychains/keychain-2.db"
)

# Returns dictionary containing:
{
    "generic_passwords": [
        {
            "rowid": 1,
            "creation_date": "2024-01-15 10:30:00",
            "modification_date": "2024-01-15 10:30:00",
            "description": "Application Password",
            "label": "My App",
            "account": "[ENCRYPTED]",
            "service": "[ENCRYPTED]",
            "access_group": "com.apple.cfnetwork",
            "protection_domain": "[ENCRYPTED]",
            "synchronizable": 0,
            "data": "[ENCRYPTED]"
        }
    ],
    "internet_passwords": [
        {
            "rowid": 2,
            "creation_date": "2024-01-16 14:20:00",
            "modification_date": "2024-01-16 14:20:00",
            "description": "Web Password",
            "label": "example.com",
            "account": "[ENCRYPTED]",
            "security_domain": "www.example.com",
            "server": "example.com",
            "protocol": 1,
            "authentication_type": 1,
            "port": 443,
            "path": "/login",
            "access_group": "com.apple.safari",
            "protection_domain": "[ENCRYPTED]",
            "synchronizable": 1,
            "data": "[ENCRYPTED]"
        }
    ],
    "certificates": [
        {
            "rowid": 3,
            "creation_date": "2024-01-10 08:00:00",
            "modification_date": "2024-01-10 08:00:00",
            "certificate_type": 1,
            "certificate_encoding": 3,
            "label": "Root CA",
            "cert_type": 0,
            "access_group": "com.apple.security",
            "protection_domain": "[ENCRYPTED]",
            "synchronizable": 0,
            "data": "[ENCRYPTED]"
        }
    ],
    "keys": [
        {
            "rowid": 4,
            "creation_date": "2024-01-12 09:15:00",
            "modification_date": "2024-01-12 09:15:00",
            "key_class": 1,
            "label": "Encryption Key",
            "application_tag": "[ENCRYPTED]",
            "creator": 0,
            "key_type": 42,
            "key_size_bits": 256,
            "effective_key_size": 256,
            "access_group": "com.example.app",
            "protection_domain": "[ENCRYPTED]",
            "synchronizable": 0,
            "data": "[ENCRYPTED]"
        }
    ],
    "summary": {
        "total_generic_passwords": 150,
        "total_internet_passwords": 45,
        "total_certificates": 12,
        "total_keys": 8,
        "synchronizable_items": 23,
        "app_specific_items": 180
    },
    "security_note": "Note: Modern iOS devices (iPhone 5s+) use Secure Enclave..."
}
```

**What You Get from iOS Keychain Metadata**:
- **Inventory**: Count of passwords, certificates, and keys stored
- **Timeline**: When credentials were created/modified
- **Application Association**: Which apps use which credentials (via access groups)
- **Synchronization Status**: Which items sync via iCloud Keychain
- **Service Identification**: Which services/websites have stored credentials
- **Key Characteristics**: Key types, sizes, and purposes

**Common Forensic Use Cases**:
```python
# Identify all apps with stored credentials
keychain = self.core_api.parse_ios_keychain("private/var/Keychains/keychain-2.db")
access_groups = set()
for item in keychain["generic_passwords"]:
    if item["access_group"]:
        access_groups.add(item["access_group"])

# Find internet passwords for specific domain
target_domain = "facebook.com"
fb_passwords = [
    item for item in keychain["internet_passwords"]
    if target_domain in (item.get("server") or "")
]

# Analyze synchronization patterns
sync_items = [
    item for item in keychain["generic_passwords"]
    if item["synchronizable"] == 1
]
self.core_api.print_info(f"Found {len(sync_items)} items that sync to iCloud")
```

#### Android Locksettings Parsing

Extract lock screen configuration from Android `locksettings.db`:

```python
# Parse Android locksettings database
locksettings = self.core_api.parse_android_locksettings(
    "data/system/locksettings.db"
)

# Returns dictionary containing:
{
    "lock_settings": {
        "lockscreen.password_type": "262144",
        "lockscreen.password_type_alternate": "0",
        "lockscreen.password_salt": "1234567890",
        "lock_pattern_autolock": "0",
        "lock_pattern_visible": "0",
        "lockscreen.disabled": "0"
    },
    "user_settings": [
        {
            "user_id": 0,
            "lockscreen.password_type": "262144",
            "lockscreen.password_salt": "1234567890",
            "lock_pattern_autolock": "0"
        }
    ],
    "summary": {
        "detected_lock_type": "password",
        "user_count": 1,
        "has_alternate_lock": False,
        "lockscreen_disabled": False
    },
    "security_note": "Note: Android 6.0+ uses Gatekeeper with hardware-backed HMAC..."
}
```

**Lock Type Detection**:
- **0 or None**: No lock screen
- **131072**: Pattern lock
- **196608**: PIN lock
- **262144**: Password lock

**What You Get from Locksettings**:
- **Lock Type**: Pattern, PIN, password, or none
- **User Profiles**: Lock configuration for each device user
- **Security Settings**: Whether lockscreen is disabled, pattern visibility
- **Password Salts**: Present but unusable without device hardware

**Common Forensic Use Cases**:
```python
# Check if device has a lock screen
locksettings = self.core_api.parse_android_locksettings("data/system/locksettings.db")
if locksettings["summary"]["detected_lock_type"] == "none":
    self.core_api.print_warning("Device has no lock screen protection")

# Analyze multi-user configurations
if locksettings["summary"]["user_count"] > 1:
    self.core_api.print_info(f"Device has {locksettings['summary']['user_count']} user profiles")
    for user in locksettings["user_settings"]:
        lock_type = {
            "131072": "Pattern",
            "196608": "PIN",
            "262144": "Password"
        }.get(user.get("lockscreen.password_type", "0"), "None")
        self.core_api.print_info(f"  User {user['user_id']}: {lock_type}")
```

#### Android Keystore File Identification

Identify and catalog Android Keystore files:

```python
# Identify keystore files in extraction
keystore_files = self.core_api.identify_android_keystore_files(
    keystore_dir="data/misc/keystore"
)

# Returns dictionary containing:
{
    "keystore_files": [
        {
            "path": "data/misc/keystore/.masterkey",
            "type": "master_key",
            "size": 96,
            "user_id": None
        },
        {
            "path": "data/misc/keystore/user_0/.masterkey",
            "type": "master_key",
            "size": 96,
            "user_id": 0
        },
        {
            "path": "data/misc/keystore/user_0/10001_USRPKEY_app_key",
            "type": "key_entry",
            "size": 2048,
            "user_id": 0
        }
    ],
    "credential_files": [
        {
            "path": "data/system/gatekeeper.password.key",
            "type": "gatekeeper_key",
            "size": 72
        },
        {
            "path": "data/system/password.key",
            "type": "legacy_credential",
            "size": 32
        }
    ],
    "user_keystores": [0, 10],
    "summary": {
        "total_keystore_files": 3,
        "master_keys": 2,
        "key_entries": 1,
        "total_credential_files": 2,
        "gatekeeper_keys": 1,
        "legacy_credentials": 1,
        "users_with_keystores": 2
    },
    "security_note": "Note: Android keystore uses hardware-backed encryption..."
}
```

**File Types Identified**:
- **`.masterkey`**: Master encryption keys (per-user)
- **`gatekeeper.*.key`**: Gatekeeper authentication files (Android 6.0+)
- **`password.key`, `gesture.key`, `pattern.key`**: Legacy lock screen credentials (pre-6.0)
- **Key entries**: Application-specific cryptographic keys

**What You Get from Keystore Files**:
- **Inventory**: Which apps have stored cryptographic keys
- **User Profiles**: Keystore files for each device user
- **Security Configuration**: Gatekeeper vs legacy authentication
- **File Metadata**: Sizes and locations of credential files

**Common Forensic Use Cases**:
```python
# Identify which apps use keystore
keystore = self.core_api.identify_android_keystore_files()
app_keys = [
    f for f in keystore["keystore_files"]
    if f["type"] == "key_entry"
]
self.core_api.print_info(f"Found {len(app_keys)} application keys")

# Check for legacy vs Gatekeeper authentication
if keystore["summary"]["gatekeeper_keys"] > 0:
    self.core_api.print_info("Device uses Gatekeeper (Android 6.0+) - hardware-backed")
elif keystore["summary"]["legacy_credentials"] > 0:
    self.core_api.print_info("Device uses legacy credentials (pre-Android 6.0)")

# Analyze multi-user keystores
for user_id in keystore["user_keystores"]:
    user_keys = [
        f for f in keystore["keystore_files"]
        if f.get("user_id") == user_id
    ]
    self.core_api.print_info(f"User {user_id}: {len(user_keys)} keystore files")
```

#### Method Signatures

```python
# iOS Keychain parsing
def parse_ios_keychain(
    keychain_db_path: str
) -> dict[str, Any]:
    """
    Parse iOS keychain-2.db and extract metadata.

    Returns:
        Dictionary with generic_passwords, internet_passwords,
        certificates, keys, summary, and security_note
    """

# Android locksettings parsing
def parse_android_locksettings(
    locksettings_db_path: str
) -> dict[str, Any]:
    """
    Parse Android locksettings.db for lock screen configuration.

    Returns:
        Dictionary with lock_settings, user_settings,
        summary, and security_note
    """

# Android keystore file identification
def identify_android_keystore_files(
    keystore_dir: str = "data/misc/keystore"
) -> dict[str, Any]:
    """
    Identify and catalog Android Keystore files.

    Args:
        keystore_dir: Base keystore directory (default: data/misc/keystore)

    Returns:
        Dictionary with keystore_files, credential_files,
        user_keystores, summary, and security_note
    """
```

#### Error Handling

```python
try:
    keychain = self.core_api.parse_ios_keychain("private/var/Keychains/keychain-2.db")
except KeyError:
    self.core_api.print_error("Keychain database not found in extraction")
except Exception as e:
    self.core_api.print_error(f"Failed to parse keychain: {e}")

try:
    locksettings = self.core_api.parse_android_locksettings("data/system/locksettings.db")
except KeyError:
    self.core_api.print_error("Locksettings database not found")
except Exception as e:
    self.core_api.print_error(f"Failed to parse locksettings: {e}")
```

#### Why Metadata-Only?

**Technical Reality**:
1. **iOS Secure Enclave** (iPhone 5s+): Encryption keys never leave the secure processor
2. **Android Gatekeeper** (6.0+): Hardware-backed HMAC requires device cooperation
3. **Hardware-Backed Keys**: Marked as non-exportable by design
4. **Device-Specific Encryption**: Keys derived from device UID + user password

**What Professional Tools Do**:
- **Cellebrite/GrayKey**: Exploit vulnerabilities, firmware-level access, or brute-force on device
- **Chip-Off Forensics**: Physical chip extraction with specialized hardware
- **Secure Enclave Exploitation**: Advanced techniques requiring significant resources

**Forensic Value of Metadata**:
- Understand which apps/services have credentials stored
- Timeline analysis (when credentials were created/modified)
- Correlation with other artifacts (app usage, network connections)
- Identify high-value targets for on-device exploitation
- Support warrant applications with evidence of credential existence
- Multi-user device analysis

**Benefits:**
- Honest about technical limitations (builds trust)
- Immediately useful for forensic analysis
- Complements professional extraction tools
- No false promises about decryption capabilities
- Provides intelligence even when decryption isn't possible

### Forensic ZIP Format Detection

The Core API automatically detects the format of forensic ZIP extractions from different tools (Cellebrite, GrayKey) and operating systems (iOS, Android):

```python
# Detect extraction format
format_type, prefix = self.core_api.detect_zip_format()
# Returns: ("cellebrite_ios", "filesystem1/") or ("graykey_android", "") etc.

# Normalize a filesystem path with the detected prefix
full_path = self.core_api.normalize_zip_path("data/data/com.example.app/databases/app.db", prefix)
# Returns: "Dump/data/data/com.example.app/databases/app.db" (Cellebrite Android)
# Or: "data/data/com.example.app/databases/app.db" (GrayKey Android)
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

**Detection Logic:**
1. Scans root-level folders in the ZIP archive (first 100 entries)
2. Identifies characteristic folder patterns for each format:
   - **Cellebrite Android**: `Dump/` and/or `extra/` folders
   - **Cellebrite iOS**: `filesystem1/` or `filesystem/` folder
   - **GrayKey Android**: 3+ matches from `apex/`, `bootstrap-apex/`, `cache/`, `data/`, `data-mirror/`, `efs/`, `system/`
   - **GrayKey iOS**: 2+ matches from `private/`, `System/`, `Library/`, `Applications/`, `var/`
3. Falls back to deeper file structure analysis if root folders don't match

**Plugin Usage:**
```python
def execute(self, *args, **kwargs):
    # Detect format
    format_type, prefix = self.core_api.detect_zip_format()

    # Use the prefix for all file paths
    if "android" in format_type:
        db_path = self.core_api.normalize_zip_path("data/data/com.example/databases/app.db", prefix)
    elif "ios" in format_type:
        plist_path = self.core_api.normalize_zip_path("System/Library/CoreServices/SystemVersion.plist", prefix)

    # Read files with normalized paths
    data = self.core_api.read_plist_from_zip(plist_path)
```

## Unified Report Generation

All plugins should use the CoreAPI's `generate_report()` method for consistent markdown report generation:

```python
# In plugin execute() method:
sections = [
    {
        "heading": "Executive Summary",
        "content": "Summary text here",
        "level": 2,  # Optional, default 2
    },
    {
        "heading": "Findings",
        "content": ["Finding 1", "Finding 2", "Finding 3"],
        "style": "list",  # Options: text, list, table, code
    },
    {
        "heading": "Statistics",
        "content": {
            "Total Files": 100,
            "Suspicious": 5,
            "Clean": 95,
        },
        "style": "table",
    },
]

metadata = {
    "Analysis Type": "Forensic ZIP Analysis",
    "Duration": "2.5 seconds",
}

report_path = self.core_api.generate_report(
    plugin_name="MyPlugin",
    title="Analysis Report Title",
    sections=sections,
    metadata=metadata,
)
# Returns: Path to generated markdown report in yaft_output/reports/
```

### Report Features

- **Automatic Metadata**: Includes plugin name, timestamp, source ZIP, case identifiers
- **Consistent Formatting**: All reports follow the same markdown structure
- **Multiple Content Styles**: text, list, table, code blocks
- **Timestamped Filenames**: Reports won't overwrite each other
- **Standard Location**: `yaft_output/<case_id>/<evidence_id>/reports/PluginName_YYYYMMDD_HHMMSS.md`
- **PDF Export**: Automatically export reports to PDF format with professional styling
- **HTML Export**: Export reports to HTML format for web-based viewing and sharing

### PDF and HTML Export

YaFT supports automatic export of markdown reports to both PDF and HTML formats with professional formatting. Exports are generated with proper styling including tables, code blocks, headings, and lists.

**Dependencies:**

Both PDF and HTML export are **optional** and require additional packages. YaFT works perfectly without these dependencies - they're only needed if you want to generate PDF or HTML reports.

```bash
# Install PDF export dependencies (includes HTML export)
uv pip install -e ".[pdf]"

# Or install manually
# For both PDF and HTML
uv pip install markdown weasyprint

# For HTML only (lighter weight, no WeasyPrint needed)
uv pip install markdown
```

**Windows Installation:**
WeasyPrint requires GTK libraries on Windows. Install GTK3 Runtime:
1. Download GTK3 Runtime from: https://github.com/tschoonj/GTK-for-Windows-Runtime-Environment-Installer/releases
2. Run the installer (gtk3-runtime-x.x.x-x64-en.exe)
3. Add GTK `bin` directory to PATH: `C:\Program Files\GTK3-Runtime Win64\bin`
4. Restart terminal and install packages: `uv pip install markdown weasyprint`

**Linux/macOS:**
```bash
# Linux (Debian/Ubuntu)
sudo apt-get install libpango-1.0-0 libpangocairo-1.0-0 libgdk-pixbuf2.0-0 libffi-dev

# macOS (with Homebrew)
brew install pango gdk-pixbuf libffi
```

**CLI Usage:**
```bash
# Enable PDF export for a single plugin
python -m yaft.cli run iOSDeviceInfoExtractorPlugin --zip evidence.zip --pdf

# Enable HTML export for a single plugin
python -m yaft.cli run iOSDeviceInfoExtractorPlugin --zip evidence.zip --html

# Enable both PDF and HTML export
python -m yaft.cli run iOSDeviceInfoExtractorPlugin --zip evidence.zip --pdf --html

# Enable PDF export for profile execution
python -m yaft.cli run --zip evidence.zip --profile profiles/ios_full_analysis.toml --pdf

# Enable HTML export for profile execution
python -m yaft.cli run --zip evidence.zip --profile profiles/ios_full_analysis.toml --html

# Enable both exports for profile execution
python -m yaft.cli run --zip evidence.zip --profile profiles/ios_full_analysis.toml --pdf --html
```

**Programmatic Usage:**
```python
# Enable automatic PDF generation
self.core_api.enable_pdf_export(True)

# Enable automatic HTML generation
self.core_api.enable_html_export(True)

# Generate report (PDF/HTML created automatically if enabled)
report_path = self.core_api.generate_report(
    plugin_name="MyPlugin",
    title="Analysis Report",
    sections=sections,
)

# Manually convert a markdown file to PDF
pdf_path = self.core_api.convert_markdown_to_pdf(markdown_path)

# Manually convert a markdown file to HTML
html_path = self.core_api.convert_markdown_to_html(markdown_path)

# Batch export all generated reports to PDF
pdf_paths = self.core_api.export_all_reports_to_pdf()

# Batch export all generated reports to HTML
html_paths = self.core_api.export_all_reports_to_html()
```

**Features:**
- **Professional Styling**:
  - PDF: Blue color scheme, proper typography, A4 page format
  - HTML: Responsive design, modern styling, browser-friendly layout
- **Full Markdown Support**: Tables, code blocks, lists, headings, emphasis, blockquotes
- **Automatic Generation**: PDFs/HTML files created alongside markdown when `--pdf`/`--html` flags are used
- **Batch Conversion**: Convert all reports from a session with `export_all_reports_to_pdf()` or `export_all_reports_to_html()`
- **Flexible Formats**: Generate PDF for archival, HTML for web viewing, or both
- **Lightweight HTML**: HTML export only requires `markdown` package (no WeasyPrint needed)
- **Graceful Degradation**: Falls back to markdown-only if export packages aren't installed

## Forensic Analysis Plugins

YaFT includes production-ready forensic analysis plugins for both iOS and Android devices:

### iOS Plugins

1. **iOSDeviceInfoExtractorPlugin** - Extract comprehensive device information
   - System version, device identifiers (UDID, IMEI, serial)
   - Carrier info, timezone, locale, backup information
   - Supports both Cellebrite and GrayKey extraction formats

2. **iOSCallLogAnalyzerPlugin** - Analyze call history
   - Extracts from CallHistory.storedata
   - Supports regular calls, FaceTime (audio/video), missed calls
   - Handles Core Data timestamps (seconds since 2001-01-01)
   - Call pattern analysis and frequent contact detection

3. **iOSCellularInfoExtractorPlugin** - Extract cellular information
   - Extracts from com.apple.commcenter.plist
   - IMSI (International Mobile Subscriber Identity)
   - IMEI (International Mobile Equipment Identity) updates
   - ICCI (Integrated Circuit Card Identifier)
   - Phone number and carrier entitlements
   - Supports both Cellebrite and GrayKey extraction formats
   - Based on iLEAPP artifact by @AlexisBrignoni and @stark4n6

### Android Plugins

1. **AndroidDeviceInfoExtractorPlugin** - Extract comprehensive device information
   - Build properties (manufacturer, model, Android version)
   - Device identifiers (Android ID, IMEI, serial number)
   - SIM card info, accounts, Bluetooth devices
   - Security settings (ADB enabled, developer mode)

2. **AndroidAppInfoExtractorPlugin** - Extract application metadata
   - Parses packages.xml, packages.list, usage statistics
   - App categorization (system, user, suspicious)
   - Launch counts and install timestamps

3. **AndroidAppPermissionsExtractorPlugin** - Analyze application permissions
   - Runtime permissions, declared permissions, app ops
   - Risk scoring based on permission types
   - High-risk permission detection (SMS, location, camera, etc.)

4. **AndroidCallLogAnalyzerPlugin** - Analyze call history
   - Extracts from calllog.db
   - Supports regular calls, video calls, missed/rejected calls
   - Handles Unix millisecond timestamps
   - Call pattern analysis and video call detection

### ZIP Format Support

All forensic plugins support both **Cellebrite** and **GrayKey** extraction formats:
- **Cellebrite**: Files prefixed with `fs/` or `filesystem1/`
- **GrayKey**: No prefix, files at root level

Plugins use CoreAPI methods to automatically detect and handle both formats:
```python
# Detect format
self.extraction_type, self.zip_prefix = self.core_api.detect_zip_format()

# Normalize paths for ZIP access
normalized_path = self.core_api.normalize_zip_path(path, self.zip_prefix)
```

## Plugin Update System

YAFT includes an automatic plugin update system that synchronizes plugins with the GitHub repository. This allows users to easily keep plugins up-to-date and download new plugins as they become available.

### Architecture: Hybrid Approach with Manifest

The plugin update system uses a manifest-based approach that balances performance, security, and offline capability:

1. **Manifest File** (`plugins_manifest.json`): Contains metadata for all plugins including SHA256 hashes
2. **Minimal API Calls**: Only checks manifest for changes (respects rate limits)
3. **Raw URL Downloads**: Downloads plugins directly from GitHub (no rate limits)
4. **SHA256 Verification**: Ensures integrity of downloaded files
5. **Offline-Friendly Caching**: Caches manifest for offline use
6. **User-Controlled**: Updates are opt-in, not automatic

### Plugin Manifest Format

```json
{
  "manifest_version": "1.0.0",
  "last_updated": "2025-01-17T10:00:00Z",
  "repository": "RedRockerSE/yaft",
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
    }
  ]
}
```

### CLI Commands

```bash
# Check for plugin updates and download them
python -m yaft.cli update-plugins

# Check only (don't download)
python -m yaft.cli update-plugins --check-only

# Force check (ignore cache)
python -m yaft.cli update-plugins --force

# Update specific plugin
python -m yaft.cli update-plugins --plugin ios_device_info_extractor.py

# List all available plugins from repository
python -m yaft.cli list-available-plugins

# Filter by OS
python -m yaft.cli list-available-plugins --os ios
```

### Core API Integration

Plugins can programmatically access the update system:

```python
# Get PluginUpdater instance
updater = self.core_api.get_plugin_updater()

# Check for updates
result = updater.check_for_updates(force=False)

if result.updates_available:
    self.core_api.print_info(f"Found {len(result.new_plugins)} new plugins")
    self.core_api.print_info(f"Found {len(result.updated_plugins)} updated plugins")

    # Download updates
    download_result = updater.download_plugins(
        plugin_list=None,  # None = all available updates
        verify=True,       # Verify SHA256 hashes
        backup=True,       # Backup existing plugins
    )

    if download_result.success:
        self.core_api.print_success(f"Downloaded {len(download_result.downloaded)} plugins")

# List available plugins
plugins = updater.list_available_plugins()
for plugin in plugins:
    print(f"{plugin['name']} - {plugin['version']}")
```

### Automatic Manifest Updates

The manifest is automatically updated via GitHub Actions when plugins change:

- **Trigger**: Any push to `plugins/*.py` files on main branch
- **Action**: Runs `scripts/generate_manifest.py` to regenerate manifest
- **Commit**: Automatically commits and pushes updated manifest
- **Workflow**: `.github/workflows/update-manifest.yml`

### Security Features

1. **SHA256 Verification**: All downloaded plugins are verified against manifest hashes
2. **HTTPS Only**: All downloads use secure connections
3. **No Code Execution**: Plugins are not executed during download
4. **Backup Creation**: Existing plugins are backed up before overwriting
5. **User Confirmation**: Updates are user-initiated, not automatic

### Update Workflow

```
User runs update-plugins
        ↓
Check cached manifest age
        ↓
Fetch remote manifest (if needed)
        ↓
Compare local vs remote plugins
        ↓
Display available updates
        ↓
Download new/updated plugins
        ↓
Verify SHA256 hashes
        ↓
Write to plugins/ directory
        ↓
Complete
```

### Cache Management

The update system maintains a cache directory (`.plugin_cache/`) containing:
- `manifest.json`: Last fetched manifest from GitHub
- `last_check.txt`: Timestamp of last update check

By default, the system checks for updates at most once every 24 hours unless `--force` is used.

### Offline Operation

The update system is designed to work offline:
- Cached manifest is used if available
- Update checks can be skipped if recently checked
- Forensic analysis works without any update checks
- No network connectivity required for plugin execution

## Development Commands

### Environment Setup with uv

```bash
# Install uv (if not installed)
# Windows: powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
# Linux/macOS: curl -LsSf https://astral.sh/uv/install.sh | sh

# Create virtual environment
uv venv

# Activate virtual environment
# Windows: .venv\Scripts\activate
# Linux/macOS: source .venv/bin/activate

# Install dependencies (editable mode with dev dependencies)
uv pip install -e ".[dev]"

# Or install from requirements files
uv pip install -r requirements-dev.txt
```

### Common Commands

```bash
# List available plugins
python -m yaft.cli list-plugins

# Analyze a ZIP file (NOTE: use full class name with "Plugin" suffix)
python -m yaft.cli run iOSDeviceInfoExtractorPlugin --zip evidence.zip
python -m yaft.cli run AndroidCallLogAnalyzerPlugin --zip android_extraction.zip

# Run multiple plugins using a profile
python -m yaft.cli run --zip evidence.zip --profile profiles/ios_full_analysis.toml
python -m yaft.cli run --zip android.zip --profile profiles/android_full_analysis.toml

# Run with PDF export enabled (generates both markdown and PDF reports)
python -m yaft.cli run --zip evidence.zip --profile profiles/ios_full_analysis.toml --pdf

# Run tests
pytest

# Run specific test file
pytest tests/test_android_call_log_analyzer.py

# Run single test
pytest tests/test_android_call_log_analyzer.py::test_parse_call_log_cellebrite

# Run tests with coverage
pytest --cov=src/yaft --cov-report=html

# Run tests with verbose output
pytest -v

# Run tests without coverage report
pytest --no-cov

# Lint code
ruff check src/ tests/ plugins/

# Format code
ruff format src/ tests/ plugins/

# Type checking
mypy src/

# Build executables
python build_exe.py

# Install/update a single package with uv
uv pip install package-name
```

## Plugin Profiles

YaFT supports plugin profiles - TOML configuration files that specify a set of plugins to run together. This makes it easy to perform standard analysis workflows without manually listing plugins each time.

### Profile Format

Plugin profiles are TOML files with the following structure:

```toml
[profile]
name = "Profile Name"
description = "Optional description of what this profile does"

plugins = [
    "PluginClassName1",
    "PluginClassName2",
    "PluginClassName3",
]
```

### Using Profiles

Run a profile using the `--profile` option:

```bash
# Run iOS full analysis profile
python -m yaft.cli run --zip evidence.zip --profile profiles/ios_full_analysis.toml

# Run Android apps analysis profile
python -m yaft.cli run --zip android.zip --profile profiles/android_apps_analysis.toml
```

### Built-in Profiles

YaFT includes several pre-configured profiles in the `profiles/` directory:

**iOS Profiles:**
- `ios_full_analysis.toml` - Complete iOS forensic analysis (device info, apps, permissions, call logs)
- `ios_device_only.toml` - Quick device information extraction

**Android Profiles:**
- `android_full_analysis.toml` - Complete Android forensic analysis (device info, apps, permissions, call logs)
- `android_apps_analysis.toml` - Application-focused analysis (metadata and permissions)

### Creating Custom Profiles

1. Create a new `.toml` file in the `profiles/` directory (or any location)
2. Use the profile format shown above
3. List plugin class names in the `plugins` array (exact class names required)
4. Plugins execute in the order listed

**Example:**

```toml
[profile]
name = "Custom iOS Analysis"
description = "Custom workflow for iOS device analysis"

plugins = [
    "iOSDeviceInfoExtractorPlugin",
    "iOSCallLogAnalyzerPlugin",
]
```

### Profile Validation

The Core API validates profiles to ensure:
- Required fields are present (`name` and `plugins`)
- Plugin list is not empty
- Plugin names are not empty or whitespace-only
- TOML syntax is valid

Invalid profiles will fail with a clear error message before execution.

### Core API Methods

```python
# Load and validate a profile (in plugins or custom code)
profile = self.core_api.load_plugin_profile(Path("profiles/my_profile.toml"))

# Access profile properties
profile.name          # str: Profile name
profile.description   # str | None: Profile description
profile.plugins       # list[str]: List of plugin class names
```

## Plugin Development

### Creating a New Plugin

1. Create a new file in `plugins/` directory
2. Inherit from `PluginBase`
3. Implement required methods: metadata, initialize(), execute(), cleanup()
4. Use Core API for ZIP handling and other shared functionality

### Example Plugin Structure

```python
from yaft.core.api import CoreAPI
from yaft.core.plugin_base import PluginBase, PluginMetadata

class MyForensicPlugin(PluginBase):
    @property
    def metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name="MyForensicPlugin",
            version="1.0.0",
            description="Description",
            author="Your Name",
            target_os=["ios", "android"],  # Optional: specify target OS
        )

    def initialize(self) -> None:
        # Setup resources
        pass

    def execute(self, *args, **kwargs) -> Any:
        # Main logic - access ZIP via self.core_api
        if not self.core_api.get_current_zip():
            self.core_api.print_error("No ZIP file loaded")
            return None

        # Detect ZIP format (Cellebrite vs GrayKey)
        extraction_type, zip_prefix = self.core_api.detect_zip_format()

        # Normalize paths for ZIP access
        path = self.core_api.normalize_zip_path("path/to/file", zip_prefix)

        # Parse data formats
        plist_data = self.core_api.read_plist_from_zip(path)
        xml_root = self.core_api.read_xml_from_zip(path)
        db_rows = self.core_api.query_sqlite_from_zip_dict(path, "SELECT * FROM table")

        # Generate report
        report_path = self.core_api.generate_report(
            plugin_name=self.metadata.name,
            title="Analysis Report",
            sections=sections,
        )

        return results

    def cleanup(self) -> None:
        # Clean up resources
        pass
```

### Forensic Plugin Pattern

For forensic analysis plugins, follow this pattern:

```python
def execute(self, *args, **kwargs) -> Dict[str, Any]:
    # 1. Check ZIP file is loaded
    if not self.core_api.get_current_zip():
        return {"success": False, "error": "No ZIP file loaded"}

    # 2. Detect ZIP structure (Cellebrite/GrayKey)
    self.extraction_type, self.zip_prefix = self.core_api.detect_zip_format()

    # 3. Extract data from ZIP
    data = self._parse_forensic_artifacts()

    # 4. Analyze and process data
    self._analyze_data()

    # 5. Generate report
    report_path = self._generate_report()

    # 6. Export to JSON
    output_dir = self.core_api.get_case_output_dir("plugin_outputs")
    json_path = output_dir / "data.json"
    self._export_to_json(json_path)

    return {
        "success": True,
        "report_path": str(report_path),
        "json_path": str(json_path),
    }
```

## Important Implementation Details

- **ZIP File Lifecycle**: ZIP files are loaded before plugin execution and closed after
- **Plugin Discovery**: Uses file system scanning + importlib (works in dev and built executables)
- **Plugin Naming**: Plugins are registered and accessed by **class name** (e.g., `iOSDeviceInfoExtractorPlugin`), not metadata name
- **Error Handling**: Plugins fail gracefully; errors don't crash the app
- **Forensic Focus**: Plugins should assume they're processing evidence and handle data carefully
- **Case Identifiers**: CLI prompts for case identifiers (Examiner ID, Case ID, Evidence ID) before plugin execution
- **Output Directory**: Use `core_api.get_case_output_dir(subdir)` for case-organized output paths (falls back to `yaft_output/` if no case IDs)
- **Report Generation**: All plugins MUST use `core_api.generate_report()` for consistent markdown reporting
- **Report Location**: Reports are saved to `yaft_output/<case_id>/<evidence_id>/reports/` with case identifiers in metadata
- **iOS/Android Analysis**: Forensic plugins use temporary directories for SQLite database extraction (auto-cleaned)
- **Windows Compatibility**: CoreAPI uses ASCII-safe output markers ([OK], [ERROR], [WARNING], [INFO]) instead of Unicode symbols for Windows console compatibility

## Testing Plugins

Create comprehensive tests for forensic plugins:

```python
# tests/test_my_plugin.py
import pytest
import zipfile
import sqlite3
from pathlib import Path

from yaft.core.api import CoreAPI
from plugins.my_plugin import MyPlugin

@pytest.fixture
def core_api(tmp_path):
    api = CoreAPI()
    api.base_output_dir = tmp_path / "yaft_output"
    api.base_output_dir.mkdir(parents=True, exist_ok=True)
    return api

@pytest.fixture
def plugin(core_api):
    return MyPlugin(core_api)

@pytest.fixture
def mock_zip_cellebrite(tmp_path):
    """Create mock ZIP in Cellebrite format."""
    zip_path = tmp_path / "extraction.zip"

    # Create mock database
    db_path = tmp_path / "test.db"
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("CREATE TABLE data (id INTEGER, value TEXT)")
    cursor.execute("INSERT INTO data VALUES (1, 'test')")
    conn.commit()
    conn.close()

    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.write(db_path, "fs/path/to/test.db")  # Cellebrite format

    return zip_path

def test_plugin_execution(plugin, core_api, mock_zip_cellebrite):
    core_api.set_zip_file(mock_zip_cellebrite)

    result = plugin.execute()

    assert result["success"] is True
    assert Path(result["report_path"]).exists()
```

### Test Coverage Guidelines

For forensic plugins, create tests covering:
- Plugin metadata and initialization
- ZIP structure detection (Cellebrite/GrayKey)
- Data parsing from forensic artifacts
- Analysis and pattern detection
- Full extraction workflow
- JSON export and report generation
- Error handling (missing files, malformed data)
- Edge cases specific to forensic data

## Building Executables

```bash
# Build for current platform
python build_exe.py

# Clean build
python build_exe.py --clean
```

Output: `dist/yaft/` containing executable and `plugins/` directory. New plugins can be added to built executables without recompilation.

## Important Notes

- **Plugin File Naming**: Plugins are discovered by class name, not filename. Use descriptive class names ending with "Plugin"
- **Unicode Output**: Always use `encoding='utf-8'` when reading/writing files to avoid Windows encoding issues
- **Timestamp Handling**: iOS uses Core Data timestamps (seconds since 2001-01-01), Android uses Unix milliseconds
- **Fallback Queries**: Always provide fallback SQL queries for older iOS/Android versions with different schemas
- **Data Validation**: Validate all extracted data before including in reports
- **Error Tracking**: Store errors in `self.errors` list and include in reports
- **Clean Imports**: Don't import temporary/test modules in production code
