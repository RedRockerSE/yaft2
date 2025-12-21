"""
iOS Biome WiFi Devices Plugin

Parses device WiFi connection/disconnection entries from iOS Biome SEGB files.
Extracts WiFi network SSIDs and connection status from Device.Wireless.WiFi biomes.

```

Ported from iLEAPP biome WiFi device artifact by @JohnHyla.
"""

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from yaft.core.api import CoreAPI
from yaft.core.plugin_base import PluginBase, PluginMetadata


class iOSbiomeDevWifiPlugin(PluginBase):
    """Extract WiFi device connection/disconnection data from iOS Biome SEGB files."""

    def __init__(self, core_api: CoreAPI):
        super().__init__(core_api)
        self.extraction_type = "unknown"
        self.zip_prefix = ""

        # Data storage
        self.wifi_data: list[dict[str, Any]] = []
        self.errors: list[str] = []

        # Dependency check flags
        self._has_blackboxprotobuf = False
        self._has_ccl_segb = False

    @property
    def metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name="iOSbiomeDevWifiPlugin",
            version="1.0.0",
            description="Parse device WiFi connection/disconnection entries from iOS Biome SEGB files",
            author="YaFT (ported from iLEAPP - @JohnHyla)",
            target_os=["ios"],
        )

    def initialize(self) -> None:
        """Initialize plugin and check dependencies."""
        self.core_api.log_info(f"Initializing {self.metadata.name}")

        

    def execute(self, *args, **kwargs) -> dict[str, Any]:
        """
        Extract WiFi device connection/disconnection data from Biome SEGB files.

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

        # Find Biome WiFi files
        self.core_api.print_info("Searching for Biome WiFi device files...")
        pattern = "*/biome/streams/restricted/Device.Wireless.WiFi/local/*"
        wifi_files = self.core_api.find_files_in_zip(pattern)

        if not wifi_files:
            self.core_api.print_warning("No Biome WiFi device files found")
            return {
                "success": True,
                "message": "No Biome WiFi device files found",
            }

        self.core_api.print_info(f"Found {len(wifi_files)} WiFi Biome file(s)")

        # Extract and parse files
        self._extract_wifi_data(wifi_files)

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
            "wifi_records": len(self.wifi_data),
            "errors": self.errors,
        }

    def _extract_wifi_data(self, wifi_files: list[str]) -> None:
        """Extract WiFi connection/disconnection data from SEGB files."""
        try:
            from yaft.ccl_segb.ccl_segb_common import EntryState

            # Protobuf type definition from original iLEAPP code
            protobuf_types = {
                "1": {"type": "str", "name": "SSID"},
                "2": {"type": "int", "name": "Connect"},
            }

            # Extract files to temporary location for processing
            temp_dir = self.core_api.get_case_output_dir("temp_wifi_biome")
            temp_dir.mkdir(parents=True, exist_ok=True)

            for wifi_file_path in wifi_files:
                try:
                    filename = Path(wifi_file_path).name

                    # Skip hidden files and tombstones (same as original iLEAPP logic)
                    if filename.startswith(".") or "tombstone" in wifi_file_path.lower():
                        continue

                    # Extract file from ZIP
                    self.core_api.extract_zip_file(wifi_file_path, temp_dir)

                    # Find extracted file
                    extracted_file = None
                    for file in temp_dir.rglob(filename):
                        extracted_file = file
                        break

                    if not extracted_file or not extracted_file.exists():
                        self.core_api.log_warning(f"Could not extract: {wifi_file_path}")
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
                                ssid = protostuff.get("SSID", "")
                                connect_value = protostuff.get("Connect", 0)
                                status = "Connected" if connect_value == 1 else "Disconnected"

                                self.wifi_data.append(
                                    {
                                        "segb_timestamp": segb_timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                                        "segb_state": record.state.name,
                                        "ssid": ssid,
                                        "status": status,
                                        "filename": filename,
                                        "offset": record.data_start_offset,
                                    }
                                )

                            except Exception as e:
                                self.core_api.log_error(f"Error decoding record: {e}")
                                continue

                        elif record.state == EntryState.Deleted:
                            self.wifi_data.append(
                                {
                                    "segb_timestamp": segb_timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                                    "segb_state": record.state.name,
                                    "ssid": "",
                                    "status": "",
                                    "filename": filename,
                                    "offset": record.data_start_offset,
                                }
                            )

                except Exception as e:
                    self.core_api.log_error(f"Error processing {wifi_file_path}: {e}")
                    self.errors.append(f"Error processing {wifi_file_path}: {str(e)}")
                    continue

            # Clean up temp directory
            import shutil

            if temp_dir.exists():
                shutil.rmtree(temp_dir, ignore_errors=True)

            self.core_api.print_success(f"Extracted {len(self.wifi_data)} WiFi records")

        except Exception as e:
            self.core_api.log_error(f"Error extracting WiFi data: {e}")
            self.errors.append(f"WiFi data extraction error: {str(e)}")

    def _generate_report(self) -> Path:
        """Generate markdown report."""
        sections = []

        # Summary
        total_records = len(self.wifi_data)
        written_records = len([r for r in self.wifi_data if r["segb_state"] == "Written"])
        deleted_records = len([r for r in self.wifi_data if r["segb_state"] == "Deleted"])

        # Count unique SSIDs
        unique_ssids = set()
        for r in self.wifi_data:
            if r["ssid"]:
                unique_ssids.add(r["ssid"])

        # Count connection/disconnection events
        connected_events = len([r for r in self.wifi_data if r["status"] == "Connected"])
        disconnected_events = len([r for r in self.wifi_data if r["status"] == "Disconnected"])

        summary_content = f"""
