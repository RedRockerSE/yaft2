"""
iOS WAL & Journal Strings Extractor Plugin

Extracts ASCII strings from SQLite Write-Ahead Log (WAL) and journal files.
These files may contain remnants of deleted data, providing valuable forensic evidence.

Ported from iLEAPP walStrings artifact.
"""

from pathlib import Path
import re
import string
from typing import Any

from yaft.core.api import CoreAPI
from yaft.core.plugin_base import PluginBase, PluginMetadata


class iOSwalStringsPlugin(PluginBase):
    """Extract ASCII strings from SQLite WAL and journal files."""

    def __init__(self, core_api: CoreAPI):
        super().__init__(core_api)
        self.extraction_type = "unknown"
        self.zip_prefix = ""
        self.extracted_strings: list[dict[str, Any]] = []
        self.errors: list[str] = []

    @property
    def metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name="iOSwalStringsPlugin",
            version="1.0.0",
            description="Extract ASCII strings from SQLite WAL and journal files",
            author="YaFT (ported from iLEAPP)",
            target_os=["ios"],
        )

    def initialize(self) -> None:
        """Initialize plugin resources."""
        self.core_api.log_info(f"Initializing {self.metadata.name}")

    def execute(self, *args, **kwargs) -> dict[str, Any]:
        """
        Extract ASCII strings from SQLite WAL and journal files.

        Returns:
            Dictionary with execution results
        """
        # Check ZIP file is loaded
        if not self.core_api.get_current_zip():
            self.core_api.print_error("No ZIP file loaded")
            return {"success": False, "error": "No ZIP file loaded"}

        # Detect ZIP format
        self.extraction_type, self.zip_prefix = self.core_api.detect_zip_format()
        self.core_api.print_info(f"Detected extraction format: {self.extraction_type}")

        # Find WAL and journal files
        self.core_api.print_info("Searching for WAL and journal files...")
        wal_files = self.core_api.find_files_in_zip("*-wal")
        journal_files = self.core_api.find_files_in_zip("*-journal")

        all_files = wal_files + journal_files

        if not all_files:
            self.core_api.print_warning("No WAL or journal files found in ZIP archive")
            return {
                "success": True,
                "message": "No WAL or journal files found",
                "files_processed": 0,
            }

        self.core_api.print_info(f"Found {len(wal_files)} WAL files and {len(journal_files)} journal files")

        # Process files
        self._process_files(all_files)

        # Generate report
        report_path = self._generate_report()

        # Export to JSON
        json_path = self._export_to_json()

        return {
            "success": True,
            "report_path": str(report_path),
            "json_path": str(json_path),
            "files_processed": len(self.extracted_strings),
            "total_unique_strings": sum(
                item["unique_strings_count"] for item in self.extracted_strings
            ),
            "errors": self.errors,
        }

    def _process_files(self, file_paths: list[str]) -> None:
        """
        Process WAL and journal files to extract ASCII strings.

        Args:
            file_paths: List of file paths in ZIP archive
        """
        # Create output directory for text files
        output_dir = self.core_api.get_case_output_dir("wal_journal_strings")
        output_dir.mkdir(parents=True, exist_ok=True)

        # Regex for ASCII printable characters (minimum 4 characters)
        # Same pattern as iLEAPP walStrings
        printable_chars_for_re = string.printable.replace('\\', '\\\\').replace('[', '\\[').replace(']', '\\]')
        ascii_chars_re = re.compile(f'[{printable_chars_for_re}]' + '{4,}')

        for idx, file_path in enumerate(file_paths, start=1):
            try:
                # Read file from ZIP
                file_data = self.core_api.read_zip_file(file_path)

                if not file_data:
                    self.core_api.print_warning(f"Empty file: {file_path}")
                    continue

                # Extract strings
                unique_strings = set()
                string_list = []

                # Decode with errors='ignore' to handle binary data (same as original)
                try:
                    text_data = file_data.decode('utf-8', errors='ignore')
                except Exception as e:
                    self.core_api.log_error(f"Failed to decode {file_path}: {e}")
                    self.errors.append(f"Decode error for {file_path}: {str(e)}")
                    continue

                # Find all ASCII strings (minimum 4 characters)
                for match in ascii_chars_re.findall(text_data):
                    if match not in unique_strings:
                        string_list.append(match)
                        unique_strings.add(match)

                if unique_strings:
                    # Save strings to text file
                    file_name = Path(file_path).name
                    output_filename = f"{idx}_{file_name}.txt"
                    output_path = output_dir / output_filename

                    with open(output_path, 'w', encoding='utf-8') as f:
                        f.write('\n'.join(string_list) + '\n')

                    # Store metadata
                    self.extracted_strings.append({
                        "file_path": file_path,
                        "output_file": str(output_path),
                        "output_filename": output_filename,
                        "unique_strings_count": len(unique_strings),
                        "file_size": len(file_data),
                    })

                    self.core_api.print_success(
                        f"Extracted {len(unique_strings)} unique strings from {file_name}"
                    )
                else:
                    self.core_api.print_warning(f"No strings found in {file_path}")

            except KeyError:
                self.core_api.log_error(f"File not found in ZIP: {file_path}")
                self.errors.append(f"File not found: {file_path}")
            except Exception as e:
                self.core_api.log_error(f"Error processing {file_path}: {e}")
                self.errors.append(f"Error processing {file_path}: {str(e)}")

    def _generate_report(self) -> Path:
        """
        Generate markdown report.

        Returns:
            Path to generated report
        """
        sections = []

        # Summary section
        total_files = len(self.extracted_strings)
        total_strings = sum(item["unique_strings_count"] for item in self.extracted_strings)

        summary_content = f"""
Extracted ASCII strings from SQLite WAL and journal files.

**Files Processed:** {total_files}
**Total Unique Strings:** {total_strings:,}

ASCII strings (minimum 4 characters) were extracted from SQLite Write-Ahead Log (WAL)
and journal files. These files may contain remnants of deleted data, providing valuable
forensic evidence.

**Note:** Extracted strings are saved as individual text files in the output directory
for detailed review.
"""

        sections.append({
            "heading": "Summary",
            "content": summary_content.strip(),
            "style": "text",
        })

        # Extracted Files section
        if self.extracted_strings:
            files_table = {
                "File Path": [],
                "Output File": [],
                "Unique Strings": [],
                "File Size (bytes)": [],
            }

            for item in self.extracted_strings:
                files_table["File Path"].append(item["file_path"])
                files_table["Output File"].append(item["output_filename"])
                files_table["Unique Strings"].append(str(item["unique_strings_count"]))
                files_table["File Size (bytes)"].append(f"{item['file_size']:,}")

            sections.append({
                "heading": "Extracted Files",
                "content": files_table,
                "style": "table",
            })

        # Errors section
        if self.errors:
            sections.append({
                "heading": "Errors",
                "content": self.errors,
                "style": "list",
            })

        # Additional metadata
        metadata = {
            "Extraction Type": self.extraction_type,
            "Files Processed": str(total_files),
            "Total Strings Extracted": f"{total_strings:,}",
        }

        report_path = self.core_api.generate_report(
            plugin_name=self.metadata.name,
            title="iOS SQLite WAL & Journal Strings Extraction",
            sections=sections,
            metadata=metadata,
        )

        self.core_api.print_success(f"Report generated: {report_path}")
        return report_path

    def _export_to_json(self) -> Path:
        """
        Export extracted data to JSON.

        Returns:
            Path to JSON file
        """
        output_dir = self.core_api.get_case_output_dir("wal_journal_strings")
        json_path = output_dir / "extracted_strings_metadata.json"

        export_data = {
            "extracted_files": self.extracted_strings,
            "summary": {
                "total_files_processed": len(self.extracted_strings),
                "total_unique_strings": sum(
                    item["unique_strings_count"] for item in self.extracted_strings
                ),
            },
            "errors": self.errors,
        }

        self.core_api.export_plugin_data_to_json(
            json_path,
            self.metadata.name,
            self.metadata.version,
            export_data,
            self.extraction_type,
        )

        self.core_api.print_success(f"JSON export: {json_path}")
        return json_path

    def cleanup(self) -> None:
        """Clean up plugin resources."""
        self.core_api.log_info(f"Cleaning up {self.metadata.name}")
