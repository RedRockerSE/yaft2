"""
Tests for Android Call Log Analyzer Plugin.
"""

import json
import sqlite3
import zipfile
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from yaft.core.api import CoreAPI
from plugins.android_call_log_analyzer import AndroidCallLogAnalyzerPlugin


@pytest.fixture
def core_api(tmp_path):
    """Create a CoreAPI instance with a temporary directory."""
    api = CoreAPI()
    api.base_output_dir = tmp_path / "yaft_output"
    api.base_output_dir.mkdir(parents=True, exist_ok=True)
    return api


@pytest.fixture
def plugin(core_api):
    """Create an Android Call Log Analyzer plugin instance."""
    return AndroidCallLogAnalyzerPlugin(core_api)


@pytest.fixture
def mock_android_zip_cellebrite(tmp_path):
    """Create a mock Android extraction ZIP in Cellebrite format with call logs."""
    zip_path = tmp_path / "android_extraction_cellebrite.zip"

    # Create calllog database
    calllog_db = tmp_path / "calllog.db"
    conn = sqlite3.connect(calllog_db)
    cursor = conn.cursor()

    # Create calls table
    # Note: column names must match what Android uses (without underscores in some cases)
    cursor.execute("""
        CREATE TABLE calls (
            _id INTEGER PRIMARY KEY,
            number TEXT,
            date INTEGER,
            duration INTEGER,
            type INTEGER,
            name TEXT,
            numbertype INTEGER,
            numberlabel TEXT,
            countryiso TEXT,
            geocoded_location TEXT,
            is_read INTEGER,
            features INTEGER,
            data_usage INTEGER,
            new INTEGER
        )
    """)

    # Unix timestamp in milliseconds: 2024-01-15 14:30:00
    base_timestamp = 1705329000000

    # Insert sample call records
    # type: 1=Incoming, 2=Outgoing, 3=Missed, 5=Rejected, 6=Blocked, 7=Answered Externally
    # features: 0=Normal, 1=Video, 2=WiFi Calling
    # Fields: _id, number, date, duration, type, name, numbertype, numberlabel, countryiso, geocoded_location, is_read, features, data_usage, new
    calls = [
        # Outgoing call to +1-555-123-4567
        (1, '+1-555-123-4567', base_timestamp, 125, 2, 'John Doe', 1, 'Mobile', 'us', 'New York, NY', 1, 0, 0, 0),
        # Incoming call from +1-555-987-6543
        (2, '+1-555-987-6543', base_timestamp - 3600000, 300, 1, 'Jane Smith', 2, 'Work', 'us', None, 1, 0, 0, 0),
        # Missed call from +1-555-111-2222
        (3, '+1-555-111-2222', base_timestamp - 7200000, 0, 3, None, 1, 'Mobile', 'us', None, 1, 0, 0, 0),
        # Video call (outgoing)
        (4, '+1-555-444-5555', base_timestamp - 10800000, 600, 2, 'Alice Brown', 1, 'Mobile', 'us', None, 1, 1, 0, 0),
        # Rejected call
        (5, '+1-555-777-8888', base_timestamp - 14400000, 0, 5, None, 1, 'Mobile', 'us', None, 1, 0, 0, 0),
        # WiFi calling (incoming)
        (6, '+1-555-333-4444', base_timestamp - 18000000, 180, 1, 'Bob Wilson', 1, 'Mobile', 'us', None, 1, 2, 0, 0),
    ]

    for call in calls:
        cursor.execute(
            "INSERT INTO calls (_id, number, date, duration, type, name, numbertype, numberlabel, countryiso, geocoded_location, is_read, features, data_usage, new) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            call
        )

    conn.commit()
    conn.close()

    with zipfile.ZipFile(zip_path, "w") as zf:
        # Cellebrite format uses "fs/" prefix
        zf.write(
            calllog_db,
            "fs/data/data/com.android.providers.contacts/databases/calllog.db"
        )

    return zip_path


