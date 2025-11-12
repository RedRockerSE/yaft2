"""
Tests for plugin profile functionality.
"""

import tempfile
from pathlib import Path

import pytest

from yaft.core.api import CoreAPI, PluginProfile


@pytest.fixture
def core_api(tmp_path):
    """Create CoreAPI instance with temporary output directory."""
    api = CoreAPI()
    api.base_output_dir = tmp_path / "yaft_output"
    api.base_output_dir.mkdir(parents=True, exist_ok=True)
    return api


@pytest.fixture
def valid_profile_toml(tmp_path):
    """Create a valid TOML profile file."""
    profile_path = tmp_path / "test_profile.toml"
    content = """
[profile]
name = "Test Profile"
description = "A test profile for unit testing"

plugins = [
    "HelloWorldPlugin",
    "SystemInfoPlugin",
]
"""
    profile_path.write_text(content, encoding="utf-8")
    return profile_path


@pytest.fixture
def minimal_profile_toml(tmp_path):
    """Create a minimal TOML profile file (no description)."""
    profile_path = tmp_path / "minimal_profile.toml"
    content = """
[profile]
name = "Minimal Profile"

plugins = [
    "HelloWorldPlugin",
]
"""
    profile_path.write_text(content, encoding="utf-8")
    return profile_path


@pytest.fixture
def invalid_syntax_profile_toml(tmp_path):
    """Create a TOML profile file with invalid syntax."""
    profile_path = tmp_path / "invalid_syntax.toml"
    content = """
[profile
name = "Invalid Profile"
plugins = ["HelloWorldPlugin"]
"""
    profile_path.write_text(content, encoding="utf-8")
    return profile_path


@pytest.fixture
def missing_section_profile_toml(tmp_path):
    """Create a TOML profile file missing the [profile] section."""
    profile_path = tmp_path / "missing_section.toml"
    content = """
[other_section]
name = "Wrong Section"
plugins = ["HelloWorldPlugin"]
"""
    profile_path.write_text(content, encoding="utf-8")
    return profile_path


@pytest.fixture
def empty_plugins_profile_toml(tmp_path):
    """Create a TOML profile file with empty plugins list."""
    profile_path = tmp_path / "empty_plugins.toml"
    content = """
[profile]
name = "Empty Plugins"
plugins = []
"""
    profile_path.write_text(content, encoding="utf-8")
    return profile_path


@pytest.fixture
def missing_name_profile_toml(tmp_path):
    """Create a TOML profile file missing the name field."""
    profile_path = tmp_path / "missing_name.toml"
    content = """
[profile]
plugins = ["HelloWorldPlugin"]
"""
    profile_path.write_text(content, encoding="utf-8")
    return profile_path


class TestPluginProfileModel:
    """Test the PluginProfile Pydantic model."""

    def test_valid_profile_with_description(self):
        """Test creating a valid profile with all fields."""
        profile = PluginProfile(
            name="Test Profile",
            description="Test description",
            plugins=["Plugin1", "Plugin2"],
        )

        assert profile.name == "Test Profile"
        assert profile.description == "Test description"
        assert profile.plugins == ["Plugin1", "Plugin2"]

    def test_valid_profile_without_description(self):
        """Test creating a valid profile without description."""
        profile = PluginProfile(
            name="Test Profile",
            plugins=["Plugin1"],
        )

        assert profile.name == "Test Profile"
        assert profile.description is None
        assert profile.plugins == ["Plugin1"]

    def test_invalid_profile_empty_plugins(self):
        """Test that empty plugins list raises validation error."""
        with pytest.raises(ValueError, match="List should have at least 1 item"):
            PluginProfile(
                name="Test",
                plugins=[],
            )

    def test_invalid_profile_empty_plugin_name(self):
        """Test that empty plugin name raises validation error."""
        with pytest.raises(ValueError, match="plugin names cannot be empty"):
            PluginProfile(
                name="Test",
                plugins=["ValidPlugin", "", "AnotherPlugin"],
            )

    def test_invalid_profile_whitespace_plugin_name(self):
        """Test that whitespace-only plugin name raises validation error."""
        with pytest.raises(ValueError, match="plugin names cannot be empty"):
            PluginProfile(
                name="Test",
                plugins=["ValidPlugin", "   ", "AnotherPlugin"],
            )

    def test_invalid_profile_missing_name(self):
        """Test that missing name raises validation error."""
        with pytest.raises(ValueError):
            PluginProfile(
                plugins=["Plugin1"],
            )

    def test_invalid_profile_missing_plugins(self):
        """Test that missing plugins raises validation error."""
        with pytest.raises(ValueError):
            PluginProfile(
                name="Test",
            )


