"""
Tests for SQLCipher encrypted database functionality in Core API.

These tests verify that the Core API can query and decrypt SQLCipher-encrypted
SQLite databases, which is common in mobile forensics (WhatsApp, iOS apps, etc.).
"""

import pytest
import zipfile
from pathlib import Path

from yaft.core.api import CoreAPI


# Check if sqlcipher3 is installed
try:
    from sqlcipher3 import dbapi2 as sqlcipher
    SQLCIPHER_AVAILABLE = True
except ImportError:
    SQLCIPHER_AVAILABLE = False


@pytest.fixture
def core_api(tmp_path):
    """Create a CoreAPI instance with temporary output directory."""
    api = CoreAPI()
    api.base_output_dir = tmp_path / "yaft_output"
    api.base_output_dir.mkdir(parents=True, exist_ok=True)
    return api


@pytest.fixture
def encrypted_db_path(tmp_path):
    """Create an encrypted SQLCipher database for testing."""
    if not SQLCIPHER_AVAILABLE:
        pytest.skip("sqlcipher3 not installed")

    db_path = tmp_path / "encrypted_test.db"

    # Create encrypted database
    conn = sqlcipher.connect(str(db_path))
    cursor = conn.cursor()

    # Set encryption key
    cursor.execute("PRAGMA key = 'test_password_123'")

    # Create test table and insert data
    cursor.execute("""
        CREATE TABLE users (
            id INTEGER PRIMARY KEY,
            username TEXT,
            email TEXT,
            created_at INTEGER
        )
    """)

    test_data = [
        (1, "alice", "alice@example.com", 1234567890),
        (2, "bob", "bob@example.com", 1234567900),
        (3, "charlie", "charlie@example.com", 1234567910),
    ]

    cursor.executemany(
        "INSERT INTO users (id, username, email, created_at) VALUES (?, ?, ?, ?)",
        test_data
    )

    conn.commit()
    conn.close()

    return db_path


@pytest.fixture
def encrypted_db_v3_path(tmp_path):
    """Create an encrypted SQLCipher v3 database for testing backward compatibility."""
    if not SQLCIPHER_AVAILABLE:
        pytest.skip("sqlcipher3 not installed")

    db_path = tmp_path / "encrypted_v3_test.db"

    # Create encrypted database with SQLCipher v3 settings
    conn = sqlcipher.connect(str(db_path))
    cursor = conn.cursor()

    # Set encryption key
    cursor.execute("PRAGMA key = 'test_password_v3'")

    # Set SQLCipher v3 compatibility
    cursor.execute("PRAGMA cipher_compatibility = 3")

    # Create test table
    cursor.execute("""
        CREATE TABLE messages (
            id INTEGER PRIMARY KEY,
            sender TEXT,
            content TEXT,
            timestamp INTEGER
        )
    """)

    test_data = [
        (1, "alice", "Hello World", 1600000000),
        (2, "bob", "Hi there!", 1600000010),
    ]

    cursor.executemany(
        "INSERT INTO messages (id, sender, content, timestamp) VALUES (?, ?, ?, ?)",
        test_data
    )

    conn.commit()
    conn.close()

    return db_path


@pytest.fixture
def mock_zip_with_encrypted_db(tmp_path, encrypted_db_path):
    """Create a ZIP file containing an encrypted SQLCipher database."""
    if not SQLCIPHER_AVAILABLE:
        pytest.skip("sqlcipher3 not installed")

    zip_path = tmp_path / "encrypted_extraction.zip"

    with zipfile.ZipFile(zip_path, "w") as zf:
        # Add encrypted database to ZIP
        zf.write(encrypted_db_path, "data/data/com.example.app/databases/app.db")

    return zip_path


@pytest.fixture
def mock_zip_with_encrypted_db_v3(tmp_path, encrypted_db_v3_path):
    """Create a ZIP file containing a SQLCipher v3 encrypted database."""
    if not SQLCIPHER_AVAILABLE:
        pytest.skip("sqlcipher3 not installed")

    zip_path = tmp_path / "encrypted_v3_extraction.zip"

    with zipfile.ZipFile(zip_path, "w") as zf:
        # Add encrypted database to ZIP (iOS-style path)
        zf.write(encrypted_db_v3_path, "private/var/mobile/Containers/Data/Application/ABC123/Documents/messages.db")

    return zip_path


