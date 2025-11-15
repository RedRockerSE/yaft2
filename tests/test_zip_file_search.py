"""
Tests for ZIP file search functionality in CoreAPI.

This module tests the find_files_in_zip() method which provides
comprehensive file search capabilities with wildcard patterns.
"""

import zipfile
from pathlib import Path

import pytest

from yaft.core.api import CoreAPI


@pytest.fixture
def core_api(tmp_path):
    """Create a CoreAPI instance with temporary output directory."""
    api = CoreAPI()
    api.base_output_dir = tmp_path / "yaft_output"
    api.base_output_dir.mkdir(parents=True, exist_ok=True)
    return api


@pytest.fixture
def mock_zip_with_various_files(tmp_path):
    """
    Create a mock ZIP file with various file types and directory structures.

    Structure:
    - root/
      - file1.txt
      - file2.log
      - data.db
      - config.json
      - System/
        - Library/
          - Preferences/
            - com.apple.safari.plist
            - com.apple.mail.plist
          - app_config.xml
        - SystemVersion.plist
      - data/
        - data/
          - com.example.app/
            - databases/
              - app.db
              - cache.db
            - files/
              - user_data.json
          - com.android.phone/
            - databases/
              - calllog.db
              - contacts2.db
      - logs/
        - error_log_2024.txt
        - system.log.txt
        - debug.log
    """
    zip_path = tmp_path / "test.zip"

    with zipfile.ZipFile(zip_path, "w") as zf:
        # Root level files
        zf.writestr("file1.txt", "content")
        zf.writestr("file2.log", "log content")
        zf.writestr("data.db", "database")
        zf.writestr("config.json", "{}")

        # iOS-style structure
        zf.writestr("System/Library/Preferences/com.apple.safari.plist", "plist")
        zf.writestr("System/Library/Preferences/com.apple.mail.plist", "plist")
        zf.writestr("System/Library/app_config.xml", "xml")
        zf.writestr("System/SystemVersion.plist", "version")

        # Android-style structure
        zf.writestr("data/data/com.example.app/databases/app.db", "db")
        zf.writestr("data/data/com.example.app/databases/cache.db", "db")
        zf.writestr("data/data/com.example.app/files/user_data.json", "json")
        zf.writestr("data/data/com.android.phone/databases/calllog.db", "db")
        zf.writestr("data/data/com.android.phone/databases/contacts2.db", "db")

        # Log files
        zf.writestr("logs/error_log_2024.txt", "errors")
        zf.writestr("logs/system.log.txt", "system")
        zf.writestr("logs/debug.log", "debug")

    return zip_path


@pytest.fixture
def mock_zip_cellebrite_ios(tmp_path):
    """Create mock ZIP in Cellebrite iOS format with filesystem1/ prefix."""
    zip_path = tmp_path / "cellebrite_ios.zip"

    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr("filesystem1/System/Library/CoreServices/SystemVersion.plist", "plist")
        zf.writestr("filesystem1/private/var/mobile/Library/SMS/sms.db", "db")
        zf.writestr("filesystem1/private/var/mobile/Library/CallHistoryDB/CallHistory.storedata", "db")

    return zip_path


@pytest.fixture
def mock_zip_graykey_android(tmp_path):
    """Create mock ZIP in GrayKey Android format (no prefix)."""
    zip_path = tmp_path / "graykey_android.zip"

    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr("data/data/com.android.providers.contacts/databases/contacts2.db", "db")
        zf.writestr("data/data/com.android.providers.telephony/databases/mmssms.db", "db")
        zf.writestr("system/build.prop", "properties")

    return zip_path


# ========== Basic Filename Search Tests ==========

def test_find_exact_filename(core_api, mock_zip_with_various_files):
    """Test finding an exact filename."""
    core_api.set_zip_file(mock_zip_with_various_files)

    # Find exact file
    results = core_api.find_files_in_zip("file1.txt")
    assert len(results) == 1
    assert results[0] == "file1.txt"


def test_find_exact_filename_with_path(core_api, mock_zip_with_various_files):
    """Test finding a file with its full path."""
    core_api.set_zip_file(mock_zip_with_various_files)

    results = core_api.find_files_in_zip("System/SystemVersion.plist")
    assert len(results) == 1
    assert results[0] == "System/SystemVersion.plist"


def test_find_nonexistent_file(core_api, mock_zip_with_various_files):
    """Test searching for a file that doesn't exist."""
    core_api.set_zip_file(mock_zip_with_various_files)

    results = core_api.find_files_in_zip("nonexistent.txt")
    assert len(results) == 0


# ========== Wildcard Extension Tests ==========

