"""
Tests for iOS Call Log Analyzer Plugin.
"""

import json
import sqlite3
import zipfile
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from yaft.core.api import CoreAPI
from plugins.ios_call_log_analyzer import iOSCallLogAnalyzerPlugin


@pytest.fixture
def core_api(tmp_path):
    """Create a CoreAPI instance with a temporary directory."""
    api = CoreAPI()
    api.base_output_dir = tmp_path / "yaft_output"
    api.base_output_dir.mkdir(parents=True, exist_ok=True)
    return api


@pytest.fixture
def plugin(core_api):
    """Create an iOS Call Log Analyzer plugin instance."""
    return iOSCallLogAnalyzerPlugin(core_api)


@pytest.fixture
def mock_ios_zip_cellebrite(tmp_path):
    """Create a mock iOS extraction ZIP in Cellebrite format with call logs."""
    zip_path = tmp_path / "ios_extraction_cellebrite.zip"

    # Create CallHistory database
    call_history_db = tmp_path / "CallHistory.storedata"
    conn = sqlite3.connect(call_history_db)
    cursor = conn.cursor()

    # Create ZCALLRECORD table with all columns
    cursor.execute("""
        CREATE TABLE ZCALLRECORD (
            Z_PK INTEGER PRIMARY KEY,
            ZADDRESS TEXT,
            ZDATE REAL,
            ZDURATION REAL,
            ZCALLTYPE INTEGER,
            ZREAD INTEGER,
            ZANSWERED INTEGER,
            ZORIGINATED INTEGER,
            ZSERVICE_PROVIDER TEXT,
            ZISO_COUNTRY_CODE TEXT,
            ZLOCATION TEXT,
            ZNAME TEXT,
            ZFACE_TIME_DATA BLOB
        )
    """)

    # Core Data timestamp: seconds since 2001-01-01
    # Example: 2024-01-15 14:30:00 is ~725,000,000 seconds after 2001-01-01
    base_timestamp = 725000000.0

    # Insert sample call records
    # Fields: ZADDRESS, ZDATE, ZDURATION, ZCALLTYPE, ZREAD, ZANSWERED, ZORIGINATED, ZSERVICE_PROVIDER, ZISO_COUNTRY_CODE, ZLOCATION, ZNAME, ZFACE_TIME_DATA
    # ZORIGINATED=1 means call was made by device (outgoing)
    # ZANSWERED=1 means call was answered (applies to both incoming and outgoing)
    calls = [
        # Outgoing call to +1-555-123-4567 (ZORIGINATED=1, ZANSWERED=1)
        ('+1-555-123-4567', base_timestamp, 125.0, 1, 1, 1, 1, None, 'US', 'New York', 'John Doe', None),
        # Incoming call from +1-555-987-6543 (ZORIGINATED=0, ZANSWERED=1)
        ('+1-555-987-6543', base_timestamp - 3600, 300.0, 2, 1, 1, 0, None, 'US', None, 'Jane Smith', None),
        # Missed call from +1-555-111-2222 (ZORIGINATED=0, ZANSWERED=0)
        ('+1-555-111-2222', base_timestamp - 7200, 0, 3, 1, 0, 0, None, 'US', None, None, None),
        # FaceTime video call (outgoing, ZORIGINATED=1)
        ('+1-555-444-5555', base_timestamp - 10800, 600.0, 5, 1, 1, 1, 'FaceTime', 'US', None, 'Alice Brown', b'facetime_data'),
        # FaceTime audio call (outgoing, ZORIGINATED=1)
        ('alice@icloud.com', base_timestamp - 14400, 450.0, 6, 1, 1, 1, 'FaceTime', None, None, 'Alice Brown', b'facetime_data'),
        # Outgoing cancelled (ZORIGINATED=1, ZANSWERED=0)
        ('+1-555-777-8888', base_timestamp - 18000, 0, 8, 1, 0, 1, None, 'US', None, None, None),
    ]

    for call in calls:
        cursor.execute(
            "INSERT INTO ZCALLRECORD (ZADDRESS, ZDATE, ZDURATION, ZCALLTYPE, ZREAD, ZANSWERED, ZORIGINATED, ZSERVICE_PROVIDER, ZISO_COUNTRY_CODE, ZLOCATION, ZNAME, ZFACE_TIME_DATA) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            call
        )

    conn.commit()
    conn.close()

    with zipfile.ZipFile(zip_path, "w") as zf:
        # Cellebrite format uses "filesystem1/" prefix
        zf.write(
            call_history_db,
            "filesystem1/private/var/mobile/Library/CallHistoryDB/CallHistory.storedata"
        )

    return zip_path