@pytest.mark.skipif(not SQLCIPHER_AVAILABLE, reason="sqlcipher3 not installed")
class TestSQLCipherQueries:
    """Test querying encrypted SQLCipher databases from ZIP archives."""

    def test_query_encrypted_database(self, core_api, mock_zip_with_encrypted_db):
        """Test querying an encrypted database with correct key."""
        core_api.set_zip_file(mock_zip_with_encrypted_db)

        # Query encrypted database
        results = core_api.query_sqlcipher_from_zip(
            "data/data/com.example.app/databases/app.db",
            "test_password_123",
            "SELECT username, email FROM users ORDER BY id"
        )

        assert len(results) == 3
        assert results[0] == ("alice", "alice@example.com")
        assert results[1] == ("bob", "bob@example.com")
        assert results[2] == ("charlie", "charlie@example.com")

    def test_query_encrypted_database_with_params(self, core_api, mock_zip_with_encrypted_db):
        """Test querying encrypted database with parameterized query."""
        core_api.set_zip_file(mock_zip_with_encrypted_db)

        results = core_api.query_sqlcipher_from_zip(
            "data/data/com.example.app/databases/app.db",
            "test_password_123",
            "SELECT username, email FROM users WHERE id = ?",
            params=(2,)
        )

        assert len(results) == 1
        assert results[0] == ("bob", "bob@example.com")

    def test_query_encrypted_database_dict(self, core_api, mock_zip_with_encrypted_db):
        """Test querying encrypted database and returning dictionaries."""
        core_api.set_zip_file(mock_zip_with_encrypted_db)

        results = core_api.query_sqlcipher_from_zip_dict(
            "data/data/com.example.app/databases/app.db",
            "test_password_123",
            "SELECT id, username, email FROM users WHERE id <= ?",
            params=(2,)
        )

        assert len(results) == 2
        assert results[0]["username"] == "alice"
        assert results[0]["email"] == "alice@example.com"
        assert results[1]["username"] == "bob"
        assert results[1]["email"] == "bob@example.com"

    def test_query_encrypted_database_wrong_key(self, core_api, mock_zip_with_encrypted_db):
        """Test that querying with wrong key raises ValueError."""
        core_api.set_zip_file(mock_zip_with_encrypted_db)

        with pytest.raises(ValueError) as exc_info:
            core_api.query_sqlcipher_from_zip(
                "data/data/com.example.app/databases/app.db",
                "wrong_password",
                "SELECT * FROM users"
            )

        assert "Failed to decrypt database" in str(exc_info.value)

    def test_query_encrypted_database_v3_compatibility(self, core_api, mock_zip_with_encrypted_db_v3):
        """Test querying SQLCipher v3 database with cipher_version parameter."""
        core_api.set_zip_file(mock_zip_with_encrypted_db_v3)

        results = core_api.query_sqlcipher_from_zip(
            "private/var/mobile/Containers/Data/Application/ABC123/Documents/messages.db",
            "test_password_v3",
            "SELECT sender, content FROM messages ORDER BY id",
            cipher_version=3
        )

        assert len(results) == 2
        assert results[0] == ("alice", "Hello World")
        assert results[1] == ("bob", "Hi there!")

    def test_query_encrypted_database_fallback_query(self, core_api, mock_zip_with_encrypted_db):
        """Test fallback query mechanism with encrypted database."""
        core_api.set_zip_file(mock_zip_with_encrypted_db)

        # Primary query will fail (no 'status' column), fallback should succeed
        results = core_api.query_sqlcipher_from_zip(
            "data/data/com.example.app/databases/app.db",
            "test_password_123",
            "SELECT username, status FROM users",  # Will fail
            fallback_query="SELECT username, 'active' as status FROM users"  # Will succeed
        )

        assert len(results) == 3
        assert results[0][1] == "active"  # Fallback query default value

    def test_query_encrypted_database_no_zip_loaded(self, core_api):
        """Test that querying without ZIP loaded raises RuntimeError."""
        with pytest.raises(RuntimeError) as exc_info:
            core_api.query_sqlcipher_from_zip(
                "databases/app.db",
                "password",
                "SELECT * FROM users"
            )

        assert "No ZIP file loaded" in str(exc_info.value)

    def test_query_encrypted_database_file_not_found(self, core_api, mock_zip_with_encrypted_db):
        """Test that querying non-existent file raises KeyError."""
        core_api.set_zip_file(mock_zip_with_encrypted_db)

        with pytest.raises(KeyError):
            core_api.query_sqlcipher_from_zip(
                "nonexistent/database.db",
                "password",
                "SELECT * FROM users"
            )


