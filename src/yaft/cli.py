"""
CLI interface for YAFT application.

Provides command-line interface with color-coded output using Typer and Rich.
"""

from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.panel import Panel

from yaft import __version__
from yaft.core.api import CoreAPI
from yaft.core.plugin_manager import PluginManager

# Create Typer app
app = typer.Typer(
    name="yaft",
    help=(
        "YAFT - Yet Another Forensic Tool: "
        "A plugin-based forensic analysis tool for processing ZIP archives"
    ),
    add_completion=False,
)

# Global console for rich output
console = Console()

# Global instances (initialized on first command)
_core_api: CoreAPI | None = None
_plugin_manager: PluginManager | None = None


def get_core_api() -> CoreAPI:
    """Get or create CoreAPI instance."""
    global _core_api
    if _core_api is None:
        config_dir = Path.cwd() / "config"
        _core_api = CoreAPI(config_dir=config_dir)
    return _core_api


def get_plugin_manager() -> PluginManager:
    """Get or create PluginManager instance."""
    global _plugin_manager
    if _plugin_manager is None:
        core_api = get_core_api()
        plugin_dirs = [Path.cwd() / "plugins"]
        _plugin_manager = PluginManager(core_api=core_api, plugin_dirs=plugin_dirs)
    return _plugin_manager


@app.command()
def version() -> None:
    """Display version information."""
    console.print(Panel(
        f"[bold cyan]YAFT[/bold cyan] v{__version__}\n"
        f"Yet Another Forensic Tool\n"
        f"A plugin-based forensic analysis tool",
        title="Version Info",
        border_style="cyan",
    ))


@app.command()
def list_plugins(
    all: Annotated[
        bool, typer.Option("--all", "-a", help="Show all discovered plugins")
    ] = False,
    filter_os: Annotated[
        bool,
        typer.Option("--filter-os", "-f", help="Filter plugins by detected OS (requires ZIP)"),
    ] = False,
) -> None:
    """List available plugins."""
    plugin_manager = get_plugin_manager()

    # Discover plugins if not already done
    if not plugin_manager._plugin_classes:
        console.print("[yellow]Discovering plugins...[/yellow]")
        plugin_manager.discover_plugins()

    plugin_manager.list_plugins(show_all=all, filter_by_os=filter_os)

    # Show statistics
    stats = plugin_manager.get_plugin_count()
    console.print(f"\n[dim]Total discovered: {stats['total_discovered']} | "
                  f"Loaded: {stats['loaded']} | "
                  f"Active: {stats['active']} | "
                  f"Errors: {stats['error']}[/dim]")


@app.command()
def load(
    plugin_name: Annotated[str, typer.Argument(help="Name of the plugin to load")],
) -> None:
    """Load a specific plugin."""
    core_api = get_core_api()
    plugin_manager = get_plugin_manager()

    # Discover plugins if not already done
    if not plugin_manager._plugin_classes:
        core_api.print_info("Discovering plugins...")
        plugin_manager.discover_plugins()

    plugin = plugin_manager.load_plugin(plugin_name)
    if plugin:
        core_api.print_success(f"Plugin '{plugin.metadata.name}' loaded successfully")
    else:
        core_api.print_error(f"Failed to load plugin '{plugin_name}'")
        raise typer.Exit(code=1)


@app.command()
def unload(
    plugin_name: Annotated[str, typer.Argument(help="Name of the plugin to unload")],
) -> None:
    """Unload a specific plugin."""
    core_api = get_core_api()
    plugin_manager = get_plugin_manager()

    if plugin_manager.unload_plugin(plugin_name):
        core_api.print_success(f"Plugin '{plugin_name}' unloaded successfully")
    else:
        core_api.print_error(f"Failed to unload plugin '{plugin_name}'")
        raise typer.Exit(code=1)


