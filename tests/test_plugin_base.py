"""Tests for PluginBase and related classes."""

from typing import Any

import pytest

from yaft.core.plugin_base import PluginBase, PluginMetadata, PluginStatus


class MockPlugin(PluginBase):
    """Mock plugin for testing."""

    @property
    def metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name="MockPlugin",
            version="1.0.0",
            description="A mock plugin for testing",
            author="Test Author",
            requires_core_version=">=0.1.0",
            dependencies=[],
            enabled=True,
        )

    def initialize(self) -> None:
        self.initialized = True

    def execute(self, *args: Any, **kwargs: Any) -> str:
        return "executed"

    def cleanup(self) -> None:
        self.cleaned_up = True


def test_plugin_metadata():
    """Test PluginMetadata creation and validation."""
    metadata = PluginMetadata(
        name="TestPlugin",
        version="1.0.0",
        description="Test description",
        author="Test Author",
    )

    assert metadata.name == "TestPlugin"
    assert metadata.version == "1.0.0"
    assert metadata.description == "Test description"
    assert metadata.author == "Test Author"
    assert metadata.enabled is True
    assert metadata.dependencies == []


def test_plugin_metadata_immutable():
    """Test that PluginMetadata is immutable."""
    metadata = PluginMetadata(
        name="TestPlugin",
        version="1.0.0",
        description="Test description",
    )

    with pytest.raises(Exception):
        metadata.name = "NewName"


def test_plugin_initialization(core_api):
    """Test plugin initialization."""
    plugin = MockPlugin(core_api)

    assert plugin.core_api == core_api
    assert plugin.status == PluginStatus.LOADED


def test_plugin_lifecycle(core_api):
    """Test complete plugin lifecycle."""
    plugin = MockPlugin(core_api)

    # Initialize
    plugin.initialize()
    assert hasattr(plugin, "initialized")
    assert plugin.initialized is True

    # Execute
    result = plugin.execute()
    assert result == "executed"

    # Cleanup
    plugin.cleanup()
    assert hasattr(plugin, "cleaned_up")
    assert plugin.cleaned_up is True


def test_plugin_status_changes(core_api):
    """Test plugin status changes."""
    plugin = MockPlugin(core_api)

    assert plugin.status == PluginStatus.LOADED

    plugin.status = PluginStatus.INITIALIZED
    assert plugin.status == PluginStatus.INITIALIZED

    plugin.status = PluginStatus.ACTIVE
    assert plugin.status == PluginStatus.ACTIVE

    plugin.status = PluginStatus.ERROR
    assert plugin.status == PluginStatus.ERROR


def test_plugin_repr(core_api):
    """Test plugin string representation."""
    plugin = MockPlugin(core_api)
    repr_str = repr(plugin)

    assert "MockPlugin" in repr_str
    assert "1.0.0" in repr_str
    assert plugin.status.value in repr_str


def test_plugin_execute_with_args(core_api):
    """Test plugin execute with arguments."""
    class ArgsPlugin(PluginBase):
        @property
        def metadata(self) -> PluginMetadata:
            return PluginMetadata(
                name="ArgsPlugin",
                version="1.0.0",
                description="Test plugin with args",
            )

        def initialize(self) -> None:
            pass

        def execute(self, *args: Any, **kwargs: Any) -> dict[str, Any]:
            return {"args": args, "kwargs": kwargs}

        def cleanup(self) -> None:
            pass

    plugin = ArgsPlugin(core_api)
    result = plugin.execute("arg1", "arg2", key1="value1", key2="value2")

    assert result["args"] == ("arg1", "arg2")
    assert result["kwargs"] == {"key1": "value1", "key2": "value2"}