@pytest.fixture
def mock_ios_zip_graykey(tmp_path):
    """Create a mock iOS extraction ZIP in GrayKey format with call logs."""
    zip_path = tmp_path / "ios_extraction_graykey.zip"

    # Create CallHistory database with minimal columns (older iOS version)
    call_history_db = tmp_path / "CallHistory.storedata"
    conn = sqlite3.connect(call_history_db)
    cursor = conn.cursor()

    # Create ZCALLRECORD table with basic columns only
    cursor.execute("""
        CREATE TABLE ZCALLRECORD (
            Z_PK INTEGER PRIMARY KEY,
            ZADDRESS TEXT,
            ZDATE REAL,
            ZDURATION REAL,
            ZCALLTYPE INTEGER,
            ZREAD INTEGER,
            ZANSWERED INTEGER,
            ZORIGINATED INTEGER
        )
    """)

    base_timestamp = 725000000.0

    # Insert sample call records (minimal schema)
    # Fields: ZADDRESS, ZDATE, ZDURATION, ZCALLTYPE, ZREAD, ZANSWERED, ZORIGINATED
    calls = [
        # Outgoing call (ZORIGINATED=1)
        ('+1-555-123-4567', base_timestamp, 180.0, 1, 1, 1, 1),
        # Incoming call (ZORIGINATED=0)
        ('+1-555-987-6543', base_timestamp - 1800, 90.0, 2, 1, 1, 0),
    ]

    for call in calls:
        cursor.execute(
            "INSERT INTO ZCALLRECORD (ZADDRESS, ZDATE, ZDURATION, ZCALLTYPE, ZREAD, ZANSWERED, ZORIGINATED) VALUES (?, ?, ?, ?, ?, ?, ?)",
            call
        )

    conn.commit()
    conn.close()

    with zipfile.ZipFile(zip_path, "w") as zf:
        # GrayKey format has no prefix
        zf.write(
            call_history_db,
            "private/var/mobile/Library/CallHistoryDB/CallHistory.storedata"
        )

    return zip_path


def test_plugin_metadata(plugin):
    """Test plugin metadata is correctly defined."""
    metadata = plugin.metadata
    assert metadata.name == "iOSCallLogAnalyzer"
    assert metadata.version == "1.0.0"
    assert "iOS" in metadata.description or "call history" in metadata.description.lower()
    assert "ios" in metadata.target_os


def test_initialize(plugin):
    """Test plugin initialization."""
    plugin.initialize()
    assert plugin.calls == []
    assert plugin.errors == []
    assert plugin.zip_prefix == ''


def test_detect_zip_structure_cellebrite(plugin, core_api, mock_ios_zip_cellebrite):
    """Test detection of Cellebrite ZIP structure."""
    core_api.set_zip_file(mock_ios_zip_cellebrite)
    plugin._detect_zip_structure()

    assert plugin.extraction_type == "cellebrite_ios"
    assert plugin.zip_prefix == "filesystem1/"


def test_detect_zip_structure_graykey(plugin, core_api, mock_ios_zip_graykey):
    """Test detection of GrayKey ZIP structure."""
    core_api.set_zip_file(mock_ios_zip_graykey)
    plugin._detect_zip_structure()

    assert plugin.extraction_type == "graykey_ios"
    assert plugin.zip_prefix == ""


def test_parse_call_history_cellebrite(plugin, core_api, mock_ios_zip_cellebrite):
    """Test parsing CallHistory.storedata from Cellebrite format."""
    core_api.set_zip_file(mock_ios_zip_cellebrite)
    plugin._detect_zip_structure()

    calls = plugin._parse_call_history()

    assert len(calls) == 6
    assert all('phone_number' in call for call in calls)
    assert all('timestamp' in call for call in calls)
    assert all('duration' in call for call in calls)

    # Check first call (most recent)
    first_call = calls[0]
    assert first_call['phone_number'] == '+1-555-123-4567'
    assert first_call['contact_name'] == 'John Doe'
    assert first_call['direction'] == 'Outgoing'
    assert first_call['duration'] == 125
    assert first_call['service'] == 'Cellular'


def test_parse_call_history_graykey(plugin, core_api, mock_ios_zip_graykey):
    """Test parsing CallHistory.storedata from GrayKey format (minimal schema)."""
    core_api.set_zip_file(mock_ios_zip_graykey)
    plugin._detect_zip_structure()

    calls = plugin._parse_call_history()

    assert len(calls) == 2
    # Verify fallback query works when newer columns don't exist
    assert all('phone_number' in call for call in calls)
    assert all('timestamp' in call for call in calls)


def test_format_duration(plugin):
    """Test call duration formatting."""
    assert plugin._format_duration(30) == "30s"
    assert plugin._format_duration(90) == "1m 30s"
    assert plugin._format_duration(3665) == "1h 1m"
    assert plugin._format_duration(0) == "0s"


