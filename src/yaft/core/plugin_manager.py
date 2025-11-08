"""
Plugin Manager for discovering, loading, and managing plugins.

This module handles the complete plugin lifecycle and provides a robust
discovery mechanism that works both in development and built executables.
"""

import importlib.util
import inspect
import sys
from pathlib import Path
from typing import Any

from rich.table import Table

from yaft.core.api import CoreAPI
from yaft.core.plugin_base import PluginBase, PluginStatus


class PluginManager:
    """
    Manages plugin discovery, loading, and lifecycle.

    The PluginManager handles:
    - Dynamic plugin discovery from directories
    - Plugin loading and validation
    - Plugin lifecycle management (initialize, execute, cleanup)
    - Plugin dependency resolution
    - Error handling and recovery
    """

    def __init__(self, core_api: CoreAPI, plugin_dirs: list[Path] | None = None) -> None:
        """
        Initialize the Plugin Manager.

        Args:
            core_api: CoreAPI instance to provide to plugins
            plugin_dirs: List of directories to search for plugins
        """
        self.core_api = core_api
        self.plugin_dirs = plugin_dirs or [Path.cwd() / "plugins"]
        self.plugins: dict[str, PluginBase] = {}
        self._plugin_classes: dict[str, type[PluginBase]] = {}

        # Ensure plugin directories exist
        for plugin_dir in self.plugin_dirs:
            plugin_dir.mkdir(parents=True, exist_ok=True)

    def discover_plugins(self) -> dict[str, type[PluginBase]]:
        """
        Discover all available plugins from plugin directories.

        Returns:
            dict: Mapping of plugin names to plugin classes

        The discovery process:
        1. Scan all plugin directories
        2. Find Python files (*.py)
        3. Load modules dynamically
        4. Inspect for PluginBase subclasses
        5. Validate plugin structure
        """
        discovered: dict[str, type[PluginBase]] = {}

        for plugin_dir in self.plugin_dirs:
            if not plugin_dir.exists():
                self.core_api.log_warning(f"Plugin directory not found: {plugin_dir}")
                continue

            self.core_api.log_info(f"Scanning for plugins in: {plugin_dir}")

            # Find all Python files in the plugin directory
            for plugin_file in plugin_dir.glob("*.py"):
                if plugin_file.name.startswith("_"):
                    continue  # Skip private modules

                try:
                    plugin_class = self._load_plugin_from_file(plugin_file)
                    if plugin_class:
                        plugin_name = plugin_class.__name__
                        discovered[plugin_name] = plugin_class
                        self.core_api.log_info(
                            f"Discovered plugin: {plugin_name} from {plugin_file.name}"
                        )
                except Exception as e:
                    self.core_api.log_error(f"Failed to load plugin from {plugin_file}: {e}")

        self._plugin_classes = discovered
        return discovered

    def _load_plugin_from_file(self, filepath: Path) -> type[PluginBase] | None:
        """
        Load a plugin class from a Python file.

        Args:
            filepath: Path to the plugin file

        Returns:
            type[PluginBase] | None: Plugin class if found, None otherwise
        """
        module_name = f"yaft.plugins.{filepath.stem}"

        # Load the module dynamically
        spec = importlib.util.spec_from_file_location(module_name, filepath)
        if spec is None or spec.loader is None:
            return None

        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)

        # Find PluginBase subclasses in the module
        for _name, obj in inspect.getmembers(module, inspect.isclass):
            if issubclass(obj, PluginBase) and obj is not PluginBase:
                return obj

        return None

    def load_plugin(self, plugin_name: str) -> PluginBase | None:
        """
        Load and initialize a specific plugin.

        Args:
            plugin_name: Name of the plugin class to load

        Returns:
            PluginBase | None: Loaded plugin instance or None if failed
        """
        if plugin_name in self.plugins:
            self.core_api.log_warning(f"Plugin {plugin_name} is already loaded")
            return self.plugins[plugin_name]

        if plugin_name not in self._plugin_classes:
            self.core_api.log_error(f"Plugin {plugin_name} not found")
            return None

        try:
            # Instantiate the plugin
            plugin_class = self._plugin_classes[plugin_name]
            plugin = plugin_class(self.core_api)

            # Check if plugin is enabled
            if not plugin.metadata.enabled:
                self.core_api.log_info(f"Plugin {plugin_name} is disabled, skipping")
                plugin.status = PluginStatus.DISABLED
                return None

            # Initialize the plugin
            plugin.initialize()
            plugin.status = PluginStatus.INITIALIZED

            # Store the loaded plugin using class name for consistency
            self.plugins[plugin_name] = plugin
            self.core_api.log_info(
                f"Loaded plugin: {plugin.metadata.name} v{plugin.metadata.version}"
            )

            return plugin

        except Exception as e:
            self.core_api.log_error(f"Failed to load plugin {plugin_name}: {e}")
            if plugin_name in self.plugins:
                self.plugins[plugin_name].status = PluginStatus.ERROR
            return None

    def load_all_plugins(self) -> None:
        """Discover and load all available plugins."""
        self.discover_plugins()

        for plugin_name in self._plugin_classes:
            self.load_plugin(plugin_name)

    def unload_plugin(self, plugin_name: str) -> bool:
        """
        Unload a specific plugin.

        Args:
            plugin_name: Name of the plugin to unload

        Returns:
            bool: True if successfully unloaded, False otherwise
        """
        if plugin_name not in self.plugins:
            self.core_api.log_warning(f"Plugin {plugin_name} is not loaded")
            return False

        try:
            plugin = self.plugins[plugin_name]
            plugin.cleanup()
            plugin.status = PluginStatus.UNLOADED
            del self.plugins[plugin_name]
            self.core_api.log_info(f"Unloaded plugin: {plugin_name}")
            return True
        except Exception as e:
            self.core_api.log_error(f"Failed to unload plugin {plugin_name}: {e}")
            return False

    def unload_all_plugins(self) -> None:
        """Unload all loaded plugins."""
        plugin_names = list(self.plugins.keys())
        for plugin_name in plugin_names:
            self.unload_plugin(plugin_name)

    def get_plugin(self, plugin_name: str) -> PluginBase | None:
        """
        Get a loaded plugin by name.

        Args:
            plugin_name: Name of the plugin

        Returns:
            PluginBase | None: Plugin instance or None if not found
        """
        return self.plugins.get(plugin_name)

    def execute_plugin(self, plugin_name: str, *args: Any, **kwargs: Any) -> Any:
        """
        Execute a loaded plugin.

        Args:
            plugin_name: Name of the plugin to execute
            *args: Positional arguments to pass to plugin
            **kwargs: Keyword arguments to pass to plugin

        Returns:
            Any: Plugin execution result
        """
        plugin = self.get_plugin(plugin_name)
        if plugin is None:
            self.core_api.log_error(f"Plugin {plugin_name} is not loaded")
            return None

        try:
            plugin.status = PluginStatus.ACTIVE
            result = plugin.execute(*args, **kwargs)
            plugin.status = PluginStatus.INITIALIZED
            return result
        except Exception as e:
            self.core_api.log_error(f"Plugin execution failed for {plugin_name}: {e}")
            plugin.status = PluginStatus.ERROR
            raise

    def is_plugin_compatible(self, plugin_class: type[PluginBase], detected_os: str) -> bool:
        """
        Check if a plugin is compatible with the detected OS.

        Args:
            plugin_class: Plugin class to check
            detected_os: Detected OS type ("ios", "android", "unknown")

        Returns:
            bool: True if plugin is compatible, False otherwise
        """
        try:
            # Create temporary instance to get metadata
            temp_plugin = plugin_class(self.core_api)
            target_os_list = temp_plugin.metadata.target_os

            # If plugin targets "any", it's always compatible
            if "any" in target_os_list:
                return True

            # If OS is unknown, only show "any" plugins
            if detected_os == "unknown":
                return False

            # Check if detected OS is in the target list
            return detected_os in target_os_list

        except Exception:
            # If we can't determine compatibility, assume it's compatible
            return True

    def get_compatible_plugins(self, detected_os: str | None = None) -> dict[str, type[PluginBase]]:
        """
        Get plugins compatible with the detected OS.

        Args:
            detected_os: Detected OS type. If None, auto-detects from current ZIP.

        Returns:
            dict: Dictionary of compatible plugin classes
        """
        # Auto-detect OS if not provided and ZIP is loaded
        if detected_os is None:
            try:
                os_type = self.core_api.get_detected_os()
                detected_os = os_type.value
            except RuntimeError:
                # No ZIP loaded, show all plugins
                detected_os = "any"

        # If no OS detected or no ZIP, show all plugins
        if detected_os == "any":
            return self._plugin_classes

        # Filter plugins by compatibility
        compatible = {}
        for name, plugin_class in self._plugin_classes.items():
            if self.is_plugin_compatible(plugin_class, detected_os):
                compatible[name] = plugin_class

        return compatible

    def list_plugins(self, show_all: bool = False, filter_by_os: bool = False) -> None:
        """
        Display a formatted list of plugins.

        Args:
            show_all: If True, show all discovered plugins. If False, show only loaded.
            filter_by_os: If True, filter plugins by detected OS compatibility.
        """
        # Get OS detection info if filtering is enabled
        os_info_str = ""
        if filter_by_os:
            try:
                extraction_info = self.core_api.get_extraction_info()
                os_type = extraction_info["os_type"]
                os_version = extraction_info["os_version"]
                if os_version:
                    os_info_str = f" (Detected: {os_type.upper()} {os_version})"
                else:
                    os_info_str = f" (Detected: {os_type.upper()})"
            except RuntimeError:
                os_info_str = " (No ZIP loaded)"
                filter_by_os = False

        table_title = "Available Plugins" if show_all else "Loaded Plugins"
        table_title += os_info_str
        table = Table(title=table_title)

        table.add_column("Name", style="cyan", no_wrap=True)
        table.add_column("Version", style="magenta")
        table.add_column("Status", style="green")
        table.add_column("Target OS", style="yellow")
        table.add_column("Description", style="white")

        # Get plugins to show
        if filter_by_os:
            # Filter by OS compatibility
            compatible_plugins = self.get_compatible_plugins()
            plugins_to_show = compatible_plugins.items() if show_all else [
                (k, v) for k, v in compatible_plugins.items()
                if k in self.plugins or any(p.__class__.__name__ == k for p in self.plugins.values())
            ]
        else:
            # No filtering
            plugins_to_show = (
                self._plugin_classes.items() if show_all else [(k, v) for k, v in self._plugin_classes.items() if k in self.plugins or any(p.__class__.__name__ == k for p in self.plugins.values())]
            )

        for plugin_name, plugin_class in plugins_to_show:
            # Try to get instance metadata if loaded, otherwise create temporary instance
            if plugin_name in self.plugins:
                plugin = self.plugins[plugin_name]
                metadata = plugin.metadata
                status = plugin.status.value
            else:
                # Check if any loaded plugin is an instance of this class
                loaded_plugin = next(
                    (p for p in self.plugins.values() if isinstance(p, plugin_class)), None
                )
                if loaded_plugin:
                    metadata = loaded_plugin.metadata
                    status = loaded_plugin.status.value
                else:
                    # Create temporary instance to get metadata
                    try:
                        temp_plugin = plugin_class(self.core_api)
                        metadata = temp_plugin.metadata
                        status = "unloaded"
                    except Exception:
                        continue

            status_color = {
                "unloaded": "yellow",
                "loaded": "blue",
                "initialized": "green",
                "active": "bright_green",
                "error": "red",
                "disabled": "dim",
            }.get(status, "white")

            # Format target OS list
            target_os_str = ", ".join(metadata.target_os)

            table.add_row(
                metadata.name,
                metadata.version,
                f"[{status_color}]{status}[/{status_color}]",
                target_os_str,
                metadata.description,
            )

        self.core_api.console.print(table)

    def get_plugin_count(self) -> dict[str, int]:
        """
        Get statistics about plugins.

        Returns:
            dict: Plugin counts by category
        """
        return {
            "total_discovered": len(self._plugin_classes),
            "loaded": len(self.plugins),
            "active": sum(1 for p in self.plugins.values() if p.status == PluginStatus.ACTIVE),
            "error": sum(1 for p in self.plugins.values() if p.status == PluginStatus.ERROR),
        }
