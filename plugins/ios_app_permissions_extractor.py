"""
iOS Application Permissions and Usage Extractor Plugin for YaFT

This plugin extracts application permission grants, usage statistics, and
notification settings from iOS full filesystem extractions.

Based on forensic research of TCC.db, knowledgeC.db, and applicationState.plist.
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime, timedelta

from yaft.core.api import CoreAPI
from yaft.core.plugin_base import PluginBase, PluginMetadata


class iOSAppPermissionsExtractorPlugin(PluginBase):
    """
    iOS Application Permissions and Usage Extractor for forensic analysis.

    Extracts comprehensive permission grants and app usage data from iOS extractions.
    """

    # TCC service name mappings
    TCC_SERVICES = {
        'kTCCServiceAddressBook': 'Contacts',
        'kTCCServicePhotos': 'Photos',
        'kTCCServiceCamera': 'Camera',
        'kTCCServiceMicrophone': 'Microphone',
        'kTCCServiceLocation': 'Location Services',
        'kTCCServiceCalendar': 'Calendar',
        'kTCCServiceReminders': 'Reminders',
        'kTCCServiceMediaLibrary': 'Media Library',
        'kTCCServiceMotion': 'Motion & Fitness',
        'kTCCServiceSiri': 'Siri & Dictation',
        'kTCCServiceBluetooth': 'Bluetooth',
        'kTCCServiceBluetoothAlways': 'Bluetooth (Always)',
        'kTCCServiceWillow': 'HomeKit',
        'kTCCServiceUbiquity': 'iCloud',
        'kTCCServiceShareKit': 'Share',
        'kTCCServiceAppleEvents': 'Automation',
        'kTCCServiceFaceID': 'Face ID',
        'kTCCServiceFileProviderDomain': 'File Provider',
        'kTCCServiceFileProviderPresence': 'File Presence',
        'kTCCServiceFocusStatus': 'Focus Status',
        'kTCCServiceLinkedIn': 'LinkedIn',
        'kTCCServiceLiverpool': 'Health',
        'kTCCServiceTwitter': 'Twitter',
        'kTCCServiceFacebook': 'Facebook',
        'kTCCServiceSinaWeibo': 'Sina Weibo',
        'kTCCServiceTencentWeibo': 'Tencent Weibo',
        'kTCCServicePhotosAdd': 'Add Photos',
        'kTCCServiceContactsLimited': 'Limited Contacts',
        'kTCCServiceContactsFull': 'Full Contacts'
    }

    # High-risk permissions
    HIGH_RISK_PERMISSIONS = {
        'Location Services', 'Camera', 'Microphone', 'Contacts',
        'Photos', 'Calendar', 'Health'
    }

    # Permission risk weights
    PERMISSION_WEIGHTS = {
        'Location Services': 3.0,
        'Camera': 2.5,
        'Microphone': 2.5,
        'Contacts': 2.0,
        'Photos': 2.0,
        'Calendar': 1.5,
        'Reminders': 1.5,
        'Health': 3.0,
        'Motion & Fitness': 1.5,
        'Media Library': 1.0,
        'Siri & Dictation': 1.0,
        'Bluetooth': 0.5,
        'HomeKit': 1.5,
        'default': 0.5
    }

    def __init__(self, core_api: CoreAPI) -> None:
        super().__init__(core_api)
        self.apps_data: Dict[str, Dict] = {}
        self.zip_prefix = ''

    @property
    def metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name="iOSAppPermissionsExtractor",
            version="1.0.0",
            description="Extract iOS app permissions, usage statistics, and privacy data from filesystem extractions",
            author="YaFT Forensics Team",
            requires_core_version=">=0.1.0",
            dependencies=[],
            enabled=True,
        )

    def initialize(self) -> None:
        """Initialize the plugin."""
        self.core_api.log_info(f"Initializing {self.metadata.name}")
        self.apps_data = {}

    def execute(self, *args: Any, **kwargs: Any) -> Dict[str, Any]:
        """
        Execute iOS permissions extraction.

        The plugin uses the ZIP file loaded via --zip option.
        """
        # Check if ZIP file is loaded
        current_zip = self.core_api.get_current_zip()
        if not current_zip:
            self.core_api.print_error("No ZIP file loaded. Use --zip option to specify an iOS extraction ZIP.")
            return {"success": False, "error": "No ZIP file loaded"}

        self.core_api.print_success(f"Analyzing iOS extraction: {current_zip.name}")

        try:
            # Detect Cellebrite format
            self._detect_zip_structure()

            # Extract from multiple sources
            self.core_api.print_info("Parsing TCC.db for permissions...")
            permissions = self._parse_tcc_db()
            self.core_api.print_success(f"Found {len(permissions)} permission grants")

            self.core_api.print_info("Parsing knowledgeC.db for app usage...")
            usage_stats = self._parse_knowledge_db()
            self.core_api.print_success(f"Found usage data for {len(usage_stats)} apps")

            self.core_api.print_info("Parsing applicationState.plist for notifications...")
            notification_data = self._parse_application_state()
            self.core_api.print_success(f"Found notification data for {len(notification_data)} apps")

            # Merge all data
            self.core_api.print_info("Merging data from all sources...")
            self.apps_data = self._merge_app_data(permissions, usage_stats, notification_data)

            # Calculate risk scores
            self.core_api.print_info("Calculating permission risk scores...")
            self.apps_data = self._calculate_risk_scores(self.apps_data)

            self.core_api.print_success(f"Total unique applications analyzed: {len(self.apps_data)}")

            # Display summary
            self._display_summary()

            # Generate comprehensive report
            report_path = self._generate_report()
            self.core_api.print_success(f"Report generated: {report_path}")

            # Export to JSON
            output_dir = Path.cwd() / "yaft_output" / "ios_extractions"
            output_dir.mkdir(parents=True, exist_ok=True)

            json_path = output_dir / f"{current_zip.stem}_permissions.json"
            self._export_to_json(json_path)
            self.core_api.print_success(f"Permissions data exported to: {json_path}")

            return {
                "success": True,
                "total_apps": len(self.apps_data),
                "total_permissions": sum(len(app['permissions']) for app in self.apps_data.values()),
                "report_path": str(report_path),
                "json_path": str(json_path)
            }

        except Exception as e:
            self.core_api.print_error(f"Extraction failed: {e}")
            self.core_api.log_error(f"Error details: {e}")
            return {"success": False, "error": str(e)}

    def _detect_zip_structure(self) -> None:
        """Detect if ZIP has Cellebrite filesystem prefix."""
        files = self.core_api.list_zip_contents()

        for file_info in files[:20]:
            filename = file_info.filename
            if filename.startswith('filesystem1/'):
                self.zip_prefix = 'filesystem1/'
                self.core_api.print_info(f"Detected Cellebrite format: {self.zip_prefix}")
                return
            elif filename.startswith('filesystem/') and not filename.startswith('filesystem1/'):
                self.zip_prefix = 'filesystem/'
                self.core_api.print_info(f"Detected Cellebrite format: {self.zip_prefix}")
                return

    def _normalize_path(self, path: str) -> str:
        """Normalize path for ZIP access."""
        if self.zip_prefix:
            return self.zip_prefix + path
        return path

    def _parse_tcc_db(self) -> List[Dict]:
        """Parse TCC.db for permission grants."""
        db_path = 'private/var/mobile/Library/TCC/TCC.db'
        permissions = []

        try:
            # Query with fallback for different iOS schemas
            primary_query = """
                SELECT service, client, client_type, auth_value, auth_reason,
                       last_modified, indirect_object_identifier
                FROM access
                ORDER BY service, client
            """

            fallback_query = """
                SELECT service, client, client_type, auth_value, auth_reason,
                       last_modified, NULL
                FROM access
                ORDER BY service, client
            """

            rows = self.core_api.query_sqlite_from_zip(
                self._normalize_path(db_path),
                primary_query,
                fallback_query=fallback_query
            )

            for row in rows:
                service, client, client_type, auth_value, auth_reason, last_modified, indirect_object = row

                # Convert auth_value to status
                auth_status_map = {0: 'Denied', 1: 'Unknown', 2: 'Allowed', 3: 'Limited'}
                auth_status = auth_status_map.get(auth_value, 'Unknown')

                # Get human-readable service name
                service_name = self.TCC_SERVICES.get(service, service)

                # Convert timestamp
                if last_modified:
                    try:
                        core_data_epoch = datetime(2001, 1, 1)
                        timestamp = core_data_epoch + timedelta(seconds=last_modified)
                        last_modified_str = timestamp.strftime('%Y-%m-%d %H:%M:%S')
                    except:
                        last_modified_str = str(last_modified)
                else:
                    last_modified_str = 'Unknown'

                permissions.append({
                    'service': service,
                    'service_name': service_name,
                    'bundle_id': client,
                    'client_type': client_type,
                    'auth_status': auth_status,
                    'auth_value': auth_value,
                    'auth_reason': auth_reason,
                    'last_modified': last_modified_str,
                    'indirect_object': indirect_object,
                    'is_high_risk': service_name in self.HIGH_RISK_PERMISSIONS
                })

        except KeyError:
            self.core_api.log_warning("TCC.db not found in ZIP")
        except Exception as e:
            self.core_api.log_error(f"Error parsing TCC.db: {e}")

        return permissions

    def _parse_knowledge_db(self) -> Dict[str, Dict]:
        """Parse knowledgeC.db for app usage statistics."""
        db_path = 'private/var/mobile/Library/CoreDuet/Knowledge/knowledgeC.db'
        usage_stats = {}

        try:
            # Query iOS 12+ schema with fallback for older versions
            primary_query = """
                SELECT
                    ZOBJECT.ZVALUESTRING as bundle_id,
                    ZOBJECT.ZSTARTDATE as start_date,
                    ZOBJECT.ZENDDATE as end_date,
                    ZOBJECT.ZSTREAMNAME as stream_name
                FROM ZOBJECT
                WHERE ZSTREAMNAME LIKE '%/app/%'
                   OR ZSTREAMNAME = '/app/inFocus'
                   OR ZSTREAMNAME = '/app/usage'
                ORDER BY ZOBJECT.ZSTARTDATE DESC
                LIMIT 10000
            """

            fallback_query = """
                SELECT
                    ZOBJECT.ZVALUESTRING as bundle_id,
                    ZOBJECT.ZSTARTDATE as start_date,
                    ZOBJECT.ZENDDATE as end_date,
                    NULL as stream_name
                FROM ZOBJECT
                WHERE ZSTREAMNAME LIKE '%app%'
                ORDER BY ZOBJECT.ZSTARTDATE DESC
                LIMIT 10000
            """

            events = self.core_api.query_sqlite_from_zip(
                self._normalize_path(db_path),
                primary_query,
                fallback_query=fallback_query
            )

            for bundle_id, start_date, end_date, stream_name in events:
                if not bundle_id:
                    continue

                if bundle_id not in usage_stats:
                    usage_stats[bundle_id] = {
                        'bundle_id': bundle_id,
                        'total_launches': 0,
                        'total_duration_seconds': 0,
                        'first_used': None,
                        'last_used': None,
                    }

                if start_date and end_date:
                    duration = end_date - start_date

                    try:
                        core_data_epoch = datetime(2001, 1, 1)
                        start_time = core_data_epoch + timedelta(seconds=start_date)

                        usage_stats[bundle_id]['total_duration_seconds'] += duration
                        usage_stats[bundle_id]['total_launches'] += 1

                        if not usage_stats[bundle_id]['first_used']:
                            usage_stats[bundle_id]['first_used'] = start_time.strftime('%Y-%m-%d %H:%M:%S')
                        usage_stats[bundle_id]['last_used'] = start_time.strftime('%Y-%m-%d %H:%M:%S')
                    except:
                        pass

            # Calculate aggregate stats
            for bundle_id, stats in usage_stats.items():
                if stats['total_launches'] > 0:
                    stats['average_session_duration'] = int(
                        stats['total_duration_seconds'] / stats['total_launches']
                    )
                else:
                    stats['average_session_duration'] = 0

        except KeyError:
            self.core_api.log_warning("knowledgeC.db not found in ZIP")
        except Exception as e:
            self.core_api.log_error(f"Error parsing knowledgeC.db: {e}")

        return usage_stats

    def _parse_application_state(self) -> Dict[str, Dict]:
        """Parse applicationState.plist for notification settings."""
        plist_path = 'private/var/mobile/Library/SpringBoard/applicationState.plist'
        notification_data = {}

        try:
            data = self.core_api.read_plist_from_zip(self._normalize_path(plist_path))

            for bundle_id, app_data in data.items():
                if not isinstance(app_data, dict):
                    continue

                notification_data[bundle_id] = {
                    'bundle_id': bundle_id,
                    'badge_count': app_data.get('SBApplicationBadgeValue', 0),
                    'has_settings': 'SBApplicationNotificationSettings' in app_data
                }

        except KeyError:
            self.core_api.log_warning("applicationState.plist not found in ZIP")
        except Exception as e:
            self.core_api.log_error(f"Error parsing applicationState.plist: {e}")

        return notification_data

    def _merge_app_data(self, permissions: List[Dict], usage_stats: Dict[str, Dict],
                       notification_data: Dict[str, Dict]) -> Dict[str, Dict]:
        """Merge data from all sources."""
        merged = {}

        # Process permissions
        for perm in permissions:
            bundle_id = perm['bundle_id']
            if bundle_id not in merged:
                merged[bundle_id] = {
                    'bundle_id': bundle_id,
                    'permissions': [],
                    'usage_stats': {},
                    'notification_data': {}
                }
            merged[bundle_id]['permissions'].append(perm)

        # Add usage stats
        for bundle_id, stats in usage_stats.items():
            if bundle_id not in merged:
                merged[bundle_id] = {
                    'bundle_id': bundle_id,
                    'permissions': [],
                    'usage_stats': stats,
                    'notification_data': {}
                }
            else:
                merged[bundle_id]['usage_stats'] = stats

        # Add notification data
        for bundle_id, notif in notification_data.items():
            if bundle_id not in merged:
                merged[bundle_id] = {
                    'bundle_id': bundle_id,
                    'permissions': [],
                    'usage_stats': {},
                    'notification_data': notif
                }
            else:
                merged[bundle_id]['notification_data'] = notif

        return merged

    def _calculate_risk_scores(self, apps_data: Dict[str, Dict]) -> Dict[str, Dict]:
        """Calculate risk scores for each app."""
        for bundle_id, app_data in apps_data.items():
            risk_score = 0.0
            permission_count = len(app_data['permissions'])

            # Calculate based on permission types
            for perm in app_data['permissions']:
                if perm['auth_status'] == 'Allowed':
                    service_name = perm['service_name']
                    weight = self.PERMISSION_WEIGHTS.get(service_name, self.PERMISSION_WEIGHTS['default'])
                    risk_score += weight

            # Bonus risk for excessive permissions
            if permission_count > 10:
                risk_score += 2.0
            elif permission_count > 5:
                risk_score += 1.0

            # Reduce risk for frequently used apps
            usage = app_data.get('usage_stats', {})
            if usage.get('total_duration_seconds', 0) > 3600:
                risk_score *= 0.7

            app_data['risk_score'] = round(risk_score, 2)
            app_data['permission_count'] = permission_count
            app_data['high_risk_permission_count'] = sum(
                1 for p in app_data['permissions']
                if p.get('is_high_risk') and p['auth_status'] == 'Allowed'
            )

        return apps_data

    def _display_summary(self) -> None:
        """Display summary of findings."""
        from rich.table import Table

        # Top apps by permissions
        table1 = Table(title="Apps with Most Permissions (Top 10)")
        table1.add_column("Bundle ID", style="cyan", no_wrap=False)
        table1.add_column("Permissions", style="yellow", justify="right")
        table1.add_column("High Risk", style="red", justify="right")
        table1.add_column("Risk Score", style="magenta", justify="right")

        sorted_apps = sorted(
            self.apps_data.values(),
            key=lambda x: x.get('permission_count', 0),
            reverse=True
        )[:10]

        for app in sorted_apps:
            table1.add_row(
                app['bundle_id'][:50],
                str(app.get('permission_count', 0)),
                str(app.get('high_risk_permission_count', 0)),
                str(app.get('risk_score', 0))
            )

        self.core_api.console.print()
        self.core_api.console.print(table1)

        # High-risk permissions summary
        table2 = Table(title="High-Risk Permission Grants")
        table2.add_column("Permission", style="cyan")
        table2.add_column("Granted Apps", style="green", justify="right")

        permission_counts = {}
        for app in self.apps_data.values():
            for perm in app['permissions']:
                if perm.get('is_high_risk') and perm['auth_status'] == 'Allowed':
                    service = perm['service_name']
                    permission_counts[service] = permission_counts.get(service, 0) + 1

        for service, count in sorted(permission_counts.items(), key=lambda x: x[1], reverse=True):
            table2.add_row(service, str(count))

        self.core_api.console.print()
        self.core_api.console.print(table2)

    def _generate_report(self) -> Path:
        """Generate markdown report."""
        total_permissions = sum(len(app['permissions']) for app in self.apps_data.values())

        sections = [
            {
                "heading": "Extraction Summary",
                "content": f"Analyzed **{len(self.apps_data)} iOS applications** with **{total_permissions} permission grants** from the provided filesystem extraction.",
            },
        ]

        # Statistics
        stats = {
            "Total Apps": len(self.apps_data),
            "Total Permissions": total_permissions,
            "Apps with High-Risk Permissions": sum(1 for a in self.apps_data.values() if a.get('high_risk_permission_count', 0) > 0),
            "Apps with Usage Data": sum(1 for a in self.apps_data.values() if a.get('usage_stats', {}).get('total_launches', 0) > 0),
        }

        sections.append({
            "heading": "Statistics",
            "content": stats,
            "style": "table",
        })

        # Top risky apps
        risky_apps = []
        for app in sorted(self.apps_data.values(), key=lambda x: x.get('risk_score', 0), reverse=True)[:10]:
            risky_apps.append({
                "Bundle ID": app['bundle_id'],
                "Permissions": app.get('permission_count', 0),
                "High Risk": app.get('high_risk_permission_count', 0),
                "Risk Score": app.get('risk_score', 0),
            })

        sections.append({
            "heading": "⚠️ Highest Risk Applications",
            "content": risky_apps,
            "style": "table",
        })

        # High-risk permission summary
        permission_summary = {}
        for app in self.apps_data.values():
            for perm in app['permissions']:
                if perm.get('is_high_risk') and perm['auth_status'] == 'Allowed':
                    service = perm['service_name']
                    permission_summary[service] = permission_summary.get(service, 0) + 1

        sections.append({
            "heading": "High-Risk Permission Distribution",
            "content": permission_summary,
            "style": "table",
        })

        metadata = {
            "Total Applications": len(self.apps_data),
            "Total Permissions": total_permissions,
            "ZIP File": self.core_api.get_current_zip().name if self.core_api.get_current_zip() else "Unknown",
        }

        return self.core_api.generate_report(
            plugin_name="iOSAppPermissionsExtractor",
            title="iOS Application Permissions & Privacy Analysis Report",
            sections=sections,
            metadata=metadata,
        )

    def _export_to_json(self, output_path: Path) -> None:
        """Export data to JSON file."""
        summary = {
            'extraction_metadata': {
                'extraction_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'total_apps_analyzed': len(self.apps_data),
                'total_permissions': sum(len(app['permissions']) for app in self.apps_data.values())
            },
            'apps': self.apps_data
        }

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)

    def cleanup(self) -> None:
        """Clean up temporary resources."""
        self.core_api.log_info(f"Cleaning up {self.metadata.name}")
