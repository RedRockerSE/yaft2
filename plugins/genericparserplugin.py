"""
A generic parser aimed at showcasing the create_plugin.py tool.

This plugin was generated using the YAFT plugin template.
"""

from typing import Any

from yaft.core.api import CoreAPI
from yaft.core.plugin_base import PluginBase, PluginMetadata


class Genericparserplugin(PluginBase):
    """
    A generic parser aimed at showcasing the create_plugin.py tool.

    This plugin implements the PluginBase interface.
    """

    def __init__(self, core_api: CoreAPI) -> None:
        """
        Initialize the plugin.

        Args:
            core_api: CoreAPI instance for accessing shared functionality
        """
        super().__init__(core_api)
        # Add your instance variables here
        self._state = {}

    @property
    def metadata(self) -> PluginMetadata:
        """
        Return plugin metadata.

        Returns:
            PluginMetadata: Plugin configuration and information
        """
        return PluginMetadata(
            name="Genericparserplugin",
            version="1.0.0",
            description="A generic parser aimed at showcasing the create_plugin.py tool.",
            author="Magnus Jonsson",
            requires_core_version=">=0.1.0",
            dependencies=[],
            enabled=True,
        )

    def initialize(self) -> None:
        """
        Initialize plugin resources.

        Called once after plugin is loaded. Use this for:
        - Loading configuration
        - Setting up resources
        - Validating dependencies

        Raises:
            Exception: If initialization fails
        """
        self.core_api.log_info(f"Initializing {self.metadata.name} plugin")

        # Example: Load configuration
        # config_path = self.core_api.get_config_path("genericparserplugin.toml")
        # if config_path.exists():
        #     import toml
        #     self.config = toml.loads(self.core_api.read_file(config_path))

        # Add your initialization logic here

    def execute(self, *args: Any, **kwargs: Any) -> Any:
        """
        Execute the plugin's main functionality.

        This is called when the plugin is run by the user.

        Args:
            *args: Positional arguments passed to the plugin
            **kwargs: Keyword arguments passed to the plugin

        Returns:
            Any: Plugin execution result

        Raises:
            Exception: If execution fails
        """
        self.core_api.log_info(f"Executing {self.metadata.name} plugin")

        # Example: Parse arguments
        # if args:
        #     input_value = args[0]
        # else:
        #     input_value = self.core_api.get_user_input("Enter value")

        # Add your main plugin logic here
        result = self._process()

        # Example: Display results
        self.core_api.print_success("Plugin executed successfully!")

        return result

    def cleanup(self) -> None:
        """
        Clean up plugin resources.

        Called when plugin is unloaded or application exits. Use this for:
        - Closing file handles
        - Releasing network connections
        - Saving state

        Note: Should not raise exceptions.
        """
        self.core_api.log_info(f"Cleaning up {self.metadata.name} plugin")

        # Add your cleanup logic here
        # Example: Save state
        # self._save_state()

    def _process(self) -> dict[str, Any]:
        """
        Process data and return results.

        This is a helper method for the execute() method.

        Returns:
            dict: Processing results
        """
        # Add your processing logic here
        return {
            "status": "success",
            "message": "Plugin executed successfully",
        }
