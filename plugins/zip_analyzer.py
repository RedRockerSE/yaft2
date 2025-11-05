"""
ZIP Analyzer Plugin - Forensic analysis of ZIP archives.

This plugin demonstrates how to use YaFT's ZIP file handling capabilities
for forensic analysis tasks.
"""

from pathlib import Path
from typing import Any

from rich.table import Table

from yaft.core.api import CoreAPI
from yaft.core.plugin_base import PluginBase, PluginMetadata


class ZipAnalyzerPlugin(PluginBase):
    """
    Forensic analysis plugin for ZIP archives.

    Provides comprehensive analysis of ZIP file contents including:
    - File listing with metadata
    - Suspicious file detection
    - File extraction capabilities
    - Content analysis
    """

    def __init__(self, core_api: CoreAPI) -> None:
        super().__init__(core_api)
        self.suspicious_extensions = {
            ".exe", ".dll", ".bat", ".cmd", ".ps1", ".vbs", ".js",
            ".jar", ".sh", ".bin", ".scr", ".com", ".pif"
        }
        self.analysis_results: dict[str, Any] = {}

    @property
    def metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name="ZipAnalyzerPlugin",
            version="1.0.0",
            description="Forensic analysis of ZIP archives - file listing, suspicious file detection, extraction",
            author="YaFT Development Team",
            requires_core_version=">=0.1.0",
            dependencies=[],
            enabled=True,
        )

    def initialize(self) -> None:
        """Initialize the ZIP analyzer plugin."""
        self.core_api.log_info(f"Initializing {self.metadata.name}")
        self.analysis_results = {
            "total_files": 0,
            "total_size": 0,
            "suspicious_files": [],
            "file_types": {},
        }

    def execute(self, *args: Any, **kwargs: Any) -> Any:
        """
        Execute ZIP analysis.

        Returns:
            dict: Analysis results
        """
        # Check if ZIP file is loaded
        current_zip = self.core_api.get_current_zip()
        if not current_zip:
            self.core_api.print_error("No ZIP file loaded. Use --zip option to specify a ZIP file.")
            return None

        self.core_api.print_success(f"Analyzing ZIP file: {current_zip.name}")
        self.core_api.console.print()

        # Display ZIP contents
        self.core_api.display_zip_contents()
        self.core_api.console.print()

        # Perform forensic analysis
        self._analyze_files()

        # Display suspicious files
        if self.analysis_results["suspicious_files"]:
            self._display_suspicious_files()
        else:
            self.core_api.print_success("No suspicious files detected")

        # Display file type statistics
        self._display_file_types()

        # Generate markdown report
        report_path = self._generate_markdown_report()
        self.core_api.print_success(f"Markdown report saved to: {report_path}")

        # Ask if user wants to extract files
        if self.core_api.confirm("Do you want to extract the ZIP contents for further analysis?"):
            self._extract_files()

        return self.analysis_results

    def _analyze_files(self) -> None:
        """Analyze files in the ZIP archive for suspicious content."""
        self.core_api.log_info("Performing forensic analysis...")

        files = self.core_api.list_zip_contents()

        for file_info in files:
            if file_info.is_dir():
                continue

            self.analysis_results["total_files"] += 1
            self.analysis_results["total_size"] += file_info.file_size

            # Track file types
            extension = Path(file_info.filename).suffix.lower()
            if extension:
                self.analysis_results["file_types"][extension] = \
                    self.analysis_results["file_types"].get(extension, 0) + 1

            # Check for suspicious files
            if extension in self.suspicious_extensions:
                self.analysis_results["suspicious_files"].append({
                    "filename": file_info.filename,
                    "size": file_info.file_size,
                    "extension": extension,
                    "compressed_size": file_info.compress_size,
                })

            # Check for hidden files (starting with dot on Unix)
            if Path(file_info.filename).name.startswith("."):
                self.analysis_results["suspicious_files"].append({
                    "filename": file_info.filename,
                    "size": file_info.file_size,
                    "extension": extension or "none",
                    "compressed_size": file_info.compress_size,
                    "reason": "Hidden file",
                })

    def _display_suspicious_files(self) -> None:
        """Display table of suspicious files found."""
        table = Table(title="[bold red]Suspicious Files Detected[/bold red]")
        table.add_column("Filename", style="red", no_wrap=False)
        table.add_column("Extension", style="yellow")
        table.add_column("Size", justify="right", style="cyan")
        table.add_column("Reason", style="magenta")

        for sus_file in self.analysis_results["suspicious_files"]:
            reason = sus_file.get("reason", "Potentially dangerous extension")
            table.add_row(
                sus_file["filename"],
                sus_file["extension"],
                self.core_api._format_size(sus_file["size"]),
                reason,
            )

        self.core_api.console.print()
        self.core_api.console.print(table)
        self.core_api.console.print()

    def _display_file_types(self) -> None:
        """Display statistics about file types in the archive."""
        if not self.analysis_results["file_types"]:
            return

        table = Table(title="File Type Distribution")
        table.add_column("Extension", style="cyan")
        table.add_column("Count", justify="right", style="green")
        table.add_column("Percentage", justify="right", style="yellow")

        total = self.analysis_results["total_files"]

        # Sort by count (descending)
        sorted_types = sorted(
            self.analysis_results["file_types"].items(),
            key=lambda x: x[1],
            reverse=True
        )

        for extension, count in sorted_types:
            percentage = (count / total) * 100
            table.add_row(
                extension or "[no extension]",
                str(count),
                f"{percentage:.1f}%",
            )

        self.core_api.console.print()
        self.core_api.console.print(table)
        self.core_api.console.print()

    def _generate_markdown_report(self) -> Path:
        """Generate markdown report using CoreAPI report method."""
        current_zip = self.core_api.get_current_zip()

        # Prepare metadata
        metadata = {
            "Total Files": self.analysis_results["total_files"],
            "Total Size": self.core_api._format_size(self.analysis_results["total_size"]),
            "Suspicious Files Found": len(self.analysis_results["suspicious_files"]),
        }

        # Prepare sections
        sections = []

        # Executive Summary
        summary_text = (
            f"Analyzed ZIP archive containing {self.analysis_results['total_files']} files "
            f"with a total size of {self.core_api._format_size(self.analysis_results['total_size'])}. "
        )
        if self.analysis_results["suspicious_files"]:
            summary_text += (
                f"**{len(self.analysis_results['suspicious_files'])} suspicious files detected** "
                f"that require further investigation."
            )
        else:
            summary_text += "No suspicious files detected during analysis."

        sections.append({
            "heading": "Executive Summary",
            "content": summary_text,
            "level": 2,
        })

        # Suspicious Files section
        if self.analysis_results["suspicious_files"]:
            suspicious_table = []
            for sus_file in self.analysis_results["suspicious_files"]:
                suspicious_table.append({
                    "Filename": sus_file["filename"],
                    "Extension": sus_file["extension"],
                    "Size": self.core_api._format_size(sus_file["size"]),
                    "Reason": sus_file.get("reason", "Potentially dangerous extension"),
                })

            sections.append({
                "heading": "⚠️ Suspicious Files",
                "content": suspicious_table,
                "level": 2,
                "style": "table",
            })
        else:
            sections.append({
                "heading": "Suspicious Files",
                "content": "✅ No suspicious files detected",
                "level": 2,
            })

        # File Type Distribution
        file_types_table = []
        sorted_types = sorted(
            self.analysis_results["file_types"].items(),
            key=lambda x: x[1],
            reverse=True
        )
        for extension, count in sorted_types:
            percentage = (count / self.analysis_results['total_files']) * 100
            file_types_table.append({
                "Extension": extension or "[no extension]",
                "Count": count,
                "Percentage": f"{percentage:.1f}%",
            })

        sections.append({
            "heading": "File Type Distribution",
            "content": file_types_table,
            "level": 2,
            "style": "table",
        })

        # Recommendations
        recommendations = []
        if self.analysis_results["suspicious_files"]:
            recommendations.append("Examine all suspicious files in a sandboxed environment")
            recommendations.append("Verify digital signatures of executable files")
            recommendations.append("Scan suspicious files with antivirus software")
            recommendations.append("Check file hashes against known malware databases")
        else:
            recommendations.append("Archive appears clean, but manual review is recommended")
            recommendations.append("Verify file integrity if archive is from untrusted source")

        sections.append({
            "heading": "Recommendations",
            "content": recommendations,
            "level": 2,
            "style": "list",
        })

        # Generate report
        report_path = self.core_api.generate_report(
            plugin_name="ZipAnalyzerPlugin",
            title=f"ZIP Forensic Analysis Report: {current_zip.name if current_zip else 'Unknown'}",
            sections=sections,
            metadata=metadata,
        )

        return report_path

    def _extract_files(self) -> None:
        """Extract ZIP contents to output directory."""
        current_zip = self.core_api.get_current_zip()
        if not current_zip:
            return

        # Create output directory
        output_dir = Path.cwd() / "yaft_output" / current_zip.stem
        output_dir.mkdir(parents=True, exist_ok=True)

        try:
            extracted_path = self.core_api.extract_all_zip(output_dir)
            self.core_api.print_success(f"Files extracted to: {extracted_path}")

        except Exception as e:
            self.core_api.print_error(f"Failed to extract files: {e}")

    def cleanup(self) -> None:
        """Clean up resources."""
        self.core_api.log_info(f"Cleaning up {self.metadata.name}")
        self.analysis_results.clear()
