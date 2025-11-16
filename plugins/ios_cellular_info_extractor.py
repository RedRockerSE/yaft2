"""
iOS Cellular Information Extractor Plugin

Extracts cellular information (IMEI, IMSI, ICCI, Phone Number) from iOS device extractions.

Based on iLEAPP artifact by @AlexisBrignoni and @stark4n6
Adapted for YAFT framework with Core API integration.

Author: YAFT Development Team
Version: 1.0.0
Date: 2025-01-15
"""

from pathlib import Path
from typing import Any, Dict, List, Tuple

from yaft.core.api import CoreAPI
from yaft.core.plugin_base import PluginBase, PluginMetadata


class iOSCellularInfoExtractorPlugin(PluginBase):
    """
    Extract cellular information from iOS device extractions.

    This plugin parses the com.apple.commcenter.plist file to extract:
    - IMSI (International Mobile Subscriber Identity)
    - IMEI (International Mobile Equipment Identity)
    - ICCI (Integrated Circuit Card Identifier)
    - Phone Number
    - Other cellular configuration data

    Supports both Cellebrite and GrayKey extraction formats.
    """

    def __init__(self, core_api: CoreAPI) -> None:
        super().__init__(core_api)
        self.extraction_type: str = "unknown"
        self.zip_prefix: str = ""
        self.cellular_data: List[Tuple[str, str]] = []
        self.errors: List[str] = []

    @property
    def metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name="iOSCellularInfoExtractor",
            version="1.0.0",
            description="Extract cellular information (IMEI, IMSI, ICCI, Phone Number) from iOS devices",
            author="YAFT Development Team (based on iLEAPP by @AlexisBrignoni, @stark4n6)",
            target_os=["ios"],
            requires_core_version=">=0.1.0",
            dependencies=[],
            enabled=True,
        )

    def initialize(self) -> None:
        """Initialize the plugin."""
        self.core_api.log_info(f"Initializing {self.metadata.name}")
        self.cellular_data = []
        self.errors = []

    def execute(self, *args: Any, **kwargs: Any) -> Dict[str, Any]:
        """
        Execute the cellular information extraction.

        Returns:
            Dict containing success status, report path, and extracted data
        """
        self.core_api.print_info("Starting iOS Cellular Information Extraction...")

        # Check if ZIP file is loaded
        if not self.core_api.get_current_zip():
            self.core_api.print_error("No ZIP file loaded")
            return {"success": False, "error": "No ZIP file loaded"}

        # Detect ZIP format
        self.extraction_type, self.zip_prefix = self.core_api.detect_zip_format()

        # Find and parse the cellular plist file
        success = self._extract_cellular_info()

        if not success:
            self.core_api.print_error("Failed to extract cellular information")
            return {
                "success": False,
                "error": "No cellular data found or extraction failed",
                "errors": self.errors
            }

        # Generate report
        report_path = self._generate_report()

        # Export to JSON
        json_path = self._export_to_json()

        self.core_api.print_success(
            f"Cellular information extraction complete! Found {len(self.cellular_data)} properties."
        )

        return {
            "success": True,
            "report_path": str(report_path),
            "json_path": str(json_path),
            "properties_found": len(self.cellular_data),
            "errors": self.errors
        }

    def cleanup(self) -> None:
        """Clean up plugin resources."""
        self.core_api.log_info(f"Cleaning up {self.metadata.name}")
        self.cellular_data.clear()
        self.errors.clear()

    def _extract_cellular_info(self) -> bool:
        """
        Extract cellular information from com.apple.commcenter.plist.

        Returns:
            bool: True if extraction successful, False otherwise
        """
        # Search for the cellular plist file
        plist_pattern = "*/wireless/Library/Preferences/com.apple.commcenter.plist"

        self.core_api.log_info(f"Searching for cellular plist files: {plist_pattern}")

        # Use Core API to find files
        plist_files = self.core_api.find_files_in_zip(plist_pattern)

        if not plist_files:
            # Try alternative search path
            plist_files = self.core_api.find_files_in_zip(
                "com.apple.commcenter.plist",
                search_path="wireless/Library/Preferences/"
            )

        if not plist_files:
            error_msg = "Cellular plist file not found in extraction"
            self.errors.append(error_msg)
            self.core_api.log_warning(error_msg)
            return False

        # Use the first match
        plist_path = plist_files[0]
        self.core_api.log_info(f"Found cellular plist: {plist_path}")

        # Parse the plist file
        try:
            plist_data = self.core_api.read_plist_from_zip(plist_path)
            self._parse_cellular_plist(plist_data, plist_path)
            return True

        except Exception as e:
            error_msg = f"Failed to parse cellular plist: {str(e)}"
            self.errors.append(error_msg)
            self.core_api.log_error(error_msg)
            return False

    def _parse_cellular_plist(self, plist_data: Dict, source_path: str) -> None:
        """
        Parse cellular plist data and extract information.

        Args:
            plist_data: Parsed plist dictionary
            source_path: Source file path in ZIP
        """
        self.core_api.log_info("Parsing cellular plist data...")

        for key, val in plist_data.items():
            if key == 'PersonalWallet':
                self._parse_personal_wallet(val, source_path)

            elif key == 'LastKnownICCI':
                last_known_icci = str(val) if val else ""
                self.cellular_data.append(('Last Known ICCI', last_known_icci))
                self.core_api.log_info(f"Last Known ICCI: {last_known_icci}")

            elif key == 'PhoneNumber':
                phone_number = str(val) if val else ""
                self.cellular_data.append(('Phone Number', phone_number))
                self.core_api.log_info(f"Phone Number: {phone_number}")

            else:
                # Store other properties
                value_str = str(val) if val is not None else ""
                # Limit very long values
                if len(value_str) > 200:
                    value_str = value_str[:200] + "..."
                self.cellular_data.append((key, value_str))

    def _parse_personal_wallet(self, personal_wallet: Dict, source_path: str) -> None:
        """
        Parse PersonalWallet section for IMSI and IMEI information.

        Args:
            personal_wallet: PersonalWallet dictionary
            source_path: Source file path in ZIP
        """
        try:
            # Get the first value from PersonalWallet
            if isinstance(personal_wallet, dict) and personal_wallet:
                wallet_data = list(personal_wallet.values())[0]

                if isinstance(wallet_data, dict) and 'CarrierEntitlements' in wallet_data:
                    carrier_entitlements = wallet_data['CarrierEntitlements']

                    # Extract Last Good IMSI
                    last_good_imsi = carrier_entitlements.get('lastGoodImsi', '')
                    if last_good_imsi:
                        self.cellular_data.append(('Last Good IMSI', last_good_imsi))
                        self.core_api.log_info(f"Last Good IMSI: {last_good_imsi}")

                    # Extract Self Registration Update IMSI
                    self_reg_imsi = carrier_entitlements.get('kEntitlementsSelfRegistrationUpdateImsi', '')
                    if self_reg_imsi:
                        self.cellular_data.append(('Self Registration Update IMSI', self_reg_imsi))
                        self.core_api.log_info(f"Self Registration Update IMSI: {self_reg_imsi}")

                    # Extract Self Registration Update IMEI
                    self_reg_imei = carrier_entitlements.get('kEntitlementsSelfRegistrationUpdateImei', '')
                    if self_reg_imei:
                        self.cellular_data.append(('Self Registration Update IMEI', self_reg_imei))
                        self.core_api.log_info(f"Self Registration Update IMEI: {self_reg_imei}")

        except (KeyError, TypeError, IndexError) as e:
            error_msg = f"Error parsing PersonalWallet: {str(e)}"
            self.errors.append(error_msg)
            self.core_api.log_warning(error_msg)

    def _generate_report(self) -> Path:
        """
        Generate markdown report of cellular information.

        Returns:
            Path to generated report
        """
        # Build report sections
        sections = []

        # Executive Summary
        summary_content = (
            f"Extracted {len(self.cellular_data)} cellular properties from iOS device extraction.\n\n"
            f"**Extraction Type**: {self.extraction_type}"
        )
        sections.append({
            "heading": "Executive Summary",
            "content": summary_content,
            "level": 2,
        })

        # Key Identifiers Section
        key_identifiers = [
            'Last Good IMSI',
            'Self Registration Update IMSI',
            'Self Registration Update IMEI',
            'Last Known ICCI',
            'Phone Number'
        ]

        key_data = {}
        for prop_name, prop_value in self.cellular_data:
            if prop_name in key_identifiers:
                key_data[prop_name] = prop_value if prop_value else "Not Available"

        if key_data:
            sections.append({
                "heading": "Key Device Identifiers",
                "content": key_data,
                "style": "table",
                "level": 2,
            })

        # All Cellular Properties
        all_properties = []
        for prop_name, prop_value in self.cellular_data:
            all_properties.append({
                "Property": prop_name,
                "Value": prop_value if prop_value else "N/A"
            })

        sections.append({
            "heading": "All Cellular Properties",
            "content": all_properties,
            "style": "table",
            "level": 2,
        })

        # Errors Section (if any)
        if self.errors:
            sections.append({
                "heading": "Errors Encountered",
                "content": self.errors,
                "style": "list",
                "level": 2,
            })

        # Additional metadata
        metadata = {
            "Extraction Type": self.extraction_type,
            "Properties Found": len(self.cellular_data),
            "Errors": len(self.errors),
        }

        # Generate report using Core API
        report_path = self.core_api.generate_report(
            plugin_name=self.metadata.name,
            title="iOS Cellular Information Extraction Report",
            sections=sections,
            metadata=metadata,
        )

        return report_path

    def _export_to_json(self) -> Path:
        """
        Export cellular data to JSON format.

        Returns:
            Path to JSON file
        """
        output_dir = self.core_api.get_case_output_dir("ios_cellular_info")
        output_dir.mkdir(parents=True, exist_ok=True)

        json_path = output_dir / "cellular_info.json"

        # Build data structure
        data = {
            "cellular_properties": [
                {"property": prop_name, "value": prop_value}
                for prop_name, prop_value in self.cellular_data
            ],
            "statistics": {
                "total_properties": len(self.cellular_data),
                "has_imsi": any("IMSI" in p[0] for p in self.cellular_data),
                "has_imei": any("IMEI" in p[0] for p in self.cellular_data),
                "has_icci": any("ICCI" in p[0] for p in self.cellular_data),
                "has_phone_number": any("Phone Number" in p[0] for p in self.cellular_data),
            }
        }

        # Use Core API to export
        self.core_api.export_plugin_data_to_json(
            output_path=json_path,
            plugin_name=self.metadata.name,
            plugin_version=self.metadata.version,
            data=data,
            extraction_type=self.extraction_type,
            errors=[{"error": err} for err in self.errors] if self.errors else None,
        )

        return json_path
