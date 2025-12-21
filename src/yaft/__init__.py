"""
YAFT - Yet Another Forensic Tool
A plugin-based forensic analysis tool for processing ZIP archives.
"""

__version__ = "0.7.0"
__author__ = "magjon@gmail.com (RedRockerSE)"

from yaft.core.api import CoreAPI
from yaft.core.plugin_base import PluginBase, PluginMetadata
from yaft.core.plugin_manager import PluginManager

__all__ = [
    "CoreAPI",
    "PluginBase",
    "PluginMetadata",
    "PluginManager",
]
