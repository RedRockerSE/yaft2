"""
Tests for iOS WAL Strings Plugin
"""

import pytest
import zipfile
from pathlib import Path

from yaft.core.api import CoreAPI
from plugins.ios_wal_strings import iOSwalStringsPlugin


@pytest.fixture
def core_api(tmp_path):
    """Create CoreAPI instance with temporary output directory."""
    api = CoreAPI()
    api.base_output_dir = tmp_path / "yaft_output"
    api.base_output_dir.mkdir(parents=True, exist_ok=True)
    return api


@pytest.fixture
def plugin(core_api):
    """Create plugin instance."""
    return iOSwalStringsPlugin(core_api)


@pytest.fixture
def mock_zip_with_wal_files(tmp_path):
    """Create mock ZIP with WAL and journal files containing ASCII strings."""
    zip_path = tmp_path / "ios_extraction.zip"

    # Create mock WAL file with ASCII strings
    wal_content = (
        b"Binary data \x00\x01\x02"
        b"username@example.com"
        b"\x00\x00\x00"
        b"SELECT * FROM users"
        b"\xFF\xFE"
        b"https://example.com/api/endpoint"
        b"\x00\x00"
        b"Jane Doe"
        b"\x01\x02\x03"
    )

    # Create mock journal file with different strings
    journal_content = (
        b"\x00\x00\x00"
        b"INSERT INTO messages"
        b"\xFF\xFE\xFD"
        b"secret_password_123"
        b"\x00"
        b"2024-01-15 10:30:00"
        b"\x01\x02"
    )

    # Write to temp files first
    wal_file = tmp_path / "database.db-wal"
    journal_file = tmp_path / "data.db-journal"

    wal_file.write_bytes(wal_content)
    journal_file.write_bytes(journal_content)

    # Create ZIP with filesystem1/ prefix (Cellebrite iOS format)
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.write(wal_file, "filesystem1/private/var/mobile/Library/database.db-wal")
        zf.write(journal_file, "filesystem1/private/var/mobile/data.db-journal")

    return zip_path


@pytest.fixture
def mock_zip_graykey(tmp_path):
    """Create mock ZIP in GrayKey format (no prefix)."""
    zip_path = tmp_path / "graykey_extraction.zip"

    # Create WAL file
    wal_content = b"Test string data\x00\x00Another test"

    wal_file = tmp_path / "app.db-wal"
    wal_file.write_bytes(wal_content)

    # Create ZIP without prefix (GrayKey format)
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.write(wal_file, "private/var/mobile/Containers/Data/app.db-wal")

    return zip_path


@pytest.fixture
def mock_zip_empty(tmp_path):
    """Create mock ZIP with empty WAL file."""
    zip_path = tmp_path / "empty.zip"

    # Create empty WAL file
    wal_file = tmp_path / "empty.db-wal"
    wal_file.write_bytes(b"")

    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.write(wal_file, "filesystem1/empty.db-wal")

    return zip_path


def test_plugin_metadata(plugin):
    """Test plugin metadata."""
    assert plugin.metadata.name == "iOSwalStringsPlugin"
    assert plugin.metadata.version == "1.0.0"
    assert "WAL" in plugin.metadata.description
    assert plugin.metadata.author == "YaFT (ported from iLEAPP)"
    assert "ios" in plugin.metadata.target_os


def test_plugin_initialization(plugin):
    """Test plugin initialization."""
    plugin.initialize()
    assert plugin.extraction_type == "unknown"
    assert plugin.zip_prefix == ""
    assert plugin.extracted_strings == []
    assert plugin.errors == []


def test_no_zip_loaded(plugin):
    """Test execution without ZIP file loaded."""
    result = plugin.execute()

    assert result["success"] is False
    assert "error" in result
    assert "No ZIP file loaded" in result["error"]


def test_no_wal_files(core_api, plugin, tmp_path):
    """Test execution with ZIP containing no WAL/journal files."""
    # Create ZIP with no WAL/journal files
    zip_path = tmp_path / "no_wal.zip"

    test_file = tmp_path / "test.txt"
    test_file.write_text("Test data")

    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.write(test_file, "filesystem1/test.txt")

    core_api.set_zip_file(zip_path)

    result = plugin.execute()

    assert result["success"] is True
    assert result["files_processed"] == 0
    assert "No WAL or journal files found" in result["message"]


