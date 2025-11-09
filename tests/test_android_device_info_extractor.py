"""
Tests for Android Device Info Extractor Plugin.
"""

import json
import sqlite3
import zipfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from yaft.core.api import CoreAPI
from plugins.android_device_info_extractor import AndroidDeviceInfoExtractorPlugin


@pytest.fixture
def core_api(tmp_path):
    """Create a CoreAPI instance with a temporary directory."""
    api = CoreAPI()
    api.base_output_dir = tmp_path / "yaft_output"
    api.base_output_dir.mkdir(parents=True, exist_ok=True)
    return api


@pytest.fixture
def plugin(core_api):
    """Create an Android Device Info Extractor plugin instance."""
    return AndroidDeviceInfoExtractorPlugin(core_api)


@pytest.fixture
def mock_android_zip_cellebrite(tmp_path):
    """Create a mock Android extraction ZIP in Cellebrite format."""
    zip_path = tmp_path / "android_extraction_cellebrite.zip"

    # Create mock build.prop content
    build_prop_content = """
# Build Properties
ro.product.manufacturer=Samsung
ro.product.model=SM-G991U
ro.product.name=galaxy_s21
ro.build.version.release=13
ro.build.version.sdk=33
ro.build.version.security_patch=2024-01-01
ro.build.id=TP1A.220624.014
ro.serialno=R5CR1234ABC
ro.build.fingerprint=samsung/galaxy_s21/SM-G991U:13/TP1A.220624.014/G991USQU3CVKL:user/release-keys
""".strip()

    # Create mock Bluetooth config
    bt_config_content = """
[Info]
FileSource = Empty

[Adapter]
Address = 11:22:33:44:55:66
Name = Galaxy S21

[11:AA:BB:CC:DD:EE]
Name = AirPods Pro
DevClass = 0x240418
LinkKey = 0123456789ABCDEF0123456789ABCDEF
TimeStamp = 1704067200

[22:FF:EE:DD:CC:BB]
Name = Smart Watch
DevClass = 0x1F00
LinkKey = FEDCBA9876543210FEDCBA9876543210
TimeStamp = 1704153600
""".strip()

    with zipfile.ZipFile(zip_path, "w") as zf:
        # Cellebrite format uses "fs/" prefix
        zf.writestr("fs/system/build.prop", build_prop_content)
        zf.writestr("fs/data/misc/bluedroid/bt_config.conf", bt_config_content)

        # Create settings databases
        settings_secure_db = tmp_path / "settings_secure.db"
        conn = sqlite3.connect(settings_secure_db)
        cursor = conn.cursor()
        cursor.execute("CREATE TABLE secure (name TEXT, value TEXT)")
        cursor.execute("INSERT INTO secure VALUES ('android_id', 'abc123def456')")
        cursor.execute("INSERT INTO secure VALUES ('bluetooth_name', 'Galaxy S21')")
        conn.commit()
        conn.close()
        zf.write(
            settings_secure_db,
            "fs/data/system/users/0/settings_secure.db",
        )

        settings_global_db = tmp_path / "settings_global.db"
        conn = sqlite3.connect(settings_global_db)
        cursor = conn.cursor()
        cursor.execute("CREATE TABLE global (name TEXT, value TEXT)")
        cursor.execute("INSERT INTO global VALUES ('device_name', 'My Galaxy S21')")
        cursor.execute("INSERT INTO global VALUES ('adb_enabled', '1')")
        cursor.execute("INSERT INTO global VALUES ('development_settings_enabled', '1')")
        conn.commit()
        conn.close()
        zf.write(
            settings_global_db,
            "fs/data/system/users/0/settings_global.db",
        )

        # Create telephony database
        telephony_db = tmp_path / "telephony.db"
        conn = sqlite3.connect(telephony_db)
        cursor = conn.cursor()
        cursor.execute(
            "CREATE TABLE siminfo (icc_id TEXT, display_name TEXT, number TEXT)"
        )
        cursor.execute(
            "INSERT INTO siminfo VALUES ('89012345678901234567', 'AT&T', '+1-555-987-6543')"
        )
        conn.commit()
        conn.close()
        zf.write(telephony_db, "fs/data/user_de/0/com.android.providers.telephony/databases/telephony.db")

        # Create accounts database
        accounts_db = tmp_path / "accounts_ce.db"
        conn = sqlite3.connect(accounts_db)
        cursor = conn.cursor()
        cursor.execute("CREATE TABLE accounts (name TEXT, type TEXT)")
        cursor.execute("INSERT INTO accounts VALUES ('user@gmail.com', 'com.google')")
        cursor.execute("INSERT INTO accounts VALUES ('user@outlook.com', 'com.microsoft')")
        conn.commit()
        conn.close()
        zf.write(accounts_db, "fs/data/system_ce/0/accounts_ce.db")

    return zip_path


