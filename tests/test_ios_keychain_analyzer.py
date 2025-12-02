"""Tests for iOS Keychain Analyzer Plugin."""

import sqlite3
import zipfile
from pathlib import Path

import pytest

from plugins.ios_keychain_analyzer import iOSKeychainAnalyzerPlugin
from yaft.core.api import CoreAPI


@pytest.fixture
def core_api(tmp_path):
    """Create Core API instance with temporary output directory."""
    api = CoreAPI()
    api.base_output_dir = tmp_path / "yaft_output"
    api.base_output_dir.mkdir(parents=True, exist_ok=True)
    return api


@pytest.fixture
def plugin(core_api):
    """Create iOS Keychain Analyzer plugin instance."""
    return iOSKeychainAnalyzerPlugin(core_api)


@pytest.fixture
def mock_ios_keychain_zip_cellebrite(tmp_path):
    """Create mock iOS extraction with keychain database in Cellebrite format."""
    zip_path = tmp_path / "ios_keychain_cellebrite.zip"

    # Create keychain database
    db_path = tmp_path / "keychain-2.db"
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Create genp table (generic passwords)
    cursor.execute(
        """
        CREATE TABLE genp (
            rowid INTEGER PRIMARY KEY,
            cdat REAL,
            mdat REAL,
            desc TEXT,
            labl TEXT,
            acct BLOB,
            svce BLOB,
            agrp TEXT,
            pdmn BLOB,
            sync INTEGER,
            data BLOB,
            sha1 BLOB
        )
        """
    )

    # Create inet table (internet passwords)
    cursor.execute(
        """
        CREATE TABLE inet (
            rowid INTEGER PRIMARY KEY,
            cdat REAL,
            mdat REAL,
            desc TEXT,
            labl TEXT,
            acct BLOB,
            sdmn TEXT,
            srvr TEXT,
            ptcl INTEGER,
            atyp INTEGER,
            port INTEGER,
            path TEXT,
            agrp TEXT,
            pdmn BLOB,
            sync INTEGER,
            data BLOB
        )
        """
    )

    # Create cert table (certificates)
    cursor.execute(
        """
        CREATE TABLE cert (
            rowid INTEGER PRIMARY KEY,
            cdat REAL,
            mdat REAL,
            ctyp INTEGER,
            cenc INTEGER,
            labl TEXT,
            certType INTEGER,
            agrp TEXT,
            pdmn BLOB,
            sync INTEGER,
            data BLOB,
            sha1 BLOB
        )
        """
    )

    # Create keys table (cryptographic keys)
    cursor.execute(
        """
        CREATE TABLE keys (
            rowid INTEGER PRIMARY KEY,
            cdat REAL,
            mdat REAL,
            kcls INTEGER,
            labl TEXT,
            atag BLOB,
            crtr INTEGER,
            type INTEGER,
            bsiz INTEGER,
            esiz INTEGER,
            agrp TEXT,
            pdmn BLOB,
            sync INTEGER,
            data BLOB
        )
        """
    )

    # Insert generic passwords
    # Core Data timestamp: seconds since 2001-01-01 00:00:00 UTC
    # 631152000 = 2020-01-01 00:00:00 UTC
    cursor.execute(
        """
        INSERT INTO genp (rowid, cdat, mdat, desc, labl, acct, svce, agrp, pdmn, sync, data, sha1)
        VALUES (1, 631152000.0, 631152000.0, 'App Password', 'MyApp', ?, ?, 'com.example.app', ?, 0, ?, ?)
        """,
        (b"encrypted_account", b"encrypted_service", b"encrypted_pdmn", b"encrypted_data", b"sha1_hash"),
    )

    cursor.execute(
        """
        INSERT INTO genp (rowid, cdat, mdat, desc, labl, acct, svce, agrp, pdmn, sync, data, sha1)
        VALUES (2, 631238400.0, 631238400.0, 'Social Media', 'Twitter', ?, ?, 'com.twitter.app', ?, 1, ?, ?)
        """,
        (b"encrypted_account", b"encrypted_service", b"encrypted_pdmn", b"encrypted_data", b"sha1_hash"),
    )

    cursor.execute(
        """
        INSERT INTO genp (rowid, cdat, mdat, desc, labl, acct, svce, agrp, pdmn, sync, data, sha1)
        VALUES (3, 631324800.0, 631324800.0, 'Email', 'Gmail', ?, ?, 'com.google.gmail', ?, 1, ?, ?)
        """,
        (b"encrypted_account", b"encrypted_service", b"encrypted_pdmn", b"encrypted_data", b"sha1_hash"),
    )

    # Insert internet passwords
    cursor.execute(
        """
        INSERT INTO inet (rowid, cdat, mdat, desc, labl, acct, sdmn, srvr, ptcl, atyp, port, path, agrp, pdmn, sync, data)
        VALUES (1, 631152000.0, 631152000.0, 'Web Login', 'facebook.com', ?, 'facebook.com', 'facebook.com', 7, 1, 443, '/login', 'com.apple.safari', ?, 1, ?)
        """,
        (b"encrypted_account", b"encrypted_pdmn", b"encrypted_data"),
    )

    cursor.execute(
        """
        INSERT INTO inet (rowid, cdat, mdat, desc, labl, acct, sdmn, srvr, ptcl, atyp, port, path, agrp, pdmn, sync, data)
        VALUES (2, 631238400.0, 631238400.0, 'Web Login', 'github.com', ?, 'github.com', 'github.com', 7, 1, 443, '/', 'com.apple.safari', ?, 0, ?)
        """,
        (b"encrypted_account", b"encrypted_pdmn", b"encrypted_data"),
    )

    cursor.execute(
        """
        INSERT INTO inet (rowid, cdat, mdat, desc, labl, acct, sdmn, srvr, ptcl, atyp, port, path, agrp, pdmn, sync, data)
        VALUES (3, 631324800.0, 631324800.0, 'Web Login', 'twitter.com', ?, 'twitter.com', 'twitter.com', 7, 1, 443, '/login', 'com.apple.safari', ?, 1, ?)
        """,
        (b"encrypted_account", b"encrypted_pdmn", b"encrypted_data"),
    )

    # Insert certificates
    cursor.execute(
        """
        INSERT INTO cert (rowid, cdat, mdat, ctyp, cenc, labl, certType, agrp, pdmn, sync, data, sha1)
        VALUES (1, 631152000.0, 631152000.0, 1, 3, 'Root CA', 0, 'com.apple.security', ?, 0, ?, ?)
        """,
        (b"encrypted_pdmn", b"encrypted_cert", b"sha1_hash"),
    )

    # Insert keys
    cursor.execute(
        """
        INSERT INTO keys (rowid, cdat, mdat, kcls, labl, atag, crtr, type, bsiz, esiz, agrp, pdmn, sync, data)
        VALUES (1, 631152000.0, 631152000.0, 1, 'Encryption Key', ?, 0, 42, 256, 256, 'com.example.app', ?, 0, ?)
        """,
        (b"encrypted_atag", b"encrypted_pdmn", b"encrypted_key"),
    )

    conn.commit()
    conn.close()

    # Create ZIP in Cellebrite format
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.write(db_path, "filesystem1/private/var/Keychains/keychain-2.db")
        # Add Cellebrite iOS marker
        zf.writestr("filesystem1/", "")

    return zip_path


