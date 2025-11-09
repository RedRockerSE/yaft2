"""
iOS Call Log Analyzer Plugin for YaFT

This plugin extracts and analyzes call history from iOS full filesystem extractions,
including incoming, outgoing, missed calls, and FaceTime audio/video calls.

Supports both Cellebrite and GrayKey extraction formats.

Based on forensic research of iOS CallHistoryDB structure.
"""

from pathlib import Path
from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta

from yaft.core.api import CoreAPI
from yaft.core.plugin_base import PluginBase, PluginMetadata


class iOSCallLogAnalyzerPlugin(PluginBase):
    """
    iOS Call Log Analyzer for forensic analysis.

    Extracts comprehensive call history from iOS CallHistoryDB including
    regular phone calls, FaceTime audio/video calls, call duration, and timestamps.
    """

    # Call type constants based on iOS CallHistoryDB schema
    CALL_TYPES = {
        1: "Outgoing",
        2: "Incoming",
        3: "Incoming (Unanswered)",  # Missed
        4: "Outgoing (Unanswered)",
        5: "FaceTime Video",
        6: "FaceTime Audio",
        7: "FaceTime Group",
        8: "Outgoing Cancelled",
    }

    # Call service types
    SERVICE_TYPES = {
        "Normal": "Cellular",
        "FaceTimeVideo": "FaceTime Video",
        "FaceTimeAudio": "FaceTime Audio",
        "WiFiCalling": "WiFi Calling",
    }

    def __init__(self, core_api: CoreAPI) -> None:
        super().__init__(core_api)
        self.calls: List[Dict[str, Any]] = []
        self.zip_prefix = ''
        self.extraction_type = 'unknown'
        self.errors: List[Dict[str, str]] = []

    @property
    def metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name="iOSCallLogAnalyzer",
            version="1.0.0",
            description="Extract and analyze iOS call history including FaceTime calls",
            author="YaFT Forensics Team",
            requires_core_version=">=0.1.0",
            dependencies=[],
            enabled=True,
            target_os=["ios"],
        )

    def initialize(self) -> None:
        """Initialize the plugin."""
        self.core_api.log_info(f"Initializing {self.metadata.name}")
        self.calls = []
        self.errors = []

    def execute(self, *args: Any, **kwargs: Any) -> Dict[str, Any]:
        """
        Execute iOS call log extraction.

        The plugin uses the ZIP file loaded via --zip option.
        """
        # Check if ZIP file is loaded
        current_zip = self.core_api.get_current_zip()
        if not current_zip:
            self.core_api.print_error(
                "No ZIP file loaded. Use --zip option to specify an iOS extraction ZIP."
            )
            return {"success": False, "error": "No ZIP file loaded"}

        self.core_api.print_success(f"Analyzing iOS extraction: {current_zip.name}")

        try:
            # Detect Cellebrite vs GrayKey format
            self._detect_zip_structure()

            # Parse call history database
            self.core_api.print_info("Parsing CallHistory.storedata...")
            self.calls = self._parse_call_history()
            self.core_api.print_success(f"Found {len(self.calls)} call records")

            # Analyze call patterns
            self._analyze_call_patterns()

            # Display summary
            self._display_summary()

            # Generate report
            report_path = self._generate_report()
            self.core_api.print_success(f"Report generated: {report_path}")

            # Export to JSON
            output_dir = self.core_api.get_case_output_dir("ios_call_logs")
            output_dir.mkdir(parents=True, exist_ok=True)

            json_path = output_dir / f"{current_zip.stem}_call_logs.json"
            self._export_to_json(json_path)
            self.core_api.print_success(f"Call log data exported to: {json_path}")

            return {
                "success": True,
                "total_calls": len(self.calls),
                "report_path": str(report_path),
                "json_path": str(json_path),
            }

        except Exception as e:
            self.core_api.print_error(f"Extraction failed: {e}")
            self.core_api.log_error(f"Error details: {e}")
            return {"success": False, "error": str(e)}

    def _detect_zip_structure(self) -> None:
        """Detect ZIP structure using CoreAPI method."""
        self.extraction_type, self.zip_prefix = self.core_api.detect_zip_format()

    def _normalize_path(self, path: str) -> str:
        """Normalize path for ZIP access using CoreAPI method."""
        return self.core_api.normalize_zip_path(path, self.zip_prefix)

    def _parse_call_history(self) -> List[Dict[str, Any]]:
        """Parse CallHistory.storedata database for call records."""
        call_history_path = 'private/var/mobile/Library/CallHistoryDB/CallHistory.storedata'
        calls = []

        try:
            # Main query for call records
            query = """
                SELECT
                    ZADDRESS as phone_number,
                    ZDATE as date,
                    ZDURATION as duration,
                    ZCALLTYPE as call_type,
                    ZREAD as is_read,
                    ZANSWERED as answered,
                    ZORIGINATED as originated,
                    ZSERVICE_PROVIDER as service_provider,
                    ZISO_COUNTRY_CODE as country_code,
                    ZLOCATION as location,
                    ZNAME as contact_name,
                    ZFACE_TIME_DATA as facetime_data
                FROM ZCALLRECORD
                ORDER BY ZDATE DESC
            """

            # Fallback query for older iOS versions (without some columns)
            fallback_query = """
                SELECT
                    ZADDRESS as phone_number,
                    ZDATE as date,
                    ZDURATION as duration,
                    ZCALLTYPE as call_type,
                    ZREAD as is_read,
                    ZANSWERED as answered,
                    ZORIGINATED as originated,
                    NULL as service_provider,
                    NULL as country_code,
                    NULL as location,
                    NULL as contact_name,
                    NULL as facetime_data
                FROM ZCALLRECORD
                ORDER BY ZDATE DESC
            """

            results = self.core_api.query_sqlite_from_zip_dict(
                self._normalize_path(call_history_path),
                query,
                fallback_query=fallback_query
            )

            for row in results:
                call = self._process_call_record(row)
                if call:
                    calls.append(call)

        except KeyError:
            self.errors.append({
                'source': call_history_path,
                'error': 'CallHistory.storedata not found in ZIP',
            })
            self.core_api.log_warning("CallHistory.storedata not found in ZIP")
        except Exception as e:
            self.errors.append({'source': call_history_path, 'error': str(e)})
            self.core_api.log_error(f"Error parsing CallHistory.storedata: {e}")

        return calls

    def _process_call_record(self, row: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Process a single call record from the database."""
        try:
            # Convert Core Data timestamp (seconds since 2001-01-01)
            core_data_epoch = datetime(2001, 1, 1)
            timestamp = None
            if row.get('date') is not None:
                timestamp = core_data_epoch + timedelta(seconds=float(row['date']))

            # Determine call type and direction
            call_type_code = row.get('call_type', 1)
            call_type = self.CALL_TYPES.get(call_type_code, f"Unknown ({call_type_code})")

            # Determine direction
            if row.get('originated'):
                direction = "Outgoing"
            elif row.get('answered'):
                direction = "Incoming"
            else:
                direction = "Missed"

            # Determine service type
            service = "Cellular"
            if row.get('facetime_data'):
                service = "FaceTime"
            elif row.get('service_provider'):
                service = row['service_provider']

            call = {
                'phone_number': row.get('phone_number', 'Unknown'),
                'contact_name': row.get('contact_name', ''),
                'timestamp': timestamp.isoformat() if timestamp else None,
                'duration': int(row.get('duration', 0)),
                'duration_formatted': self._format_duration(row.get('duration', 0)),
                'call_type': call_type,
                'direction': direction,
                'service': service,
                'answered': bool(row.get('answered')),
                'read': bool(row.get('is_read')),
                'country_code': row.get('country_code', ''),
                'location': row.get('location', ''),
            }

            return call

        except Exception as e:
            self.core_api.log_warning(f"Error processing call record: {e}")
            return None

    def _format_duration(self, seconds: float) -> str:
        """Format call duration in human-readable format."""
        seconds = int(seconds)
        if seconds < 60:
            return f"{seconds}s"
        elif seconds < 3600:
            minutes = seconds // 60
            secs = seconds % 60
            return f"{minutes}m {secs}s"
        else:
            hours = seconds // 3600
            minutes = (seconds % 3600) // 60
            return f"{hours}h {minutes}m"

    def _analyze_call_patterns(self) -> None:
        """Analyze call patterns and add statistics."""
        if not self.calls:
            return

        # Count calls by direction
        self.outgoing_count = sum(1 for c in self.calls if c['direction'] == 'Outgoing')
        self.incoming_count = sum(1 for c in self.calls if c['direction'] == 'Incoming')
        self.missed_count = sum(1 for c in self.calls if c['direction'] == 'Missed')

        # Count FaceTime calls
        self.facetime_count = sum(1 for c in self.calls if 'FaceTime' in c['service'])

        # Calculate total duration
        self.total_duration = sum(c['duration'] for c in self.calls)

        # Find most frequent contacts
        from collections import Counter
        phone_numbers = [c['phone_number'] for c in self.calls if c['phone_number'] != 'Unknown']
        self.frequent_contacts = Counter(phone_numbers).most_common(10)

    def _display_summary(self) -> None:
        """Display summary table of call log analysis."""
        from rich.table import Table

        table = Table(title="iOS Call Log Summary")
        table.add_column("Category", style="cyan", no_wrap=True)
        table.add_column("Count", style="green", justify="right")

        table.add_row("Total Calls", str(len(self.calls)))
        table.add_row("Outgoing", str(getattr(self, 'outgoing_count', 0)))
        table.add_row("Incoming", str(getattr(self, 'incoming_count', 0)))
        table.add_row("Missed", str(getattr(self, 'missed_count', 0)))
        table.add_row("FaceTime Calls", str(getattr(self, 'facetime_count', 0)))

        total_duration = getattr(self, 'total_duration', 0)
        table.add_row("Total Duration", self._format_duration(total_duration))

        self.core_api.console.print()
        self.core_api.console.print(table)

        if self.errors:
            self.core_api.print_warning(
                f"Encountered {len(self.errors)} errors during extraction (see report for details)"
            )

    def _generate_report(self) -> Path:
        """Generate markdown report."""
        # Statistics
        total_calls = len(self.calls)
        outgoing = getattr(self, 'outgoing_count', 0)
        incoming = getattr(self, 'incoming_count', 0)
        missed = getattr(self, 'missed_count', 0)
        facetime = getattr(self, 'facetime_count', 0)

        sections = [
            {
                "heading": "Executive Summary",
                "content": (
                    f"**Total Call Records:** {total_calls}  \n"
                    f"**Outgoing Calls:** {outgoing}  \n"
                    f"**Incoming Calls:** {incoming}  \n"
                    f"**Missed Calls:** {missed}  \n"
                    f"**FaceTime Calls:** {facetime}  \n"
                    f"**Total Duration:** {self._format_duration(getattr(self, 'total_duration', 0))}  \n"
                ),
            },
        ]

        # Recent calls
        recent_calls = self.calls[:50]  # Last 50 calls
        if recent_calls:
            recent_table = []
            for call in recent_calls:
                recent_table.append({
                    "Timestamp": call.get('timestamp', 'N/A')[:19] if call.get('timestamp') else 'N/A',
                    "Number": call.get('phone_number', 'Unknown')[:20],
                    "Contact": call.get('contact_name', '')[:20] if call.get('contact_name') else '',
                    "Direction": call.get('direction', 'N/A'),
                    "Duration": call.get('duration_formatted', '0s'),
                    "Service": call.get('service', 'Cellular'),
                })
            sections.append({
                "heading": "Recent Calls (Last 50)",
                "content": recent_table,
                "style": "table",
            })

        # Frequent contacts
        frequent_contacts = getattr(self, 'frequent_contacts', [])
        if frequent_contacts:
            freq_table = []
            for number, count in frequent_contacts:
                freq_table.append({
                    "Phone Number": number,
                    "Call Count": str(count),
                })
            sections.append({
                "heading": "Most Frequent Contacts",
                "content": freq_table,
                "style": "table",
            })

        # Missed calls
        missed_calls = [c for c in self.calls if c['direction'] == 'Missed'][:20]
        if missed_calls:
            missed_table = []
            for call in missed_calls:
                missed_table.append({
                    "Timestamp": call.get('timestamp', 'N/A')[:19] if call.get('timestamp') else 'N/A',
                    "Number": call.get('phone_number', 'Unknown'),
                    "Contact": call.get('contact_name', '') if call.get('contact_name') else '',
                })
            sections.append({
                "heading": "Missed Calls",
                "content": missed_table,
                "style": "table",
            })

        # Forensic notes
        forensic_notes = []
        if missed > 0:
            forensic_notes.append(f"⚠️ {missed} missed calls identified")
        if facetime > 0:
            forensic_notes.append(f"📹 {facetime} FaceTime calls (audio/video) detected")

        if forensic_notes:
            sections.append({
                "heading": "Forensic Notes",
                "content": '\n\n'.join(forensic_notes),
            })

        # Errors
        if self.errors:
            sections.append({
                "heading": "Extraction Errors",
                "content": self.errors,
                "style": "table",
            })

        metadata = {
            "Total Calls": str(total_calls),
            "Date Range": self._get_date_range(),
            "ZIP File": self.core_api.get_current_zip().name
            if self.core_api.get_current_zip()
            else "Unknown",
        }

        return self.core_api.generate_report(
            plugin_name="iOSCallLogAnalyzer",
            title="iOS Call Log Analysis Report",
            sections=sections,
            metadata=metadata,
        )

    def _get_date_range(self) -> str:
        """Get the date range of calls."""
        if not self.calls:
            return "N/A"

        timestamps = [c['timestamp'] for c in self.calls if c.get('timestamp')]
        if not timestamps:
            return "N/A"

        earliest = min(timestamps)
        latest = max(timestamps)
        return f"{earliest[:10]} to {latest[:10]}"

    def _export_to_json(self, output_path: Path) -> None:
        """Export call log data to JSON file using CoreAPI method."""
        self.core_api.export_plugin_data_to_json(
            output_path=output_path,
            plugin_name=self.metadata.name,
            plugin_version=self.metadata.version,
            data={
                'calls': self.calls,
                'statistics': {
                    'total_calls': len(self.calls),
                    'outgoing': getattr(self, 'outgoing_count', 0),
                    'incoming': getattr(self, 'incoming_count', 0),
                    'missed': getattr(self, 'missed_count', 0),
                    'facetime': getattr(self, 'facetime_count', 0),
                    'total_duration': getattr(self, 'total_duration', 0),
                    'date_range': self._get_date_range(),
                },
            },
            extraction_type=self.extraction_type,
            errors=self.errors,
        )

    def cleanup(self) -> None:
        """Clean up temporary resources."""
        self.core_api.log_info(f"Cleaning up {self.metadata.name}")
