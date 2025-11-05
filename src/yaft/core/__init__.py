"""Core framework components."""

from yaft.core.api import CoreAPI
from yaft.core.plugin_base import PluginBase, PluginMetadata
from yaft.core.plugin_manager import PluginManager

__all__ = [
    "CoreAPI",
    "PluginBase",
    "PluginMetadata",
    "PluginManager",
]
