"""
iOS Application GUID and Bundle ID Extractor Plugin for YaFT

This plugin extracts application metadata from iOS full filesystem extractions,
including bundle identifiers, container GUIDs, and app information.

Based on forensic research of iOS file structures and databases.
"""

import re
from pathlib import Path
from typing import Any, Dict, List, Optional

from yaft.core.api import CoreAPI
from yaft.core.plugin_base import PluginBase, PluginMetadata


class iOSAppGUIDExtractorPlugin(PluginBase):
    """
    iOS Application GUID and Bundle ID Extractor for forensic analysis.

    Extracts comprehensive app metadata from iOS filesystem extractions or ZIP files.
    """

    def __init__(self, core_api: CoreAPI) -> None:
        super().__init__(core_api)
        self.apps: List[Dict] = []
        self.zip_prefix = ''

    @property
    def metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name="iOSAppGUIDExtractor",
            version="1.0.0",
            description="Extract iOS app GUIDs, bundle IDs, and metadata from filesystem extractions",
            author="YaFT Forensics Team",
            requires_core_version=">=0.1.0",
            dependencies=[],
            enabled=True,
            target_os=["ios"],
        )

    def initialize(self) -> None:
        """Initialize the plugin."""
        self.core_api.log_info(f"Initializing {self.metadata.name}")
        self.apps = []

    def execute(self, *args: Any, **kwargs: Any) -> Dict[str, Any]:
        """
        Execute iOS app extraction.

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
            self.core_api.print_info("Parsing MobileInstallation.plist...")
            mobile_installation_apps = self._parse_mobile_installation()
            self.core_api.print_success(f"Found {len(mobile_installation_apps)} apps in MobileInstallation.plist")

            self.core_api.print_info("Parsing applicationState.db...")
            app_state_bundle_ids = self._parse_application_state_db()
            self.core_api.print_success(f"Found {len(app_state_bundle_ids)} bundle IDs in applicationState.db")

            self.core_api.print_info("Enumerating filesystem for .app bundles...")
            filesystem_apps = self._enumerate_filesystem()
            self.core_api.print_success(f"Found {len(filesystem_apps)} apps via filesystem enumeration")

            # Merge data
            self.core_api.print_info("Merging data from all sources...")
            self.apps = self._merge_app_data(
                mobile_installation_apps,
                app_state_bundle_ids,
                filesystem_apps
            )

            self.core_api.print_success(f"Total unique applications found: {len(self.apps)}")

            # Display summary
            self._display_summary()

            # Generate comprehensive report
            report_path = self._generate_report()
            self.core_api.print_success(f"Report generated: {report_path}")

            # Export to JSON
            output_dir = self.core_api.get_case_output_dir("ios_extractions")
            output_dir.mkdir(parents=True, exist_ok=True)

            json_path = output_dir / f"{current_zip.stem}_apps.json"
            self._export_to_json(json_path)
            self.core_api.print_success(f"App data exported to: {json_path}")

            return {
                "success": True,
                "total_apps": len(self.apps),
                "report_path": str(report_path),
                "json_path": str(json_path)
            }

        except Exception as e:
            self.core_api.print_error(f"Extraction failed: {e}")
            self.core_api.log_error(f"Error details: {e}")
            return {"success": False, "error": str(e)}

    def _detect_zip_structure(self) -> None:
        """Detect ZIP structure (Cellebrite, GrayKey, or raw filesystem)."""
        files = self.core_api.list_zip_contents()

        # Check for Cellebrite format first
        for file_info in files[:20]:  # Check first 20 entries
            filename = file_info.filename
            if filename.startswith('filesystem1/'):
                self.zip_prefix = 'filesystem1/'
                self.core_api.print_info(f"Detected format: Cellebrite (filesystem1/)")
                return
            elif filename.startswith('filesystem/') and not filename.startswith('filesystem1/'):
                self.zip_prefix = 'filesystem/'
                self.core_api.print_info(f"Detected format: Cellebrite (filesystem/)")
                return

        # Check if it's GrayKey or raw filesystem format (no prefix)
        # Look for characteristic iOS paths at root level
        has_ios_paths = False
        for file_info in files[:50]:  # Check more entries for root paths
            filename = file_info.filename.lower()
            if (filename.startswith('private/var/') or
                filename.startswith('library/') or
                filename.startswith('applications/') or
                filename.startswith('system/')):
                has_ios_paths = True
                break

        if has_ios_paths:
            self.core_api.print_info(f"Detected format: GrayKey/Raw filesystem (no prefix)")
        else:
            self.core_api.print_warning(f"Could not detect extraction format, attempting raw filesystem access")

    def _normalize_path(self, path: str) -> str:
        """Normalize path for ZIP access."""
        if self.zip_prefix:
            return self.zip_prefix + path
        return path

    def _parse_mobile_installation(self) -> Dict[str, Dict]:
        """Parse MobileInstallation.plist."""
        plist_path = 'private/var/mobile/Library/MobileInstallation/MobileInstallation.plist'
        apps = {}

        try:
            data = self.core_api.read_plist_from_zip(self._normalize_path(plist_path))

            for bundle_id, app_data in data.items():
                if not isinstance(app_data, dict):
                    continue

                container_path = app_data.get('Container', '')
                data_container_path = app_data.get('DataContainer', '')

                apps[bundle_id] = {
                    'bundle_identifier': bundle_id,
                    'bundle_container_guid': self._extract_guid(container_path),
                    'data_container_guid': self._extract_guid(data_container_path),
                    'bundle_container_path': container_path,
                    'data_container_path': data_container_path,
                    'app_bundle_path': app_data.get('Path', ''),
                    'display_name': app_data.get('CFBundleDisplayName', ''),
                    'bundle_name': app_data.get('CFBundleName', ''),
                    'version': app_data.get('CFBundleVersion', ''),
                    'short_version': app_data.get('CFBundleShortVersionString', ''),
                    'app_store_id': app_data.get('ItemID', ''),
                    'dsid': app_data.get('ApplicationDSID', ''),
                    'sequence_number': app_data.get('SequenceNumber', 0),
                    'is_app_clip': app_data.get('IsAppClip', False),
                    'source': 'MobileInstallation.plist'
                }

        except KeyError:
            self.core_api.log_warning("MobileInstallation.plist not found in ZIP")
        except Exception as e:
            self.core_api.log_error(f"Error parsing MobileInstallation.plist: {e}")

        return apps

    def _parse_application_state_db(self) -> List[str]:
        """Parse applicationState.db for bundle identifiers."""
        db_path = 'private/var/mobile/Library/FrontBoard/applicationState.db'
        bundle_ids = []

        try:
            query = """
                SELECT application_identifier
                FROM application_identifier_tab
                ORDER BY application_identifier
            """

            results = self.core_api.query_sqlite_from_zip(self._normalize_path(db_path), query)
            bundle_ids = [row[0] for row in results]

        except KeyError:
            self.core_api.log_warning("applicationState.db not found in ZIP")
        except Exception as e:
            self.core_api.log_error(f"Error parsing applicationState.db: {e}")

        return bundle_ids

    def _enumerate_filesystem(self) -> Dict[str, Dict]:
        """Enumerate .app bundles from filesystem."""
        apps = {}
        bundle_app_path = 'private/var/containers/Bundle/Application'

        try:
            files = self.core_api.list_zip_contents()

            # Find all GUID directories and .app bundles
            guid_pattern = r'[A-F0-9]{8}-[A-F0-9]{4}-[A-F0-9]{4}-[A-F0-9]{4}-[A-F0-9]{12}'
            normalized_base = self._normalize_path(bundle_app_path)

            guid_apps = {}
            for file_info in files:
                path = file_info.filename

                if normalized_base in path and '.app/' in path:
                    # Extract GUID and app bundle name
                    parts = path[len(normalized_base):].strip('/').split('/')
                    if len(parts) >= 2:
                        guid = parts[0]
                        app_name = parts[1]

                        if app_name.endswith('.app') and re.match(guid_pattern, guid, re.IGNORECASE):
                            if guid not in guid_apps:
                                guid_apps[guid] = []
                            if app_name not in guid_apps[guid]:
                                guid_apps[guid].append(app_name)

            # Parse Info.plist for each app
            for guid, app_names in guid_apps.items():
                for app_name in app_names:
                    info_plist_path = f"{bundle_app_path}/{guid}/{app_name}/Info.plist"

                    try:
                        info = self.core_api.read_plist_from_zip(self._normalize_path(info_plist_path))

                        bundle_id = info.get('CFBundleIdentifier')
                        if bundle_id:
                            apps[bundle_id] = {
                                'bundle_identifier': bundle_id,
                                'bundle_container_guid': guid,
                                'app_bundle_path': f"{bundle_app_path}/{guid}/{app_name}",
                                'display_name': info.get('CFBundleDisplayName', info.get('CFBundleName', '')),
                                'version': info.get('CFBundleVersion', ''),
                                'short_version': info.get('CFBundleShortVersionString', ''),
                                'executable': info.get('CFBundleExecutable', ''),
                                'minimum_os_version': info.get('MinimumOSVersion', ''),
                                'source': 'filesystem_enumeration'
                            }
                    except:
                        pass

        except Exception as e:
            self.core_api.log_error(f"Error enumerating filesystem: {e}")

        return apps

    def _merge_app_data(self, mobile_installation: Dict, app_state_ids: List[str],
                       filesystem: Dict) -> List[Dict]:
        """Merge data from multiple sources."""
        merged = {}

        # Start with MobileInstallation (most complete)
        for bundle_id, data in mobile_installation.items():
            merged[bundle_id] = data

        # Add filesystem data
        for bundle_id, data in filesystem.items():
            if bundle_id not in merged:
                merged[bundle_id] = data
            else:
                # Supplement existing data
                for key, value in data.items():
                    if key not in merged[bundle_id] or not merged[bundle_id][key]:
                        merged[bundle_id][key] = value

        # Flag apps from applicationState.db
        for bundle_id in app_state_ids:
            if bundle_id in merged:
                merged[bundle_id]['in_app_state_db'] = True
            else:
                merged[bundle_id] = {
                    'bundle_identifier': bundle_id,
                    'source': 'applicationState.db_only',
                    'in_app_state_db': True
                }

        return list(merged.values())

    def _extract_guid(self, path: str) -> Optional[str]:
        """Extract GUID from iOS container path."""
        guid_pattern = r'[A-F0-9]{8}-[A-F0-9]{4}-[A-F0-9]{4}-[A-F0-9]{4}-[A-F0-9]{12}'
        match = re.search(guid_pattern, path, re.IGNORECASE)
        return match.group(0) if match else None

    def _display_summary(self) -> None:
        """Display summary table of extracted apps."""
        from rich.table import Table

        table = Table(title=f"iOS Applications Found: {len(self.apps)}")
        table.add_column("Bundle ID", style="cyan", no_wrap=False)
        table.add_column("Display Name", style="green")
        table.add_column("Version", style="yellow")
        table.add_column("Bundle GUID", style="blue", no_wrap=False)

        # Show top 20 apps
        for app in sorted(self.apps, key=lambda x: x.get('display_name', x.get('bundle_identifier', '')))[:20]:
            table.add_row(
                app.get('bundle_identifier', 'N/A')[:50],
                app.get('display_name', 'N/A')[:30],
                app.get('version', 'N/A'),
                app.get('bundle_container_guid', 'N/A')[:20]
            )

        self.core_api.console.print()
        self.core_api.console.print(table)

        if len(self.apps) > 20:
            self.core_api.print_info(f"Showing 20 of {len(self.apps)} apps. See full report for complete list.")

    def _generate_report(self) -> Path:
        """Generate markdown report."""
        # Group apps by source
        sources = {}
        for app in self.apps:
            source = app.get('source', 'unknown')
            if source not in sources:
                sources[source] = []
            sources[source].append(app)

        sections = [
            {
                "heading": "Extraction Summary",
                "content": f"Extracted metadata for **{len(self.apps)} iOS applications** from the provided filesystem extraction.",
            },
            {
                "heading": "Data Sources",
                "content": {
                    "MobileInstallation.plist": len(sources.get('MobileInstallation.plist', [])),
                    "Filesystem Enumeration": len(sources.get('filesystem_enumeration', [])),
                    "applicationState.db Only": len(sources.get('applicationState.db_only', [])),
                },
                "style": "table",
            },
        ]

        # Applications table
        app_table = []
        for app in sorted(self.apps, key=lambda x: x.get('display_name', x.get('bundle_identifier', ''))):
            app_table.append({
                "Bundle ID": app.get('bundle_identifier', 'N/A'),
                "Display Name": app.get('display_name', 'N/A'),
                "Version": app.get('version', 'N/A'),
                "Bundle GUID": app.get('bundle_container_guid', 'N/A'),
                "Data GUID": app.get('data_container_guid', 'N/A'),
            })

        sections.append({
            "heading": "Applications",
            "content": app_table,
            "style": "table",
        })

        # Statistics
        stats = {
            "Total Apps": len(self.apps),
            "Apps with Bundle GUID": sum(1 for a in self.apps if a.get('bundle_container_guid')),
            "Apps with Data GUID": sum(1 for a in self.apps if a.get('data_container_guid')),
            "App Store Apps": sum(1 for a in self.apps if a.get('app_store_id')),
        }

        sections.append({
            "heading": "Statistics",
            "content": stats,
            "style": "table",
        })

        metadata = {
            "Total Applications": len(self.apps),
            "ZIP File": self.core_api.get_current_zip().name if self.core_api.get_current_zip() else "Unknown",
        }

        return self.core_api.generate_report(
            plugin_name="iOSAppGUIDExtractor",
            title="iOS Application GUID Extraction Report",
            sections=sections,
            metadata=metadata,
        )

    def _export_to_json(self, output_path: Path) -> None:
        """Export apps to JSON file."""
        import json

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(self.apps, f, indent=2, ensure_ascii=False)

    def cleanup(self) -> None:
        """Clean up temporary resources."""
        self.core_api.log_info(f"Cleaning up {self.metadata.name}")
