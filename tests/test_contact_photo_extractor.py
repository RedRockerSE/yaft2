"""Tests for Contact Photo Extractor Plugin."""

import sqlite3
import zipfile
from pathlib import Path

import pytest

from plugins.contact_photo_extractor import ContactPhotoExtractorPlugin
from yaft.core.api import CoreAPI


# Sample JPEG header (valid but minimal)
JPEG_HEADER = b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00"
JPEG_FOOTER = b"\xff\xd9"
SAMPLE_JPEG = JPEG_HEADER + b"\x00" * 100 + JPEG_FOOTER

# Sample PNG header
PNG_HEADER = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00"
SAMPLE_PNG = PNG_HEADER + b"\x00" * 50


@pytest.fixture
def core_api(tmp_path):
    """Create Core API instance with temporary output directory."""
    api = CoreAPI()
    api.base_output_dir = tmp_path / "yaft_output"
    api.base_output_dir.mkdir(parents=True, exist_ok=True)
    return api


@pytest.fixture
def plugin(core_api):
    """Create Contact Photo Extractor plugin instance."""
    return ContactPhotoExtractorPlugin(core_api)


@pytest.fixture
def mock_android_zip_cellebrite(tmp_path):
    """Create mock Android extraction in Cellebrite format with contact photos."""
    zip_path = tmp_path / "android_cellebrite.zip"

    # Create contacts database
    db_path = tmp_path / "contacts2.db"
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Create contacts table
    cursor.execute(
        """
        CREATE TABLE contacts (
            _id INTEGER PRIMARY KEY,
            display_name TEXT
        )
        """
    )

    # Create data table with photos
    cursor.execute(
        """
        CREATE TABLE data (
            _id INTEGER PRIMARY KEY,
            raw_contact_id INTEGER,
            mimetype TEXT,
            data15 BLOB
        )
        """
    )

    # Insert contacts
    cursor.execute("INSERT INTO contacts (_id, display_name) VALUES (1, 'John Doe')")
    cursor.execute("INSERT INTO contacts (_id, display_name) VALUES (2, 'Jane Smith')")
    cursor.execute("INSERT INTO contacts (_id, display_name) VALUES (3, 'Bob Johnson')")

    # Insert photo data (JPEG and PNG)
    cursor.execute(
        "INSERT INTO data (raw_contact_id, mimetype, data15) VALUES (1, 'vnd.android.cursor.item/photo', ?)",
        (SAMPLE_JPEG,),
    )
    cursor.execute(
        "INSERT INTO data (raw_contact_id, mimetype, data15) VALUES (2, 'vnd.android.cursor.item/photo', ?)",
        (SAMPLE_PNG,),
    )
    cursor.execute(
        "INSERT INTO data (raw_contact_id, mimetype, data15) VALUES (3, 'vnd.android.cursor.item/photo', ?)",
        (SAMPLE_JPEG,),
    )

    conn.commit()
    conn.close()

    # Create ZIP in Cellebrite format
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.write(
            db_path,
            "Dump/data/data/com.android.providers.contacts/databases/contacts2.db",
        )
        # Add Cellebrite markers
        zf.writestr("Dump/", "")
        zf.writestr("extra/", "")

    return zip_path


@pytest.fixture
def mock_android_zip_graykey(tmp_path):
    """Create mock Android extraction in GrayKey format with contact photos."""
    zip_path = tmp_path / "android_graykey.zip"

    # Create contacts database
    db_path = tmp_path / "contacts2.db"
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Create contacts table
    cursor.execute(
        """
        CREATE TABLE contacts (
            _id INTEGER PRIMARY KEY,
            display_name TEXT
        )
        """
    )

    # Create data table with photos
    cursor.execute(
        """
        CREATE TABLE data (
            _id INTEGER PRIMARY KEY,
            raw_contact_id INTEGER,
            mimetype TEXT,
            data15 BLOB
        )
        """
    )

    # Insert contacts
    cursor.execute("INSERT INTO contacts (_id, display_name) VALUES (10, 'Alice Wonder')")

    # Insert photo data
    cursor.execute(
        "INSERT INTO data (raw_contact_id, mimetype, data15) VALUES (10, 'vnd.android.cursor.item/photo', ?)",
        (SAMPLE_PNG,),
    )

    conn.commit()
    conn.close()

    # Create ZIP in GrayKey format (no prefix)
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.write(
            db_path, "data/data/com.android.providers.contacts/databases/contacts2.db"
        )
        # Add GrayKey markers
        zf.writestr("data/", "")
        zf.writestr("system/", "")
        zf.writestr("cache/", "")

    return zip_path


