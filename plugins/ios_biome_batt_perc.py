"""
iOS Biome Battery Percentage Plugin

Parses battery percentage entries from iOS Biome SEGB files.

**Dependencies:**
This plugin uses Core API methods that require:

1. blackboxprotobuf - For protobuf decoding (via core_api.decode_protobuf)
   Install: pip install blackboxprotobuf

2. ccl_segb - For SEGB file parsing (via core_api.read_segb_file)
   Location: src/yaft/ccl_segb/ (included in project)

The dependencies are managed through the Core API, so plugins don't need to
import them directly. The Core API will raise ImportError if dependencies
are missing.

**Installation:**
```bash
# Install optional blackboxprotobuf dependency
pip install blackboxprotobuf

# ccl_segb is included in the project at src/yaft/ccl_segb/
```

Ported from iLEAPP biome battery percentage artifact.
"""

from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from yaft.core.api import CoreAPI
from yaft.core.plugin_base import PluginBase, PluginMetadata


class iOSbiomeBattPercPlugin(PluginBase):
    """Extract battery percentage data from iOS Biome SEGB files."""

    def __init__(self, core_api: CoreAPI):
        super().__init__(core_api)
        self.extraction_type = "unknown"
        self.zip_prefix = ""

        # Data storage
        self.battery_data: list[dict[str, Any]] = []
        self.errors: list[str] = []

        # Dependency check flags
        self._has_blackboxprotobuf = False
        self._has_ccl_segb = False

    @property
    def metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name="iOSbiomeBattPercPlugin",
            version="1.0.0",
            description="Extract battery percentage data from iOS Biome SEGB files",
            author="YaFT (ported from iLEAPP - @JohnHyla)",
            target_os=["ios"],
        )

    def initialize(self) -> None:
        """Initialize plugin and check dependencies."""
        self.core_api.log_info(f"Initializing {self.metadata.name}")

        # Check for required dependencies by trying to use Core API methods
        try:
            # Test blackboxprotobuf availability
            self.core_api.decode_protobuf(b"\x08\x01")
            self._has_blackboxprotobuf = True
            self.core_api.log_debug("blackboxprotobuf is available")
        except ImportError:
            self.core_api.log_warning("blackboxprotobuf not installed")
            self._has_blackboxprotobuf = False
        except Exception:
            # Other errors are OK, we just want to check if it's installed
            self._has_blackboxprotobuf = True

        try:
            # Test ccl_segb availability (will fail gracefully if not available)
            # We can't actually test it without a file, so we check the import
            from yaft.ccl_segb import ccl_segb  # noqa: F401

            self._has_ccl_segb = True
            self.core_api.log_debug("ccl_segb is available")
        except ImportError:
            self.core_api.log_warning("ccl_segb not available")
            self._has_ccl_segb = False

    def execute(self, *args, **kwargs) -> dict[str, Any]:
        """
        Extract battery percentage data from Biome SEGB files.

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

        # Find Biome battery percentage files
        self.core_api.print_info("Searching for Biome battery percentage files...")
        pattern = "*/biome/streams/restricted/_DKEvent.Device.BatteryPercentage/local/*"
        biome_files = self.core_api.find_files_in_zip(pattern)

        if not biome_files:
            self.core_api.print_warning("No Biome battery percentage files found")
            return {
                "success": True,
                "message": "No Biome battery percentage files found",
            }

        self.core_api.print_info(f"Found {len(biome_files)} Biome file(s)")

        # Extract and parse files
        self._extract_battery_data(biome_files)

        # Generate report
        report_path = self._generate_report()

        # Export to JSON
        json_path = self._export_to_json()

        # Export to CSV
        csv_path = self._export_to_csv()

        return {
            "success": True,
            "report_path": str(report_path),
            "json_path": str(json_path),
            "csv_path": str(csv_path),
            "battery_records": len(self.battery_data),
            "errors": self.errors,
        }

    def _extract_battery_data(self, biome_files: list[str]) -> None:
        """Extract battery data from SEGB files."""
        try:
            from yaft.ccl_segb.ccl_segb_common import EntryState

            # Protobuf type definition from original iLEAPP code
            protobuf_types = {
                "1": {
                    "type": "message",
                    "message_typedef": {
                        "1": {"type": "str", "name": ""},
                        "2": {
                            "type": "message",
                            "message_typedef": {
                                "1": {"type": "int", "name": ""},
                                "2": {"type": "int", "name": ""},
                            },
                            "name": "",
                        },
                    },
                    "name": "",
                },
                "2": {"type": "double", "name": ""},
                "3": {"type": "double", "name": ""},
                "4": {
                    "type": "message",
                    "message_typedef": {
                        "1": {
                            "type": "message",
                            "message_typedef": {
                                "1": {"type": "int", "name": ""},
                                "2": {"type": "int", "name": ""},
                            },
                            "name": "",
                        },
                        "5": {"type": "double", "name": ""},
                    },
                    "name": "",
                },
                "5": {"type": "str", "name": ""},
                "8": {"type": "double", "name": ""},
                "10": {"type": "int", "name": ""},
            }

            # Extract files to temporary location for processing
            temp_dir = self.core_api.get_case_output_dir("temp_biome")
            temp_dir.mkdir(parents=True, exist_ok=True)

            for biome_file_path in biome_files:
                try:
                    filename = Path(biome_file_path).name

                    # Skip hidden files and tombstones
                    if filename.startswith(".") or "tombstone" in biome_file_path.lower():
                        continue

                    # Extract file from ZIP
                    self.core_api.extract_zip_file(biome_file_path, temp_dir)

                    # Find extracted file
                    extracted_file = None
                    for file in temp_dir.rglob(filename):
                        extracted_file = file
                        break

                    if not extracted_file or not extracted_file.exists():
                        self.core_api.log_warning(f"Could not extract: {biome_file_path}")
                        continue

                    # Parse SEGB file using Core API
                    for record in self.core_api.read_segb_file(str(extracted_file)):
                        segb_timestamp = record.timestamp1.replace(tzinfo=timezone.utc)

                        if record.state == EntryState.Written:
                            try:
                                # Decode protobuf message using Core API
                                protostuff, _ = self.core_api.decode_protobuf(
                                    record.data, protobuf_types
                                )

                                # Extract data fields
                                activity = protostuff.get("1", {}).get("1", "")
                                time_start = self._convert_webkit_timestamp(protostuff.get("2", 0))
                                time_end = self._convert_webkit_timestamp(protostuff.get("3", 0))
                                time_write = self._convert_webkit_timestamp(protostuff.get("8", 0))
                                percent = protostuff.get("4", {}).get("5", 0)
                                action_guid = protostuff.get("5", "")

                                self.battery_data.append(
                                    {
                                        "segb_timestamp": segb_timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                                        "time_start": time_start,
                                        "time_end": time_end,
                                        "time_write": time_write,
                                        "segb_state": record.state.name,
                                        "activity": activity,
                                        "battery_percentage": round(percent, 2),
                                        "action_guid": action_guid,
                                        "filename": filename,
                                        "offset": record.data_start_offset,
                                    }
                                )

                            except Exception as e:
                                self.core_api.log_error(f"Error decoding record: {e}")
                                continue

                        elif record.state == EntryState.Deleted:
                            self.battery_data.append(
                                {
                                    "segb_timestamp": segb_timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                                    "time_start": "",
                                    "time_end": "",
                                    "time_write": "",
                                    "segb_state": record.state.name,
                                    "activity": "",
                                    "battery_percentage": 0,
                                    "action_guid": "",
                                    "filename": filename,
                                    "offset": record.data_start_offset,
                                }
                            )

                except Exception as e:
                    self.core_api.log_error(f"Error processing {biome_file_path}: {e}")
                    self.errors.append(f"Error processing {biome_file_path}: {str(e)}")
                    continue

            # Clean up temp directory
            import shutil

            if temp_dir.exists():
                shutil.rmtree(temp_dir, ignore_errors=True)

            self.core_api.print_success(f"Extracted {len(self.battery_data)} battery records")

        except Exception as e:
            self.core_api.log_error(f"Error extracting battery data: {e}")
            self.errors.append(f"Battery data extraction error: {str(e)}")

    def _convert_webkit_timestamp(self, webkit_ts: float) -> str:
        """
        Convert WebKit timestamp to ISO format string.
        WebKit timestamps are seconds since 2001-01-01 00:00:00 UTC.
        """
        if not webkit_ts or webkit_ts == 0:
            return ""
        try:
            # WebKit reference date: January 1, 2001, 00:00:00 UTC
            reference_date = datetime(2001, 1, 1, tzinfo=timezone.utc)
            dt = reference_date + timedelta(seconds=webkit_ts)
            return dt.strftime("%Y-%m-%d %H:%M:%S")
        except (ValueError, OverflowError, OSError):
            return str(webkit_ts)

    def _generate_report(self) -> Path:
        """Generate markdown report."""
        sections = []

        # Summary
        total_records = len(self.battery_data)
        written_records = len([r for r in self.battery_data if r["segb_state"] == "Written"])
        deleted_records = len([r for r in self.battery_data if r["segb_state"] == "Deleted"])

        summary_content = f"""