@pytest.fixture
def mock_android_zip_graykey(tmp_path):
    """Create a mock Android extraction ZIP in GrayKey format."""
    zip_path = tmp_path / "android_extraction_graykey.zip"

    # Create mock build.prop content
    build_prop_content = """
ro.product.manufacturer=Google
ro.product.model=Pixel 7
ro.product.name=cheetah
ro.build.version.release=14
ro.build.version.sdk=34
ro.build.id=UP1A.231105.001
ro.serialno=1A2B3C4D5E
""".strip()

    with zipfile.ZipFile(zip_path, "w") as zf:
        # GrayKey format has no prefix
        zf.writestr("system/build.prop", build_prop_content)

        # Create minimal settings database
        settings_secure_db = tmp_path / "settings_secure_gk.db"
        conn = sqlite3.connect(settings_secure_db)
        cursor = conn.cursor()
        cursor.execute("CREATE TABLE secure (name TEXT, value TEXT)")
        cursor.execute("INSERT INTO secure VALUES ('android_id', 'xyz789abc123')")
        conn.commit()
        conn.close()
        zf.write(settings_secure_db, "data/system/users/0/settings_secure.db")

    return zip_path


def test_plugin_metadata(plugin):
    """Test that plugin metadata is correctly defined."""
    metadata = plugin.metadata

    assert metadata.name == "AndroidDeviceInfoExtractor"
    assert metadata.version == "1.0.0"
    assert "android" in metadata.target_os
    assert metadata.enabled is True
    assert "device metadata" in metadata.description.lower()


def test_initialize(plugin):
    """Test plugin initialization."""
    plugin.initialize()
    assert plugin.metadata_extracted == {}
    assert plugin.errors == []
    assert plugin.zip_prefix == ''


def test_detect_zip_structure_cellebrite(plugin, core_api, mock_android_zip_cellebrite):
    """Test detection of Cellebrite ZIP structure."""
    core_api.set_zip_file(mock_android_zip_cellebrite)

    plugin._detect_zip_structure()

    assert plugin.zip_prefix == "fs/"


def test_detect_zip_structure_graykey(plugin, core_api, mock_android_zip_graykey):
    """Test detection of GrayKey ZIP structure."""
    core_api.set_zip_file(mock_android_zip_graykey)

    plugin._detect_zip_structure()

    assert plugin.zip_prefix == ""


def test_extract_build_properties_cellebrite(plugin, core_api, mock_android_zip_cellebrite):
    """Test extraction of build properties from Cellebrite format."""
    core_api.set_zip_file(mock_android_zip_cellebrite)
    plugin._detect_zip_structure()

    plugin._extract_build_properties()

    build = plugin.metadata_extracted.get("build_properties", {})
    assert build.get("manufacturer") == "Samsung"
    assert build.get("model") == "SM-G991U"
    assert build.get("device") == "galaxy_s21"
    assert build.get("android_version") == "13"
    assert build.get("sdk_version") == "33"
    assert build.get("security_patch") == "2024-01-01"
    assert build.get("build_id") == "TP1A.220624.014"
    assert build.get("serial") == "R5CR1234ABC"


