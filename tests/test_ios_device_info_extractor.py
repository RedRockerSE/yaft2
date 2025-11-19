"""
Tests for iOS Device Info Extractor Plugin.
"""

import json
import zipfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import plistlib
import pytest

from yaft.core.api import CoreAPI
from plugins.ios_device_info_extractor import iOSDeviceInfoExtractorPlugin


@pytest.fixture
def core_api(tmp_path):
    """Create a CoreAPI instance with a temporary directory."""
    api = CoreAPI()
    api.base_output_dir = tmp_path / "yaft_output"
    api.base_output_dir.mkdir(parents=True, exist_ok=True)
    return api


@pytest.fixture
def plugin(core_api):
    """Create an iOS Device Info Extractor plugin instance."""
    return iOSDeviceInfoExtractorPlugin(core_api)


@pytest.fixture
def mock_ios_zip_cellebrite(tmp_path):
    """Create a mock iOS extraction ZIP in Cellebrite format."""
    zip_path = tmp_path / "ios_extraction_cellebrite.zip"

    # Create mock plist data
    system_version_data = {
        "ProductVersion": "16.5.1",
        "ProductBuildVersion": "20F75",
        "ProductName": "iPhone OS",
    }

    data_ark_data = {
        "SerialNumber": "F2LW12345ABC",
        "UniqueDeviceID": "00008030-001A12345678901E",
        "DeviceName": "John's iPhone",
        "ProductType": "iPhone14,2",
        "HardwareModel": "D53gAP",
    }

    cellular_data = {
        "kCTIMEI": "123456789012345",
        "kCTMEID": "12345678901234",
        "kCTICCID": "89012345678901234567",
    }

    carrier_data = {
        "ReportedPhoneNumber": "+1-555-123-4567",
        "OperatorName": "AT&T",
    }

    global_prefs_data = {
        "AppleLanguages": ["en-US"],
        "AppleLocale": "en_US",
        "Country": "US",
    }

    backup_data = {
        "LastBackupDate": "2024-01-15T10:30:00Z",
        "BackupComputerName": "DESKTOP-ABC123",
        "IsFullBackup": True,
        "IsEncrypted": False,
    }

    with zipfile.ZipFile(zip_path, "w") as zf:
        # Cellebrite format uses "filesystem1/" prefix
        zf.writestr(
            "filesystem1/System/Library/CoreServices/SystemVersion.plist",
            plistlib.dumps(system_version_data),
        )
        zf.writestr(
            "filesystem1/private/var/mobile/Library/Preferences/com.apple.MobileBackup.plist",
            plistlib.dumps(backup_data),
        )
        # Add data_ark.plist (device identifiers)
        zf.writestr(
            "filesystem1/private/var/containers/Shared/SystemGroup/systemgroup.com.apple.mobileactivationd/Library/internal/data_ark.plist",
            plistlib.dumps(data_ark_data),
        )
        # Add commcenter plists (cellular and carrier info)
        zf.writestr(
            "filesystem1/private/var/wireless/Library/Preferences/com.apple.commcenter.device_specific_nobackup.plist",
            plistlib.dumps(cellular_data),
        )
        zf.writestr(
            "filesystem1/private/var/wireless/Library/Preferences/com.apple.commcenter.plist",
            plistlib.dumps(carrier_data),
        )
        zf.writestr(
            "filesystem1/private/var/mobile/Library/Preferences/.GlobalPreferences.plist",
            plistlib.dumps(global_prefs_data),
        )

    return zip_path


@pytest.fixture
def mock_ios_zip_graykey(tmp_path):
    """Create a mock iOS extraction ZIP in GrayKey format."""
    zip_path = tmp_path / "ios_extraction_graykey.zip"

    # Create mock plist data
    system_version_data = {
        "ProductVersion": "15.7",
        "ProductBuildVersion": "19H12",
        "ProductName": "iPhone OS",
    }

    data_ark_data = {
        "SerialNumber": "C02YW1234567",
        "UniqueDeviceID": "00008030-001234567890ABCD",
        "DeviceName": "Jane's iPhone",
        "DeviceClass": "iPhone",
        "ProductType": "iPhone13,2",
    }

    with zipfile.ZipFile(zip_path, "w") as zf:
        # GrayKey format has no prefix
        zf.writestr(
            "System/Library/CoreServices/SystemVersion.plist",
            plistlib.dumps(system_version_data),
        )
        # Add data_ark.plist (device identifiers)
        zf.writestr(
            "private/var/containers/Shared/SystemGroup/systemgroup.com.apple.mobileactivationd/Library/internal/data_ark.plist",
            plistlib.dumps(data_ark_data),
        )
        zf.writestr(
            "private/var/wireless/Library/Preferences/com.apple.commcenter.device_specific_nobackup.plist",
            plistlib.dumps(data_ark_data),
        )

    return zip_path