@pytest.fixture
def mock_ios_keychain_zip_graykey(tmp_path):
    """Create mock iOS extraction with keychain database in GrayKey format."""
    zip_path = tmp_path / "ios_keychain_graykey.zip"

    # Create keychain database
    db_path = tmp_path / "keychain-2.db"
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Create tables (same structure as above)
    cursor.execute(
        """
        CREATE TABLE genp (
            rowid INTEGER PRIMARY KEY,
            cdat REAL,
            mdat REAL,
            desc TEXT,
            labl TEXT,
            acct BLOB,
            svce BLOB,
            agrp TEXT,
            pdmn BLOB,
            sync INTEGER,
            data BLOB,
            sha1 BLOB
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE inet (
            rowid INTEGER PRIMARY KEY,
            cdat REAL,
            mdat REAL,
            desc TEXT,
            labl TEXT,
            acct BLOB,
            sdmn TEXT,
            srvr TEXT,
            ptcl INTEGER,
            atyp INTEGER,
            port INTEGER,
            path TEXT,
            agrp TEXT,
            pdmn BLOB,
            sync INTEGER,
            data BLOB
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE cert (
            rowid INTEGER PRIMARY KEY,
            cdat REAL,
            mdat REAL,
            ctyp INTEGER,
            cenc INTEGER,
            labl TEXT,
            certType INTEGER,
            agrp TEXT,
            pdmn BLOB,
            sync INTEGER,
            data BLOB,
            sha1 BLOB
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE keys (
            rowid INTEGER PRIMARY KEY,
            cdat REAL,
            mdat REAL,
            kcls INTEGER,
            labl TEXT,
            atag BLOB,
            crtr INTEGER,
            type INTEGER,
            bsiz INTEGER,
            esiz INTEGER,
            agrp TEXT,
            pdmn BLOB,
            sync INTEGER,
            data BLOB
        )
        """
    )

    # Insert one password
    cursor.execute(
        """
        INSERT INTO genp (rowid, cdat, mdat, desc, labl, acct, svce, agrp, pdmn, sync, data, sha1)
        VALUES (1, 631152000.0, 631152000.0, 'Password', 'TestApp', ?, ?, 'com.test.app', ?, 0, ?, ?)
        """,
        (b"encrypted_account", b"encrypted_service", b"encrypted_pdmn", b"encrypted_data", b"sha1_hash"),
    )

    conn.commit()
    conn.close()

    # Create ZIP in GrayKey format (no prefix)
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.write(db_path, "private/var/Keychains/keychain-2.db")
        # Add GrayKey iOS markers
        zf.writestr("private/", "")
        zf.writestr("System/", "")

    return zip_path


