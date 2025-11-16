"""
Tests for iOS Cellular Information Extractor Plugin

Tests the extraction of cellular information (IMEI, IMSI, ICCI, Phone Number)
from iOS device extractions.
"""

import zipfile
from pathlib import Path

import plistlib
import pytest

from yaft.core.api import CoreAPI
from plugins.ios_cellular_info_extractor import iOSCellularInfoExtractorPlugin


@pytest.fixture
def core_api(tmp_path):
    """Create a CoreAPI instance with temporary output directory."""
    api = CoreAPI()
    api.base_output_dir = tmp_path / "yaft_output"
    api.base_output_dir.mkdir(parents=True, exist_ok=True)
    return api


@pytest.fixture
def plugin(core_api):
    """Create plugin instance."""
    return iOSCellularInfoExtractorPlugin(core_api)


@pytest.fixture
def mock_cellular_plist_data():
    """Create mock cellular plist data structure."""
    return {
        'PersonalWallet': {
            'CTPhonebookEntry': {
                'CarrierEntitlements': {
                    'lastGoodImsi': '310260123456789',
                    'kEntitlementsSelfRegistrationUpdateImsi': '310260987654321',
                    'kEntitlementsSelfRegistrationUpdateImei': '356938035643809'
                }
            }
        },
        'LastKnownICCI': '89014103211118510720',
        'PhoneNumber': '+14155552671',
        'Airplane Mode': False,
        'MyPhoneNumber': '+14155552671',
    }


@pytest.fixture
def mock_zip_cellebrite_with_cellular(tmp_path, mock_cellular_plist_data):
    """Create mock ZIP in Cellebrite iOS format with cellular plist."""
    zip_path = tmp_path / "cellebrite_ios.zip"

    with zipfile.ZipFile(zip_path, "w") as zf:
        # Write cellular plist
        plist_bytes = plistlib.dumps(mock_cellular_plist_data)
        zf.writestr(
            "filesystem1/wireless/Library/Preferences/com.apple.commcenter.plist",
            plist_bytes
        )

    return zip_path


@pytest.fixture
def mock_zip_graykey_with_cellular(tmp_path, mock_cellular_plist_data):
    """Create mock ZIP in GrayKey iOS format with cellular plist."""
    zip_path = tmp_path / "graykey_ios.zip"

    with zipfile.ZipFile(zip_path, "w") as zf:
        # Write cellular plist
        plist_bytes = plistlib.dumps(mock_cellular_plist_data)
        zf.writestr(
            "wireless/Library/Preferences/com.apple.commcenter.plist",
            plist_bytes
        )

    return zip_path


@pytest.fixture
def mock_zip_minimal_cellular(tmp_path):
    """Create mock ZIP with minimal cellular data."""
    zip_path = tmp_path / "minimal_cellular.zip"

    minimal_data = {
        'LastKnownICCI': '89014103211118510720',
        'PhoneNumber': '+14155552671',
    }

    with zipfile.ZipFile(zip_path, "w") as zf:
        plist_bytes = plistlib.dumps(minimal_data)
        zf.writestr(
            "filesystem1/wireless/Library/Preferences/com.apple.commcenter.plist",
            plist_bytes
        )

    return zip_path


@pytest.fixture
def mock_zip_no_cellular(tmp_path):
    """Create mock ZIP without cellular plist."""
    zip_path = tmp_path / "no_cellular.zip"

    with zipfile.ZipFile(zip_path, "w") as zf:
        # Add some other file
        zf.writestr("filesystem1/System/Library/CoreServices/SystemVersion.plist", b"test")

    return zip_path


# ========== Plugin Metadata Tests ==========

def test_plugin_metadata(plugin):
    """Test plugin metadata."""
    metadata = plugin.metadata

    assert metadata.name == "iOSCellularInfoExtractor"
    assert metadata.version == "1.0.0"
    assert "cellular" in metadata.description.lower()
    assert "ios" in metadata.target_os
    assert metadata.enabled is True


def test_plugin_initialization(plugin):
    """Test plugin initialization."""
    plugin.initialize()

    assert plugin.cellular_data == []
    assert plugin.errors == []


def test_plugin_cleanup(plugin):
    """Test plugin cleanup."""
    plugin.cellular_data = [("test", "value")]
    plugin.errors = ["error1"]

    plugin.cleanup()

    assert plugin.cellular_data == []
    assert plugin.errors == []


