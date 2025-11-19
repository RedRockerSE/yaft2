"""
iOS Device Information Extractor Plugin for YaFT

This plugin extracts comprehensive device metadata from iOS full filesystem extractions,
including system version, device identifiers, IMEI/MEID, carrier info, iCloud accounts,
backup information, and locale settings.

Supports both Cellebrite and GrayKey extraction formats.

Based on forensic research documented in docs/PluginResearch.md
"""

import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional

from yaft.core.api import CoreAPI
from yaft.core.plugin_base import PluginBase, PluginMetadata


class iOSDeviceInfoExtractorPlugin(PluginBase):
    """
    iOS Device Information Extractor for comprehensive device metadata analysis.

    Extracts device information from multiple sources including plists, databases,
    and system files to provide a complete picture of the iOS device.
    """

    def __init__(self, core_api: CoreAPI) -> None:
        super().__init__(core_api)
        self.metadata_extracted: Dict[str, Any] = {}
        self.errors: List[Dict[str, str]] = []
        self.zip_prefix = ''
        self.extraction_type = 'unknown'

    @property
    def metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name="iOSDeviceInfoExtractor",
            version="1.1.0",
            description="Extract comprehensive device metadata from iOS filesystem extractions",
            author="YaFT Forensics Team",
            requires_core_version=">=0.1.0",
            dependencies=[],
            enabled=True,
            target_os=["ios"],
        )

    def initialize(self) -> None:
        """Initialize the plugin."""
        self.core_api.log_info(f"Initializing {self.metadata.name}")
        self.metadata_extracted = {}
        self.errors = []

    def execute(self, *args: Any, **kwargs: Any) -> Dict[str, Any]:
        """
        Execute iOS device information extraction.

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

            # Extract from all sources
            self.core_api.print_info("Extracting system version information...")
            self._extract_system_version()

            self.core_api.print_info("Extracting device identifiers...")
            self._extract_device_identifiers()

            self.core_api.print_info("Extracting cellular information...")
            self._extract_cellular_info()

            self.core_api.print_info("Extracting carrier information...")
            self._extract_carrier_info()

            self.core_api.print_info("Extracting iCloud account information...")
            self._extract_icloud_accounts()

            self.core_api.print_info("Extracting backup information...")
            self._extract_backup_info()

            self.core_api.print_info("Extracting timezone and locale settings...")
            self._extract_timezone_locale()

            # Display summary
            self._display_summary()

            # Generate report
            report_path = self._generate_report()
            self.core_api.print_success(f"Report generated: {report_path}")

            # Export to JSON
            output_dir = self.core_api.get_case_output_dir("ios_device_info")
            output_dir.mkdir(parents=True, exist_ok=True)

            json_path = output_dir / f"{current_zip.stem}_device_info.json"
            self._export_to_json(json_path)
            self.core_api.print_success(f"Device info exported to: {json_path}")

            return {
                "success": True,
                "report_path": str(report_path),
                "json_path": str(json_path),
                "device_info": self._format_device_info(),
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

    def _extract_system_version(self) -> None:
        """Extract iOS system version information."""
        # Try multiple possible file patterns
        patterns = [
            'SystemVersion.plist',
            'LastBuildInfo.plist',
        ]

        data = None
        found_file = None

        for pattern in patterns:
            files = self.core_api.find_files_in_zip(pattern)
            if files:
                for file_path in files:
                    try:
                        data = self.core_api.read_plist_from_zip(file_path)
                        found_file = file_path
                        break
                    except Exception:
                        continue
            if data:
                break

        if data:
            self.metadata_extracted['system_version'] = {
                'product_version': data.get('ProductVersion'),
                'product_build_version': data.get('ProductBuildVersion'),
                'product_name': data.get('ProductName'),
            }
            self.core_api.log_info(f"Extracted system version from: {found_file}")
        else:
            self.errors.append({
                'source': 'SystemVersion.plist/LastBuildInfo.plist',
                'error': 'System version plist not found in ZIP'
            })
            self.core_api.log_warning("System version plist not found")

    def _extract_device_identifiers(self) -> None:
        """Extract device serial number, UDID, and activation state."""
        # Search for data_ark.plist which contains device identifiers
        patterns = [
            'data_ark.plist',
            '*mobileactivationd*data_ark.plist',
        ]

        for pattern in patterns:
            files = self.core_api.find_files_in_zip(pattern)
            for file_path in files:
                try:
                    data = self.core_api.read_plist_from_zip(file_path)

                    self.metadata_extracted['device_identifiers'] = {
                        'serial_number': data.get('SerialNumber'),
                        'unique_device_id': data.get('UniqueDeviceID'),
                        'activation_state': data.get('ActivationState'),
                        'device_name': data.get('DeviceName'),
                    }

                    # If we successfully extracted data, return
                    if self.metadata_extracted['device_identifiers'].get('serial_number'):
                        self.core_api.log_info(f"Extracted device identifiers from: {file_path}")
                        return

                except Exception as e:
                    self.core_api.log_error(f"Error parsing {file_path}: {e}")
                    continue

        # Also try to extract from commcenter plist which may have activation state
        commcenter_files = self.core_api.find_files_in_zip('com.apple.commcenter.device_specific_nobackup.plist')
        if commcenter_files:
            try:
                data = self.core_api.read_plist_from_zip(commcenter_files[0])
                if 'device_identifiers' not in self.metadata_extracted:
                    self.metadata_extracted['device_identifiers'] = {}

                # Extract activation state if available
                if data.get('ActivationState'):
                    self.metadata_extracted['device_identifiers']['activation_state'] = data.get('ActivationState')

                self.core_api.log_info(f"Extracted additional device info from: {commcenter_files[0]}")
            except Exception as e:
                self.core_api.log_error(f"Error parsing commcenter plist: {e}")

        if 'device_identifiers' not in self.metadata_extracted:
            self.errors.append({
                'source': 'device identifiers',
                'error': 'Could not find device identifier files'
            })

    def _extract_cellular_info(self) -> None:
        """Extract IMEI, MEID, ICCID information."""
        # Search for commcenter device specific plist
        files = self.core_api.find_files_in_zip('com.apple.commcenter.device_specific_nobackup.plist')

        if files:
            try:
                data = self.core_api.read_plist_from_zip(files[0])

                # Try multiple key names for IMEI (different iOS versions use different keys)
                imei = (
                    data.get('kCTIMEI') or
                    data.get('IMEI') or
                    data.get('imeis') or  # Newer iOS versions use 'imeis'
                    data.get('kEnableIMEI')
                )

                # Handle imeis which may be a string containing multiple IMEIs
                if isinstance(imei, str) and '_' in imei:
                    # Split multiple IMEIs
                    imei = imei.split('_')[0]

                self.metadata_extracted['cellular_info'] = {
                    'imei': imei,
                    'meid': data.get('kCTMEID') or data.get('MEID') or data.get('meid'),
                    'iccid': data.get('kCTICCID') or data.get('ICCID') or data.get('LastKnownICCID'),
                    'imsi': data.get('ReportedSubscriberIdentity'),
                }

                self.core_api.log_info(f"Extracted cellular info from: {files[0]}")
                return
            except Exception as e:
                self.core_api.log_warning(f"Could not extract from {files[0]}: {e}")

        # Try CellularUsage database as fallback
        db_files = self.core_api.find_files_in_zip('CellularUsage.db')
        if db_files:
            try:
                # Query for subscriber info if available
                results = self.core_api.query_sqlite_from_zip_dict(
                    db_files[0],
                    "SELECT subscriber_id, subscriber_mdn FROM subscriber LIMIT 1"
                )
                if results:
                    if 'cellular_info' not in self.metadata_extracted:
                        self.metadata_extracted['cellular_info'] = {}
                    self.metadata_extracted['cellular_info']['subscriber_id'] = results[0].get('subscriber_id')
                    self.metadata_extracted['cellular_info']['subscriber_mdn'] = results[0].get('subscriber_mdn')
                    self.core_api.log_info(f"Extracted subscriber info from: {db_files[0]}")
                    return
            except Exception as e:
                self.core_api.log_warning(f"Could not extract from CellularUsage.db: {e}")

        self.errors.append({
            'source': 'cellular info',
            'error': 'Could not extract IMEI/MEID/ICCID'
        })

    def _extract_carrier_info(self) -> None:
        """Extract carrier and phone number information."""
        # First try device_specific_nobackup.plist which has more reliable phone number
        device_specific_files = self.core_api.find_files_in_zip('com.apple.commcenter.device_specific_nobackup.plist')
        if device_specific_files:
            try:
                data = self.core_api.read_plist_from_zip(device_specific_files[0])

                self.metadata_extracted['carrier_info'] = {
                    'phone_number': data.get('ReportedPhoneNumber'),
                    'operator_name': data.get('OperatorName'),
                    'carrier_bundle_version': data.get('CarrierBundleVersion'),
                }

                self.core_api.log_info(f"Extracted carrier info from: {device_specific_files[0]}")

                # If we got a phone number, we're done
                if self.metadata_extracted['carrier_info'].get('phone_number'):
                    return
            except Exception as e:
                self.core_api.log_warning(f"Could not extract from device_specific_nobackup.plist: {e}")

        # Try commcenter.plist as fallback
        commcenter_files = self.core_api.find_files_in_zip('com.apple.commcenter.plist')
        if commcenter_files:
            try:
                data = self.core_api.read_plist_from_zip(commcenter_files[0])

                if 'carrier_info' not in self.metadata_extracted:
                    self.metadata_extracted['carrier_info'] = {}

                # Update with any additional info
                if not self.metadata_extracted['carrier_info'].get('phone_number'):
                    # Try multiple phone number keys
                    phone = None
                    for key in ['PhoneNumber', 'ReportedPhoneNumber']:
                        if data.get(key):
                            phone = data.get(key)
                            break
                    # Also check nested com.apple.carrier_1
                    carrier_data = data.get('com.apple.carrier_1', {})
                    if isinstance(carrier_data, dict):
                        phone = phone or carrier_data.get('PhoneNumber')

                    self.metadata_extracted['carrier_info']['phone_number'] = phone

                if not self.metadata_extracted['carrier_info'].get('operator_name'):
                    self.metadata_extracted['carrier_info']['operator_name'] = data.get('OperatorName')

                # Extract last known info
                self.metadata_extracted['carrier_info']['last_known_iccid'] = data.get('LastKnownICCID')
                self.metadata_extracted['carrier_info']['last_known_serving_mcc'] = data.get('LastKnownServingMcc')
                self.metadata_extracted['carrier_info']['last_known_serving_mnc'] = data.get('LastKnownServingMnc')

                self.core_api.log_info(f"Extracted additional carrier info from: {commcenter_files[0]}")
                return
            except Exception as e:
                self.core_api.log_warning(f"Could not extract from commcenter.plist: {e}")

        if 'carrier_info' not in self.metadata_extracted:
            self.errors.append({
                'source': 'carrier info',
                'error': 'Could not find carrier info files'
            })

    def _extract_icloud_accounts(self) -> None:
        """Extract iCloud account information from Accounts database."""
        # Search for Accounts database
        db_files = self.core_api.find_files_in_zip('Accounts3.sqlite')

        if not db_files:
            # Try alternate names
            db_files = self.core_api.find_files_in_zip('*Accounts*.sqlite')

        if db_files:
            try:
                query = """
                    SELECT
                        ZACCOUNTTYPE.ZACCOUNTTYPEDESCRIPTION as account_type,
                        ZACCOUNT.ZUSERNAME as username,
                        datetime(ZACCOUNT.ZDATE + 978307200, 'unixepoch') as date_added
                    FROM ZACCOUNT
                    LEFT JOIN ZACCOUNTTYPE ON ZACCOUNT.ZACCOUNTTYPE = ZACCOUNTTYPE.Z_PK
                """

                results = self.core_api.query_sqlite_from_zip_dict(
                    db_files[0], query
                )

                self.metadata_extracted['accounts'] = results
                self.core_api.log_info(f"Extracted accounts from: {db_files[0]}")

            except Exception as e:
                self.errors.append({'source': db_files[0], 'error': str(e)})
                self.core_api.log_warning(f"Could not extract iCloud accounts: {e}")
        else:
            self.errors.append({
                'source': 'Accounts3.sqlite',
                'error': 'Accounts database not found in ZIP'
            })

    def _extract_backup_info(self) -> None:
        """Extract iTunes/Finder backup information."""
        # Search for MobileBackup plist
        files = self.core_api.find_files_in_zip('com.apple.MobileBackup.plist')

        if files:
            try:
                data = self.core_api.read_plist_from_zip(files[0])

                self.metadata_extracted['backup_info'] = {
                    'last_backup_date': data.get('LastBackupDate'),
                    'backup_computer_name': data.get('BackupComputerName'),
                    'backup_computer': data.get('BackupComputer'),
                }

                self.core_api.log_info(f"Extracted backup info from: {files[0]}")
            except Exception as e:
                self.errors.append({'source': files[0], 'error': str(e)})
                self.core_api.log_warning(f"Could not extract backup info: {e}")
        else:
            self.errors.append({
                'source': 'com.apple.MobileBackup.plist',
                'error': 'MobileBackup plist not found in ZIP'
            })

    def _extract_timezone_locale(self) -> None:
        """Extract timezone and locale settings."""
        # Search for GlobalPreferences plist
        files = self.core_api.find_files_in_zip('.GlobalPreferences.plist')

        if not files:
            # Try without the dot prefix
            files = self.core_api.find_files_in_zip('*GlobalPreferences.plist')

        if files:
            try:
                data = self.core_api.read_plist_from_zip(files[0])

                self.metadata_extracted['timezone_locale'] = {
                    'locale': data.get('AppleLocale'),
                    'languages': data.get('AppleLanguages'),
                    'keyboard': data.get('AppleKeyboards'),
                }

                self.core_api.log_info(f"Extracted locale settings from: {files[0]}")
            except Exception as e:
                self.errors.append({'source': files[0], 'error': str(e)})
                self.core_api.log_warning(f"Could not extract timezone/locale: {e}")
        else:
            self.errors.append({
                'source': '.GlobalPreferences.plist',
                'error': 'GlobalPreferences plist not found in ZIP'
            })

        # Try to get timezone from datetime preferences
        tz_files = self.core_api.find_files_in_zip('com.apple.preferences.datetime.plist')
        if tz_files:
            try:
                data = self.core_api.read_plist_from_zip(tz_files[0])
                if 'timezone_locale' not in self.metadata_extracted:
                    self.metadata_extracted['timezone_locale'] = {}
                self.metadata_extracted['timezone_locale']['timezone'] = data.get('timezone')
                self.core_api.log_info(f"Extracted timezone from: {tz_files[0]}")
            except Exception:
                pass

        # Also try com.apple.preferences.plist for additional locale info
        pref_files = self.core_api.find_files_in_zip('com.apple.preferences.plist')
        if pref_files:
            try:
                data = self.core_api.read_plist_from_zip(pref_files[0])
                if 'timezone_locale' not in self.metadata_extracted:
                    self.metadata_extracted['timezone_locale'] = {}
                # Extract any additional locale/preferences info
                if data.get('AppleLocale'):
                    self.metadata_extracted['timezone_locale']['locale'] = data.get('AppleLocale')
                self.core_api.log_info(f"Extracted additional preferences from: {pref_files[0]}")
            except Exception:
                pass

    def _format_device_info(self) -> Dict[str, Any]:
        """Format extracted metadata into structured output."""
        system_version = self.metadata_extracted.get('system_version', {})
        device_ids = self.metadata_extracted.get('device_identifiers', {})
        cellular = self.metadata_extracted.get('cellular_info', {})
        carrier = self.metadata_extracted.get('carrier_info', {})
        backup = self.metadata_extracted.get('backup_info', {})
        tz_locale = self.metadata_extracted.get('timezone_locale', {})
        accounts = self.metadata_extracted.get('accounts', [])

        # Find iCloud accounts
        icloud_accounts = [
            acc for acc in accounts if 'icloud' in str(acc.get('account_type', '')).lower()
        ]

        return {
            'ios_version': system_version.get('product_version'),
            'ios_build': system_version.get('product_build_version'),
            'product_name': system_version.get('product_name'),
            'device_name': device_ids.get('device_name'),
            'serial_number': device_ids.get('serial_number'),
            'udid': device_ids.get('unique_device_id'),
            'activation_state': device_ids.get('activation_state'),
            'imei': cellular.get('imei'),
            'meid': cellular.get('meid'),
            'iccid': cellular.get('iccid') or carrier.get('last_known_iccid'),
            'imsi': cellular.get('imsi'),
            'phone_number': carrier.get('phone_number'),
            'carrier': carrier.get('operator_name'),
            'mcc': carrier.get('last_known_serving_mcc'),
            'mnc': carrier.get('last_known_serving_mnc'),
            'last_backup_date': str(backup.get('last_backup_date'))
            if backup.get('last_backup_date')
            else None,
            'backup_computer_name': backup.get('backup_computer_name'),
            'timezone': tz_locale.get('timezone'),
            'locale': tz_locale.get('locale'),
            'languages': tz_locale.get('languages'),
            'icloud_accounts': icloud_accounts,
            'all_accounts': accounts,
        }

    def _display_summary(self) -> None:
        """Display summary table of extracted device information."""
        from rich.table import Table

        device_info = self._format_device_info()

        table = Table(title="iOS Device Information Summary")
        table.add_column("Property", style="cyan", no_wrap=True)
        table.add_column("Value", style="green")

        # Add rows with available data
        if device_info.get('ios_version'):
            table.add_row("iOS Version", str(device_info['ios_version']))
        if device_info.get('ios_build'):
            table.add_row("iOS Build", str(device_info['ios_build']))
        if device_info.get('device_name'):
            table.add_row("Device Name", str(device_info['device_name']))
        if device_info.get('serial_number'):
            table.add_row("Serial Number", str(device_info['serial_number']))
        if device_info.get('udid'):
            udid_str = str(device_info['udid'])
            table.add_row("UDID", udid_str[:30] + "..." if len(udid_str) > 30 else udid_str)
        if device_info.get('imei'):
            table.add_row("IMEI", str(device_info['imei']))
        if device_info.get('imsi'):
            table.add_row("IMSI", str(device_info['imsi']))
        if device_info.get('iccid'):
            table.add_row("ICCID", str(device_info['iccid']))
        if device_info.get('phone_number'):
            table.add_row("Phone Number", str(device_info['phone_number']))
        if device_info.get('carrier'):
            table.add_row("Carrier", str(device_info['carrier']))
        if device_info.get('mcc') and device_info.get('mnc'):
            table.add_row("MCC/MNC", f"{device_info['mcc']}/{device_info['mnc']}")
        if device_info.get('locale'):
            table.add_row("Locale", str(device_info['locale']))

        # iCloud accounts
        if device_info.get('icloud_accounts'):
            for acc in device_info['icloud_accounts'][:3]:  # Show first 3
                table.add_row("iCloud Account", acc.get('username', 'N/A'))

        self.core_api.console.print()
        self.core_api.console.print(table)

        if self.errors:
            self.core_api.print_warning(
                f"Encountered {len(self.errors)} errors during extraction (see report for details)"
            )

    def _generate_report(self) -> Path:
        """Generate markdown report."""
        device_info = self._format_device_info()

        sections = [
            {
                "heading": "Device Summary",
                "content": (
                    f"**iOS Version:** {device_info.get('ios_version') or 'N/A'}  \n"
                    f"**Serial Number:** {device_info.get('serial_number') or 'N/A'}  \n"
                    f"**IMEI:** {device_info.get('imei') or 'N/A'}  \n"
                    f"**Phone Number:** {device_info.get('phone_number') or 'N/A'}  \n"
                    f"**Carrier:** {device_info.get('carrier') or 'N/A'}  \n"
                ),
            },
        ]

        # System Information
        system_info = {
            "iOS Version": device_info.get('ios_version'),
            "iOS Build": device_info.get('ios_build'),
            "Product Name": device_info.get('product_name'),
        }
        sections.append({
            "heading": "System Information",
            "content": {k: v for k, v in system_info.items() if v},
            "style": "table",
        })

        # Device Identifiers
        device_ids = {
            "Device Name": device_info.get('device_name'),
            "Serial Number": device_info.get('serial_number'),
            "UDID": device_info.get('udid'),
            "Activation State": device_info.get('activation_state'),
        }
        sections.append({
            "heading": "Device Identifiers",
            "content": {k: v for k, v in device_ids.items() if v},
            "style": "table",
        })

        # Cellular Information
        cellular_info = {
            "IMEI": device_info.get('imei'),
            "MEID": device_info.get('meid'),
            "ICCID": device_info.get('iccid'),
            "IMSI": device_info.get('imsi'),
            "Phone Number": device_info.get('phone_number'),
            "Carrier": device_info.get('carrier'),
            "MCC": device_info.get('mcc'),
            "MNC": device_info.get('mnc'),
        }
        sections.append({
            "heading": "Cellular Information",
            "content": {k: v for k, v in cellular_info.items() if v},
            "style": "table",
        })

        # iCloud Accounts
        if device_info.get('icloud_accounts'):
            accounts_table = []
            for acc in device_info['icloud_accounts']:
                accounts_table.append({
                    "Account Type": acc.get('account_type', 'N/A'),
                    "Username": acc.get('username', 'N/A'),
                    "Date Added": acc.get('date_added', 'N/A'),
                })
            sections.append({
                "heading": "iCloud Accounts",
                "content": accounts_table,
                "style": "table",
            })

        # Backup Information
        if device_info.get('last_backup_date') or device_info.get('backup_computer_name'):
            backup_info = {
                "Last Backup Date": device_info.get('last_backup_date'),
                "Backup Computer": device_info.get('backup_computer_name'),
            }
            sections.append({
                "heading": "Backup Information",
                "content": {k: v for k, v in backup_info.items() if v},
                "style": "table",
            })

        # Locale Settings
        locale_info = {
            "Timezone": device_info.get('timezone'),
            "Locale": device_info.get('locale'),
            "Languages": ', '.join(device_info.get('languages', []))
            if device_info.get('languages')
            else None,
        }
        sections.append({
            "heading": "Locale Settings",
            "content": {k: v for k, v in locale_info.items() if v},
            "style": "table",
        })

        # Errors
        if self.errors:
            sections.append({
                "heading": "Extraction Errors",
                "content": self.errors,
                "style": "table",
            })

        metadata = {
            "Device Name": device_info.get('device_name', 'Unknown'),
            "iOS Version": device_info.get('ios_version', 'Unknown'),
            "ZIP File": self.core_api.get_current_zip().name
            if self.core_api.get_current_zip()
            else "Unknown",
        }

        return self.core_api.generate_report(
            plugin_name="iOSDeviceInfoExtractor",
            title="iOS Device Information Extraction Report",
            sections=sections,
            metadata=metadata,
        )

    def _export_to_json(self, output_path: Path) -> None:
        """Export device info to JSON file using CoreAPI method."""
        device_info = self._format_device_info()

        self.core_api.export_plugin_data_to_json(
            output_path=output_path,
            plugin_name=self.metadata.name,
            plugin_version=self.metadata.version,
            data=device_info,
            extraction_type=self.extraction_type,
            errors=self.errors,
        )

    def cleanup(self) -> None:
        """Clean up temporary resources."""
        self.core_api.log_info(f"Cleaning up {self.metadata.name}")
