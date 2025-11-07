"""Tests for CoreAPI."""

import plistlib
import sqlite3
import zipfile
from pathlib import Path

import pytest

from yaft.core.api import CoreAPI


def test_core_api_initialization(temp_dir):
    """Test CoreAPI initialization."""
    config_dir = temp_dir / "config"
    api = CoreAPI(config_dir=config_dir)

    assert api.config_dir == config_dir
    assert config_dir.exists()
    assert api.console is not None
    assert api.logger is not None


def test_get_config_path(core_api, temp_dir):
    """Test getting configuration file paths."""
    config_path = core_api.get_config_path("test.toml")

    expected_path = temp_dir / "config" / "test.toml"
    assert config_path == expected_path


def test_shared_data_operations(core_api):
    """Test shared data storage and retrieval."""
    # Set data
    core_api.set_shared_data("test_key", "test_value")
    assert core_api.get_shared_data("test_key") == "test_value"

    # Get with default
    assert core_api.get_shared_data("nonexistent", "default") == "default"

    # Clear specific key
    core_api.clear_shared_data("test_key")
    assert core_api.get_shared_data("test_key") is None

    # Set multiple and clear all
    core_api.set_shared_data("key1", "value1")
    core_api.set_shared_data("key2", "value2")
    core_api.clear_shared_data()
    assert core_api.get_shared_data("key1") is None
    assert core_api.get_shared_data("key2") is None


def test_file_operations(core_api, temp_dir):
    """Test file read/write operations."""
    test_file = temp_dir / "test.txt"
    test_content = "Hello, YAFT!"

    # Write file
    core_api.write_file(test_file, test_content)
    assert test_file.exists()

    # Read file
    content = core_api.read_file(test_file)
    assert content == test_content


def test_file_read_nonexistent(core_api, temp_dir):
    """Test reading a nonexistent file raises error."""
    nonexistent_file = temp_dir / "nonexistent.txt"

    with pytest.raises(FileNotFoundError):
        core_api.read_file(nonexistent_file)


def test_logging_methods(core_api, capsys):
    """Test logging methods don't raise errors."""
    # These should not raise exceptions
    core_api.log_info("Info message")
    core_api.log_warning("Warning message")
    core_api.log_error("Error message")
    core_api.log_debug("Debug message")


def test_print_methods(core_api, capsys):
    """Test print methods don't raise errors."""
    # These should not raise exceptions
    core_api.print_success("Success message")
    core_api.print_error("Error message")
    core_api.print_warning("Warning message")
    core_api.print_info("Info message")


# ========== ZIP File Handling Tests ==========


def test_set_zip_file(core_api, temp_dir):
    """Test setting a ZIP file."""
    zip_path = temp_dir / "test.zip"

    # Create a simple ZIP file
    with zipfile.ZipFile(zip_path, 'w') as zf:
        zf.writestr("test.txt", "test content")

    core_api.set_zip_file(zip_path)

    assert core_api.get_current_zip() == zip_path
    assert core_api._zip_handle is not None


def test_set_zip_file_nonexistent(core_api, temp_dir):
    """Test setting a nonexistent ZIP file raises error."""
    zip_path = temp_dir / "nonexistent.zip"

    with pytest.raises(FileNotFoundError):
        core_api.set_zip_file(zip_path)


def test_read_zip_file(core_api, temp_dir):
    """Test reading a file from ZIP."""
    zip_path = temp_dir / "test.zip"
    test_content = b"test content"

    with zipfile.ZipFile(zip_path, 'w') as zf:
        zf.writestr("test.txt", test_content)

    core_api.set_zip_file(zip_path)
    content = core_api.read_zip_file("test.txt")

    assert content == test_content


def test_read_zip_file_text(core_api, temp_dir):
    """Test reading a text file from ZIP."""
    zip_path = temp_dir / "test.zip"
    test_content = "test content"

    with zipfile.ZipFile(zip_path, 'w') as zf:
        zf.writestr("test.txt", test_content)

    core_api.set_zip_file(zip_path)
    content = core_api.read_zip_file_text("test.txt")

    assert content == test_content


def test_read_zip_file_not_found(core_api, temp_dir):
    """Test reading a nonexistent file from ZIP raises error."""
    zip_path = temp_dir / "test.zip"

    with zipfile.ZipFile(zip_path, 'w') as zf:
        zf.writestr("test.txt", "content")

    core_api.set_zip_file(zip_path)

    with pytest.raises(KeyError):
        core_api.read_zip_file("nonexistent.txt")


def test_read_zip_no_zip_loaded(core_api):
    """Test reading from ZIP without loading a ZIP file."""
    with pytest.raises(RuntimeError, match="No ZIP file loaded"):
        core_api.read_zip_file("test.txt")