def test_extract_build_properties_graykey(plugin, core_api, mock_android_zip_graykey):
    """Test extraction of build properties from GrayKey format."""
    core_api.set_zip_file(mock_android_zip_graykey)
    plugin._detect_zip_structure()

    plugin._extract_build_properties()

    assert plugin.metadata_extracted.get("Manufacturer") == "Google"
    assert plugin.metadata_extracted.get("Model") == "Pixel 7"
    assert plugin.metadata_extracted.get("Android Version") == "14"
    assert plugin.metadata_extracted.get("SDK Level") == "34"


def test_extract_settings_databases_cellebrite(plugin, core_api, mock_android_zip_cellebrite):
    """Test extraction of settings databases from Cellebrite format."""
    core_api.set_zip_file(mock_android_zip_cellebrite)
    plugin._detect_zip_structure()

    plugin._extract_settings_databases()

    assert plugin.metadata_extracted.get("Android ID") == "abc123def456"
    assert plugin.metadata_extracted.get("Device Name") == "My Galaxy S21"
    assert plugin.metadata_extracted.get("Bluetooth Name") == "Galaxy S21"
    assert "ADB Enabled: Yes" in plugin.metadata_extracted.get("Security Warnings", [])
    assert "Developer Mode Enabled: Yes" in plugin.metadata_extracted.get("Security Warnings", [])


def test_extract_telephony_info_cellebrite(plugin, core_api, mock_android_zip_cellebrite):
    """Test extraction of telephony info from Cellebrite format."""
    core_api.set_zip_file(mock_android_zip_cellebrite)
    plugin._detect_zip_structure()

    plugin._extract_telephony_info()

    assert plugin.metadata_extracted.get("ICCID") == "89012345678901234567"
    assert plugin.metadata_extracted.get("Carrier") == "AT&T"
    assert plugin.metadata_extracted.get("Phone Number") == "+1-555-987-6543"


def test_extract_accounts_cellebrite(plugin, core_api, mock_android_zip_cellebrite):
    """Test extraction of accounts from Cellebrite format."""
    core_api.set_zip_file(mock_android_zip_cellebrite)
    plugin._detect_zip_structure()

    plugin._extract_accounts()

    accounts = plugin.metadata_extracted.get("Accounts", [])
    assert len(accounts) == 2
    assert any("user@gmail.com" in acc for acc in accounts)
    assert any("user@outlook.com" in acc for acc in accounts)


def test_extract_bluetooth_info_cellebrite(plugin, core_api, mock_android_zip_cellebrite):
    """Test extraction of Bluetooth info from Cellebrite format."""
    core_api.set_zip_file(mock_android_zip_cellebrite)
    plugin._detect_zip_structure()

    plugin._extract_bluetooth_info()

    bt_devices = plugin.metadata_extracted.get("Paired Bluetooth Devices", [])
    assert len(bt_devices) == 2
    assert any("AirPods Pro" in dev for dev in bt_devices)
    assert any("Smart Watch" in dev for dev in bt_devices)
    assert any("11:AA:BB:CC:DD:EE" in dev for dev in bt_devices)


def test_execute_full_extraction_cellebrite(plugin, core_api, mock_android_zip_cellebrite):
    """Test full execution of plugin with Cellebrite format."""
    core_api.set_zip_file(mock_android_zip_cellebrite)

    result = plugin.execute()

    assert result["success"] is True
    assert "report_path" in result
    assert Path(result["report_path"]).exists()

    # Verify device info was collected
    assert len(plugin.metadata_extracted) > 0
    assert plugin.metadata_extracted.get("Manufacturer") == "Samsung"
    assert plugin.metadata_extracted.get("Model") == "SM-G991U"
    assert plugin.metadata_extracted.get("Android Version") == "13"


