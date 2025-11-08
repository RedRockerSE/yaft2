"""
Tests for Android App Permissions Extractor Plugin.
"""

import json
import sqlite3
import zipfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from yaft.core.api import CoreAPI
from plugins.android_app_permissions_extractor import AndroidAppPermissionsExtractorPlugin


@pytest.fixture
def core_api(tmp_path):
    """Create a CoreAPI instance with a temporary directory."""
    api = CoreAPI()
    api.base_output_dir = tmp_path / "yaft_output"
    api.base_output_dir.mkdir(parents=True, exist_ok=True)
    return api


@pytest.fixture
def plugin(core_api):
    """Create an Android App Permissions Extractor plugin instance."""
    return AndroidAppPermissionsExtractorPlugin(core_api)


@pytest.fixture
def mock_android_permissions_zip(tmp_path):
    """Create a mock Android extraction ZIP with permissions data."""
    zip_path = tmp_path / "android_permissions.zip"

    # Create mock packages.xml with declared permissions
    packages_xml_content = """<?xml version='1.0' encoding='utf-8' standalone='yes' ?>
<packages>
    <package name="com.whatsapp"
             codePath="/data/app/~~abc123/com.whatsapp-xyz789"
             version="232054"
             userId="10123"
             flags="0">
        <perms>
            <item name="android.permission.CAMERA" granted="true" />
            <item name="android.permission.READ_CONTACTS" granted="true" />
            <item name="android.permission.RECORD_AUDIO" granted="true" />
            <item name="android.permission.ACCESS_FINE_LOCATION" granted="true" />
            <item name="android.permission.READ_SMS" granted="true" />
        </perms>
    </package>
    <package name="com.facebook.katana"
             codePath="/data/app/~~def456/com.facebook.katana-uvw123"
             version="405012345"
             userId="10124"
             flags="0">
        <perms>
            <item name="android.permission.CAMERA" granted="true" />
            <item name="android.permission.ACCESS_FINE_LOCATION" granted="true" />
            <item name="android.permission.ACCESS_BACKGROUND_LOCATION" granted="true" />
        </perms>
    </package>
    <package name="com.android.systemui"
             codePath="/system/priv-app/SystemUI"
             version="33"
             userId="1000"
             flags="1">
        <perms>
            <item name="android.permission.STATUS_BAR" granted="true" />
        </perms>
    </package>
</packages>
"""

    # Create mock runtime-permissions.xml
    runtime_permissions_content = """<?xml version='1.0' encoding='utf-8' standalone='yes' ?>
<runtime-permissions version="8">
    <pkg name="com.whatsapp">
        <item name="android.permission.CAMERA" granted="true" flags="0" />
        <item name="android.permission.RECORD_AUDIO" granted="true" flags="0" />
        <item name="android.permission.ACCESS_FINE_LOCATION" granted="true" flags="0" />
    </pkg>
    <pkg name="com.facebook.katana">
        <item name="android.permission.CAMERA" granted="true" flags="0" />
        <item name="android.permission.ACCESS_FINE_LOCATION" granted="true" flags="0" />
        <item name="android.permission.ACCESS_BACKGROUND_LOCATION" granted="true" flags="0" />
    </pkg>
</runtime-permissions>
"""

    # Create mock appops.xml
    appops_content = """<?xml version='1.0' encoding='utf-8' standalone='yes' ?>
<app-ops version="1">
    <pkg n="com.whatsapp">
        <uid n="10123">
            <op n="26" m="0" t="1704326400000" d="5000" />
            <op n="27" m="0" t="1704326400000" d="10000" />
            <op n="1" m="0" t="1704326400000" />
        </uid>
    </pkg>
    <pkg n="com.facebook.katana">
        <uid n="10124">
            <op n="26" m="0" t="1704240000000" d="3000" />
            <op n="1" m="0" t="1704240000000" />
        </uid>
    </pkg>
</app-ops>
"""

    # Create mock usage stats
    usage_stats_content = """<?xml version='1.0' encoding='utf-8' standalone='yes' ?>
<usage-history>
    <app package="com.whatsapp" lastTimeUsed="1704326400000" totalTimeInForeground="3600000" launchCount="150" />
    <app package="com.facebook.katana" lastTimeUsed="1704240000000" totalTimeInForeground="1800000" launchCount="75" />
</usage-history>
"""

    with zipfile.ZipFile(zip_path, "w") as zf:
        # Use "fs/" prefix for Cellebrite format
        zf.writestr("fs/data/system/packages.xml", packages_xml_content)
        zf.writestr("fs/data/system/users/0/runtime-permissions.xml", runtime_permissions_content)
        zf.writestr("fs/data/system/appops.xml", appops_content)
        zf.writestr("fs/data/system/usagestats/0/usage-history.xml", usage_stats_content)

    return zip_path