# ========== Cellular Data Extraction Tests ==========

def test_extract_cellular_cellebrite_format(plugin, core_api, mock_zip_cellebrite_with_cellular):
    """Test cellular extraction from Cellebrite format."""
    core_api.set_zip_file(mock_zip_cellebrite_with_cellular)

    result = plugin.execute()

    assert result["success"] is True
    assert result["properties_found"] > 0
    assert Path(result["report_path"]).exists()
    assert Path(result["json_path"]).exists()

    # Check that key cellular data was extracted
    data_dict = dict(plugin.cellular_data)
    assert "Last Good IMSI" in data_dict
    assert data_dict["Last Good IMSI"] == "310260123456789"


def test_extract_cellular_graykey_format(plugin, core_api, mock_zip_graykey_with_cellular):
    """Test cellular extraction from GrayKey format."""
    core_api.set_zip_file(mock_zip_graykey_with_cellular)

    result = plugin.execute()

    assert result["success"] is True
    assert result["properties_found"] > 0

    # Check that key cellular data was extracted
    data_dict = dict(plugin.cellular_data)
    assert "Last Good IMSI" in data_dict
    assert data_dict["Last Good IMSI"] == "310260123456789"


def test_extract_imsi_values(plugin, core_api, mock_zip_cellebrite_with_cellular):
    """Test extraction of IMSI values."""
    core_api.set_zip_file(mock_zip_cellebrite_with_cellular)

    plugin.execute()

    data_dict = dict(plugin.cellular_data)

    assert "Last Good IMSI" in data_dict
    assert data_dict["Last Good IMSI"] == "310260123456789"

    assert "Self Registration Update IMSI" in data_dict
    assert data_dict["Self Registration Update IMSI"] == "310260987654321"


def test_extract_imei_value(plugin, core_api, mock_zip_cellebrite_with_cellular):
    """Test extraction of IMEI value."""
    core_api.set_zip_file(mock_zip_cellebrite_with_cellular)

    plugin.execute()

    data_dict = dict(plugin.cellular_data)

    assert "Self Registration Update IMEI" in data_dict
    assert data_dict["Self Registration Update IMEI"] == "356938035643809"


def test_extract_icci_value(plugin, core_api, mock_zip_cellebrite_with_cellular):
    """Test extraction of ICCI value."""
    core_api.set_zip_file(mock_zip_cellebrite_with_cellular)

    plugin.execute()

    data_dict = dict(plugin.cellular_data)

    assert "Last Known ICCI" in data_dict
    assert data_dict["Last Known ICCI"] == "89014103211118510720"


def test_extract_phone_number(plugin, core_api, mock_zip_cellebrite_with_cellular):
    """Test extraction of phone number."""
    core_api.set_zip_file(mock_zip_cellebrite_with_cellular)

    plugin.execute()

    data_dict = dict(plugin.cellular_data)

    assert "Phone Number" in data_dict
    assert data_dict["Phone Number"] == "+14155552671"


def test_extract_other_properties(plugin, core_api, mock_zip_cellebrite_with_cellular):
    """Test extraction of other cellular properties."""
    core_api.set_zip_file(mock_zip_cellebrite_with_cellular)

    plugin.execute()

    data_dict = dict(plugin.cellular_data)

    # Should capture other properties in the plist
    assert len(plugin.cellular_data) > 5
    assert "Airplane Mode" in data_dict or "MyPhoneNumber" in data_dict


def test_minimal_cellular_data(plugin, core_api, mock_zip_minimal_cellular):
    """Test extraction with minimal cellular data (no PersonalWallet)."""
    core_api.set_zip_file(mock_zip_minimal_cellular)

    result = plugin.execute()

    assert result["success"] is True

    data_dict = dict(plugin.cellular_data)

    # Should still extract ICCI and Phone Number
    assert "Last Known ICCI" in data_dict
    assert "Phone Number" in data_dict

    # Should not have IMSI/IMEI (not in PersonalWallet)
    assert "Last Good IMSI" not in data_dict


# ========== Error Handling Tests ==========

def test_no_zip_loaded(plugin, core_api):
    """Test error when no ZIP file is loaded."""
    result = plugin.execute()

    assert result["success"] is False
    assert "error" in result
    assert "No ZIP file loaded" in result["error"]