def test_plugin_metadata(plugin):
    """Test that plugin metadata is correctly defined."""
    metadata = plugin.metadata

    assert metadata.name == "iOSDeviceInfoExtractor"
    assert metadata.version == "1.1.0"
    assert "ios" in metadata.target_os
    assert metadata.enabled is True
    assert "device metadata" in metadata.description.lower()


def test_initialize(plugin):
    """Test plugin initialization."""
    plugin.initialize()
    assert plugin.metadata_extracted == {}
    assert plugin.errors == []
    assert plugin.zip_prefix == ''


def test_detect_zip_structure_cellebrite(plugin, core_api, mock_ios_zip_cellebrite):
    """Test detection of Cellebrite ZIP structure."""
    core_api.set_zip_file(mock_ios_zip_cellebrite)

    plugin._detect_zip_structure()

    assert plugin.zip_prefix in ["filesystem1/", "filesystem/"]


def test_detect_zip_structure_graykey(plugin, core_api, mock_ios_zip_graykey):
    """Test detection of GrayKey ZIP structure."""
    core_api.set_zip_file(mock_ios_zip_graykey)

    plugin._detect_zip_structure()

    assert plugin.zip_prefix == ""


def test_extract_system_version_cellebrite(plugin, core_api, mock_ios_zip_cellebrite):
    """Test extraction of system version from Cellebrite format."""
    core_api.set_zip_file(mock_ios_zip_cellebrite)
    plugin._detect_zip_structure()

    plugin._extract_system_version()

    system_version = plugin.metadata_extracted.get("system_version", {})
    assert system_version.get("product_version") == "16.5.1"
    assert system_version.get("product_build_version") == "20F75"
    assert system_version.get("product_name") == "iPhone OS"


def test_extract_system_version_graykey(plugin, core_api, mock_ios_zip_graykey):
    """Test extraction of system version from GrayKey format."""
    core_api.set_zip_file(mock_ios_zip_graykey)
    plugin._detect_zip_structure()

    plugin._extract_system_version()

    system_version = plugin.metadata_extracted.get("system_version", {})
    assert system_version.get("product_version") == "15.7"
    assert system_version.get("product_build_version") == "19H12"


def test_extract_device_identifiers_cellebrite(plugin, core_api, mock_ios_zip_cellebrite):
    """Test extraction of device identifiers from Cellebrite format."""
    core_api.set_zip_file(mock_ios_zip_cellebrite)
    plugin._detect_zip_structure()

    plugin._extract_device_identifiers()

    device_ids = plugin.metadata_extracted.get("device_identifiers", {})
    assert device_ids.get("serial_number") == "F2LW12345ABC"
    assert device_ids.get("unique_device_id") == "00008030-001A12345678901E"
    assert device_ids.get("device_name") == "John's iPhone"


def test_extract_cellular_info_cellebrite(plugin, core_api, mock_ios_zip_cellebrite):
    """Test extraction of cellular info from Cellebrite format."""
    core_api.set_zip_file(mock_ios_zip_cellebrite)
    plugin._detect_zip_structure()

    plugin._extract_cellular_info()

    cellular = plugin.metadata_extracted.get("cellular_info", {})
    assert cellular.get("imei") == "123456789012345"
    assert cellular.get("meid") == "12345678901234"
    assert cellular.get("iccid") == "89012345678901234567"


def test_extract_carrier_info_cellebrite(plugin, core_api, mock_ios_zip_cellebrite):
    """Test extraction of carrier info from Cellebrite format."""
    core_api.set_zip_file(mock_ios_zip_cellebrite)
    plugin._detect_zip_structure()

    plugin._extract_carrier_info()

    carrier = plugin.metadata_extracted.get("carrier_info", {})
    assert carrier.get("phone_number") == "+1-555-123-4567"
    assert carrier.get("operator_name") == "AT&T"


