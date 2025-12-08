"""
Tests for Core API documentation functionality.
"""

import pytest

from yaft.core.api import CoreAPI


@pytest.fixture
def core_api(tmp_path):
    """Create CoreAPI instance for testing."""
    api = CoreAPI(config_dir=tmp_path / "config", base_output_dir=tmp_path / "output")
    return api


def test_get_api_methods_returns_dict(core_api):
    """Test that get_api_methods returns a dictionary."""
    methods = core_api.get_api_methods()
    assert isinstance(methods, dict)


def test_get_api_methods_has_categories(core_api):
    """Test that get_api_methods returns expected categories."""
    methods = core_api.get_api_methods()

    # Check that common categories exist
    expected_categories = [
        "Logging",
        "Output & Display",
        "Case Management",
        "ZIP File Handling",
        "Data Format Parsing",
        "SQLite & Database",
    ]

    for category in expected_categories:
        assert category in methods, f"Expected category '{category}' not found"


def test_get_api_methods_structure(core_api):
    """Test that method info dictionaries have correct structure."""
    methods = core_api.get_api_methods()

    # Get first category with methods
    category = next(iter(methods.keys()))
    method_list = methods[category]

    assert len(method_list) > 0, "Category should have at least one method"

    # Check structure of first method
    method_info = method_list[0]
    assert "name" in method_info
    assert "signature" in method_info
    assert "returns" in method_info
    assert "description" in method_info

    # Check types
    assert isinstance(method_info["name"], str)
    assert isinstance(method_info["signature"], str)
    assert isinstance(method_info["returns"], str)
    assert isinstance(method_info["description"], str)


def test_get_api_methods_logging_category(core_api):
    """Test that Logging category contains expected methods."""
    methods = core_api.get_api_methods()

    assert "Logging" in methods
    logging_methods = methods["Logging"]

    # Check for expected logging methods
    method_names = [m["name"] for m in logging_methods]
    assert "log_info" in method_names
    assert "log_error" in method_names
    assert "log_warning" in method_names
    assert "log_debug" in method_names


def test_get_api_methods_zip_handling_category(core_api):
    """Test that ZIP File Handling category contains expected methods."""
    methods = core_api.get_api_methods()

    assert "ZIP File Handling" in methods
    zip_methods = methods["ZIP File Handling"]

    # Check for expected ZIP methods
    method_names = [m["name"] for m in zip_methods]
    assert "set_zip_file" in method_names
    assert "get_current_zip" in method_names
    assert "close_zip" in method_names
    assert "read_zip_file" in method_names
    assert "list_zip_contents" in method_names


def test_get_api_methods_no_private_methods(core_api):
    """Test that private methods are not included."""
    methods = core_api.get_api_methods()

    # Flatten all method names
    all_method_names = []
    for method_list in methods.values():
        all_method_names.extend([m["name"] for m in method_list])

    # Check that no private methods are included
    for name in all_method_names:
        assert not name.startswith("_"), f"Private method '{name}' should not be included"


def test_get_api_methods_signatures_valid(core_api):
    """Test that method signatures are properly formatted."""
    methods = core_api.get_api_methods()

    # Check a few known methods
    all_methods = []
    for method_list in methods.values():
        all_methods.extend(method_list)

    # Find print_success method
    print_success = next((m for m in all_methods if m["name"] == "print_success"), None)
    assert print_success is not None
    assert "message" in print_success["signature"]
    assert print_success["returns"] == "None"

    # Find set_zip_file method
    set_zip_file = next((m for m in all_methods if m["name"] == "set_zip_file"), None)
    assert set_zip_file is not None
    assert "zip_path" in set_zip_file["signature"]


def test_get_api_methods_returns_consistent_count(core_api):
    """Test that get_api_methods returns consistent results."""
    methods1 = core_api.get_api_methods()
    methods2 = core_api.get_api_methods()

    # Should return same number of categories
    assert len(methods1) == len(methods2)

    # Should return same number of methods in each category
    for category in methods1.keys():
        assert len(methods1[category]) == len(methods2[category])


def test_get_api_methods_minimum_count(core_api):
    """Test that API has a reasonable minimum number of methods."""
    methods = core_api.get_api_methods()

    # Count total methods
    total_methods = sum(len(method_list) for method_list in methods.values())

    # YAFT should have at least 50 public API methods
    assert total_methods >= 50, f"Expected at least 50 methods, found {total_methods}"


def test_get_api_methods_category_grouping(core_api):
    """Test that methods are properly categorized."""
    methods = core_api.get_api_methods()

    # All log_* methods should be in Logging category
    if "Logging" in methods:
        logging_methods = methods["Logging"]
        for method in logging_methods:
            assert method["name"].startswith("log_")

    # All print_* methods should be in Output & Display category
    if "Output & Display" in methods:
        output_methods = methods["Output & Display"]
        for method in output_methods:
            assert method["name"].startswith("print_")

    # Check ZIP File Handling has zip-related methods
    if "ZIP File Handling" in methods:
        zip_methods = methods["ZIP File Handling"]
        zip_method_names = [m["name"] for m in zip_methods]
        # Should contain core ZIP operations
        assert any("zip" in name for name in zip_method_names)