def test_find_wildcard_extension(core_api, mock_zip_with_various_files):
    """Test finding files with wildcard extension (file.*)."""
    core_api.set_zip_file(mock_zip_with_various_files)

    # Find file1.* (should match file1.txt)
    results = core_api.find_files_in_zip("file1.*")
    assert len(results) == 1
    assert "file1.txt" in results


def test_find_wildcard_extension_multiple_matches(core_api, mock_zip_with_various_files):
    """Test wildcard extension with multiple matches."""
    core_api.set_zip_file(mock_zip_with_various_files)

    # Find all SystemVersion.* files
    results = core_api.find_files_in_zip("SystemVersion.*")
    assert len(results) == 1
    assert "System/SystemVersion.plist" in results


# ========== Wildcard Name Tests ==========

def test_find_all_files_with_extension(core_api, mock_zip_with_various_files):
    """Test finding all files with specific extension (*.ext)."""
    core_api.set_zip_file(mock_zip_with_various_files)

    # Find all .db files
    results = core_api.find_files_in_zip("*.db")
    assert len(results) == 5
    assert "data.db" in results
    assert "data/data/com.example.app/databases/app.db" in results
    assert "data/data/com.example.app/databases/cache.db" in results
    assert "data/data/com.android.phone/databases/calllog.db" in results
    assert "data/data/com.android.phone/databases/contacts2.db" in results


def test_find_all_plist_files(core_api, mock_zip_with_various_files):
    """Test finding all .plist files."""
    core_api.set_zip_file(mock_zip_with_various_files)

    results = core_api.find_files_in_zip("*.plist")
    assert len(results) == 3
    assert "System/Library/Preferences/com.apple.safari.plist" in results
    assert "System/Library/Preferences/com.apple.mail.plist" in results
    assert "System/SystemVersion.plist" in results


def test_find_all_log_files(core_api, mock_zip_with_various_files):
    """Test finding all .log files."""
    core_api.set_zip_file(mock_zip_with_various_files)

    results = core_api.find_files_in_zip("*.log")
    assert len(results) == 2
    assert "file2.log" in results
    assert "logs/debug.log" in results


# ========== Multiple Wildcards Tests ==========

def test_find_with_pattern_in_name(core_api, mock_zip_with_various_files):
    """Test finding files with pattern in the name (*log*.txt)."""
    core_api.set_zip_file(mock_zip_with_various_files)

    # Find all files with 'log' in name and .txt extension
    results = core_api.find_files_in_zip("*log*.txt")
    assert len(results) == 2
    assert "logs/error_log_2024.txt" in results
    assert "logs/system.log.txt" in results


def test_find_with_question_mark_wildcard(core_api, mock_zip_with_various_files):
    """Test finding files with ? wildcard (matches single character)."""
    core_api.set_zip_file(mock_zip_with_various_files)

    # Find file?.txt (matches file1.txt, file2.log won't match)
    results = core_api.find_files_in_zip("file?.txt")
    assert len(results) == 1
    assert "file1.txt" in results


def test_find_com_apple_files(core_api, mock_zip_with_various_files):
    """Test finding files matching com.apple.* pattern."""
    core_api.set_zip_file(mock_zip_with_various_files)

    results = core_api.find_files_in_zip("com.apple.*")
    assert len(results) == 2
    assert "System/Library/Preferences/com.apple.safari.plist" in results
    assert "System/Library/Preferences/com.apple.mail.plist" in results


# ========== Path-based Search Tests ==========

def test_find_with_search_path(core_api, mock_zip_with_various_files):
    """Test finding files within a specific directory."""
    core_api.set_zip_file(mock_zip_with_various_files)

    # Find all .db files in data/data/ directory
    results = core_api.find_files_in_zip("*.db", search_path="data/data/")
    assert len(results) == 4
    assert "data/data/com.example.app/databases/app.db" in results
    assert "data/data/com.example.app/databases/cache.db" in results
    assert "data/data/com.android.phone/databases/calllog.db" in results
    assert "data/data/com.android.phone/databases/contacts2.db" in results
    # Should NOT include root level data.db
    assert "data.db" not in results


def test_find_with_nested_search_path(core_api, mock_zip_with_various_files):
    """Test finding files in a deeply nested directory."""
    core_api.set_zip_file(mock_zip_with_various_files)

    # Find files in System/Library/
    results = core_api.find_files_in_zip("*.plist", search_path="System/Library/")
    assert len(results) == 2
    assert "System/Library/Preferences/com.apple.safari.plist" in results
    assert "System/Library/Preferences/com.apple.mail.plist" in results
    # Should NOT include System/SystemVersion.plist (not in Library/)
    assert "System/SystemVersion.plist" not in results