Extracted WiFi device connection/disconnection data from iOS Biome SEGB files.

**Total Records:** {total_records:,}
**Written Records:** {written_records:,}
**Deleted Records:** {deleted_records:,}
**Unique WiFi Networks (SSIDs):** {len(unique_ssids)}
**Connection Events:** {connected_events:,}
**Disconnection Events:** {disconnected_events:,}

The iOS Biome system stores WiFi connection and disconnection events in SEGB (Segmented Binary) files.
These files contain timestamped WiFi network information including SSIDs and connection status that can
provide insights into device location patterns, network usage, and user behavior.

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
        if self.wifi_data:
            stats = {
                "Total Records": f"{total_records:,}",
                "Written Records": f"{written_records:,}",
                "Deleted Records": f"{deleted_records:,}",
                "Unique WiFi Networks": f"{len(unique_ssids)}",
                "Connection Events": f"{connected_events:,}",
                "Disconnection Events": f"{disconnected_events:,}",
            }

            sections.append(
                {
                    "heading": "Statistics",
                    "content": stats,
                    "style": "table",
                }
            )

        # Unique SSIDs list
        if unique_ssids:
            ssid_list = sorted(list(unique_ssids))
            sections.append(
                {
                    "heading": "Unique WiFi Networks (SSIDs)",
                    "content": ssid_list,
                    "style": "list",
                }
            )

        # Sample data (first 20 written records)
        if self.wifi_data:
            written_sample = [r for r in self.wifi_data if r["segb_state"] == "Written"][:20]
            if written_sample:
                self._add_section_with_sample(sections, "WiFi Events (Sample)", written_sample)

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
            "Unique Networks": f"{len(unique_ssids)}",
        }

        report_path = self.core_api.generate_report(
            plugin_name=self.metadata.name,
            title="iOS Biome WiFi Devices Analysis",
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
        output_dir = self.core_api.get_case_output_dir("biome_wifi_data")
        output_dir.mkdir(parents=True, exist_ok=True)
        json_path = output_dir / "biome_wifi_devices.json"

        # Count unique SSIDs
        unique_ssids = set()
        for r in self.wifi_data:
            if r["ssid"]:
                unique_ssids.add(r["ssid"])

        export_data = {
            "wifi_data": self.wifi_data,
            "summary": {
                "total_records": len(self.wifi_data),
                "written_records": len([r for r in self.wifi_data if r["segb_state"] == "Written"]),
                "deleted_records": len([r for r in self.wifi_data if r["segb_state"] == "Deleted"]),
                "unique_ssids": len(unique_ssids),
                "connection_events": len([r for r in self.wifi_data if r["status"] == "Connected"]),
                "disconnection_events": len([r for r in self.wifi_data if r["status"] == "Disconnected"]),
            },
            "unique_networks": sorted(list(unique_ssids)),
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
        output_dir = self.core_api.get_case_output_dir("biome_wifi_data")
        output_dir.mkdir(parents=True, exist_ok=True)
        csv_path = output_dir / "biome_wifi_devices.csv"

        if self.wifi_data:
            self.core_api.export_plugin_data_to_csv(
                csv_path,
                self.metadata.name,
                self.metadata.version,
                self.wifi_data,
                self.extraction_type,
            )

            self.core_api.print_success(f"CSV export: {csv_path}")

        return csv_path

    def cleanup(self) -> None:
        """Clean up plugin resources."""
        self.core_api.log_info(f"Cleaning up {self.metadata.name}")