@app.command()
def run(
    plugin_name: Annotated[
        str | None,
        typer.Argument(
            help="Name of the plugin to run (optional if using --plugins, --all, --os, or --profile)"
        ),
    ] = None,
    zip_file: Annotated[
        Path | None, typer.Option("--zip", "-z", help="ZIP file to analyze")
    ] = None,
    plugins: Annotated[
        str | None,
        typer.Option("--plugins", "-p", help="Comma-separated list of plugin names to run"),
    ] = None,
    profile: Annotated[
        Path | None,
        typer.Option("--profile", help="Path to TOML profile file specifying plugins to run"),
    ] = None,
    run_all: Annotated[
        bool,
        typer.Option("--all", help="Run all compatible plugins (filters by OS if ZIP provided)"),
    ] = False,
    os_filter: Annotated[
        str | None, typer.Option("--os", help="Run plugins for specific OS (ios/android)")
    ] = None,
    pdf_export: Annotated[
        bool,
        typer.Option("--pdf", help="Export all generated markdown reports to PDF format"),
    ] = False,
    html_export: Annotated[
        bool,
        typer.Option("--html", help="Export all generated markdown reports to HTML format"),
    ] = False,
    args: Annotated[
        list[str] | None, typer.Argument(help="Arguments to pass to the plugin(s)")
    ] = None,
) -> None:
    """Load and execute one or more plugins, optionally with a ZIP file for forensic analysis.

    Examples:
        # Run single plugin
        yaft run HelloWorldPlugin

        # Run multiple specific plugins
        yaft run --zip evidence.zip --plugins \\
            iOSAppGUIDExtractorPlugin,iOSAppPermissionsExtractorPlugin

        # Run plugins from profile file
        yaft run --zip evidence.zip --profile ios_analysis.toml

        # Run all compatible plugins (auto-detects OS from ZIP)
        yaft run --zip evidence.zip --all

        # Run all iOS plugins
        yaft run --zip evidence.zip --os ios

        # Run with PDF export enabled
        yaft run --zip evidence.zip --profile ios_full_analysis.toml --pdf

        # Run with HTML export enabled
        yaft run --zip evidence.zip --profile ios_full_analysis.toml --html

        # Run with both PDF and HTML export
        yaft run --zip evidence.zip --profile ios_full_analysis.toml --pdf --html
    """
    core_api = get_core_api()
    plugin_manager = get_plugin_manager()

    # Validate arguments
    mode_count = sum([bool(plugin_name), bool(plugins), bool(profile), run_all, bool(os_filter)])
    if mode_count == 0:
        core_api.print_error("Must specify plugin_name, --plugins, --profile, --all, or --os")
        raise typer.Exit(code=1)
    if mode_count > 1:
        core_api.print_error("Cannot combine plugin_name, --plugins, --profile, --all, and --os options")
        raise typer.Exit(code=1)
   

    # Enable PDF export if requested
    if pdf_export:
        core_api.enable_pdf_export(True)

    # Enable HTML export if requested
    if html_export:
        core_api.enable_html_export(True)

    # Load ZIP file if provided
    if zip_file:
        try:
            core_api.set_zip_file(zip_file)
            core_api.print_success(f"Loaded ZIP file: {zip_file.name}")

            # Detect OS
            extraction_info = core_api.get_extraction_info()
            os_type = extraction_info["os_type"]
            os_version = extraction_info["os_version"]
            if os_version:
                core_api.print_info(f"Detected OS: {os_type.upper()} {os_version}")
            else:
                core_api.print_info(f"Detected OS: {os_type.upper()}")
        except Exception as e:
            core_api.print_error(f"Failed to load ZIP file: {e}")
            raise typer.Exit(code=1) from e

    # Discover plugins if not already done
    if not plugin_manager._plugin_classes:
        core_api.print_info("Discovering plugins...")
        plugin_manager.discover_plugins()

    # Determine which plugins to run
    plugins_to_run = []
    profile_name = None

    if plugin_name:
        # Single plugin mode
        plugins_to_run = [plugin_name]
    elif plugins:
        # Multiple specific plugins mode
        plugins_to_run = [p.strip() for p in plugins.split(",")]
    elif profile:
        # Profile mode - load plugins from TOML file
        try:
            plugin_profile = core_api.load_plugin_profile(profile)
            plugins_to_run = plugin_profile.plugins
            profile_name = plugin_profile.name
            core_api.print_success(f"Loaded profile '{profile_name}'")
            if plugin_profile.description:
                core_api.print_info(f"Description: {plugin_profile.description}")
            core_api.print_info(f"Running {len(plugins_to_run)} plugins from profile")
        except FileNotFoundError as e:
            core_api.print_error(str(e))
            raise typer.Exit(code=1) from e
        except ValueError as e:
            core_api.print_error(f"Invalid profile: {e}")
            raise typer.Exit(code=1) from e
        except Exception as e:
            core_api.print_error(f"Failed to load profile: {e}")
            raise typer.Exit(code=1) from e
    elif run_all:
        # Run all compatible plugins
        if zip_file:
            compatible = plugin_manager.get_compatible_plugins()
            plugins_to_run = list(compatible.keys())
            core_api.print_info(f"Running {len(plugins_to_run)} compatible plugins")
        else:
            plugins_to_run = list(plugin_manager._plugin_classes.keys())
            core_api.print_info(f"Running all {len(plugins_to_run)} plugins")
    elif os_filter:
        # Run plugins for specific OS
        os_filter_lower = os_filter.lower()
        if os_filter_lower not in ["ios", "android"]:
            core_api.print_error("--os must be 'ios' or 'android'")
            raise typer.Exit(code=1)
        compatible = plugin_manager.get_compatible_plugins(os_filter_lower)
        plugins_to_run = list(compatible.keys())
        core_api.print_info(f"Running {len(plugins_to_run)} {os_filter_lower.upper()} plugins")

    if not plugins_to_run:
        core_api.print_error("No plugins to run")
        raise typer.Exit(code=1)

    # Prompt for case identifiers
    try:
        core_api.prompt_for_case_identifiers()
    except KeyboardInterrupt:
        core_api.print_error("\nCase identifier input cancelled")
        raise typer.Exit(code=1) from None
    except Exception as e:
        core_api.print_error(f"Failed to get case identifiers: {e}")
        raise typer.Exit(code=1) from e

    # Execute plugins
    success_count = 0
    failed_count = 0

    for idx, plugin_name_to_run in enumerate(plugins_to_run, 1):
        if len(plugins_to_run) > 1:
            console.print(
                f"\n[bold cyan]═══ Plugin {idx}/{len(plugins_to_run)}: "
                f"{plugin_name_to_run} ═══[/bold cyan]"
            )

        try:
            # Load plugin if not already loaded
            plugin = plugin_manager.get_plugin(plugin_name_to_run)
            if not plugin:
                core_api.print_info(f"Loading plugin '{plugin_name_to_run}'...")
                plugin = plugin_manager.load_plugin(plugin_name_to_run)
                if not plugin:
                    core_api.print_error(f"Failed to load plugin '{plugin_name_to_run}'")
                    failed_count += 1
                    continue

            # Execute plugin
            core_api.print_info(f"Executing plugin '{plugin.metadata.name}'...")
            result = plugin_manager.execute_plugin(plugin_name_to_run, *(args or []))

            if result is not None and len(plugins_to_run) == 1:
                console.print("\n[bold green]Plugin Result:[/bold green]")
                console.print(result)

            core_api.print_success(f"Plugin '{plugin.metadata.name}' executed successfully")
            success_count += 1

        except Exception as e:
            core_api.print_error(f"Plugin execution failed: {e}")
            failed_count += 1
            if len(plugins_to_run) == 1:
                raise typer.Exit(code=1) from e
            # Continue with next plugin in batch mode

    # Show summary for batch execution
    if len(plugins_to_run) > 1:
        console.print("\n[bold]Execution Summary:[/bold]")
        console.print(f"  Total: {len(plugins_to_run)}")
        console.print(f"  [green]Success: {success_count}[/green]")
        console.print(f"  [red]Failed: {failed_count}[/red]")

    # Export all reports to PDF if not already done (when --pdf flag is used)
    # Note: Individual PDFs are created automatically during report generation if PDF export is enabled
    # This is a fallback for batch conversion or if you want to ensure all reports are exported
    if pdf_export and not core_api.is_pdf_export_enabled():
        # Manual batch export (only if automatic export wasn't enabled)
        try:
            console.print("\n[bold cyan]Exporting reports to PDF...[/bold cyan]")
            pdf_paths = core_api.export_all_reports_to_pdf()
            if pdf_paths:
                core_api.print_success(f"Exported {len(pdf_paths)} reports to PDF")
        except ImportError:
            core_api.print_error(
                "PDF export requires 'markdown' and 'weasyprint' packages. "
                "Install with: uv pip install markdown weasyprint"
            )
        except Exception as e:
            core_api.print_error(f"PDF export failed: {e}")

    # Export all reports to HTML if not already done (when --html flag is used)
    # Note: Individual HTML files are created automatically during report generation if HTML export is enabled
    # This is a fallback for batch conversion or if you want to ensure all reports are exported
    if html_export and not core_api.is_html_export_enabled():
        # Manual batch export (only if automatic export wasn't enabled)
        try:
            console.print("\n[bold cyan]Exporting reports to HTML...[/bold cyan]")
            html_paths = core_api.export_all_reports_to_html()
            if html_paths:
                core_api.print_success(f"Exported {len(html_paths)} reports to HTML")
        except ImportError:
            core_api.print_error(
                "HTML export requires 'markdown' package. "
                "Install with: uv pip install markdown"
            )
        except Exception as e:
            core_api.print_error(f"HTML export failed: {e}")

    # Close ZIP file if it was opened
    if zip_file:
        core_api.close_zip()

    if failed_count > 0 and len(plugins_to_run) > 1:
        raise typer.Exit(code=1)


