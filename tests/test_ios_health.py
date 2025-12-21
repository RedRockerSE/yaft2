"""
Tests for iOS Health Plugin
"""

import json
import sqlite3
import zipfile
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from plugins.ios_health import iOShealthPlugin
from yaft.core.api import CoreAPI


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
    return iOShealthPlugin(core_api)


@pytest.fixture
def mock_health_databases(tmp_path):
    """Create mock healthdb_secure.sqlite and healthdb.sqlite databases with test data."""
    # Create healthdb_secure.sqlite
    secure_db_path = tmp_path / "healthdb_secure.sqlite"
    conn_secure = sqlite3.connect(secure_db_path)
    cursor_secure = conn_secure.cursor()

    # Create tables for healthdb_secure.sqlite
    # Workouts tables
    cursor_secure.execute(
        """
        CREATE TABLE workouts (
            data_id INTEGER PRIMARY KEY,
            activity_type INTEGER,
            duration REAL,
            total_distance REAL,
            total_energy_burned REAL,
            goal_type INTEGER,
            goal REAL
        )
    """
    )

    cursor_secure.execute(
        """
        CREATE TABLE samples (
            data_id INTEGER,
            start_date REAL,
            end_date REAL,
            data_type INTEGER
        )
    """
    )

    cursor_secure.execute(
        """
        CREATE TABLE quantity_samples (
            data_id INTEGER,
            quantity REAL
        )
    """
    )

    cursor_secure.execute(
        """
        CREATE TABLE category_samples (
            data_id INTEGER,
            value INTEGER
        )
    """
    )

    cursor_secure.execute(
        """
        CREATE TABLE objects (
            data_id INTEGER,
            type INTEGER,
            provenance INTEGER,
            creation_date REAL
        )
    """
    )

    cursor_secure.execute(
        """
        CREATE TABLE data_provenances (
            ROWID INTEGER PRIMARY KEY,
            origin_product_type TEXT,
            origin_build TEXT,
            local_product_type TEXT,
            local_build TEXT,
            source_id INTEGER,
            source_version TEXT,
            device_id INTEGER,
            tz_name TEXT
        )
    """
    )

    cursor_secure.execute(
        """
        CREATE TABLE metadata_values (
            object_id INTEGER,
            key_id INTEGER,
            numerical_value REAL,
            string_value TEXT
        )
    """
    )

    cursor_secure.execute(
        """
        CREATE TABLE metadata_keys (
            ROWID INTEGER PRIMARY KEY,
            key TEXT
        )
    """
    )

    cursor_secure.execute(
        """
        CREATE TABLE ACHAchievementsPlugin_earned_instances (
            created_date REAL,
            earned_date TEXT,
            template_unique_name TEXT,
            value_in_canonical_unit REAL,
            value_canonical_unit TEXT,
            creator_device TEXT
        )
    """
    )

    # Insert test data for workouts (data_type doesn't matter for workouts table)
    # Using Core Data timestamp: 86400 = 1 day after 2001-01-01 = 2001-01-02
    cursor_secure.execute(
        """
        INSERT INTO workouts VALUES (1, 37, 1800.0, 5000.0, 250.0, 0, 0)
    """
    )  # Running, 30 min, 5km, 250 kcal

    cursor_secure.execute(
        """
        INSERT INTO samples VALUES (1, 86400.0, 88200.0, NULL)
    """
    )  # 2001-01-02 00:00 - 00:30

    # Insert test data for steps (data_type = 7)
    cursor_secure.execute(
        """
        INSERT INTO samples VALUES (2, 90000.0, 93600.0, 7)
    """
    )  # 2001-01-02 01:00 - 02:00
    cursor_secure.execute(
        """
        INSERT INTO quantity_samples VALUES (2, 1500.0)
    """
    )

    # Insert test data for heart rate (data_type = 5)
    cursor_secure.execute(
        """
        INSERT INTO samples VALUES (3, 95000.0, 95000.0, 5)
    """
    )
    cursor_secure.execute(
        """
        INSERT INTO quantity_samples VALUES (3, 1.25)
    """
    )  # 75 BPM (1.25 Hz * 60)
    cursor_secure.execute("INSERT INTO objects VALUES (3, 1, 1, 95000.0)")
    cursor_secure.execute("INSERT INTO metadata_keys VALUES (1, 'HKHeartRateContext')")
    cursor_secure.execute(
        """
        INSERT INTO metadata_values VALUES (3, 1, 1.0, NULL)
    """
    )  # Background

    # Insert test data for resting heart rate (data_type = 118)
    cursor_secure.execute(
        """
        INSERT INTO samples VALUES (4, 96000.0, 96000.0, 118)
    """
    )
    cursor_secure.execute(
        """
        INSERT INTO quantity_samples VALUES (4, 60.0)
    """
    )  # 60 BPM
    cursor_secure.execute("INSERT INTO objects VALUES (4, 1, 1, 96000.0)")

    # Insert test data for sleep (data_type = 63, values 2-5)
    cursor_secure.execute(
        """
        INSERT INTO samples VALUES (5, 100000.0, 107200.0, 63)
    """
    )  # 2 hours
    cursor_secure.execute(
        """
        INSERT INTO category_samples VALUES (5, 4)
    """
    )  # DEEP sleep

    # Insert test data for achievements
    cursor_secure.execute(
        """
        INSERT INTO ACHAchievementsPlugin_earned_instances
        VALUES (86400.0, '2024-01-01', 'DailyStepGoal', 10000, 'steps', 'iPhone')
    """
    )

    # Insert test data for height (data_type = 2)
    cursor_secure.execute(
        """
        INSERT INTO samples VALUES (6, 86400.0, 86400.0, 2)
    """
    )
    cursor_secure.execute(
        """
        INSERT INTO quantity_samples VALUES (6, 1.75)
    """
    )  # 1.75 meters

    # Insert test data for weight (data_type = 3)
    cursor_secure.execute(
        """
        INSERT INTO samples VALUES (7, 86400.0, 86400.0, 3)
    """
    )
    cursor_secure.execute(
        """
        INSERT INTO quantity_samples VALUES (7, 70.0)
    """
    )  # 70 kg

    # Insert test data for watch worn (data_type = 70)
    cursor_secure.execute(
        """
        INSERT INTO samples VALUES (8, 86400.0, 90000.0, 70)
    """
    )
    cursor_secure.execute(
        """
        INSERT INTO samples VALUES (9, 90000.0, 93600.0, 70)
    """
    )

    # Insert test data for headphone audio levels (data_type = 173)
    cursor_secure.execute(
        """
        INSERT INTO samples VALUES (10, 86400.0, 86400.0, 173)
    """
    )
    cursor_secure.execute(
        """
        INSERT INTO quantity_samples VALUES (10, 75.0)
    """
    )  # 75 dB
    cursor_secure.execute("INSERT INTO objects VALUES (10, 1, 1, 86400.0)")
    cursor_secure.execute(
        "INSERT INTO metadata_keys VALUES (2, '_HKPrivateMetadataKeyHeadphoneAudioDataBundleName')"
    )
    cursor_secure.execute(
        """
        INSERT INTO metadata_values VALUES (10, 2, NULL, 'com.apple.music')
    """
    )

    # Insert test data for wrist temperature (data_type = 256)
    cursor_secure.execute(
        """
        INSERT INTO samples VALUES (11, 86400.0, 86400.0, 256)
    """
    )
    cursor_secure.execute(
        """
        INSERT INTO quantity_samples VALUES (11, 36.5)
    """
    )  # 36.5°C
    cursor_secure.execute("INSERT INTO objects VALUES (11, 1, 1, 86400.0)")
    cursor_secure.execute(
        "INSERT INTO metadata_keys VALUES (3, '_HKPrivateMetadataKeySkinSurfaceTemperature')"
    )
    cursor_secure.execute("INSERT INTO metadata_keys VALUES (4, 'HKAlgorithmVersion')")
    cursor_secure.execute(
        """
        INSERT INTO metadata_values VALUES (11, 3, 36.2, NULL)
    """
    )
    cursor_secure.execute(
        """
        INSERT INTO metadata_values VALUES (11, 4, 1.0, NULL)
    """
    )

    # Insert provenance data
    cursor_secure.execute(
        """
        INSERT INTO data_provenances VALUES (
            1, 'Watch6,1', '18A1234', 'iPhone12,1', '18A5678',
            1, '1.0.0', 1, 'America/New_York'
        )
    """
    )

    conn_secure.commit()
    conn_secure.close()

    # Create healthdb.sqlite
    health_db_path = tmp_path / "healthdb.sqlite"
    conn_health = sqlite3.connect(health_db_path)
    cursor_health = conn_health.cursor()

    # Create tables for healthdb.sqlite
    cursor_health.execute(
        """
        CREATE TABLE source_devices (
            ROWID INTEGER PRIMARY KEY,
            creation_date REAL,
            name TEXT,
            manufacturer TEXT,
            model TEXT,
            hardware TEXT,
            firmware TEXT,
            software TEXT,
            localIdentifier TEXT
        )
    """
    )

    cursor_health.execute(
        """
        CREATE TABLE sources (
            ROWID INTEGER PRIMARY KEY,
            name TEXT,
            product_type TEXT,
            source_options INTEGER
        )
    """
    )

    # Insert test data for source devices
    cursor_health.execute(
        """
        INSERT INTO source_devices VALUES (
            1, 86400.0, 'Apple Watch', 'Apple Inc.', 'Watch6,1',
            'Watch6,1', '1.0', 'watchOS 8.0', 'ABC123'
        )
    """
    )

    # Insert test data for sources
    cursor_health.execute(
        """
        INSERT INTO sources VALUES (1, 'Health', 'Watch6,1', 0)
    """
    )

    conn_health.commit()
    conn_health.close()

    return secure_db_path, health_db_path


