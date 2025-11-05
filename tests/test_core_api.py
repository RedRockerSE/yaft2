"""Tests for CoreAPI."""

from pathlib import Path

import pytest

from yaft.core.api import CoreAPI


def test_core_api_initialization(temp_dir):
    """Test CoreAPI initialization."""
    config_dir = temp_dir / "config"
    api = CoreAPI(config_dir=config_dir)

    assert api.config_dir == config_dir
    assert config_dir.exists()
    assert api.console is not None
    assert api.logger is not None


def test_get_config_path(core_api, temp_dir):
    """Test getting configuration file paths."""
    config_path = core_api.get_config_path("test.toml")

    expected_path = temp_dir / "config" / "test.toml"
    assert config_path == expected_path


def test_shared_data_operations(core_api):
    """Test shared data storage and retrieval."""
    # Set data
    core_api.set_shared_data("test_key", "test_value")
    assert core_api.get_shared_data("test_key") == "test_value"

    # Get with default
    assert core_api.get_shared_data("nonexistent", "default") == "default"

    # Clear specific key
    core_api.clear_shared_data("test_key")
    assert core_api.get_shared_data("test_key") is None

    # Set multiple and clear all
    core_api.set_shared_data("key1", "value1")
    core_api.set_shared_data("key2", "value2")
    core_api.clear_shared_data()
    assert core_api.get_shared_data("key1") is None
    assert core_api.get_shared_data("key2") is None


def test_file_operations(core_api, temp_dir):
    """Test file read/write operations."""
    test_file = temp_dir / "test.txt"
    test_content = "Hello, YAFT!"

    # Write file
    core_api.write_file(test_file, test_content)
    assert test_file.exists()

    # Read file
    content = core_api.read_file(test_file)
    assert content == test_content


def test_file_read_nonexistent(core_api, temp_dir):
    """Test reading a nonexistent file raises error."""
    nonexistent_file = temp_dir / "nonexistent.txt"

    with pytest.raises(FileNotFoundError):
        core_api.read_file(nonexistent_file)


def test_logging_methods(core_api, capsys):
    """Test logging methods don't raise errors."""
    # These should not raise exceptions
    core_api.log_info("Info message")
    core_api.log_warning("Warning message")
    core_api.log_error("Error message")
    core_api.log_debug("Debug message")


def test_print_methods(core_api, capsys):
    """Test print methods don't raise errors."""
    # These should not raise exceptions
    core_api.print_success("Success message")
    core_api.print_error("Error message")
    core_api.print_warning("Warning message")
    core_api.print_info("Info message")
