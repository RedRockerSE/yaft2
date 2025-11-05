"""
iOS Application Permissions and Usage Extractor

This tool extracts application permission grants, usage statistics, and
notification settings from iOS full filesystem extractions.

Based on forensic research of TCC.db, knowledgeC.db, and applicationState.plist.
"""

import os
import sqlite3
import plistlib
import json
import csv
import zipfile
import tempfile
import shutil
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta


class iOSAppPermissionsExtractor:
    """
    Comprehensive iOS Application Permissions and Usage Extractor
    for full filesystem extractions
    """

    # TCC service name mappings to human-readable names
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

    # Permission risk weights for scoring
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
        self.permissions = []
        self.usage_stats = {}
        self.apps_data = {}
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

    def _normalize_zip_path(self, path: Path) -> str:
        """Convert Path object to normalized zip entry path"""
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
        return (zip_path in self.zip_file.namelist() or
                any(name.startswith(zip_path + '/') for name in self.zip_file.namelist()))

    def _open_file_from_source(self, path: Path, mode='rb'):
        """Open file from either zip or filesystem"""
        if not self.is_zip:
            return open(path, mode)

        zip_path = self._normalize_zip_path(path)
        if zip_path in self.zip_file.namelist():
            return self.zip_file.open(zip_path, 'r')

        # Try with different root prefixes
        for name in self.zip_file.namelist():
            if name.endswith('/' + zip_path) or name.endswith('\\' + zip_path):
                return self.zip_file.open(name, 'r')

        raise FileNotFoundError(f"File not found in zip: {zip_path}")

    def extract_all(self, app_metadata_path: Optional[str] = None) -> Dict:
        """
        Extract permission and usage information from all available sources

        Args:
            app_metadata_path: Optional path to app metadata JSON from app_guid_extractor

        Returns:
            Dictionary containing comprehensive permission and usage information
        """
        print("[*] Starting extraction from multiple sources...")

        # Load app metadata if provided
        if app_metadata_path:
            print(f"[*] Loading app metadata from {app_metadata_path}...")
            self._load_app_metadata(app_metadata_path)

        # Primary source: TCC.db
        print("[*] Parsing TCC.db for permissions...")
        permissions = self._parse_tcc_db()
        print(f"[+] Found {len(permissions)} permission grants in TCC.db")

        # Secondary source: knowledgeC.db
        print("[*] Parsing knowledgeC.db for app usage...")
        usage_stats = self._parse_knowledge_db()
        print(f"[+] Found usage data for {len(usage_stats)} apps in knowledgeC.db")

        # Tertiary source: applicationState.plist
        print("[*] Parsing applicationState.plist for notifications...")
        notification_data = self._parse_application_state()
        print(f"[+] Found notification data for {len(notification_data)} apps")

        # Merge all data
        print("[*] Merging data from all sources...")
        merged_data = self._merge_app_data(permissions, usage_stats, notification_data)

        # Calculate risk scores
        print("[*] Calculating permission risk scores...")
        merged_data = self._calculate_risk_scores(merged_data)

        self.apps_data = merged_data
        print(f"[+] Total unique applications analyzed: {len(self.apps_data)}")

        return self._generate_summary()

    def _load_app_metadata(self, metadata_path: str):
        """Load app metadata from app_guid_extractor output"""
        try:
            with open(metadata_path, 'r', encoding='utf-8') as f:
                apps = json.load(f)

            self.app_metadata = {app['bundle_identifier']: app for app in apps}
            print(f"[+] Loaded metadata for {len(self.app_metadata)} apps")
        except Exception as e:
            print(f"[!] Error loading app metadata: {e}")
            self.app_metadata = {}

    def _parse_tcc_db(self) -> List[Dict]:
        """Parse TCC.db for permission grants"""
        if self.is_zip:
            db_path = Path('private/var/mobile/Library/TCC/TCC.db')
        else:
            db_path = self.fs_root / 'private/var/mobile/Library/TCC/TCC.db'

        permissions = []

        if not self._zip_path_exists(db_path):
            print("[!] Warning: TCC.db not found")
            return permissions

        try:
            # SQLite can't read from zip directly, need to extract to temp file
            if self.is_zip:
                if not self.temp_dir:
                    self.temp_dir = tempfile.mkdtemp(prefix='ios_extraction_')

                temp_db_path = os.path.join(self.temp_dir, 'TCC.db')

                with self._open_file_from_source(db_path, 'rb') as src:
                    with open(temp_db_path, 'wb') as dst:
                        shutil.copyfileobj(src, dst)

                db_path_str = temp_db_path
            else:
                db_path_str = str(db_path)

            conn = sqlite3.connect(db_path_str)
            cursor = conn.cursor()

            # Query permissions - handle both old and new schema
            try:
                # Try newer iOS schema first
                cursor.execute("""
                    SELECT service, client, client_type, auth_value, auth_reason,
                           last_modified, indirect_object_identifier
                    FROM access
                    ORDER BY service, client
                """)
            except sqlite3.OperationalError:
                # Fall back to older schema without indirect_object_identifier
                cursor.execute("""
                    SELECT service, client, client_type, auth_value, auth_reason,
                           last_modified, NULL
                    FROM access
                    ORDER BY service, client
                """)

            for row in cursor.fetchall():
                service, client, client_type, auth_value, auth_reason, last_modified, indirect_object = row

                # Convert auth_value to status
                auth_status_map = {
                    0: 'Denied',
                    1: 'Unknown',
                    2: 'Allowed',
                    3: 'Limited'
                }
                auth_status = auth_status_map.get(auth_value, 'Unknown')

                # Get human-readable service name
                service_name = self.TCC_SERVICES.get(service, service)

                # Convert timestamp (Core Data format: seconds since 2001-01-01)
                if last_modified:
                    try:
                        # Core Data timestamp: seconds since 2001-01-01 00:00:00 UTC
                        # Convert to Unix timestamp
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

            conn.close()

        except Exception as e:
            print(f"[!] Error parsing TCC.db: {e}")

        return permissions

    def _parse_knowledge_db(self) -> Dict[str, Dict]:
        """Parse knowledgeC.db for app usage statistics"""
        if self.is_zip:
            db_path = Path('private/var/mobile/Library/CoreDuet/Knowledge/knowledgeC.db')
        else:
            db_path = self.fs_root / 'private/var/mobile/Library/CoreDuet/Knowledge/knowledgeC.db'

        usage_stats = {}

        if not self._zip_path_exists(db_path):
            print("[!] Warning: knowledgeC.db not found")
            return usage_stats

        try:
            # Extract to temp file if zip
            if self.is_zip:
                if not self.temp_dir:
                    self.temp_dir = tempfile.mkdtemp(prefix='ios_extraction_')

                temp_db_path = os.path.join(self.temp_dir, 'knowledgeC.db')

                with self._open_file_from_source(db_path, 'rb') as src:
                    with open(temp_db_path, 'wb') as dst:
                        shutil.copyfileobj(src, dst)

                db_path_str = temp_db_path
            else:
                db_path_str = str(db_path)

            conn = sqlite3.connect(db_path_str)
            cursor = conn.cursor()

            # Query app usage events
            # The schema varies by iOS version, try different approaches
            try:
                # Try iOS 12+ schema
                cursor.execute("""
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
                """)

                events = cursor.fetchall()

                for bundle_id, start_date, end_date, stream_name in events:
                    if not bundle_id:
                        continue

                    # Initialize bundle stats if needed
                    if bundle_id not in usage_stats:
                        usage_stats[bundle_id] = {
                            'bundle_id': bundle_id,
                            'total_launches': 0,
                            'total_duration_seconds': 0,
                            'first_used': None,
                            'last_used': None,
                            'events': []
                        }

                    # Calculate duration
                    if start_date and end_date:
                        duration = end_date - start_date

                        # Convert Core Data timestamps
                        try:
                            core_data_epoch = datetime(2001, 1, 1)
                            start_time = core_data_epoch + timedelta(seconds=start_date)
                            end_time = core_data_epoch + timedelta(seconds=end_date)

                            usage_stats[bundle_id]['events'].append({
                                'start_time': start_time.strftime('%Y-%m-%d %H:%M:%S'),
                                'end_time': end_time.strftime('%Y-%m-%d %H:%M:%S'),
                                'duration_seconds': duration
                            })

                            usage_stats[bundle_id]['total_duration_seconds'] += duration
                            usage_stats[bundle_id]['total_launches'] += 1

                            # Track first/last usage
                            if not usage_stats[bundle_id]['first_used']:
                                usage_stats[bundle_id]['first_used'] = start_time.strftime('%Y-%m-%d %H:%M:%S')
                            usage_stats[bundle_id]['last_used'] = start_time.strftime('%Y-%m-%d %H:%M:%S')

                        except:
                            pass

            except sqlite3.OperationalError as e:
                print(f"[!] knowledgeC.db schema not recognized: {e}")

            conn.close()

            # Calculate aggregate stats
            for bundle_id, stats in usage_stats.items():
                if stats['total_launches'] > 0:
                    stats['average_session_duration'] = int(
                        stats['total_duration_seconds'] / stats['total_launches']
                    )
                else:
                    stats['average_session_duration'] = 0

                # Remove detailed events from final output (too large)
                del stats['events']

        except Exception as e:
            print(f"[!] Error parsing knowledgeC.db: {e}")

        return usage_stats

    def _parse_application_state(self) -> Dict[str, Dict]:
        """Parse applicationState.plist for notification settings"""
        if self.is_zip:
            plist_path = Path('private/var/mobile/Library/SpringBoard/applicationState.plist')
        else:
            plist_path = self.fs_root / 'private/var/mobile/Library/SpringBoard/applicationState.plist'

        notification_data = {}

        if not self._zip_path_exists(plist_path):
            print("[!] Warning: applicationState.plist not found")
            return notification_data

        try:
            with self._open_file_from_source(plist_path, 'rb') as f:
                data = plistlib.load(f)

            # Parse notification settings per app
            for bundle_id, app_data in data.items():
                if not isinstance(app_data, dict):
                    continue

                notification_data[bundle_id] = {
                    'bundle_id': bundle_id,
                    'badge_count': app_data.get('SBApplicationBadgeValue', 0),
                    'has_settings': 'SBApplicationNotificationSettings' in app_data
                }

        except Exception as e:
            print(f"[!] Error parsing applicationState.plist: {e}")

        return notification_data

    def _merge_app_data(self, permissions: List[Dict], usage_stats: Dict[str, Dict],
                       notification_data: Dict[str, Dict]) -> Dict[str, Dict]:
        """Merge data from all sources"""
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

        # Enrich with app metadata if available
        if hasattr(self, 'app_metadata'):
            for bundle_id, app_data in merged.items():
                if bundle_id in self.app_metadata:
                    metadata = self.app_metadata[bundle_id]
                    app_data['display_name'] = metadata.get('display_name', '')
                    app_data['version'] = metadata.get('version', '')
                    app_data['bundle_container_guid'] = metadata.get('bundle_container_guid', '')
                    app_data['data_container_guid'] = metadata.get('data_container_guid', '')

        return merged

    def _calculate_risk_scores(self, apps_data: Dict[str, Dict]) -> Dict[str, Dict]:
        """Calculate risk scores for each app based on permissions"""
        for bundle_id, app_data in apps_data.items():
            risk_score = 0.0
            permission_count = len(app_data['permissions'])

            # Calculate based on permission types
            for perm in app_data['permissions']:
                if perm['auth_status'] == 'Allowed':
                    service_name = perm['service_name']
                    weight = self.PERMISSION_WEIGHTS.get(service_name,
                                                         self.PERMISSION_WEIGHTS['default'])
                    risk_score += weight

            # Bonus risk for excessive permissions
            if permission_count > 10:
                risk_score += 2.0
            elif permission_count > 5:
                risk_score += 1.0

            # Reduce risk for frequently used apps
            usage = app_data.get('usage_stats', {})
            if usage.get('total_duration_seconds', 0) > 3600:  # More than 1 hour usage
                risk_score *= 0.7  # Reduce by 30%

            app_data['risk_score'] = round(risk_score, 2)
            app_data['permission_count'] = permission_count
            app_data['high_risk_permission_count'] = sum(
                1 for p in app_data['permissions']
                if p.get('is_high_risk') and p['auth_status'] == 'Allowed'
            )

        return apps_data

    def _generate_summary(self) -> Dict:
        """Generate summary statistics"""
        total_apps = len(self.apps_data)
        total_permissions = sum(len(app['permissions']) for app in self.apps_data.values())

        # Count by permission type
        permission_counts = {}
        for app in self.apps_data.values():
            for perm in app['permissions']:
                service_name = perm['service_name']
                if service_name not in permission_counts:
                    permission_counts[service_name] = {'allowed': 0, 'denied': 0, 'total': 0}

                permission_counts[service_name]['total'] += 1
                if perm['auth_status'] == 'Allowed':
                    permission_counts[service_name]['allowed'] += 1
                elif perm['auth_status'] == 'Denied':
                    permission_counts[service_name]['denied'] += 1

        return {
            'extraction_metadata': {
                'extraction_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'total_apps_analyzed': total_apps,
                'total_permissions': total_permissions
            },
            'apps': self.apps_data,
            'permissions_by_type': permission_counts
        }

    def export_to_json(self, output_path: str):
        """Export app permission and usage data to JSON"""
        if not self.apps_data:
            print("[!] No data extracted. Run extract_all() first.")
            return

        summary = self._generate_summary()

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)

        print(f"[+] Exported data for {len(self.apps_data)} apps to {output_path}")

    def export_to_csv(self, output_path: str):
        """Export app permission and usage data to CSV"""
        if not self.apps_data:
            print("[!] No data extracted. Run extract_all() first.")
            return

        # Flatten data for CSV
        rows = []
        for bundle_id, app_data in self.apps_data.items():
            base_row = {
                'bundle_id': bundle_id,
                'display_name': app_data.get('display_name', ''),
                'version': app_data.get('version', ''),
                'risk_score': app_data.get('risk_score', 0),
                'permission_count': app_data.get('permission_count', 0),
                'high_risk_permission_count': app_data.get('high_risk_permission_count', 0),
                'total_launches': app_data.get('usage_stats', {}).get('total_launches', 0),
                'total_duration_seconds': app_data.get('usage_stats', {}).get('total_duration_seconds', 0),
                'first_used': app_data.get('usage_stats', {}).get('first_used', ''),
                'last_used': app_data.get('usage_stats', {}).get('last_used', ''),
                'badge_count': app_data.get('notification_data', {}).get('badge_count', 0)
            }

            # Create row for each permission
            if app_data['permissions']:
                for perm in app_data['permissions']:
                    row = base_row.copy()
                    row.update({
                        'permission_service': perm['service_name'],
                        'permission_status': perm['auth_status'],
                        'permission_last_modified': perm['last_modified'],
                        'is_high_risk_permission': perm.get('is_high_risk', False)
                    })
                    rows.append(row)
            else:
                # App with no permissions
                row = base_row.copy()
                row.update({
                    'permission_service': '',
                    'permission_status': '',
                    'permission_last_modified': '',
                    'is_high_risk_permission': False
                })
                rows.append(row)

        if rows:
            fieldnames = rows[0].keys()
            with open(output_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(rows)

            print(f"[+] Exported {len(rows)} permission records to {output_path}")

    def print_summary(self):
        """Print a summary of extracted data"""
        if not self.apps_data:
            print("[!] No data extracted.")
            return

        summary = self._generate_summary()

        print(f"\n{'='*80}")
        print(f"App Permissions & Usage Summary")
        print(f"{'='*80}\n")

        print(f"Total Apps Analyzed: {summary['extraction_metadata']['total_apps_analyzed']}")
        print(f"Total Permission Grants: {summary['extraction_metadata']['total_permissions']}\n")

        # Top apps by permission count
        print("Apps with Most Permissions:")
        sorted_apps = sorted(
            self.apps_data.values(),
            key=lambda x: x.get('permission_count', 0),
            reverse=True
        )[:5]

        for i, app in enumerate(sorted_apps, 1):
            display_name = app.get('display_name') or app['bundle_id']
            print(f"{i}. {display_name} ({app.get('permission_count', 0)} permissions)")

        # Top apps by usage
        print("\nMost Used Apps (by duration):")
        sorted_by_usage = sorted(
            self.apps_data.values(),
            key=lambda x: x.get('usage_stats', {}).get('total_duration_seconds', 0),
            reverse=True
        )[:5]

        for i, app in enumerate(sorted_by_usage, 1):
            display_name = app.get('display_name') or app['bundle_id']
            duration_hours = app.get('usage_stats', {}).get('total_duration_seconds', 0) / 3600
            if duration_hours > 0:
                print(f"{i}. {display_name} ({duration_hours:.1f} hours)")

        # High-risk permission summary
        print("\nHigh-Risk Permission Grants:")
        for service_name in self.HIGH_RISK_PERMISSIONS:
            if service_name in summary['permissions_by_type']:
                count = summary['permissions_by_type'][service_name]['allowed']
                print(f"- {count} apps with {service_name} access")

        # Top risky apps
        print("\nHighest Risk Apps:")
        sorted_by_risk = sorted(
            self.apps_data.values(),
            key=lambda x: x.get('risk_score', 0),
            reverse=True
        )[:5]

        for i, app in enumerate(sorted_by_risk, 1):
            display_name = app.get('display_name') or app['bundle_id']
            risk_score = app.get('risk_score', 0)
            if risk_score > 0:
                print(f"{i}. {display_name} (risk score: {risk_score})")

    def get_app_by_bundle_id(self, bundle_id: str) -> Optional[Dict]:
        """Get app information by bundle identifier"""
        return self.apps_data.get(bundle_id)

    def get_apps_with_permission(self, permission_name: str) -> List[Dict]:
        """Get all apps that have a specific permission"""
        result = []
        for app in self.apps_data.values():
            for perm in app['permissions']:
                if (perm['service_name'] == permission_name and
                    perm['auth_status'] == 'Allowed'):
                    result.append(app)
                    break
        return result


def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(
        description='Extract iOS app permissions and usage from filesystem extraction or zip file'
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
        '--permission',
        help='Search for apps with specific permission (e.g., "Location Services")'
    )
    parser.add_argument(
        '--app-metadata',
        help='Path to app metadata JSON from app_guid_extractor'
    )

    args = parser.parse_args()

    # Initialize extractor
    print(f"[*] Initializing iOS App Permissions Extractor")
    print(f"[*] Extraction root: {args.extraction_path}\n")

    extractor = iOSAppPermissionsExtractor(args.extraction_path)

    try:
        # Extract all permission and usage information
        summary = extractor.extract_all(app_metadata_path=args.app_metadata)

        # Search for specific app if requested
        if args.bundle_id:
            print(f"\n[*] Searching for bundle ID: {args.bundle_id}")
            app = extractor.get_app_by_bundle_id(args.bundle_id)
            if app:
                print(f"[+] Found app:")
                print(f"\nBundle ID: {app['bundle_id']}")
                print(f"Display Name: {app.get('display_name', 'N/A')}")
                print(f"Risk Score: {app.get('risk_score', 0)}")
                print(f"\nPermissions ({len(app['permissions'])}):")
                for perm in app['permissions']:
                    print(f"  - {perm['service_name']}: {perm['auth_status']}")
                if app.get('usage_stats'):
                    print(f"\nUsage Statistics:")
                    print(f"  Total Launches: {app['usage_stats'].get('total_launches', 0)}")
                    print(f"  Total Duration: {app['usage_stats'].get('total_duration_seconds', 0) / 3600:.1f} hours")
            else:
                print(f"[!] App with bundle ID '{args.bundle_id}' not found")
            return

        # Search for apps with specific permission
        if args.permission:
            print(f"\n[*] Searching for apps with permission: {args.permission}")
            apps = extractor.get_apps_with_permission(args.permission)
            if apps:
                print(f"[+] Found {len(apps)} apps with {args.permission}:")
                for app in apps:
                    display_name = app.get('display_name') or app['bundle_id']
                    print(f"  - {display_name}")
            else:
                print(f"[!] No apps found with permission '{args.permission}'")
            return

        # Print summary
        extractor.print_summary()

        # Export results
        os.makedirs(args.output_dir, exist_ok=True)

        if args.format in ['json', 'both']:
            json_path = os.path.join(args.output_dir, 'ios_app_permissions.json')
            extractor.export_to_json(json_path)

        if args.format in ['csv', 'both']:
            csv_path = os.path.join(args.output_dir, 'ios_app_permissions.csv')
            extractor.export_to_csv(csv_path)

    finally:
        # Ensure cleanup happens even if there's an error
        extractor.cleanup()


if __name__ == "__main__":
    main()