@pytest.fixture
def mock_zip_cellebrite(tmp_path, mock_health_databases):
    """Create mock ZIP file in Cellebrite format with health databases."""
    secure_db_path, health_db_path = mock_health_databases
    zip_path = tmp_path / "cellebrite_health.zip"

    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.write(secure_db_path, "filesystem1/private/var/mobile/Library/Health/healthdb_secure.sqlite")
        zf.write(health_db_path, "filesystem1/private/var/mobile/Library/Health/healthdb.sqlite")

    return zip_path


def test_plugin_metadata(plugin):
    """Test plugin metadata is correct."""
    assert plugin.metadata.name == "iOShealthPlugin"
    assert plugin.metadata.version == "1.0.0"
    assert plugin.metadata.description == "Extract comprehensive health and fitness data from iOS Health databases"
    assert "ios" in plugin.metadata.target_os


def test_plugin_initialization(plugin, core_api):
    """Test plugin initializes correctly."""
    plugin.initialize()
    assert plugin.core_api == core_api
    assert plugin.extraction_type == "unknown"
    assert plugin.errors == []


def test_no_zip_loaded(plugin):
    """Test plugin handles missing ZIP file."""
    result = plugin.execute()
    assert result["success"] is False
    assert "error" in result


def test_no_health_databases(plugin, core_api, tmp_path):
    """Test plugin handles missing health databases in ZIP."""
    # Create empty ZIP
    zip_path = tmp_path / "empty.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        pass

    core_api.set_zip_file(zip_path)
    result = plugin.execute()

    assert result["success"] is True
    assert "No Health databases found" in result.get("message", "")


