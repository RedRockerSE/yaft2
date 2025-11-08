"""
Tests for Android App Info Extractor Plugin.
"""

import json
import sqlite3
import zipfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from yaft.core.api import CoreAPI
from plugins.android_app_info_extractor import AndroidAppInfoExtractorPlugin


@pytest.fixture
def core_api(tmp_path):
    """Create a CoreAPI instance with a temporary directory."""
    api = CoreAPI()
    api.base_output_dir = tmp_path / "yaft_output"
    api.base_output_dir.mkdir(parents=True, exist_ok=True)
    return api


@pytest.fixture
def plugin(core_api):
    """Create an Android App Info Extractor plugin instance."""
    return AndroidAppInfoExtractorPlugin(core_api)


@pytest.fixture
def mock_android_zip(tmp_path):
    """Create a mock Android extraction ZIP with packages.xml."""
    zip_path = tmp_path / "android_apps.zip"

    # Create mock packages.xml
    packages_xml_content = """<?xml version='1.0' encoding='utf-8' standalone='yes' ?>
<packages>
    <package name="com.android.systemui"
             codePath="/system/priv-app/SystemUI"
             nativeLibraryPath="/system/lib64"
             version="33"
             userId="1000"
             flags="1"
             ft="1704067200000"
             it="1704067200000"
             ut="1704067200000">
        <perms>
            <item name="android.permission.STATUS_BAR" granted="true" />
            <item name="android.permission.EXPAND_STATUS_BAR" granted="true" />
        </perms>
    </package>
    <package name="com.whatsapp"
             codePath="/data/app/~~abc123/com.whatsapp-xyz789"
             version="232054"
             userId="10123"
             flags="0"
             installer="com.android.vending"
             ft="1704153600000"
             it="1704153600000">
        <perms>
            <item name="android.permission.CAMERA" granted="true" />
            <item name="android.permission.READ_CONTACTS" granted="true" />
            <item name="android.permission.RECORD_AUDIO" granted="true" />
        </perms>
    </package>
    <package name="com.facebook.katana"
             codePath="/data/app/~~def456/com.facebook.katana-uvw123"
             version="405012345"
             userId="10124"
             flags="0"
             installer="com.android.vending"
             ft="1704240000000">
        <perms>
            <item name="android.permission.CAMERA" granted="true" />
            <item name="android.permission.ACCESS_FINE_LOCATION" granted="true" />
        </perms>
    </package>
</packages>
"""

    # Create mock packages.list
    packages_list_content = """com.android.systemui 1000 0 /data/user/0/com.android.systemui default:targetSdkVersion=33
com.whatsapp 10123 0 /data/user/0/com.whatsapp default:targetSdkVersion=31
com.facebook.katana 10124 1 /data/user/0/com.facebook.katana default:targetSdkVersion=30
"""

    # Create mock usage stats XML
    usage_stats_content = """<?xml version='1.0' encoding='utf-8' standalone='yes' ?>
<usage-history>
    <app package="com.whatsapp" lastTimeUsed="1704326400000" totalTimeInForeground="3600000" launchCount="150" />
    <app package="com.facebook.katana" lastTimeUsed="1704240000000" totalTimeInForeground="1800000" launchCount="75" />
</usage-history>
"""

    with zipfile.ZipFile(zip_path, "w") as zf:
        # Use "fs/" prefix for Cellebrite format
        zf.writestr("fs/data/system/packages.xml", packages_xml_content)
        zf.writestr("fs/data/system/packages.list", packages_list_content)
        zf.writestr("fs/data/system/usagestats/0/usage-history.xml", usage_stats_content)

    return zip_path


@pytest.fixture
def mock_android_zip_graykey(tmp_path):
    """Create a mock Android extraction ZIP in GrayKey format (no prefix)."""
    zip_path = tmp_path / "android_apps_graykey.zip"

    packages_xml_content = """<?xml version='1.0' encoding='utf-8' standalone='yes' ?>
<packages>
    <package name="com.google.android.gms"
             codePath="/system/priv-app/GmsCore"
             version="233012345"
             userId="10001"
             flags="129"
             installer="preload">
        <perms>
            <item name="android.permission.ACCESS_FINE_LOCATION" granted="true" />
        </perms>
    </package>
</packages>
"""

    with zipfile.ZipFile(zip_path, "w") as zf:
        # GrayKey format has no prefix
        zf.writestr("data/system/packages.xml", packages_xml_content)

    return zip_path


def test_plugin_metadata(plugin):
    """Test that plugin metadata is correctly defined."""
    metadata = plugin.metadata

    assert metadata.name == "AndroidAppInfoExtractor"
    assert metadata.version == "1.0.0"
    assert "android" in metadata.target_os
    assert metadata.enabled is True
    assert "app" in metadata.description.lower()