def test_no_cellular_plist_found(plugin, core_api, mock_zip_no_cellular):
    """Test error when cellular plist not found."""
    core_api.set_zip_file(mock_zip_no_cellular)

    result = plugin.execute()

    assert result["success"] is False
    assert len(plugin.errors) > 0
    assert any("not found" in err.lower() for err in plugin.errors)


def test_malformed_plist(plugin, core_api, tmp_path):
    """Test handling of malformed plist data."""
    zip_path = tmp_path / "malformed.zip"

    with zipfile.ZipFile(zip_path, "w") as zf:
        # Write invalid plist data
        zf.writestr(
            "filesystem1/wireless/Library/Preferences/com.apple.commcenter.plist",
            b"invalid plist data"
        )

    core_api.set_zip_file(zip_path)

    result = plugin.execute()

    assert result["success"] is False
    assert len(plugin.errors) > 0


def test_malformed_personal_wallet(plugin, core_api, tmp_path):
    """Test handling of malformed PersonalWallet structure."""
    zip_path = tmp_path / "malformed_wallet.zip"

    # Create plist with invalid PersonalWallet structure
    bad_data = {
        'PersonalWallet': "invalid_structure",  # Should be dict
        'PhoneNumber': '+14155552671',
    }

    with zipfile.ZipFile(zip_path, "w") as zf:
        plist_bytes = plistlib.dumps(bad_data)
        zf.writestr(
            "filesystem1/wireless/Library/Preferences/com.apple.commcenter.plist",
            plist_bytes
        )

    core_api.set_zip_file(zip_path)

    result = plugin.execute()

    # Should still succeed but with errors logged
    # Phone Number should still be extracted
    data_dict = dict(plugin.cellular_data)
    assert "Phone Number" in data_dict


# ========== Report Generation Tests ==========

def test_report_generation(plugin, core_api, mock_zip_cellebrite_with_cellular):
    """Test report generation."""
    core_api.set_zip_file(mock_zip_cellebrite_with_cellular)

    result = plugin.execute()

    assert result["success"] is True

    report_path = Path(result["report_path"])
    assert report_path.exists()
    assert report_path.suffix == ".md"

    # Read report and check contents
    report_content = report_path.read_text(encoding='utf-8')

    assert "iOS Cellular Information Extraction Report" in report_content
    assert "Executive Summary" in report_content
    assert "Key Device Identifiers" in report_content
    assert "310260123456789" in report_content  # IMSI
    assert "356938035643809" in report_content  # IMEI


def test_json_export(plugin, core_api, mock_zip_cellebrite_with_cellular):
    """Test JSON data export."""
    core_api.set_zip_file(mock_zip_cellebrite_with_cellular)

    result = plugin.execute()

    json_path = Path(result["json_path"])
    assert json_path.exists()
    assert json_path.suffix == ".json"

    # Read and validate JSON
    import json
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    assert "plugin_name" in data
    assert data["plugin_name"] == "iOSCellularInfoExtractor"

    assert "data" in data
    assert "cellular_properties" in data["data"]
    assert "statistics" in data["data"]

    stats = data["data"]["statistics"]
    assert stats["has_imsi"] is True
    assert stats["has_imei"] is True
    assert stats["has_icci"] is True
    assert stats["has_phone_number"] is True


def test_report_includes_errors(plugin, core_api, tmp_path):
    """Test that errors are included in report."""
    # Create a plist that will cause a parsing error in PersonalWallet
    zip_path = tmp_path / "error_case.zip"

    bad_data = {
        'PersonalWallet': {
            'Entry': {
                'CarrierEntitlements': {
                    # Missing the expected keys, should trigger error in parsing
                }
            }
        },
        'PhoneNumber': '+14155552671',
    }

    with zipfile.ZipFile(zip_path, "w") as zf:
        plist_bytes = plistlib.dumps(bad_data)
        zf.writestr(
            "filesystem1/wireless/Library/Preferences/com.apple.commcenter.plist",
            plist_bytes
        )

    core_api.set_zip_file(zip_path)

    # Execute and check for errors in parsing PersonalWallet
    plugin._extract_cellular_info()

    # Manually add an error to test error reporting
    plugin.errors.append("Test error for reporting")

    # Generate report with errors
    report_path = plugin._generate_report()
    report_content = report_path.read_text(encoding='utf-8')

    assert "Errors Encountered" in report_content
    assert "Test error for reporting" in report_content