@pytest.fixture
def mock_android_zip(tmp_path):
    """Create mock Android extraction (should fail for iOS plugin)."""
    zip_path = tmp_path / "android.zip"

    with zipfile.ZipFile(zip_path, "w") as zf:
        # Add Android markers
        zf.writestr("Dump/", "")
        zf.writestr("extra/", "")

    return zip_path


def test_plugin_metadata(plugin):
    """Test plugin metadata."""
    metadata = plugin.metadata
    assert metadata.name == "iOSKeychainAnalyzerPlugin"
    assert metadata.version == "1.0.0"
    assert "ios" in metadata.target_os


def test_analyze_keychain_cellebrite(plugin, core_api, mock_ios_keychain_zip_cellebrite):
    """Test analyzing iOS keychain from Cellebrite format."""
    core_api.set_zip_file(mock_ios_keychain_zip_cellebrite)

    result = plugin.execute()

    assert result["success"] is True
    assert result["total_credentials"] == 3
    assert result["total_internet_passwords"] == 3
    assert result["total_certificates"] == 1
    assert result["total_keys"] == 1


def test_analyze_keychain_graykey(plugin, core_api, mock_ios_keychain_zip_graykey):
    """Test analyzing iOS keychain from GrayKey format."""
    core_api.set_zip_file(mock_ios_keychain_zip_graykey)

    result = plugin.execute()

    assert result["success"] is True
    assert result["total_credentials"] == 1


def test_credential_statistics(plugin, core_api, mock_ios_keychain_zip_cellebrite):
    """Test credential statistics analysis."""
    core_api.set_zip_file(mock_ios_keychain_zip_cellebrite)

    result = plugin.execute()

    assert result["success"] is True

    cred_stats = plugin.analysis_results["credential_stats"]
    assert cred_stats["total_items"] == 8  # 3 genp + 3 inet + 1 cert + 1 key
    assert cred_stats["generic_passwords"] == 3
    assert cred_stats["internet_passwords"] == 3
    assert cred_stats["certificates"] == 1
    assert cred_stats["cryptographic_keys"] == 1
    assert cred_stats["synchronizable_items"] == 4  # 2 genp + 2 inet


def test_application_analysis(plugin, core_api, mock_ios_keychain_zip_cellebrite):
    """Test application association analysis."""
    core_api.set_zip_file(mock_ios_keychain_zip_cellebrite)

    result = plugin.execute()

    assert result["success"] is True

    app_analysis = plugin.analysis_results["application_analysis"]
    assert app_analysis["total_apps_with_credentials"] >= 3

    # Check for expected apps
    all_apps = app_analysis["all_apps"]
    assert "com.example.app" in all_apps
    assert "com.apple.safari" in all_apps


def test_synchronization_analysis(plugin, core_api, mock_ios_keychain_zip_cellebrite):
    """Test iCloud synchronization analysis."""
    core_api.set_zip_file(mock_ios_keychain_zip_cellebrite)

    result = plugin.execute()

    assert result["success"] is True

    sync_analysis = plugin.analysis_results["synchronization_analysis"]
    assert sync_analysis["total_synced_items"] == 4
    assert sync_analysis["total_local_items"] == 2
    assert sync_analysis["sync_percentage"] > 0


