"""
iOS Keychain Analyzer Plugin

Analyzes iOS Keychain metadata to provide forensic intelligence about
stored credentials, certificates, and cryptographic keys. This plugin
demonstrates the Core API's keychain parsing capabilities.

Important: This plugin extracts METADATA ONLY. Modern iOS devices (iPhone 5s+)
use Secure Enclave encryption, making offline decryption of actual credentials
practically impossible without the physical device.

Forensic Value:
- Inventory of stored credentials
- Timeline analysis (when credentials were created/modified)
- Application associations (which apps use which credentials)
- iCloud Keychain synchronization status
- Certificate and key management analysis

Supports:
- iOS keychain-2.db from both Cellebrite and GrayKey extractions
- Generic passwords (app credentials)
- Internet passwords (web credentials)
- Certificates
- Cryptographic keys

Author: YaFT Development Team
Version: 1.0.0
"""

from datetime import datetime
from pathlib import Path
from typing import Any

from yaft.core.plugin_base import PluginBase, PluginMetadata


class iOSKeychainAnalyzerPlugin(PluginBase):
    """Analyze iOS Keychain metadata for forensic intelligence."""

    def __init__(self, core_api):
        """Initialize plugin with Core API."""
        super().__init__(core_api)
        self.initialize()

    @property
    def metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name="iOSKeychainAnalyzerPlugin",
            version="1.0.0",
            description="Analyze iOS Keychain metadata for credential inventory and forensic intelligence",
            author="YaFT Development Team",
            target_os=["ios"],
        )

    def initialize(self) -> None:
        """Initialize plugin resources."""
        self.extraction_type: str = "unknown"
        self.zip_prefix: str = ""
        self.keychain_data: dict[str, Any] | None = None
        self.analysis_results: dict[str, Any] = {}
        self.errors: list[str] = []

    def execute(self, *args, **kwargs) -> dict[str, Any]:
        """
        Execute iOS Keychain analysis.

        Returns:
            dict: Execution results with analysis and statistics
        """
        self.core_api.print_info("Starting iOS Keychain analysis...")

        # Check ZIP file is loaded
        if not self.core_api.get_current_zip():
            self.core_api.print_error("No ZIP file loaded")
            return {"success": False, "error": "No ZIP file loaded"}

        # Detect ZIP format
        self.extraction_type, self.zip_prefix = self.core_api.detect_zip_format()
        self.core_api.print_info(
            f"Detected extraction format: {self.extraction_type}"
        )

        # Verify iOS extraction
        if "android" in self.extraction_type:
            self.core_api.print_error("Android extraction detected - iOS Keychain not available")
            return {"success": False, "error": "Not an iOS extraction"}

        # Parse keychain database
        if not self._parse_keychain():
            return {"success": False, "error": "Failed to parse keychain database"}

        # Perform analysis
        self._analyze_credentials()
        self._analyze_applications()
        self._analyze_synchronization()
        self._analyze_timeline()
        self._analyze_internet_passwords()

        # Generate report
        report_path = self._generate_report()

        # Export to JSON
        output_dir = self.core_api.get_case_output_dir("ios_keychain")
        json_path = output_dir / "keychain_analysis.json"
        self._export_to_json(json_path)

        return {
            "success": True,
            "total_credentials": self.keychain_data["summary"]["generic_passwords_count"],
            "total_internet_passwords": self.keychain_data["summary"]["internet_passwords_count"],
            "total_certificates": self.keychain_data["summary"]["certificates_count"],
            "total_keys": self.keychain_data["summary"]["keys_count"],
            "report_path": str(report_path),
            "json_path": str(json_path),
            "errors": self.errors,
        }

    def _parse_keychain(self) -> bool:
        """Parse iOS keychain database."""
        self.core_api.print_info("Searching for iOS Keychain database...")

        # Find keychain database
        db_paths = [
            "private/var/Keychains/keychain-2.db",
            "var/Keychains/keychain-2.db",
        ]

        db_path = None
        for path in db_paths:
            normalized = self.core_api.normalize_zip_path(path, self.zip_prefix)
            try:
                files = self.core_api.find_files_in_zip(normalized)
                if files:
                    db_path = normalized
                    break
            except Exception:
                continue

        if not db_path:
            error_msg = "iOS Keychain database (keychain-2.db) not found"
            self.errors.append(error_msg)
            self.core_api.print_error(error_msg)
            return False

        self.core_api.print_info(f"Found iOS Keychain database: {db_path}")

        try:
            # Parse keychain using Core API
            self.keychain_data = self.core_api.parse_ios_keychain(db_path)

            # Display summary
            summary = self.keychain_data["summary"]
            self.core_api.print_success(
                f"Parsed keychain: {summary['generic_passwords_count']} passwords, "
                f"{summary['internet_passwords_count']} internet passwords, "
                f"{summary['certificates_count']} certificates, "
                f"{summary['keys_count']} keys"
            )

            # Display security note
            self.core_api.print_warning(
                "Note: Actual credentials are encrypted by Secure Enclave. "
                "This analysis provides metadata only."
            )

            return True

        except Exception as e:
            error_msg = f"Failed to parse keychain: {e}"
            self.errors.append(error_msg)
            self.core_api.print_error(error_msg)
            return False

    def _analyze_credentials(self) -> None:
        """Analyze credential statistics."""
        self.core_api.print_info("Analyzing credentials...")

        summary = self.keychain_data["summary"]

        # Count synchronizable items
        sync_count = sum(
            1 for item in (
                self.keychain_data["generic_passwords"] +
                self.keychain_data["internet_passwords"]
            )
            if item.get("sync_enabled") or item.get("synchronizable") == 1
        )

        self.analysis_results["credential_stats"] = {
            "total_items": summary["total_entries"],
            "generic_passwords": summary["generic_passwords_count"],
            "internet_passwords": summary["internet_passwords_count"],
            "certificates": summary["certificates_count"],
            "cryptographic_keys": summary["keys_count"],
            "synchronizable_items": sync_count,
            "encrypted_entries": summary.get("encrypted_entries", 0),
        }

    def _analyze_applications(self) -> None:
        """Analyze application associations."""
        self.core_api.print_info("Analyzing application associations...")

        # Collect all access groups
        access_groups: dict[str, int] = {}

        for item in self.keychain_data["generic_passwords"]:
            access_group = item.get("access_group")
            if access_group:
                access_groups[access_group] = access_groups.get(access_group, 0) + 1

        for item in self.keychain_data["internet_passwords"]:
            access_group = item.get("access_group")
            if access_group:
                access_groups[access_group] = access_groups.get(access_group, 0) + 1

        # Sort by count
        sorted_groups = sorted(
            access_groups.items(), key=lambda x: x[1], reverse=True
        )

        self.analysis_results["application_analysis"] = {
            "total_apps_with_credentials": len(access_groups),
            "top_apps": dict(sorted_groups[:20]),  # Top 20 apps
            "all_apps": dict(sorted_groups),
        }

        self.core_api.print_success(
            f"Found {len(access_groups)} applications with stored credentials"
        )

    def _analyze_synchronization(self) -> None:
        """Analyze iCloud Keychain synchronization."""
        self.core_api.print_info("Analyzing iCloud Keychain synchronization...")

        sync_items = []
        non_sync_items = []

        for item in self.keychain_data["generic_passwords"]:
            # Check both sync_enabled (boolean) and synchronizable (integer) for compatibility
            if item.get("sync_enabled") or item.get("synchronizable") == 1:
                sync_items.append(item)
            else:
                non_sync_items.append(item)

        for item in self.keychain_data["internet_passwords"]:
            # Check both sync_enabled (boolean) and synchronizable (integer) for compatibility
            if item.get("sync_enabled") or item.get("synchronizable") == 1:
                sync_items.append(item)
            else:
                non_sync_items.append(item)

        self.analysis_results["synchronization_analysis"] = {
            "total_synced_items": len(sync_items),
            "total_local_items": len(non_sync_items),
            "sync_percentage": (
                round(len(sync_items) / (len(sync_items) + len(non_sync_items)) * 100, 2)
                if (len(sync_items) + len(non_sync_items)) > 0
                else 0
            ),
        }

        if len(sync_items) > 0:
            self.core_api.print_warning(
                f"Found {len(sync_items)} items synchronized to iCloud "
                "(may exist on other user devices)"
            )

    def _analyze_timeline(self) -> None:
        """Analyze credential timeline (creation/modification dates)."""
        self.core_api.print_info("Analyzing credential timeline...")

        all_items = (
            self.keychain_data["generic_passwords"]
            + self.keychain_data["internet_passwords"]
        )

        if not all_items:
            self.analysis_results["timeline_analysis"] = {
                "oldest_credential": None,
                "newest_credential": None,
                "date_range_days": 0,
            }
            return

        # Find oldest and newest
        oldest = None
        newest = None

        for item in all_items:
            creation_date = item.get("creation_date")
            if creation_date and creation_date != "N/A":
                if oldest is None or creation_date < oldest:
                    oldest = creation_date
                if newest is None or creation_date > newest:
                    newest = creation_date

        # Calculate date range
        date_range_days = 0
        if oldest and newest:
            try:
                oldest_dt = datetime.strptime(oldest, "%Y-%m-%d %H:%M:%S")
                newest_dt = datetime.strptime(newest, "%Y-%m-%d %H:%M:%S")
                date_range_days = (newest_dt - oldest_dt).days
            except Exception:
                pass

        self.analysis_results["timeline_analysis"] = {
            "oldest_credential": oldest,
            "newest_credential": newest,
            "date_range_days": date_range_days,
        }

    def _analyze_internet_passwords(self) -> None:
        """Analyze internet passwords for interesting domains."""
        self.core_api.print_info("Analyzing internet passwords...")

        domains: dict[str, int] = {}
        protocols: dict[str, int] = {}

        for item in self.keychain_data["internet_passwords"]:
            # Count domains
            server = item.get("server")
            if server:
                domains[server] = domains.get(server, 0) + 1

            # Count protocols
            protocol = item.get("protocol")
            if protocol is not None:
                protocol_name = self._get_protocol_name(protocol)
                protocols[protocol_name] = protocols.get(protocol_name, 0) + 1

        # Sort by count
        sorted_domains = sorted(domains.items(), key=lambda x: x[1], reverse=True)

        self.analysis_results["internet_password_analysis"] = {
            "total_domains": len(domains),
            "top_domains": dict(sorted_domains[:20]),  # Top 20 domains
            "protocol_distribution": protocols,
        }

        self.core_api.print_success(
            f"Found credentials for {len(domains)} different domains/servers"
        )

    def _get_protocol_name(self, protocol_code: int) -> str:
        """Convert protocol code to name."""
        protocol_map = {
            0: "FTP",
            1: "HTTP",
            2: "IMAP",
            3: "LDAP",
            4: "POP3",
            5: "SMTP",
            6: "SOCKS",
            7: "HTTPS",
        }
        return protocol_map.get(protocol_code, f"Unknown ({protocol_code})")

    def _generate_report(self) -> Path:
        """Generate markdown report."""
        sections = []

        # Executive Summary
        cred_stats = self.analysis_results["credential_stats"]
        sections.append(
            {
                "heading": "Executive Summary",
                "content": (
                    f"Analyzed iOS Keychain containing {cred_stats['total_items']} total items. "
                    f"Found credentials for {self.analysis_results['application_analysis']['total_apps_with_credentials']} applications "
                    f"and {self.analysis_results['internet_password_analysis']['total_domains']} domains/servers."
                ),
                "level": 2,
            }
        )

        # Security Notice
        sections.append(
            {
                "heading": "Security Notice",
                "content": self.keychain_data["security_note"],
                "level": 2,
            }
        )

        # Credential Statistics
        sections.append(
            {
                "heading": "Credential Statistics",
                "content": cred_stats,
                "style": "table",
            }
        )

        # Application Analysis
        app_analysis = self.analysis_results["application_analysis"]
        sections.append(
            {
                "heading": "Top Applications with Credentials",
                "content": app_analysis["top_apps"] if app_analysis["top_apps"] else {"None": 0},
                "style": "table",
            }
        )

        # Synchronization Analysis
        sync_analysis = self.analysis_results["synchronization_analysis"]
        sections.append(
            {
                "heading": "iCloud Keychain Synchronization",
                "content": sync_analysis,
                "style": "table",
            }
        )

        # Timeline Analysis
        timeline = self.analysis_results["timeline_analysis"]
        sections.append(
            {
                "heading": "Timeline Analysis",
                "content": timeline,
                "style": "table",
            }
        )

        # Internet Password Analysis
        inet_analysis = self.analysis_results["internet_password_analysis"]
        sections.append(
            {
                "heading": "Top Domains with Stored Credentials",
                "content": inet_analysis["top_domains"] if inet_analysis["top_domains"] else {"None": 0},
                "style": "table",
            }
        )

        sections.append(
            {
                "heading": "Protocol Distribution",
                "content": inet_analysis["protocol_distribution"] if inet_analysis["protocol_distribution"] else {"None": 0},
                "style": "table",
            }
        )

        # Sample Generic Passwords (first 10)
        if self.keychain_data["generic_passwords"]:
            sample_passwords = []
            for item in self.keychain_data["generic_passwords"][:10]:
                sample_passwords.append(
                    f"**Label:** {item.get('label', 'N/A')}\n"
                    f"  - Created: {item.get('creation_date', 'N/A')}\n"
                    f"  - Modified: {item.get('modification_date', 'N/A')}\n"
                    f"  - Access Group: {item.get('access_group', 'N/A')}\n"
                    f"  - Synchronizable: {'Yes' if item.get('synchronizable') == 1 else 'No'}"
                )

            sections.append(
                {
                    "heading": "Sample Generic Passwords (First 10)",
                    "content": sample_passwords,
                    "style": "list",
                }
            )

        # Sample Internet Passwords (first 10)
        if self.keychain_data["internet_passwords"]:
            sample_internet = []
            for item in self.keychain_data["internet_passwords"][:10]:
                sample_internet.append(
                    f"**Server:** {item.get('server', 'N/A')}\n"
                    f"  - Label: {item.get('label', 'N/A')}\n"
                    f"  - Created: {item.get('creation_date', 'N/A')}\n"
                    f"  - Protocol: {self._get_protocol_name(item.get('protocol', -1))}\n"
                    f"  - Port: {item.get('port', 'N/A')}\n"
                    f"  - Access Group: {item.get('access_group', 'N/A')}"
                )

            sections.append(
                {
                    "heading": "Sample Internet Passwords (First 10)",
                    "content": sample_internet,
                    "style": "list",
                }
            )

        # Forensic Recommendations
        recommendations = [
            "Correlate keychain access groups with installed applications",
            "Investigate high-value targets (banking, email, social media)",
            "Analyze timeline for credential creation/modification patterns",
            "Check iCloud-synced items for presence on other user devices",
            "Cross-reference domains with browser history and network artifacts",
            "Consider on-device exploitation for high-value encrypted credentials",
        ]

        sections.append(
            {
                "heading": "Forensic Recommendations",
                "content": recommendations,
                "style": "list",
            }
        )

        # Add errors if any
        if self.errors:
            sections.append(
                {
                    "heading": "Errors",
                    "content": self.errors,
                    "style": "list",
                }
            )

        # Generate report
        metadata = {
            "Extraction Type": self.extraction_type,
            "Total Keychain Items": cred_stats["total_items"],
            "Applications": app_analysis["total_apps_with_credentials"],
        }

        report_path = self.core_api.generate_report(
            plugin_name=self.metadata.name,
            title="iOS Keychain Analysis Report",
            sections=sections,
            metadata=metadata,
        )

        return report_path

    def _export_to_json(self, output_path: Path) -> None:
        """Export analysis results to JSON."""
        output_path.parent.mkdir(parents=True, exist_ok=True)

        data = {
            "extraction_type": self.extraction_type,
            "keychain_summary": self.keychain_data["summary"],
            "analysis_results": self.analysis_results,
            "security_note": self.keychain_data["security_note"],
            "errors": self.errors,
        }

        self.core_api.export_plugin_data_to_json(
            output_path,
            self.metadata.name,
            self.metadata.version,
            data,
        )
        self.core_api.print_success(f"Exported analysis to: {output_path}")

    def cleanup(self) -> None:
        """Clean up plugin resources."""
        self.keychain_data = None
        self.analysis_results.clear()
        self.errors.clear()