@pytest.mark.skipif(not SQLCIPHER_AVAILABLE, reason="sqlcipher3 not installed")
class TestSQLCipherDecryption:
    """Test decrypting SQLCipher databases to plain SQLite format."""

    def test_decrypt_database(self, core_api, mock_zip_with_encrypted_db, tmp_path):
        """Test decrypting an encrypted database to plain SQLite."""
        core_api.set_zip_file(mock_zip_with_encrypted_db)

        output_path = tmp_path / "decrypted" / "app.db"

        # Decrypt the database
        result_path = core_api.decrypt_sqlcipher_database(
            "data/data/com.example.app/databases/app.db",
            "test_password_123",
            output_path
        )

        assert result_path == output_path
        assert output_path.exists()

        # Verify we can query the decrypted database with standard sqlite3
        import sqlite3
        conn = sqlite3.connect(str(output_path))
        cursor = conn.cursor()
        cursor.execute("SELECT username FROM users ORDER BY id")
        results = cursor.fetchall()
        conn.close()

        assert len(results) == 3
        assert results[0][0] == "alice"
        assert results[1][0] == "bob"
        assert results[2][0] == "charlie"

    def test_decrypt_database_v3_compatibility(self, core_api, mock_zip_with_encrypted_db_v3, tmp_path):
        """Test decrypting SQLCipher v3 database with cipher_version parameter."""
        core_api.set_zip_file(mock_zip_with_encrypted_db_v3)

        output_path = tmp_path / "decrypted_v3" / "messages.db"

        # Decrypt the v3 database
        result_path = core_api.decrypt_sqlcipher_database(
            "private/var/mobile/Containers/Data/Application/ABC123/Documents/messages.db",
            "test_password_v3",
            output_path,
            cipher_version=3
        )

        assert result_path == output_path
        assert output_path.exists()

        # Verify decrypted database
        import sqlite3
        conn = sqlite3.connect(str(output_path))
        cursor = conn.cursor()
        cursor.execute("SELECT content FROM messages ORDER BY id")
        results = cursor.fetchall()
        conn.close()

        assert len(results) == 2
        assert results[0][0] == "Hello World"
        assert results[1][0] == "Hi there!"

    def test_decrypt_database_wrong_key(self, core_api, mock_zip_with_encrypted_db, tmp_path):
        """Test that decrypting with wrong key raises ValueError."""
        core_api.set_zip_file(mock_zip_with_encrypted_db)

        output_path = tmp_path / "decrypted" / "failed.db"

        with pytest.raises(ValueError) as exc_info:
            core_api.decrypt_sqlcipher_database(
                "data/data/com.example.app/databases/app.db",
                "wrong_password",
                output_path
            )

        assert "Failed to decrypt database" in str(exc_info.value)

    def test_decrypt_database_creates_output_dir(self, core_api, mock_zip_with_encrypted_db, tmp_path):
        """Test that decrypt_sqlcipher_database creates output directory if needed."""
        core_api.set_zip_file(mock_zip_with_encrypted_db)

        # Use nested directory that doesn't exist
        output_path = tmp_path / "nested" / "directories" / "decrypted.db"

        result_path = core_api.decrypt_sqlcipher_database(
            "data/data/com.example.app/databases/app.db",
            "test_password_123",
            output_path
        )

        assert result_path.exists()
        assert result_path.parent.exists()


class TestSQLCipherImportError:
    """Test behavior when sqlcipher3 is not installed."""

    def test_query_without_sqlcipher_installed(self, core_api, tmp_path, monkeypatch):
        """Test that helpful error is raised when sqlcipher3 not installed."""
        # Create a mock ZIP file
        zip_path = tmp_path / "test.zip"
        with zipfile.ZipFile(zip_path, "w") as zf:
            zf.writestr("database.db", b"fake data")

        core_api.set_zip_file(zip_path)

        # Mock the import to simulate sqlcipher3 not being installed
        def mock_import(name, *args, **kwargs):
            if name == "sqlcipher3":
                raise ImportError("No module named 'sqlcipher3'")
            return __import__(name, *args, **kwargs)

        monkeypatch.setattr("builtins.__import__", mock_import)

        with pytest.raises(ImportError) as exc_info:
            core_api.query_sqlcipher_from_zip(
                "database.db",
                "password",
                "SELECT * FROM users"
            )

        assert "sqlcipher3" in str(exc_info.value).lower()
        assert "uv pip install" in str(exc_info.value)

    def test_decrypt_without_sqlcipher_installed(self, core_api, tmp_path, monkeypatch):
        """Test that helpful error is raised when sqlcipher3 not installed for decryption."""
        # Create a mock ZIP file
        zip_path = tmp_path / "test.zip"
        with zipfile.ZipFile(zip_path, "w") as zf:
            zf.writestr("database.db", b"fake data")

        core_api.set_zip_file(zip_path)

        # Mock the import to simulate sqlcipher3 not being installed
        def mock_import(name, *args, **kwargs):
            if name == "sqlcipher3":
                raise ImportError("No module named 'sqlcipher3'")
            return __import__(name, *args, **kwargs)

        monkeypatch.setattr("builtins.__import__", mock_import)

        output_path = tmp_path / "decrypted.db"

        with pytest.raises(ImportError) as exc_info:
            core_api.decrypt_sqlcipher_database(
                "database.db",
                "password",
                output_path
            )

        assert "sqlcipher3" in str(exc_info.value).lower()
        assert "uv pip install" in str(exc_info.value)