@app.command()
def info(
    plugin_name: Annotated[str, typer.Argument(help="Name of the plugin")],
) -> None:
    """Show detailed information about a plugin."""
    core_api = get_core_api()
    plugin_manager = get_plugin_manager()

    # Discover plugins if not already done
    if not plugin_manager._plugin_classes:
        plugin_manager.discover_plugins()

    # Try to get the plugin (loaded or create temporary instance)
    plugin = plugin_manager.get_plugin(plugin_name)
    if not plugin and plugin_name in plugin_manager._plugin_classes:
        # Create temporary instance to get metadata
        plugin_class = plugin_manager._plugin_classes[plugin_name]
        try:
            plugin = plugin_class(core_api)
        except Exception as e:
            core_api.print_error(f"Failed to get plugin info: {e}")
            raise typer.Exit(code=1) from e

    if not plugin:
        core_api.print_error(f"Plugin '{plugin_name}' not found")
        raise typer.Exit(code=1)

    metadata = plugin.metadata

    info_text = (
        f"[bold]Name:[/bold] {metadata.name}\n"
        f"[bold]Version:[/bold] {metadata.version}\n"
        f"[bold]Author:[/bold] {metadata.author}\n"
        f"[bold]Description:[/bold] {metadata.description}\n"
        f"[bold]Status:[/bold] {plugin.status.value}\n"
        f"[bold]Enabled:[/bold] {metadata.enabled}\n"
        f"[bold]Required Core Version:[/bold] {metadata.requires_core_version}\n"
        f"[bold]Dependencies:[/bold] "
        f"{', '.join(metadata.dependencies) if metadata.dependencies else 'None'}"
    )

    console.print(Panel(info_text, title=f"Plugin: {metadata.name}", border_style="cyan"))