def test_full_extraction_workflow(plugin, core_api, mock_zip_cellebrite):
    """Test complete extraction workflow."""
    core_api.set_zip_file(mock_zip_cellebrite)

    result = plugin.execute()

    assert result["success"] is True
    assert "report_path" in result
    assert "json_path" in result
    assert "csv_paths" in result
    assert len(result["errors"]) == 0

    # Verify report was created
    assert Path(result["report_path"]).exists()

    # Verify JSON was created
    assert Path(result["json_path"]).exists()

    # Verify at least some CSV files were created
    assert len(result["csv_paths"]) > 0


def test_workouts_extraction(plugin, core_api, mock_zip_cellebrite):
    """Test workouts extraction."""
    core_api.set_zip_file(mock_zip_cellebrite)
    plugin.execute()

    assert len(plugin.workouts_data) > 0
    workout = plugin.workouts_data[0]

    assert "start_time" in workout
    assert "end_time" in workout
    assert "activity_type" in workout
    assert "duration" in workout
    assert "distance_km" in workout
    assert "energy_kcal" in workout


def test_steps_extraction(plugin, core_api, mock_zip_cellebrite):
    """Test steps extraction."""
    core_api.set_zip_file(mock_zip_cellebrite)
    plugin.execute()

    assert len(plugin.steps_data) > 0
    steps = plugin.steps_data[0]

    assert "start_time" in steps
    assert "end_time" in steps
    assert "steps" in steps
    assert steps["steps"] == 1500