@pytest.mark.skipif(not SQLCIPHER_AVAILABLE, reason="sqlcipher3 not installed")
class TestSQLCipherForensicUseCases:
    """Test real-world forensic analysis scenarios with encrypted databases."""

    def test_whatsapp_style_encrypted_db(self, core_api, tmp_path):
        """Test analyzing a WhatsApp-style encrypted message database."""
        # Create a WhatsApp-style encrypted database
        db_path = tmp_path / "msgstore.db"
        conn = sqlcipher.connect(str(db_path))
        cursor = conn.cursor()
        cursor.execute("PRAGMA key = 'whatsapp_key_example'")

        # Create WhatsApp-like schema
        cursor.execute("""
            CREATE TABLE messages (
                _id INTEGER PRIMARY KEY,
                key_remote_jid TEXT,
                key_from_me INTEGER,
                data TEXT,
                timestamp INTEGER,
                media_wa_type INTEGER
            )
        """)

        test_messages = [
            (1, "+1234567890@s.whatsapp.net", 0, "Hello, how are you?", 1609459200000, 0),
            (2, "+1234567890@s.whatsapp.net", 1, "I'm good, thanks!", 1609459210000, 0),
            (3, "+9876543210@s.whatsapp.net", 0, "Meeting at 3pm", 1609459220000, 0),
        ]

        cursor.executemany(
            "INSERT INTO messages (_id, key_remote_jid, key_from_me, data, timestamp, media_wa_type) VALUES (?, ?, ?, ?, ?, ?)",
            test_messages
        )
        conn.commit()
        conn.close()

        # Create ZIP with encrypted database
        zip_path = tmp_path / "whatsapp_backup.zip"
        with zipfile.ZipFile(zip_path, "w") as zf:
            zf.write(db_path, "data/data/com.whatsapp/databases/msgstore.db")

        # Load ZIP and query encrypted database
        core_api.set_zip_file(zip_path)

        results = core_api.query_sqlcipher_from_zip_dict(
            "data/data/com.whatsapp/databases/msgstore.db",
            "whatsapp_key_example",
            "SELECT key_remote_jid, data, timestamp FROM messages WHERE key_from_me = 0 ORDER BY timestamp"
        )

        assert len(results) == 2
        assert results[0]["data"] == "Hello, how are you?"
        assert results[1]["data"] == "Meeting at 3pm"

    def test_ios_app_encrypted_db(self, core_api, tmp_path):
        """Test analyzing an iOS app encrypted database."""
        # Create iOS-style encrypted database
        db_path = tmp_path / "app_data.db"
        conn = sqlcipher.connect(str(db_path))
        cursor = conn.cursor()
        cursor.execute("PRAGMA key = 'ios_app_key'")

        # Create app-like schema
        cursor.execute("""
            CREATE TABLE user_activity (
                id INTEGER PRIMARY KEY,
                activity_type TEXT,
                timestamp REAL,
                metadata TEXT
            )
        """)

        test_data = [
            (1, "login", 631152000.0, '{"device": "iPhone12"}'),
            (2, "search", 631152060.0, '{"query": "forensics"}'),
            (3, "logout", 631152120.0, '{"duration": 120}'),
        ]

        cursor.executemany(
            "INSERT INTO user_activity VALUES (?, ?, ?, ?)",
            test_data
        )
        conn.commit()
        conn.close()

        # Create iOS-style ZIP
        zip_path = tmp_path / "ios_backup.zip"
        with zipfile.ZipFile(zip_path, "w") as zf:
            zf.write(db_path, "private/var/mobile/Containers/Data/Application/ABC123/Library/app_data.db")

        # Query encrypted database
        core_api.set_zip_file(zip_path)

        results = core_api.query_sqlcipher_from_zip_dict(
            "private/var/mobile/Containers/Data/Application/ABC123/Library/app_data.db",
            "ios_app_key",
            "SELECT activity_type, timestamp FROM user_activity ORDER BY timestamp"
        )

        assert len(results) == 3
        assert results[0]["activity_type"] == "login"
        assert results[1]["activity_type"] == "search"
        assert results[2]["activity_type"] == "logout"
