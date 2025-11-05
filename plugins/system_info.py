"""
System Info Plugin - Demonstrates system information gathering.

This plugin shows how to:
- Gather system information
- Use rich formatting
- Create interactive output
"""

import platform
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from rich.panel import Panel
from rich.table import Table

from yaft.core.api import CoreAPI
from yaft.core.plugin_base import PluginBase, PluginMetadata


class SystemInfoPlugin(PluginBase):
    """A plugin that displays system information."""

    def __init__(self, core_api: CoreAPI) -> None:
        """Initialize the plugin."""
        super().__init__(core_api)

    @property
    def metadata(self) -> PluginMetadata:
        """Return plugin metadata."""
        return PluginMetadata(
            name="SystemInfo",
            version="1.0.0",
            description="Displays system and Python environment information",
            author="YAFT Team",
            requires_core_version=">=0.1.0",
            dependencies=[],
            enabled=True,
        )

    def initialize(self) -> None:
        """Initialize the plugin."""
        self.core_api.log_info(f"Initializing {self.metadata.name} plugin")

    def execute(self, *args: Any, **kwargs: Any) -> dict[str, Any]:
        """Execute the plugin's main functionality."""
        self.core_api.print_info("Gathering system information...")

        # Collect system information
        system_info = self._collect_system_info()

        # Display information
        self._display_system_info(system_info)

        # Generate report
        report_path = self._generate_report(system_info)
        self.core_api.print_info(f"Report saved to: {report_path}")

        # Store in shared data
        self.core_api.set_shared_data("last_system_info", system_info)

        return system_info

    def _collect_system_info(self) -> dict[str, Any]:
        """Collect system information."""
        return {
            "platform": platform.system(),
            "platform_release": platform.release(),
            "platform_version": platform.version(),
            "architecture": platform.machine(),
            "processor": platform.processor(),
            "python_version": sys.version,
            "python_implementation": platform.python_implementation(),
            "python_compiler": platform.python_compiler(),
            "hostname": platform.node(),
            "current_directory": str(Path.cwd()),
            "timestamp": datetime.now().isoformat(),
        }

    def _display_system_info(self, info: dict[str, Any]) -> None:
        """Display system information in a formatted table."""
        # Create system table
        system_table = Table(title="System Information", show_header=False)
        system_table.add_column("Property", style="cyan", no_wrap=True)
        system_table.add_column("Value", style="white")

        system_table.add_row("Platform", info["platform"])
        system_table.add_row("Release", info["platform_release"])
        system_table.add_row("Architecture", info["architecture"])
        system_table.add_row("Processor", info["processor"])
        system_table.add_row("Hostname", info["hostname"])

        # Create Python table
        python_table = Table(title="Python Environment", show_header=False)
        python_table.add_column("Property", style="cyan", no_wrap=True)
        python_table.add_column("Value", style="white")

        python_table.add_row("Version", info["python_version"].split()[0])
        python_table.add_row("Implementation", info["python_implementation"])
        python_table.add_row("Compiler", info["python_compiler"])
        python_table.add_row("Executable", sys.executable)

        # Display tables
        self.core_api.console.print(system_table)
        self.core_api.console.print()
        self.core_api.console.print(python_table)

        # Display summary panel
        summary = (
            f"[bold]OS:[/bold] {info['platform']} {info['platform_release']}\n"
            f"[bold]Python:[/bold] {info['python_version'].split()[0]}\n"
            f"[bold]Timestamp:[/bold] {info['timestamp']}"
        )
        self.core_api.console.print()
        self.core_api.console.print(Panel(summary, title="Summary", border_style="green"))

    def _generate_report(self, info: dict[str, Any]) -> Path:
        """Generate markdown report for system information."""
        sections = [
            {
                "heading": "System Information",
                "content": {
                    "Platform": info["platform"],
                    "Release": info["platform_release"],
                    "Version": info["platform_version"],
                    "Architecture": info["architecture"],
                    "Processor": info["processor"],
                    "Hostname": info["hostname"],
                },
                "style": "table",
            },
            {
                "heading": "Python Environment",
                "content": {
                    "Version": info["python_version"].split()[0],
                    "Full Version": info["python_version"].replace("\n", " "),
                    "Implementation": info["python_implementation"],
                    "Compiler": info["python_compiler"],
                    "Executable": sys.executable,
                },
                "style": "table",
            },
            {
                "heading": "Environment Details",
                "content": {
                    "Current Directory": info["current_directory"],
                    "Timestamp": info["timestamp"],
                },
                "style": "table",
            },
            {
                "heading": "System Summary",
                "content": f"System information collected from {info['hostname']} running "
                          f"{info['platform']} {info['platform_release']} with "
                          f"Python {info['python_version'].split()[0]}.",
            },
        ]

        metadata = {
            "Platform": f"{info['platform']} {info['platform_release']}",
            "Python Version": info["python_version"].split()[0],
            "Hostname": info["hostname"],
            "Collection Time": info["timestamp"],
        }

        return self.core_api.generate_report(
            plugin_name="SystemInfo",
            title="System Information Report",
            sections=sections,
            metadata=metadata,
        )

    def cleanup(self) -> None:
        """Clean up plugin resources."""
        self.core_api.log_info(f"Cleaning up {self.metadata.name} plugin")
