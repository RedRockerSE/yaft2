"""
iOS Application GUID and Bundle ID Extractor

This tool extracts application metadata from iOS full filesystem extractions,
including bundle identifiers, container GUIDs, and app information.

Based on forensic research of iOS file structures and databases.
"""

import os
import sqlite3
import plistlib
import re
import json
import csv
import zipfile
import tempfile
import shutil
from pathlib import Path
from typing import List, Dict, Optional


class iOSAppGUIDExtractor:
    """
    Comprehensive iOS Application GUID and Bundle ID Extractor
    for full filesystem extractions
    """

    def __init__(self, fs_root: str):
        """
        Initialize extractor with iOS filesystem root or zip file

        Args:
            fs_root: Root directory of iOS filesystem extraction or path to zip file
        """
        self.fs_root_path = Path(fs_root)
        self.is_zip = self.fs_root_path.is_file() and zipfile.is_zipfile(self.fs_root_path)
        self.zip_file = None
        self.temp_dir = None
        self.apps = []
        self.zip_prefix = ''  # For Cellebrite extractions with filesystem1/ prefix

        if self.is_zip:
            print(f"[*] Detected zip file: {self.fs_root_path}")
            self.zip_file = zipfile.ZipFile(self.fs_root_path, 'r')
            # Detect Cellebrite filesystem prefix
            self._detect_zip_structure()
        else:
            print(f"[*] Using directory extraction: {self.fs_root_path}")
            self.fs_root = self.fs_root_path

    def __del__(self):
        """Cleanup temporary resources"""
        self.cleanup()

    def cleanup(self):
        """Clean up temporary files and close resources"""
        if self.zip_file:
            try:
                self.zip_file.close()
            except:
                pass

        if self.temp_dir and os.path.exists(self.temp_dir):
            try:
                shutil.rmtree(self.temp_dir)
            except:
                pass

    def _detect_zip_structure(self):
        """Detect if zip has Cellebrite filesystem prefix (e.g., filesystem1/)"""
        if not self.is_zip:
            return

        # Check for common Cellebrite patterns in first few entries
        # Cellebrite puts filesystem1/ or filesystem/ at the root
        for name in self.zip_file.namelist()[:20]:  # Check first 20 entries
            # Look for filesystem1/ pattern
            if name.startswith('filesystem1/'):
                self.zip_prefix = 'filesystem1/'
                print(f"[*] Detected Cellebrite extraction format with prefix: {self.zip_prefix}")
                return
            # Look for filesystem/ pattern (alternative)
            elif name.startswith('filesystem/') and not name.startswith('filesystem1/'):
                self.zip_prefix = 'filesystem/'
                print(f"[*] Detected Cellebrite extraction format with prefix: {self.zip_prefix}")
                return

    def extract_all(self) -> List[Dict]:
        """
        Extract app information from all available sources

        Returns:
            List of dictionaries containing comprehensive app information
        """
        print("[*] Starting extraction from multiple sources...")

        # Primary source: MobileInstallation.plist
        print("[*] Parsing MobileInstallation.plist...")
        mobile_installation_apps = self._parse_mobile_installation()
        print(f"[+] Found {len(mobile_installation_apps)} apps in MobileInstallation.plist")

        # Secondary source: applicationState.db
        print("[*] Parsing applicationState.db...")
        app_state_bundle_ids = self._parse_application_state_db()
        print(f"[+] Found {len(app_state_bundle_ids)} bundle IDs in applicationState.db")

        # Tertiary: Filesystem enumeration
        print("[*] Enumerating filesystem for .app bundles...")
        filesystem_apps = self._enumerate_filesystem()
        print(f"[+] Found {len(filesystem_apps)} apps via filesystem enumeration")

        # Merge data
        print("[*] Merging data from all sources...")
        self.apps = self._merge_app_data(
            mobile_installation_apps,
            app_state_bundle_ids,
            filesystem_apps
        )

        print(f"[+] Total unique applications found: {len(self.apps)}")
        return self.apps

    def _normalize_zip_path(self, path: Path) -> str:
        """Convert Path object to normalized zip entry path"""
        # Convert to forward slashes for zip files
        normalized = str(path).replace('\\', '/').lstrip('/')
        # Add Cellebrite prefix if detected
        if self.zip_prefix:
            normalized = self.zip_prefix + normalized
        return normalized

    def _zip_path_exists(self, path: Path) -> bool:
        """Check if path exists in zip file"""
        if not self.is_zip:
            return path.exists()

        zip_path = self._normalize_zip_path(path)
        # Check exact match or as directory
        return (zip_path in self.zip_file.namelist() or
                any(name.startswith(zip_path + '/') for name in self.zip_file.namelist()))

    def _open_file_from_source(self, path: Path, mode='rb'):
        """Open file from either zip or filesystem"""
        if not self.is_zip:
            return open(path, mode)

        zip_path = self._normalize_zip_path(path)
        # Try to find the file in zip
        if zip_path in self.zip_file.namelist():
            return self.zip_file.open(zip_path, 'r')

        # Try with different root prefixes (some zips have extra directories)
        for name in self.zip_file.namelist():
            if name.endswith('/' + zip_path) or name.endswith('\\' + zip_path):
                return self.zip_file.open(name, 'r')

        raise FileNotFoundError(f"File not found in zip: {zip_path}")

    def _list_zip_directory(self, dir_path: Path):
        """List items in a directory (works for both zip and filesystem)"""
        if not self.is_zip:
            if dir_path.exists():
                return list(dir_path.iterdir())
            return []

        zip_dir = self._normalize_zip_path(dir_path)
        items = []
        seen = set()

        for name in self.zip_file.namelist():
            # Normalize the name
            normalized = name.replace('\\', '/')

            # Check if this path is under our directory
            if normalized.startswith(zip_dir + '/'):
                # Get the relative path from our directory
                rel_path = normalized[len(zip_dir)+1:]
                # Get the first component (immediate child)
                first_component = rel_path.split('/')[0]

                if first_component and first_component not in seen:
                    seen.add(first_component)
                    # Create a pseudo-path object
                    full_path = dir_path / first_component
                    items.append(full_path)

        return items

    def _get_zip_guid_directories(self, base_path: Path):
        """Get GUID directories from zip file"""
        if not self.is_zip:
            if base_path.exists():
                return [d for d in base_path.iterdir() if d.is_dir()]
            return []

        zip_base = self._normalize_zip_path(base_path)
        guid_dirs = {}

        for name in self.zip_file.namelist():
            normalized = name.replace('\\', '/')
            if normalized.startswith(zip_base + '/'):
                rel_path = normalized[len(zip_base)+1:]
                if rel_path:
                    guid = rel_path.split('/')[0]
                    if guid and guid not in guid_dirs:
                        guid_dirs[guid] = base_path / guid

        return list(guid_dirs.values())

    def _parse_mobile_installation(self) -> Dict[str, Dict]:
        """Parse MobileInstallation.plist"""
        # Build path relative to root
        if self.is_zip:
            plist_path = Path('private/var/mobile/Library/MobileInstallation/MobileInstallation.plist')
        else:
            plist_path = self.fs_root / 'private/var/mobile/Library/MobileInstallation/MobileInstallation.plist'

        apps = {}

        if not self._zip_path_exists(plist_path):
            print(f"[!] Warning: MobileInstallation.plist not found")
            return apps

        try:
            with self._open_file_from_source(plist_path, 'rb') as f:
                data = plistlib.load(f)

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

        except Exception as e:
            print(f"[!] Error parsing MobileInstallation.plist: {e}")

        return apps

    def _parse_application_state_db(self) -> List[str]:
        """Parse applicationState.db for bundle identifiers"""
        # Build path relative to root
        if self.is_zip:
            db_path = Path('private/var/mobile/Library/FrontBoard/applicationState.db')
        else:
            db_path = self.fs_root / 'private/var/mobile/Library/FrontBoard/applicationState.db'

        bundle_ids = []

        if not self._zip_path_exists(db_path):
            print(f"[!] Warning: applicationState.db not found")
            return bundle_ids

        try:
            # SQLite can't read from zip directly, need to extract to temp file
            if self.is_zip:
                # Create temp directory if needed
                if not self.temp_dir:
                    self.temp_dir = tempfile.mkdtemp(prefix='ios_extraction_')

                temp_db_path = os.path.join(self.temp_dir, 'applicationState.db')

                # Extract database to temp file
                with self._open_file_from_source(db_path, 'rb') as src:
                    with open(temp_db_path, 'wb') as dst:
                        shutil.copyfileobj(src, dst)

                db_path_str = temp_db_path
            else:
                db_path_str = str(db_path)

            conn = sqlite3.connect(db_path_str)
            cursor = conn.cursor()

            cursor.execute("""
                SELECT application_identifier
                FROM application_identifier_tab
                ORDER BY application_identifier
            """)

            bundle_ids = [row[0] for row in cursor.fetchall()]

            conn.close()

        except Exception as e:
            print(f"[!] Error querying applicationState.db: {e}")

        return bundle_ids

    def _enumerate_filesystem(self) -> Dict[str, Dict]:
        """Enumerate .app bundles from filesystem"""
        apps = {}

        # Build path relative to root
        if self.is_zip:
            bundle_app_dir = Path('private/var/containers/Bundle/Application')
        else:
            bundle_app_dir = self.fs_root / 'private/var/containers/Bundle/Application'

        if not self._zip_path_exists(bundle_app_dir):
            print(f"[!] Warning: Bundle/Application directory not found")
            return apps

        # Enumerate all GUID directories
        guid_dirs = self._get_zip_guid_directories(bundle_app_dir)

        for guid_dir in guid_dirs:
            bundle_guid = guid_dir.name

            # Find .app bundles
            if self.is_zip:
                # For zip files, search for .app directories under this GUID
                app_bundles = []
                zip_guid_path = self._normalize_zip_path(guid_dir)

                for name in self.zip_file.namelist():
                    normalized = name.replace('\\', '/')
                    if normalized.startswith(zip_guid_path + '/'):
                        rel_path = normalized[len(zip_guid_path)+1:]
                        if '.app/' in rel_path or rel_path.endswith('.app'):
                            app_name = rel_path.split('/')[0]
                            if app_name.endswith('.app'):
                                app_bundle_path = guid_dir / app_name
                                if app_bundle_path not in app_bundles:
                                    app_bundles.append(app_bundle_path)
            else:
                app_bundles = list(guid_dir.glob('*.app'))

            for app_bundle in app_bundles:
                info_plist = app_bundle / 'Info.plist'

                if not self._zip_path_exists(info_plist):
                    continue

                try:
                    with self._open_file_from_source(info_plist, 'rb') as f:
                        info = plistlib.load(f)

                    bundle_id = info.get('CFBundleIdentifier')

                    if not bundle_id:
                        continue

                    apps[bundle_id] = {
                        'bundle_identifier': bundle_id,
                        'bundle_container_guid': bundle_guid,
                        'app_bundle_path': str(app_bundle),
                        'display_name': info.get('CFBundleDisplayName',
                                                info.get('CFBundleName', '')),
                        'version': info.get('CFBundleVersion', ''),
                        'short_version': info.get('CFBundleShortVersionString', ''),
                        'executable': info.get('CFBundleExecutable', ''),
                        'minimum_os_version': info.get('MinimumOSVersion', ''),
                        'source': 'filesystem_enumeration'
                    }

                except Exception as e:
                    print(f"[!] Error parsing Info.plist in {app_bundle}: {e}")

        return apps

    def _merge_app_data(self, mobile_installation: Dict,
                       app_state_ids: List[str],
                       filesystem: Dict) -> List[Dict]:
        """Merge data from multiple sources"""
        merged = {}

        # Start with MobileInstallation (most complete)
        for bundle_id, data in mobile_installation.items():
            merged[bundle_id] = data

        # Add filesystem data for apps not in MobileInstallation
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
                # App in state DB but not found elsewhere
                merged[bundle_id] = {
                    'bundle_identifier': bundle_id,
                    'source': 'applicationState.db_only',
                    'in_app_state_db': True
                }

        return list(merged.values())

    def _extract_guid(self, path: str) -> Optional[str]:
        """Extract GUID from iOS container path"""
        guid_pattern = r'[A-F0-9]{8}-[A-F0-9]{4}-[A-F0-9]{4}-[A-F0-9]{4}-[A-F0-9]{12}'
        match = re.search(guid_pattern, path, re.IGNORECASE)
        return match.group(0) if match else None

    def find_data_container(self, bundle_id: str) -> Optional[str]:
        """
        Find data container path for a given bundle identifier

        Args:
            bundle_id: App bundle identifier

        Returns:
            Path to data container or None
        """
        for app in self.apps:
            if app.get('bundle_identifier') == bundle_id:
                return app.get('data_container_path')
        return None

    def get_app_by_bundle_id(self, bundle_id: str) -> Optional[Dict]:
        """Get app information by bundle identifier"""
        for app in self.apps:
            if app.get('bundle_identifier') == bundle_id:
                return app
        return None

    def get_app_by_guid(self, guid: str) -> Optional[Dict]:
        """Get app information by container GUID"""
        for app in self.apps:
            if (app.get('bundle_container_guid') == guid or
                app.get('data_container_guid') == guid):
                return app
        return None

    def export_to_csv(self, output_path: str):
        """Export app information to CSV"""
        if not self.apps:
            print("[!] No apps extracted. Run extract_all() first.")
            return

        # Determine all possible fields
        all_fields = set()
        for app in self.apps:
            all_fields.update(app.keys())

        fields = sorted(list(all_fields))

        with open(output_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fields)
            writer.writeheader()
            writer.writerows(self.apps)

        print(f"[+] Exported {len(self.apps)} apps to {output_path}")

    def export_to_json(self, output_path: str):
        """Export app information to JSON"""
        if not self.apps:
            print("[!] No apps extracted. Run extract_all() first.")
            return

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(self.apps, f, indent=2, ensure_ascii=False)

        print(f"[+] Exported {len(self.apps)} apps to {output_path}")

    def print_summary(self):
        """Print a summary of extracted apps"""
        if not self.apps:
            print("[!] No apps extracted.")
            return

        print(f"\n{'='*80}")
        print(f"Found {len(self.apps)} applications")
        print(f"{'='*80}\n")

        for app in sorted(self.apps, key=lambda x: x.get('bundle_identifier', '')):
            print(f"Bundle ID: {app.get('bundle_identifier', 'N/A')}")
            print(f"  Display Name: {app.get('display_name', 'N/A')}")
            print(f"  Bundle GUID: {app.get('bundle_container_guid', 'N/A')}")
            print(f"  Data GUID: {app.get('data_container_guid', 'N/A')}")
            print(f"  Version: {app.get('version', 'N/A')}")
            print(f"  Source: {app.get('source', 'N/A')}")
            print()