def test_list_zip_contents(core_api, temp_dir):
    """Test listing ZIP contents."""
    zip_path = temp_dir / "test.zip"

    with zipfile.ZipFile(zip_path, 'w') as zf:
        zf.writestr("file1.txt", "content1")
        zf.writestr("file2.txt", "content2")
        zf.writestr("dir/file3.txt", "content3")

    core_api.set_zip_file(zip_path)
    files = core_api.list_zip_contents()

    assert len(files) == 3
    filenames = [f.filename for f in files]
    assert "file1.txt" in filenames
    assert "file2.txt" in filenames
    assert "dir/file3.txt" in filenames


def test_extract_zip_file(core_api, temp_dir):
    """Test extracting a single file from ZIP."""
    zip_path = temp_dir / "test.zip"
    output_dir = temp_dir / "output"

    with zipfile.ZipFile(zip_path, 'w') as zf:
        zf.writestr("test.txt", "test content")

    core_api.set_zip_file(zip_path)
    extracted_path = core_api.extract_zip_file("test.txt", output_dir)

    assert extracted_path.exists()
    assert extracted_path.read_text() == "test content"


def test_extract_all_zip(core_api, temp_dir):
    """Test extracting all files from ZIP."""
    zip_path = temp_dir / "test.zip"
    output_dir = temp_dir / "output"

    with zipfile.ZipFile(zip_path, 'w') as zf:
        zf.writestr("file1.txt", "content1")
        zf.writestr("file2.txt", "content2")

    core_api.set_zip_file(zip_path)
    result_dir = core_api.extract_all_zip(output_dir)

    assert (output_dir / "file1.txt").exists()
    assert (output_dir / "file2.txt").exists()
    assert result_dir == output_dir


def test_close_zip(core_api, temp_dir):
    """Test closing a ZIP file."""
    zip_path = temp_dir / "test.zip"

    with zipfile.ZipFile(zip_path, 'w') as zf:
        zf.writestr("test.txt", "content")

    core_api.set_zip_file(zip_path)
    assert core_api._zip_handle is not None

    core_api.close_zip()
    assert core_api._zip_handle is None
    assert core_api._current_zip is None


# ========== Plist Parsing Tests ==========


def test_parse_plist(core_api):
    """Test parsing plist from bytes."""
    plist_data = {"key1": "value1", "key2": 123, "key3": ["item1", "item2"]}
    plist_bytes = plistlib.dumps(plist_data)

    result = core_api.parse_plist(plist_bytes)

    assert result == plist_data


def test_parse_plist_invalid(core_api):
    """Test parsing invalid plist data raises error."""
    invalid_data = b"not a valid plist"

    with pytest.raises(Exception):
        core_api.parse_plist(invalid_data)


def test_read_plist_from_zip(core_api, temp_dir):
    """Test reading and parsing plist from ZIP."""
    zip_path = temp_dir / "test.zip"
    plist_data = {"app_name": "TestApp", "version": "1.0.0", "features": ["feature1", "feature2"]}
    plist_bytes = plistlib.dumps(plist_data)

    with zipfile.ZipFile(zip_path, 'w') as zf:
        zf.writestr("Info.plist", plist_bytes)

    core_api.set_zip_file(zip_path)
    result = core_api.read_plist_from_zip("Info.plist")

    assert result == plist_data
    assert result["app_name"] == "TestApp"
    assert result["version"] == "1.0.0"
    assert len(result["features"]) == 2


def test_read_plist_from_zip_not_found(core_api, temp_dir):
    """Test reading nonexistent plist from ZIP raises error."""
    zip_path = temp_dir / "test.zip"

    with zipfile.ZipFile(zip_path, 'w') as zf:
        zf.writestr("other.txt", "content")

    core_api.set_zip_file(zip_path)

    with pytest.raises(KeyError):
        core_api.read_plist_from_zip("Info.plist")


# ========== SQLite Query Tests ==========


def test_query_sqlite_from_zip(core_api, temp_dir):
    """Test querying SQLite database from ZIP."""
    zip_path = temp_dir / "test.zip"
    db_path = temp_dir / "test.db"

    # Create a SQLite database
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    cursor.execute("CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT, age INTEGER)")
    cursor.execute("INSERT INTO users (name, age) VALUES (?, ?)", ("Alice", 30))
    cursor.execute("INSERT INTO users (name, age) VALUES (?, ?)", ("Bob", 25))
    conn.commit()
    conn.close()

    # Add database to ZIP
    with zipfile.ZipFile(zip_path, 'w') as zf:
        zf.write(db_path, "test.db")

    core_api.set_zip_file(zip_path)
    results = core_api.query_sqlite_from_zip("test.db", "SELECT name, age FROM users ORDER BY name")

    assert len(results) == 2
    assert results[0] == ("Alice", 30)
    assert results[1] == ("Bob", 25)


