"""
Android Call Log Analyzer Plugin for YaFT

This plugin extracts and analyzes call history from Android full filesystem extractions,
including incoming, outgoing, missed calls, rejected calls, and call duration.

Supports both Cellebrite and GrayKey extraction formats.

Based on forensic research of Android call log database structure.
"""

from pathlib import Path
from typing import Any, Dict, List, Optional
from datetime import datetime

from yaft.core.api import CoreAPI
from yaft.core.plugin_base import PluginBase, PluginMetadata


class AndroidCallLogAnalyzerPlugin(PluginBase):
    """
    Android Call Log Analyzer for forensic analysis.

    Extracts comprehensive call history from Android call log database including
    call types, duration, phone numbers, and contact names.
    """

    # Call type constants based on Android CallLog.Calls schema
    CALL_TYPES = {
        1: "Incoming",
        2: "Outgoing",
        3: "Missed",
        4: "Voicemail",
        5: "Rejected",
        6: "Blocked",
        7: "Answered Externally",
    }

    # Call features (VoIP, video calls, etc.)
    CALL_FEATURES = {
        0: "Audio",
        1: "Video",
        2: "WiFi Calling",
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
            name="AndroidCallLogAnalyzer",
            version="1.0.0",
            description="Extract and analyze Android call history including call types and duration",
            author="YaFT Forensics Team",
            requires_core_version=">=0.1.0",
            dependencies=[],
            enabled=True,
            target_os=["android"],
        )

    def initialize(self) -> None:
        """Initialize the plugin."""
        self.core_api.log_info(f"Initializing {self.metadata.name}")
        self.calls = []
        self.errors = []

    def execute(self, *args: Any, **kwargs: Any) -> Dict[str, Any]:
        """
        Execute Android call log extraction.

        The plugin uses the ZIP file loaded via --zip option.
        """
        # Check if ZIP file is loaded
        current_zip = self.core_api.get_current_zip()
        if not current_zip:
            self.core_api.print_error(
                "No ZIP file loaded. Use --zip option to specify an Android extraction ZIP."
            )
            return {"success": False, "error": "No ZIP file loaded"}

        self.core_api.print_success(f"Analyzing Android extraction: {current_zip.name}")

        try:
            # Detect Cellebrite vs GrayKey format
            self._detect_zip_structure()

            # Parse call log database
            self.core_api.print_info("Parsing calllog.db...")
            self.calls = self._parse_call_log()
            self.core_api.print_success(f"Found {len(self.calls)} call records")

            # Analyze call patterns
            self._analyze_call_patterns()

            # Display summary
            self._display_summary()

            # Generate report
            report_path = self._generate_report()
            self.core_api.print_success(f"Report generated: {report_path}")

            # Export to JSON
            output_dir = self.core_api.get_case_output_dir("android_call_logs")
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

    def _parse_call_log(self) -> List[Dict[str, Any]]:
        """Parse calllog.db database for call records."""
        calllog_path = 'data/data/com.android.providers.contacts/databases/calllog.db'
        calls = []

        try:
            # Main query for call records
            query = """
                SELECT
                    number,
                    date,
                    duration,
                    type,
                    name,
                    numbertype,
                    numberlabel,
                    countryiso,
                    geocoded_location,
                    data_usage,
                    features,
                    is_read,
                    new,
                    _id
                FROM calls
                ORDER BY date DESC
            """

            # Fallback query for older/minimal Android versions (fewer columns)
            fallback_query = """
                SELECT
                    number,
                    date,
                    duration,
                    type,
                    NULL as name,
                    NULL as numbertype,
                    NULL as numberlabel,
                    NULL as countryiso,
                    NULL as geocoded_location,
                    NULL as data_usage,
                    NULL as features,
                    is_read,
                    NULL as new,
                    _id
                FROM calls
                ORDER BY date DESC
            """

            results = self.core_api.query_sqlite_from_zip_dict(
                self._normalize_path(calllog_path),
                query,
                fallback_query=fallback_query
            )

            for row in results:
                call = self._process_call_record(row)
                if call:
                    calls.append(call)

        except KeyError:
            self.errors.append({
                'source': calllog_path,
                'error': 'calllog.db not found in ZIP',
            })
            self.core_api.log_warning("calllog.db not found in ZIP")
        except Exception as e:
            self.errors.append({'source': calllog_path, 'error': str(e)})
            self.core_api.log_error(f"Error parsing calllog.db: {e}")

        return calls

    def _process_call_record(self, row: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Process a single call record from the database."""
        try:
            # Convert timestamp (milliseconds since epoch)
            timestamp = None
            if row.get('date') is not None:
                timestamp = datetime.fromtimestamp(int(row['date']) / 1000.0)

            # Determine call type
            call_type_code = row.get('type', 1)
            call_type = self.CALL_TYPES.get(call_type_code, f"Unknown ({call_type_code})")

            # Determine direction
            if call_type_code == 2:
                direction = "Outgoing"
            elif call_type_code == 1:
                direction = "Incoming"
            elif call_type_code == 3:
                direction = "Missed"
            elif call_type_code == 5:
                direction = "Rejected"
            else:
                direction = call_type

            # Determine call features (video, VoIP, etc.)
            features = row.get('features', 0)
            if features:
                feature_type = self.CALL_FEATURES.get(features, "Unknown")
            else:
                feature_type = "Audio"

            # Number type (Mobile, Home, Work, etc.)
            number_type = self._get_number_type(row.get('numbertype'), row.get('numberlabel'))

            call = {
                'phone_number': row.get('number', 'Unknown'),
                'contact_name': row.get('name', ''),
                'timestamp': timestamp.isoformat() if timestamp else None,
                'duration': int(row.get('duration', 0)),
                'duration_formatted': self._format_duration(row.get('duration', 0)),
                'call_type': call_type,
                'direction': direction,
                'feature_type': feature_type,
                'number_type': number_type,
                'country_code': row.get('countryiso', ''),
                'location': row.get('geocoded_location', ''),
                'data_usage': row.get('data_usage', 0),
                'is_read': bool(row.get('is_read')),
                'is_new': bool(row.get('new')),
                'record_id': row.get('_id'),
            }

            return call

        except Exception as e:
            self.core_api.log_warning(f"Error processing call record: {e}")
            return None

    def _get_number_type(self, type_code: Optional[int], label: Optional[str]) -> str:
        """Get human-readable number type."""
        # Android ContactsContract.CommonDataKinds.Phone types
        types = {
            1: "Home",
            2: "Mobile",
            3: "Work",
            4: "Fax (Work)",
            5: "Fax (Home)",
            6: "Pager",
            7: "Other",
            8: "Custom",
            9: "Main",
            10: "Work (Mobile)",
            11: "Work (Pager)",
            12: "Assistant",
            13: "MMS",
        }

        if type_code == 0 or type_code is None:
            return "Unknown"

        if type_code == 8 and label:  # Custom type
            return f"Custom ({label})"

        return types.get(type_code, f"Type {type_code}")

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
        self.rejected_count = sum(1 for c in self.calls if c['direction'] == 'Rejected')

        # Count video calls
        self.video_count = sum(1 for c in self.calls if c['feature_type'] == 'Video')

        # Calculate total duration
        self.total_duration = sum(c['duration'] for c in self.calls)

        # Find most frequent contacts
        from collections import Counter
        phone_numbers = [c['phone_number'] for c in self.calls if c['phone_number'] != 'Unknown']
        self.frequent_contacts = Counter(phone_numbers).most_common(10)

    def _display_summary(self) -> None:
        """Display summary table of call log analysis."""
        from rich.table import Table

        table = Table(title="Android Call Log Summary")
        table.add_column("Category", style="cyan", no_wrap=True)
        table.add_column("Count", style="green", justify="right")

        table.add_row("Total Calls", str(len(self.calls)))
        table.add_row("Outgoing", str(getattr(self, 'outgoing_count', 0)))
        table.add_row("Incoming", str(getattr(self, 'incoming_count', 0)))
        table.add_row("Missed", str(getattr(self, 'missed_count', 0)))
        table.add_row("Rejected", str(getattr(self, 'rejected_count', 0)))
        table.add_row("Video Calls", str(getattr(self, 'video_count', 0)))

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
        rejected = getattr(self, 'rejected_count', 0)
        video = getattr(self, 'video_count', 0)

        sections = [
            {
                "heading": "Executive Summary",
                "content": (
                    f"**Total Call Records:** {total_calls}  \n"
                    f"**Outgoing Calls:** {outgoing}  \n"
                    f"**Incoming Calls:** {incoming}  \n"
                    f"**Missed Calls:** {missed}  \n"
                    f"**Rejected Calls:** {rejected}  \n"
                    f"**Video Calls:** {video}  \n"
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
                    "Type": call.get('feature_type', 'Audio'),
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
        if rejected > 0:
            forensic_notes.append(f"⚠️ {rejected} rejected calls identified")
        if video > 0:
            forensic_notes.append(f"📹 {video} video calls detected")

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
            plugin_name="AndroidCallLogAnalyzer",
            title="Android Call Log Analysis Report",
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
                    'rejected': getattr(self, 'rejected_count', 0),
                    'video': getattr(self, 'video_count', 0),
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