def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(
        description='Extract iOS app GUIDs and metadata from filesystem extraction or zip file'
    )
    parser.add_argument(
        'extraction_path',
        help='Path to iOS filesystem extraction root or zip file'
    )
    parser.add_argument(
        '--output-dir',
        default='../data/output',
        help='Output directory for exported data (default: ../data/output)'
    )
    parser.add_argument(
        '--format',
        choices=['json', 'csv', 'both'],
        default='both',
        help='Output format (default: both)'
    )
    parser.add_argument(
        '--bundle-id',
        help='Search for specific bundle ID'
    )
    parser.add_argument(
        '--guid',
        help='Search for specific GUID'
    )

    args = parser.parse_args()

    # Initialize extractor
    print(f"[*] Initializing iOS App GUID Extractor")
    print(f"[*] Extraction root: {args.extraction_path}\n")

    extractor = iOSAppGUIDExtractor(args.extraction_path)

    try:
        # Extract all app information
        apps = extractor.extract_all()

        # Search for specific app if requested
        if args.bundle_id:
            print(f"\n[*] Searching for bundle ID: {args.bundle_id}")
            app = extractor.get_app_by_bundle_id(args.bundle_id)
            if app:
                print(f"[+] Found app:")
                for key, value in app.items():
                    print(f"  {key}: {value}")
            else:
                print(f"[!] App with bundle ID '{args.bundle_id}' not found")
            return

        if args.guid:
            print(f"\n[*] Searching for GUID: {args.guid}")
            app = extractor.get_app_by_guid(args.guid)
            if app:
                print(f"[+] Found app:")
                for key, value in app.items():
                    print(f"  {key}: {value}")
            else:
                print(f"[!] App with GUID '{args.guid}' not found")
            return

        # Print summary
        extractor.print_summary()

        # Export results
        os.makedirs(args.output_dir, exist_ok=True)

        if args.format in ['json', 'both']:
            json_path = os.path.join(args.output_dir, 'ios_apps.json')
            extractor.export_to_json(json_path)

        if args.format in ['csv', 'both']:
            csv_path = os.path.join(args.output_dir, 'ios_apps.csv')
            extractor.export_to_csv(csv_path)

    finally:
        # Ensure cleanup happens even if there's an error
        extractor.cleanup()


if __name__ == "__main__":
    main()