def test_query_sqlite_from_zip_with_params(core_api, temp_dir):
    """Test querying SQLite with parameters."""
    zip_path = temp_dir / "test.zip"
    db_path = temp_dir / "test.db"

    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    cursor.execute("CREATE TABLE products (id INTEGER PRIMARY KEY, name TEXT, price REAL)")
    cursor.execute("INSERT INTO products (name, price) VALUES (?, ?)", ("Product A", 10.99))
    cursor.execute("INSERT INTO products (name, price) VALUES (?, ?)", ("Product B", 20.99))
    cursor.execute("INSERT INTO products (name, price) VALUES (?, ?)", ("Product C", 5.99))
    conn.commit()
    conn.close()

    with zipfile.ZipFile(zip_path, 'w') as zf:
        zf.write(db_path, "products.db")

    core_api.set_zip_file(zip_path)
    results = core_api.query_sqlite_from_zip(
        "products.db",
        "SELECT name, price FROM products WHERE price > ? ORDER BY price",
        params=(10.0,)
    )

    assert len(results) == 2
    assert results[0][0] == "Product A"
    assert results[1][0] == "Product B"


def test_query_sqlite_from_zip_with_fallback(core_api, temp_dir):
    """Test querying SQLite with fallback query."""
    zip_path = temp_dir / "test.zip"
    db_path = temp_dir / "test.db"

    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    cursor.execute("CREATE TABLE old_schema (id INTEGER PRIMARY KEY, name TEXT)")
    cursor.execute("INSERT INTO old_schema (name) VALUES (?)", ("Item 1",))
    conn.commit()
    conn.close()

    with zipfile.ZipFile(zip_path, 'w') as zf:
        zf.write(db_path, "schema.db")

    core_api.set_zip_file(zip_path)

    # Primary query fails (column doesn't exist), fallback succeeds
    results = core_api.query_sqlite_from_zip(
        "schema.db",
        "SELECT id, name, new_column FROM old_schema",  # Will fail
        fallback_query="SELECT id, name FROM old_schema"  # Will succeed
    )

    assert len(results) == 1
    assert results[0] == (1, "Item 1")


def test_query_sqlite_from_zip_dict(core_api, temp_dir):
    """Test querying SQLite and getting results as dictionaries."""
    zip_path = temp_dir / "test.zip"
    db_path = temp_dir / "test.db"

    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    cursor.execute("CREATE TABLE books (id INTEGER PRIMARY KEY, title TEXT, author TEXT, year INTEGER)")
    cursor.execute("INSERT INTO books (title, author, year) VALUES (?, ?, ?)", ("Book 1", "Author A", 2020))
    cursor.execute("INSERT INTO books (title, author, year) VALUES (?, ?, ?)", ("Book 2", "Author B", 2021))
    conn.commit()
    conn.close()

    with zipfile.ZipFile(zip_path, 'w') as zf:
        zf.write(db_path, "books.db")

    core_api.set_zip_file(zip_path)
    results = core_api.query_sqlite_from_zip_dict("books.db", "SELECT title, author, year FROM books ORDER BY year")

    assert len(results) == 2
    assert results[0]["title"] == "Book 1"
    assert results[0]["author"] == "Author A"
    assert results[0]["year"] == 2020
    assert results[1]["title"] == "Book 2"


def test_query_sqlite_from_zip_db_not_found(core_api, temp_dir):
    """Test querying nonexistent database from ZIP."""
    zip_path = temp_dir / "test.zip"

    with zipfile.ZipFile(zip_path, 'w') as zf:
        zf.writestr("other.txt", "content")

    core_api.set_zip_file(zip_path)

    with pytest.raises(KeyError):
        core_api.query_sqlite_from_zip("nonexistent.db", "SELECT * FROM table")


# ========== Case Identifier Tests ==========


def test_validate_examiner_id(core_api):
    """Test Examiner ID validation."""
    # Valid formats
    assert core_api.validate_examiner_id("john_doe") is True
    assert core_api.validate_examiner_id("examiner-123") is True
    assert core_api.validate_examiner_id("JD") is True  # Minimum length
    assert core_api.validate_examiner_id("A" * 50) is True  # Maximum length
    assert core_api.validate_examiner_id("user123") is True
    assert core_api.validate_examiner_id("Test_User-01") is True

    # Invalid formats
    assert core_api.validate_examiner_id("j") is False  # Too short
    assert core_api.validate_examiner_id("A" * 51) is False  # Too long
    assert core_api.validate_examiner_id("user@mail") is False  # Invalid character @
    assert core_api.validate_examiner_id("user name") is False  # Space not allowed
    assert core_api.validate_examiner_id("user.name") is False  # Dot not allowed