Extracted battery percentage data from iOS Biome SEGB files.

**Total Records:** {total_records:,}
**Written Records:** {written_records:,}
**Deleted Records:** {deleted_records:,}

The iOS Biome system stores battery percentage events in SEGB (Segmented Binary) files.
These files contain timestamped battery level information that can provide insights into
device usage patterns and charging behavior.

**Note:** Full data exported to CSV and JSON files for detailed analysis.
"""

        sections.append(
            {
                "heading": "Summary",
                "content": summary_content.strip(),
                "style": "text",
            }
        )

        # Statistics
        if self.battery_data:
            # Calculate battery statistics for written records
            written_data = [r for r in self.battery_data if r["segb_state"] == "Written"]
            if written_data:
                percentages = [r["battery_percentage"] for r in written_data if r["battery_percentage"] > 0]
                if percentages:
                    avg_battery = sum(percentages) / len(percentages)
                    min_battery = min(percentages)
                    max_battery = max(percentages)

                    stats = {
                        "Total Records": f"{total_records:,}",
                        "Written Records": f"{written_records:,}",
                        "Deleted Records": f"{deleted_records:,}",
                        "Average Battery Level": f"{avg_battery:.1f}%",
                        "Minimum Battery Level": f"{min_battery:.1f}%",
                        "Maximum Battery Level": f"{max_battery:.1f}%",
                    }

                    sections.append(
                        {
                            "heading": "Statistics",
                            "content": stats,
                            "style": "table",
                        }
                    )

        # Sample data (first 20 written records)
        if self.battery_data:
            written_sample = [r for r in self.battery_data if r["segb_state"] == "Written"][:20]
            if written_sample:
                self._add_section_with_sample(sections, "Battery Data (Sample)", written_sample)

        # Errors
        if self.errors:
            sections.append(
                {
                    "heading": "Errors",
                    "content": self.errors,
                    "style": "list",
                }
            )

        metadata = {
            "Extraction Type": self.extraction_type,
            "Total Records": f"{total_records:,}",
        }

        report_path = self.core_api.generate_report(
            plugin_name=self.metadata.name,
            title="iOS Biome Battery Percentage Analysis",
            sections=sections,
            metadata=metadata,
        )

        self.core_api.print_success(f"Report generated: {report_path}")
        return report_path

    def _add_section_with_sample(self, sections: list, heading: str, data: list[dict]) -> None:
        """Add a section with sample data table."""
        if not data:
            return

        # Convert list of dicts to table format
        table = {}
        for key in data[0].keys():
            # Convert key to title case for display
            display_key = key.replace("_", " ").title()
            table[display_key] = [str(item.get(key, "")) for item in data]

        sections.append(
            {
                "heading": heading,
                "content": table,
                "style": "table",
            }
        )

    def _export_to_json(self) -> Path:
        """Export all data to JSON."""
        output_dir = self.core_api.get_case_output_dir("biome_battery_data")
        output_dir.mkdir(parents=True, exist_ok=True)
        json_path = output_dir / "biome_battery_percentage.json"

        export_data = {
            "battery_data": self.battery_data,
            "summary": {
                "total_records": len(self.battery_data),
                "written_records": len([r for r in self.battery_data if r["segb_state"] == "Written"]),
                "deleted_records": len([r for r in self.battery_data if r["segb_state"] == "Deleted"]),
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

    def _export_to_csv(self) -> Path:
        """Export data to CSV."""
        output_dir = self.core_api.get_case_output_dir("biome_battery_data")
        output_dir.mkdir(parents=True, exist_ok=True)
        csv_path = output_dir / "biome_battery_percentage.csv"

        if self.battery_data:
            self.core_api.export_plugin_data_to_csv(
                csv_path,
                self.metadata.name,
                self.metadata.version,
                self.battery_data,
                self.extraction_type,
            )

            self.core_api.print_success(f"CSV export: {csv_path}")

        return csv_path

    def cleanup(self) -> None:
        """Clean up plugin resources."""
        self.core_api.log_info(f"Cleaning up {self.metadata.name}")
