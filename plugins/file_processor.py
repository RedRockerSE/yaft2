"""
File Processor Plugin - Demonstrates file operations using Core API.

This plugin shows how to:
- Use core API utilities
- Handle file operations
- Process user input
- Generate formatted output
"""

from pathlib import Path
from typing import Any

from rich.table import Table

from yaft.core.api import CoreAPI
from yaft.core.plugin_base import PluginBase, PluginMetadata


class FileProcessorPlugin(PluginBase):
    """A plugin that demonstrates file processing capabilities."""

    def __init__(self, core_api: CoreAPI) -> None:
        """Initialize the plugin."""
        super().__init__(core_api)
        self._processed_files: list[str] = []

    @property
    def metadata(self) -> PluginMetadata:
        """Return plugin metadata."""
        return PluginMetadata(
            name="FileProcessor",
            version="1.0.0",
            description="Processes text files and displays statistics",
            author="YAFT Team",
            requires_core_version=">=0.1.0",
            dependencies=[],
            enabled=True,
        )

    def initialize(self) -> None:
        """Initialize the plugin."""
        self.core_api.log_info(f"Initializing {self.metadata.name} plugin")
        self._processed_files = []

    def execute(self, *args: Any, **kwargs: Any) -> dict[str, Any]:
        """Execute the plugin's main functionality."""
        # Get file path from arguments or ask user
        if args:
            filepath = Path(args[0])
        else:
            filepath_str = self.core_api.get_user_input("Enter file path to process")
            filepath = Path(filepath_str)

        if not filepath.exists():
            self.core_api.print_error(f"File not found: {filepath}")
            return {"success": False, "error": "File not found"}

        if not filepath.is_file():
            self.core_api.print_error(f"Not a file: {filepath}")
            return {"success": False, "error": "Not a file"}

        try:
            # Read file using core API
            self.core_api.print_info(f"Processing file: {filepath.name}")
            content = self.core_api.read_file(filepath)

            # Calculate statistics
            stats = self._calculate_statistics(content)

            # Display results
            self._display_results(filepath, stats)

            # Generate report
            report_path = self._generate_report(filepath, stats)
            self.core_api.print_info(f"Report saved to: {report_path}")

            # Store in processed files list
            self._processed_files.append(str(filepath))

            # Store stats in shared data
            self.core_api.set_shared_data(f"file_stats_{filepath.name}", stats)

            return {"success": True, "filepath": str(filepath), "stats": stats}

        except Exception as e:
            self.core_api.print_error(f"Failed to process file: {e}")
            return {"success": False, "error": str(e)}

    def _calculate_statistics(self, content: str) -> dict[str, int]:
        """Calculate file statistics."""
        lines = content.split("\n")
        words = content.split()

        return {
            "characters": len(content),
            "lines": len(lines),
            "words": len(words),
            "non_empty_lines": len([line for line in lines if line.strip()]),
        }

    def _display_results(self, filepath: Path, stats: dict[str, int]) -> None:
        """Display processing results in a formatted table."""
        table = Table(title=f"File Statistics: {filepath.name}")

        table.add_column("Metric", style="cyan", no_wrap=True)
        table.add_column("Value", style="magenta", justify="right")

        table.add_row("Total Characters", str(stats["characters"]))
        table.add_row("Total Lines", str(stats["lines"]))
        table.add_row("Non-Empty Lines", str(stats["non_empty_lines"]))
        table.add_row("Total Words", str(stats["words"]))

        self.core_api.console.print(table)
        self.core_api.print_success("File processed successfully")

    def _generate_report(self, filepath: Path, stats: dict[str, int]) -> Path:
        """Generate markdown report for file processing."""
        sections = [
            {
                "heading": "File Information",
                "content": {
                    "Filename": filepath.name,
                    "Full Path": str(filepath.absolute()),
                    "File Size": f"{filepath.stat().st_size} bytes",
                },
                "style": "table",
            },
            {
                "heading": "Text Statistics",
                "content": {
                    "Total Characters": stats["characters"],
                    "Total Lines": stats["lines"],
                    "Non-Empty Lines": stats["non_empty_lines"],
                    "Total Words": stats["words"],
                    "Average Words per Line": round(stats["words"] / stats["lines"], 2) if stats["lines"] > 0 else 0,
                },
                "style": "table",
            },
            {
                "heading": "Analysis Summary",
                "content": f"Processed text file with {stats['lines']} lines and {stats['words']} words. "
                          f"The file contains {stats['non_empty_lines']} non-empty lines out of {stats['lines']} total lines.",
            },
        ]

        metadata = {
            "Filename": filepath.name,
            "Lines": stats["lines"],
            "Words": stats["words"],
        }

        return self.core_api.generate_report(
            plugin_name="FileProcessor",
            title=f"File Processing Report: {filepath.name}",
            sections=sections,
            metadata=metadata,
        )

    def cleanup(self) -> None:
        """Clean up plugin resources."""
        self.core_api.log_info(
            f"Cleaning up {self.metadata.name} plugin "
            f"(Processed {len(self._processed_files)} files)"
        )
