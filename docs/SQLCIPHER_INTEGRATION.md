# SQLCipher Integration for YaFT

This document describes the SQLCipher encrypted database support added to YaFT's Core API.

## Overview

SQLCipher is an open-source extension to SQLite that provides transparent 256-bit AES encryption of database files. It's widely used in mobile applications for securing sensitive data, making it common in mobile forensics scenarios.

## Use Cases in Mobile Forensics

SQLCipher-encrypted databases are commonly found in:

- **WhatsApp**: Message databases (msgstore.db)
- **Signal**: Secure messaging databases
- **iOS Applications**: App-specific encrypted data stores
- **Android Applications**: Encrypted app databases
- **Custom Enterprise Apps**: Business applications with sensitive data

## Installation

SQLCipher support is **optional** and requires the `sqlcipher3` Python package:

```bash
# Install SQLCipher support
uv pip install sqlcipher3
```

The `sqlcipher3` package provides:
- DB-API 2.0 compliant interface
- Binary wheels (no external dependencies on most platforms)
- SQLCipher 4 by default, with backward compatibility for v1-v3

## Core API Methods

YaFT's Core API provides three main methods for working with encrypted databases:

### 1. `query_sqlcipher_from_zip()`

Query an encrypted database and return results as tuples.

```python
def query_sqlcipher_from_zip(
    db_path: str,
    key: str,
    query: str,
    params: tuple = (),
    fallback_query: str | None = None,
    cipher_version: int | None = None,
) -> list[tuple]
```

**Parameters:**
- `db_path`: Path to encrypted database within ZIP archive
- `key`: Encryption key/password
- `query`: SQL query to execute
- `params`: Optional query parameters (for ? placeholders)
- `fallback_query`: Fallback query for schema differences
- `cipher_version`: SQLCipher version (1-4) for compatibility

**Example:**
```python
rows = self.core_api.query_sqlcipher_from_zip(
    "data/data/com.whatsapp/databases/msgstore.db",
    "encryption_key",
    "SELECT key_remote_jid, data, timestamp FROM messages WHERE timestamp > ?",
    params=(1609459200000,)
)
```

### 2. `query_sqlcipher_from_zip_dict()`

Query an encrypted database and return results as dictionaries (with column names).

```python
def query_sqlcipher_from_zip_dict(
    db_path: str,
    key: str,
    query: str,
    params: tuple = (),
    fallback_query: str | None = None,
    cipher_version: int | None = None,
) -> list[dict[str, Any]]
```

**Example:**
```python
messages = self.core_api.query_sqlcipher_from_zip_dict(
    "data/data/com.whatsapp/databases/msgstore.db",
    "encryption_key",
    "SELECT key_remote_jid, data, timestamp FROM messages ORDER BY timestamp DESC LIMIT 100"
)

for msg in messages:
    print(f"{msg['timestamp']}: {msg['data']}")
```

### 3. `decrypt_sqlcipher_database()`

Decrypt an encrypted database and save as plain SQLite file.

```python
def decrypt_sqlcipher_database(
    db_path: str,
    key: str,
    output_path: Path,
    cipher_version: int | None = None,
) -> Path
```

**Example:**
```python
decrypted_path = self.core_api.decrypt_sqlcipher_database(
    "data/data/com.whatsapp/databases/msgstore.db",
    "encryption_key",
    Path("yaft_output/decrypted/whatsapp_msgstore.db")
)
# Now you can use standard SQLite tools on the decrypted database
```

## SQLCipher Version Compatibility

SQLCipher has evolved through several versions, each with different encryption parameters:

- **SQLCipher 4** (default): Current version, strongest security
- **SQLCipher 3**: Common in older Android/iOS apps (2013-2018)
- **SQLCipher 2**: Legacy apps
- **SQLCipher 1**: Very old apps

Use the `cipher_version` parameter when working with older databases:

```python
# Query a SQLCipher v3 database
rows = self.core_api.query_sqlcipher_from_zip(
    "old_app.db",
    "key",
    "SELECT * FROM users",
    cipher_version=3
)
```

## Error Handling

The SQLCipher methods provide clear error handling:

### ImportError
Raised when `sqlcipher3` is not installed:
```python
try:
    rows = self.core_api.query_sqlcipher_from_zip(db_path, key, query)
except ImportError:
    self.core_api.print_error("SQLCipher support requires: uv pip install sqlcipher3")
```

### ValueError
Raised when decryption fails (wrong key, corrupted database, version mismatch):
```python
try:
    rows = self.core_api.query_sqlcipher_from_zip(db_path, key, query)
except ValueError as e:
    # Try with different cipher version
    rows = self.core_api.query_sqlcipher_from_zip(
        db_path, key, query, cipher_version=3
    )
```

### KeyError
Raised when database file not found in ZIP:
```python
try:
    rows = self.core_api.query_sqlcipher_from_zip(db_path, key, query)
except KeyError:
    self.core_api.print_error(f"Database not found: {db_path}")
```

## Forensic Workflows

### Workflow 1: WhatsApp Message Extraction

```python
def extract_whatsapp_messages(self):
    """Extract WhatsApp messages from encrypted database."""

    # Find WhatsApp database
    db_files = self.core_api.find_files_in_zip("msgstore.db")

    if not db_files:
        self.core_api.print_error("WhatsApp database not found")
        return

    # Obtain encryption key (in real forensics, derived from device)
    key = self._derive_whatsapp_key()

    # Query messages
    messages = self.core_api.query_sqlcipher_from_zip_dict(
        db_files[0],
        key,
        """
        SELECT
            key_remote_jid,
            key_from_me,
            data,
            timestamp,
            media_wa_type
        FROM messages
        ORDER BY timestamp DESC
        LIMIT 1000
        """
    )

    # Process and report
    self._generate_message_report(messages)
```

