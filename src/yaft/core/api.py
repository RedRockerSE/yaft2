"""
Core API that provides shared functionality to plugins.

This module exposes common services and utilities that plugins can use.
"""

import logging
import plistlib
import sqlite3
import tempfile
import toml
import zipfile
from enum import Enum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, field_validator
from rich.console import Console
from rich.logging import RichHandler
from rich.table import Table


class ExtractionOS(str, Enum):
    """Operating system type detected in extraction."""

    UNKNOWN = "unknown"
    IOS = "ios"
    ANDROID = "android"


class PluginProfile(BaseModel):
    """Plugin profile configuration model."""

    name: str = Field(..., description="Profile name")
    description: str | None = Field(None, description="Profile description")
    plugins: list[str] = Field(..., min_length=1, description="List of plugin class names to run")

    @field_validator("plugins")
    @classmethod
    def validate_plugins(cls, v: list[str]) -> list[str]:
        """Validate that plugins list is not empty and contains valid names."""
        if not v:
            raise ValueError("plugins list cannot be empty")
        for plugin_name in v:
            if not plugin_name or not plugin_name.strip():
                raise ValueError("plugin names cannot be empty")
        return v


class CoreAPI:
    """
    Core API providing shared functionality to plugins.

    This class acts as a service layer, offering plugins access to:
    - Logging facilities
    - Configuration management
    - Output formatting
    - File system utilities
    - ZIP file handling (forensic analysis)
    - Inter-plugin communication
    """

    def __init__(self, config_dir: Path | None = None) -> None:
        """
        Initialize the Core API.

        Args:
            config_dir: Optional configuration directory path
        """
        self.config_dir = config_dir or Path.cwd() / "config"
        self.config_dir.mkdir(parents=True, exist_ok=True)

        # Initialize Rich console for beautiful output
        self.console = Console()

        # Setup logging with Rich handler
        self._setup_logging()

        # Storage for shared data between plugins
        self._shared_data: dict[str, Any] = {}

        # Current ZIP file being analyzed
        self._current_zip: Path | None = None
        self._zip_handle: zipfile.ZipFile | None = None
        self._detected_os: ExtractionOS = ExtractionOS.UNKNOWN

        # Case identifiers for forensic analysis
        self._examiner_id: str | None = None
        self._case_id: str | None = None
        self._evidence_id: str | None = None

        # PDF export configuration
        self._enable_pdf_export: bool = False
        self._generated_reports: list[Path] = []  # Track reports for batch PDF export

    def _setup_logging(self) -> None:
        """Configure logging with Rich handler."""
        logging.basicConfig(
            level=logging.INFO,
            format="%(message)s",
            datefmt="[%X]",
            handlers=[RichHandler(console=self.console, rich_tracebacks=True)],
        )
        self.logger = logging.getLogger("yaft")

    def log_info(self, message: str) -> None:
        """Log an info message."""
        self.logger.info(message)

    def log_warning(self, message: str) -> None:
        """Log a warning message."""
        self.logger.warning(message)

    def log_error(self, message: str) -> None:
        """Log an error message."""
        self.logger.error(message)

    def log_debug(self, message: str) -> None:
        """Log a debug message."""
        self.logger.debug(message)

    def print_success(self, message: str) -> None:
        """Print a success message in green."""
        self.console.print(f"[bold green][OK][/bold green] {message}")

    def print_error(self, message: str) -> None:
        """Print an error message in red."""
        self.console.print(f"[bold red][ERROR][/bold red] {message}")

    def print_warning(self, message: str) -> None:
        """Print a warning message in yellow."""
        self.console.print(f"[bold yellow][WARNING][/bold yellow] {message}")

    def print_info(self, message: str) -> None:
        """Print an info message in blue."""
        self.console.print(f"[bold blue][INFO][/bold blue] {message}")

    def get_config_path(self, filename: str) -> Path:
        """
        Get path to a configuration file.

        Args:
            filename: Name of the configuration file

        Returns:
            Path: Full path to the configuration file
        """
        return self.config_dir / filename

    def set_shared_data(self, key: str, value: Any) -> None:
        """
        Store data that can be accessed by other plugins.

        Args:
            key: Data identifier
            value: Data to store
        """
        self._shared_data[key] = value

    def get_shared_data(self, key: str, default: Any = None) -> Any:
        """
        Retrieve shared data stored by plugins.

        Args:
            key: Data identifier
            default: Default value if key not found

        Returns:
            Any: Retrieved data or default value
        """
        return self._shared_data.get(key, default)

    def clear_shared_data(self, key: str | None = None) -> None:
        """
        Clear shared data.

        Args:
            key: Optional specific key to clear. If None, clears all data.
        """
        if key is None:
            self._shared_data.clear()
        else:
            self._shared_data.pop(key, None)

    def get_user_input(self, prompt: str) -> str:
        """
        Get user input with a formatted prompt.

        Args:
            prompt: Prompt message to display

        Returns:
            str: User input
        """
        return self.console.input(f"[bold cyan]?[/bold cyan] {prompt}: ")

    def confirm(self, message: str) -> bool:
        """
        Ask user for yes/no confirmation.

        Args:
            message: Confirmation message

        Returns:
            bool: True if user confirmed, False otherwise
        """
        response = self.console.input(f"[bold cyan]?[/bold cyan] {message} [y/N]: ")
        return response.lower() in ("y", "yes")

    # ========== Case Identifier Methods ==========

    def validate_examiner_id(self, value: str) -> bool:
        """
        Validate Examiner ID format: alphanumeric with underscores and hyphens, 2-50 characters.

        Args:
            value: Examiner ID to validate

        Returns:
            bool: True if valid, False otherwise
        """
        import re
        return bool(re.match(r'^[A-Za-z0-9_-]{2,50}$', value))

    def validate_case_id(self, value: str) -> bool:
        """
        Validate Case ID format: any alphanumeric string.
        Examples: CASE2024-01, K2024001-01, 2024-001, Case123, MyCase

        Args:
            value: Case ID to validate

        Returns:
            bool: True if valid (any non-empty alphanumeric string), False otherwise
        """
        import re
        return bool(re.match(r'^[A-Za-z0-9_-]+$', value))

    def validate_evidence_id(self, value: str) -> bool:
        """
        Validate Evidence ID format: any alphanumeric string.
        Examples: EV123456-1, EV123456-1, ITEM1234-01, Evidence1, Ev-001

        Args:
            value: Evidence ID to validate

        Returns:
            bool: True if valid (any non-empty alphanumeric string), False otherwise
        """
        import re
        return bool(re.match(r'^[A-Za-z0-9_-]+$', value))

    def prompt_for_case_identifiers(self) -> tuple[str, str, str]:
        """
        Prompt user for case identifiers with validation.

        Returns:
            tuple[str, str, str]: (examiner_id, case_id, evidence_id)

        Raises:
            ValueError: If user cancels input (Ctrl+C)
        """
        self.console.print("\n[bold cyan]Case Information Required[/bold cyan]")
        self.console.print("Please enter the following case identifiers:\n")

        # Prompt for Examiner ID
        while True:
            examiner_id = self.console.input("[bold cyan]?[/bold cyan] Examiner ID (alphanumeric, 2-50 chars): ").strip()
            if self.validate_examiner_id(examiner_id):
                break
            self.console.print("[bold red]✗[/bold red] Invalid format. Use alphanumeric characters, underscores, or hyphens (e.g., john_doe, examiner-123)")

        # Prompt for Case ID
        while True:
            case_id = self.console.input("[bold cyan]?[/bold cyan] Case ID (alphanumeric): ").strip()
            if self.validate_case_id(case_id):
                break
            self.console.print("[bold red]✗[/bold red] Invalid format. Use alphanumeric characters, underscores, or hyphens (e.g., CASE2024-01, Case123, MyCase)")

        # Prompt for Evidence ID
        while True:
            evidence_id = self.console.input("[bold cyan]?[/bold cyan] Evidence ID (alphanumeric): ").strip()
            if self.validate_evidence_id(evidence_id):
                break
            self.console.print("[bold red]✗[/bold red] Invalid format. Use alphanumeric characters, underscores, or hyphens (e.g., EV123456-1, Evidence1, Ev-001)")

        # Store identifiers
        self._examiner_id = examiner_id
        self._case_id = case_id
        self._evidence_id = evidence_id

        self.console.print("\n[bold green]✓[/bold green] Case identifiers set:")
        self.console.print(f"  Examiner ID:  {examiner_id}")
        self.console.print(f"  Case ID:      {case_id}")
        self.console.print(f"  Evidence ID:  {evidence_id}\n")

        return examiner_id, case_id, evidence_id

    def get_case_identifiers(self) -> tuple[str | None, str | None, str | None]:
        """
        Get stored case identifiers.

        Returns:
            tuple[str | None, str | None, str | None]: (examiner_id, case_id, evidence_id)
        """
        return self._examiner_id, self._case_id, self._evidence_id

    def set_case_identifiers(self, examiner_id: str, case_id: str, evidence_id: str) -> None:
        """
        Set case identifiers programmatically (for testing).

        Args:
            examiner_id: Examiner ID
            case_id: Case ID
            evidence_id: Evidence ID

        Raises:
            ValueError: If any identifier has invalid format
        """
        if not self.validate_examiner_id(examiner_id):
            raise ValueError(f"Invalid Examiner ID format: {examiner_id}")
        if not self.validate_case_id(case_id):
            raise ValueError(f"Invalid Case ID format: {case_id}")
        if not self.validate_evidence_id(evidence_id):
            raise ValueError(f"Invalid Evidence ID format: {evidence_id}")

        self._examiner_id = examiner_id
        self._case_id = case_id
        self._evidence_id = evidence_id

    def get_case_output_dir(self, subdir: str = "") -> Path:
        """
        Get case-based output directory path.

        Args:
            subdir: Optional subdirectory name (e.g., "ios_extractions", "reports")

        Returns:
            Path: Output directory path (yaft_output/<case_id>/<evidence_id>/<subdir>)
                  Falls back to yaft_output/<subdir> if case identifiers not set
        """
        base_dir = Path.cwd() / "yaft_output"

        if self._case_id and self._evidence_id:
            if subdir:
                return base_dir / self._case_id / self._evidence_id / subdir
            return base_dir / self._case_id / self._evidence_id
        else:
            if subdir:
                return base_dir / subdir
            return base_dir

    def enable_pdf_export(self, enabled: bool = True) -> None:
        """
        Enable or disable automatic PDF export for generated reports.

        When enabled, all markdown reports will also be exported as PDF files.

        Args:
            enabled: True to enable PDF export, False to disable
        """
        self._enable_pdf_export = enabled
        if enabled:
            self.log_info("PDF export enabled for reports")

    def is_pdf_export_enabled(self) -> bool:
        """
        Check if PDF export is enabled.

        Returns:
            bool: True if PDF export is enabled
        """
        return self._enable_pdf_export

    def get_generated_reports(self) -> list[Path]:
        """
        Get list of markdown reports generated during current session.

        Returns:
            list[Path]: List of paths to generated markdown reports
        """
        return self._generated_reports.copy()

    def clear_generated_reports(self) -> None:
        """Clear the list of generated reports."""
        self._generated_reports.clear()

    def read_file(self, filepath: Path) -> str:
        """
        Read a text file safely.

        Args:
            filepath: Path to the file

        Returns:
            str: File contents

        Raises:
            FileNotFoundError: If file doesn't exist
            IOError: If file cannot be read
        """
        try:
            return filepath.read_text(encoding="utf-8")
        except Exception as e:
            self.log_error(f"Failed to read file {filepath}: {e}")
            raise

    def write_file(self, filepath: Path, content: str) -> None:
        """
        Write content to a text file safely.

        Args:
            filepath: Path to the file
            content: Content to write

        Raises:
            IOError: If file cannot be written
        """
        try:
            filepath.parent.mkdir(parents=True, exist_ok=True)
            filepath.write_text(content, encoding="utf-8")
        except Exception as e:
            self.log_error(f"Failed to write file {filepath}: {e}")
            raise

    # ========== ZIP File Handling Methods ==========

    def set_zip_file(self, zip_path: Path) -> None:
        """
        Set the current ZIP file for analysis.

        Args:
            zip_path: Path to the ZIP file

        Raises:
            FileNotFoundError: If ZIP file doesn't exist
            zipfile.BadZipFile: If file is not a valid ZIP
        """
        if not zip_path.exists():
            raise FileNotFoundError(f"ZIP file not found: {zip_path}")

        if not zipfile.is_zipfile(zip_path):
            raise zipfile.BadZipFile(f"Not a valid ZIP file: {zip_path}")

        # Close previous ZIP if open
        self.close_zip()

        self._current_zip = zip_path
        self._zip_handle = zipfile.ZipFile(zip_path, "r")
        self.log_info(f"Loaded ZIP file: {zip_path.name}")

    def get_current_zip(self) -> Path | None:
        """
        Get the path to the currently loaded ZIP file.

        Returns:
            Path | None: Path to current ZIP file, or None if no ZIP loaded
        """
        return self._current_zip

    def close_zip(self) -> None:
        """Close the currently open ZIP file."""
        if self._zip_handle:
            self._zip_handle.close()
            self._zip_handle = None
            self._current_zip = None
            self._detected_os = ExtractionOS.UNKNOWN

    # ========== OS Detection Methods ==========

    def detect_extraction_os(self) -> ExtractionOS:
        """
        Detect operating system type from ZIP file structure.

        Analyzes the ZIP file contents to determine if it's an iOS or Android extraction
        by looking for characteristic file paths and directory structures.

        Returns:
            ExtractionOS: Detected OS type (IOS, ANDROID, or UNKNOWN)

        Raises:
            RuntimeError: If no ZIP file is currently loaded
        """
        if not self._zip_handle:
            raise RuntimeError("No ZIP file loaded. Use set_zip_file() first.")

        # Get all file paths from ZIP
        file_list = [info.filename.lower() for info in self._zip_handle.infolist()]

        # iOS indicators (with and without Cellebrite/GrayKey prefixes)
        ios_indicators = [
            "private/var/mobile/",
            "library/",
            "applications/",
            "system/library/frameworks/",
            "system/library/coreservices/",
            "/private/var/mobile/",
            "/library/",
            "/applications/",
            "systemversion.plist",
        ]

        # Android indicators
        android_indicators = [
            "data/data/",
            "data/app/",
            "system/app/",
            "system/framework/",
            "data/system/",
            "/data/data/",
            "/data/app/",
            "/system/app/",
            "build.prop",
        ]

        # Count matches for each OS
        ios_matches = sum(1 for indicator in ios_indicators if any(indicator in path for path in file_list))
        android_matches = sum(1 for indicator in android_indicators if any(indicator in path for path in file_list))

        # Determine OS based on strongest match (require at least 2 matches for confidence)
        if ios_matches >= 2 and ios_matches > android_matches:
            self._detected_os = ExtractionOS.IOS
        elif android_matches >= 2 and android_matches > ios_matches:
            self._detected_os = ExtractionOS.ANDROID
        else:
            self._detected_os = ExtractionOS.UNKNOWN

        return self._detected_os

    def get_detected_os(self) -> ExtractionOS:
        """
        Get the detected OS type for the current extraction.

        Returns the cached OS detection result. If detection hasn't been run yet,
        it will be performed automatically.

        Returns:
            ExtractionOS: Detected OS type

        Raises:
            RuntimeError: If no ZIP file is currently loaded
        """
        if not self._zip_handle:
            raise RuntimeError("No ZIP file loaded. Use set_zip_file() first.")

        if self._detected_os == ExtractionOS.UNKNOWN:
            return self.detect_extraction_os()

        return self._detected_os

    def get_ios_version(self) -> str | None:
        """
        Extract iOS version from SystemVersion.plist.

        Returns:
            str | None: iOS version string (e.g., "15.4.1") or None if not found
        """
        if self._detected_os != ExtractionOS.IOS:
            return None

        # Try multiple possible locations (with/without prefixes)
        possible_paths = [
            "System/Library/CoreServices/SystemVersion.plist",
            "filesystem/System/Library/CoreServices/SystemVersion.plist",
            "filesystem1/System/Library/CoreServices/SystemVersion.plist",
        ]

        for path in possible_paths:
            try:
                plist_data = self.read_plist_from_zip(path)
                version = plist_data.get("ProductVersion")
                return str(version) if version else None
            except (KeyError, Exception):
                continue

        return None

    def get_android_version(self) -> str | None:
        """
        Extract Android version from build.prop.

        Returns:
            str | None: Android version string (e.g., "12") or None if not found
        """
        if self._detected_os != ExtractionOS.ANDROID:
            return None

        # Try multiple possible locations
        possible_paths = [
            "system/build.prop",
            "filesystem/system/build.prop",
        ]

        for path in possible_paths:
            try:
                content = self.read_zip_file_text(path)
                for line in content.split('\n'):
                    if line.startswith('ro.build.version.release='):
                        return line.split('=', 1)[1].strip()
            except (KeyError, Exception):
                continue

        return None

    def get_extraction_info(self) -> dict[str, Any]:
        """
        Get comprehensive extraction information including OS type and version.

        Returns:
            dict[str, Any]: Dictionary containing:
                - os_type: Detected OS (ios, android, unknown)
                - os_version: OS version string if available
                - detection_confidence: Detection confidence indicator
        """
        os_type = self.get_detected_os()

        info = {
            "os_type": os_type.value,
            "os_version": None,
            "detection_confidence": "unknown"
        }

        if os_type == ExtractionOS.IOS:
            info["os_version"] = self.get_ios_version()
            info["detection_confidence"] = "high" if info["os_version"] else "medium"
        elif os_type == ExtractionOS.ANDROID:
            info["os_version"] = self.get_android_version()
            info["detection_confidence"] = "high" if info["os_version"] else "medium"

        return info

    # ========== End OS Detection Methods ==========

    def list_zip_contents(self) -> list[zipfile.ZipInfo]:
        """
        List all files in the current ZIP archive.

        Returns:
            list[ZipInfo]: List of file information objects

        Raises:
            RuntimeError: If no ZIP file is currently loaded
        """
        if not self._zip_handle:
            raise RuntimeError("No ZIP file loaded. Use set_zip_file() first.")

        return self._zip_handle.infolist()

    def get_zip_info(self, filename: str) -> zipfile.ZipInfo | None:
        """
        Get information about a specific file in the ZIP archive.

        Args:
            filename: Name of file in ZIP archive

        Returns:
            ZipInfo | None: File information or None if not found

        Raises:
            RuntimeError: If no ZIP file is currently loaded
        """
        if not self._zip_handle:
            raise RuntimeError("No ZIP file loaded. Use set_zip_file() first.")

        try:
            return self._zip_handle.getinfo(filename)
        except KeyError:
            return None

    def read_zip_file(self, filename: str) -> bytes:
        """
        Read a file from the current ZIP archive.

        Args:
            filename: Name of file in ZIP archive

        Returns:
            bytes: File contents as bytes

        Raises:
            RuntimeError: If no ZIP file is currently loaded
            KeyError: If file not found in ZIP
        """
        if not self._zip_handle:
            raise RuntimeError("No ZIP file loaded. Use set_zip_file() first.")

        return self._zip_handle.read(filename)

    def read_zip_file_text(self, filename: str, encoding: str = "utf-8") -> str:
        """
        Read a text file from the current ZIP archive.

        Args:
            filename: Name of file in ZIP archive
            encoding: Text encoding (default: utf-8)

        Returns:
            str: File contents as string

        Raises:
            RuntimeError: If no ZIP file is currently loaded
            KeyError: If file not found in ZIP
            UnicodeDecodeError: If file cannot be decoded with given encoding
        """
        data = self.read_zip_file(filename)
        return data.decode(encoding)

    def extract_zip_file(self, filename: str, output_dir: Path) -> Path:
        """
        Extract a single file from the ZIP archive.

        Args:
            filename: Name of file in ZIP archive
            output_dir: Directory to extract file to

        Returns:
            Path: Path to extracted file

        Raises:
            RuntimeError: If no ZIP file is currently loaded
            KeyError: If file not found in ZIP
        """
        if not self._zip_handle:
            raise RuntimeError("No ZIP file loaded. Use set_zip_file() first.")

        output_dir.mkdir(parents=True, exist_ok=True)
        extracted_path = self._zip_handle.extract(filename, output_dir)
        return Path(extracted_path)

    def extract_all_zip(self, output_dir: Path) -> Path:
        """
        Extract all files from the ZIP archive.

        Args:
            output_dir: Directory to extract files to

        Returns:
            Path: Path to extraction directory

        Raises:
            RuntimeError: If no ZIP file is currently loaded
        """
        if not self._zip_handle:
            raise RuntimeError("No ZIP file loaded. Use set_zip_file() first.")

        output_dir.mkdir(parents=True, exist_ok=True)
        self._zip_handle.extractall(output_dir)
        self.log_info(f"Extracted all files to: {output_dir}")
        return output_dir

    def find_files_in_zip(
        self,
        pattern: str,
        *,
        case_sensitive: bool = False,
        search_path: str | None = None,
        max_results: int | None = None
    ) -> list[str]:
        """
        Find files in the ZIP archive matching the given pattern.

        Supports glob-style wildcard patterns for flexible file searching:
        - Exact filename: "file.txt" - matches only "file.txt"
        - Wildcard extension: "file.*" - matches "file.txt", "file.db", etc.
        - Wildcard name: "*.txt" - matches all .txt files
        - Multiple wildcards: "*log*.txt" - matches "error_log_2024.txt", "system.log.txt", etc.
        - Path patterns: "data/*/*.db" - matches databases two levels deep in data/
        - Question mark: "file?.txt" - matches "file1.txt", "fileA.txt", etc.

        Args:
            pattern: File pattern to search for (supports * and ? wildcards)
            case_sensitive: Whether search should be case-sensitive (default: False)
            search_path: Optional path prefix to limit search scope (e.g., "data/data/", "System/")
            max_results: Maximum number of results to return (default: unlimited)

        Returns:
            list[str]: List of matching file paths in the ZIP archive, sorted alphabetically

        Raises:
            RuntimeError: If no ZIP file is currently loaded
            ValueError: If pattern is empty or invalid

        Examples:
            >>> # Find specific file
            >>> files = api.find_files_in_zip("SystemVersion.plist")

            >>> # Find all log files
            >>> files = api.find_files_in_zip("*.log")

            >>> # Find all databases in Android data directory
            >>> files = api.find_files_in_zip("*.db", search_path="data/data/")

            >>> # Find call log databases (case-insensitive)
            >>> files = api.find_files_in_zip("*call*.db", case_sensitive=False)

            >>> # Find files with wildcard path and name
            >>> files = api.find_files_in_zip("*/Library/Preferences/*.plist")
        """
        import fnmatch

        if not self._zip_handle:
            raise RuntimeError("No ZIP file loaded. Use set_zip_file() first.")

        if not pattern or not pattern.strip():
            raise ValueError("Search pattern cannot be empty")

        pattern = pattern.strip()

        # Get all file paths from ZIP (exclude directories)
        all_files = [info.filename for info in self._zip_handle.infolist() if not info.is_dir()]

        # Filter by search_path if provided
        if search_path:
            search_path = search_path.strip()
            if not case_sensitive:
                search_path_lower = search_path.lower()
                all_files = [f for f in all_files if f.lower().startswith(search_path_lower)]
            else:
                all_files = [f for f in all_files if f.startswith(search_path)]

        # Prepare pattern for matching
        if not case_sensitive:
            pattern = pattern.lower()

        # Match files against pattern
        matches = []
        for filepath in all_files:
            # Get the filename to match against
            if case_sensitive:
                match_target = filepath
            else:
                match_target = filepath.lower()

            # If search_path is specified, match against the relative path
            if search_path:
                # Remove the search_path prefix for pattern matching
                search_prefix = search_path if case_sensitive else search_path.lower()
                if match_target.startswith(search_prefix):
                    relative_path = match_target[len(search_prefix):]
                    # Use case-sensitive string comparison for pattern matching
                    if case_sensitive:
                        if fnmatch.fnmatchcase(relative_path, pattern):
                            matches.append(filepath)
                    else:
                        if fnmatch.fnmatch(relative_path, pattern):
                            matches.append(filepath)
            else:
                # Match against full path or just filename depending on pattern
                if '/' in pattern:
                    # Pattern includes path components, match full path
                    if case_sensitive:
                        if fnmatch.fnmatchcase(match_target, pattern):
                            matches.append(filepath)
                    else:
                        if fnmatch.fnmatch(match_target, pattern):
                            matches.append(filepath)
                else:
                    # Pattern is filename only, match just the basename
                    basename = match_target.split('/')[-1]
                    if case_sensitive:
                        if fnmatch.fnmatchcase(basename, pattern):
                            matches.append(filepath)
                    else:
                        if fnmatch.fnmatch(basename, pattern):
                            matches.append(filepath)

            # Check if we've hit the max results limit
            if max_results is not None and len(matches) >= max_results:
                break

        # Sort results alphabetically for consistent output
        matches.sort()

        return matches

    def display_zip_contents(self) -> None:
        """
        Display a formatted table of ZIP contents.

        Raises:
            RuntimeError: If no ZIP file is currently loaded
        """
        if not self._zip_handle:
            raise RuntimeError("No ZIP file loaded. Use set_zip_file() first.")

        table = Table(title=f"Contents of {self._current_zip.name if self._current_zip else 'ZIP'}")
        table.add_column("Filename", style="cyan", no_wrap=False)
        table.add_column("Size", justify="right", style="green")
        table.add_column("Compressed", justify="right", style="yellow")
        table.add_column("Date Modified", style="blue")

        total_size = 0
        total_compressed = 0

        for file_info in self._zip_handle.infolist():
            if not file_info.is_dir():
                date_time = f"{file_info.date_time[0]}-{file_info.date_time[1]:02d}-{file_info.date_time[2]:02d} " \
                           f"{file_info.date_time[3]:02d}:{file_info.date_time[4]:02d}"

                table.add_row(
                    file_info.filename,
                    self._format_size(file_info.file_size),
                    self._format_size(file_info.compress_size),
                    date_time,
                )
                total_size += file_info.file_size
                total_compressed += file_info.compress_size

        # Add summary row
        compression_ratio = (1 - total_compressed / total_size) * 100 if total_size > 0 else 0
        table.add_section()
        table.add_row(
            "[bold]TOTAL[/bold]",
            f"[bold]{self._format_size(total_size)}[/bold]",
            f"[bold]{self._format_size(total_compressed)}[/bold] ({compression_ratio:.1f}% compression)",
            "",
        )

        self.console.print(table)

    def _format_size(self, size: int) -> str:
        """
        Format file size in human-readable format.

        Args:
            size: Size in bytes

        Returns:
            str: Formatted size string
        """
        size_float = float(size)
        for unit in ["B", "KB", "MB", "GB", "TB"]:
            if size_float < 1024.0:
                return f"{size_float:.2f} {unit}"
            size_float /= 1024.0
        return f"{size_float:.2f} PB"

    # ========== Forensic ZIP Format Detection ==========

    def detect_zip_format(self) -> tuple[str, str]:
        """
        Detect the format of a loaded forensic ZIP file (Cellebrite, GrayKey, etc.).

        Returns:
            tuple[str, str]: A tuple of (format_type, path_prefix) where:
                - format_type: "cellebrite_ios", "cellebrite_android", "graykey_ios", "graykey_android", or "unknown"
                - path_prefix: The prefix to use for paths ("filesystem1/", "Dump/", or "")

        Raises:
            RuntimeError: If no ZIP file is currently loaded

        Examples:
            >>> format_type, prefix = api.detect_zip_format()
            >>> if format_type == "cellebrite_ios":
            ...     full_path = prefix + "System/Library/CoreServices/SystemVersion.plist"
        """
        if not self._zip_handle:
            raise RuntimeError("No ZIP file loaded. Use set_zip_file() first.")

        files = self.list_zip_contents()

        # Get root-level folders (check first 100 entries to find directories)
        root_folders = set()
        for file_info in files[:100]:
            filename = file_info.filename
            # Extract the first-level folder
            parts = filename.split('/')
            if len(parts) > 1:
                root_folders.add(parts[0] + '/')

        # Check for Cellebrite Android format (Dump/ and extra/ folders)
        if 'Dump/' in root_folders or 'extra/' in root_folders and not 'filesystem1/' in root_folders:
            self.log_info("Detected format: Cellebrite Android (Dump/extra/)")
            return ("cellebrite_android", "Dump/")

        # Check for Cellebrite iOS format (filesystem1/ or filesystem/)
        if 'filesystem1/' in root_folders:
            self.log_info("Detected format: Cellebrite iOS (filesystem1/)")
            return ("cellebrite_ios", "filesystem1/")
        elif 'filesystem/' in root_folders:
            self.log_info("Detected format: Cellebrite iOS (filesystem/)")
            return ("cellebrite_ios", "filesystem/")

        # Check for legacy Cellebrite Android format (fs/)
        if 'fs/' in root_folders:
            self.log_info("Detected format: Cellebrite Android (fs/)")
            return ("cellebrite_android", "fs/")

        # Check for GrayKey Android format (characteristic root folders)
        graykey_android_folders = {'apex/', 'bootstrap-apex/', 'cache/', 'data/', 'data-mirror/', 'efs/', 'system/'}
        if len(graykey_android_folders & root_folders) >= 3:  # At least 3 matches
            self.log_info("Detected format: GrayKey Android (no prefix)")
            return ("graykey_android", "")

        # Check for GrayKey iOS format (characteristic iOS paths)
        graykey_ios_folders = {'private/', 'System/', 'Library/', 'Applications/', 'var/'}
        if len(graykey_ios_folders & root_folders) >= 2:  # At least 2 matches
            self.log_info("Detected format: GrayKey iOS (no prefix)")
            return ("graykey_ios", "")

        # Fallback: Look deeper into file structure
        for file_info in files[:50]:
            filename = file_info.filename.lower()
            # iOS indicators
            if (
                filename.startswith('private/var/')
                or filename.startswith('system/library/')
                or filename.startswith('library/')
            ):
                self.log_info("Detected format: GrayKey/Raw iOS filesystem (no prefix)")
                return ("graykey_ios", "")
            # Android indicators
            if (
                filename.startswith('data/data/')
                or filename.startswith('system/build.prop')
                or filename.startswith('system/app/')
            ):
                self.log_info("Detected format: GrayKey/Raw Android filesystem (no prefix)")
                return ("graykey_android", "")

        self.log_warning("Could not detect extraction format, using raw access")
        return ("unknown", "")

    def normalize_zip_path(self, path: str, prefix: str = "") -> str:
        """
        Normalize a filesystem path for ZIP access by adding the appropriate prefix.

        Args:
            path: The filesystem path (e.g., "System/Library/CoreServices/SystemVersion.plist")
            prefix: The prefix to add (e.g., "filesystem1/", "fs/", "")

        Returns:
            str: The normalized path for ZIP access

        Examples:
            >>> _, prefix = api.detect_zip_format()
            >>> full_path = api.normalize_zip_path("System/Library/file.plist", prefix)
        """
        if prefix:
            return prefix + path
        return path

    def export_plugin_data_to_json(
        self,
        output_path: Path,
        plugin_name: str,
        plugin_version: str,
        data: dict[str, Any],
        extraction_type: str = "unknown",
        errors: list[dict[str, str]] | None = None,
    ) -> None:
        """
        Export plugin data to JSON file with standardized format.

        Args:
            output_path: Path where JSON file should be written
            plugin_name: Name of the plugin
            plugin_version: Version of the plugin
            data: The data to export
            extraction_type: Type of extraction ("cellebrite", "graykey", "unknown")
            errors: Optional list of errors encountered during extraction

        Examples:
            >>> api.export_plugin_data_to_json(
            ...     Path("output.json"),
            ...     "MyPlugin",
            ...     "1.0.0",
            ...     {"key": "value"},
            ...     "cellebrite",
            ...     [{"source": "file.db", "error": "not found"}]
            ... )
        """
        import json
        from datetime import datetime, UTC

        output_data = {
            "plugin_name": plugin_name,
            "plugin_version": plugin_version,
            "extraction_source": extraction_type,
            "processing_timestamp": datetime.now(UTC).isoformat(),
            "data": data,
            "errors": errors or [],
        }

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False, default=str)

        self.log_info(f"Exported data to: {output_path}")

    # ========== Plist Parsing Methods ==========

    def parse_plist(self, content: bytes) -> Any:
        """
        Parse plist content from bytes.

        Args:
            content: Plist file content as bytes

        Returns:
            Any: Parsed plist data (usually dict or list)

        Raises:
            Exception: If plist parsing fails
        """
        try:
            return plistlib.loads(content)
        except Exception as e:
            self.log_error(f"Failed to parse plist: {e}")
            raise

    def read_plist_from_zip(self, path: str) -> Any:
        """
        Read and parse a plist file from the current ZIP archive.

        Args:
            path: Path to plist file within the ZIP archive

        Returns:
            Any: Parsed plist data (usually dict or list)

        Raises:
            RuntimeError: If no ZIP file is currently loaded
            KeyError: If file is not found in ZIP
            Exception: If plist parsing fails
        """
        content = self.read_zip_file(path)
        return self.parse_plist(content)

    # ========== XML Parsing Methods ==========

    def parse_xml(self, content: bytes | str) -> Any:
        """
        Parse XML content from bytes or string.

        Args:
            content: XML file content as bytes or string

        Returns:
            xml.etree.ElementTree.Element: Root element of parsed XML tree

        Raises:
            Exception: If XML parsing fails
        """
        import xml.etree.ElementTree as ET

        try:
            if isinstance(content, bytes):
                content_str = content.decode('utf-8')
            else:
                content_str = content

            return ET.fromstring(content_str)
        except Exception as e:
            self.log_error(f"Failed to parse XML: {e}")
            raise

    def read_xml_from_zip(self, path: str) -> Any:
        """
        Read and parse an XML file from the current ZIP archive.

        Args:
            path: Path to XML file within the ZIP archive

        Returns:
            xml.etree.ElementTree.Element: Root element of parsed XML tree

        Raises:
            RuntimeError: If no ZIP file is currently loaded
            KeyError: If file is not found in ZIP
            Exception: If XML parsing fails
        """
        content = self.read_zip_file(path)
        return self.parse_xml(content)

    # ========== SQLite Database Methods ==========

    def query_sqlcipher_from_zip(
        self,
        db_path: str,
        key: str,
        query: str,
        params: tuple = (),
        fallback_query: str | None = None,
        cipher_version: int | None = None,
    ) -> list[tuple]:
        """
        Execute SQL query on an encrypted SQLCipher database from the ZIP archive.

        This method extracts the encrypted database to a temporary file, decrypts it
        using the provided key, executes the query, and returns the results as a list of tuples.

        Args:
            db_path: Path to encrypted SQLCipher database within the ZIP archive
            key: Encryption key/password for the database
            query: SQL query to execute
            params: Optional tuple of query parameters
            fallback_query: Optional fallback query if primary query fails (e.g., for schema differences)
            cipher_version: Optional SQLCipher version compatibility (1-4). Use this for older databases.
                           If None, uses default (SQLCipher 4)

        Returns:
            list[tuple]: Query results as list of tuples

        Raises:
            RuntimeError: If no ZIP file is currently loaded
            KeyError: If database file is not found in ZIP
            ImportError: If sqlcipher3 is not installed
            Exception: If decryption fails (wrong key, corrupted database)

        Examples:
            >>> # Query with default SQLCipher version
            >>> rows = api.query_sqlcipher_from_zip(
            ...     "private/var/mobile/Containers/Data/Application/.../Documents/database.db",
            ...     "encryption_key_123",
            ...     "SELECT * FROM messages WHERE date > ?",
            ...     params=(1234567890,)
            ... )

            >>> # Query with SQLCipher v3 compatibility (older iOS apps)
            >>> rows = api.query_sqlcipher_from_zip(
            ...     "databases/whatsapp.db",
            ...     "my_key",
            ...     "SELECT * FROM chat",
            ...     cipher_version=3
            ... )
        """
        try:
            from sqlcipher3 import dbapi2 as sqlcipher
        except ImportError as e:
            error_msg = (
                "SQLCipher support requires 'sqlcipher3' package. "
                "Install with: uv pip install sqlcipher3"
            )
            self.log_error(error_msg)
            raise ImportError(error_msg) from e

        temp_db_path = None
        try:
            # Extract database to temporary file
            content = self.read_zip_file(db_path)

            # Create temp file
            with tempfile.NamedTemporaryFile(delete=False, suffix='.db') as temp_file:
                temp_db_path = Path(temp_file.name)
                temp_file.write(content)

            # Connect to encrypted database
            conn = sqlcipher.connect(str(temp_db_path))
            cursor = conn.cursor()

            # Set encryption key
            cursor.execute(f"PRAGMA key = '{key}'")

            # Set cipher version compatibility if specified
            if cipher_version is not None:
                cursor.execute(f"PRAGMA cipher_compatibility = {cipher_version}")

            # Verify database is accessible (will fail if wrong key)
            try:
                cursor.execute("SELECT count(*) FROM sqlite_master")
                cursor.fetchone()
            except Exception as e:
                conn.close()
                raise ValueError(
                    f"Failed to decrypt database. Possible causes: wrong key, corrupted database, "
                    f"or incompatible SQLCipher version. Error: {e}"
                ) from e

            # Execute the actual query
            try:
                cursor.execute(query, params)
                results: list[tuple] = cursor.fetchall()
            except sqlcipher.OperationalError as e:
                if fallback_query:
                    self.log_warning(f"Primary query failed, trying fallback: {e}")
                    cursor.execute(fallback_query, params)
                    results = cursor.fetchall()
                else:
                    raise

            conn.close()
            return results

        finally:
            # Clean up temp file
            if temp_db_path and temp_db_path.exists():
                try:
                    temp_db_path.unlink()
                except Exception as e:
                    self.log_warning(f"Failed to delete temp database file: {e}")

    def query_sqlcipher_from_zip_dict(
        self,
        db_path: str,
        key: str,
        query: str,
        params: tuple = (),
        fallback_query: str | None = None,
        cipher_version: int | None = None,
    ) -> list[dict[str, Any]]:
        """
        Execute SQL query on an encrypted SQLCipher database from ZIP and return results as dictionaries.

        This method extracts the encrypted database to a temporary file, decrypts it,
        executes the query, and returns the results as a list of dictionaries with column names as keys.

        Args:
            db_path: Path to encrypted SQLCipher database within the ZIP archive
            key: Encryption key/password for the database
            query: SQL query to execute
            params: Optional tuple of query parameters
            fallback_query: Optional fallback query if primary query fails
            cipher_version: Optional SQLCipher version compatibility (1-4)

        Returns:
            list[dict[str, Any]]: Query results as list of dictionaries

        Raises:
            RuntimeError: If no ZIP file is currently loaded
            KeyError: If database file is not found in ZIP
            ImportError: If sqlcipher3 is not installed
            Exception: If decryption fails

        Examples:
            >>> # Query WhatsApp messages
            >>> messages = api.query_sqlcipher_from_zip_dict(
            ...     "data/data/com.whatsapp/databases/msgstore.db",
            ...     "encryption_key",
            ...     "SELECT key_remote_jid, data, timestamp FROM messages ORDER BY timestamp DESC LIMIT 100"
            ... )
            >>> for msg in messages:
            ...     print(f"{msg['timestamp']}: {msg['data']}")
        """
        try:
            from sqlcipher3 import dbapi2 as sqlcipher
        except ImportError as e:
            error_msg = (
                "SQLCipher support requires 'sqlcipher3' package. "
                "Install with: uv pip install sqlcipher3"
            )
            self.log_error(error_msg)
            raise ImportError(error_msg) from e

        temp_db_path = None
        try:
            # Extract database to temporary file
            content = self.read_zip_file(db_path)

            # Create temp file
            with tempfile.NamedTemporaryFile(delete=False, suffix='.db') as temp_file:
                temp_db_path = Path(temp_file.name)
                temp_file.write(content)

            # Connect to encrypted database
            conn = sqlcipher.connect(str(temp_db_path))
            conn.row_factory = sqlcipher.Row
            cursor = conn.cursor()

            # Set encryption key
            cursor.execute(f"PRAGMA key = '{key}'")

            # Set cipher version compatibility if specified
            if cipher_version is not None:
                cursor.execute(f"PRAGMA cipher_compatibility = {cipher_version}")

            # Verify database is accessible
            try:
                cursor.execute("SELECT count(*) FROM sqlite_master")
                cursor.fetchone()
            except Exception as e:
                conn.close()
                raise ValueError(
                    f"Failed to decrypt database. Possible causes: wrong key, corrupted database, "
                    f"or incompatible SQLCipher version. Error: {e}"
                ) from e

            # Execute the actual query
            try:
                cursor.execute(query, params)
                rows = cursor.fetchall()
                results = [dict(row) for row in rows]
            except sqlcipher.OperationalError as e:
                if fallback_query:
                    self.log_warning(f"Primary query failed, trying fallback: {e}")
                    cursor.execute(fallback_query, params)
                    rows = cursor.fetchall()
                    results = [dict(row) for row in rows]
                else:
                    raise

            conn.close()
            return results

        finally:
            # Clean up temp file
            if temp_db_path and temp_db_path.exists():
                try:
                    temp_db_path.unlink()
                except Exception as e:
                    self.log_warning(f"Failed to delete temp database file: {e}")

    def decrypt_sqlcipher_database(
        self,
        db_path: str,
        key: str,
        output_path: Path,
        cipher_version: int | None = None,
    ) -> Path:
        """
        Decrypt a SQLCipher database from ZIP and save as plain SQLite database.

        This method extracts an encrypted database, decrypts it, and exports it as
        a standard unencrypted SQLite database file. Useful for forensic analysis
        when you need to use other SQLite tools.

        Args:
            db_path: Path to encrypted SQLCipher database within the ZIP archive
            key: Encryption key/password for the database
            output_path: Path where decrypted SQLite database should be saved
            cipher_version: Optional SQLCipher version compatibility (1-4)

        Returns:
            Path: Path to decrypted SQLite database file

        Raises:
            RuntimeError: If no ZIP file is currently loaded
            KeyError: If database file is not found in ZIP
            ImportError: If sqlcipher3 is not installed
            Exception: If decryption fails

        Examples:
            >>> # Decrypt WhatsApp database for analysis
            >>> decrypted_db = api.decrypt_sqlcipher_database(
            ...     "data/data/com.whatsapp/databases/msgstore.db",
            ...     "my_encryption_key",
            ...     Path("yaft_output/decrypted/whatsapp_msgstore.db")
            ... )
            >>> # Now you can use standard SQLite tools on decrypted_db
        """
        try:
            from sqlcipher3 import dbapi2 as sqlcipher
        except ImportError as e:
            error_msg = (
                "SQLCipher support requires 'sqlcipher3' package. "
                "Install with: uv pip install sqlcipher3"
            )
            self.log_error(error_msg)
            raise ImportError(error_msg) from e

        temp_encrypted_path = None
        try:
            # Extract encrypted database to temporary file
            content = self.read_zip_file(db_path)

            # Create temp file for encrypted database
            with tempfile.NamedTemporaryFile(delete=False, suffix='.db') as temp_file:
                temp_encrypted_path = Path(temp_file.name)
                temp_file.write(content)

            # Ensure output directory exists
            output_path.parent.mkdir(parents=True, exist_ok=True)

            # Connect to encrypted database
            conn = sqlcipher.connect(str(temp_encrypted_path))
            cursor = conn.cursor()

            # Set encryption key
            cursor.execute(f"PRAGMA key = '{key}'")

            # Set cipher version compatibility if specified
            if cipher_version is not None:
                cursor.execute(f"PRAGMA cipher_compatibility = {cipher_version}")

            # Verify database is accessible
            try:
                cursor.execute("SELECT count(*) FROM sqlite_master")
                cursor.fetchone()
            except Exception as e:
                conn.close()
                raise ValueError(
                    f"Failed to decrypt database. Possible causes: wrong key, corrupted database, "
                    f"or incompatible SQLCipher version. Error: {e}"
                ) from e

            # Export to plaintext SQLite database
            # SQLCipher 4 uses: ATTACH DATABASE 'plaintext.db' AS plaintext KEY '';
            # Then: SELECT sqlcipher_export('plaintext');
            cursor.execute(f"ATTACH DATABASE '{output_path}' AS plaintext KEY ''")
            cursor.execute("SELECT sqlcipher_export('plaintext')")
            cursor.execute("DETACH DATABASE plaintext")

            conn.close()

            self.log_info(f"Decrypted database saved to: {output_path}")
            return output_path

        except Exception as e:
            self.log_error(f"Failed to decrypt database: {e}")
            raise
        finally:
            # Clean up temp file
            if temp_encrypted_path and temp_encrypted_path.exists():
                try:
                    temp_encrypted_path.unlink()
                except Exception as e:
                    self.log_warning(f"Failed to delete temp encrypted database file: {e}")

    def query_sqlite_from_zip(
        self,
        db_path: str,
        query: str,
        params: tuple = (),
        fallback_query: str | None = None
    ) -> list[tuple]:
        """
        Execute SQL query on a SQLite database from the ZIP archive.

        This method extracts the database to a temporary file, executes the query,
        and returns the results as a list of tuples.

        Args:
            db_path: Path to SQLite database within the ZIP archive
            query: SQL query to execute
            params: Optional tuple of query parameters
            fallback_query: Optional fallback query if primary query fails (e.g., for schema differences)

        Returns:
            list[tuple]: Query results as list of tuples

        Raises:
            RuntimeError: If no ZIP file is currently loaded
            KeyError: If database file is not found in ZIP
            sqlite3.Error: If database query fails
        """
        temp_db_path = None
        try:
            # Extract database to temporary file
            content = self.read_zip_file(db_path)

            # Create temp file
            with tempfile.NamedTemporaryFile(delete=False, suffix='.db') as temp_file:
                temp_db_path = Path(temp_file.name)
                temp_file.write(content)

            # Query the database
            conn = sqlite3.connect(str(temp_db_path))
            cursor = conn.cursor()

            try:
                cursor.execute(query, params)
                results = cursor.fetchall()
            except sqlite3.OperationalError as e:
                if fallback_query:
                    self.log_warning(f"Primary query failed, trying fallback: {e}")
                    cursor.execute(fallback_query, params)
                    results = cursor.fetchall()
                else:
                    raise

            conn.close()
            return results

        finally:
            # Clean up temp file
            if temp_db_path and temp_db_path.exists():
                try:
                    temp_db_path.unlink()
                except Exception as e:
                    self.log_warning(f"Failed to delete temp database file: {e}")

    def query_sqlite_from_zip_dict(
        self,
        db_path: str,
        query: str,
        params: tuple = (),
        fallback_query: str | None = None
    ) -> list[dict[str, Any]]:
        """
        Execute SQL query on a SQLite database from ZIP and return results as dictionaries.

        This method extracts the database to a temporary file, executes the query,
        and returns the results as a list of dictionaries with column names as keys.

        Args:
            db_path: Path to SQLite database within the ZIP archive
            query: SQL query to execute
            params: Optional tuple of query parameters
            fallback_query: Optional fallback query if primary query fails

        Returns:
            list[dict[str, Any]]: Query results as list of dictionaries

        Raises:
            RuntimeError: If no ZIP file is currently loaded
            KeyError: If database file is not found in ZIP
            sqlite3.Error: If database query fails
        """
        temp_db_path = None
        try:
            # Extract database to temporary file
            content = self.read_zip_file(db_path)

            # Create temp file
            with tempfile.NamedTemporaryFile(delete=False, suffix='.db') as temp_file:
                temp_db_path = Path(temp_file.name)
                temp_file.write(content)

            # Query the database with row_factory
            conn = sqlite3.connect(str(temp_db_path))
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            try:
                cursor.execute(query, params)
                rows = cursor.fetchall()
                results = [dict(row) for row in rows]
            except sqlite3.OperationalError as e:
                if fallback_query:
                    self.log_warning(f"Primary query failed, trying fallback: {e}")
                    cursor.execute(fallback_query, params)
                    rows = cursor.fetchall()
                    results = [dict(row) for row in rows]
                else:
                    raise

            conn.close()
            return results

        finally:
            # Clean up temp file
            if temp_db_path and temp_db_path.exists():
                try:
                    temp_db_path.unlink()
                except Exception as e:
                    self.log_warning(f"Failed to delete temp database file: {e}")

    # ========== Report Generation Methods ==========

    def convert_markdown_to_pdf(self, markdown_path: Path, pdf_path: Path | None = None) -> Path:
        """
        Convert a markdown file to PDF format.

        Args:
            markdown_path: Path to the markdown file
            pdf_path: Optional path for the PDF output (defaults to same name with .pdf extension)

        Returns:
            Path: Path to generated PDF file

        Raises:
            ImportError: If weasyprint is not installed
            FileNotFoundError: If markdown file doesn't exist
            Exception: If PDF conversion fails
        """
        try:
            import markdown
            from weasyprint import HTML  # type: ignore[import-untyped,unused-ignore]
        except ImportError as e:
            error_msg = (
                "PDF export requires 'markdown' and 'weasyprint' packages. "
                "Install with: uv pip install markdown weasyprint"
            )
            self.log_error(error_msg)
            raise ImportError(error_msg) from e

        if not markdown_path.exists():
            raise FileNotFoundError(f"Markdown file not found: {markdown_path}")

        # Default PDF path
        if pdf_path is None:
            pdf_path = markdown_path.with_suffix('.pdf')

        try:
            # Read markdown content
            md_content = markdown_path.read_text(encoding='utf-8')

            # Convert markdown to HTML with extensions for better formatting
            html_content = markdown.markdown(
                md_content,
                extensions=['tables', 'fenced_code', 'nl2br']
            )

            # Add CSS styling for better PDF formatting
            css_style = """
            <style>
                @page {
                    size: A4;
                    margin: 2cm;
                }
                body {
                    font-family: 'Segoe UI', Arial, sans-serif;
                    font-size: 11pt;
                    line-height: 1.6;
                    color: #333;
                }
                h1 {
                    font-size: 24pt;
                    color: #2c3e50;
                    border-bottom: 3px solid #3498db;
                    padding-bottom: 10px;
                    margin-top: 20px;
                    margin-bottom: 20px;
                }
                h2 {
                    font-size: 18pt;
                    color: #34495e;
                    border-bottom: 2px solid #bdc3c7;
                    padding-bottom: 8px;
                    margin-top: 18px;
                    margin-bottom: 12px;
                }
                h3 {
                    font-size: 14pt;
                    color: #34495e;
                    margin-top: 14px;
                    margin-bottom: 10px;
                }
                table {
                    width: 100%;
                    border-collapse: collapse;
                    margin: 15px 0;
                    font-size: 10pt;
                }
                th {
                    background-color: #3498db;
                    color: white;
                    font-weight: bold;
                    padding: 10px;
                    text-align: left;
                    border: 1px solid #2980b9;
                }
                td {
                    padding: 8px;
                    border: 1px solid #bdc3c7;
                }
                tr:nth-child(even) {
                    background-color: #ecf0f1;
                }
                code {
                    background-color: #f4f4f4;
                    padding: 2px 6px;
                    border-radius: 3px;
                    font-family: 'Courier New', monospace;
                    font-size: 9pt;
                }
                pre {
                    background-color: #2c3e50;
                    color: #ecf0f1;
                    padding: 15px;
                    border-radius: 5px;
                    overflow-x: auto;
                    font-family: 'Courier New', monospace;
                    font-size: 9pt;
                    line-height: 1.4;
                }
                pre code {
                    background-color: transparent;
                    color: inherit;
                    padding: 0;
                }
                ul, ol {
                    margin: 10px 0;
                    padding-left: 30px;
                }
                li {
                    margin: 5px 0;
                }
                hr {
                    border: none;
                    border-top: 2px solid #bdc3c7;
                    margin: 20px 0;
                }
                strong {
                    color: #2c3e50;
                }
            </style>
            """

            # Combine CSS and HTML
            full_html = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="utf-8">
                {css_style}
            </head>
            <body>
                {html_content}
            </body>
            </html>
            """

            # Convert HTML to PDF
            HTML(string=full_html).write_pdf(pdf_path)

            self.log_info(f"PDF generated: {pdf_path}")
            return pdf_path

        except Exception as e:
            self.log_error(f"Failed to convert markdown to PDF: {e}")
            raise

    def generate_report(
        self,
        plugin_name: str,
        title: str,
        sections: list[dict[str, Any]],
        output_dir: Path | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Path:
        """
        Generate a unified markdown report for plugin findings and results.

        This method provides a standardized way for plugins to create reports
        with consistent formatting, metadata, and structure.

        Args:
            plugin_name: Name of the plugin generating the report
            title: Report title
            sections: List of report sections, each containing:
                - heading (str): Section heading
                - content (str|list|dict): Section content
                - level (int, optional): Heading level (default: 2)
                - style (str, optional): Content style ('text'|'table'|'list'|'code', default: 'text')
            output_dir: Output directory for report (default: yaft_output/reports)
            metadata: Additional metadata to include in report header

        Returns:
            Path: Path to generated report file

        Example:
            >>> sections = [
            ...     {
            ...         "heading": "Summary",
            ...         "content": "Analysis completed successfully",
            ...     },
            ...     {
            ...         "heading": "Findings",
            ...         "content": ["Finding 1", "Finding 2"],
            ...         "style": "list",
            ...     },
            ...     {
            ...         "heading": "Statistics",
            ...         "content": {"total": 10, "suspicious": 2},
            ...         "style": "table",
            ...     },
            ... ]
            >>> report_path = core_api.generate_report(
            ...     plugin_name="MyPlugin",
            ...     title="Analysis Report",
            ...     sections=sections,
            ... )
        """
        from datetime import datetime

        # Setup output directory with case-based structure
        if output_dir is None:
            # Use case identifiers for path structure: yaft_output/<case_id>/<evidence_id>/reports
            if self._case_id and self._evidence_id:
                output_dir = Path.cwd() / "yaft_output" / self._case_id / self._evidence_id / "reports"
            else:
                # Fallback to default if identifiers not set
                output_dir = Path.cwd() / "yaft_output" / "reports"
        output_dir.mkdir(parents=True, exist_ok=True)

        # Generate filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{plugin_name}_{timestamp}.md"
        report_path = output_dir / filename

        # Build report content
        lines: list[str] = []

        # Header
        lines.append(f"# {title}")
        lines.append("")

        # Metadata section
        lines.append("---")
        lines.append("")
        lines.append("**Report Metadata**")
        lines.append("")
        lines.append(f"- **Plugin**: {plugin_name}")
        lines.append(f"- **Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        # Add case identifiers if set
        if self._examiner_id:
            lines.append(f"- **Examiner ID**: {self._examiner_id}")
        if self._case_id:
            lines.append(f"- **Case ID**: {self._case_id}")
        if self._evidence_id:
            lines.append(f"- **Evidence ID**: {self._evidence_id}")

        if self._current_zip:
            lines.append(f"- **Source ZIP**: {self._current_zip.name}")

        if metadata:
            for key, value in metadata.items():
                lines.append(f"- **{key}**: {value}")

        lines.append("")
        lines.append("---")
        lines.append("")

        # Sections
        for section in sections:
            heading = section.get("heading", "Section")
            content = section.get("content", "")
            level = section.get("level", 2)
            style = section.get("style", "text")

            # Add heading
            lines.append(f"{'#' * level} {heading}")
            lines.append("")

            # Add content based on style
            if style == "text":
                lines.append(str(content))
            elif style == "list":
                if isinstance(content, list):
                    for item in content:
                        lines.append(f"- {item}")
                else:
                    lines.append(f"- {content}")
            elif style == "code":
                lines.append("```")
                lines.append(str(content))
                lines.append("```")
            elif style == "table":
                if isinstance(content, dict):
                    # Convert dict to markdown table
                    lines.append("| Key | Value |")
                    lines.append("|-----|-------|")
                    for key, value in content.items():
                        lines.append(f"| {key} | {value} |")
                elif isinstance(content, list) and len(content) > 0:
                    # Assume list of dicts for table
                    if isinstance(content[0], dict):
                        # Get headers from first dict
                        headers = list(content[0].keys())
                        lines.append("| " + " | ".join(headers) + " |")
                        lines.append("|" + "|".join(["-----"] * len(headers)) + "|")
                        for row in content:
                            values = [str(row.get(h, "")) for h in headers]
                            lines.append("| " + " | ".join(values) + " |")
                    else:
                        # Simple list to single-column table
                        lines.append("| Item |")
                        lines.append("|------|")
                        for item in content:
                            lines.append(f"| {item} |")
                else:
                    lines.append(str(content))
            else:
                lines.append(str(content))

            lines.append("")

        # Footer
        lines.append("---")
        lines.append("")
        lines.append("*Report generated by YaFT (Yet Another Forensic Tool)*")
        lines.append("")

        # Write report
        report_content = "\n".join(lines)
        self.write_file(report_path, report_content)

        self.log_info(f"Report generated: {report_path}")

        # Track generated report
        self._generated_reports.append(report_path)

        # Generate PDF if enabled
        if self._enable_pdf_export:
            try:
                pdf_path = self.convert_markdown_to_pdf(report_path)
                self.log_info(f"PDF export: {pdf_path}")
            except ImportError:
                self.log_warning(
                    "PDF export is enabled but required packages are not installed. "
                    "Install with: uv pip install markdown weasyprint"
                )
            except Exception as e:
                self.log_warning(f"Failed to generate PDF: {e}")

        return report_path

    def save_report_attachment(
        self,
        report_dir: Path,
        filename: str,
        content: str | bytes,
    ) -> Path:
        """
        Save an attachment file alongside a report.

        Args:
            report_dir: Directory where the report is saved
            filename: Name of the attachment file
            content: Content to save (text or binary)

        Returns:
            Path: Path to saved attachment

        Raises:
            IOError: If file cannot be written
        """
        attachments_dir = report_dir / "attachments"
        attachments_dir.mkdir(parents=True, exist_ok=True)

        attachment_path = attachments_dir / filename

        try:
            if isinstance(content, bytes):
                attachment_path.write_bytes(content)
            else:
                attachment_path.write_text(content, encoding="utf-8")

            self.log_info(f"Attachment saved: {attachment_path}")
            return attachment_path
        except Exception as e:
            self.log_error(f"Failed to save attachment {filename}: {e}")
            raise

    def export_all_reports_to_pdf(self) -> list[Path]:
        """
        Export all generated markdown reports from the current session to PDF format.

        This method processes all reports tracked during the current session and
        generates corresponding PDF files. Useful for batch conversion at the end
        of a forensic analysis workflow.

        Returns:
            list[Path]: List of paths to generated PDF files

        Raises:
            ImportError: If weasyprint is not installed
        """
        if not self._generated_reports:
            self.log_info("No reports to export to PDF")
            return []

        self.log_info(f"Exporting {len(self._generated_reports)} reports to PDF...")

        pdf_paths: list[Path] = []
        success_count = 0
        failed_count = 0

        for md_path in self._generated_reports:
            if not md_path.exists():
                self.log_warning(f"Markdown file not found, skipping: {md_path}")
                failed_count += 1
                continue

            try:
                pdf_path = self.convert_markdown_to_pdf(md_path)
                pdf_paths.append(pdf_path)
                success_count += 1
            except ImportError as e:
                # Re-raise ImportError since user needs to install dependencies
                raise
            except Exception as e:
                self.log_error(f"Failed to export {md_path.name} to PDF: {e}")
                failed_count += 1

        # Summary
        self.log_info(
            f"PDF export complete: {success_count} successful, {failed_count} failed"
        )

        return pdf_paths

    def load_plugin_profile(self, profile_path: Path) -> PluginProfile:
        """
        Load and parse a plugin profile from a TOML file.

        Args:
            profile_path: Path to the TOML profile file

        Returns:
            PluginProfile: Parsed and validated profile

        Raises:
            FileNotFoundError: If profile file does not exist
            ValueError: If profile is invalid or cannot be parsed
        """
        if not profile_path.exists():
            raise FileNotFoundError(f"Profile file not found: {profile_path}")

        if not profile_path.is_file():
            raise ValueError(f"Profile path is not a file: {profile_path}")

        try:
            # Read and parse TOML file
            with open(profile_path, "r", encoding="utf-8") as f:
                profile_data = toml.load(f)

            # Validate required 'profile' section
            if "profile" not in profile_data:
                raise ValueError("Profile file must contain a [profile] section")

            profile_config = profile_data["profile"]

            # Create and validate PluginProfile
            profile = PluginProfile(**profile_config)

            self.log_info(f"Loaded profile '{profile.name}' with {len(profile.plugins)} plugins")
            return profile

        except toml.TomlDecodeError as e:
            raise ValueError(f"Invalid TOML syntax in profile file: {e}") from e
        except Exception as e:
            raise ValueError(f"Failed to parse profile file: {e}") from e

    # ========================================================================
    # Plugin Update System
    # ========================================================================

    def get_plugin_updater(
        self,
        repo: str = "RedRockerSE/yaft2",
        branch: str = "main",
        plugins_dir: Path | None = None,
    ) -> Any:
        """
        Get a PluginUpdater instance for managing plugin updates.

        Args:
            repo: GitHub repository (owner/repo format)
            branch: Git branch to use
            plugins_dir: Custom plugins directory (default: plugins/)

        Returns:
            PluginUpdater instance

        Example:
            updater = self.core_api.get_plugin_updater()
            result = updater.check_for_updates()
            if result.updates_available:
                updater.download_plugins()
        """
        from yaft.core.plugin_updater import PluginUpdater

        if plugins_dir is None:
            plugins_dir = Path("plugins")

        return PluginUpdater(
            repo=repo,
            branch=branch,
            plugins_dir=plugins_dir,
            cache_dir=Path(".plugin_cache"),
        )
