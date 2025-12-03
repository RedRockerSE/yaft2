"""
Tests for logging configuration functionality.
"""

import logging
import tempfile
from pathlib import Path

import pytest
import toml

from yaft.core.api import CoreAPI, LoggingConfig


@pytest.fixture
def temp_config_dir():
    """Create a temporary config directory."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        yield Path(tmp_dir)


@pytest.fixture
def temp_output_dir():
    """Create a temporary output directory."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        yield Path(tmp_dir)


def test_logging_config_defaults():
    """Test default logging configuration values."""
    config = LoggingConfig()

    assert config.level == "INFO"
    assert config.output == "console"
    assert config.file_path == "logs/yaft.log"
    assert config.max_bytes == 10485760  # 10 MB
    assert config.backup_count == 5
    assert config.include_timestamp is True
    assert config.timestamp_format == "[%Y-%m-%d %H:%M:%S]"
    assert config.include_level is True
    assert config.include_name is False
    assert config.rich_formatting is True
    assert config.rich_tracebacks is True


def test_logging_config_validation_level():
    """Test log level validation."""
    # Valid levels
    for level in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]:
        config = LoggingConfig(level=level)
        assert config.level == level

    # Case insensitive
    config = LoggingConfig(level="debug")
    assert config.level == "DEBUG"

    config = LoggingConfig(level="Info")
    assert config.level == "INFO"

    # Invalid level
    with pytest.raises(ValueError, match="Invalid log level"):
        LoggingConfig(level="INVALID")


def test_logging_config_validation_output():
    """Test output mode validation."""
    # Valid outputs
    for output in ["console", "file", "both"]:
        config = LoggingConfig(output=output)
        assert config.output == output

    # Case insensitive
    config = LoggingConfig(output="Console")
    assert config.output == "console"

    config = LoggingConfig(output="FILE")
    assert config.output == "file"

    # Invalid output
    with pytest.raises(ValueError, match="Invalid output mode"):
        LoggingConfig(output="invalid")


def test_core_api_default_logging_config(temp_config_dir, temp_output_dir):
    """Test CoreAPI with default logging configuration (no config file)."""
    core_api = CoreAPI(config_dir=temp_config_dir, base_output_dir=temp_output_dir)

    # Should use default configuration
    assert core_api._logging_config.level == "INFO"
    assert core_api._logging_config.output == "console"


def test_core_api_load_logging_config_from_file(temp_config_dir, temp_output_dir):
    """Test CoreAPI loading logging configuration from TOML file."""
    # Create logging config file
    config_file = temp_config_dir / "logging.toml"
    config_data = {
        "logging": {
            "level": "DEBUG",
            "output": "file",
            "file_path": "custom/path/app.log",
            "max_bytes": 5242880,  # 5 MB
            "backup_count": 3,
            "format": {
                "include_timestamp": False,
                "include_level": False,
                "rich_formatting": False,
            },
        }
    }

    with open(config_file, "w", encoding="utf-8") as f:
        toml.dump(config_data, f)

    # Create CoreAPI and verify config loaded
    core_api = CoreAPI(config_dir=temp_config_dir, base_output_dir=temp_output_dir)

    try:
        assert core_api._logging_config.level == "DEBUG"
        assert core_api._logging_config.output == "file"
        assert core_api._logging_config.file_path == "custom/path/app.log"
        assert core_api._logging_config.max_bytes == 5242880
        assert core_api._logging_config.backup_count == 3
        assert core_api._logging_config.include_timestamp is False
        assert core_api._logging_config.include_level is False
        assert core_api._logging_config.rich_formatting is False
    finally:
        core_api.close_logging_handlers()


def test_core_api_logging_console_output(temp_config_dir, temp_output_dir):
    """Test logging to console."""
    # Create config for console output
    config_file = temp_config_dir / "logging.toml"
    config_data = {
        "logging": {
            "level": "DEBUG",
            "output": "console",
        }
    }

    with open(config_file, "w", encoding="utf-8") as f:
        toml.dump(config_data, f)

    core_api = CoreAPI(config_dir=temp_config_dir, base_output_dir=temp_output_dir)

    try:
        # Verify logger is configured (handlers are on root logger)
        assert core_api.logger.level == logging.DEBUG
        root_logger = logging.getLogger()
        assert len(root_logger.handlers) > 0
    finally:
        core_api.close_logging_handlers()


def test_core_api_logging_file_output(temp_config_dir, temp_output_dir):
    """Test logging to file."""
    # Create config for file output
    config_file = temp_config_dir / "logging.toml"
    log_file_path = "test_logs/yaft.log"
    config_data = {
        "logging": {
            "level": "INFO",
            "output": "file",
            "file_path": log_file_path,
        }
    }

    with open(config_file, "w", encoding="utf-8") as f:
        toml.dump(config_data, f)

    core_api = CoreAPI(config_dir=temp_config_dir, base_output_dir=temp_output_dir)

    try:
        # Log a test message
        core_api.log_info("Test log message")

        # Close handlers to flush and release file
        core_api.close_logging_handlers()

        # Verify log file was created
        expected_log_path = temp_output_dir / log_file_path
        assert expected_log_path.exists()

        # Verify log content
        with open(expected_log_path, encoding="utf-8") as f:
            log_content = f.read()
            assert "Test log message" in log_content
    finally:
        # Ensure handlers are closed
        if core_api.logger.handlers:
            core_api.close_logging_handlers()