class TestLoadPluginProfile:
    """Test the load_plugin_profile method."""

    def test_load_valid_profile(self, core_api, valid_profile_toml):
        """Test loading a valid profile file."""
        profile = core_api.load_plugin_profile(valid_profile_toml)

        assert isinstance(profile, PluginProfile)
        assert profile.name == "Test Profile"
        assert profile.description == "A test profile for unit testing"
        assert profile.plugins == ["HelloWorldPlugin", "SystemInfoPlugin"]

    def test_load_minimal_profile(self, core_api, minimal_profile_toml):
        """Test loading a minimal profile file."""
        profile = core_api.load_plugin_profile(minimal_profile_toml)

        assert isinstance(profile, PluginProfile)
        assert profile.name == "Minimal Profile"
        assert profile.description is None
        assert profile.plugins == ["HelloWorldPlugin"]

    def test_load_nonexistent_profile(self, core_api, tmp_path):
        """Test loading a profile that doesn't exist."""
        nonexistent_path = tmp_path / "nonexistent.toml"

        with pytest.raises(FileNotFoundError, match="Profile file not found"):
            core_api.load_plugin_profile(nonexistent_path)

    def test_load_directory_instead_of_file(self, core_api, tmp_path):
        """Test loading a directory instead of a file."""
        dir_path = tmp_path / "profile_dir"
        dir_path.mkdir()

        with pytest.raises(ValueError, match="Profile path is not a file"):
            core_api.load_plugin_profile(dir_path)

    def test_load_invalid_syntax_profile(self, core_api, invalid_syntax_profile_toml):
        """Test loading a profile with invalid TOML syntax."""
        with pytest.raises(ValueError, match="Invalid TOML syntax"):
            core_api.load_plugin_profile(invalid_syntax_profile_toml)

    def test_load_missing_section_profile(self, core_api, missing_section_profile_toml):
        """Test loading a profile missing the [profile] section."""
        with pytest.raises(ValueError, match="must contain a \\[profile\\] section"):
            core_api.load_plugin_profile(missing_section_profile_toml)

    def test_load_empty_plugins_profile(self, core_api, empty_plugins_profile_toml):
        """Test loading a profile with empty plugins list."""
        with pytest.raises(ValueError, match="Failed to parse profile file"):
            core_api.load_plugin_profile(empty_plugins_profile_toml)

    def test_load_missing_name_profile(self, core_api, missing_name_profile_toml):
        """Test loading a profile missing the name field."""
        with pytest.raises(ValueError, match="Failed to parse profile file"):
            core_api.load_plugin_profile(missing_name_profile_toml)

    def test_load_profile_with_special_characters(self, core_api, tmp_path):
        """Test loading a profile with special characters in fields."""
        profile_path = tmp_path / "special_chars.toml"
        # Use single quotes for the description to avoid escaping issues in TOML
        content = """
[profile]
name = "Profile with Special Chars: @#$%"
description = 'Description with quotes "test" and symbols <>'

plugins = [
    "Plugin_with_underscores",
    "PluginWithNumbers123",
]
"""
        profile_path.write_text(content, encoding="utf-8")

        profile = core_api.load_plugin_profile(profile_path)

        assert profile.name == "Profile with Special Chars: @#$%"
        assert 'quotes "test"' in profile.description
        assert profile.plugins == ["Plugin_with_underscores", "PluginWithNumbers123"]

    def test_load_profile_with_long_plugin_list(self, core_api, tmp_path):
        """Test loading a profile with many plugins."""
        profile_path = tmp_path / "long_list.toml"
        plugins = [f"Plugin{i}" for i in range(50)]
        content = f"""
[profile]
name = "Long Plugin List"

plugins = {plugins}
"""
        profile_path.write_text(content, encoding="utf-8")

        profile = core_api.load_plugin_profile(profile_path)

        assert len(profile.plugins) == 50
        assert profile.plugins[0] == "Plugin0"
        assert profile.plugins[-1] == "Plugin49"


class TestProfileIntegration:
    """Integration tests for profile functionality."""

    def test_profile_roundtrip(self, core_api, tmp_path):
        """Test creating, saving, and loading a profile."""
        # Create a profile file
        profile_path = tmp_path / "roundtrip.toml"
        content = """
[profile]
name = "Roundtrip Test"
description = "Test roundtrip functionality"

plugins = [
    "PluginA",
    "PluginB",
    "PluginC",
]
"""
        profile_path.write_text(content, encoding="utf-8")

        # Load the profile
        profile = core_api.load_plugin_profile(profile_path)

        # Verify all fields
        assert profile.name == "Roundtrip Test"
        assert profile.description == "Test roundtrip functionality"
        assert len(profile.plugins) == 3
        assert "PluginA" in profile.plugins
        assert "PluginB" in profile.plugins
        assert "PluginC" in profile.plugins

    def test_profile_with_unicode(self, core_api, tmp_path):
        """Test profile with Unicode characters."""
        profile_path = tmp_path / "unicode.toml"
        content = """
[profile]
name = "Profile avec caractères spéciaux 中文"
description = "Тест Unicode поддержки"

plugins = [
    "HelloWorldPlugin",
]
"""
        profile_path.write_text(content, encoding="utf-8")

        profile = core_api.load_plugin_profile(profile_path)

        assert "avec caractères" in profile.name
        assert "中文" in profile.name
        assert "поддержки" in profile.description
