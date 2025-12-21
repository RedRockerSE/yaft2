"""
iOS knowledgeC Database Extractor Plugin

Extracts device usage data from iOS knowledgeC.db database including:
- Battery percentage and charging status
- Media playback events
- App usage statistics
- Device lock/unlock events
- Screen on/off events
- Do Not Disturb status

Ported from iLEAPP knowledgeC artifacts.
"""

from datetime import datetime, timedelta
from pathlib import Path
import plistlib
from typing import Any

from yaft.core.api import CoreAPI
from yaft.core.plugin_base import PluginBase, PluginMetadata


class iOSknowledgeCPlugin(PluginBase):
    """Extract device usage data from iOS knowledgeC.db database."""

    def __init__(self, core_api: CoreAPI):
        super().__init__(core_api)
        self.extraction_type = "unknown"
        self.zip_prefix = ""
        self.battery_data: list[dict[str, Any]] = []
        self.plugin_status_data: list[dict[str, Any]] = []
        self.media_playing_data: list[dict[str, Any]] = []
        self.dnd_data: list[dict[str, Any]] = []
        self.app_usage_data: list[dict[str, Any]] = []
        self.lock_status_data: list[dict[str, Any]] = []
        self.screen_status_data: list[dict[str, Any]] = []
        self.errors: list[str] = []

    @property
    def metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name="iOSknowledgeCPlugin",
            version="1.0.0",
            description="Extract device usage data from iOS knowledgeC.db database",
            author="YaFT (ported from iLEAPP - @JohannPLW, @mxkrt, Geraldine Blay)",
            target_os=["ios"],
        )

    def initialize(self) -> None:
        """Initialize plugin resources."""
        self.core_api.log_info(f"Initializing {self.metadata.name}")

    def execute(self, *args, **kwargs) -> dict[str, Any]:
        """
        Extract device usage data from knowledgeC.db.

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

        # Find knowledgeC.db
        self.core_api.print_info("Searching for knowledgeC.db...")
        db_files = self.core_api.find_files_in_zip("knowledgeC.db")

        if not db_files:
            self.core_api.print_warning("knowledgeC.db not found in ZIP archive")
            return {
                "success": True,
                "message": "knowledgeC.db not found",
            }

        # Use the first database found
        db_path = db_files[0]
        self.core_api.print_info(f"Found knowledgeC.db: {db_path}")

        # Extract all artifacts
        self._extract_battery_percentage(db_path)
        self._extract_device_plugin_status(db_path)
        self._extract_media_playing(db_path)
        self._extract_do_not_disturb(db_path)
        self._extract_app_usage(db_path)
        self._extract_lock_status(db_path)
        self._extract_screen_status(db_path)

        # Generate report
        report_path = self._generate_report()

        # Export to JSON
        json_path = self._export_to_json()

        # Export to CSV (each artifact separately)
        csv_paths = self._export_to_csv()

        return {
            "success": True,
            "report_path": str(report_path),
            "json_path": str(json_path),
            "csv_paths": csv_paths,
            "battery_events": len(self.battery_data),
            "plugin_events": len(self.plugin_status_data),
            "media_events": len(self.media_playing_data),
            "dnd_events": len(self.dnd_data),
            "app_usage_events": len(self.app_usage_data),
            "lock_events": len(self.lock_status_data),
            "screen_events": len(self.screen_status_data),
            "errors": self.errors,
        }

    def _convert_core_data_timestamp(self, timestamp: float) -> str:
        """
        Convert Core Data timestamp to ISO format string.
        Core Data timestamps are seconds since 2001-01-01.
        """
        if timestamp is None:
            return ""
        try:
            dt = datetime(2001, 1, 1) + timedelta(seconds=timestamp)
            return dt.strftime("%Y-%m-%d %H:%M:%S")
        except (ValueError, OverflowError, OSError):
            return str(timestamp)

    def _format_duration(self, seconds: float) -> str:
        """Format duration in seconds to HH:MM:SS format."""
        if seconds is None:
            return ""
        try:
            total_seconds = int(seconds)
            hours = total_seconds // 3600
            minutes = (total_seconds % 3600) // 60
            secs = total_seconds % 60
            return f"{hours:02d}:{minutes:02d}:{secs:02d}"
        except (ValueError, TypeError):
            return ""

    def _extract_battery_percentage(self, db_path: str) -> None:
        """Extract battery percentage events."""
        try:
            query = """
            SELECT
                ZOBJECT.ZSTARTDATE,
                ZOBJECT.ZENDDATE,
                ZOBJECT.ZVALUEINTEGER,
                ZOBJECT.ZHASSTRUCTUREDMETADATA,
                ZOBJECT.ZCREATIONDATE
            FROM ZOBJECT
            WHERE ZOBJECT.ZSTREAMNAME = '/device/batteryPercentage'
            ORDER BY ZOBJECT.ZSTARTDATE
            """

            rows = self.core_api.query_sqlite_from_zip(db_path, query)

            for row in rows:
                start_time = self._convert_core_data_timestamp(row[0])
                end_time = self._convert_core_data_timestamp(row[1])
                battery_pct = row[2]
                is_fully_charged = "Yes" if row[3] == 1 else "No"
                time_added = self._convert_core_data_timestamp(row[4])

                self.battery_data.append({
                    "start_time": start_time,
                    "end_time": end_time,
                    "battery_percentage": battery_pct,
                    "is_fully_charged": is_fully_charged,
                    "time_added": time_added,
                })

            self.core_api.print_success(f"Extracted {len(self.battery_data)} battery events")

        except Exception as e:
            self.core_api.log_error(f"Error extracting battery data: {e}")
            self.errors.append(f"Battery extraction error: {str(e)}")

    def _extract_device_plugin_status(self, db_path: str) -> None:
        """Extract device plugin status events."""
        try:
            # Check if wireless adapter column exists
            query_check = """
            SELECT name FROM pragma_table_info('ZSTRUCTUREDMETADATA')
            WHERE name = 'Z_DKDEVICEISPLUGGEDINMETADATAKEY__ADAPTERISWIRELESS'
            """
            check_rows = self.core_api.query_sqlite_from_zip(db_path, query_check)
            has_wireless_column = len(check_rows) > 0

            if has_wireless_column:
                query = """
                SELECT
                    ZOBJECT.ZSTARTDATE,
                    ZOBJECT.ZENDDATE,
                    ZOBJECT.ZVALUEINTEGER,
                    ZSTRUCTUREDMETADATA.Z_DKDEVICEISPLUGGEDINMETADATAKEY__ADAPTERISWIRELESS,
                    ZOBJECT.ZCREATIONDATE
                FROM ZOBJECT
                LEFT OUTER JOIN ZSTRUCTUREDMETADATA ON ZOBJECT.ZSTRUCTUREDMETADATA = ZSTRUCTUREDMETADATA.Z_PK
                WHERE ZOBJECT.ZSTREAMNAME = '/device/isPluggedIn'
                ORDER BY ZOBJECT.ZSTARTDATE
                """
            else:
                query = """
                SELECT
                    ZOBJECT.ZSTARTDATE,
                    ZOBJECT.ZENDDATE,
                    ZOBJECT.ZVALUEINTEGER,
                    ZOBJECT.ZCREATIONDATE
                FROM ZOBJECT
                WHERE ZOBJECT.ZSTREAMNAME = '/device/isPluggedIn'
                ORDER BY ZOBJECT.ZSTARTDATE
                """

            rows = self.core_api.query_sqlite_from_zip(db_path, query)

            for row in rows:
                start_time = self._convert_core_data_timestamp(row[0])
                end_time = self._convert_core_data_timestamp(row[1])
                status = "Plugged in" if row[2] == 1 else "Unplugged"

                data = {
                    "start_time": start_time,
                    "end_time": end_time,
                    "device_plugin_status": status,
                }

                if has_wireless_column:
                    is_wireless = row[3]
                    data["is_adapter_wireless"] = "Yes" if is_wireless == '1' else "No" if is_wireless == '0' else "Not specified"
                    data["time_added"] = self._convert_core_data_timestamp(row[4])
                else:
                    data["time_added"] = self._convert_core_data_timestamp(row[3])

                self.plugin_status_data.append(data)

            self.core_api.print_success(f"Extracted {len(self.plugin_status_data)} plugin status events")

        except Exception as e:
            self.core_api.log_error(f"Error extracting plugin status: {e}")
            self.errors.append(f"Plugin status extraction error: {str(e)}")

    def _extract_media_playing(self, db_path: str) -> None:
        """Extract media playing events."""
        try:
            # Check if AirPlay video column exists
            query_check = """
            SELECT name FROM pragma_table_info('ZSTRUCTUREDMETADATA')
            WHERE name = 'Z_DKNOWPLAYINGMETADATAKEY__ISAIRPLAYVIDEO'
            """
            check_rows = self.core_api.query_sqlite_from_zip(db_path, query_check)
            has_airplay_column = len(check_rows) > 0

            if has_airplay_column:
                query = """
                SELECT
                    ZOBJECT.ZSTARTDATE,
                    ZOBJECT.ZENDDATE,
                    ZSTRUCTUREDMETADATA.Z_DKNOWPLAYINGMETADATAKEY__PLAYING,
                    ZOBJECT.ZVALUESTRING,
                    ZSTRUCTUREDMETADATA.Z_DKNOWPLAYINGMETADATAKEY__ARTIST,
                    ZSTRUCTUREDMETADATA.Z_DKNOWPLAYINGMETADATAKEY__ALBUM,
                    ZSTRUCTUREDMETADATA.Z_DKNOWPLAYINGMETADATAKEY__TITLE,
                    ZSTRUCTUREDMETADATA.Z_DKNOWPLAYINGMETADATAKEY__GENRE,
                    ZSTRUCTUREDMETADATA.Z_DKNOWPLAYINGMETADATAKEY__DURATION,
                    ZSTRUCTUREDMETADATA.Z_DKNOWPLAYINGMETADATAKEY__ISAIRPLAYVIDEO,
                    ZSTRUCTUREDMETADATA.Z_DKNOWPLAYINGMETADATAKEY__OUTPUTDEVICEIDS,
                    ZOBJECT.ZCREATIONDATE
                FROM ZOBJECT
                LEFT OUTER JOIN ZSTRUCTUREDMETADATA ON ZOBJECT.ZSTRUCTUREDMETADATA = ZSTRUCTUREDMETADATA.Z_PK
                WHERE ZOBJECT.ZSTREAMNAME = '/media/nowPlaying' AND ZOBJECT.ZVALUESTRING != ''
                ORDER BY ZOBJECT.ZSTARTDATE
                """
            else:
                query = """
                SELECT
                    ZOBJECT.ZSTARTDATE,
                    ZOBJECT.ZENDDATE,
                    ZSTRUCTUREDMETADATA.Z_DKNOWPLAYINGMETADATAKEY__PLAYING,
                    ZOBJECT.ZVALUESTRING,
                    ZSTRUCTUREDMETADATA.Z_DKNOWPLAYINGMETADATAKEY__ARTIST,
                    ZSTRUCTUREDMETADATA.Z_DKNOWPLAYINGMETADATAKEY__ALBUM,
                    ZSTRUCTUREDMETADATA.Z_DKNOWPLAYINGMETADATAKEY__TITLE,
                    ZSTRUCTUREDMETADATA.Z_DKNOWPLAYINGMETADATAKEY__GENRE,
                    ZSTRUCTUREDMETADATA.Z_DKNOWPLAYINGMETADATAKEY__DURATION,
                    ZOBJECT.ZCREATIONDATE
                FROM ZOBJECT
                LEFT OUTER JOIN ZSTRUCTUREDMETADATA ON ZOBJECT.ZSTRUCTUREDMETADATA = ZSTRUCTUREDMETADATA.Z_PK
                WHERE ZOBJECT.ZSTREAMNAME = '/media/nowPlaying' AND ZOBJECT.ZVALUESTRING != ''
                ORDER BY ZOBJECT.ZSTARTDATE
                """

            rows = self.core_api.query_sqlite_from_zip(db_path, query)

            for row in rows:
                start_time = self._convert_core_data_timestamp(row[0])
                end_time = self._convert_core_data_timestamp(row[1])

                # Playing state
                playing_state_map = {0: "Stop", 1: "Play", 2: "Pause", 3: "Loading", 4: "Interruption"}
                playing_state = playing_state_map.get(row[2], str(row[2]))

                # Calculate playing duration
                playing_duration = ""
                if row[0] and row[1]:
                    duration_seconds = row[1] - row[0]
                    playing_duration = self._format_duration(duration_seconds)

                # Media duration
                media_duration = self._format_duration(row[8])

                data = {
                    "start_time": start_time,
                    "end_time": end_time,
                    "playing_state": playing_state,
                    "playing_duration": playing_duration,
                    "app_bundle_id": row[3] or "",
                    "artist": row[4] or "",
                    "album": row[5] or "",
                    "title": row[6] or "",
                    "genre": row[7] or "",
                    "media_duration": media_duration,
                }

                if has_airplay_column:
                    is_airplay = "Yes" if row[9] == 1 else "No"
                    data["airplay_video"] = is_airplay

                    # Parse output device from binary plist
                    output_device = ""
                    output_device_ids = row[10]
                    if isinstance(output_device_ids, bytes):
                        try:
                            output_device_bplist = plistlib.loads(output_device_ids)
                            if isinstance(output_device_bplist, dict) and '$objects' in output_device_bplist:
                                objects = output_device_bplist['$objects']
                                if len(objects) > 6:
                                    output_device = str(objects[6])
                        except Exception:
                            pass
                    data["output_device"] = output_device
                    data["time_added"] = self._convert_core_data_timestamp(row[11])
                else:
                    data["time_added"] = self._convert_core_data_timestamp(row[9])

                self.media_playing_data.append(data)

            self.core_api.print_success(f"Extracted {len(self.media_playing_data)} media playing events")

        except Exception as e:
            self.core_api.log_error(f"Error extracting media playing data: {e}")
            self.errors.append(f"Media playing extraction error: {str(e)}")

    def _extract_do_not_disturb(self, db_path: str) -> None:
        """Extract Do Not Disturb events."""
        try:
            query = """
            SELECT
                ZOBJECT.ZSTARTDATE,
                ZOBJECT.ZENDDATE,
                ZOBJECT.ZVALUEINTEGER,
                ZOBJECT.ZCREATIONDATE
            FROM ZOBJECT
            WHERE ZOBJECT.ZSTREAMNAME = '/settings/doNotDisturb'
            ORDER BY ZOBJECT.ZSTARTDATE
            """

            rows = self.core_api.query_sqlite_from_zip(db_path, query)

            for row in rows:
                start_time = self._convert_core_data_timestamp(row[0])
                end_time = self._convert_core_data_timestamp(row[1])
                is_dnd_on = "Yes" if row[2] == 1 else "No"
                time_added = self._convert_core_data_timestamp(row[3])

                self.dnd_data.append({
                    "start_time": start_time,
                    "end_time": end_time,
                    "do_not_disturb": is_dnd_on,
                    "time_added": time_added,
                })

            self.core_api.print_success(f"Extracted {len(self.dnd_data)} Do Not Disturb events")

        except Exception as e:
            self.core_api.log_error(f"Error extracting DND data: {e}")
            self.errors.append(f"DND extraction error: {str(e)}")

    def _extract_app_usage(self, db_path: str) -> None:
        """Extract app usage events."""
        try:
            query = """
            SELECT
                ZOBJECT.ZSTARTDATE,
                ZOBJECT.ZENDDATE,
                ZOBJECT.ZCREATIONDATE,
                ZOBJECT.ZVALUESTRING
            FROM ZOBJECT
            WHERE ZSTREAMNAME = '/app/usage'
            ORDER BY ZOBJECT.ZSTARTDATE
            """

            rows = self.core_api.query_sqlite_from_zip(db_path, query)

            for row in rows:
                start_time = self._convert_core_data_timestamp(row[0])
                end_time = self._convert_core_data_timestamp(row[1])
                time_added = self._convert_core_data_timestamp(row[2])
                app_bundle_id = row[3] or ""

                self.app_usage_data.append({
                    "start_time": start_time,
                    "end_time": end_time,
                    "time_added": time_added,
                    "application": app_bundle_id,
                })

            self.core_api.print_success(f"Extracted {len(self.app_usage_data)} app usage events")

        except Exception as e:
            self.core_api.log_error(f"Error extracting app usage: {e}")
            self.errors.append(f"App usage extraction error: {str(e)}")

    def _extract_lock_status(self, db_path: str) -> None:
        """Extract device lock status events."""
        try:
            query = """
            SELECT
                ZOBJECT.ZSTARTDATE,
                ZOBJECT.ZENDDATE,
                ZOBJECT.ZCREATIONDATE,
                ZOBJECT.ZVALUEINTEGER
            FROM ZOBJECT
            WHERE ZSTREAMNAME = '/device/isLocked'
            ORDER BY ZOBJECT.ZSTARTDATE
            """

            rows = self.core_api.query_sqlite_from_zip(db_path, query)

            for row in rows:
                start_time = self._convert_core_data_timestamp(row[0])
                end_time = self._convert_core_data_timestamp(row[1])
                time_added = self._convert_core_data_timestamp(row[2])
                lock_status = "Locked" if row[3] == 1 else "Unlocked"

                self.lock_status_data.append({
                    "start_time": start_time,
                    "end_time": end_time,
                    "time_added": time_added,
                    "device_lock_status": lock_status,
                })

            self.core_api.print_success(f"Extracted {len(self.lock_status_data)} lock status events")

        except Exception as e:
            self.core_api.log_error(f"Error extracting lock status: {e}")
            self.errors.append(f"Lock status extraction error: {str(e)}")

    def _extract_screen_status(self, db_path: str) -> None:
        """Extract screen backlight status events."""
        try:
            query = """
            SELECT
                ZOBJECT.ZSTARTDATE,
                ZOBJECT.ZENDDATE,
                ZOBJECT.ZCREATIONDATE,
                ZOBJECT.ZVALUEINTEGER
            FROM ZOBJECT
            WHERE ZSTREAMNAME = '/display/isBacklit'
            ORDER BY ZOBJECT.ZSTARTDATE
            """

            rows = self.core_api.query_sqlite_from_zip(db_path, query)

            for row in rows:
                start_time = self._convert_core_data_timestamp(row[0])
                end_time = self._convert_core_data_timestamp(row[1])
                time_added = self._convert_core_data_timestamp(row[2])
                screen_status = "Backlight on" if row[3] == 1 else "Backlight off"

                self.screen_status_data.append({
                    "start_time": start_time,
                    "end_time": end_time,
                    "time_added": time_added,
                    "device_screen_status": screen_status,
                })

            self.core_api.print_success(f"Extracted {len(self.screen_status_data)} screen status events")

        except Exception as e:
            self.core_api.log_error(f"Error extracting screen status: {e}")
            self.errors.append(f"Screen status extraction error: {str(e)}")

    def _generate_report(self) -> Path:
        """Generate markdown report."""
        sections = []

        # Summary
        total_events = (
            len(self.battery_data) +
            len(self.plugin_status_data) +
            len(self.media_playing_data) +
            len(self.dnd_data) +
            len(self.app_usage_data) +
            len(self.lock_status_data) +
            len(self.screen_status_data)
        )

        summary_content = f"""