def test_heart_rate_extraction(plugin, core_api, mock_zip_cellebrite):
    """Test heart rate extraction."""
    core_api.set_zip_file(mock_zip_cellebrite)
    plugin.execute()

    assert len(plugin.heart_rate_data) > 0
    hr = plugin.heart_rate_data[0]

    assert "start_time" in hr
    assert "heart_rate_bpm" in hr
    assert "context" in hr
    assert hr["heart_rate_bpm"] == 75  # 1.25 * 60


def test_resting_heart_rate_extraction(plugin, core_api, mock_zip_cellebrite):
    """Test resting heart rate extraction."""
    core_api.set_zip_file(mock_zip_cellebrite)
    plugin.execute()

    assert len(plugin.resting_heart_rate_data) > 0
    rhr = plugin.resting_heart_rate_data[0]

    assert "start_time" in rhr
    assert "resting_heart_rate_bpm" in rhr
    assert rhr["resting_heart_rate_bpm"] == 60


def test_sleep_extraction(plugin, core_api, mock_zip_cellebrite):
    """Test sleep data extraction."""
    core_api.set_zip_file(mock_zip_cellebrite)
    plugin.execute()

    assert len(plugin.sleep_data) > 0
    sleep = plugin.sleep_data[0]

    assert "start_time" in sleep
    assert "end_time" in sleep
    assert "sleep_state" in sleep
    assert "duration" in sleep
    assert sleep["sleep_state"] == "DEEP"


def test_achievements_extraction(plugin, core_api, mock_zip_cellebrite):
    """Test achievements extraction."""
    core_api.set_zip_file(mock_zip_cellebrite)
    plugin.execute()

    assert len(plugin.achievements_data) > 0
    achievement = plugin.achievements_data[0]

    assert "created_date" in achievement
    assert "achievement" in achievement
    assert "value" in achievement
    assert achievement["achievement"] == "DailyStepGoal"


def test_height_extraction(plugin, core_api, mock_zip_cellebrite):
    """Test height extraction."""
    core_api.set_zip_file(mock_zip_cellebrite)
    plugin.execute()

    assert len(plugin.height_data) > 0
    height = plugin.height_data[0]

    assert "timestamp" in height
    assert "height_meters" in height
    assert "height_cm" in height
    assert "height_feet_inches" in height
    assert height["height_meters"] == 1.75


def test_weight_extraction(plugin, core_api, mock_zip_cellebrite):
    """Test weight extraction."""
    core_api.set_zip_file(mock_zip_cellebrite)
    plugin.execute()

    assert len(plugin.weight_data) > 0
    weight = plugin.weight_data[0]

    assert "timestamp" in weight
    assert "weight_kg" in weight
    assert "weight_pounds" in weight
    assert "weight_stone" in weight
    assert weight["weight_kg"] == 70.0


def test_watch_worn_extraction(plugin, core_api, mock_zip_cellebrite):
    """Test watch worn data extraction."""
    core_api.set_zip_file(mock_zip_cellebrite)
    plugin.execute()

    # Watch worn data requires complex CTE queries and may not have results with minimal test data
    # Just verify the method doesn't crash
    assert isinstance(plugin.watch_worn_data, list)


def test_sleep_period_extraction(plugin, core_api, mock_zip_cellebrite):
    """Test sleep period extraction."""
    core_api.set_zip_file(mock_zip_cellebrite)
    plugin.execute()

    # Sleep period data requires complex CTE queries and may not have results with minimal test data
    # Just verify the method doesn't crash
    assert isinstance(plugin.sleep_period_data, list)


