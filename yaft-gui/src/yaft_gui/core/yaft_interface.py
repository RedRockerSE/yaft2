"""Interface module for communicating with YAFT executable."""

import re
import subprocess
from pathlib import Path
from typing import List, Dict, Optional


class YAFTInterface:
    """Interface to YAFT forensic analysis tool executable."""

    def __init__(self, yaft_exe_path: Optional[str] = None):
        """
        Initialize YAFT interface.

        Args:
            yaft_exe_path: Path to yaft executable. If None, searches in common locations.
        """
        self.yaft_exe = self._locate_yaft_exe(yaft_exe_path)

    def _locate_yaft_exe(self, provided_path: Optional[str]) -> Path:
        """
        Locate YAFT executable.

        Args:
            provided_path: User-provided path to executable

        Returns:
            Path to YAFT executable

        Raises:
            FileNotFoundError: If YAFT executable cannot be found
        """
        if provided_path:
            exe_path = Path(provided_path)
            if exe_path.exists():
                return exe_path

        # Search in common locations
        search_paths = [
            Path("yaft.exe"),  # Current directory
            Path("../yaft.exe"),  # Parent directory
            Path("../dist/yaft/yaft.exe"),  # Build output directory
            Path("yaft"),  # Linux executable
            Path("../yaft"),  # Parent directory (Linux)
            Path("../dist/yaft/yaft"),  # Build output (Linux)
        ]

        for path in search_paths:
            if path.exists():
                return path.resolve()

        raise FileNotFoundError(
            "YAFT executable not found. Please specify the path to yaft.exe"
        )

    def is_available(self) -> bool:
        """Check if YAFT executable is available and working."""
        try:
            result = subprocess.run(
                [str(self.yaft_exe), "--version"],
                capture_output=True,
                text=True,
                encoding="utf-8",
                timeout=5,
            )
            return result.returncode == 0
        except (subprocess.SubprocessError, FileNotFoundError):
            return False

    def get_available_plugins(self) -> List[Dict[str, str]]:
        """
        Query YAFT for available plugins.

        Returns:
            List of plugin dictionaries with 'name', 'version', and 'description' keys

        Raises:
            RuntimeError: If failed to query plugins
        """
        try:
            result = subprocess.run(
                [str(self.yaft_exe), "list-plugins"],
                capture_output=True,
                text=True,
                encoding="utf-8",
                timeout=10,
            )

            if result.returncode != 0:
                raise RuntimeError(f"Failed to query plugins: {result.stderr}")

            plugins = self._parse_plugin_list(result.stdout)
            return plugins

        except subprocess.SubprocessError as e:
            raise RuntimeError(f"Failed to execute YAFT: {e}")

    def _parse_plugin_list(self, output: str) -> List[Dict[str, str]]:
        """
        Parse plugin list output from YAFT.

        Expected format:
        PluginName (v1.0.0) - Description here
        AnotherPlugin (v2.1.0) - Another description

        Args:
            output: Raw output from 'yaft list-plugins' command

        Returns:
            List of plugin dictionaries
        """
        plugins = []

        # Pattern to match plugin output lines
        # Matches: PluginName (v1.0.0) - Description
        pattern = r"^([A-Za-z0-9_]+)\s+\(v([\d.]+)\)\s*-\s*(.+)$"

        for line in output.splitlines():
            line = line.strip()
            if not line or line.startswith("Available plugins:") or line.startswith("---"):
                continue

            match = re.match(pattern, line)
            if match:
                plugins.append(
                    {
                        "name": match.group(1),
                        "version": match.group(2),
                        "description": match.group(3),
                    }
                )

        return plugins

    def build_command(
        self,
        zip_file: str,
        plugins: Optional[List[str]] = None,
        profile: Optional[str] = None,
        html_export: bool = False,
        pdf_export: bool = False,
        examiner_id: Optional[str] = None,
        case_id: Optional[str] = None,
        evidence_id: Optional[str] = None,
    ) -> List[str]:
        """
        Build YAFT command-line arguments.

        Args:
            zip_file: Path to ZIP extraction file
            plugins: List of plugin names to execute (mutually exclusive with profile)
            profile: Path to profile TOML file (mutually exclusive with plugins)
            html_export: Enable HTML export
            pdf_export: Enable PDF export
            examiner_id: Forensic examiner ID
            case_id: Forensic case ID
            evidence_id: Evidence ID

        Returns:
            Complete command as list of strings

        Raises:
            ValueError: If both plugins and profile are specified, or neither is specified
        """
        if plugins and profile:
            raise ValueError("Cannot specify both plugins and profile")

        if not plugins and not profile:
            raise ValueError("Must specify either plugins or profile")

        cmd = [str(self.yaft_exe), "run", "--zip", zip_file]

        # Add profile or individual plugins
        if profile:
            cmd.extend(["--profile", profile])
        elif plugins:
            for plugin in plugins:
                cmd.append(plugin)

        # Add export options
        if html_export:
            cmd.append("--html")

        if pdf_export:
            cmd.append("--pdf")

        # Add case identifiers if provided
        if examiner_id:
            cmd.extend(["--examiner-id", examiner_id])

        if case_id:
            cmd.extend(["--case-id", case_id])

        if evidence_id:
            cmd.extend(["--evidence-id", evidence_id])

        return cmd

    def validate_zip_file(self, zip_path: str) -> bool:
        """
        Validate that the specified file is a valid ZIP archive.

        Args:
            zip_path: Path to ZIP file

        Returns:
            True if valid ZIP file, False otherwise
        """
        path = Path(zip_path)
        if not path.exists():
            return False

        if not path.is_file():
            return False

        # Check file extension
        if path.suffix.lower() != ".zip":
            return False

        # TODO: Could add more validation (check ZIP magic bytes, etc.)
        return True

    def get_version(self) -> str:
        """
        Get YAFT version string.

        Returns:
            Version string (e.g., "0.3.5")

        Raises:
            RuntimeError: If failed to get version
        """
        try:
            result = subprocess.run(
                [str(self.yaft_exe), "--version"],
                capture_output=True,
                text=True,
                encoding="utf-8",
                timeout=5,
            )

            if result.returncode != 0:
                raise RuntimeError("Failed to get YAFT version")

            # Parse version from output
            # Expected format: "YAFT version 0.3.5" or similar
            version_match = re.search(r"(\d+\.\d+\.\d+)", result.stdout)
            if version_match:
                return version_match.group(1)

            return result.stdout.strip()

        except subprocess.SubprocessError as e:
            raise RuntimeError(f"Failed to execute YAFT: {e}")