@app.command()
def reload() -> None:
    """Reload all plugins (unload and load again)."""
    core_api = get_core_api()
    plugin_manager = get_plugin_manager()

    core_api.print_info("Reloading plugins...")

    # Unload all plugins
    plugin_manager.unload_all_plugins()

    # Discover and load all plugins
    plugin_manager.discover_plugins()
    plugin_manager.load_all_plugins()

    stats = plugin_manager.get_plugin_count()
    core_api.print_success(f"Reloaded {stats['loaded']} plugins")


@app.command()
def update_plugins(
    force: Annotated[
        bool,
        typer.Option("--force", "-f", help="Force update check (ignore cache)"),
    ] = False,
    plugin: Annotated[
        str | None,
        typer.Option("--plugin", "-p", help="Update specific plugin by filename"),
    ] = None,
    check_only: Annotated[
        bool,
        typer.Option("--check-only", "-c", help="Only check for updates, don't download"),
    ] = False,
    no_verify: Annotated[
        bool,
        typer.Option("--no-verify", help="Skip SHA256 verification (not recommended)"),
    ] = False,
) -> None:
    """
    Update plugins from GitHub repository.

    This command checks for plugin updates and optionally downloads them.
    By default, it checks for updates and downloads any new or updated plugins.

    Examples:
        yaft update-plugins                    # Check and download updates
        yaft update-plugins --check-only       # Only check, don't download
        yaft update-plugins --force            # Force check (ignore cache)
        yaft update-plugins --plugin ios.py    # Update specific plugin
    """
    core_api = get_core_api()

    console.print(Panel(
        "[bold cyan]Plugin Update System[/bold cyan]\n"
        "Checking for plugin updates from GitHub...",
        border_style="cyan",
    ))

    try:
        # Get updater instance
        updater = core_api.get_plugin_updater()

        # Check for updates
        console.print("[cyan]→[/cyan] Checking for updates...")
        check_result = updater.check_for_updates(force=force)

        if check_result.error:
            console.print(f"[red]✗ Error:[/red] {check_result.error}")
            raise typer.Exit(code=1)

        if not check_result.updates_available:
            console.print("[green]✓[/green] All plugins up to date!")
            console.print(f"[dim]Total plugins: {check_result.total_plugins}[/dim]")
            return

        # Display update information
        console.print(f"\n[yellow]Updates available:[/yellow]")
        if check_result.new_plugins:
            console.print(f"  [cyan]New plugins:[/cyan] {len(check_result.new_plugins)}")
            for p in check_result.new_plugins[:5]:  # Show first 5
                console.print(f"    • {p}")
            if len(check_result.new_plugins) > 5:
                console.print(f"    ... and {len(check_result.new_plugins) - 5} more")

        if check_result.updated_plugins:
            console.print(f"  [cyan]Updated plugins:[/cyan] {len(check_result.updated_plugins)}")
            for p in check_result.updated_plugins[:5]:  # Show first 5
                console.print(f"    • {p}")
            if len(check_result.updated_plugins) > 5:
                console.print(f"    ... and {len(check_result.updated_plugins) - 5} more")

        if check_only:
            console.print("\n[dim]Use [bold]update-plugins[/bold] without --check-only to download updates.[/dim]")
            return

        # Download updates
        console.print("\n[cyan]→[/cyan] Downloading updates...")

        plugins_to_download = None
        if plugin:
            plugins_to_download = [plugin]

        download_result = updater.download_plugins(
            plugin_list=plugins_to_download,
            verify=not no_verify,
            backup=True,
        )

        # Display results
        if download_result.success:
            console.print(f"\n[green]✓ Update complete![/green]")
            console.print(f"  Downloaded: {len(download_result.downloaded)} plugins")
            if download_result.verified:
                console.print(f"  Verified: {len(download_result.verified)} plugins")
        else:
            console.print(f"\n[yellow]⚠ Update completed with errors[/yellow]")
            console.print(f"  Downloaded: {len(download_result.downloaded)} plugins")
            console.print(f"  Failed: {len(download_result.failed)} plugins")

            if download_result.errors:
                console.print("\n[red]Errors:[/red]")
                for error in download_result.errors[:5]:  # Show first 5 errors
                    console.print(f"  • {error}")

    except Exception as e:
        console.print(f"\n[red]✗ Failed to update plugins:[/red] {str(e)}")
        raise typer.Exit(code=1)