@pytest.fixture
def mock_android_zip_graykey(tmp_path):
    """Create a mock Android extraction ZIP in GrayKey format with call logs."""
    zip_path = tmp_path / "android_extraction_graykey.zip"

    # Create calllog database with minimal columns
    calllog_db = tmp_path / "calllog.db"
    conn = sqlite3.connect(calllog_db)
    cursor = conn.cursor()

    # Create calls table with basic columns
    cursor.execute("""
        CREATE TABLE calls (
            _id INTEGER PRIMARY KEY,
            number TEXT,
            date INTEGER,
            duration INTEGER,
            type INTEGER,
            is_read INTEGER
        )
    """)

    base_timestamp = 1705329000000

    # Insert sample call records (minimal schema)
    calls = [
        (1, '+1-555-123-4567', base_timestamp, 180, 2, 1),  # Outgoing
        (2, '+1-555-987-6543', base_timestamp - 1800000, 90, 1, 1),  # Incoming
    ]

    for call in calls:
        cursor.execute(
            "INSERT INTO calls (_id, number, date, duration, type, is_read) VALUES (?, ?, ?, ?, ?, ?)",
            call
        )

    conn.commit()
    conn.close()

    with zipfile.ZipFile(zip_path, "w") as zf:
        # GrayKey format has no prefix
        zf.write(
            calllog_db,
            "data/data/com.android.providers.contacts/databases/calllog.db"
        )

    return zip_path


@pytest.fixture
def mock_android_zip_samsung(tmp_path):
    """Create a mock Android extraction ZIP with Samsung-specific call log path."""
    zip_path = tmp_path / "android_extraction_samsung.zip"

    # Create calllog database
    calllog_db = tmp_path / "calllog_samsung.db"
    conn = sqlite3.connect(calllog_db)
    cursor = conn.cursor()

    # Create calls table with full schema
    cursor.execute("""
        CREATE TABLE calls (
            _id INTEGER PRIMARY KEY,
            number TEXT,
            date INTEGER,
            duration INTEGER,
            type INTEGER,
            name TEXT,
            numbertype INTEGER,
            numberlabel TEXT,
            countryiso TEXT,
            geocoded_location TEXT,
            is_read INTEGER,
            features INTEGER,
            data_usage INTEGER,
            new INTEGER
        )
    """)

    base_timestamp = 1705329000000

    # Insert sample call records
    calls = [
        (1, '+82-10-1234-5678', base_timestamp, 200, 2, 'Kim Samsung', 1, 'Mobile', 'kr', 'Seoul', 1, 0, 0, 0),
        (2, '+82-10-9876-5432', base_timestamp - 3600000, 150, 1, 'Lee Galaxy', 2, 'Work', 'kr', None, 1, 0, 0, 0),
        (3, '+82-10-5555-1234', base_timestamp - 7200000, 0, 3, None, 1, 'Mobile', 'kr', None, 1, 0, 0, 0),
    ]

    for call in calls:
        cursor.execute(
            "INSERT INTO calls (_id, number, date, duration, type, name, numbertype, numberlabel, countryiso, geocoded_location, is_read, features, data_usage, new) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            call
        )

    conn.commit()
    conn.close()

    with zipfile.ZipFile(zip_path, "w") as zf:
        # Samsung-specific path (Cellebrite extraction with Dump/ prefix)
        zf.write(
            calllog_db,
            "Dump/data/data/com.samsung.android.providers.contacts/databases/calllog.db"
        )

    return zip_path


def test_plugin_metadata(plugin):
    """Test plugin metadata is correctly defined."""
    metadata = plugin.metadata
    assert metadata.name == "AndroidCallLogAnalyzer"
    assert metadata.version == "1.0.0"
    assert "Android" in metadata.description or "call" in metadata.description.lower()
    assert "android" in metadata.target_os


def test_initialize(plugin):
    """Test plugin initialization."""
    plugin.initialize()
    assert plugin.calls == []
    assert plugin.errors == []
    assert plugin.zip_prefix == ''


def test_detect_zip_structure_cellebrite(plugin, core_api, mock_android_zip_cellebrite):
    """Test detection of Cellebrite ZIP structure."""
    core_api.set_zip_file(mock_android_zip_cellebrite)
    plugin._detect_zip_structure()

    assert plugin.extraction_type == "cellebrite_android"
    assert plugin.zip_prefix == "fs/"


def test_detect_zip_structure_graykey(plugin, core_api, mock_android_zip_graykey):
    """Test detection of GrayKey ZIP structure."""
    core_api.set_zip_file(mock_android_zip_graykey)
    plugin._detect_zip_structure()

    assert plugin.extraction_type == "graykey_android"
    assert plugin.zip_prefix == ""


