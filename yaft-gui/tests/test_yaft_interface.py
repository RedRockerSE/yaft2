"""Tests for YAFT interface module."""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch

from yaft_gui.core.yaft_interface import YAFTInterface


@pytest.fixture
def mock_interface():
    """Create YAFTInterface with mocked executable."""
    with patch.object(YAFTInterface, '_locate_yaft_exe', return_value=Path('yaft.exe')):
        interface = YAFTInterface("yaft.exe")
        return interface


def test_build_command_with_plugins(mock_interface):
    """Test building command with individual plugins."""
    interface = mock_interface

    cmd = interface.build_command(
        zip_file="evidence.zip",
        plugins=["Plugin1", "Plugin2"],
        html_export=True,
    )

    assert "yaft.exe" in str(cmd[0])
    assert "run" in cmd
    assert "--zip" in cmd
    assert "evidence.zip" in cmd
    assert "Plugin1" in cmd
    assert "Plugin2" in cmd
    assert "--html" in cmd


def test_build_command_with_profile(mock_interface):
    """Test building command with profile."""
    interface = mock_interface

    cmd = interface.build_command(
        zip_file="evidence.zip",
        profile="profile.toml",
        pdf_export=True,
    )

    assert "run" in cmd
    assert "--zip" in cmd
    assert "--profile" in cmd
    assert "profile.toml" in cmd
    assert "--pdf" in cmd


def test_build_command_requires_plugins_or_profile(mock_interface):
    """Test that either plugins or profile must be specified."""
    interface = mock_interface

    with pytest.raises(ValueError, match="Must specify either plugins or profile"):
        interface.build_command(zip_file="evidence.zip")


def test_build_command_not_both_plugins_and_profile(mock_interface):
    """Test that both plugins and profile cannot be specified."""
    interface = mock_interface

    with pytest.raises(ValueError, match="Cannot specify both"):
        interface.build_command(
            zip_file="evidence.zip",
            plugins=["Plugin1"],
            profile="profile.toml",
        )


def test_parse_plugin_list(mock_interface):
    """Test parsing plugin list output."""
    interface = mock_interface

    output = """
Available plugins:
---
TestPlugin1 (v1.0.0) - Test plugin one
TestPlugin2 (v2.1.0) - Test plugin two
AnotherPlugin (v1.5.2) - Another test plugin
"""

    plugins = interface._parse_plugin_list(output)

    assert len(plugins) == 3
    assert plugins[0]["name"] == "TestPlugin1"
    assert plugins[0]["version"] == "1.0.0"
    assert plugins[0]["description"] == "Test plugin one"
    assert plugins[2]["name"] == "AnotherPlugin"


def test_validate_zip_file(mock_interface, tmp_path):
    """Test ZIP file validation."""
    interface = mock_interface

    # Create a test ZIP file
    zip_path = tmp_path / "test.zip"
    zip_path.touch()

    assert interface.validate_zip_file(str(zip_path)) is True

    # Test non-existent file
    assert interface.validate_zip_file("nonexistent.zip") is False

    # Test non-ZIP file
    txt_path = tmp_path / "test.txt"
    txt_path.touch()
    assert interface.validate_zip_file(str(txt_path)) is False
