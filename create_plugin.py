#!/usr/bin/env python3
"""
Helper script to create a new plugin from a template.

Usage:
    python create_plugin.py
    python create_plugin.py --name MyPlugin --author "Your Name"
"""

import argparse
import sys
from pathlib import Path


PLUGIN_TEMPLATE = '''"""
{description}

This plugin was generated using the YAFT plugin template.
"""

from typing import Any

from yaft.core.api import CoreAPI
from yaft.core.plugin_base import PluginBase, PluginMetadata


class {class_name}(PluginBase):
    """
    {description}

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
        self._state = {{}}

    @property
    def metadata(self) -> PluginMetadata:
        """
        Return plugin metadata.

        Returns:
            PluginMetadata: Plugin configuration and information
        """
        return PluginMetadata(
            name="{plugin_name}",
            version="1.0.0",
            description="{description}",
            author="{author}",
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
        self.core_api.log_info(f"Initializing {{self.metadata.name}} plugin")

        # Example: Load configuration
        # config_path = self.core_api.get_config_path("{config_name}.toml")
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
        self.core_api.log_info(f"Executing {{self.metadata.name}} plugin")

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
        self.core_api.log_info(f"Cleaning up {{self.metadata.name}} plugin")

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
        return {{
            "status": "success",
            "message": "Plugin executed successfully",
        }}
'''


def sanitize_name(name: str) -> str:
    """Convert a plugin name to a valid class name."""
    # Remove non-alphanumeric characters
    name = "".join(c for c in name if c.isalnum() or c == "_")
    # Ensure it starts with a letter
    if name and name[0].isdigit():
        name = "Plugin" + name
    # Capitalize each word
    parts = name.split("_")
    return "".join(word.capitalize() for word in parts)


def get_user_input(prompt: str, default: str = "") -> str:
    """Get user input with a default value."""
    if default:
        response = input(f"{prompt} [{default}]: ").strip()
        return response if response else default
    else:
        response = input(f"{prompt}: ").strip()
        while not response:
            response = input(f"{prompt} (required): ").strip()
        return response


def create_plugin(
    name: str,
    description: str,
    author: str,
    output_dir: Path,
) -> Path:
    """
    Create a new plugin file from template.

    Args:
        name: Plugin name (will be converted to class name)
        description: Plugin description
        author: Plugin author
        output_dir: Directory to create plugin in

    Returns:
        Path: Path to created plugin file
    """
    # Generate names
    class_name = sanitize_name(name)
    plugin_name = class_name
    file_name = name.lower().replace(" ", "_") + ".py"
    config_name = name.lower().replace(" ", "_")

    # Fill template
    plugin_code = PLUGIN_TEMPLATE.format(
        class_name=class_name,
        plugin_name=plugin_name,
        description=description,
        author=author,
        config_name=config_name,
    )

    # Create file
    output_file = output_dir / file_name
    output_file.write_text(plugin_code, encoding="utf-8")

    return output_file


def main() -> int:
    """Main function."""
    parser = argparse.ArgumentParser(
        description="Create a new YAFT plugin from template"
    )
    parser.add_argument(
        "--name",
        help="Plugin name (e.g., 'MyPlugin' or 'My Plugin')",
    )
    parser.add_argument(
        "--description",
        help="Plugin description",
    )
    parser.add_argument(
        "--author",
        help="Plugin author name",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("plugins"),
        help="Output directory (default: plugins/)",
    )
    parser.add_argument(
        "--no-interactive",
        action="store_true",
        help="Non-interactive mode (use provided arguments only)",
    )

    args = parser.parse_args()

    print("YAFT Plugin Generator")
    print("=" * 50)
    print()

    # Get plugin details
    if args.no_interactive:
        if not args.name:
            print("Error: --name is required in non-interactive mode")
            return 1
        name = args.name
        description = args.description or f"A plugin for {name}"
        author = args.author or "Unknown"
    else:
        name = args.name or get_user_input(
            "Plugin name",
            default="MyPlugin"
        )
        description = args.description or get_user_input(
            "Description",
            default=f"A plugin for {name}"
        )
        author = args.author or get_user_input(
            "Author",
            default="Unknown"
        )

    output_dir = args.output_dir

    # Create output directory if it doesn't exist
    output_dir.mkdir(parents=True, exist_ok=True)

    # Generate plugin
    print()
    print("Generating plugin...")
    try:
        output_file = create_plugin(name, description, author, output_dir)
        print(f"\nPlugin created successfully!")
        print(f"Location: {output_file}")
        print()
        print("Next steps:")
        print(f"1. Edit the plugin: {output_file}")
        print(f"2. Implement the _process() method with your logic")
        print("3. Test the plugin:")
        print(f"   python -m yaft.cli run {sanitize_name(name)}")
        print()
        print("For more information, see:")
        print("  - docs/PLUGIN_DEVELOPMENT.md")
        print("  - README.md")
        return 0

    except Exception as e:
        print(f"\nError creating plugin: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