@pytest.fixture
def mock_ios_zip_cellebrite(tmp_path):
    """Create mock iOS extraction in Cellebrite format with contact photos."""
    zip_path = tmp_path / "ios_cellebrite.zip"

    # Create AddressBook database
    db_path = tmp_path / "AddressBook.sqlitedb"
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Create ABPerson table
    cursor.execute(
        """
        CREATE TABLE ABPerson (
            ROWID INTEGER PRIMARY KEY,
            First TEXT,
            Last TEXT,
            data BLOB
        )
        """
    )

    # Insert contacts with photos
    cursor.execute(
        "INSERT INTO ABPerson (ROWID, First, Last, data) VALUES (1, 'Steve', 'Jobs', ?)",
        (SAMPLE_JPEG,),
    )
    cursor.execute(
        "INSERT INTO ABPerson (ROWID, First, Last, data) VALUES (2, 'Tim', 'Cook', ?)",
        (SAMPLE_PNG,),
    )

    conn.commit()
    conn.close()

    # Create ZIP in Cellebrite format
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.write(
            db_path,
            "filesystem1/private/var/mobile/Library/AddressBook/AddressBook.sqlitedb",
        )
        # Add Cellebrite iOS marker
        zf.writestr("filesystem1/", "")

    return zip_path


@pytest.fixture
def mock_ios_zip_graykey(tmp_path):
    """Create mock iOS extraction in GrayKey format with contact photos."""
    zip_path = tmp_path / "ios_graykey.zip"

    # Create AddressBook database
    db_path = tmp_path / "AddressBook.sqlitedb"
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Create ABPerson table
    cursor.execute(
        """
        CREATE TABLE ABPerson (
            ROWID INTEGER PRIMARY KEY,
            First TEXT,
            Last TEXT,
            data BLOB
        )
        """
    )

    # Insert contacts with photos
    cursor.execute(
        "INSERT INTO ABPerson (ROWID, First, Last, data) VALUES (5, 'Craig', 'Federighi', ?)",
        (SAMPLE_JPEG,),
    )

    conn.commit()
    conn.close()

    # Create ZIP in GrayKey format (no prefix)
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.write(
            db_path,
            "private/var/mobile/Library/AddressBook/AddressBook.sqlitedb",
        )
        # Add GrayKey iOS markers
        zf.writestr("private/", "")
        zf.writestr("System/", "")

    return zip_path


def test_plugin_metadata(plugin):
    """Test plugin metadata."""
    metadata = plugin.metadata
    assert metadata.name == "ContactPhotoExtractorPlugin"
    assert metadata.version == "1.0.0"
    assert "android" in metadata.target_os
    assert "ios" in metadata.target_os


def test_extract_android_photos_cellebrite(plugin, core_api, mock_android_zip_cellebrite):
    """Test extracting Android contact photos from Cellebrite format."""
    core_api.set_zip_file(mock_android_zip_cellebrite)

    result = plugin.execute()

    assert result["success"] is True
    assert result["total_photos"] == 3
    assert len(plugin.extracted_photos) == 3

    # Check photo types
    photo_types = [p["photo_type"] for p in plugin.extracted_photos]
    assert "jpeg" in photo_types
    assert "png" in photo_types

    # Check sources
    assert all(p["source"] == "android" for p in plugin.extracted_photos)

    # Verify files were created
    output_dir = core_api.get_case_output_dir("contact_photos/android")
    assert output_dir.exists()
    photo_files = list(output_dir.glob("*.*"))
    assert len(photo_files) >= 3  # May have files from previous tests


