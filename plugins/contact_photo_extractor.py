"""
Contact Photo Extractor Plugin

Extracts contact photos/avatars from Android and iOS contact databases.
Demonstrates the Core API's BLOB extraction capabilities with automatic
type detection and file saving.

Supports:
- Android: contacts2.db (com.android.providers.contacts)
- iOS: AddressBook.sqlitedb
- Both Cellebrite and GrayKey extraction formats

Author: YaFT Development Team
Version: 1.0.0
"""

from pathlib import Path
from typing import Any

from yaft.core.plugin_base import PluginBase, PluginMetadata


class ContactPhotoExtractorPlugin(PluginBase):
    """Extract contact photos/avatars from Android and iOS databases."""

    def __init__(self, core_api):
        """Initialize plugin with Core API."""
        super().__init__(core_api)
        self.initialize()

    @property
    def metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name="ContactPhotoExtractorPlugin",
            version="1.0.0",
            description="Extract contact photos/avatars from mobile device databases",
            author="YaFT Development Team",
            target_os=["android", "ios"],
        )

    def initialize(self) -> None:
        """Initialize plugin resources."""
        self.extraction_type: str = "unknown"
        self.zip_prefix: str = ""
        self.extracted_photos: list[dict[str, Any]] = []
        self.errors: list[str] = []

    def execute(self, *args, **kwargs) -> dict[str, Any]:
        """
        Execute contact photo extraction.

        Returns:
            dict: Execution results with photo paths and statistics
        """
        self.core_api.print_info("Starting contact photo extraction...")

        # Check ZIP file is loaded
        if not self.core_api.get_current_zip():
            self.core_api.print_error("No ZIP file loaded")
            return {"success": False, "error": "No ZIP file loaded"}

        # Detect ZIP format
        self.extraction_type, self.zip_prefix = self.core_api.detect_zip_format()
        self.core_api.print_info(
            f"Detected extraction format: {self.extraction_type}"
        )

        # Extract photos based on OS
        if "android" in self.extraction_type:
            self._extract_android_photos()
        elif "ios" in self.extraction_type:
            self._extract_ios_photos()
        else:
            # Try both
            self.core_api.print_warning("Unknown format, trying both Android and iOS")
            self._extract_android_photos()
            self._extract_ios_photos()

        # Generate report
        report_path = self._generate_report()

        # Export to JSON
        output_dir = self.core_api.get_case_output_dir("contact_photos")
        json_path = output_dir / "contact_photos.json"
        self._export_to_json(json_path)

        return {
            "success": True,
            "total_photos": len(self.extracted_photos),
            "report_path": str(report_path),
            "json_path": str(json_path),
            "errors": self.errors,
        }

    def _extract_android_photos(self) -> None:
        """Extract contact photos from Android contacts2.db."""
        self.core_api.print_info("Searching for Android contact databases...")

        # Find contacts database
        db_paths = [
            "data/data/com.android.providers.contacts/databases/contacts2.db",
            "data/com.android.providers.contacts/databases/contacts2.db",
        ]

        db_path = None
        for path in db_paths:
            normalized = self.core_api.normalize_zip_path(path, self.zip_prefix)
            try:
                # Check if file exists in ZIP
                files = self.core_api.find_files_in_zip(normalized)
                if files:
                    db_path = normalized
                    break
            except Exception:
                continue

        if not db_path:
            self.core_api.print_warning("Android contacts database not found")
            return

        self.core_api.print_info(f"Found Android contacts database: {db_path}")

        try:
            # Extract contact photos
            query = """
                SELECT
                    contacts._id,
                    contacts.display_name,
                    data.data15 as photo
                FROM contacts
                JOIN data ON contacts._id = data.raw_contact_id
                WHERE data.mimetype = 'vnd.android.cursor.item/photo'
                AND data.data15 IS NOT NULL
            """

            # Try main query, fallback to simpler schema
            fallback_query = """
                SELECT
                    _id,
                    display_name,
                    photo_id
                FROM contacts
                WHERE photo_id IS NOT NULL
            """

            rows = self.core_api.query_sqlite_from_zip_dict(
                db_path, query, fallback_query=fallback_query
            )

            if not rows:
                self.core_api.print_warning("No contact photos found in Android database")
                return

            self.core_api.print_info(f"Found {len(rows)} contacts with photos")

            # Create output directory
            output_dir = self.core_api.get_case_output_dir("contact_photos/android")
            output_dir.mkdir(parents=True, exist_ok=True)

            # Extract each photo
            for row in rows:
                contact_id = row.get("_id")
                display_name = row.get("display_name", f"contact_{contact_id}")
                photo_data = row.get("photo")

                if not photo_data:
                    continue

                try:
                    # Detect BLOB type
                    blob_type = self.core_api.detect_blob_type(photo_data)

                    # Save photo with auto extension
                    safe_name = "".join(
                        c for c in display_name if c.isalnum() or c in (" ", "_", "-")
                    ).strip()
                    safe_name = safe_name[:50] if safe_name else f"contact_{contact_id}"

                    photo_path = self.core_api.save_blob_as_file(
                        photo_data,
                        output_dir / f"{safe_name}_{contact_id}.dat",
                        auto_extension=True,
                    )

                    self.extracted_photos.append(
                        {
                            "source": "android",
                            "contact_id": contact_id,
                            "contact_name": display_name,
                            "photo_type": blob_type,
                            "file_path": str(photo_path),
                            "file_size": len(photo_data),
                        }
                    )

                    self.core_api.print_success(
                        f"Extracted {blob_type} photo for: {display_name}"
                    )

                except Exception as e:
                    error_msg = f"Failed to extract photo for {display_name}: {e}"
                    self.errors.append(error_msg)
                    self.core_api.print_error(error_msg)

        except Exception as e:
            error_msg = f"Failed to extract Android photos: {e}"
            self.errors.append(error_msg)
            self.core_api.print_error(error_msg)

    def _extract_ios_photos(self) -> None:
        """Extract contact photos from iOS AddressBook database."""
        self.core_api.print_info("Searching for iOS AddressBook database...")

        # Find AddressBook database
        db_paths = [
            "private/var/mobile/Library/AddressBook/AddressBook.sqlitedb",
            "Library/AddressBook/AddressBook.sqlitedb",
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
            self.core_api.print_warning("iOS AddressBook database not found")
            return

        self.core_api.print_info(f"Found iOS AddressBook database: {db_path}")

        try:
            # Extract contact photos from iOS
            query = """
                SELECT
                    ABPerson.ROWID as contact_id,
                    ABPerson.First as first_name,
                    ABPerson.Last as last_name,
                    ABPerson.data as photo
                FROM ABPerson
                WHERE ABPerson.data IS NOT NULL
            """

            fallback_query = """
                SELECT
                    ROWID as contact_id,
                    First as first_name,
                    Last as last_name,
                    data as photo
                FROM ABPerson
                WHERE data IS NOT NULL
            """

            rows = self.core_api.query_sqlite_from_zip_dict(
                db_path, query, fallback_query=fallback_query
            )

            if not rows:
                self.core_api.print_warning("No contact photos found in iOS database")
                return

            self.core_api.print_info(f"Found {len(rows)} contacts with photos")

            # Create output directory
            output_dir = self.core_api.get_case_output_dir("contact_photos/ios")
            output_dir.mkdir(parents=True, exist_ok=True)

            # Extract each photo
            for row in rows:
                contact_id = row.get("contact_id")
                first_name = row.get("first_name", "")
                last_name = row.get("last_name", "")
                display_name = f"{first_name} {last_name}".strip() or f"contact_{contact_id}"
                photo_data = row.get("photo")

                if not photo_data:
                    continue

                try:
                    # Detect BLOB type
                    blob_type = self.core_api.detect_blob_type(photo_data)

                    # Save photo with auto extension
                    safe_name = "".join(
                        c for c in display_name if c.isalnum() or c in (" ", "_", "-")
                    ).strip()
                    safe_name = safe_name[:50] if safe_name else f"contact_{contact_id}"

                    photo_path = self.core_api.save_blob_as_file(
                        photo_data,
                        output_dir / f"{safe_name}_{contact_id}.dat",
                        auto_extension=True,
                    )

                    self.extracted_photos.append(
                        {
                            "source": "ios",
                            "contact_id": contact_id,
                            "contact_name": display_name,
                            "photo_type": blob_type,
                            "file_path": str(photo_path),
                            "file_size": len(photo_data),
                        }
                    )

                    self.core_api.print_success(
                        f"Extracted {blob_type} photo for: {display_name}"
                    )

                except Exception as e:
                    error_msg = f"Failed to extract photo for {display_name}: {e}"
                    self.errors.append(error_msg)
                    self.core_api.print_error(error_msg)

        except Exception as e:
            error_msg = f"Failed to extract iOS photos: {e}"
            self.errors.append(error_msg)
            self.core_api.print_error(error_msg)

    def _generate_report(self) -> Path:
        """Generate markdown report."""
        # Statistics
        total_photos = len(self.extracted_photos)
        android_photos = len([p for p in self.extracted_photos if p["source"] == "android"])
        ios_photos = len([p for p in self.extracted_photos if p["source"] == "ios"])

        # Photo types
        photo_types: dict[str, int] = {}
        for photo in self.extracted_photos:
            photo_type = photo["photo_type"]
            photo_types[photo_type] = photo_types.get(photo_type, 0) + 1

        # Sections
        sections = [
            {
                "heading": "Executive Summary",
                "content": f"Extracted {total_photos} contact photos from the forensic extraction.",
                "level": 2,
            },
            {
                "heading": "Statistics",
                "content": {
                    "Total Photos": total_photos,
                    "Android Photos": android_photos,
                    "iOS Photos": ios_photos,
                    "Errors": len(self.errors),
                },
                "style": "table",
            },
            {
                "heading": "Photo Types",
                "content": photo_types if photo_types else {"None": 0},
                "style": "table",
            },
        ]

        # Add photo list
        if self.extracted_photos:
            photo_list = []
            for photo in self.extracted_photos[:100]:  # Limit to first 100
                photo_list.append(
                    f"**{photo['contact_name']}** ({photo['source'].upper()})\n"
                    f"  - Type: {photo['photo_type']}\n"
                    f"  - Size: {photo['file_size']:,} bytes\n"
                    f"  - Path: `{Path(photo['file_path']).name}`"
                )

            sections.append(
                {
                    "heading": "Extracted Photos",
                    "content": photo_list,
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
            "Total Photos": total_photos,
        }

        report_path = self.core_api.generate_report(
            plugin_name=self.metadata.name,
            title="Contact Photo Extraction Report",
            sections=sections,
            metadata=metadata,
        )

        return report_path

    def _export_to_json(self, output_path: Path) -> None:
        """Export extracted photo metadata to JSON."""
        output_path.parent.mkdir(parents=True, exist_ok=True)

        data = {
            "extraction_type": self.extraction_type,
            "total_photos": len(self.extracted_photos),
            "photos": self.extracted_photos,
            "errors": self.errors,
        }

        self.core_api.export_plugin_data_to_json(
            output_path,
            self.metadata.name,
            self.metadata.version,
            data,
        )
        self.core_api.print_success(f"Exported metadata to: {output_path}")

    def cleanup(self) -> None:
        """Clean up plugin resources."""
        self.extracted_photos.clear()
        self.errors.clear()