# ========== Integration Tests ==========

def test_full_workflow_cellebrite(plugin, core_api, mock_zip_cellebrite_with_cellular):
    """Test complete workflow with Cellebrite extraction."""
    core_api.set_zip_file(mock_zip_cellebrite_with_cellular)

    # Set case identifiers
    core_api.set_case_identifiers("examiner1", "CASE2024-001", "EV-001")

    # Execute plugin
    result = plugin.execute()

    assert result["success"] is True
    assert result["properties_found"] >= 5

    # Verify report exists in case-based directory
    report_path = Path(result["report_path"])
    assert report_path.exists()
    assert "CASE2024-001" in str(report_path)
    assert "EV-001" in str(report_path)

    # Verify JSON exists
    json_path = Path(result["json_path"])
    assert json_path.exists()


def test_full_workflow_graykey(plugin, core_api, mock_zip_graykey_with_cellular):
    """Test complete workflow with GrayKey extraction."""
    core_api.set_zip_file(mock_zip_graykey_with_cellular)

    result = plugin.execute()

    assert result["success"] is True

    # Verify all major identifiers extracted
    data_dict = dict(plugin.cellular_data)

    assert "Last Good IMSI" in data_dict
    assert "Self Registration Update IMEI" in data_dict
    assert "Last Known ICCI" in data_dict
    assert "Phone Number" in data_dict


def test_statistics_accuracy(plugin, core_api, mock_zip_cellebrite_with_cellular):
    """Test that statistics are accurately calculated."""
    core_api.set_zip_file(mock_zip_cellebrite_with_cellular)

    result = plugin.execute()

    json_path = Path(result["json_path"])

    import json
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    stats = data["data"]["statistics"]

    # Verify statistics match actual data
    has_imsi = any("IMSI" in p["property"] for p in data["data"]["cellular_properties"])
    has_imei = any("IMEI" in p["property"] for p in data["data"]["cellular_properties"])
    has_icci = any("ICCI" in p["property"] for p in data["data"]["cellular_properties"])
    has_phone = any("Phone Number" in p["property"] for p in data["data"]["cellular_properties"])

    assert stats["has_imsi"] == has_imsi
    assert stats["has_imei"] == has_imei
    assert stats["has_icci"] == has_icci
    assert stats["has_phone_number"] == has_phone


# ========== Edge Cases ==========

def test_empty_cellular_values(plugin, core_api, tmp_path):
    """Test handling of empty/null cellular values."""
    zip_path = tmp_path / "empty_values.zip"

    empty_data = {
        'PersonalWallet': {
            'Entry': {
                'CarrierEntitlements': {
                    'lastGoodImsi': '',
                    'kEntitlementsSelfRegistrationUpdateImei': ''
                }
            }
        },
        'LastKnownICCI': '',
        'PhoneNumber': '',
    }

    with zipfile.ZipFile(zip_path, "w") as zf:
        plist_bytes = plistlib.dumps(empty_data)
        zf.writestr(
            "filesystem1/wireless/Library/Preferences/com.apple.commcenter.plist",
            plist_bytes
        )

    core_api.set_zip_file(zip_path)

    result = plugin.execute()

    # Should succeed even with empty values
    assert result["success"] is True


def test_very_long_property_value(plugin, core_api, tmp_path):
    """Test handling of very long property values."""
    zip_path = tmp_path / "long_value.zip"

    long_value = "x" * 500  # Very long value

    long_data = {
        'SomeVeryLongProperty': long_value,
        'PhoneNumber': '+14155552671',
    }

    with zipfile.ZipFile(zip_path, "w") as zf:
        plist_bytes = plistlib.dumps(long_data)
        zf.writestr(
            "filesystem1/wireless/Library/Preferences/com.apple.commcenter.plist",
            plist_bytes
        )

    core_api.set_zip_file(zip_path)

    result = plugin.execute()

    assert result["success"] is True

    # Check that long value is truncated
    data_dict = dict(plugin.cellular_data)
    if 'SomeVeryLongProperty' in data_dict:
        assert len(data_dict['SomeVeryLongProperty']) <= 203  # 200 + "..."
