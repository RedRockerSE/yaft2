"""
CLI interface for YAFT application.

Provides command-line interface with color-coded output using Typer and Rich.
"""

from pathlib import Path
from typing import Annotated, Optional

import typer
from rich.console import Console
from rich.panel import Panel

from yaft import __version__
from yaft.core.api import CoreAPI
from yaft.core.plugin_manager import PluginManager

# Create Typer app
app = typer.Typer(
    name="yaft",
    help="YAFT - Yet Another Forensic Tool: A plugin-based forensic analysis tool for processing ZIP archives",
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
    all: Annotated[bool, typer.Option("--all", "-a", help="Show all discovered plugins")] = False,
) -> None:
    """List available plugins."""
    plugin_manager = get_plugin_manager()

    # Discover plugins if not already done
    if not plugin_manager._plugin_classes:
        console.print("[yellow]Discovering plugins...[/yellow]")
        plugin_manager.discover_plugins()

    plugin_manager.list_plugins(show_all=all)

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
    plugin_name: Annotated[str, typer.Argument(help="Name of the plugin to run")],
    zip_file: Annotated[Optional[Path], typer.Option("--zip", "-z", help="ZIP file to analyze")] = None,
    args: Annotated[Optional[list[str]], typer.Argument(help="Arguments to pass to the plugin")] = None,
) -> None:
    """Load and execute a plugin, optionally with a ZIP file for forensic analysis."""
    core_api = get_core_api()
    plugin_manager = get_plugin_manager()

    # Prompt for case identifiers
    try:
        core_api.prompt_for_case_identifiers()
    except KeyboardInterrupt:
        core_api.print_error("\nCase identifier input cancelled")
        raise typer.Exit(code=1)
    except Exception as e:
        core_api.print_error(f"Failed to get case identifiers: {e}")
        raise typer.Exit(code=1)

    # Load ZIP file if provided
    if zip_file:
        try:
            core_api.set_zip_file(zip_file)
            core_api.print_success(f"Loaded ZIP file: {zip_file.name}")
        except Exception as e:
            core_api.print_error(f"Failed to load ZIP file: {e}")
            raise typer.Exit(code=1)

    # Discover plugins if not already done
    if not plugin_manager._plugin_classes:
        core_api.print_info("Discovering plugins...")
        plugin_manager.discover_plugins()

    # Load plugin if not already loaded
    plugin = plugin_manager.get_plugin(plugin_name)
    if not plugin:
        core_api.print_info(f"Loading plugin '{plugin_name}'...")
        plugin = plugin_manager.load_plugin(plugin_name)
        if not plugin:
            core_api.print_error(f"Failed to load plugin '{plugin_name}'")
            raise typer.Exit(code=1)

    # Execute plugin
    try:
        core_api.print_info(f"Executing plugin '{plugin.metadata.name}'...")
        result = plugin_manager.execute_plugin(plugin_name, *(args or []))

        if result is not None:
            console.print("\n[bold green]Plugin Result:[/bold green]")
            console.print(result)

        core_api.print_success(f"Plugin '{plugin.metadata.name}' executed successfully")
    except Exception as e:
        core_api.print_error(f"Plugin execution failed: {e}")
        raise typer.Exit(code=1)
    finally:
        # Close ZIP file if it was opened
        if zip_file:
            core_api.close_zip()


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
            raise typer.Exit(code=1)

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
        f"[bold]Dependencies:[/bold] {', '.join(metadata.dependencies) if metadata.dependencies else 'None'}"
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


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    version_flag: Annotated[
        Optional[bool],
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