def test_core_api_logging_both_output(temp_config_dir, temp_output_dir):
    """Test logging to both console and file."""
    # Create config for both outputs
    config_file = temp_config_dir / "logging.toml"
    log_file_path = "test_logs/yaft.log"
    config_data = {
        "logging": {
            "level": "WARNING",
            "output": "both",
            "file_path": log_file_path,
        }
    }

    with open(config_file, "w", encoding="utf-8") as f:
        toml.dump(config_data, f)

    core_api = CoreAPI(config_dir=temp_config_dir, base_output_dir=temp_output_dir)

    try:
        # Log messages
        core_api.log_warning("Test warning message")
        core_api.log_error("Test error message")

        # Close handlers to flush
        core_api.close_logging_handlers()

        # Verify log file was created and contains messages
        expected_log_path = temp_output_dir / log_file_path
        assert expected_log_path.exists()

        with open(expected_log_path, encoding="utf-8") as f:
            log_content = f.read()
            assert "Test warning message" in log_content
            assert "Test error message" in log_content
    finally:
        if core_api.logger.handlers:
            core_api.close_logging_handlers()


def test_core_api_logging_absolute_path(temp_config_dir, temp_output_dir):
    """Test logging with absolute file path."""
    # Create config with absolute path
    with tempfile.TemporaryDirectory() as tmp_log_dir:
        absolute_log_path = Path(tmp_log_dir) / "absolute.log"

        config_file = temp_config_dir / "logging.toml"
        config_data = {
            "logging": {
                "level": "INFO",
                "output": "file",
                "file_path": str(absolute_log_path),
            }
        }

        with open(config_file, "w", encoding="utf-8") as f:
            toml.dump(config_data, f)

        core_api = CoreAPI(config_dir=temp_config_dir, base_output_dir=temp_output_dir)

        try:
            # Log a message
            core_api.log_info("Absolute path test")

            # Close handlers to flush
            core_api.close_logging_handlers()

            # Verify log file at absolute path
            assert absolute_log_path.exists()
        finally:
            if core_api.logger.handlers:
                core_api.close_logging_handlers()


def test_core_api_logging_rotation(temp_config_dir, temp_output_dir):
    """Test log file rotation configuration."""
    config_file = temp_config_dir / "logging.toml"
    config_data = {
        "logging": {
            "level": "INFO",
            "output": "file",
            "file_path": "logs/rotate.log",
            "max_bytes": 1024,  # 1 KB for easy testing
            "backup_count": 2,
        }
    }

    with open(config_file, "w", encoding="utf-8") as f:
        toml.dump(config_data, f)

    core_api = CoreAPI(config_dir=temp_config_dir, base_output_dir=temp_output_dir)

    try:
        # Verify handler is RotatingFileHandler
        # Note: When output="file", we should check root logger handlers
        root_logger = logging.getLogger()
        file_handlers = [
            h for h in root_logger.handlers if isinstance(h, logging.handlers.RotatingFileHandler)
        ]
        assert len(file_handlers) >= 1

        handler = file_handlers[0]
        assert handler.maxBytes == 1024
        assert handler.backupCount == 2
    finally:
        core_api.close_logging_handlers()


def test_core_api_invalid_config_fallback(temp_config_dir, temp_output_dir):
    """Test that invalid config falls back to defaults."""
    # Create invalid config file
    config_file = temp_config_dir / "logging.toml"
    with open(config_file, "w", encoding="utf-8") as f:
        f.write("invalid toml content {{{")

    # Should still create CoreAPI with default config
    core_api = CoreAPI(config_dir=temp_config_dir, base_output_dir=temp_output_dir)

    # Should use default configuration
    assert core_api._logging_config.level == "INFO"
    assert core_api._logging_config.output == "console"


def test_logging_methods(temp_config_dir, temp_output_dir):
    """Test all logging methods."""
    config_file = temp_config_dir / "logging.toml"
    config_data = {
        "logging": {
            "level": "DEBUG",
            "output": "file",
            "file_path": "logs/methods.log",
        }
    }

    with open(config_file, "w", encoding="utf-8") as f:
        toml.dump(config_data, f)

    core_api = CoreAPI(config_dir=temp_config_dir, base_output_dir=temp_output_dir)

    try:
        # Test all logging methods
        core_api.log_debug("Debug message")
        core_api.log_info("Info message")
        core_api.log_warning("Warning message")
        core_api.log_error("Error message")

        # Close handlers to flush
        core_api.close_logging_handlers()

        # Verify all messages in log file
        log_path = temp_output_dir / "logs/methods.log"
        with open(log_path, encoding="utf-8") as f:
            log_content = f.read()
            assert "Debug message" in log_content
            assert "Info message" in log_content
            assert "Warning message" in log_content
            assert "Error message" in log_content
    finally:
        if core_api.logger.handlers:
            core_api.close_logging_handlers()


def test_logging_level_filtering(temp_config_dir, temp_output_dir):
    """Test that log level filtering works correctly."""
    config_file = temp_config_dir / "logging.toml"
    config_data = {
        "logging": {
            "level": "WARNING",  # Only WARNING and above
            "output": "file",
            "file_path": "logs/filter.log",
        }
    }

    with open(config_file, "w", encoding="utf-8") as f:
        toml.dump(config_data, f)

    core_api = CoreAPI(config_dir=temp_config_dir, base_output_dir=temp_output_dir)

    try:
        # Log at different levels
        core_api.log_debug("Debug message - should not appear")
        core_api.log_info("Info message - should not appear")
        core_api.log_warning("Warning message - should appear")
        core_api.log_error("Error message - should appear")

        # Close handlers to flush
        core_api.close_logging_handlers()

        # Verify only WARNING and ERROR appear
        log_path = temp_output_dir / "logs/filter.log"
        with open(log_path, encoding="utf-8") as f:
            log_content = f.read()
            assert "Debug message" not in log_content
            assert "Info message" not in log_content
            assert "Warning message" in log_content
            assert "Error message" in log_content
    finally:
        if core_api.logger.handlers:
            core_api.close_logging_handlers()
