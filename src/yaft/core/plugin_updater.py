"""
Plugin Update System for YAFT.

This module handles automatic plugin updates from the GitHub repository using a
manifest-based approach. It checks for updates, downloads missing plugins, and
verifies integrity using SHA256 hashes.

Design: Option 3 - Hybrid Approach with Manifest
- Uses manifest file (plugins_manifest.json) to track plugin metadata
- Checks GitHub Contents API for manifest updates (minimal API calls)
- Downloads plugins via raw URLs (no rate limits)
- SHA256 verification for security
- Offline-friendly with caching

Author: YAFT Development Team
Version: 1.0.0
Date: 2025-01-17
"""

import hashlib
import json
import logging
import shutil
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import quote

import requests
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class PluginManifestEntry(BaseModel):
    """Represents a single plugin entry in the manifest."""

    name: str = Field(..., description="Plugin class name")
    filename: str = Field(..., description="Plugin filename")
    version: str = Field(..., description="Plugin version")
    description: str = Field(default="", description="Plugin description")
    sha256: str = Field(..., description="SHA256 hash of plugin file")
    size: int = Field(..., description="File size in bytes")
    required: bool = Field(default=False, description="Whether plugin is required")
    os_target: Optional[List[str]] = Field(None, description="Target OS (ios, android)")
    dependencies: List[str] = Field(default_factory=list, description="Plugin dependencies")


class PluginManifest(BaseModel):
    """Represents the plugin manifest file structure."""

    manifest_version: str = Field(..., description="Manifest format version")
    last_updated: str = Field(..., description="Last update timestamp (ISO 8601)")
    repository: str = Field(..., description="GitHub repository (owner/repo)")
    branch: str = Field(..., description="Git branch")
    plugins: List[PluginManifestEntry] = Field(..., description="List of plugin entries")


class UpdateCheckResult(BaseModel):
    """Result of checking for plugin updates."""

    updates_available: bool = Field(..., description="Whether updates are available")
    new_plugins: List[str] = Field(default_factory=list, description="New plugins to download")
    updated_plugins: List[str] = Field(default_factory=list, description="Plugins with updates")
    total_plugins: int = Field(default=0, description="Total plugins in remote manifest")
    manifest_changed: bool = Field(default=False, description="Whether manifest has changed")
    error: Optional[str] = Field(None, description="Error message if check failed")


class DownloadResult(BaseModel):
    """Result of downloading plugins."""

    success: bool = Field(..., description="Whether download was successful")
    downloaded: List[str] = Field(default_factory=list, description="Successfully downloaded plugins")
    failed: List[str] = Field(default_factory=list, description="Failed downloads")
    verified: List[str] = Field(default_factory=list, description="Plugins that passed verification")
    errors: List[str] = Field(default_factory=list, description="Error messages")


