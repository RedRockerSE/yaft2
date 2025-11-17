"""
Generate plugins_manifest.json from plugins directory.

This script scans the plugins/ directory and generates a manifest file
containing metadata and SHA256 hashes for all plugin files.

Usage:
    python scripts/generate_manifest.py
"""

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


def calculate_sha256(file_path: Path) -> str:
    """Calculate SHA256 hash of a file."""
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()


def extract_plugin_metadata(file_path: Path) -> Dict[str, Any]:
    """Extract plugin metadata from Python file."""
    content = file_path.read_text(encoding="utf-8")

    # Extract class name
    class_match = re.search(r'class\s+(\w+)\s*\(.*PluginBase.*\)', content)
    class_name = class_match.group(1) if class_match else file_path.stem

    # Extract version from metadata
    version_match = re.search(r'version\s*=\s*["\']([^"\']+)["\']', content)
    version = version_match.group(1) if version_match else "1.0.0"

    # Extract description
    desc_match = re.search(r'description\s*=\s*["\']([^"\']+)["\']', content)
    description = desc_match.group(1) if desc_match else ""

    # Extract target OS
    target_os = []
    if 'target_os' in content:
        ios_match = re.search(r'["\']ios["\']', content)
        android_match = re.search(r'["\']android["\']', content)
        if ios_match:
            target_os.append("ios")
        if android_match:
            target_os.append("android")

    # Determine if plugin is required (production plugins)
    required = any([
        "ios_device_info" in file_path.name,
        "android_device_info" in file_path.name,
        "ios_call_log" in file_path.name,
        "android_call_log" in file_path.name,
        "ios_app_permissions" in file_path.name,
        "android_app_permissions" in file_path.name,
        "android_app_info" in file_path.name,
        "ios_app_guid" in file_path.name,
        "ios_cellular_info" in file_path.name,
    ])

    return {
        "name": class_name,
        "version": version,
        "description": description,
        "target_os": target_os,
        "required": required,
    }


def generate_manifest(
    plugins_dir: Path,
    output_path: Path,
    repository: str = "RedRockerSE/yaft2",
    branch: str = "main",
) -> None:
    """Generate plugins manifest file."""

    if not plugins_dir.exists():
        print(f"Error: Plugins directory not found: {plugins_dir}")
        return

    # Scan for Python plugin files
    plugin_files = sorted(plugins_dir.glob("*.py"))

    # Exclude __init__.py and __pycache__
    plugin_files = [
        f for f in plugin_files
        if f.name != "__init__.py" and not f.name.startswith("_")
    ]

    plugins = []

    for plugin_file in plugin_files:
        print(f"Processing: {plugin_file.name}")

        # Extract metadata
        metadata = extract_plugin_metadata(plugin_file)

        # Calculate hash
        sha256 = calculate_sha256(plugin_file)

        # Get file size
        size = plugin_file.stat().st_size

        # Build plugin entry
        plugin_entry = {
            "name": metadata["name"],
            "filename": plugin_file.name,
            "version": metadata["version"],
            "description": metadata["description"],
            "sha256": sha256,
            "size": size,
            "required": metadata["required"],
            "os_target": metadata["target_os"] if metadata["target_os"] else None,
            "dependencies": [],
        }

        plugins.append(plugin_entry)

    # Build manifest
    manifest = {
        "manifest_version": "1.0.0",
        "last_updated": datetime.now(timezone.utc).isoformat(),
        "repository": repository,
        "branch": branch,
        "plugins": plugins,
    }

    # Write manifest file
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)

    print(f"\n[OK] Manifest generated: {output_path}")
    print(f"[OK] Total plugins: {len(plugins)}")
    print(f"[OK] Required plugins: {sum(1 for p in plugins if p['required'])}")


def main():
    """Main entry point."""
    # Determine paths
    script_dir = Path(__file__).parent
    repo_root = script_dir.parent
    plugins_dir = repo_root / "plugins"
    output_path = repo_root / "plugins_manifest.json"

    print("=" * 60)
    print("YAFT Plugin Manifest Generator")
    print("=" * 60)
    print()

    generate_manifest(
        plugins_dir=plugins_dir,
        output_path=output_path,
        repository="RedRockerSE/yaft2",
        branch="main",
    )

    print()
    print("=" * 60)
    print("Done!")
    print("=" * 60)


if __name__ == "__main__":
    main()