def test_timeline_analysis(plugin, core_api, mock_ios_keychain_zip_cellebrite):
    """Test credential timeline analysis."""
    core_api.set_zip_file(mock_ios_keychain_zip_cellebrite)

    result = plugin.execute()

    assert result["success"] is True

    timeline = plugin.analysis_results["timeline_analysis"]
    assert timeline["oldest_credential"] is not None
    assert timeline["newest_credential"] is not None
    assert timeline["date_range_days"] >= 0


def test_internet_password_analysis(plugin, core_api, mock_ios_keychain_zip_cellebrite):
    """Test internet password analysis."""
    core_api.set_zip_file(mock_ios_keychain_zip_cellebrite)

    result = plugin.execute()

    assert result["success"] is True

    inet_analysis = plugin.analysis_results["internet_password_analysis"]
    assert inet_analysis["total_domains"] == 3

    # Check for expected domains
    top_domains = inet_analysis["top_domains"]
    assert "facebook.com" in top_domains
    assert "github.com" in top_domains
    assert "twitter.com" in top_domains

    # Check protocol distribution
    protocols = inet_analysis["protocol_distribution"]
    assert "HTTPS" in protocols


def test_no_zip_loaded(plugin, core_api):
    """Test execution without ZIP file loaded."""
    result = plugin.execute()

    assert result["success"] is False
    assert "No ZIP file loaded" in result["error"]


def test_android_extraction_fails(plugin, core_api, mock_android_zip):
    """Test that plugin fails gracefully on Android extraction."""
    core_api.set_zip_file(mock_android_zip)

    result = plugin.execute()

    assert result["success"] is False
    assert "Not an iOS extraction" in result["error"]


def test_no_keychain_database(plugin, core_api, tmp_path):
    """Test with iOS ZIP that doesn't contain keychain database."""
    zip_path = tmp_path / "ios_no_keychain.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr("private/", "")
        zf.writestr("System/", "")

    core_api.set_zip_file(zip_path)
    result = plugin.execute()

    assert result["success"] is False
    assert len(plugin.errors) > 0


def test_report_generation(plugin, core_api, mock_ios_keychain_zip_cellebrite):
    """Test report generation."""
    core_api.set_zip_file(mock_ios_keychain_zip_cellebrite)

    result = plugin.execute()

    assert result["success"] is True
    assert "report_path" in result
    assert Path(result["report_path"]).exists()

    # Read report and verify content
    report_content = Path(result["report_path"]).read_text(encoding="utf-8")
    assert "iOS Keychain Analysis Report" in report_content
    assert "Executive Summary" in report_content
    assert "Security Notice" in report_content
    assert "Credential Statistics" in report_content
    assert "Forensic Recommendations" in report_content


def test_json_export(plugin, core_api, mock_ios_keychain_zip_cellebrite):
    """Test JSON export."""
    core_api.set_zip_file(mock_ios_keychain_zip_cellebrite)

    result = plugin.execute()

    assert result["success"] is True
    assert "json_path" in result
    assert Path(result["json_path"]).exists()

    # Verify JSON structure
    import json

    with open(result["json_path"], encoding="utf-8") as f:
        data = json.load(f)

    assert data["plugin_name"] == "iOSKeychainAnalyzerPlugin"
    assert data["plugin_version"] == "1.0.0"
    assert "keychain_summary" in data["data"]
    assert "analysis_results" in data["data"]
    assert "security_note" in data["data"]


def test_protocol_name_conversion(plugin):
    """Test protocol code to name conversion."""
    assert plugin._get_protocol_name(0) == "FTP"
    assert plugin._get_protocol_name(1) == "HTTP"
    assert plugin._get_protocol_name(7) == "HTTPS"
    assert "Unknown" in plugin._get_protocol_name(999)


def test_full_workflow(plugin, core_api, mock_ios_keychain_zip_cellebrite):
    """Test complete analysis workflow."""
    core_api.set_zip_file(mock_ios_keychain_zip_cellebrite)

    # Initialize
    plugin.initialize()

    # Execute
    result = plugin.execute()

    # Verify success
    assert result["success"] is True
    assert result["total_credentials"] == 3
    assert Path(result["report_path"]).exists()
    assert Path(result["json_path"]).exists()

    # Verify analysis was performed
    assert "credential_stats" in plugin.analysis_results
    assert "application_analysis" in plugin.analysis_results
    assert "synchronization_analysis" in plugin.analysis_results
    assert "timeline_analysis" in plugin.analysis_results
    assert "internet_password_analysis" in plugin.analysis_results

    # Cleanup
    plugin.cleanup()
    assert plugin.keychain_data is None
    assert len(plugin.analysis_results) == 0
    assert len(plugin.errors) == 0