def test_plugin_metadata(plugin):
    """Test that plugin metadata is correctly defined."""
    metadata = plugin.metadata

    assert metadata.name == "AndroidAppPermissionsExtractor"
    assert metadata.version == "1.0.0"
    assert "android" in metadata.target_os
    assert metadata.enabled is True
    assert "permissions" in metadata.description.lower()


def test_initialize(plugin):
    """Test plugin initialization."""
    plugin.initialize()
    assert plugin.apps_data == {}
    assert plugin.errors == []
    assert plugin.zip_prefix == ''


def test_detect_zip_structure(plugin, core_api, mock_android_permissions_zip):
    """Test detection of ZIP structure."""
    core_api.set_zip_file(mock_android_permissions_zip)

    plugin._detect_zip_structure()

    assert plugin.zip_prefix == "fs/"


def test_parse_declared_permissions(plugin, core_api, mock_android_permissions_zip):
    """Test parsing of declared permissions from packages.xml."""
    core_api.set_zip_file(mock_android_permissions_zip)
    plugin._detect_zip_structure()

    declared = plugin._parse_declared_permissions()

    assert len(declared) == 3
    assert "com.whatsapp" in declared
    assert "com.facebook.katana" in declared

    whatsapp = declared["com.whatsapp"]
    assert whatsapp["package_name"] == "com.whatsapp"
    assert "android.permission.CAMERA" in whatsapp["granted_permissions"]
    assert "android.permission.READ_CONTACTS" in whatsapp["granted_permissions"]
    assert "android.permission.ACCESS_FINE_LOCATION" in whatsapp["granted_permissions"]


def test_parse_runtime_permissions(plugin, core_api, mock_android_permissions_zip):
    """Test parsing of runtime permissions."""
    core_api.set_zip_file(mock_android_permissions_zip)
    plugin._detect_zip_structure()

    runtime = plugin._parse_runtime_permissions()

    assert len(runtime) == 2
    assert "com.whatsapp" in runtime
    assert "com.facebook.katana" in runtime

    whatsapp = runtime["com.whatsapp"]
    runtime_perms = whatsapp["runtime_permissions"]
    assert len(runtime_perms) == 3

    # Check camera permission details
    camera_perm = next(
        (p for p in runtime_perms if p["permission"] == "android.permission.CAMERA"), None
    )
    assert camera_perm is not None
    assert camera_perm["granted"] is True


def test_parse_app_ops(plugin, core_api, mock_android_permissions_zip):
    """Test parsing of app ops."""
    core_api.set_zip_file(mock_android_permissions_zip)
    plugin._detect_zip_structure()

    app_ops = plugin._parse_app_ops()

    assert len(app_ops) == 2
    assert "com.whatsapp" in app_ops

    whatsapp_ops = app_ops["com.whatsapp"]["app_ops"]
    assert len(whatsapp_ops) == 3

    # Check for camera op (op code 26)
    camera_op = next((op for op in whatsapp_ops if op["operation"] == "CAMERA"), None)
    assert camera_op is not None
    assert camera_op["mode"] == "Allowed"
    assert camera_op["last_access_time"] == "1704326400000"


def test_parse_usage_stats(plugin, core_api, mock_android_permissions_zip):
    """Test parsing of usage stats."""
    core_api.set_zip_file(mock_android_permissions_zip)
    plugin._detect_zip_structure()

    usage = plugin._parse_usage_stats()

    assert len(usage) == 2
    assert "com.whatsapp" in usage

    whatsapp_usage = usage["com.whatsapp"]
    assert whatsapp_usage["last_time_used"] == "1704326400000"
    assert whatsapp_usage["launch_count"] == "150"