def test_extract_strings_cellebrite(core_api, plugin, mock_zip_with_wal_files):
    """Test string extraction from Cellebrite format ZIP."""
    core_api.set_zip_file(mock_zip_with_wal_files)

    result = plugin.execute()

    assert result["success"] is True
    assert result["files_processed"] == 2  # 1 WAL + 1 journal
    assert result["total_unique_strings"] > 0
    assert Path(result["report_path"]).exists()
    assert Path(result["json_path"]).exists()

    # Verify extracted strings data
    assert len(plugin.extracted_strings) == 2

    # Check that strings were found
    total_strings = sum(item["unique_strings_count"] for item in plugin.extracted_strings)
    assert total_strings > 0

    # Verify output files were created
    for item in plugin.extracted_strings:
        output_path = Path(item["output_file"])
        assert output_path.exists()
        assert output_path.stat().st_size > 0

        # Read and verify content
        content = output_path.read_text(encoding='utf-8')
        assert len(content) > 0


def test_extract_strings_graykey(core_api, plugin, mock_zip_graykey):
    """Test string extraction from GrayKey format ZIP."""
    core_api.set_zip_file(mock_zip_graykey)

    result = plugin.execute()

    assert result["success"] is True
    assert result["files_processed"] == 1
    assert result["total_unique_strings"] > 0


def test_empty_wal_file(core_api, plugin, mock_zip_empty):
    """Test handling of empty WAL file."""
    core_api.set_zip_file(mock_zip_empty)

    result = plugin.execute()

    # Should succeed but find no strings
    assert result["success"] is True
    assert result["files_processed"] == 0


def test_string_deduplication(core_api, plugin, tmp_path):
    """Test that duplicate strings are deduplicated."""
    zip_path = tmp_path / "duplicates.zip"

    # Create WAL file with duplicate strings
    wal_content = (
        b"test_string"
        b"\x00\x00"
        b"test_string"  # Duplicate
        b"\x00"
        b"another_string"
        b"\x00\x00"
        b"test_string"  # Another duplicate
    )

    wal_file = tmp_path / "test.db-wal"
    wal_file.write_bytes(wal_content)

    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.write(wal_file, "filesystem1/test.db-wal")

    core_api.set_zip_file(zip_path)

    result = plugin.execute()

    assert result["success"] is True
    assert result["files_processed"] == 1

    # Verify deduplication worked
    # Should find "test_string" and "another_string" (2 unique strings)
    assert plugin.extracted_strings[0]["unique_strings_count"] == 2


def test_minimum_string_length(core_api, plugin, tmp_path):
    """Test that strings less than 4 characters are ignored."""
    zip_path = tmp_path / "short_strings.zip"

    # Create WAL file with short strings
    wal_content = (
        b"ab"  # 2 chars - should be ignored
        b"\x00"
        b"abc"  # 3 chars - should be ignored
        b"\x00"
        b"abcd"  # 4 chars - should be extracted
        b"\x00"
        b"abcde"  # 5 chars - should be extracted
    )

    wal_file = tmp_path / "test.db-wal"
    wal_file.write_bytes(wal_content)

    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.write(wal_file, "filesystem1/test.db-wal")

    core_api.set_zip_file(zip_path)

    result = plugin.execute()

    assert result["success"] is True
    assert result["files_processed"] == 1

    # Should find only strings with 4+ characters
    assert plugin.extracted_strings[0]["unique_strings_count"] == 2


def test_report_generation(core_api, plugin, mock_zip_with_wal_files):
    """Test report generation."""
    core_api.set_zip_file(mock_zip_with_wal_files)

    result = plugin.execute()

    assert result["success"] is True

    # Verify report exists
    report_path = Path(result["report_path"])
    assert report_path.exists()
    assert report_path.suffix == ".md"

    # Read and verify report content
    report_content = report_path.read_text(encoding='utf-8')
    assert "iOS SQLite WAL & Journal Strings Extraction" in report_content
    assert "Summary" in report_content
    assert "Extracted Files" in report_content
    assert "Files Processed:" in report_content


def test_json_export(core_api, plugin, mock_zip_with_wal_files):
    """Test JSON export."""
    core_api.set_zip_file(mock_zip_with_wal_files)

    result = plugin.execute()

    assert result["success"] is True

    # Verify JSON exists
    json_path = Path(result["json_path"])
    assert json_path.exists()
    assert json_path.suffix == ".json"

    # Read and verify JSON content
    import json
    with open(json_path, 'r', encoding='utf-8') as f:
        export_data = json.load(f)

    # The export_plugin_data_to_json wraps data in a "data" field
    assert "data" in export_data
    data = export_data["data"]

    assert "extracted_files" in data
    assert "summary" in data
    assert len(data["extracted_files"]) == 2
    assert data["summary"]["total_files_processed"] == 2


def test_cleanup(plugin):
    """Test plugin cleanup."""
    plugin.cleanup()
    # Should not raise any errors