def test_initialize(plugin):
    """Test plugin initialization."""
    plugin.initialize()
    assert plugin.apps == []
    assert plugin.errors == []
    assert plugin.zip_prefix == ''


def test_detect_zip_structure_cellebrite(plugin, core_api, mock_android_zip):
    """Test detection of Cellebrite ZIP structure."""
    core_api.set_zip_file(mock_android_zip)

    plugin._detect_zip_structure()

    assert plugin.zip_prefix == "fs/"


def test_detect_zip_structure_graykey(plugin, core_api, mock_android_zip_graykey):
    """Test detection of GrayKey ZIP structure."""
    core_api.set_zip_file(mock_android_zip_graykey)

    plugin._detect_zip_structure()

    assert plugin.zip_prefix == ""


def test_parse_packages_xml(plugin, core_api, mock_android_zip):
    """Test parsing of packages.xml."""
    core_api.set_zip_file(mock_android_zip)
    plugin._detect_zip_structure()

    packages = plugin._parse_packages_xml()

    assert len(packages) == 3
    assert "com.whatsapp" in packages
    assert "com.facebook.katana" in packages
    assert "com.android.systemui" in packages

    whatsapp = packages["com.whatsapp"]
    assert whatsapp["package_name"] == "com.whatsapp"
    assert whatsapp["version_code"] == "232054"
    assert whatsapp["installer"] == "com.android.vending"
    assert "android.permission.CAMERA" in whatsapp["granted_permissions"]
    assert whatsapp["is_system_app"] is False


def test_parse_packages_list(plugin, core_api, mock_android_zip):
    """Test parsing of packages.list."""
    core_api.set_zip_file(mock_android_zip)
    plugin._detect_zip_structure()

    packages = plugin._parse_packages_list()

    assert len(packages) == 3
    assert "com.whatsapp" in packages

    whatsapp = packages["com.whatsapp"]
    assert whatsapp["package_name"] == "com.whatsapp"
    assert whatsapp["user_id"] == "10123"
    assert whatsapp["debuggable"] is False

    facebook = packages["com.facebook.katana"]
    assert facebook["debuggable"] is True  # debug_flag = 1


def test_parse_usage_stats(plugin, core_api, mock_android_zip):
    """Test parsing of usage stats."""
    core_api.set_zip_file(mock_android_zip)
    plugin._detect_zip_structure()

    usage = plugin._parse_usage_stats()

    assert len(usage) == 2
    assert "com.whatsapp" in usage
    assert "com.facebook.katana" in usage

    whatsapp = usage["com.whatsapp"]
    assert whatsapp["last_time_used"] == "1704326400000"
    # launch_count is optional
    if "launch_count" in whatsapp:
        assert whatsapp["launch_count"] == "150"


def test_merge_app_data(plugin, core_api, mock_android_zip):
    """Test merging data from multiple sources."""
    core_api.set_zip_file(mock_android_zip)
    plugin._detect_zip_structure()

    packages_xml = plugin._parse_packages_xml()
    packages_list = plugin._parse_packages_list()
    usage_stats = plugin._parse_usage_stats()

    merged = plugin._merge_app_data(packages_xml, packages_list, usage_stats)

    assert len(merged) == 3

    # Find WhatsApp in merged data
    whatsapp = next((app for app in merged if app["package_name"] == "com.whatsapp"), None)
    assert whatsapp is not None
    assert "granted_permissions" in whatsapp
    assert "debuggable" in whatsapp
    assert "last_time_used" in whatsapp


def test_categorize_apps(plugin, core_api, mock_android_zip):
    """Test app categorization."""
    core_api.set_zip_file(mock_android_zip)
    plugin._detect_zip_structure()

    packages_xml = plugin._parse_packages_xml()
    packages_list = plugin._parse_packages_list()
    usage_stats = plugin._parse_usage_stats()

    plugin.apps = plugin._merge_app_data(packages_xml, packages_list, usage_stats)
    plugin._categorize_apps()

    # Find apps by category
    whatsapp = next((app for app in plugin.apps if app["package_name"] == "com.whatsapp"), None)
    facebook = next((app for app in plugin.apps if app["package_name"] == "com.facebook.katana"), None)
    systemui = next((app for app in plugin.apps if app["package_name"] == "com.android.systemui"), None)

    assert whatsapp["category"] == "messaging"
    assert facebook["category"] == "facebook"
    assert systemui["category"] == "system"  # com.android.systemui has is_system_app=True