def test_find_with_pattern_path(core_api, mock_zip_with_various_files):
    """Test finding files with wildcard in path pattern."""
    core_api.set_zip_file(mock_zip_with_various_files)

    # Find all .db files in */databases/ directories
    results = core_api.find_files_in_zip("*/databases/*.db")
    assert len(results) == 4
    assert "data/data/com.example.app/databases/app.db" in results
    assert "data/data/com.android.phone/databases/calllog.db" in results


def test_find_calllog_databases(core_api, mock_zip_with_various_files):
    """Test finding call log databases specifically."""
    core_api.set_zip_file(mock_zip_with_various_files)

    results = core_api.find_files_in_zip("*call*.db")
    assert len(results) == 1
    assert "data/data/com.android.phone/databases/calllog.db" in results


# ========== Case Sensitivity Tests ==========

def test_case_insensitive_search_default(core_api, mock_zip_with_various_files):
    """Test that search is case-insensitive by default."""
    core_api.set_zip_file(mock_zip_with_various_files)

    # Search with different case
    results = core_api.find_files_in_zip("FILE1.TXT")
    assert len(results) == 1
    assert "file1.txt" in results


def test_case_sensitive_search(core_api, mock_zip_with_various_files):
    """Test case-sensitive search."""
    core_api.set_zip_file(mock_zip_with_various_files)

    # Case-sensitive search should fail
    results = core_api.find_files_in_zip("FILE1.TXT", case_sensitive=True)
    assert len(results) == 0

    # Correct case should work
    results = core_api.find_files_in_zip("file1.txt", case_sensitive=True)
    assert len(results) == 1


def test_case_insensitive_path_search(core_api, mock_zip_with_various_files):
    """Test case-insensitive search with path."""
    core_api.set_zip_file(mock_zip_with_various_files)

    # Search with different case in path
    results = core_api.find_files_in_zip("*.plist", search_path="SYSTEM/LIBRARY/")
    assert len(results) == 2


# ========== Max Results Tests ==========

def test_max_results_limit(core_api, mock_zip_with_various_files):
    """Test limiting the number of results returned."""
    core_api.set_zip_file(mock_zip_with_various_files)

    # Find all .db files but limit to 2 results
    results = core_api.find_files_in_zip("*.db", max_results=2)
    assert len(results) == 2


def test_max_results_one(core_api, mock_zip_with_various_files):
    """Test limiting to a single result."""
    core_api.set_zip_file(mock_zip_with_various_files)

    results = core_api.find_files_in_zip("*.plist", max_results=1)
    assert len(results) == 1


def test_max_results_larger_than_matches(core_api, mock_zip_with_various_files):
    """Test max_results larger than actual matches."""
    core_api.set_zip_file(mock_zip_with_various_files)

    # Only 1 match exists, but max_results is 10
    results = core_api.find_files_in_zip("SystemVersion.plist", max_results=10)
    assert len(results) == 1


# ========== Forensic Format Tests ==========

def test_find_in_cellebrite_ios_format(core_api, mock_zip_cellebrite_ios):
    """Test finding files in Cellebrite iOS format (with filesystem1/ prefix)."""
    core_api.set_zip_file(mock_zip_cellebrite_ios)

    # Find all .db files (CallHistory.storedata has different extension)
    results = core_api.find_files_in_zip("*.db")
    assert len(results) == 1
    assert "filesystem1/private/var/mobile/Library/SMS/sms.db" in results

    # Find CallHistory with wildcard
    results = core_api.find_files_in_zip("*CallHistory*")
    assert len(results) == 1
    assert "filesystem1/private/var/mobile/Library/CallHistoryDB/CallHistory.storedata" in results


def test_find_in_cellebrite_with_search_path(core_api, mock_zip_cellebrite_ios):
    """Test finding files in Cellebrite format with search_path."""
    core_api.set_zip_file(mock_zip_cellebrite_ios)

    # Search within filesystem1/System/
    results = core_api.find_files_in_zip("*.plist", search_path="filesystem1/System/")
    assert len(results) == 1
    assert "filesystem1/System/Library/CoreServices/SystemVersion.plist" in results


def test_find_in_graykey_android_format(core_api, mock_zip_graykey_android):
    """Test finding files in GrayKey Android format (no prefix)."""
    core_api.set_zip_file(mock_zip_graykey_android)

    # Find all .db files
    results = core_api.find_files_in_zip("*.db")
    assert len(results) == 2
    assert "data/data/com.android.providers.contacts/databases/contacts2.db" in results
    assert "data/data/com.android.providers.telephony/databases/mmssms.db" in results