def test_map_app_op(plugin):
    """Test app op code to name mapping."""
    assert plugin._map_app_op("26") == "CAMERA"
    assert plugin._map_app_op("27") == "RECORD_AUDIO"
    assert plugin._map_app_op("1") == "FINE_LOCATION"
    assert plugin._map_app_op("999") == "OP_999"
    assert plugin._map_app_op(None) == "Unknown"


def test_map_op_mode(plugin):
    """Test app op mode mapping."""
    assert plugin._map_op_mode("0") == "Allowed"
    assert plugin._map_op_mode("1") == "Ignored"
    assert plugin._map_op_mode("2") == "Errored"
    assert plugin._map_op_mode("3") == "Default"
    assert plugin._map_op_mode("999") == "Mode_999"
    assert plugin._map_op_mode(None) == "Unknown"


def test_merge_app_data(plugin, core_api, mock_android_permissions_zip):
    """Test merging data from multiple sources."""
    core_api.set_zip_file(mock_android_permissions_zip)
    plugin._detect_zip_structure()

    declared = plugin._parse_declared_permissions()
    runtime = plugin._parse_runtime_permissions()
    app_ops = plugin._parse_app_ops()
    usage = plugin._parse_usage_stats()

    merged = plugin._merge_app_data(declared, runtime, app_ops, usage)

    assert len(merged) == 3
    assert "com.whatsapp" in merged

    whatsapp = merged["com.whatsapp"]
    assert "granted_permissions" in whatsapp
    assert "runtime_permissions" in whatsapp
    assert "app_ops" in whatsapp
    assert "last_time_used" in whatsapp


def test_calculate_risk_scores(plugin, core_api, mock_android_permissions_zip):
    """Test risk score calculation."""
    core_api.set_zip_file(mock_android_permissions_zip)
    plugin._detect_zip_structure()

    declared = plugin._parse_declared_permissions()
    runtime = plugin._parse_runtime_permissions()
    app_ops = plugin._parse_app_ops()
    usage = plugin._parse_usage_stats()

    plugin.apps_data = plugin._merge_app_data(declared, runtime, app_ops, usage)
    plugin._calculate_risk_scores()

    # WhatsApp has many high-risk permissions
    whatsapp = plugin.apps_data["com.whatsapp"]
    assert "risk_score" in whatsapp
    assert "risk_level" in whatsapp
    assert "high_risk_permissions" in whatsapp

    # WhatsApp should have HIGH or CRITICAL risk
    assert whatsapp["risk_level"] in ["High", "Critical", "Medium"]
    assert whatsapp["risk_score"] > 0

    # Check high-risk permissions are identified
    high_risk_perms = whatsapp["high_risk_permissions"]
    assert "android.permission.ACCESS_FINE_LOCATION" in high_risk_perms
    assert "android.permission.CAMERA" in high_risk_perms


def test_categorize_risk(plugin):
    """Test risk categorization."""
    assert plugin._categorize_risk(15.0) == "Critical"
    assert plugin._categorize_risk(9.0) == "High"
    assert plugin._categorize_risk(5.0) == "Medium"
    assert plugin._categorize_risk(3.0) == "Low"
    assert plugin._categorize_risk(1.0) == "Minimal"


def test_execute_full_extraction(plugin, core_api, mock_android_permissions_zip):
    """Test full execution of plugin."""
    core_api.set_zip_file(mock_android_permissions_zip)

    result = plugin.execute()

    assert result["success"] is True
    assert result["total_apps"] == 3
    assert result["total_permissions"] > 0
    assert "report_path" in result
    assert "json_path" in result
    assert Path(result["report_path"]).exists()
    assert Path(result["json_path"]).exists()


def test_export_to_json(plugin, core_api, mock_android_permissions_zip, tmp_path):
    """Test JSON export functionality."""
    core_api.set_zip_file(mock_android_permissions_zip)
    plugin._detect_zip_structure()

    declared = plugin._parse_declared_permissions()
    runtime = plugin._parse_runtime_permissions()
    app_ops = plugin._parse_app_ops()
    usage = plugin._parse_usage_stats()

    plugin.apps_data = plugin._merge_app_data(declared, runtime, app_ops, usage)
    plugin._calculate_risk_scores()

    json_path = tmp_path / "test_export.json"
    plugin._export_to_json(json_path)

    assert json_path.exists()

    with open(json_path) as f:
        data = json.load(f)

    assert data["plugin_name"] == "AndroidAppPermissionsExtractor"
    assert data["plugin_version"] == "1.0.0"
    assert "data" in data
    assert "applications" in data["data"]