def test_analyze_call_patterns(plugin, core_api, mock_ios_zip_cellebrite):
    """Test call pattern analysis."""
    core_api.set_zip_file(mock_ios_zip_cellebrite)
    plugin._detect_zip_structure()
    plugin.calls = plugin._parse_call_history()

    plugin._analyze_call_patterns()

    assert hasattr(plugin, 'outgoing_count')
    assert hasattr(plugin, 'incoming_count')
    assert hasattr(plugin, 'missed_count')
    assert hasattr(plugin, 'facetime_count')
    assert hasattr(plugin, 'total_duration')
    assert hasattr(plugin, 'frequent_contacts')

    # Verify counts
    # Outgoing: regular call, FaceTime video, FaceTime audio, cancelled = 4
    assert plugin.outgoing_count == 4
    assert plugin.incoming_count == 1  # One incoming call
    assert plugin.missed_count == 1  # One missed call (direction is Missed, not answered)
    assert plugin.facetime_count == 2  # Two FaceTime calls
    assert plugin.total_duration > 0


def test_execute_full_extraction_cellebrite(plugin, core_api, mock_ios_zip_cellebrite):
    """Test full call log extraction from Cellebrite format."""
    core_api.set_zip_file(mock_ios_zip_cellebrite)

    result = plugin.execute()

    assert result["success"] is True
    assert result["total_calls"] == 6
    assert "report_path" in result
    assert "json_path" in result
    assert Path(result["report_path"]).exists()
    assert Path(result["json_path"]).exists()


def test_execute_full_extraction_graykey(plugin, core_api, mock_ios_zip_graykey):
    """Test full call log extraction from GrayKey format."""
    core_api.set_zip_file(mock_ios_zip_graykey)

    result = plugin.execute()

    assert result["success"] is True
    assert result["total_calls"] == 2


def test_export_to_json(plugin, core_api, mock_ios_zip_cellebrite, tmp_path):
    """Test JSON export functionality."""
    core_api.set_zip_file(mock_ios_zip_cellebrite)
    plugin._detect_zip_structure()
    plugin.calls = plugin._parse_call_history()
    plugin._analyze_call_patterns()

    json_path = tmp_path / "call_logs.json"
    plugin._export_to_json(json_path)

    assert json_path.exists()

    with open(json_path, encoding='utf-8') as f:
        data = json.load(f)

    assert "plugin_name" in data
    assert "data" in data
    assert "calls" in data["data"]
    assert "statistics" in data["data"]
    assert len(data["data"]["calls"]) == 6


def test_generate_report(plugin, core_api, mock_ios_zip_cellebrite):
    """Test markdown report generation."""
    core_api.set_zip_file(mock_ios_zip_cellebrite)
    plugin._detect_zip_structure()
    plugin.calls = plugin._parse_call_history()
    plugin._analyze_call_patterns()

    report_path = plugin._generate_report()

    assert Path(report_path).exists()

    with open(report_path, encoding='utf-8') as f:
        content = f.read()

    assert "# iOS Call Log Analysis Report" in content
    assert "Total Call Records" in content
    assert "Outgoing Calls" in content


def test_missing_database_handling(plugin, core_api, tmp_path):
    """Test handling of missing CallHistory database."""
    # Create empty ZIP
    zip_path = tmp_path / "empty_ios.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr("filesystem1/dummy.txt", "dummy")

    core_api.set_zip_file(zip_path)
    plugin._detect_zip_structure()

    calls = plugin._parse_call_history()

    assert len(calls) == 0
    assert len(plugin.errors) > 0
    assert any('CallHistory.storedata' in err['source'] for err in plugin.errors)


def test_cleanup(plugin):
    """Test plugin cleanup."""
    plugin.calls = [{'test': 'data'}]
    plugin.cleanup()
    # Cleanup should not clear data, just log
    # (data persists for report generation after cleanup)


def test_no_zip_loaded_error(plugin, core_api):
    """Test error handling when no ZIP is loaded."""
    result = plugin.execute()

    assert result["success"] is False
    assert "error" in result
    assert "No ZIP file loaded" in result["error"]


def test_facetime_call_detection(plugin, core_api, mock_ios_zip_cellebrite):
    """Test FaceTime call detection."""
    core_api.set_zip_file(mock_ios_zip_cellebrite)
    plugin._detect_zip_structure()
    plugin.calls = plugin._parse_call_history()

    facetime_calls = [c for c in plugin.calls if 'FaceTime' in c['service']]

    assert len(facetime_calls) == 2


def test_missed_call_detection(plugin, core_api, mock_ios_zip_cellebrite):
    """Test missed call detection."""
    core_api.set_zip_file(mock_ios_zip_cellebrite)
    plugin._detect_zip_structure()
    plugin.calls = plugin._parse_call_history()

    missed_calls = [c for c in plugin.calls if c['direction'] == 'Missed']

    assert len(missed_calls) == 1
    assert missed_calls[0]['phone_number'] == '+1-555-111-2222'


def test_call_type_mapping(plugin):
    """Test call type constants are properly defined."""
    assert 1 in plugin.CALL_TYPES  # Outgoing
    assert 2 in plugin.CALL_TYPES  # Incoming
    assert 3 in plugin.CALL_TYPES  # Missed
    assert 5 in plugin.CALL_TYPES  # FaceTime Video
    assert 6 in plugin.CALL_TYPES  # FaceTime Audio