def test_parse_call_log_cellebrite(plugin, core_api, mock_android_zip_cellebrite):
    """Test parsing calllog.db from Cellebrite format."""
    core_api.set_zip_file(mock_android_zip_cellebrite)
    plugin._detect_zip_structure()

    calls = plugin._parse_call_log()

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
    assert first_call['call_type'] == 'Outgoing'  # call_type is the direction in Android
    assert first_call['feature_type'] == 'Audio'  # Normal audio call


def test_parse_call_log_graykey(plugin, core_api, mock_android_zip_graykey):
    """Test parsing calllog.db from GrayKey format (minimal schema)."""
    core_api.set_zip_file(mock_android_zip_graykey)
    plugin._detect_zip_structure()

    calls = plugin._parse_call_log()

    assert len(calls) == 2
    # Verify fallback query works when newer columns don't exist
    assert all('phone_number' in call for call in calls)
    assert all('timestamp' in call for call in calls)


def test_parse_call_log_samsung(plugin, core_api, mock_android_zip_samsung):
    """Test parsing calllog.db from Samsung-specific path."""
    core_api.set_zip_file(mock_android_zip_samsung)
    plugin._detect_zip_structure()

    calls = plugin._parse_call_log()

    assert len(calls) == 3
    # Verify Samsung-specific path was found and parsed
    assert calls[0]['phone_number'] == '+82-10-1234-5678'
    assert calls[0]['contact_name'] == 'Kim Samsung'
    assert calls[1]['phone_number'] == '+82-10-9876-5432'
    assert calls[2]['phone_number'] == '+82-10-5555-1234'