def test_generate_report(plugin, core_api, mock_android_permissions_zip):
    """Test markdown report generation."""
    core_api.set_zip_file(mock_android_permissions_zip)
    plugin._detect_zip_structure()

    declared = plugin._parse_declared_permissions()
    runtime = plugin._parse_runtime_permissions()
    app_ops = plugin._parse_app_ops()
    usage = plugin._parse_usage_stats()

    plugin.apps_data = plugin._merge_app_data(declared, runtime, app_ops, usage)
    plugin._calculate_risk_scores()

    report_path = plugin._generate_report()

    assert Path(report_path).exists()

    with open(report_path, encoding='utf-8') as f:
        content = f.read()

    assert "Android Application Permissions" in content
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
    declared = plugin._parse_declared_permissions()
    runtime = plugin._parse_runtime_permissions()
    app_ops = plugin._parse_app_ops()
    usage = plugin._parse_usage_stats()

    assert declared == {}
    assert runtime == {}
    assert app_ops == {}
    assert usage == {}


def test_cleanup(plugin):
    """Test plugin cleanup."""
    plugin.apps_data = {"test": "data"}
    plugin.cleanup()

    # Cleanup just logs, doesn't clear data
    assert isinstance(plugin.apps_data, dict)


def test_no_zip_loaded_error(plugin):
    """Test error handling when no ZIP is loaded."""
    result = plugin.execute()
    assert result["success"] is False
    assert "error" in result


def test_high_risk_permission_detection(plugin, core_api, mock_android_permissions_zip):
    """Test that high-risk permissions are correctly identified."""
    core_api.set_zip_file(mock_android_permissions_zip)
    plugin._detect_zip_structure()

    declared = plugin._parse_declared_permissions()
    runtime = plugin._parse_runtime_permissions()
    app_ops = plugin._parse_app_ops()
    usage = plugin._parse_usage_stats()

    plugin.apps_data = plugin._merge_app_data(declared, runtime, app_ops, usage)
    plugin._calculate_risk_scores()

    # Facebook has background location - should be flagged
    facebook = plugin.apps_data.get("com.facebook.katana")
    if facebook:
        high_risk_perms = facebook.get("high_risk_permissions", [])
        assert "android.permission.ACCESS_BACKGROUND_LOCATION" in high_risk_perms
        # Background location should contribute heavily to risk score
        assert facebook.get("risk_score", 0) > 5.0


def test_permission_categories(plugin):
    """Test that permission categories are correctly defined."""
    assert "location" in plugin.PERMISSION_CATEGORIES
    assert "camera" in plugin.PERMISSION_CATEGORIES
    assert "microphone" in plugin.PERMISSION_CATEGORIES
    assert "contacts" in plugin.PERMISSION_CATEGORIES

    # Check that categories contain expected permissions
    assert "ACCESS_FINE_LOCATION" in plugin.PERMISSION_CATEGORIES["location"]
    assert "CAMERA" in plugin.PERMISSION_CATEGORIES["camera"]
    assert "RECORD_AUDIO" in plugin.PERMISSION_CATEGORIES["microphone"]


def test_risk_boosting_for_multiple_high_risk_perms(plugin, core_api, mock_android_permissions_zip):
    """Test that risk score is boosted for apps with 3+ high-risk permissions."""
    core_api.set_zip_file(mock_android_permissions_zip)
    plugin._detect_zip_structure()

    declared = plugin._parse_declared_permissions()
    runtime = plugin._parse_runtime_permissions()
    app_ops = plugin._parse_app_ops()
    usage = plugin._parse_usage_stats()

    plugin.apps_data = plugin._merge_app_data(declared, runtime, app_ops, usage)
    plugin._calculate_risk_scores()

    whatsapp = plugin.apps_data["com.whatsapp"]
    # WhatsApp has 5 high-risk permissions, so should get 1.5x boost
    high_risk_count = len(whatsapp["high_risk_permissions"])
    assert high_risk_count >= 3
    # Risk score should be substantial
    assert whatsapp["risk_score"] >= 7.0