def test_find_build_prop(core_api, mock_zip_graykey_android):
    """Test finding build.prop file."""
    core_api.set_zip_file(mock_zip_graykey_android)

    results = core_api.find_files_in_zip("build.prop")
    assert len(results) == 1
    assert "system/build.prop" in results


# ========== Error Handling Tests ==========

def test_error_no_zip_loaded(core_api):
    """Test error when no ZIP file is loaded."""
    with pytest.raises(RuntimeError, match="No ZIP file loaded"):
        core_api.find_files_in_zip("*.txt")


def test_error_empty_pattern(core_api, mock_zip_with_various_files):
    """Test error when pattern is empty."""
    core_api.set_zip_file(mock_zip_with_various_files)

    with pytest.raises(ValueError, match="Search pattern cannot be empty"):
        core_api.find_files_in_zip("")


def test_error_whitespace_pattern(core_api, mock_zip_with_various_files):
    """Test error when pattern is only whitespace."""
    core_api.set_zip_file(mock_zip_with_various_files)

    with pytest.raises(ValueError, match="Search pattern cannot be empty"):
        core_api.find_files_in_zip("   ")


# ========== Edge Cases ==========

def test_results_are_sorted(core_api, mock_zip_with_various_files):
    """Test that results are sorted alphabetically."""
    core_api.set_zip_file(mock_zip_with_various_files)

    results = core_api.find_files_in_zip("*.db")
    # Check that results are sorted
    assert results == sorted(results)


def test_pattern_with_leading_slash(core_api, mock_zip_with_various_files):
    """Test pattern with leading slash."""
    core_api.set_zip_file(mock_zip_with_various_files)

    # Patterns shouldn't typically have leading slashes in ZIP files
    results = core_api.find_files_in_zip("/file1.txt")
    # Should not match because ZIP paths don't have leading slashes
    assert len(results) == 0


def test_search_path_without_trailing_slash(core_api, mock_zip_with_various_files):
    """Test that search_path works with or without trailing slash."""
    core_api.set_zip_file(mock_zip_with_various_files)

    # With trailing slash
    results1 = core_api.find_files_in_zip("*.db", search_path="data/data/")

    # Without trailing slash
    results2 = core_api.find_files_in_zip("*.db", search_path="data/data")

    # Both should return same results
    assert results1 == results2
    assert len(results1) == 4


def test_find_all_files_with_star_star(core_api, mock_zip_with_various_files):
    """Test finding all files with *.*."""
    core_api.set_zip_file(mock_zip_with_various_files)

    results = core_api.find_files_in_zip("*.*")
    # Should match all files with extensions (16 files have extensions)
    # Note: *.* only matches files with a dot in the name
    assert len(results) == 16


def test_find_json_files(core_api, mock_zip_with_various_files):
    """Test finding JSON files."""
    core_api.set_zip_file(mock_zip_with_various_files)

    results = core_api.find_files_in_zip("*.json")
    assert len(results) == 2
    assert "config.json" in results
    assert "data/data/com.example.app/files/user_data.json" in results


# ========== Real-World Use Cases ==========

def test_find_ios_call_history(core_api, mock_zip_cellebrite_ios):
    """Test finding iOS call history database."""
    core_api.set_zip_file(mock_zip_cellebrite_ios)

    results = core_api.find_files_in_zip("*CallHistory*")
    assert len(results) == 1
    assert "filesystem1/private/var/mobile/Library/CallHistoryDB/CallHistory.storedata" in results


def test_find_android_contact_databases(core_api, mock_zip_graykey_android):
    """Test finding Android contact databases."""
    core_api.set_zip_file(mock_zip_graykey_android)

    results = core_api.find_files_in_zip("*contact*.db")
    assert len(results) == 1
    assert "data/data/com.android.providers.contacts/databases/contacts2.db" in results


def test_find_all_databases_in_app(core_api, mock_zip_with_various_files):
    """Test finding all databases for a specific app."""
    core_api.set_zip_file(mock_zip_with_various_files)

    results = core_api.find_files_in_zip(
        "*.db",
        search_path="data/data/com.example.app/"
    )
    assert len(results) == 2
    assert "data/data/com.example.app/databases/app.db" in results
    assert "data/data/com.example.app/databases/cache.db" in results


def test_find_preferences_plists(core_api, mock_zip_with_various_files):
    """Test finding all preference plist files."""
    core_api.set_zip_file(mock_zip_with_various_files)

    results = core_api.find_files_in_zip(
        "*.plist",
        search_path="System/Library/Preferences/"
    )
    assert len(results) == 2
    assert "System/Library/Preferences/com.apple.safari.plist" in results
    assert "System/Library/Preferences/com.apple.mail.plist" in results
