"""Pytest configuration and fixtures."""

import tempfile
from pathlib import Path

import pytest

from yaft.core.api import CoreAPI
from yaft.core.plugin_manager import PluginManager


@pytest.fixture
def temp_dir():
    """Create a temporary directory for tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def core_api(temp_dir):
    """Create a CoreAPI instance for testing."""
    config_dir = temp_dir / "config"
    return CoreAPI(config_dir=config_dir)


@pytest.fixture
def plugin_dir(temp_dir):
    """Create a temporary plugin directory."""
    plugin_dir = temp_dir / "plugins"
    plugin_dir.mkdir()
    return plugin_dir


@pytest.fixture
def plugin_manager(core_api, plugin_dir):
    """Create a PluginManager instance for testing."""
    return PluginManager(core_api=core_api, plugin_dirs=[plugin_dir])