### Workflow 2: iOS App Database Analysis

```python
def analyze_ios_app_database(self):
    """Analyze encrypted iOS app database."""

    # Detect ZIP format
    extraction_type, prefix = self.core_api.detect_zip_format()

    # Find app databases
    db_path = self.core_api.normalize_zip_path(
        "private/var/mobile/Containers/Data/Application/ABC123/Documents/app.db",
        prefix
    )

    # Query with SQLCipher v3 (common in iOS apps)
    try:
        tables = self.core_api.query_sqlcipher_from_zip_dict(
            db_path,
            app_key,
            "SELECT name FROM sqlite_master WHERE type='table'",
            cipher_version=3
        )

        for table in tables:
            self._analyze_table(table['name'])

    except ValueError:
        self.core_api.print_error("Failed to decrypt (wrong key or version)")
```

### Workflow 3: Bulk Database Decryption

```python
def decrypt_all_databases(self):
    """Decrypt all encrypted databases for external analysis."""

    # Find all databases
    db_files = self.core_api.find_files_in_zip("*.db")

    output_dir = self.core_api.get_case_output_dir("decrypted_databases")
    output_dir.mkdir(parents=True, exist_ok=True)

    for db_path in db_files:
        try:
            output_path = output_dir / Path(db_path).name

            self.core_api.decrypt_sqlcipher_database(
                db_path,
                self._get_key_for_database(db_path),
                output_path
            )

            self.core_api.print_success(f"Decrypted: {db_path}")

        except ValueError:
            self.core_api.print_warning(f"Could not decrypt: {db_path}")
```

## Key Discovery Methods

In forensic analysis, encryption keys are typically obtained through:

### iOS Devices
- **Backup Password**: Derive key from iTunes/iCloud backup password
- **Keychain Extraction**: Extract keys from device keychain (jailbroken devices)
- **App Binary Analysis**: Reverse engineer app to find key derivation logic
- **Memory Forensics**: Extract keys from device memory dump

### Android Devices
- **Root Access**: Read keys from app's private storage
- **Shared Preferences**: Keys stored in SharedPreferences XML files
- **App Code Analysis**: Decompile APK to find key derivation logic
- **Memory Dump**: Extract keys from running process memory

### Common Key Derivation Methods
- **IMEI-based**: Key derived from device IMEI number
- **Phone Number**: Key based on user's phone number
- **Device ID**: Key derived from Android ID or iOS UDID
- **User Password**: Key derived from user-entered password
- **Hardcoded**: Static keys embedded in app (poor security)

## Best Practices

### 1. Always Handle ImportError
```python
try:
    rows = self.core_api.query_sqlcipher_from_zip(db_path, key, query)
except ImportError:
    self.core_api.print_warning("SQLCipher support not available, skipping encrypted databases")
    return None
```

### 2. Try Multiple Cipher Versions
```python
for version in [None, 3, 2, 1]:  # Try v4, v3, v2, v1
    try:
        rows = self.core_api.query_sqlcipher_from_zip(
            db_path, key, query, cipher_version=version
        )
        self.core_api.print_success(f"Decrypted with SQLCipher v{version or 4}")
        break
    except ValueError:
        continue
```

### 3. Validate Decryption Success
```python
# After decryption, verify the database is valid
try:
    # Query a known system table
    tables = self.core_api.query_sqlcipher_from_zip(
        db_path,
        key,
        "SELECT COUNT(*) FROM sqlite_master"
    )
    # If we get here, decryption succeeded
except Exception:
    # Decryption failed or database corrupted
    pass
```

### 4. Document Key Sources
Always document where encryption keys came from in your reports:
```python
metadata = {
    "Encryption Key Source": "Derived from device IMEI",
    "Key Derivation Method": "MD5(IMEI + UIN)[0:7]",
    "SQLCipher Version": "3",
}
```

## Testing

Comprehensive tests are provided in `tests/test_sqlcipher.py`:

```bash
# Run SQLCipher tests
python -m pytest tests/test_sqlcipher.py -v

# Run all tests
python -m pytest --no-cov -q
```

Tests cover:
- Querying encrypted databases (tuples and dicts)
- Wrong key handling
- SQLCipher version compatibility
- Database decryption
- Error handling for missing package
- Real-world forensic scenarios (WhatsApp, iOS apps)

## Example Plugin

A complete example plugin is provided in `examples/sqlcipher_example_plugin.py` demonstrating:
- Querying encrypted databases
- Handling different SQLCipher versions
- Decrypting databases to plain SQLite
- Error handling and reporting

## Implementation Details

### Temporary File Management
- Encrypted databases are extracted to temporary files
- Temporary files are automatically cleaned up after use
- No user intervention required

### Security Considerations
- Encryption keys are kept in memory only
- Decrypted databases are saved to case-specific directories
- Original encrypted databases remain unchanged in ZIP

### Performance
- Decryption happens once per query/operation
- No caching of decrypted databases (for security)
- Minimal memory footprint (streaming processing)

## Related Documentation

- [CLAUDE.md](../CLAUDE.md) - Complete project documentation
- [Core API Reference](../src/yaft/core/api.py) - Core API source code
- [Example Plugin](../examples/sqlcipher_example_plugin.py) - Working example

## References

- [SQLCipher Official Documentation](https://www.zetetic.net/sqlcipher/)
- [sqlcipher3 Python Package](https://pypi.org/project/sqlcipher3/)
- [Encrypted SQLite Databases with Python and SQLCipher](https://charlesleifer.com/blog/encrypted-sqlite-databases-with-python-and-sqlcipher/)
- [Recovering SQLCipher encrypted data with Frida](https://ackcent.com/recovering-sqlcipher-encrypted-data-with-frida/)
