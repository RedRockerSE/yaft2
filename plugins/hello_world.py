"""
Hello World Plugin - A simple example plugin.

This demonstrates the basic structure of a YAFT plugin.
"""

from pathlib import Path
from typing import Any

from yaft.core.api import CoreAPI
from yaft.core.plugin_base import PluginBase, PluginMetadata


class HelloWorldPlugin(PluginBase):
    """A simple hello world plugin demonstrating basic functionality."""

    def __init__(self, core_api: CoreAPI) -> None:
        """Initialize the plugin."""
        super().__init__(core_api)
        self._greeting_count = 0

    @property
    def metadata(self) -> PluginMetadata:
        """Return plugin metadata."""
        return PluginMetadata(
            name="HelloWorld",
            version="1.0.0",
            description="A simple greeting plugin that demonstrates basic plugin functionality",
            author="YAFT Team",
            requires_core_version=">=0.1.0",
            dependencies=[],
            enabled=True,
        )

    def initialize(self) -> None:
        """Initialize the plugin."""
        self.core_api.log_info(f"Initializing {self.metadata.name} plugin")
        self._greeting_count = 0

    def execute(self, *args: Any, **kwargs: Any) -> str:
        """Execute the plugin's main functionality."""
        self._greeting_count += 1

        # Get name from arguments or use default
        name = args[0] if args else kwargs.get("name", "World")

        # Use core API for colored output
        greeting = f"Hello, {name}!"
        self.core_api.print_success(greeting)

        # Store greeting count in shared data
        self.core_api.set_shared_data("hello_world_count", self._greeting_count)

        self.core_api.log_info(f"Total greetings: {self._greeting_count}")

        # Generate report
        report_path = self._generate_report(name)
        self.core_api.print_info(f"Report saved to: {report_path}")

        return f"Greeting #{self._greeting_count}: {greeting}"

    def _generate_report(self, name: str) -> Path:
        """Generate markdown report for greeting."""
        sections = [
            {
                "heading": "Greeting Details",
                "content": {
                    "Recipient": name,
                    "Greeting Number": self._greeting_count,
                    "Message": f"Hello, {name}!",
                },
                "style": "table",
            },
            {
                "heading": "Session Statistics",
                "content": f"This is greeting number {self._greeting_count} in the current session.",
            },
        ]

        metadata = {
            "Greeting Count": self._greeting_count,
            "Recipient": name,
        }

        return self.core_api.generate_report(
            plugin_name="HelloWorld",
            title="Hello World Greeting Report",
            sections=sections,
            metadata=metadata,
        )

    def cleanup(self) -> None:
        """Clean up plugin resources."""
        self.core_api.log_info(
            f"Cleaning up {self.metadata.name} plugin "
            f"(Total greetings: {self._greeting_count})"
        )