@app.command()
def list_available_plugins(
    os_filter: Annotated[
        str | None,
        typer.Option("--os", "-o", help="Filter by OS (ios, android)"),
    ] = None,
) -> None:
    """
    List all available plugins from GitHub repository.

    Shows plugins available for download from the remote repository,
    including version, size, and target OS information.

    Examples:
        yaft list-available-plugins              # List all plugins
        yaft list-available-plugins --os ios     # List iOS plugins only
    """
    core_api = get_core_api()

    console.print(Panel(
        "[bold cyan]Available Plugins[/bold cyan]\n"
        "Listing plugins from GitHub repository...",
        border_style="cyan",
    ))

    try:
        # Get updater instance
        updater = core_api.get_plugin_updater()

        # Check for updates to refresh manifest
        console.print("[cyan]→[/cyan] Fetching plugin list...")
        updater.check_for_updates(force=True)

        # List plugins
        plugins = updater.list_available_plugins()

        if not plugins:
            console.print("[yellow]No plugins found in repository[/yellow]")
            return

        # Filter by OS if requested
        if os_filter:
            os_filter_lower = os_filter.lower()
            plugins = [
                p for p in plugins
                if p["os_target"] and os_filter_lower in [os.lower() for os in p["os_target"]]
            ]

        if not plugins:
            console.print(f"[yellow]No {os_filter} plugins found[/yellow]")
            return

        # Display plugins in a table
        from rich.table import Table

        table = Table(title=f"Available Plugins ({len(plugins)} total)")
        table.add_column("Plugin Name", style="cyan")
        table.add_column("Filename", style="white")
        table.add_column("Version", style="green")
        table.add_column("OS", style="yellow")
        table.add_column("Size", style="dim")
        table.add_column("Required", style="magenta")

        for plugin in plugins:
            os_target = ", ".join(plugin["os_target"]) if plugin["os_target"] else "N/A"
            size_kb = plugin["size"] / 1024
            required = "Yes" if plugin["required"] else "No"

            table.add_row(
                plugin["name"],
                plugin["filename"],
                plugin["version"],
                os_target,
                f"{size_kb:.1f} KB",
                required,
            )

        console.print(table)

        if os_filter:
            console.print(f"\n[dim]Filtered by OS: {os_filter}[/dim]")

    except Exception as e:
        console.print(f"\n[red]✗ Failed to list plugins:[/red] {str(e)}")
        raise typer.Exit(code=1)