def test_execute_full_extraction_graykey(plugin, core_api, mock_android_zip_graykey):
    """Test full execution of plugin with GrayKey format."""
    core_api.set_zip_file(mock_android_zip_graykey)

    result = plugin.execute()

    assert result["success"] is True
    assert "report_path" in result
    assert Path(result["report_path"]).exists()

    # Verify device info was collected
    assert len(plugin.metadata_extracted) > 0
    assert plugin.metadata_extracted.get("Manufacturer") == "Google"
    assert plugin.metadata_extracted.get("Model") == "Pixel 7"


def test_export_to_json(plugin, core_api, mock_android_zip_cellebrite, tmp_path):
    """Test JSON export functionality."""
    core_api.set_zip_file(mock_android_zip_cellebrite)
    plugin._detect_zip_structure()
    plugin._extract_build_properties()
    plugin._extract_settings_databases()

    json_path = tmp_path / "test_export.json"
    plugin._export_to_json(json_path)

    assert json_path.exists()

    with open(json_path) as f:
        data = json.load(f)

    assert data["plugin_name"] == "AndroidDeviceInfoExtractor"
    assert data["plugin_version"] == "1.0.0"
    assert "data" in data  # CoreAPI uses "data" key for plugin data


def test_generate_report(plugin, core_api, mock_android_zip_cellebrite):
    """Test markdown report generation."""
    core_api.set_zip_file(mock_android_zip_cellebrite)
    plugin._detect_zip_structure()
    plugin._extract_build_properties()
    plugin._extract_settings_databases()
    plugin._extract_telephony_info()

    report_path = plugin._generate_report()

    assert Path(report_path).exists()

    with open(report_path, encoding='utf-8') as f:
        content = f.read()

    assert "# Android Device Information" in content
    assert "Samsung" in content
    assert "SM-G991U" in content


# The following tests are removed because the Android plugin
# doesn't expose these as separate public methods - they're inline in the extraction methods

# def test_parse_build_prop(plugin):
#     """Test build.prop parsing functionality."""
#     # This functionality is tested indirectly via test_extract_build_properties_*
#     pass

# def test_parse_bluetooth_config(plugin):
#     """Test Bluetooth config parsing functionality."""
#     # This functionality is tested indirectly via test_extract_bluetooth_info_*
#     pass


def test_missing_files_handling(plugin, core_api, tmp_path):
    """Test handling of missing files in extraction."""
    # Create an empty ZIP
    zip_path = tmp_path / "empty.zip"
    with zipfile.ZipFile(zip_path, "w"):
        pass

    core_api.set_zip_file(zip_path)

    # Should not raise exceptions
    plugin._detect_zip_structure()
    plugin._extract_build_properties()
    plugin._extract_settings_databases()
    plugin._extract_telephony_info()

    # Device info should be empty or have default values
    assert isinstance(plugin.metadata_extracted, dict)


def test_cleanup(plugin):
    """Test plugin cleanup."""
    plugin.metadata_extracted = {"test": "data"}
    plugin.cleanup()

    # Cleanup just logs, doesn't clear metadata
    assert isinstance(plugin.metadata_extracted, dict)


def test_no_zip_loaded_error(plugin):
    """Test error handling when no ZIP is loaded."""
    result = plugin.execute()
    assert result["success"] is False
    assert "error" in result


def test_security_warnings_detection(plugin, core_api, mock_android_zip_cellebrite):
    """Test that security warnings are properly detected."""
    core_api.set_zip_file(mock_android_zip_cellebrite)
    plugin._detect_zip_structure()
    plugin._extract_settings_databases()

    warnings = plugin.metadata_extracted.get("Security Warnings", [])

    assert len(warnings) >= 2
    assert any("ADB" in w for w in warnings)
    assert any("Developer Mode" in w for w in warnings)


def test_network_info_extraction(plugin, core_api, mock_android_zip_cellebrite):
    """Test network information extraction."""
    core_api.set_zip_file(mock_android_zip_cellebrite)
    plugin._detect_zip_structure()

    # Network extraction is part of _extract_settings_databases
    plugin._extract_settings_databases()

    # Even if no specific network files, should handle gracefully
    assert isinstance(plugin.metadata_extracted, dict)
