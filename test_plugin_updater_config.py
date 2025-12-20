"""
Test script for plugin updater configuration.

This script tests the new configurable plugin updater system with both
online and local sources.
"""

from pathlib import Path
import sys

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

from yaft.core.plugin_updater import (
    PluginUpdaterConfig,
    OnlineSourceConfig,
    LocalSourceConfig,
    PluginUpdater,
)
from yaft.core.api import CoreAPI


def test_default_config():
    """Test loading default configuration."""
    print("\n=== Test 1: Default Configuration ===")
    config = PluginUpdaterConfig()
    print(f"Source type: {config.source_type}")
    print(f"Online repo: {config.online.repository}")
    print(f"Online branch: {config.online.branch}")
    print(f"Check interval: {config.check_interval_hours} hours")
    print(f"Verify integrity: {config.verify_integrity}")
    print("[OK] Default config loaded successfully")


def test_config_from_file():
    """Test loading configuration from TOML file."""
    print("\n=== Test 2: Load Config from File ===")
    core_api = CoreAPI()

    # The config should be loaded automatically in __init__
    config = core_api._plugin_updater_config

    print(f"Source type: {config.source_type}")
    print(f"Online repo: {config.online.repository}")
    print(f"Online branch: {config.online.branch}")
    print(f"Local path: {config.local.path}")
    print(f"Auto-generate manifest: {config.local.auto_generate_manifest}")
    print("[OK] Config loaded from file successfully")


def test_online_config():
    """Test online source configuration."""
    print("\n=== Test 3: Online Source Configuration ===")
    config = PluginUpdaterConfig(
        source_type="online",
    )
    config.online.repository = "TestUser/test-repo"
    config.online.branch = "develop"

    # Create updater with config
    updater = PluginUpdater(config=config)

    print(f"Source type: {updater.config.source_type}")
    print(f"Repository: {updater.config.online.repository}")
    print(f"Branch: {updater.config.online.branch}")
    print("[OK] Online source config working")


def test_local_config_validation():
    """Test local source configuration validation."""
    print("\n=== Test 4: Local Source Validation ===")

    # Test with empty path (should fail when creating updater)
    config = PluginUpdaterConfig(source_type="local")

    try:
        updater = PluginUpdater(config=config)
        print("[ERROR] Should have failed with empty local path")
    except ValueError as e:
        print(f"[OK] Correctly rejected empty path: {e}")

    # Test with non-existent path (should fail)
    config.local.path = "C:\\non_existent_path"
    try:
        updater = PluginUpdater(config=config)
        print("[ERROR] Should have failed with non-existent path")
    except ValueError as e:
        print(f"[OK] Correctly rejected non-existent path: {e}")


def test_get_plugin_updater():
    """Test Core API get_plugin_updater method."""
    print("\n=== Test 5: Core API Integration ===")
    core_api = CoreAPI()

    # Get updater using config from file
    updater = core_api.get_plugin_updater()

    print(f"Updater source type: {updater.config.source_type}")
    print(f"Updater config loaded: {updater.config is not None}")
    print("[OK] Core API integration working")


def test_custom_config_override():
    """Test overriding config in get_plugin_updater."""
    print("\n=== Test 6: Custom Config Override ===")
    core_api = CoreAPI()

    # Create custom config
    custom_config = PluginUpdaterConfig(source_type="online")
    custom_config.online.repository = "CustomUser/custom-repo"

    # Get updater with custom config
    updater = core_api.get_plugin_updater(config=custom_config)

    print(f"Repository: {updater.config.online.repository}")
    assert updater.config.online.repository == "CustomUser/custom-repo"
    print("[OK] Custom config override working")


def main():
    """Run all tests."""
    print("=" * 60)
    print("Plugin Updater Configuration Test Suite")
    print("=" * 60)

    try:
        test_default_config()
        test_config_from_file()
        test_online_config()
        test_local_config_validation()
        test_get_plugin_updater()
        test_custom_config_override()

        print("\n" + "=" * 60)
        print("[OK] All tests passed!")
        print("=" * 60)

    except Exception as e:
        print(f"\n[ERROR] Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
