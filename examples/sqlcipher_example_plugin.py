"""
Example plugin demonstrating SQLCipher encrypted database analysis.

This plugin shows how to query and decrypt SQLCipher-encrypted databases
commonly found in mobile forensics (WhatsApp, Signal, iOS apps, etc.).
"""

from pathlib import Path
from typing import Any

from yaft.core.api import CoreAPI
from yaft.core.plugin_base import PluginBase, PluginMetadata


class SQLCipherExamplePlugin(PluginBase):
    """Example plugin for analyzing SQLCipher encrypted databases."""

    @property
    def metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name="SQLCipherExamplePlugin",
            version="1.0.0",
            description="Example plugin demonstrating SQLCipher encrypted database analysis",
            author="YaFT Team",
            target_os=["android", "ios"],
        )

    def initialize(self) -> None:
        """Initialize the plugin."""
        self.core_api.print_info("SQLCipher Example Plugin initialized")

    def execute(self, *args, **kwargs) -> dict[str, Any]:
        """
        Demonstrate SQLCipher functionality.

        This example shows:
        1. Querying encrypted databases
        2. Handling different SQLCipher versions
        3. Decrypting databases to plain SQLite
        4. Error handling for wrong keys
        """
        # Check if ZIP file is loaded
        if not self.core_api.get_current_zip():
            self.core_api.print_error("No ZIP file loaded")
            return {"success": False, "error": "No ZIP file loaded"}

        # Example 1: Query encrypted WhatsApp-style database
        self.core_api.print_info("\n=== Example 1: Query Encrypted Database ===")

        try:
            # In real forensics, you'd obtain this key through various methods:
            # - Extracted from device memory
            # - Derived from device identifiers (IMEI, phone number)
            # - Obtained from app's secure storage
            encryption_key = kwargs.get("key", "example_key")

            # Find encrypted databases in the ZIP
            encrypted_dbs = self.core_api.find_files_in_zip("*.db")

            if not encrypted_dbs:
                self.core_api.print_warning("No database files found in ZIP")
                return {"success": False, "error": "No databases found"}

            self.core_api.print_info(f"Found {len(encrypted_dbs)} database files")

            # Try to query the first encrypted database
            db_path = encrypted_dbs[0]
            self.core_api.print_info(f"Attempting to query: {db_path}")

            # Query encrypted database
            try:
                # Get table list
                tables = self.core_api.query_sqlcipher_from_zip_dict(
                    db_path,
                    encryption_key,
                    "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
                )

                self.core_api.print_success(f"Successfully decrypted database")
                self.core_api.print_info(f"Found {len(tables)} tables:")
                for table in tables:
                    self.core_api.print_info(f"  - {table['name']}")

            except ValueError as e:
                self.core_api.print_warning(f"Decryption failed (possibly wrong key): {e}")
                self.core_api.print_info("Trying with SQLCipher v3 compatibility...")

                # Retry with SQLCipher v3 compatibility
                try:
                    tables = self.core_api.query_sqlcipher_from_zip_dict(
                        db_path,
                        encryption_key,
                        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name",
                        cipher_version=3
                    )
                    self.core_api.print_success("Successfully decrypted with SQLCipher v3 compatibility")
                except ValueError:
                    self.core_api.print_error("Could not decrypt database (wrong key or corrupted)")
                    return {"success": False, "error": "Decryption failed"}

        except ImportError:
            self.core_api.print_error(
                "SQLCipher support not installed. Run: uv pip install sqlcipher3"
            )
            return {"success": False, "error": "sqlcipher3 not installed"}

        # Example 2: Decrypt database to plain SQLite
        self.core_api.print_info("\n=== Example 2: Decrypt to Plain SQLite ===")

        try:
            # Create output directory
            output_dir = self.core_api.get_case_output_dir("decrypted_databases")
            output_dir.mkdir(parents=True, exist_ok=True)

            # Decrypt the database
            output_path = output_dir / f"decrypted_{Path(db_path).name}"

            decrypted_path = self.core_api.decrypt_sqlcipher_database(
                db_path,
                encryption_key,
                output_path
            )

            self.core_api.print_success(f"Decrypted database saved to: {decrypted_path}")

        except Exception as e:
            self.core_api.print_error(f"Failed to decrypt database: {e}")

        # Example 3: Query specific data (simulating forensic analysis)
        self.core_api.print_info("\n=== Example 3: Forensic Data Extraction ===")

        try:
            # This is a generic example - in real forensics, you'd know the schema
            # For WhatsApp: SELECT key_remote_jid, data, timestamp FROM messages
            # For Signal: SELECT address, body, date_sent FROM sms
            # For iOS apps: Query app-specific tables

            # Try to get row count from first table
            if tables:
                first_table = tables[0]['name']

                count_result = self.core_api.query_sqlcipher_from_zip(
                    db_path,
                    encryption_key,
                    f"SELECT COUNT(*) FROM {first_table}"
                )

                row_count = count_result[0][0] if count_result else 0
                self.core_api.print_info(f"Table '{first_table}' contains {row_count} rows")

        except Exception as e:
            self.core_api.print_warning(f"Could not query table data: {e}")

        # Generate report
        self.core_api.print_info("\n=== Generating Report ===")

        sections = [
            {
                "heading": "SQLCipher Analysis Summary",
                "content": "This report demonstrates SQLCipher encrypted database analysis",
            },
            {
                "heading": "Databases Found",
                "content": [f"{db}" for db in encrypted_dbs[:10]],  # First 10
                "style": "list",
            },
            {
                "heading": "Tables Discovered",
                "content": [table['name'] for table in tables] if tables else ["No tables found"],
                "style": "list",
            },
            {
                "heading": "Notes",
                "content": (
                    "In real forensic analysis, you would:\n"
                    "1. Obtain encryption keys through proper forensic techniques\n"
                    "2. Extract specific data based on known database schemas\n"
                    "3. Analyze message content, timestamps, and metadata\n"
                    "4. Generate comprehensive reports with extracted data"
                ),
            },
        ]

        report_path = self.core_api.generate_report(
            plugin_name=self.metadata.name,
            title="SQLCipher Encrypted Database Analysis",
            sections=sections,
        )

        self.core_api.print_success(f"Report generated: {report_path}")

        return {
            "success": True,
            "databases_found": len(encrypted_dbs),
            "tables_found": len(tables) if tables else 0,
            "report_path": str(report_path),
            "decrypted_path": str(decrypted_path) if 'decrypted_path' in locals() else None,
        }

    def cleanup(self) -> None:
        """Clean up plugin resources."""
        self.core_api.print_info("SQLCipher Example Plugin cleanup complete")