def test_samsung_path_fallback(plugin, core_api, tmp_path):
    """Test that plugin tries multiple paths and finds Samsung-specific path."""
    # Create ZIP with ONLY Samsung path (no standard path)
    zip_path = tmp_path / "samsung_only.zip"

    calllog_db = tmp_path / "calllog_only_samsung.db"
    conn = sqlite3.connect(calllog_db)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE calls (
            _id INTEGER PRIMARY KEY,
            number TEXT,
            date INTEGER,
            duration INTEGER,
            type INTEGER,
            is_read INTEGER
        )
    """)
    cursor.execute("INSERT INTO calls VALUES (1, '+82-10-1111-2222', 1705329000000, 100, 2, 1)")
    conn.commit()
    conn.close()

    with zipfile.ZipFile(zip_path, "w") as zf:
        # Only add Samsung path, NOT standard path
        zf.write(
            calllog_db,
            "Dump/data/data/com.samsung.android.providers.contacts/databases/calllog.db"
        )

    core_api.set_zip_file(zip_path)
    plugin._detect_zip_structure()
    calls = plugin._parse_call_log()

    # Should successfully find and parse Samsung-specific database
    assert len(calls) == 1
    assert calls[0]['phone_number'] == '+82-10-1111-2222'


def test_format_duration(plugin):
    """Test call duration formatting."""
    assert plugin._format_duration(30) == "30s"
    assert plugin._format_duration(90) == "1m 30s"
    assert plugin._format_duration(3665) == "1h 1m"
    assert plugin._format_duration(0) == "0s"


def test_analyze_call_patterns(plugin, core_api, mock_android_zip_cellebrite):
    """Test call pattern analysis."""
    core_api.set_zip_file(mock_android_zip_cellebrite)
    plugin._detect_zip_structure()
    plugin.calls = plugin._parse_call_log()

    plugin._analyze_call_patterns()

    assert hasattr(plugin, 'outgoing_count')
    assert hasattr(plugin, 'incoming_count')
    assert hasattr(plugin, 'missed_count')
    assert hasattr(plugin, 'video_count')
    assert hasattr(plugin, 'total_duration')
    assert hasattr(plugin, 'frequent_contacts')

    # Verify counts
    assert plugin.outgoing_count == 2  # Two outgoing calls (one regular, one video)
    assert plugin.incoming_count == 2  # Two incoming calls (one regular, one WiFi)
    assert plugin.missed_count == 1  # One missed call
    assert plugin.video_count == 1  # One video call
    assert plugin.total_duration > 0


def test_execute_full_extraction_cellebrite(plugin, core_api, mock_android_zip_cellebrite):
    """Test full call log extraction from Cellebrite format."""
    core_api.set_zip_file(mock_android_zip_cellebrite)

    result = plugin.execute()

    assert result["success"] is True
    assert result["total_calls"] == 6
    assert "report_path" in result
    assert "json_path" in result
    assert Path(result["report_path"]).exists()
    assert Path(result["json_path"]).exists()


def test_execute_full_extraction_graykey(plugin, core_api, mock_android_zip_graykey):
    """Test full call log extraction from GrayKey format."""
    core_api.set_zip_file(mock_android_zip_graykey)

    result = plugin.execute()

    assert result["success"] is True
    assert result["total_calls"] == 2


def test_export_to_json(plugin, core_api, mock_android_zip_cellebrite, tmp_path):
    """Test JSON export functionality."""
    core_api.set_zip_file(mock_android_zip_cellebrite)
    plugin._detect_zip_structure()
    plugin.calls = plugin._parse_call_log()
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


def test_generate_report(plugin, core_api, mock_android_zip_cellebrite):
    """Test markdown report generation."""
    core_api.set_zip_file(mock_android_zip_cellebrite)
    plugin._detect_zip_structure()
    plugin.calls = plugin._parse_call_log()
    plugin._analyze_call_patterns()

    report_path = plugin._generate_report()

    assert Path(report_path).exists()

    with open(report_path, encoding='utf-8') as f:
        content = f.read()

    assert "# Android Call Log Analysis Report" in content
    assert "Total Call Records" in content
    assert "Outgoing Calls" in content


def test_missing_database_handling(plugin, core_api, tmp_path):
    """Test handling of missing calllog database."""
    # Create empty ZIP
    zip_path = tmp_path / "empty_android.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr("fs/dummy.txt", "dummy")

    core_api.set_zip_file(zip_path)
    plugin._detect_zip_structure()

    calls = plugin._parse_call_log()

    assert len(calls) == 0
    assert len(plugin.errors) > 0
    assert any('calllog.db' in err['source'] for err in plugin.errors)


def test_cleanup(plugin):
    """Test plugin cleanup."""
    plugin.calls = [{'test': 'data'}]
    plugin.cleanup()
    # Cleanup should not clear data, just log


def test_no_zip_loaded_error(plugin, core_api):
    """Test error handling when no ZIP is loaded."""
    result = plugin.execute()

    assert result["success"] is False
    assert "error" in result
    assert "No ZIP file loaded" in result["error"]


def test_video_call_detection(plugin, core_api, mock_android_zip_cellebrite):
    """Test video call detection."""
    core_api.set_zip_file(mock_android_zip_cellebrite)
    plugin._detect_zip_structure()
    plugin.calls = plugin._parse_call_log()

    # Video calls are indicated by feature_type, not call_type
    video_calls = [c for c in plugin.calls if c.get('feature_type') == 'Video']

    assert len(video_calls) == 1


def test_missed_call_detection(plugin, core_api, mock_android_zip_cellebrite):
    """Test missed call detection."""
    core_api.set_zip_file(mock_android_zip_cellebrite)
    plugin._detect_zip_structure()
    plugin.calls = plugin._parse_call_log()

    missed_calls = [c for c in plugin.calls if c['direction'] == 'Missed']

    assert len(missed_calls) == 1
    assert missed_calls[0]['phone_number'] == '+1-555-111-2222'


def test_rejected_call_detection(plugin, core_api, mock_android_zip_cellebrite):
    """Test rejected call detection."""
    core_api.set_zip_file(mock_android_zip_cellebrite)
    plugin._detect_zip_structure()
    plugin.calls = plugin._parse_call_log()

    rejected_calls = [c for c in plugin.calls if c['direction'] == 'Rejected']

    assert len(rejected_calls) == 1


def test_call_type_mapping(plugin):
    """Test call type constants are properly defined."""
    assert 1 in plugin.CALL_TYPES  # Incoming
    assert 2 in plugin.CALL_TYPES  # Outgoing
    assert 3 in plugin.CALL_TYPES  # Missed
    assert 5 in plugin.CALL_TYPES  # Rejected