def test_validate_case_id(core_api):
    """Test Case ID validation."""
    # Valid formats
    assert core_api.validate_case_id("CASE2024-01") is True
    assert core_api.validate_case_id("K2024001-01") is True
    assert core_api.validate_case_id("2024-001") is True
    assert core_api.validate_case_id("ABCD-99") is True

    # Invalid formats
    assert core_api.validate_case_id("case2024-01") is False  # Lowercase not allowed
    assert core_api.validate_case_id("ABC-01") is False  # First part too short
    assert core_api.validate_case_id("CASE2024-1") is False  # Second part too short
    assert core_api.validate_case_id("CASE2024") is False  # Missing dash and suffix
    assert core_api.validate_case_id("CASE-2024-01") is False  # Too many dashes


def test_validate_evidence_id(core_api):
    """Test Evidence ID validation."""
    # Valid formats
    assert core_api.validate_evidence_id("BG123456-1") is True
    assert core_api.validate_evidence_id("EV123456-01") is True
    assert core_api.validate_evidence_id("ITEM1234-1") is True
    assert core_api.validate_evidence_id("AB1234-99") is True

    # Invalid formats
    assert core_api.validate_evidence_id("bg123456-1") is False  # Lowercase not allowed
    assert core_api.validate_evidence_id("A123456-1") is False  # Letter part too short
    assert core_api.validate_evidence_id("ABCDE123456-1") is False  # Letter part too long
    assert core_api.validate_evidence_id("BG123-1") is False  # Number part too short
    assert core_api.validate_evidence_id("BG123456-123") is False  # Suffix too long
    assert core_api.validate_evidence_id("BG123456") is False  # Missing dash and suffix


def test_set_and_get_case_identifiers(core_api):
    """Test setting and getting case identifiers."""
    core_api.set_case_identifiers("examiner01", "CASE2024-01", "BG999888-7")

    examiner, case, evidence = core_api.get_case_identifiers()

    assert examiner == "examiner01"
    assert case == "CASE2024-01"
    assert evidence == "BG999888-7"


def test_set_case_identifiers_normalization(core_api):
    """Test case identifier normalization."""
    # Case ID and Evidence ID should be uppercase
    core_api.set_case_identifiers("john_doe", "case2024-01", "bg999888-7")

    examiner, case, evidence = core_api.get_case_identifiers()

    assert examiner == "john_doe"  # Kept as-is
    assert case == "CASE2024-01"  # Normalized to uppercase
    assert evidence == "BG999888-7"  # Normalized to uppercase


def test_set_case_identifiers_invalid(core_api):
    """Test setting invalid case identifiers raises errors."""
    with pytest.raises(ValueError, match="Invalid Examiner ID"):
        core_api.set_case_identifiers("x", "CASE2024-01", "BG123456-1")

    with pytest.raises(ValueError, match="Invalid Case ID"):
        core_api.set_case_identifiers("examiner01", "invalid", "BG123456-1")

    with pytest.raises(ValueError, match="Invalid Evidence ID"):
        core_api.set_case_identifiers("examiner01", "CASE2024-01", "invalid")


def test_get_case_output_dir_with_identifiers(core_api):
    """Test getting case-based output directory."""
    core_api.set_case_identifiers("examiner01", "CASE2024-01", "BG999888-7")

    # Base directory
    base_dir = core_api.get_case_output_dir()
    assert base_dir.parts[-3:] == ("yaft_output", "CASE2024-01", "BG999888-7")

    # With subdirectory
    reports_dir = core_api.get_case_output_dir("reports")
    assert reports_dir.parts[-4:] == ("yaft_output", "CASE2024-01", "BG999888-7", "reports")

    ios_dir = core_api.get_case_output_dir("ios_extractions")
    assert ios_dir.parts[-4:] == ("yaft_output", "CASE2024-01", "BG999888-7", "ios_extractions")


def test_get_case_output_dir_without_identifiers(core_api):
    """Test getting output directory without case identifiers."""
    # Without case identifiers, should fall back to default
    base_dir = core_api.get_case_output_dir()
    assert base_dir.parts[-1] == "yaft_output"
    assert "CASE" not in str(base_dir)

    reports_dir = core_api.get_case_output_dir("reports")
    assert reports_dir.parts[-2:] == ("yaft_output", "reports")