def test_extract_timezone_locale_cellebrite(plugin, core_api, mock_ios_zip_cellebrite):
    """Test extraction of timezone and locale from Cellebrite format."""
    core_api.set_zip_file(mock_ios_zip_cellebrite)
    plugin._detect_zip_structure()

    plugin._extract_timezone_locale()

    tz_locale = plugin.metadata_extracted.get("timezone_locale", {})
    assert tz_locale.get("locale") == "en_US"
    assert "en-US" in str(tz_locale.get("languages", []))


def test_extract_backup_info_cellebrite(plugin, core_api, mock_ios_zip_cellebrite):
    """Test extraction of backup info from Cellebrite format."""
    core_api.set_zip_file(mock_ios_zip_cellebrite)
    plugin._detect_zip_structure()

    plugin._extract_backup_info()

    backup = plugin.metadata_extracted.get("backup_info", {})
    assert backup.get("last_backup_date") is not None
    assert backup.get("backup_computer_name") == "DESKTOP-ABC123"


def test_execute_full_extraction_cellebrite(plugin, core_api, mock_ios_zip_cellebrite):
    """Test full execution of plugin with Cellebrite format."""
    core_api.set_zip_file(mock_ios_zip_cellebrite)

    result = plugin.execute()

    assert result["success"] is True
    assert "report_path" in result
    assert Path(result["report_path"]).exists()

    # Verify metadata was collected
    assert len(plugin.metadata_extracted) > 0
    system_version = plugin.metadata_extracted.get("system_version", {})
    device_ids = plugin.metadata_extracted.get("device_identifiers", {})
    assert system_version.get("product_version") == "16.5.1"
    assert device_ids.get("serial_number") == "F2LW12345ABC"


def test_execute_full_extraction_graykey(plugin, core_api, mock_ios_zip_graykey):
    """Test full execution of plugin with GrayKey format."""
    core_api.set_zip_file(mock_ios_zip_graykey)

    result = plugin.execute()

    assert result["success"] is True
    assert "report_path" in result
    assert Path(result["report_path"]).exists()

    # Verify metadata was collected
    assert len(plugin.metadata_extracted) > 0
    system_version = plugin.metadata_extracted.get("system_version", {})
    device_ids = plugin.metadata_extracted.get("device_identifiers", {})
    assert system_version.get("product_version") == "15.7"
    assert device_ids.get("serial_number") == "C02YW1234567"


def test_export_to_json(plugin, core_api, mock_ios_zip_cellebrite, tmp_path):
    """Test JSON export functionality."""
    core_api.set_zip_file(mock_ios_zip_cellebrite)
    plugin._detect_zip_structure()
    plugin._extract_system_version()
    plugin._extract_device_identifiers()

    json_path = tmp_path / "test_export.json"
    plugin._export_to_json(json_path)

    assert json_path.exists()

    with open(json_path) as f:
        data = json.load(f)

    assert data["plugin_name"] == "iOSDeviceInfoExtractor"
    assert data["plugin_version"] == "1.1.0"
    assert "data" in data  # CoreAPI uses "data" key for plugin data
    assert data["extraction_source"] == "cellebrite_ios"


def test_generate_report(plugin, core_api, mock_ios_zip_cellebrite):
    """Test markdown report generation."""
    core_api.set_zip_file(mock_ios_zip_cellebrite)
    plugin._detect_zip_structure()
    plugin._extract_system_version()
    plugin._extract_device_identifiers()
    plugin._extract_cellular_info()

    report_path = plugin._generate_report()

    assert Path(report_path).exists()

    with open(report_path) as f:
        content = f.read()

    assert "# iOS Device Information" in content
    assert "16.5.1" in content
    assert "## System Information" in content


def test_missing_files_handling(plugin, core_api, tmp_path):
    """Test handling of missing files in extraction."""
    # Create an empty ZIP
    zip_path = tmp_path / "empty.zip"
    with zipfile.ZipFile(zip_path, "w"):
        pass

    core_api.set_zip_file(zip_path)

    # Should not raise exceptions
    plugin._detect_zip_structure()
    plugin._extract_system_version()
    plugin._extract_device_identifiers()

    # Metadata should be empty or have default values
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