class PluginUpdater:
    """
    Handles plugin updates from GitHub repository.

    This class implements the hybrid manifest-based update system:
    1. Checks if local manifest is outdated
    2. Downloads new manifest if changed
    3. Compares local vs remote plugins
    4. Downloads missing/updated plugins
    5. Verifies downloads with SHA256 hashes
    """

    def __init__(
        self,
        repo: str = "RedRockerSE/yaft",
        branch: str = "main",
        plugins_dir: Path | None = None,
        cache_dir: Path | None = None,
        timeout: int = 30,
    ) -> None:
        """
        Initialize the plugin updater.

        Args:
            repo: GitHub repository in format "owner/repo"
            branch: Git branch to use
            plugins_dir: Local plugins directory (default: plugins/)
            cache_dir: Cache directory for manifest (default: .plugin_cache/)
            timeout: Request timeout in seconds
        """
        self.repo = repo
        self.branch = branch
        self.plugins_dir = plugins_dir or Path("plugins")
        self.cache_dir = cache_dir or Path(".plugin_cache")
        self.timeout = timeout

        # Ensure directories exist
        self.plugins_dir.mkdir(parents=True, exist_ok=True)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        # Cache file paths
        self.cached_manifest_path = self.cache_dir / "manifest.json"
        self.last_check_path = self.cache_dir / "last_check.txt"

        # GitHub API and raw URLs
        self.api_base = "https://api.github.com"
        self.raw_base = "https://raw.githubusercontent.com"

    def check_for_updates(
        self,
        force: bool = False,
        check_interval_hours: int = 24,
    ) -> UpdateCheckResult:
        """
        Check if plugin updates are available.

        Args:
            force: Force check even if cache is recent
            check_interval_hours: Hours between checks (default: 24)

        Returns:
            UpdateCheckResult with update information
        """
        logger.info("Checking for plugin updates...")

        # Check if we should skip based on last check time
        if not force and self._should_skip_check(check_interval_hours):
            logger.info(f"Skipping check (last check within {check_interval_hours} hours)")
            return UpdateCheckResult(
                updates_available=False,
                manifest_changed=False,
                error=None,
            )

        try:
            # Download remote manifest
            remote_manifest = self._fetch_remote_manifest()

            # Load local manifest (if exists)
            local_manifest = self._load_local_manifest()

            # Check if manifest changed
            manifest_changed = self._has_manifest_changed(local_manifest, remote_manifest)

            if not manifest_changed and not force:
                logger.info("No manifest changes detected")
                self._update_last_check_time()
                return UpdateCheckResult(
                    updates_available=False,
                    manifest_changed=False,
                    total_plugins=len(remote_manifest.plugins),
                    error=None,
                )

            # Compare local vs remote plugins
            new_plugins, updated_plugins = self._compare_plugins(
                local_manifest, remote_manifest
            )

            # Cache the remote manifest
            self._cache_manifest(remote_manifest)
            self._update_last_check_time()

            updates_available = len(new_plugins) > 0 or len(updated_plugins) > 0

            logger.info(
                f"Update check complete: {len(new_plugins)} new, "
                f"{len(updated_plugins)} updated"
            )

            return UpdateCheckResult(
                updates_available=updates_available,
                new_plugins=new_plugins,
                updated_plugins=updated_plugins,
                total_plugins=len(remote_manifest.plugins),
                manifest_changed=manifest_changed,
                error=None,
            )

        except Exception as e:
            error_msg = f"Failed to check for updates: {str(e)}"
            logger.error(error_msg)
            return UpdateCheckResult(
                updates_available=False,
                error=error_msg,
            )

    def download_plugins(
        self,
        plugin_list: List[str] | None = None,
        verify: bool = True,
        backup: bool = True,
    ) -> DownloadResult:
        """
        Download specified plugins from GitHub.

        Args:
            plugin_list: List of plugin filenames to download (None = all from manifest)
            verify: Verify SHA256 hashes after download
            backup: Create backup of existing plugins before overwriting

        Returns:
            DownloadResult with download status
        """
        logger.info("Starting plugin download...")

        # Load cached manifest
        manifest = self._load_cached_manifest()
        if not manifest:
            return DownloadResult(
                success=False,
                errors=["No cached manifest found. Run check_for_updates() first."],
            )

        # Determine which plugins to download
        if plugin_list is None:
            plugins_to_download = manifest.plugins
        else:
            plugins_to_download = [
                p for p in manifest.plugins if p.filename in plugin_list
            ]

        if not plugins_to_download:
            return DownloadResult(
                success=True,
                errors=["No plugins to download"],
            )

        downloaded = []
        failed = []
        verified = []
        errors = []

        for plugin in plugins_to_download:
            try:
                logger.info(f"Downloading {plugin.filename}...")

                # Backup existing file if requested
                local_path = self.plugins_dir / plugin.filename
                if backup and local_path.exists():
                    backup_path = local_path.with_suffix(f".bak.{int(datetime.now().timestamp())}")
                    shutil.copy2(local_path, backup_path)
                    logger.debug(f"Backed up to {backup_path}")

                # Download plugin
                content = self._download_plugin_file(plugin.filename)

                # Verify SHA256 if requested
                if verify:
                    calculated_hash = self._calculate_sha256(content)
                    if calculated_hash != plugin.sha256:
                        error_msg = (
                            f"SHA256 mismatch for {plugin.filename}: "
                            f"expected {plugin.sha256}, got {calculated_hash}"
                        )
                        logger.error(error_msg)
                        errors.append(error_msg)
                        failed.append(plugin.filename)
                        continue

                    verified.append(plugin.filename)
                    logger.debug(f"SHA256 verified for {plugin.filename}")

                # Write to file
                local_path.write_bytes(content)
                downloaded.append(plugin.filename)
                logger.info(f"Downloaded {plugin.filename} ({plugin.size} bytes)")

            except Exception as e:
                error_msg = f"Failed to download {plugin.filename}: {str(e)}"
                logger.error(error_msg)
                errors.append(error_msg)
                failed.append(plugin.filename)

        success = len(failed) == 0
        logger.info(
            f"Download complete: {len(downloaded)} succeeded, {len(failed)} failed"
        )

        return DownloadResult(
            success=success,
            downloaded=downloaded,
            failed=failed,
            verified=verified,
            errors=errors,
        )

    def update_all_plugins(
        self,
        force: bool = False,
        auto_download: bool = True,
    ) -> Dict[str, Any]:
        """
        Check and update all plugins.

        Args:
            force: Force update check
            auto_download: Automatically download updates without prompting

        Returns:
            Dict with update results
        """
        # Check for updates
        check_result = self.check_for_updates(force=force)

        if check_result.error:
            return {"success": False, "error": check_result.error}

        if not check_result.updates_available:
            return {
                "success": True,
                "message": "All plugins up to date",
                "total_plugins": check_result.total_plugins,
            }

        # Download updates
        plugins_to_download = check_result.new_plugins + check_result.updated_plugins

        if not auto_download:
            return {
                "success": True,
                "updates_available": True,
                "new_plugins": check_result.new_plugins,
                "updated_plugins": check_result.updated_plugins,
                "message": "Updates available, run download_plugins() to install",
            }

        download_result = self.download_plugins(plugin_list=plugins_to_download)

        return {
            "success": download_result.success,
            "downloaded": download_result.downloaded,
            "failed": download_result.failed,
            "verified": download_result.verified,
            "errors": download_result.errors,
        }

    def list_available_plugins(self) -> List[Dict[str, Any]]:
        """
        List all available plugins from cached manifest.

        Returns:
            List of plugin information dictionaries
        """
        manifest = self._load_cached_manifest()
        if not manifest:
            logger.warning("No cached manifest found")
            return []

        return [
            {
                "name": p.name,
                "filename": p.filename,
                "version": p.version,
                "description": p.description,
                "size": p.size,
                "required": p.required,
                "os_target": p.os_target,
            }
            for p in manifest.plugins
        ]

    # Private helper methods

    def _fetch_remote_manifest(self) -> PluginManifest:
        """Fetch manifest from GitHub."""
        url = f"{self.raw_base}/{self.repo}/{self.branch}/plugins_manifest.json"
        logger.debug(f"Fetching manifest from {url}")

        response = requests.get(url, timeout=self.timeout)
        response.raise_for_status()

        manifest_data = response.json()
        return PluginManifest(**manifest_data)

    def _download_plugin_file(self, filename: str) -> bytes:
        """Download a single plugin file."""
        # URL encode the filename
        encoded_filename = quote(filename)
        url = f"{self.raw_base}/{self.repo}/{self.branch}/plugins/{encoded_filename}"
        logger.debug(f"Downloading from {url}")

        response = requests.get(url, timeout=self.timeout)
        response.raise_for_status()

        return response.content

    def _load_local_manifest(self) -> Optional[PluginManifest]:
        """Load manifest from local plugins directory (generated on-the-fly)."""
        # This scans local plugins and creates a manifest structure
        # Used for comparison with remote manifest
        plugin_files = list(self.plugins_dir.glob("*.py"))
        plugin_files = [
            f for f in plugin_files
            if f.name != "__init__.py" and not f.name.startswith("_")
        ]

        if not plugin_files:
            return None

        entries = []
        for plugin_file in plugin_files:
            sha256 = self._calculate_sha256_file(plugin_file)
            size = plugin_file.stat().st_size

            entries.append(
                PluginManifestEntry(
                    name=plugin_file.stem,
                    filename=plugin_file.name,
                    version="unknown",
                    sha256=sha256,
                    size=size,
                    required=False,
                    os_target=None,
                )
            )

        return PluginManifest(
            manifest_version="1.0.0",
            last_updated=datetime.now(timezone.utc).isoformat(),
            repository=self.repo,
            branch=self.branch,
            plugins=entries,
        )

    def _load_cached_manifest(self) -> Optional[PluginManifest]:
        """Load cached remote manifest."""
        if not self.cached_manifest_path.exists():
            return None

        try:
            manifest_data = json.loads(self.cached_manifest_path.read_text())
            return PluginManifest(**manifest_data)
        except Exception as e:
            logger.warning(f"Failed to load cached manifest: {e}")
            return None

    def _cache_manifest(self, manifest: PluginManifest) -> None:
        """Cache manifest to disk."""
        self.cached_manifest_path.write_text(
            manifest.model_dump_json(indent=2),
            encoding="utf-8",
        )
        logger.debug("Cached manifest to disk")

    def _has_manifest_changed(
        self,
        local_manifest: Optional[PluginManifest],
        remote_manifest: PluginManifest,
    ) -> bool:
        """Check if remote manifest has changed compared to local."""
        if not local_manifest:
            return True

        # Compare last_updated timestamps
        return local_manifest.last_updated != remote_manifest.last_updated

    def _compare_plugins(
        self,
        local_manifest: Optional[PluginManifest],
        remote_manifest: PluginManifest,
    ) -> tuple[List[str], List[str]]:
        """
        Compare local and remote plugins to find new and updated ones.

        Returns:
            Tuple of (new_plugins, updated_plugins) - lists of filenames
        """
        if not local_manifest:
            # All remote plugins are new
            return [p.filename for p in remote_manifest.plugins], []

        # Build lookup maps
        local_map = {p.filename: p for p in local_manifest.plugins}
        remote_map = {p.filename: p for p in remote_manifest.plugins}

        new_plugins = []
        updated_plugins = []

        for filename, remote_plugin in remote_map.items():
            if filename not in local_map:
                # New plugin
                new_plugins.append(filename)
            else:
                # Check if updated (SHA256 changed)
                local_plugin = local_map[filename]
                if local_plugin.sha256 != remote_plugin.sha256:
                    updated_plugins.append(filename)

        return new_plugins, updated_plugins

    def _should_skip_check(self, check_interval_hours: int) -> bool:
        """Check if we should skip update check based on last check time."""
        if not self.last_check_path.exists():
            return False

        try:
            last_check_str = self.last_check_path.read_text().strip()
            last_check = datetime.fromisoformat(last_check_str)
            now = datetime.now(timezone.utc)
            elapsed = now - last_check

            return elapsed < timedelta(hours=check_interval_hours)
        except Exception:
            return False

    def _update_last_check_time(self) -> None:
        """Update last check timestamp."""
        now = datetime.now(timezone.utc).isoformat()
        self.last_check_path.write_text(now, encoding="utf-8")

    def _calculate_sha256(self, content: bytes) -> str:
        """Calculate SHA256 hash of content."""
        return hashlib.sha256(content).hexdigest()

    def _calculate_sha256_file(self, file_path: Path) -> str:
        """Calculate SHA256 hash of a file."""
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()