@app.command()
def api_docs(
    category: Annotated[
        str | None,
        typer.Argument(help="Show methods for specific category (optional)"),
    ] = None,
    search: Annotated[
        str | None,
        typer.Option("--search", "-s", help="Search for methods by name"),
    ] = None,
) -> None:
    """
    Display Core API methods available for plugin development.

    Lists all public methods in the Core API, organized by functional category.
    This is useful for plugin developers to discover available functionality.

    Examples:
        yaft api-docs                           # Show all categories and method counts
        yaft api-docs "ZIP File Handling"       # Show all ZIP-related methods
        yaft api-docs --search plist            # Search for plist-related methods
        yaft api-docs --search query            # Search for query methods
    """
    from rich.table import Table
    from rich.text import Text

    core_api = get_core_api()

    console.print(Panel(
        "[bold cyan]Core API Documentation[/bold cyan]\n"
        f"YAFT v{__version__} - Plugin Developer Reference",
        border_style="cyan",
    ))

    try:
        methods = core_api.get_api_methods()

        # Search mode
        if search:
            search_lower = search.lower()
            console.print(f"\n[bold]Searching for methods matching: [cyan]{search}[/cyan][/bold]\n")

            found = False
            for cat, method_list in methods.items():
                matching = [m for m in method_list if search_lower in m["name"].lower()]
                if matching:
                    found = True
                    console.print(f"[bold yellow]{cat}:[/bold yellow]")
                    for method in matching:
                        console.print(f"  [cyan]{method['signature']}[/cyan]")
                        if method["returns"]:
                            console.print(f"    [dim]Returns: {method['returns']}[/dim]")
                        console.print(f"    {method['description']}\n")

            if not found:
                console.print(f"[yellow]No methods found matching '{search}'[/yellow]")
            return

        # Specific category mode
        if category:
            if category not in methods:
                console.print(f"[red]Category '{category}' not found.[/red]\n")
                console.print("[bold]Available categories:[/bold]")
                for cat in methods.keys():
                    console.print(f"  - {cat}")
                raise typer.Exit(code=1)

            method_list = methods[category]
            console.print(f"\n[bold yellow]{category}[/bold yellow] ([cyan]{len(method_list)}[/cyan] methods)\n")

            table = Table(show_header=True, header_style="bold cyan", box=None)
            table.add_column("Method", style="cyan", no_wrap=False)
            table.add_column("Returns", style="green", no_wrap=True)
            table.add_column("Description", style="white", no_wrap=False)

            for method in method_list:
                table.add_row(
                    method["signature"],
                    method["returns"] or "-",
                    method["description"],
                )

            console.print(table)
            return

        # Overview mode - show all categories
        console.print("\n[bold]API Method Categories:[/bold]\n")

        # Count total methods
        total_methods = sum(len(method_list) for method_list in methods.values())

        table = Table(show_header=True, header_style="bold cyan")
        table.add_column("Category", style="yellow", no_wrap=False)
        table.add_column("Methods", justify="right", style="cyan")
        table.add_column("Examples", style="dim", no_wrap=False)

        for cat, method_list in methods.items():
            # Show first 3 method names as examples
            examples = ", ".join([m["name"] for m in method_list[:3]])
            if len(method_list) > 3:
                examples += ", ..."

            table.add_row(
                cat,
                str(len(method_list)),
                examples,
            )

        console.print(table)

        console.print(f"\n[bold]Total API Methods:[/bold] [cyan]{total_methods}[/cyan]")
        console.print("\n[dim]Usage:[/dim]")
        console.print("  [dim]yaft api-docs \"<category>\"     - View methods in specific category[/dim]")
        console.print("  [dim]yaft api-docs --search <term>  - Search for methods by name[/dim]")

    except Exception as e:
        console.print(f"\n[red]✗ Failed to retrieve API documentation:[/red] {str(e)}")
        raise typer.Exit(code=1)


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    version_flag: Annotated[
        bool | None,
        typer.Option("--version", "-v", help="Show version and exit"),
    ] = None,
) -> None:
    """
    YAFT - Yet Another Forensic Tool

    A plugin-based forensic analysis tool for processing ZIP archives with extensible plugins.
    """
    if version_flag:
        version()
        raise typer.Exit()

    if ctx.invoked_subcommand is None:
        console.print(Panel(
            "[bold cyan]YAFT[/bold cyan] - Yet Another Forensic Tool\n\n"
            "Use [bold]--help[/bold] to see available commands.\n"
            "Use [bold]list-plugins[/bold] to see available plugins.\n"
            "Use [bold]run PLUGIN_NAME --zip FILE.zip[/bold] to analyze a ZIP file with a plugin.",
            title="Welcome",
            border_style="cyan",
        ))


if __name__ == "__main__":
    app()