def test_extract_android_photos_graykey(plugin, core_api, mock_android_zip_graykey):
    """Test extracting Android contact photos from GrayKey format."""
    core_api.set_zip_file(mock_android_zip_graykey)

    result = plugin.execute()

    assert result["success"] is True
    assert result["total_photos"] == 1
    assert plugin.extracted_photos[0]["contact_name"] == "Alice Wonder"
    assert plugin.extracted_photos[0]["photo_type"] == "png"


def test_extract_ios_photos_cellebrite(plugin, core_api, mock_ios_zip_cellebrite):
    """Test extracting iOS contact photos from Cellebrite format."""
    core_api.set_zip_file(mock_ios_zip_cellebrite)

    result = plugin.execute()

    assert result["success"] is True
    assert result["total_photos"] == 2

    # Check contact names
    names = [p["contact_name"] for p in plugin.extracted_photos]
    assert "Steve Jobs" in names
    assert "Tim Cook" in names

    # Check sources
    assert all(p["source"] == "ios" for p in plugin.extracted_photos)

    # Verify files were created
    output_dir = core_api.get_case_output_dir("contact_photos/ios")
    assert output_dir.exists()
    photo_files = list(output_dir.glob("*.*"))
    assert len(photo_files) >= 2  # May have files from previous tests


def test_extract_ios_photos_graykey(plugin, core_api, mock_ios_zip_graykey):
    """Test extracting iOS contact photos from GrayKey format."""
    core_api.set_zip_file(mock_ios_zip_graykey)

    result = plugin.execute()

    assert result["success"] is True
    assert result["total_photos"] == 1
    assert plugin.extracted_photos[0]["contact_name"] == "Craig Federighi"
    assert plugin.extracted_photos[0]["photo_type"] == "jpeg"


def test_no_zip_loaded(plugin, core_api):
    """Test execution without ZIP file loaded."""
    result = plugin.execute()

    assert result["success"] is False
    assert "No ZIP file loaded" in result["error"]


def test_no_contact_database(plugin, core_api, tmp_path):
    """Test with ZIP that doesn't contain contact database."""
    zip_path = tmp_path / "empty.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr("data/", "")
        zf.writestr("system/", "")
        zf.writestr("cache/", "")

    core_api.set_zip_file(zip_path)
    result = plugin.execute()

    # Should succeed but find no photos
    assert result["success"] is True
    assert result["total_photos"] == 0


def test_report_generation(plugin, core_api, mock_android_zip_cellebrite):
    """Test report generation."""
    core_api.set_zip_file(mock_android_zip_cellebrite)

    result = plugin.execute()

    assert result["success"] is True
    assert "report_path" in result
    assert Path(result["report_path"]).exists()

    # Read report and verify content
    report_content = Path(result["report_path"]).read_text(encoding="utf-8")
    assert "Contact Photo Extraction Report" in report_content
    assert "Executive Summary" in report_content
    assert "Statistics" in report_content


def test_json_export(plugin, core_api, mock_android_zip_cellebrite):
    """Test JSON export."""
    core_api.set_zip_file(mock_android_zip_cellebrite)

    result = plugin.execute()

    assert result["success"] is True
    assert "json_path" in result
    assert Path(result["json_path"]).exists()

    # Verify JSON structure
    import json

    with open(result["json_path"], encoding="utf-8") as f:
        data = json.load(f)

    assert data["plugin_name"] == "ContactPhotoExtractorPlugin"
    assert data["plugin_version"] == "1.0.0"
    assert data["data"]["total_photos"] == 3
    assert len(data["data"]["photos"]) == 3


def test_full_workflow(plugin, core_api, mock_android_zip_cellebrite):
    """Test complete extraction workflow."""
    core_api.set_zip_file(mock_android_zip_cellebrite)

    # Initialize
    plugin.initialize()

    # Execute
    result = plugin.execute()

    # Verify success
    assert result["success"] is True
    assert result["total_photos"] == 3
    assert Path(result["report_path"]).exists()
    assert Path(result["json_path"]).exists()

    # Cleanup
    plugin.cleanup()
    assert len(plugin.extracted_photos) == 0
    assert len(plugin.errors) == 0
