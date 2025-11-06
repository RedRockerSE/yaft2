"""
Core API that provides shared functionality to plugins.

This module exposes common services and utilities that plugins can use.
"""

import logging
import plistlib
import sqlite3
import tempfile
import zipfile
from pathlib import Path
from typing import Any

from rich.console import Console
from rich.logging import RichHandler
from rich.table import Table


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

        # Case identifiers for forensic analysis
        self._u_nummer: str | None = None
        self._k_nummer: str | None = None
        self._bg_nummer: str | None = None

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

    def validate_u_nummer(self, value: str) -> bool:
        """
        Validate U-nummer format: u0000000 (7 digits).

        Args:
            value: U-nummer to validate

        Returns:
            bool: True if valid, False otherwise
        """
        import re
        return bool(re.match(r'^u\d{7}$', value, re.IGNORECASE))

    def validate_k_nummer(self, value: str) -> bool:
        """
        Validate K-nummer format: K0000000-00 (8 digits, dash, 2 digits).

        Args:
            value: K-nummer to validate

        Returns:
            bool: True if valid, False otherwise
        """
        import re
        return bool(re.match(r'^K\d{7}-\d{2}$', value, re.IGNORECASE))

    def validate_bg_nummer(self, value: str) -> bool:
        """
        Validate BG-nummer format: BG000000-0 (6 digits, dash, 1 digit).

        Args:
            value: BG-nummer to validate

        Returns:
            bool: True if valid, False otherwise
        """
        import re
        return bool(re.match(r'^BG\d{6}-\d$', value, re.IGNORECASE))

    def prompt_for_case_identifiers(self) -> tuple[str, str, str]:
        """
        Prompt user for case identifiers with validation.

        Returns:
            tuple[str, str, str]: (u_nummer, k_nummer, bg_nummer)

        Raises:
            ValueError: If user cancels input (Ctrl+C)
        """
        self.console.print("\n[bold cyan]Case Information Required[/bold cyan]")
        self.console.print("Please enter the following case identifiers:\n")

        # Prompt for U-nummer
        while True:
            u_nummer = self.console.input("[bold cyan]?[/bold cyan] U-nummer (format: u0000000): ").strip()
            if self.validate_u_nummer(u_nummer):
                u_nummer = u_nummer.lower()  # Normalize to lowercase
                break
            self.console.print("[bold red]✗[/bold red] Invalid format. Expected: u followed by 7 digits (e.g., u1234567)")

        # Prompt for K-nummer
        while True:
            k_nummer = self.console.input("[bold cyan]?[/bold cyan] K-nummer (format: K0000000-00): ").strip()
            if self.validate_k_nummer(k_nummer):
                k_nummer = k_nummer.upper()  # Normalize to uppercase
                break
            self.console.print("[bold red]✗[/bold red] Invalid format. Expected: K followed by 7 digits, dash, 2 digits (e.g., K1234567-01)")

        # Prompt for BG-nummer
        while True:
            bg_nummer = self.console.input("[bold cyan]?[/bold cyan] BG-nummer (format: BG000000-0): ").strip()
            if self.validate_bg_nummer(bg_nummer):
                bg_nummer = bg_nummer.upper()  # Normalize to uppercase
                break
            self.console.print("[bold red]✗[/bold red] Invalid format. Expected: BG followed by 6 digits, dash, 1 digit (e.g., BG123456-1)")

        # Store identifiers
        self._u_nummer = u_nummer
        self._k_nummer = k_nummer
        self._bg_nummer = bg_nummer

        self.console.print(f"\n[bold green]✓[/bold green] Case identifiers set:")
        self.console.print(f"  U-nummer:  {u_nummer}")
        self.console.print(f"  K-nummer:  {k_nummer}")
        self.console.print(f"  BG-nummer: {bg_nummer}\n")

        return u_nummer, k_nummer, bg_nummer

    def get_case_identifiers(self) -> tuple[str | None, str | None, str | None]:
        """
        Get stored case identifiers.

        Returns:
            tuple[str | None, str | None, str | None]: (u_nummer, k_nummer, bg_nummer)
        """
        return self._u_nummer, self._k_nummer, self._bg_nummer

    def set_case_identifiers(self, u_nummer: str, k_nummer: str, bg_nummer: str) -> None:
        """
        Set case identifiers programmatically (for testing).

        Args:
            u_nummer: U-nummer
            k_nummer: K-nummer
            bg_nummer: BG-nummer

        Raises:
            ValueError: If any identifier has invalid format
        """
        if not self.validate_u_nummer(u_nummer):
            raise ValueError(f"Invalid U-nummer format: {u_nummer}")
        if not self.validate_k_nummer(k_nummer):
            raise ValueError(f"Invalid K-nummer format: {k_nummer}")
        if not self.validate_bg_nummer(bg_nummer):
            raise ValueError(f"Invalid BG-nummer format: {bg_nummer}")

        self._u_nummer = u_nummer.lower()
        self._k_nummer = k_nummer.upper()
        self._bg_nummer = bg_nummer.upper()

    def get_case_output_dir(self, subdir: str = "") -> Path:
        """
        Get case-based output directory path.

        Args:
            subdir: Optional subdirectory name (e.g., "ios_extractions", "reports")

        Returns:
            Path: Output directory path (yaft_output/<K-nummer>/<BG-nummer>/<subdir>)
                  Falls back to yaft_output/<subdir> if case identifiers not set
        """
        base_dir = Path.cwd() / "yaft_output"

        if self._k_nummer and self._bg_nummer:
            if subdir:
                return base_dir / self._k_nummer / self._bg_nummer / subdir
            return base_dir / self._k_nummer / self._bg_nummer
        else:
            if subdir:
                return base_dir / subdir
            return base_dir

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
        for unit in ["B", "KB", "MB", "GB", "TB"]:
            if size < 1024.0:
                return f"{size:.2f} {unit}"
            size /= 1024.0
        return f"{size:.2f} PB"

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

    # ========== SQLite Database Methods ==========

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
            # Use case identifiers for path structure: yaft_output/<K-nummer>/<BG-nummer>/reports
            if self._k_nummer and self._bg_nummer:
                output_dir = Path.cwd() / "yaft_output" / self._k_nummer / self._bg_nummer / "reports"
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
        if self._u_nummer:
            lines.append(f"- **U-nummer**: {self._u_nummer}")
        if self._k_nummer:
            lines.append(f"- **K-nummer**: {self._k_nummer}")
        if self._bg_nummer:
            lines.append(f"- **BG-nummer**: {self._bg_nummer}")

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