def test_suspicious_app_flagging(plugin, core_api, mock_android_zip):
    """Test flagging of suspicious apps."""
    core_api.set_zip_file(mock_android_zip)
    plugin._detect_zip_structure()

    packages_xml = plugin._parse_packages_xml()
    packages_list = plugin._parse_packages_list()
    usage_stats = plugin._parse_usage_stats()

    plugin.apps = plugin._merge_app_data(packages_xml, packages_list, usage_stats)
    plugin._categorize_apps()

    # Facebook has debuggable flag set to True
    facebook = next((app for app in plugin.apps if app["package_name"] == "com.facebook.katana"), None)
    assert facebook.get("suspicious_flag") == "debuggable"


def test_execute_full_extraction(plugin, core_api, mock_android_zip):
    """Test full execution of plugin."""
    core_api.set_zip_file(mock_android_zip)

    result = plugin.execute()

    assert result["success"] is True
    assert result["total_apps"] == 3
    assert "report_path" in result
    assert "json_path" in result
    assert Path(result["report_path"]).exists()
    assert Path(result["json_path"]).exists()


def test_execute_graykey_format(plugin, core_api, mock_android_zip_graykey):
    """Test execution with GrayKey format."""
    core_api.set_zip_file(mock_android_zip_graykey)

    result = plugin.execute()

    assert result["success"] is True
    assert result["total_apps"] >= 1


def test_export_to_json(plugin, core_api, mock_android_zip, tmp_path):
    """Test JSON export functionality."""
    core_api.set_zip_file(mock_android_zip)
    plugin._detect_zip_structure()

    packages_xml = plugin._parse_packages_xml()
    packages_list = plugin._parse_packages_list()
    usage_stats = plugin._parse_usage_stats()

    plugin.apps = plugin._merge_app_data(packages_xml, packages_list, usage_stats)

    json_path = tmp_path / "test_export.json"
    plugin._export_to_json(json_path)

    assert json_path.exists()

    with open(json_path) as f:
        data = json.load(f)

    assert data["plugin_name"] == "AndroidAppInfoExtractor"
    assert data["plugin_version"] == "1.0.0"
    assert "data" in data
    assert "applications" in data["data"]


def test_generate_report(plugin, core_api, mock_android_zip):
    """Test markdown report generation."""
    core_api.set_zip_file(mock_android_zip)
    plugin._detect_zip_structure()

    packages_xml = plugin._parse_packages_xml()
    packages_list = plugin._parse_packages_list()
    usage_stats = plugin._parse_usage_stats()

    plugin.apps = plugin._merge_app_data(packages_xml, packages_list, usage_stats)
    plugin._categorize_apps()

    report_path = plugin._generate_report()

    assert Path(report_path).exists()

    with open(report_path, encoding='utf-8') as f:
        content = f.read()

    assert "Android Application Information" in content
    assert "com.whatsapp" in content or "whatsapp" in content.lower()


def test_missing_files_handling(plugin, core_api, tmp_path):
    """Test handling of missing files in extraction."""
    # Create an empty ZIP
    zip_path = tmp_path / "empty.zip"
    with zipfile.ZipFile(zip_path, "w"):
        pass

    core_api.set_zip_file(zip_path)

    # Should not raise exceptions
    plugin._detect_zip_structure()
    packages_xml = plugin._parse_packages_xml()
    packages_list = plugin._parse_packages_list()
    usage_stats = plugin._parse_usage_stats()

    assert packages_xml == {}
    assert packages_list == {}
    assert usage_stats == {}


def test_cleanup(plugin):
    """Test plugin cleanup."""
    plugin.apps = [{"test": "data"}]
    plugin.cleanup()

    # Cleanup just logs, doesn't clear data
    assert isinstance(plugin.apps, list)


def test_no_zip_loaded_error(plugin):
    """Test error handling when no ZIP is loaded."""
    result = plugin.execute()
    assert result["success"] is False
    assert "error" in result


def test_system_app_detection(plugin, core_api, mock_android_zip):
    """Test that system apps are correctly identified."""
    core_api.set_zip_file(mock_android_zip)
    plugin._detect_zip_structure()

    packages = plugin._parse_packages_xml()

    systemui = packages["com.android.systemui"]
    # flags=1 means it's a system app (SYSTEM flag = 0x00000001)
    assert systemui["is_system_app"] is True

    whatsapp = packages["com.whatsapp"]
    # flags=0 means it's not a system app
    assert whatsapp["is_system_app"] is False


def test_permission_extraction(plugin, core_api, mock_android_zip):
    """Test that permissions are correctly extracted."""
    core_api.set_zip_file(mock_android_zip)
    plugin._detect_zip_structure()

    packages = plugin._parse_packages_xml()

    whatsapp = packages["com.whatsapp"]
    perms = whatsapp["granted_permissions"]

    assert "android.permission.CAMERA" in perms
    assert "android.permission.READ_CONTACTS" in perms
    assert "android.permission.RECORD_AUDIO" in perms