Extracted device usage data from iOS knowledgeC.db database.

**Total Events:** {total_events:,}

The knowledgeC database contains rich device usage information including battery status,
charging events, media playback, app usage, lock status, and screen activity. This data
provides valuable insights into device usage patterns and user behavior.

**Note:** Full data exported to CSV and JSON files for detailed analysis.
"""

        sections.append({
            "heading": "Summary",
            "content": summary_content.strip(),
            "style": "text",
        })

        # Statistics table
        stats = {
            "Battery Events": f"{len(self.battery_data):,}",
            "Plugin Status Events": f"{len(self.plugin_status_data):,}",
            "Media Playing Events": f"{len(self.media_playing_data):,}",
            "Do Not Disturb Events": f"{len(self.dnd_data):,}",
            "App Usage Events": f"{len(self.app_usage_data):,}",
            "Lock Status Events": f"{len(self.lock_status_data):,}",
            "Screen Status Events": f"{len(self.screen_status_data):,}",
        }

        sections.append({
            "heading": "Event Statistics",
            "content": stats,
            "style": "table",
        })

        # Add sample data for each artifact (first 10 records)
        if self.battery_data:
            self._add_section_with_sample(sections, "Battery Percentage (Sample)", self.battery_data[:10])

        if self.plugin_status_data:
            self._add_section_with_sample(sections, "Device Plugin Status (Sample)", self.plugin_status_data[:10])

        if self.media_playing_data:
            self._add_section_with_sample(sections, "Media Playing (Sample)", self.media_playing_data[:10])

        if self.dnd_data:
            self._add_section_with_sample(sections, "Do Not Disturb (Sample)", self.dnd_data[:10])

        if self.app_usage_data:
            self._add_section_with_sample(sections, "App Usage (Sample)", self.app_usage_data[:10])

        if self.lock_status_data:
            self._add_section_with_sample(sections, "Lock Status (Sample)", self.lock_status_data[:10])

        if self.screen_status_data:
            self._add_section_with_sample(sections, "Screen Status (Sample)", self.screen_status_data[:10])

        # Errors
        if self.errors:
            sections.append({
                "heading": "Errors",
                "content": self.errors,
                "style": "list",
            })

        metadata = {
            "Extraction Type": self.extraction_type,
            "Total Events": f"{total_events:,}",
        }

        report_path = self.core_api.generate_report(
            plugin_name=self.metadata.name,
            title="iOS knowledgeC Database Analysis",
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

        sections.append({
            "heading": heading,
            "content": table,
            "style": "table",
        })

    def _export_to_json(self) -> Path:
        """Export all data to JSON."""
        output_dir = self.core_api.get_case_output_dir("knowledgec_data")
        output_dir.mkdir(parents=True, exist_ok=True)
        json_path = output_dir / "knowledgeC_all_data.json"

        export_data = {
            "battery_percentage": self.battery_data,
            "device_plugin_status": self.plugin_status_data,
            "media_playing": self.media_playing_data,
            "do_not_disturb": self.dnd_data,
            "app_usage": self.app_usage_data,
            "lock_status": self.lock_status_data,
            "screen_status": self.screen_status_data,
            "summary": {
                "total_battery_events": len(self.battery_data),
                "total_plugin_events": len(self.plugin_status_data),
                "total_media_events": len(self.media_playing_data),
                "total_dnd_events": len(self.dnd_data),
                "total_app_usage_events": len(self.app_usage_data),
                "total_lock_events": len(self.lock_status_data),
                "total_screen_events": len(self.screen_status_data),
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

    def _export_to_csv(self) -> list[str]:
        """Export each artifact to separate CSV files."""
        output_dir = self.core_api.get_case_output_dir("knowledgec_data")
        output_dir.mkdir(parents=True, exist_ok=True)
        csv_paths = []

        artifacts = [
            ("battery_percentage", self.battery_data),
            ("device_plugin_status", self.plugin_status_data),
            ("media_playing", self.media_playing_data),
            ("do_not_disturb", self.dnd_data),
            ("app_usage", self.app_usage_data),
            ("lock_status", self.lock_status_data),
            ("screen_status", self.screen_status_data),
        ]

        for name, data in artifacts:
            if data:
                csv_path = output_dir / f"knowledgeC_{name}.csv"
                self.core_api.export_plugin_data_to_csv(
                    csv_path,
                    self.metadata.name,
                    self.metadata.version,
                    data,
                    self.extraction_type,
                )
                csv_paths.append(str(csv_path))

        if csv_paths:
            self.core_api.print_success(f"Exported {len(csv_paths)} CSV files")

        return csv_paths

    def cleanup(self) -> None:
        """Clean up plugin resources."""
        self.core_api.log_info(f"Cleaning up {self.metadata.name}")
