"""
Tests for iOS knowledgeC Plugin
"""

import pytest
import zipfile
import sqlite3
import plistlib
from pathlib import Path
from datetime import datetime, timedelta

from yaft.core.api import CoreAPI
from plugins.ios_knowledgec import iOSknowledgeCPlugin


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
    return iOSknowledgeCPlugin(core_api)


def create_knowledgec_db(db_path: Path):
    """Create a mock knowledgeC.db with sample data."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Create ZOBJECT table
    cursor.execute("""
        CREATE TABLE ZOBJECT (
            Z_PK INTEGER PRIMARY KEY,
            ZSTREAMNAME TEXT,
            ZSTARTDATE REAL,
            ZENDDATE REAL,
            ZCREATIONDATE REAL,
            ZVALUEINTEGER INTEGER,
            ZVALUESTRING TEXT,
            ZHASSTRUCTUREDMETADATA INTEGER,
            ZSTRUCTUREDMETADATA INTEGER
        )
    """)

    # Create ZSTRUCTUREDMETADATA table
    cursor.execute("""
        CREATE TABLE ZSTRUCTUREDMETADATA (
            Z_PK INTEGER PRIMARY KEY,
            Z_DKDEVICEISPLUGGEDINMETADATAKEY__ADAPTERISWIRELESS TEXT,
            Z_DKNOWPLAYINGMETADATAKEY__PLAYING INTEGER,
            Z_DKNOWPLAYINGMETADATAKEY__ARTIST TEXT,
            Z_DKNOWPLAYINGMETADATAKEY__ALBUM TEXT,
            Z_DKNOWPLAYINGMETADATAKEY__TITLE TEXT,
            Z_DKNOWPLAYINGMETADATAKEY__GENRE TEXT,
            Z_DKNOWPLAYINGMETADATAKEY__DURATION REAL,
            Z_DKNOWPLAYINGMETADATAKEY__ISAIRPLAYVIDEO INTEGER,
            Z_DKNOWPLAYINGMETADATAKEY__OUTPUTDEVICEIDS BLOB
        )
    """)

    # Core Data reference date: 2001-01-01
    # Convert to seconds since 2001-01-01
    def to_core_data_timestamp(dt: datetime) -> float:
        ref_date = datetime(2001, 1, 1)
        delta = dt - ref_date
        return delta.total_seconds()

    # Insert battery percentage data
    cursor.execute("""
        INSERT INTO ZOBJECT (Z_PK, ZSTREAMNAME, ZSTARTDATE, ZENDDATE, ZVALUEINTEGER, ZHASSTRUCTUREDMETADATA, ZCREATIONDATE)
        VALUES (1, '/device/batteryPercentage', ?, ?, 85, 0, ?)
    """, (
        to_core_data_timestamp(datetime(2024, 1, 15, 10, 0)),
        to_core_data_timestamp(datetime(2024, 1, 15, 10, 5)),
        to_core_data_timestamp(datetime(2024, 1, 15, 10, 0)),
    ))

    cursor.execute("""
        INSERT INTO ZOBJECT (Z_PK, ZSTREAMNAME, ZSTARTDATE, ZENDDATE, ZVALUEINTEGER, ZHASSTRUCTUREDMETADATA, ZCREATIONDATE)
        VALUES (2, '/device/batteryPercentage', ?, ?, 100, 1, ?)
    """, (
        to_core_data_timestamp(datetime(2024, 1, 15, 11, 0)),
        to_core_data_timestamp(datetime(2024, 1, 15, 11, 5)),
        to_core_data_timestamp(datetime(2024, 1, 15, 11, 0)),
    ))

    # Insert device plugin status data
    cursor.execute("""
        INSERT INTO ZSTRUCTUREDMETADATA (Z_PK, Z_DKDEVICEISPLUGGEDINMETADATAKEY__ADAPTERISWIRELESS)
        VALUES (1, '0')
    """)

    cursor.execute("""
        INSERT INTO ZOBJECT (Z_PK, ZSTREAMNAME, ZSTARTDATE, ZENDDATE, ZVALUEINTEGER, ZSTRUCTUREDMETADATA, ZCREATIONDATE)
        VALUES (3, '/device/isPluggedIn', ?, ?, 1, 1, ?)
    """, (
        to_core_data_timestamp(datetime(2024, 1, 15, 9, 0)),
        to_core_data_timestamp(datetime(2024, 1, 15, 10, 0)),
        to_core_data_timestamp(datetime(2024, 1, 15, 9, 0)),
    ))

    # Insert media playing data
    output_device_plist = {
        '$version': 100000,
        '$archiver': 'NSKeyedArchiver',
        '$top': {'root': {'CF$UID': 1}},
        '$objects': ['$null', 'NSArray', 'item1', 'item2', 'item3', 'item4', 'Built-in Speaker']
    }
    output_device_blob = plistlib.dumps(output_device_plist)

    cursor.execute("""
        INSERT INTO ZSTRUCTUREDMETADATA (
            Z_PK, Z_DKNOWPLAYINGMETADATAKEY__PLAYING, Z_DKNOWPLAYINGMETADATAKEY__ARTIST,
            Z_DKNOWPLAYINGMETADATAKEY__ALBUM, Z_DKNOWPLAYINGMETADATAKEY__TITLE,
            Z_DKNOWPLAYINGMETADATAKEY__GENRE, Z_DKNOWPLAYINGMETADATAKEY__DURATION,
            Z_DKNOWPLAYINGMETADATAKEY__ISAIRPLAYVIDEO, Z_DKNOWPLAYINGMETADATAKEY__OUTPUTDEVICEIDS
        )
        VALUES (2, 1, 'Artist Name', 'Album Name', 'Song Title', 'Rock', 240, 0, ?)
    """, (output_device_blob,))

    cursor.execute("""
        INSERT INTO ZOBJECT (Z_PK, ZSTREAMNAME, ZSTARTDATE, ZENDDATE, ZVALUESTRING, ZSTRUCTUREDMETADATA, ZCREATIONDATE)
        VALUES (4, '/media/nowPlaying', ?, ?, 'com.apple.music', 2, ?)
    """, (
        to_core_data_timestamp(datetime(2024, 1, 15, 14, 0)),
        to_core_data_timestamp(datetime(2024, 1, 15, 14, 4)),
        to_core_data_timestamp(datetime(2024, 1, 15, 14, 0)),
    ))

    # Insert Do Not Disturb data
    cursor.execute("""
        INSERT INTO ZOBJECT (Z_PK, ZSTREAMNAME, ZSTARTDATE, ZENDDATE, ZVALUEINTEGER, ZCREATIONDATE)
        VALUES (5, '/settings/doNotDisturb', ?, ?, 1, ?)
    """, (
        to_core_data_timestamp(datetime(2024, 1, 15, 22, 0)),
        to_core_data_timestamp(datetime(2024, 1, 16, 7, 0)),
        to_core_data_timestamp(datetime(2024, 1, 15, 22, 0)),
    ))

    # Insert app usage data
    cursor.execute("""
        INSERT INTO ZOBJECT (Z_PK, ZSTREAMNAME, ZSTARTDATE, ZENDDATE, ZVALUESTRING, ZCREATIONDATE)
        VALUES (6, '/app/usage', ?, ?, 'com.apple.mobilesafari', ?)
    """, (
        to_core_data_timestamp(datetime(2024, 1, 15, 13, 0)),
        to_core_data_timestamp(datetime(2024, 1, 15, 13, 30)),
        to_core_data_timestamp(datetime(2024, 1, 15, 13, 0)),
    ))

    # Insert lock status data
    cursor.execute("""
        INSERT INTO ZOBJECT (Z_PK, ZSTREAMNAME, ZSTARTDATE, ZENDDATE, ZVALUEINTEGER, ZCREATIONDATE)
        VALUES (7, '/device/isLocked', ?, ?, 1, ?)
    """, (
        to_core_data_timestamp(datetime(2024, 1, 15, 12, 0)),
        to_core_data_timestamp(datetime(2024, 1, 15, 12, 5)),
        to_core_data_timestamp(datetime(2024, 1, 15, 12, 0)),
    ))

    # Insert screen status data
    cursor.execute("""
        INSERT INTO ZOBJECT (Z_PK, ZSTREAMNAME, ZSTARTDATE, ZENDDATE, ZVALUEINTEGER, ZCREATIONDATE)
        VALUES (8, '/display/isBacklit', ?, ?, 1, ?)
    """, (
        to_core_data_timestamp(datetime(2024, 1, 15, 8, 0)),
        to_core_data_timestamp(datetime(2024, 1, 15, 8, 30)),
        to_core_data_timestamp(datetime(2024, 1, 15, 8, 0)),
    ))

    conn.commit()
    conn.close()


@pytest.fixture
def mock_zip_with_knowledgec(tmp_path):
    """Create mock ZIP with knowledgeC.db."""
    zip_path = tmp_path / "ios_extraction.zip"

    # Create knowledgeC.db
    db_path = tmp_path / "knowledgeC.db"
    create_knowledgec_db(db_path)

    # Create ZIP with Cellebrite format
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.write(db_path, "filesystem1/private/var/mobile/Library/CoreDuet/Knowledge/knowledgeC.db")

    return zip_path


@pytest.fixture
def mock_zip_no_db(tmp_path):
    """Create mock ZIP without knowledgeC.db."""
    zip_path = tmp_path / "no_db.zip"

    test_file = tmp_path / "test.txt"
    test_file.write_text("Test data")

    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.write(test_file, "filesystem1/test.txt")

    return zip_path


def test_plugin_metadata(plugin):
    """Test plugin metadata."""
    assert plugin.metadata.name == "iOSknowledgeCPlugin"
    assert plugin.metadata.version == "1.0.0"
    assert "knowledgeC" in plugin.metadata.description
    assert "ios" in plugin.metadata.target_os


def test_plugin_initialization(plugin):
    """Test plugin initialization."""
    plugin.initialize()
    assert plugin.extraction_type == "unknown"
    assert plugin.zip_prefix == ""
    assert len(plugin.battery_data) == 0
    assert len(plugin.errors) == 0


def test_no_zip_loaded(plugin):
    """Test execution without ZIP file loaded."""
    result = plugin.execute()

    assert result["success"] is False
    assert "error" in result
    assert "No ZIP file loaded" in result["error"]


def test_no_knowledgec_db(core_api, plugin, mock_zip_no_db):
    """Test execution with ZIP containing no knowledgeC.db."""
    core_api.set_zip_file(mock_zip_no_db)

    result = plugin.execute()

    assert result["success"] is True
    assert "knowledgeC.db not found" in result["message"]


def test_full_extraction(core_api, plugin, mock_zip_with_knowledgec):
    """Test full extraction of all artifacts."""
    core_api.set_zip_file(mock_zip_with_knowledgec)

    result = plugin.execute()

    assert result["success"] is True
    assert result["battery_events"] == 2
    assert result["plugin_events"] == 1
    assert result["media_events"] == 1
    assert result["dnd_events"] == 1
    assert result["app_usage_events"] == 1
    assert result["lock_events"] == 1
    assert result["screen_events"] == 1

    # Verify report and exports exist
    assert Path(result["report_path"]).exists()
    assert Path(result["json_path"]).exists()
    assert len(result["csv_paths"]) == 7  # 7 artifacts


def test_battery_percentage_extraction(core_api, plugin, mock_zip_with_knowledgec):
    """Test battery percentage extraction."""
    core_api.set_zip_file(mock_zip_with_knowledgec)
    plugin.execute()

    assert len(plugin.battery_data) == 2

    # First record
    assert plugin.battery_data[0]["battery_percentage"] == 85
    assert plugin.battery_data[0]["is_fully_charged"] == "No"
    assert "2024-01-15" in plugin.battery_data[0]["start_time"]

    # Second record (fully charged)
    assert plugin.battery_data[1]["battery_percentage"] == 100
    assert plugin.battery_data[1]["is_fully_charged"] == "Yes"


def test_plugin_status_extraction(core_api, plugin, mock_zip_with_knowledgec):
    """Test device plugin status extraction."""
    core_api.set_zip_file(mock_zip_with_knowledgec)
    plugin.execute()

    assert len(plugin.plugin_status_data) == 1
    assert plugin.plugin_status_data[0]["device_plugin_status"] == "Plugged in"
    assert plugin.plugin_status_data[0]["is_adapter_wireless"] == "No"


def test_media_playing_extraction(core_api, plugin, mock_zip_with_knowledgec):
    """Test media playing extraction."""
    core_api.set_zip_file(mock_zip_with_knowledgec)
    plugin.execute()

    assert len(plugin.media_playing_data) == 1

    media = plugin.media_playing_data[0]
    assert media["playing_state"] == "Play"
    assert media["app_bundle_id"] == "com.apple.music"
    assert media["artist"] == "Artist Name"
    assert media["album"] == "Album Name"
    assert media["title"] == "Song Title"
    assert media["genre"] == "Rock"
    assert media["media_duration"] == "00:04:00"  # 240 seconds
    assert media["airplay_video"] == "No"
    assert media["output_device"] == "Built-in Speaker"


def test_do_not_disturb_extraction(core_api, plugin, mock_zip_with_knowledgec):
    """Test Do Not Disturb extraction."""
    core_api.set_zip_file(mock_zip_with_knowledgec)
    plugin.execute()

    assert len(plugin.dnd_data) == 1
    assert plugin.dnd_data[0]["do_not_disturb"] == "Yes"
    assert "2024-01-15 22:00:00" in plugin.dnd_data[0]["start_time"]


def test_app_usage_extraction(core_api, plugin, mock_zip_with_knowledgec):
    """Test app usage extraction."""
    core_api.set_zip_file(mock_zip_with_knowledgec)
    plugin.execute()

    assert len(plugin.app_usage_data) == 1
    assert plugin.app_usage_data[0]["application"] == "com.apple.mobilesafari"


def test_lock_status_extraction(core_api, plugin, mock_zip_with_knowledgec):
    """Test lock status extraction."""
    core_api.set_zip_file(mock_zip_with_knowledgec)
    plugin.execute()

    assert len(plugin.lock_status_data) == 1
    assert plugin.lock_status_data[0]["device_lock_status"] == "Locked"


def test_screen_status_extraction(core_api, plugin, mock_zip_with_knowledgec):
    """Test screen status extraction."""
    core_api.set_zip_file(mock_zip_with_knowledgec)
    plugin.execute()

    assert len(plugin.screen_status_data) == 1
    assert plugin.screen_status_data[0]["device_screen_status"] == "Backlight on"


def test_core_data_timestamp_conversion(plugin):
    """Test Core Data timestamp conversion."""
    # Test with a known timestamp
    # 1 day = 86400 seconds
    # Test 1 day after 2001-01-01 = 2001-01-02
    timestamp = 86400.0
    result = plugin._convert_core_data_timestamp(timestamp)

    assert "2001-01-02" in result

    # Test with 0 (should be 2001-01-01)
    result = plugin._convert_core_data_timestamp(0)
    assert "2001-01-01" in result


def test_duration_formatting(plugin):
    """Test duration formatting."""
    # 3661 seconds = 1 hour, 1 minute, 1 second
    result = plugin._format_duration(3661)
    assert result == "01:01:01"

    # 240 seconds = 4 minutes
    result = plugin._format_duration(240)
    assert result == "00:04:00"

    # 0 seconds
    result = plugin._format_duration(0)
    assert result == "00:00:00"


def test_report_generation(core_api, plugin, mock_zip_with_knowledgec):
    """Test report generation."""
    core_api.set_zip_file(mock_zip_with_knowledgec)
    result = plugin.execute()

    report_path = Path(result["report_path"])
    assert report_path.exists()
    assert report_path.suffix == ".md"

    # Read and verify report content
    report_content = report_path.read_text(encoding='utf-8')
    assert "iOS knowledgeC Database Analysis" in report_content
    assert "Summary" in report_content
    assert "Event Statistics" in report_content
    assert "Battery Percentage" in report_content


def test_json_export(core_api, plugin, mock_zip_with_knowledgec):
    """Test JSON export."""
    core_api.set_zip_file(mock_zip_with_knowledgec)
    result = plugin.execute()

    json_path = Path(result["json_path"])
    assert json_path.exists()
    assert json_path.suffix == ".json"

    # Read and verify JSON content
    import json
    with open(json_path, 'r', encoding='utf-8') as f:
        export_data = json.load(f)

    assert "data" in export_data
    data = export_data["data"]

    assert "battery_percentage" in data
    assert "device_plugin_status" in data
    assert "media_playing" in data
    assert "summary" in data
    assert data["summary"]["total_battery_events"] == 2


def test_csv_export(core_api, plugin, mock_zip_with_knowledgec):
    """Test CSV export."""
    core_api.set_zip_file(mock_zip_with_knowledgec)
    result = plugin.execute()

    csv_paths = result["csv_paths"]
    assert len(csv_paths) == 7  # All 7 artifacts

    # Verify all CSV files exist
    for csv_path in csv_paths:
        assert Path(csv_path).exists()
        assert Path(csv_path).suffix == ".csv"


def test_cleanup(plugin):
    """Test plugin cleanup."""
    plugin.cleanup()
    # Should not raise any errors
