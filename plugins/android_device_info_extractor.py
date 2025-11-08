"""
Android Device Information Extractor Plugin for YaFT

This plugin extracts comprehensive device metadata from Android full filesystem extractions,
including build properties, device identifiers, IMEI/serial numbers, carrier info,
accounts, WiFi/Bluetooth MAC addresses, and system settings.

Supports both Cellebrite and GrayKey extraction formats.

Based on forensic research documented in docs/PluginResearch.md
"""

import re
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional

from yaft.core.api import CoreAPI
from yaft.core.plugin_base import PluginBase, PluginMetadata


class AndroidDeviceInfoExtractorPlugin(PluginBase):
    """
    Android Device Information Extractor for comprehensive device metadata analysis.

    Extracts device information from multiple sources including build.prop, databases,
    system settings, and configuration files to provide a complete picture of the Android device.
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
            name="AndroidDeviceInfoExtractor",
            version="1.0.0",
            description=(
                "Extract comprehensive device metadata from Android filesystem extractions"
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
        self.metadata_extracted = {}
        self.errors = []

    def execute(self, *args: Any, **kwargs: Any) -> Dict[str, Any]:
        """
        Execute Android device information extraction.

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

            # Extract from all sources
            self.core_api.print_info("Extracting build properties...")
            self._extract_build_properties()

            self.core_api.print_info("Extracting settings databases...")
            self._extract_settings_databases()

            self.core_api.print_info("Extracting telephony information...")
            self._extract_telephony_info()

            self.core_api.print_info("Extracting accounts information...")
            self._extract_accounts()

            self.core_api.print_info("Extracting network information...")
            self._extract_network_info()

            self.core_api.print_info("Extracting Bluetooth information...")
            self._extract_bluetooth_info()

            # Display summary
            self._display_summary()

            # Generate report
            report_path = self._generate_report()
            self.core_api.print_success(f"Report generated: {report_path}")

            # Export to JSON
            output_dir = self.core_api.get_case_output_dir("android_device_info")
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

    def _extract_build_properties(self) -> None:
        """Extract device information from build.prop."""
        build_prop_path = 'system/build.prop'

        try:
            content = self.core_api.read_zip_file_text(self._normalize_path(build_prop_path))

            props = {}
            for line in content.split('\n'):
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    props[key.strip()] = value.strip()

            # Map to standardized keys
            self.metadata_extracted['build_properties'] = {
                'manufacturer': self._get_prop_value(
                    props, ['ro.product.manufacturer', 'ro.product.vendor.manufacturer']
                ),
                'brand': self._get_prop_value(
                    props, ['ro.product.brand', 'ro.product.vendor.brand']
                ),
                'model': self._get_prop_value(
                    props, ['ro.product.model', 'ro.product.vendor.model']
                ),
                'device': self._get_prop_value(
                    props, ['ro.product.device', 'ro.product.vendor.device']
                ),
                'android_version': props.get('ro.build.version.release'),
                'sdk_version': props.get('ro.build.version.sdk'),
                'security_patch': props.get('ro.build.version.security_patch'),
                'build_id': props.get('ro.build.id'),
                'build_fingerprint': props.get('ro.build.fingerprint'),
                'serial': self._get_prop_value(props, ['ro.serialno', 'ro.boot.serialno']),
                'hardware': self._get_prop_value(props, ['ro.hardware', 'ro.hardware.chipname']),
                'bootloader': props.get('ro.bootloader'),
            }

        except (KeyError, Exception) as e:
            self.errors.append({'source': build_prop_path, 'error': str(e)})
            self.core_api.log_error(f"Error parsing build.prop: {e}")

    def _get_prop_value(self, props: Dict[str, str], keys: List[str]) -> Optional[str]:
        """Get property value from list of possible keys."""
        for key in keys:
            if key in props:
                return props[key]
        return None

    def _extract_settings_databases(self) -> None:
        """Extract settings from Android settings databases."""
        # Settings Secure
        settings_secure_path = 'data/system/users/0/settings_secure.db'
        try:
            query = "SELECT name, value FROM secure"
            results = self.core_api.query_sqlite_from_zip_dict(
                self._normalize_path(settings_secure_path), query
            )

            settings_secure = {item['name']: item['value'] for item in results}
            self.metadata_extracted['settings_secure'] = {
                'android_id': settings_secure.get('android_id'),
                'bluetooth_name': settings_secure.get('bluetooth_name'),
                'default_input_method': settings_secure.get('default_input_method'),
            }

        except (KeyError, Exception) as e:
            self.errors.append({'source': settings_secure_path, 'error': str(e)})
            self.core_api.log_warning(f"Could not extract settings_secure.db: {e}")

        # Settings Global
        settings_global_path = 'data/system/users/0/settings_global.db'
        try:
            query = "SELECT name, value FROM global"
            results = self.core_api.query_sqlite_from_zip_dict(
                self._normalize_path(settings_global_path), query
            )

            settings_global = {item['name']: item['value'] for item in results}
            self.metadata_extracted['settings_global'] = {
                'device_name': settings_global.get('device_name'),
                'adb_enabled': settings_global.get('adb_enabled') == '1',
                'development_settings_enabled': settings_global.get(
                    'development_settings_enabled'
                )
                == '1',
            }

        except (KeyError, Exception) as e:
            self.errors.append({'source': settings_global_path, 'error': str(e)})
            self.core_api.log_warning(f"Could not extract settings_global.db: {e}")

    def _extract_telephony_info(self) -> None:
        """Extract SIM card and carrier information."""
        telephony_path = 'data/user_de/0/com.android.providers.telephony/databases/telephony.db'

        try:
            query = """
                SELECT
                    display_name,
                    icc_id,
                    number as phone_number,
                    mcc,
                    mnc,
                    carrier_name
                FROM siminfo
            """

            results = self.core_api.query_sqlite_from_zip_dict(
                self._normalize_path(telephony_path), query
            )

            self.metadata_extracted['telephony'] = results

        except (KeyError, Exception) as e:
            self.errors.append({'source': telephony_path, 'error': str(e)})
            self.core_api.log_warning(f"Could not extract telephony info: {e}")

    def _extract_accounts(self) -> None:
        """Extract account information."""
        accounts_path = 'data/system_ce/0/accounts_ce.db'

        try:
            query = """
                SELECT
                    name as account_name,
                    type as account_type
                FROM accounts
            """

            results = self.core_api.query_sqlite_from_zip_dict(
                self._normalize_path(accounts_path), query
            )

            self.metadata_extracted['accounts'] = results

        except (KeyError, Exception) as e:
            self.errors.append({'source': accounts_path, 'error': str(e)})
            self.core_api.log_warning(f"Could not extract accounts: {e}")

    def _extract_network_info(self) -> None:
        """Extract WiFi MAC address."""
        wifi_mac_path = 'sys/class/net/wlan0/address'

        try:
            mac_address = self.core_api.read_zip_file_text(
                self._normalize_path(wifi_mac_path)
            ).strip()
            self.metadata_extracted['wifi_mac'] = mac_address

        except (KeyError, Exception) as e:
            self.errors.append({'source': wifi_mac_path, 'error': str(e)})
            self.core_api.log_warning(f"Could not extract WiFi MAC: {e}")

    def _extract_bluetooth_info(self) -> None:
        """Extract Bluetooth MAC and paired devices."""
        bt_config_path = 'data/misc/bluedroid/bt_config.conf'

        try:
            content = self.core_api.read_zip_file_text(self._normalize_path(bt_config_path))

            bt_info = {
                'local_address': None,
                'local_name': None,
                'paired_devices': [],
            }

            current_section = None
            device_info = {}

            for line in content.split('\n'):
                line = line.strip()

                # Section headers
                if line.startswith('[') and line.endswith(']'):
                    if current_section and current_section.startswith('Remote'):
                        bt_info['paired_devices'].append(device_info)

                    current_section = line[1:-1]
                    device_info = {}

                    if current_section.startswith('Remote'):
                        device_info['address'] = current_section.replace('Remote ', '')

                # Key-value pairs
                elif '=' in line:
                    key, value = line.split('=', 1)
                    key = key.strip()
                    value = value.strip()

                    if current_section == 'Local':
                        if key == 'Address':
                            bt_info['local_address'] = value
                        elif key == 'Name':
                            bt_info['local_name'] = value
                    elif current_section and current_section.startswith('Remote'):
                        device_info[key.lower()] = value

            # Don't forget last device
            if current_section and current_section.startswith('Remote') and device_info:
                bt_info['paired_devices'].append(device_info)

            self.metadata_extracted['bluetooth'] = bt_info

        except (KeyError, Exception) as e:
            self.errors.append({'source': bt_config_path, 'error': str(e)})
            self.core_api.log_warning(f"Could not extract Bluetooth info: {e}")

    def _format_device_info(self) -> Dict[str, Any]:
        """Format extracted metadata into structured output."""
        build = self.metadata_extracted.get('build_properties', {})
        settings_secure = self.metadata_extracted.get('settings_secure', {})
        settings_global = self.metadata_extracted.get('settings_global', {})
        telephony = self.metadata_extracted.get('telephony', [])
        accounts = self.metadata_extracted.get('accounts', [])
        bluetooth = self.metadata_extracted.get('bluetooth', {})
        wifi_mac = self.metadata_extracted.get('wifi_mac')

        # Get first SIM info
        sim_info = telephony[0] if telephony else {}

        # Find Google accounts
        google_accounts = [
            acc for acc in accounts if 'google' in str(acc.get('account_type', '')).lower()
        ]

        return {
            'manufacturer': build.get('manufacturer'),
            'brand': build.get('brand'),
            'model': build.get('model'),
            'device_codename': build.get('device'),
            'android_version': build.get('android_version'),
            'sdk_version': build.get('sdk_version'),
            'security_patch': build.get('security_patch'),
            'build_id': build.get('build_id'),
            'build_fingerprint': build.get('build_fingerprint'),
            'serial_number': build.get('serial'),
            'hardware': build.get('hardware'),
            'bootloader_version': build.get('bootloader'),
            'android_id': settings_secure.get('android_id'),
            'device_name': settings_global.get('device_name'),
            'bluetooth_name': settings_secure.get('bluetooth_name'),
            'bluetooth_mac': bluetooth.get('local_address'),
            'wifi_mac': wifi_mac,
            'iccid': sim_info.get('icc_id'),
            'phone_number': sim_info.get('phone_number'),
            'carrier_name': sim_info.get('carrier_name'),
            'mcc': sim_info.get('mcc'),
            'mnc': sim_info.get('mnc'),
            'adb_enabled': settings_global.get('adb_enabled'),
            'developer_mode': settings_global.get('development_settings_enabled'),
            'google_accounts': google_accounts,
            'all_accounts': accounts,
            'bluetooth_paired_devices': bluetooth.get('paired_devices', []),
        }

    def _display_summary(self) -> None:
        """Display summary table of extracted device information."""
        from rich.table import Table

        device_info = self._format_device_info()

        table = Table(title="Android Device Information Summary")
        table.add_column("Property", style="cyan", no_wrap=True)
        table.add_column("Value", style="green")

        # Add rows with available data
        if device_info.get('manufacturer'):
            table.add_row("Manufacturer", device_info['manufacturer'])
        if device_info.get('model'):
            table.add_row("Model", device_info['model'])
        if device_info.get('android_version'):
            table.add_row("Android Version", device_info['android_version'])
        if device_info.get('security_patch'):
            table.add_row("Security Patch", device_info['security_patch'])
        if device_info.get('serial_number'):
            table.add_row("Serial Number", device_info['serial_number'])
        if device_info.get('android_id'):
            table.add_row("Android ID", device_info['android_id'])
        if device_info.get('phone_number'):
            table.add_row("Phone Number", device_info['phone_number'])
        if device_info.get('carrier_name'):
            table.add_row("Carrier", device_info['carrier_name'])
        if device_info.get('wifi_mac'):
            table.add_row("WiFi MAC", device_info['wifi_mac'])

        # Google accounts
        if device_info.get('google_accounts'):
            for acc in device_info['google_accounts'][:3]:  # Show first 3
                table.add_row("Google Account", acc.get('account_name', 'N/A'))

        # Security warnings
        if device_info.get('adb_enabled'):
            table.add_row("[red]WARNING[/red]", "[red]ADB is enabled[/red]")
        if device_info.get('developer_mode'):
            table.add_row("[yellow]NOTE[/yellow]", "[yellow]Developer mode is enabled[/yellow]")

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
                    f"**Manufacturer:** {device_info.get('manufacturer') or 'N/A'}  \n"
                    f"**Model:** {device_info.get('model') or 'N/A'}  \n"
                    f"**Android Version:** {device_info.get('android_version') or 'N/A'}  \n"
                    f"**Serial Number:** {device_info.get('serial_number') or 'N/A'}  \n"
                    f"**Phone Number:** {device_info.get('phone_number') or 'N/A'}  \n"
                ),
            },
        ]

        # Build Information
        build_info = {
            "Manufacturer": device_info.get('manufacturer'),
            "Brand": device_info.get('brand'),
            "Model": device_info.get('model'),
            "Device Codename": device_info.get('device_codename'),
            "Android Version": device_info.get('android_version'),
            "SDK Version": device_info.get('sdk_version'),
            "Security Patch": device_info.get('security_patch'),
            "Build ID": device_info.get('build_id'),
            "Build Fingerprint": device_info.get('build_fingerprint'),
            "Hardware": device_info.get('hardware'),
            "Bootloader": device_info.get('bootloader_version'),
        }
        sections.append({
            "heading": "Build Information",
            "content": {k: v for k, v in build_info.items() if v},
            "style": "table",
        })

        # Device Identifiers
        identifiers = {
            "Serial Number": device_info.get('serial_number'),
            "Android ID": device_info.get('android_id'),
            "Device Name": device_info.get('device_name'),
            "Bluetooth Name": device_info.get('bluetooth_name'),
        }
        sections.append({
            "heading": "Device Identifiers",
            "content": {k: v for k, v in identifiers.items() if v},
            "style": "table",
        })

        # Network Information
        network_info = {
            "WiFi MAC": device_info.get('wifi_mac'),
            "Bluetooth MAC": device_info.get('bluetooth_mac'),
            "Phone Number": device_info.get('phone_number'),
            "ICCID": device_info.get('iccid'),
            "Carrier": device_info.get('carrier_name'),
            "MCC": device_info.get('mcc'),
            "MNC": device_info.get('mnc'),
        }
        sections.append({
            "heading": "Network Information",
            "content": {k: v for k, v in network_info.items() if v},
            "style": "table",
        })

        # Google Accounts
        if device_info.get('google_accounts'):
            accounts_table = []
            for acc in device_info['google_accounts']:
                accounts_table.append({
                    "Account Type": acc.get('account_type', 'N/A'),
                    "Account Name": acc.get('account_name', 'N/A'),
                })
            sections.append({
                "heading": "Google Accounts",
                "content": accounts_table,
                "style": "table",
            })

        # Bluetooth Paired Devices
        if device_info.get('bluetooth_paired_devices'):
            bt_table = []
            for dev in device_info['bluetooth_paired_devices'][:10]:  # Limit to 10
                bt_table.append({
                    "Device Address": dev.get('address', 'N/A'),
                    "Device Name": dev.get('name', 'N/A'),
                })
            sections.append({
                "heading": "Bluetooth Paired Devices",
                "content": bt_table,
                "style": "table",
            })

        # Security Settings
        security_info = {
            "ADB Enabled": "Yes" if device_info.get('adb_enabled') else "No",
            "Developer Mode": "Yes" if device_info.get('developer_mode') else "No",
        }
        sections.append({
            "heading": "Security Settings",
            "content": security_info,
            "style": "table",
        })

        # Forensic Notes
        forensic_notes = []
        if device_info.get('adb_enabled'):
            forensic_notes.append("⚠️ WARNING: ADB was enabled on device - potential security risk")
        if device_info.get('developer_mode'):
            forensic_notes.append("ℹ️ Developer options were enabled")
        if 'test-keys' in str(device_info.get('build_fingerprint', '')):
            forensic_notes.append(
                "⚠️ WARNING: Device has test/unsigned build - may indicate custom ROM"
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
            "Device Model": device_info.get('model', 'Unknown'),
            "Android Version": device_info.get('android_version', 'Unknown'),
            "ZIP File": self.core_api.get_current_zip().name
            if self.core_api.get_current_zip()
            else "Unknown",
        }

        return self.core_api.generate_report(
            plugin_name="AndroidDeviceInfoExtractor",
            title="Android Device Information Extraction Report",
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
