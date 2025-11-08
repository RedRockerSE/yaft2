"""
Android Application Permissions and Usage Extractor Plugin for YaFT

This plugin extracts application runtime permissions, usage statistics, and
privacy-related data from Android full filesystem extractions.

Supports both Cellebrite and GrayKey extraction formats.

Based on forensic research of Android permission systems and usage databases.
"""

import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from yaft.core.api import CoreAPI
from yaft.core.plugin_base import PluginBase, PluginMetadata


class AndroidAppPermissionsExtractorPlugin(PluginBase):
    """
    Android Application Permissions and Usage Extractor for forensic analysis.

    Extracts comprehensive permission grants, runtime permissions, usage statistics,
    and privacy data from Android filesystem extractions.
    """

    # High-risk Android permissions
    HIGH_RISK_PERMISSIONS = {
        'android.permission.ACCESS_FINE_LOCATION',
        'android.permission.ACCESS_COARSE_LOCATION',
        'android.permission.ACCESS_BACKGROUND_LOCATION',
        'android.permission.CAMERA',
        'android.permission.RECORD_AUDIO',
        'android.permission.READ_CONTACTS',
        'android.permission.WRITE_CONTACTS',
        'android.permission.READ_CALL_LOG',
        'android.permission.WRITE_CALL_LOG',
        'android.permission.READ_SMS',
        'android.permission.SEND_SMS',
        'android.permission.RECEIVE_SMS',
        'android.permission.READ_CALENDAR',
        'android.permission.WRITE_CALENDAR',
        'android.permission.BODY_SENSORS',
        'android.permission.READ_PHONE_STATE',
        'android.permission.CALL_PHONE',
        'android.permission.READ_EXTERNAL_STORAGE',
        'android.permission.WRITE_EXTERNAL_STORAGE',
        'android.permission.ACCESS_MEDIA_LOCATION',
    }

    # Permission risk weights for scoring
    PERMISSION_WEIGHTS = {
        'android.permission.ACCESS_FINE_LOCATION': 3.0,
        'android.permission.ACCESS_BACKGROUND_LOCATION': 3.5,
        'android.permission.CAMERA': 2.5,
        'android.permission.RECORD_AUDIO': 2.5,
        'android.permission.READ_CONTACTS': 2.0,
        'android.permission.WRITE_CONTACTS': 2.0,
        'android.permission.READ_SMS': 2.5,
        'android.permission.SEND_SMS': 2.5,
        'android.permission.READ_CALL_LOG': 2.0,
        'android.permission.CALL_PHONE': 2.0,
        'android.permission.BODY_SENSORS': 2.0,
        'android.permission.READ_CALENDAR': 1.5,
        'android.permission.ACCESS_COARSE_LOCATION': 2.0,
        'android.permission.READ_PHONE_STATE': 1.5,
        'android.permission.READ_EXTERNAL_STORAGE': 1.0,
        'android.permission.WRITE_EXTERNAL_STORAGE': 1.5,
        'default': 0.5,
    }

    # Permission categories
    PERMISSION_CATEGORIES = {
        'location': [
            'ACCESS_FINE_LOCATION',
            'ACCESS_COARSE_LOCATION',
            'ACCESS_BACKGROUND_LOCATION',
        ],
        'camera': ['CAMERA'],
        'microphone': ['RECORD_AUDIO'],
        'contacts': ['READ_CONTACTS', 'WRITE_CONTACTS', 'GET_ACCOUNTS'],
        'phone': [
            'READ_PHONE_STATE',
            'READ_CALL_LOG',
            'WRITE_CALL_LOG',
            'CALL_PHONE',
            'READ_PHONE_NUMBERS',
        ],
        'sms': [
            'READ_SMS',
            'SEND_SMS',
            'RECEIVE_SMS',
            'RECEIVE_MMS',
            'RECEIVE_WAP_PUSH',
        ],
        'calendar': ['READ_CALENDAR', 'WRITE_CALENDAR'],
        'storage': [
            'READ_EXTERNAL_STORAGE',
            'WRITE_EXTERNAL_STORAGE',
            'ACCESS_MEDIA_LOCATION',
        ],
        'sensors': ['BODY_SENSORS'],
    }

    def __init__(self, core_api: CoreAPI) -> None:
        super().__init__(core_api)
        self.apps_data: Dict[str, Dict[str, Any]] = {}
        self.zip_prefix = ''
        self.extraction_type = 'unknown'
        self.errors: List[Dict[str, str]] = []

    @property
    def metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name="AndroidAppPermissionsExtractor",
            version="1.0.0",
            description=(
                "Extract Android app runtime permissions, usage statistics, and privacy data"
            ),
            author="YaFT Forensics Team",
            requires_core_version=">=0.1.0",
            dependencies=[],
            enabled=True,
            target_os=["android"],
        )

    def initialize(self) -> None:
        """Initialize the plugin."""
        self.core_api.log_info(f"Initializing {self.metadata.name}")
        self.apps_data = {}
        self.errors = []

    def execute(self, *args: Any, **kwargs: Any) -> Dict[str, Any]:
        """
        Execute Android permissions extraction.

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

            # Extract from multiple sources
            self.core_api.print_info("Parsing packages.xml for declared permissions...")
            declared_perms = self._parse_declared_permissions()
            self.core_api.print_success(
                f"Found declared permissions for {len(declared_perms)} apps"
            )

            self.core_api.print_info("Parsing runtime_permissions.xml...")
            runtime_perms = self._parse_runtime_permissions()
            self.core_api.print_success(
                f"Found runtime permissions for {len(runtime_perms)} apps"
            )

            self.core_api.print_info("Parsing app ops for permission usage...")
            app_ops = self._parse_app_ops()
            self.core_api.print_success(f"Found app ops data for {len(app_ops)} apps")

            self.core_api.print_info("Parsing usage stats database...")
            usage_stats = self._parse_usage_stats()
            self.core_api.print_success(
                f"Found usage statistics for {len(usage_stats)} apps"
            )

            # Merge all data
            self.core_api.print_info("Merging data from all sources...")
            self.apps_data = self._merge_app_data(
                declared_perms, runtime_perms, app_ops, usage_stats
            )

            # Calculate risk scores
            self.core_api.print_info("Calculating permission risk scores...")
            self._calculate_risk_scores()

            self.core_api.print_success(
                f"Total unique applications analyzed: {len(self.apps_data)}"
            )

            # Display summary
            self._display_summary()

            # Generate report
            report_path = self._generate_report()
            self.core_api.print_success(f"Report generated: {report_path}")

            # Export to JSON
            output_dir = self.core_api.get_case_output_dir("android_extractions")
            output_dir.mkdir(parents=True, exist_ok=True)

            json_path = output_dir / f"{current_zip.stem}_permissions.json"
            self._export_to_json(json_path)
            self.core_api.print_success(f"Permissions data exported to: {json_path}")

            return {
                "success": True,
                "total_apps": len(self.apps_data),
                "total_permissions": sum(
                    len(app.get('granted_permissions', []))
                    for app in self.apps_data.values()
                ),
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

    def _parse_declared_permissions(self) -> Dict[str, Dict[str, Any]]:
        """Parse packages.xml for declared permissions."""
        packages_xml_path = 'data/system/packages.xml'
        apps = {}

        try:
            root = self.core_api.read_xml_from_zip(
                self._normalize_path(packages_xml_path)
            )

            # Parse <package> elements
            for package in root.findall('.//package'):
                package_name = package.get('name')
                if not package_name:
                    continue

                # Parse declared permissions (from manifest)
                requested_permissions = []
                for perm in package.findall('.//perms/item'):
                    perm_name = perm.get('name')
                    if perm_name:
                        requested_permissions.append(perm_name)

                # Parse granted permissions
                granted_permissions = []
                for perm in package.findall('.//perms/item[@granted="true"]'):
                    perm_name = perm.get('name')
                    if perm_name:
                        granted_permissions.append(perm_name)

                apps[package_name] = {
                    'package_name': package_name,
                    'requested_permissions': requested_permissions,
                    'granted_permissions': granted_permissions,
                }

        except (KeyError, Exception) as e:
            self.errors.append({'source': packages_xml_path, 'error': str(e)})
            self.core_api.log_warning(f"Could not parse packages.xml: {e}")

        return apps

    def _parse_runtime_permissions(self) -> Dict[str, Dict[str, Any]]:
        """Parse runtime_permissions.xml for runtime permission grants."""
        runtime_perms_path = 'data/system/users/0/runtime-permissions.xml'
        apps = {}

        try:
            root = self.core_api.read_xml_from_zip(
                self._normalize_path(runtime_perms_path)
            )

            # Parse <pkg> elements
            for pkg in root.findall('.//pkg'):
                package_name = pkg.get('name')
                if not package_name:
                    continue

                runtime_perms = []
                for perm in pkg.findall('.//item'):
                    perm_name = perm.get('name')
                    granted = perm.get('granted', 'false') == 'true'
                    flags = perm.get('flags', '0')

                    if granted and perm_name:
                        runtime_perms.append({
                            'permission': perm_name,
                            'granted': granted,
                            'flags': flags,
                        })

                apps[package_name] = {
                    'package_name': package_name,
                    'runtime_permissions': runtime_perms,
                }

        except (KeyError, Exception) as e:
            self.errors.append({'source': runtime_perms_path, 'error': str(e)})
            self.core_api.log_warning(f"Could not parse runtime-permissions.xml: {e}")

        return apps

    def _parse_app_ops(self) -> Dict[str, Dict[str, Any]]:
        """Parse appops.xml for permission usage tracking."""
        appops_path = 'data/system/appops.xml'
        apps = {}

        try:
            root = self.core_api.read_xml_from_zip(self._normalize_path(appops_path))

            # Parse <pkg> elements
            for pkg in root.findall('.//pkg'):
                package_name = pkg.get('n')  # 'n' attribute in appops
                if not package_name:
                    continue

                app_ops = []
                for uid in pkg.findall('.//uid'):
                    uid_val = uid.get('n')
                    for op in uid.findall('.//op'):
                        op_name = op.get('n')
                        mode = op.get('m')  # Mode: 0=allowed, 1=ignored, 2=errored
                        time = op.get('t')  # Last access time
                        reject_time = op.get('r')  # Last reject time
                        duration = op.get('d')  # Duration

                        app_ops.append({
                            'operation': self._map_app_op(op_name),
                            'mode': self._map_op_mode(mode),
                            'last_access_time': time,
                            'last_reject_time': reject_time,
                            'duration': duration,
                        })

                apps[package_name] = {'package_name': package_name, 'app_ops': app_ops}

        except (KeyError, Exception) as e:
            self.errors.append({'source': appops_path, 'error': str(e)})
            self.core_api.log_warning(f"Could not parse appops.xml: {e}")

        return apps

    def _parse_usage_stats(self) -> Dict[str, Dict[str, Any]]:
        """Parse usage stats database for app usage information."""
        usage_stats_path = 'data/system/usagestats/0/usage-history.xml'
        apps = {}

        try:
            root = self.core_api.read_xml_from_zip(
                self._normalize_path(usage_stats_path)
            )

            # Parse app usage entries
            for app in root.findall('.//app'):
                package_name = app.get('package')
                if not package_name:
                    continue

                last_time_used = app.get('lastTimeUsed')
                total_time_used = app.get('totalTimeInForeground')
                launch_count = app.get('launchCount')

                apps[package_name] = {
                    'package_name': package_name,
                    'last_time_used': last_time_used,
                    'total_time_used': total_time_used,
                    'launch_count': launch_count,
                }

        except (KeyError, Exception) as e:
            # Usage stats may not always be available
            self.core_api.log_info(f"Usage stats not available: {e}")

        return apps

    def _map_app_op(self, op_code: Optional[str]) -> str:
        """Map app op code to readable name."""
        if not op_code:
            return 'Unknown'

        op_map = {
            '0': 'COARSE_LOCATION',
            '1': 'FINE_LOCATION',
            '2': 'GPS',
            '26': 'CAMERA',
            '27': 'RECORD_AUDIO',
            '4': 'READ_CONTACTS',
            '5': 'WRITE_CONTACTS',
            '6': 'READ_CALL_LOG',
            '7': 'WRITE_CALL_LOG',
            '8': 'READ_CALENDAR',
            '9': 'WRITE_CALENDAR',
            '14': 'READ_SMS',
            '15': 'WRITE_SMS',
            '16': 'RECEIVE_SMS',
            '59': 'ACCESS_MEDIA_LOCATION',
        }

        return op_map.get(op_code, f'OP_{op_code}')

    def _map_op_mode(self, mode: Optional[str]) -> str:
        """Map app op mode to readable status."""
        if not mode:
            return 'Unknown'

        mode_map = {'0': 'Allowed', '1': 'Ignored', '2': 'Errored', '3': 'Default'}

        return mode_map.get(mode, f'Mode_{mode}')

    def _merge_app_data(
        self,
        declared: Dict[str, Dict[str, Any]],
        runtime: Dict[str, Dict[str, Any]],
        app_ops: Dict[str, Dict[str, Any]],
        usage: Dict[str, Dict[str, Any]],
    ) -> Dict[str, Dict[str, Any]]:
        """Merge data from multiple sources."""
        merged = {}

        # Start with declared permissions
        for package_name, data in declared.items():
            merged[package_name] = data.copy()

        # Add runtime permissions
        for package_name, data in runtime.items():
            if package_name not in merged:
                merged[package_name] = {'package_name': package_name}
            merged[package_name]['runtime_permissions'] = data.get('runtime_permissions', [])

        # Add app ops
        for package_name, data in app_ops.items():
            if package_name not in merged:
                merged[package_name] = {'package_name': package_name}
            merged[package_name]['app_ops'] = data.get('app_ops', [])

        # Add usage stats
        for package_name, data in usage.items():
            if package_name not in merged:
                merged[package_name] = {'package_name': package_name}
            merged[package_name].update({
                'last_time_used': data.get('last_time_used'),
                'total_time_used': data.get('total_time_used'),
                'launch_count': data.get('launch_count'),
            })

        return merged

    def _calculate_risk_scores(self) -> None:
        """Calculate risk scores based on permissions."""
        for package_name, app_data in self.apps_data.items():
            risk_score = 0.0
            high_risk_perms = []

            # Score granted permissions
            granted = app_data.get('granted_permissions', [])
            for perm in granted:
                weight = self.PERMISSION_WEIGHTS.get(perm, self.PERMISSION_WEIGHTS['default'])
                risk_score += weight

                if perm in self.HIGH_RISK_PERMISSIONS:
                    high_risk_perms.append(perm)

            # Boost score for apps with many high-risk permissions
            if len(high_risk_perms) >= 3:
                risk_score *= 1.5

            app_data['risk_score'] = round(risk_score, 2)
            app_data['high_risk_permissions'] = high_risk_perms
            app_data['risk_level'] = self._categorize_risk(risk_score)

    def _categorize_risk(self, risk_score: float) -> str:
        """Categorize risk level based on score."""
        if risk_score >= 10.0:
            return 'Critical'
        elif risk_score >= 7.0:
            return 'High'
        elif risk_score >= 4.0:
            return 'Medium'
        elif risk_score >= 2.0:
            return 'Low'
        else:
            return 'Minimal'

    def _display_summary(self) -> None:
        """Display summary table of permission analysis."""
        from rich.table import Table

        # Calculate statistics
        high_risk_apps = [
            app for app in self.apps_data.values() if app.get('risk_level') in ['High', 'Critical']
        ]

        # Permission category statistics
        category_stats = {}
        for category in self.PERMISSION_CATEGORIES.keys():
            count = sum(
                1
                for app in self.apps_data.values()
                if any(
                    perm_suffix in perm
                    for perm in app.get('granted_permissions', [])
                    for perm_suffix in self.PERMISSION_CATEGORIES[category]
                )
            )
            category_stats[category] = count

        table = Table(title="Android App Permissions Summary")
        table.add_column("Permission Category", style="cyan", no_wrap=True)
        table.add_column("Apps with Access", style="green", justify="right")

        for category, count in sorted(
            category_stats.items(), key=lambda x: x[1], reverse=True
        ):
            if count > 0:
                table.add_row(category.title(), str(count))

        self.core_api.console.print()
        self.core_api.console.print(table)

        # Risk summary
        if high_risk_apps:
            self.core_api.print_warning(
                f"Found {len(high_risk_apps)} apps with HIGH or CRITICAL risk levels"
            )

        if self.errors:
            self.core_api.print_warning(
                f"Encountered {len(self.errors)} errors during extraction (see report for details)"
            )

    def _generate_report(self) -> Path:
        """Generate markdown report."""
        # Statistics
        high_risk_apps = [
            app
            for app in self.apps_data.values()
            if app.get('risk_level') in ['High', 'Critical']
        ]
        location_apps = [
            app
            for app in self.apps_data.values()
            if any('LOCATION' in perm for perm in app.get('granted_permissions', []))
        ]
        camera_apps = [
            app
            for app in self.apps_data.values()
            if any('CAMERA' in perm for perm in app.get('granted_permissions', []))
        ]

        sections = [
            {
                "heading": "Executive Summary",
                "content": (
                    f"**Total Applications Analyzed:** {len(self.apps_data)}  \n"
                    f"**High/Critical Risk Apps:** {len(high_risk_apps)}  \n"
                    f"**Apps with Location Access:** {len(location_apps)}  \n"
                    f"**Apps with Camera Access:** {len(camera_apps)}  \n"
                ),
            },
        ]

        # High-risk apps
        if high_risk_apps:
            high_risk_table = []
            for app in sorted(high_risk_apps, key=lambda x: x.get('risk_score', 0), reverse=True)[
                :20
            ]:
                high_risk_table.append({
                    "Package Name": app.get('package_name', 'N/A'),
                    "Risk Level": app.get('risk_level', 'N/A'),
                    "Risk Score": str(app.get('risk_score', 0)),
                    "High-Risk Permissions": str(len(app.get('high_risk_permissions', []))),
                })
            sections.append({
                "heading": "High-Risk Applications",
                "content": high_risk_table,
                "style": "table",
            })

        # Location access apps
        if location_apps:
            location_table = []
            for app in location_apps[:20]:
                location_perms = [
                    p for p in app.get('granted_permissions', []) if 'LOCATION' in p
                ]
                location_table.append({
                    "Package Name": app.get('package_name', 'N/A'),
                    "Location Permissions": ', '.join(
                        [p.split('.')[-1] for p in location_perms]
                    ),
                    "Risk Level": app.get('risk_level', 'N/A'),
                })
            sections.append({
                "heading": "Apps with Location Access",
                "content": location_table,
                "style": "table",
            })

        # Camera/Microphone access
        camera_mic_apps = [
            app
            for app in self.apps_data.values()
            if any(p in app.get('granted_permissions', []) for p in [
                'android.permission.CAMERA',
                'android.permission.RECORD_AUDIO'
            ])
        ]
        if camera_mic_apps:
            cam_mic_table = []
            for app in camera_mic_apps[:20]:
                perms = app.get('granted_permissions', [])
                has_camera = 'android.permission.CAMERA' in perms
                has_mic = 'android.permission.RECORD_AUDIO' in perms
                cam_mic_table.append({
                    "Package Name": app.get('package_name', 'N/A'),
                    "Camera": "Yes" if has_camera else "No",
                    "Microphone": "Yes" if has_mic else "No",
                    "Risk Level": app.get('risk_level', 'N/A'),
                })
            sections.append({
                "heading": "Apps with Camera/Microphone Access",
                "content": cam_mic_table,
                "style": "table",
            })

        # Forensic notes
        forensic_notes = []
        if high_risk_apps:
            forensic_notes.append(
                f"⚠️ {len(high_risk_apps)} applications have HIGH or CRITICAL risk scores"
            )
        if location_apps:
            background_location = [
                app
                for app in location_apps
                if 'android.permission.ACCESS_BACKGROUND_LOCATION'
                in app.get('granted_permissions', [])
            ]
            if background_location:
                forensic_notes.append(
                    f"⚠️ {len(background_location)} apps have background location access"
                )

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
            "Total Applications": str(len(self.apps_data)),
            "High-Risk Apps": str(len(high_risk_apps)),
            "ZIP File": self.core_api.get_current_zip().name
            if self.core_api.get_current_zip()
            else "Unknown",
        }

        return self.core_api.generate_report(
            plugin_name="AndroidAppPermissionsExtractor",
            title="Android Application Permissions Analysis Report",
            sections=sections,
            metadata=metadata,
        )

    def _export_to_json(self, output_path: Path) -> None:
        """Export permissions data to JSON file using CoreAPI method."""
        self.core_api.export_plugin_data_to_json(
            output_path=output_path,
            plugin_name=self.metadata.name,
            plugin_version=self.metadata.version,
            data={'applications': list(self.apps_data.values())},
            extraction_type=self.extraction_type,
            errors=self.errors,
        )

    def cleanup(self) -> None:
        """Clean up temporary resources."""
        self.core_api.log_info(f"Cleaning up {self.metadata.name}")