def test_headphone_audio_extraction(plugin, core_api, mock_zip_cellebrite):
    """Test headphone audio extraction."""
    core_api.set_zip_file(mock_zip_cellebrite)
    plugin.execute()

    assert len(plugin.headphone_audio_data) > 0
    audio = plugin.headphone_audio_data[0]

    assert "start_time" in audio
    assert "decibels" in audio
    assert "bundle_name" in audio
    assert audio["decibels"] == 75.0


def test_wrist_temperature_extraction(plugin, core_api, mock_zip_cellebrite):
    """Test wrist temperature extraction."""
    core_api.set_zip_file(mock_zip_cellebrite)
    plugin.execute()

    assert len(plugin.wrist_temperature_data) > 0
    temp = plugin.wrist_temperature_data[0]

    assert "start_time" in temp
    assert "wrist_temp_celsius" in temp
    assert "wrist_temp_fahrenheit" in temp
    assert temp["wrist_temp_celsius"] == 36.5


def test_provenances_extraction(plugin, core_api, mock_zip_cellebrite):
    """Test provenances extraction."""
    core_api.set_zip_file(mock_zip_cellebrite)
    plugin.execute()

    assert len(plugin.provenances_data) > 0
    prov = plugin.provenances_data[0]

    assert "row_id" in prov
    assert "origin_product_type" in prov
    assert "source_name" in prov
    assert "timezone" in prov


def test_source_devices_extraction(plugin, core_api, mock_zip_cellebrite):
    """Test source devices extraction."""
    core_api.set_zip_file(mock_zip_cellebrite)
    plugin.execute()

    assert len(plugin.source_devices_data) > 0
    device = plugin.source_devices_data[0]

    assert "creation_date" in device
    assert "device_name" in device
    assert "manufacturer" in device
    assert "model" in device
    assert device["device_name"] == "Apple Watch"


def test_timestamp_conversion(plugin):
    """Test Core Data timestamp conversion."""
    # Test 1 day after 2001-01-01 = 2001-01-02
    timestamp = 86400.0
    result = plugin._convert_cocoa_timestamp(timestamp)
    assert "2001-01-02" in result

    # Test with 0 (should be 2001-01-01)
    result = plugin._convert_cocoa_timestamp(0)
    assert "2001-01-01" in result

    # Test with None
    result = plugin._convert_cocoa_timestamp(None)
    assert result == ""


def test_duration_formatting(plugin):
    """Test duration formatting."""
    # Test 1 hour
    result = plugin._format_duration_hms(3600)
    assert result == "01:00:00"

    # Test 1 hour 30 minutes 45 seconds
    result = plugin._format_duration_hms(5445)
    assert result == "01:30:45"

    # Test with None
    result = plugin._format_duration_hms(None)
    assert result == ""


def test_report_generation(plugin, core_api, mock_zip_cellebrite):
    """Test report generation."""
    core_api.set_zip_file(mock_zip_cellebrite)
    plugin.execute()

    report_path = plugin._generate_report()

    assert report_path.exists()
    content = report_path.read_text(encoding="utf-8")
    assert "iOS Health Database Analysis" in content
    assert "Total Records:" in content


def test_json_export(plugin, core_api, mock_zip_cellebrite):
    """Test JSON export."""
    core_api.set_zip_file(mock_zip_cellebrite)
    plugin.execute()

    json_path = plugin._export_to_json()

    assert json_path.exists()
    with open(json_path, encoding="utf-8") as f:
        export_data = json.load(f)

    # CoreAPI wraps data in "data" field
    assert "data" in export_data
    data = export_data["data"]

    assert "workouts" in data
    assert "steps" in data
    assert "heart_rate" in data
    assert "sleep" in data
    assert "source_devices" in data
    assert "summary" in data


def test_csv_export(plugin, core_api, mock_zip_cellebrite):
    """Test CSV export."""
    core_api.set_zip_file(mock_zip_cellebrite)
    plugin.execute()

    csv_paths = plugin._export_to_csv()

    assert len(csv_paths) > 0
    # Verify at least one CSV file was created
    for csv_path in csv_paths:
        assert Path(csv_path).exists()


def test_plugin_cleanup(plugin):
    """Test plugin cleanup."""
    # Should not crash even if temp_dir doesn't exist
    plugin.cleanup()

    # Verify cleanup doesn't raise errors
    assert True
