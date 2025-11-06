"""Tests for PluginManager."""

from typing import Any

import pytest

from yaft.core.plugin_base import PluginBase, PluginMetadata, PluginStatus
from yaft.core.plugin_manager import PluginManager


# Test plugin for discovery
TEST_PLUGIN_CODE = '''"""Test plugin for unit tests."""

from typing import Any
from yaft.core.plugin_base import PluginBase, PluginMetadata


class TestDiscoveryPlugin(PluginBase):
    """A test plugin for discovery tests."""

    @property
    def metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name="TestDiscovery",
            version="1.0.0",
            description="Test plugin for discovery",
            author="Test",
        )

    def initialize(self) -> None:
        self.initialized = True

    def execute(self, *args: Any, **kwargs: Any) -> str:
        return "test_executed"

    def cleanup(self) -> None:
        pass
'''


def test_plugin_manager_initialization(core_api, plugin_dir):
    """Test PluginManager initialization."""
    manager = PluginManager(core_api=core_api, plugin_dirs=[plugin_dir])

    assert manager.core_api == core_api
    assert plugin_dir in manager.plugin_dirs
    assert len(manager.plugins) == 0


def test_plugin_discovery(plugin_manager, plugin_dir):
    """Test plugin discovery from directory."""
    # Create a test plugin file
    plugin_file = plugin_dir / "test_plugin.py"
    plugin_file.write_text(TEST_PLUGIN_CODE, encoding="utf-8")

    # Discover plugins
    discovered = plugin_manager.discover_plugins()

    assert len(discovered) > 0
    assert "TestDiscoveryPlugin" in discovered


def test_plugin_discovery_skips_private_files(plugin_manager, plugin_dir):
    """Test that plugin discovery skips private files."""
    # Create private file
    private_file = plugin_dir / "_private.py"
    private_file.write_text(TEST_PLUGIN_CODE, encoding="utf-8")

    discovered = plugin_manager.discover_plugins()

    # Should not discover private files
    assert len(discovered) == 0


def test_load_plugin(plugin_manager, plugin_dir):
    """Test loading a plugin."""
    # Create and discover plugin
    plugin_file = plugin_dir / "test_plugin.py"
    plugin_file.write_text(TEST_PLUGIN_CODE, encoding="utf-8")
    plugin_manager.discover_plugins()

    # Load plugin
    plugin = plugin_manager.load_plugin("TestDiscoveryPlugin")

    assert plugin is not None
    assert plugin.metadata.name == "TestDiscovery"
    assert plugin.status == PluginStatus.INITIALIZED
    assert "TestDiscoveryPlugin" in plugin_manager.plugins


def test_load_nonexistent_plugin(plugin_manager):
    """Test loading a plugin that doesn't exist."""
    plugin = plugin_manager.load_plugin("NonexistentPlugin")
    assert plugin is None


def test_load_plugin_twice(plugin_manager, plugin_dir):
    """Test loading the same plugin twice."""
    # Create and discover plugin
    plugin_file = plugin_dir / "test_plugin.py"
    plugin_file.write_text(TEST_PLUGIN_CODE, encoding="utf-8")
    plugin_manager.discover_plugins()

    # Load plugin twice
    plugin1 = plugin_manager.load_plugin("TestDiscoveryPlugin")
    plugin2 = plugin_manager.load_plugin("TestDiscoveryPlugin")

    # Should return the same instance
    assert plugin1 == plugin2


def test_unload_plugin(plugin_manager, plugin_dir):
    """Test unloading a plugin."""
    # Create, discover, and load plugin
    plugin_file = plugin_dir / "test_plugin.py"
    plugin_file.write_text(TEST_PLUGIN_CODE, encoding="utf-8")
    plugin_manager.discover_plugins()
    plugin_manager.load_plugin("TestDiscoveryPlugin")

    # Unload plugin
    success = plugin_manager.unload_plugin("TestDiscoveryPlugin")

    assert success is True
    assert "TestDiscoveryPlugin" not in plugin_manager.plugins


def test_unload_nonexistent_plugin(plugin_manager):
    """Test unloading a plugin that isn't loaded."""
    success = plugin_manager.unload_plugin("NonexistentPlugin")
    assert success is False


def test_get_plugin(plugin_manager, plugin_dir):
    """Test getting a loaded plugin."""
    # Create, discover, and load plugin
    plugin_file = plugin_dir / "test_plugin.py"
    plugin_file.write_text(TEST_PLUGIN_CODE, encoding="utf-8")
    plugin_manager.discover_plugins()
    plugin_manager.load_plugin("TestDiscoveryPlugin")

    # Get plugin
    plugin = plugin_manager.get_plugin("TestDiscoveryPlugin")

    assert plugin is not None
    assert plugin.metadata.name == "TestDiscovery"


def test_execute_plugin(plugin_manager, plugin_dir):
    """Test executing a loaded plugin."""
    # Create, discover, and load plugin
    plugin_file = plugin_dir / "test_plugin.py"
    plugin_file.write_text(TEST_PLUGIN_CODE, encoding="utf-8")
    plugin_manager.discover_plugins()
    plugin_manager.load_plugin("TestDiscoveryPlugin")

    # Execute plugin
    result = plugin_manager.execute_plugin("TestDiscoveryPlugin")

    assert result == "test_executed"


def test_execute_nonexistent_plugin(plugin_manager):
    """Test executing a plugin that isn't loaded."""
    result = plugin_manager.execute_plugin("NonexistentPlugin")
    assert result is None


def test_load_all_plugins(plugin_manager, plugin_dir):
    """Test loading all discovered plugins."""
    # Create multiple plugin files
    plugin_file1 = plugin_dir / "test_plugin1.py"
    plugin_file1.write_text(TEST_PLUGIN_CODE, encoding="utf-8")

    plugin_file2 = plugin_dir / "test_plugin2.py"
    plugin_code2 = TEST_PLUGIN_CODE.replace("TestDiscovery", "TestDiscovery2")
    plugin_file2.write_text(plugin_code2, encoding="utf-8")

    # Load all plugins
    plugin_manager.load_all_plugins()

    # Should have discovered and loaded all plugins
    assert len(plugin_manager.plugins) >= 2


def test_unload_all_plugins(plugin_manager, plugin_dir):
    """Test unloading all plugins."""
    # Create, discover, and load plugins
    plugin_file = plugin_dir / "test_plugin.py"
    plugin_file.write_text(TEST_PLUGIN_CODE, encoding="utf-8")
    plugin_manager.load_all_plugins()

    # Unload all plugins
    plugin_manager.unload_all_plugins()

    assert len(plugin_manager.plugins) == 0


def test_get_plugin_count(plugin_manager, plugin_dir):
    """Test getting plugin statistics."""
    # Create and load plugin
    plugin_file = plugin_dir / "test_plugin.py"
    plugin_file.write_text(TEST_PLUGIN_CODE, encoding="utf-8")
    plugin_manager.load_all_plugins()

    stats = plugin_manager.get_plugin_count()

    assert "total_discovered" in stats
    assert "loaded" in stats
    assert "active" in stats
    assert "error" in stats
    assert stats["total_discovered"] >= 1
    assert stats["loaded"] >= 1
