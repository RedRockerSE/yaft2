"""
Android Application Information Extractor Plugin for YaFT

This plugin extracts application metadata from Android full filesystem extractions,
including package names, app versions, installation dates, APK paths, and app metadata.

Supports both Cellebrite and GrayKey extraction formats.

Based on forensic research of Android package manager structures and databases.
"""

import re
from pathlib import Path
from typing import Any, Dict, List, Optional

from yaft.core.api import CoreAPI
from yaft.core.plugin_base import PluginBase, PluginMetadata


class AndroidAppInfoExtractorPlugin(PluginBase):
    """
    Android Application Information Extractor for forensic analysis.

    Extracts comprehensive app metadata from Android filesystem extractions including
    packages.xml, installed apps databases, and filesystem enumeration.
    """

    def __init__(self, core_api: CoreAPI) -> None:
        super().__init__(core_api)
        self.apps: List[Dict[str, Any]] = []
        self.zip_prefix = ''
        self.extraction_type = 'unknown'
        self.errors: List[Dict[str, str]] = []

    @property
    def metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name="AndroidAppInfoExtractor",
            version="1.0.0",
            description=(
                "Extract Android app package names, versions, and metadata from filesystem extractions"
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
        self.apps = []
        self.errors = []

    def execute(self, *args: Any, **kwargs: Any) -> Dict[str, Any]:
        """
        Execute Android app information extraction.

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
            self.core_api.print_info("Parsing packages.xml...")
            packages_xml_apps = self._parse_packages_xml()
            self.core_api.print_success(
                f"Found {len(packages_xml_apps)} apps in packages.xml"
            )

            self.core_api.print_info("Parsing packages.list...")
            packages_list_apps = self._parse_packages_list()
            self.core_api.print_success(
                f"Found {len(packages_list_apps)} apps in packages.list"
            )

            self.core_api.print_info("Parsing usage stats database...")
            usage_stats_apps = self._parse_usage_stats()
            self.core_api.print_success(
                f"Found {len(usage_stats_apps)} apps in usage stats"
            )

            # Merge data
            self.core_api.print_info("Merging data from all sources...")
            self.apps = self._merge_app_data(
                packages_xml_apps, packages_list_apps, usage_stats_apps
            )

            self.core_api.print_success(f"Total unique applications found: {len(self.apps)}")

            # Categorize apps
            self._categorize_apps()

            # Display summary
            self._display_summary()

            # Generate report
            report_path = self._generate_report()
            self.core_api.print_success(f"Report generated: {report_path}")

            # Export to JSON
            output_dir = self.core_api.get_case_output_dir("android_extractions")
            output_dir.mkdir(parents=True, exist_ok=True)

            json_path = output_dir / f"{current_zip.stem}_apps.json"
            self._export_to_json(json_path)
            self.core_api.print_success(f"App data exported to: {json_path}")

            return {
                "success": True,
                "total_apps": len(self.apps),
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

    def _parse_packages_xml(self) -> Dict[str, Dict[str, Any]]:
        """Parse packages.xml for comprehensive app information."""
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

                # Extract basic package info
                app_data = {
                    'package_name': package_name,
                    'code_path': package.get('codePath'),
                    'native_library_path': package.get('nativeLibraryPath'),
                    'flags': package.get('flags'),
                    'ft': package.get('ft'),  # First install time
                    'it': package.get('it'),  # Install time
                    'ut': package.get('ut'),  # Update time
                    'version_code': package.get('version'),
                    'version_name': None,
                    'user_id': package.get('userId'),
                    'shared_user_id': package.get('sharedUserId'),
                    'installer': package.get('installer'),
                    'source': 'packages.xml',
                }

                # Parse perms (granted permissions)
                permissions = []
                for perm in package.findall('.//perms/item'):
                    perm_name = perm.get('name')
                    if perm_name:
                        permissions.append(perm_name)
                app_data['granted_permissions'] = permissions

                # Check if system app
                flags_int = int(package.get('flags', '0'))
                app_data['is_system_app'] = bool(flags_int & 0x00000001)
                app_data['is_updated_system_app'] = bool(flags_int & 0x00000080)

                apps[package_name] = app_data

        except KeyError:
            self.errors.append({
                'source': packages_xml_path,
                'error': 'packages.xml not found in ZIP',
            })
            self.core_api.log_warning("packages.xml not found in ZIP")
        except Exception as e:
            self.errors.append({'source': packages_xml_path, 'error': str(e)})
            self.core_api.log_error(f"Error parsing packages.xml: {e}")

        return apps

    def _parse_packages_list(self) -> Dict[str, Dict[str, Any]]:
        """Parse packages.list for supplementary app information."""
        packages_list_path = 'data/system/packages.list'
        apps = {}

        try:
            content = self.core_api.read_zip_file_text(
                self._normalize_path(packages_list_path)
            )

            for line in content.split('\n'):
                line = line.strip()
                if not line or line.startswith('#'):
                    continue

                parts = line.split()
                if len(parts) >= 4:
                    package_name = parts[0]
                    user_id = parts[1]
                    debug_flag = parts[2]
                    data_dir = parts[3]
                    seinfo = parts[4] if len(parts) > 4 else None

                    apps[package_name] = {
                        'package_name': package_name,
                        'user_id': user_id,
                        'debuggable': debug_flag == '1',
                        'data_dir': data_dir,
                        'seinfo': seinfo,
                        'source': 'packages.list',
                    }

        except (KeyError, Exception) as e:
            self.errors.append({'source': packages_list_path, 'error': str(e)})
            self.core_api.log_warning(f"Could not parse packages.list: {e}")

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

                apps[package_name] = {
                    'package_name': package_name,
                    'last_time_used': last_time_used,
                    'total_time_used': total_time_used,
                    'source': 'usage_stats',
                }

        except (KeyError, Exception) as e:
            # Usage stats may not always be available
            self.core_api.log_info(f"Usage stats not available: {e}")

        return apps

    def _merge_app_data(
        self,
        packages_xml: Dict[str, Dict[str, Any]],
        packages_list: Dict[str, Dict[str, Any]],
        usage_stats: Dict[str, Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """Merge data from multiple sources."""
        merged = {}

        # Start with packages.xml (most complete)
        for package_name, data in packages_xml.items():
            merged[package_name] = data.copy()

        # Add packages.list data
        for package_name, data in packages_list.items():
            if package_name not in merged:
                merged[package_name] = data.copy()
            else:
                # Supplement existing data
                for key, value in data.items():
                    if key not in merged[package_name] or not merged[package_name][key]:
                        merged[package_name][key] = value

        # Add usage stats
        for package_name, data in usage_stats.items():
            if package_name not in merged:
                merged[package_name] = data.copy()
            else:
                merged[package_name]['last_time_used'] = data.get('last_time_used')
                merged[package_name]['total_time_used'] = data.get('total_time_used')

        return list(merged.values())

    def _categorize_apps(self) -> None:
        """Categorize apps by type (system, user, etc.)."""
        for app in self.apps:
            package_name = app.get('package_name', '')

            # Detect app categories
            if app.get('is_system_app'):
                app['category'] = 'system'
            elif package_name.startswith('com.google.'):
                app['category'] = 'google'
            elif package_name.startswith('com.android.'):
                app['category'] = 'android_system'
            elif package_name.startswith('com.samsung.'):
                app['category'] = 'samsung'
            elif package_name.startswith('com.facebook.'):
                app['category'] = 'facebook'
            elif package_name.startswith('com.whatsapp'):
                app['category'] = 'messaging'
            elif any(
                x in package_name
                for x in ['telegram', 'signal', 'messenger', 'wechat', 'line']
            ):
                app['category'] = 'messaging'
            elif any(x in package_name for x in ['browser', 'chrome', 'firefox', 'opera']):
                app['category'] = 'browser'
            elif any(x in package_name for x in ['game', 'play.games']):
                app['category'] = 'games'
            else:
                app['category'] = 'user_installed'

            # Detect potentially suspicious apps
            if app.get('debuggable'):
                app['suspicious_flag'] = 'debuggable'
            elif '/tmp/' in str(app.get('code_path', '')):
                app['suspicious_flag'] = 'temp_location'
            elif not app.get('installer'):
                app['suspicious_flag'] = 'no_installer'

    def _display_summary(self) -> None:
        """Display summary table of extracted app information."""
        from rich.table import Table

        # Category statistics
        categories = {}
        for app in self.apps:
            cat = app.get('category', 'unknown')
            categories[cat] = categories.get(cat, 0) + 1

        table = Table(title="Android Application Summary")
        table.add_column("Category", style="cyan", no_wrap=True)
        table.add_column("Count", style="green", justify="right")

        for cat, count in sorted(categories.items(), key=lambda x: x[1], reverse=True):
            table.add_row(cat.replace('_', ' ').title(), str(count))

        table.add_row("[bold]Total[/bold]", f"[bold]{len(self.apps)}[/bold]")

        self.core_api.console.print()
        self.core_api.console.print(table)

        # Show suspicious apps
        suspicious_apps = [app for app in self.apps if app.get('suspicious_flag')]
        if suspicious_apps:
            self.core_api.print_warning(
                f"Found {len(suspicious_apps)} potentially suspicious apps"
            )

        if self.errors:
            self.core_api.print_warning(
                f"Encountered {len(self.errors)} errors during extraction (see report for details)"
            )

    def _generate_report(self) -> Path:
        """Generate markdown report."""
        # Summary statistics
        system_apps = sum(1 for app in self.apps if app.get('category') == 'system')
        user_apps = sum(1 for app in self.apps if app.get('category') == 'user_installed')
        suspicious_apps = [app for app in self.apps if app.get('suspicious_flag')]

        sections = [
            {
                "heading": "Executive Summary",
                "content": (
                    f"**Total Applications:** {len(self.apps)}  \n"
                    f"**System Apps:** {system_apps}  \n"
                    f"**User-Installed Apps:** {user_apps}  \n"
                    f"**Suspicious Apps:** {len(suspicious_apps)}  \n"
                ),
            },
        ]

        # Category breakdown
        categories = {}
        for app in self.apps:
            cat = app.get('category', 'unknown')
            categories[cat] = categories.get(cat, 0) + 1

        sections.append({
            "heading": "Apps by Category",
            "content": {k.replace('_', ' ').title(): v for k, v in categories.items()},
            "style": "table",
        })

        # User-installed apps
        user_installed = [
            app
            for app in self.apps
            if app.get('category') == 'user_installed'
        ][:50]  # Limit to 50

        if user_installed:
            user_table = []
            for app in user_installed:
                user_table.append({
                    "Package Name": app.get('package_name', 'N/A'),
                    "Version": app.get('version_code', 'N/A'),
                    "Installer": app.get('installer', 'Unknown'),
                    "Code Path": app.get('code_path', 'N/A'),
                })
            sections.append({
                "heading": "User-Installed Applications",
                "content": user_table,
                "style": "table",
            })

        # Messaging apps
        messaging_apps = [app for app in self.apps if app.get('category') == 'messaging']
        if messaging_apps:
            msg_table = []
            for app in messaging_apps:
                msg_table.append({
                    "Package Name": app.get('package_name', 'N/A'),
                    "Version": app.get('version_code', 'N/A'),
                })
            sections.append({
                "heading": "Messaging Applications",
                "content": msg_table,
                "style": "table",
            })

        # Suspicious apps
        if suspicious_apps:
            susp_table = []
            for app in suspicious_apps:
                susp_table.append({
                    "Package Name": app.get('package_name', 'N/A'),
                    "Suspicious Flag": app.get('suspicious_flag', 'N/A'),
                    "Code Path": app.get('code_path', 'N/A'),
                })
            sections.append({
                "heading": "Potentially Suspicious Applications",
                "content": susp_table,
                "style": "table",
            })

        # Forensic notes
        forensic_notes = []
        if suspicious_apps:
            forensic_notes.append(
                f"⚠️ {len(suspicious_apps)} applications flagged for review"
            )
        if any(app.get('debuggable') for app in self.apps):
            debuggable_count = sum(1 for app in self.apps if app.get('debuggable'))
            forensic_notes.append(
                f"⚠️ {debuggable_count} applications have debugging enabled"
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
            "Total Applications": str(len(self.apps)),
            "ZIP File": self.core_api.get_current_zip().name
            if self.core_api.get_current_zip()
            else "Unknown",
        }

        return self.core_api.generate_report(
            plugin_name="AndroidAppInfoExtractor",
            title="Android Application Information Extraction Report",
            sections=sections,
            metadata=metadata,
        )

    def _export_to_json(self, output_path: Path) -> None:
        """Export app data to JSON file using CoreAPI method."""
        self.core_api.export_plugin_data_to_json(
            output_path=output_path,
            plugin_name=self.metadata.name,
            plugin_version=self.metadata.version,
            data={'applications': self.apps},
            extraction_type=self.extraction_type,
            errors=self.errors,
        )

    def cleanup(self) -> None:
        """Clean up temporary resources."""
        self.core_api.log_info(f"Cleaning up {self.metadata.name}")
