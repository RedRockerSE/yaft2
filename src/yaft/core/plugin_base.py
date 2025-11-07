"""
Base classes and interfaces for plugins.

This module defines the contract that all plugins must implement.
"""

from abc import ABC, abstractmethod
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class PluginStatus(str, Enum):
    """Plugin lifecycle status."""

    UNLOADED = "unloaded"
    LOADED = "loaded"
    INITIALIZED = "initialized"
    ACTIVE = "active"
    ERROR = "error"
    DISABLED = "disabled"


class PluginMetadata(BaseModel):
    """
    Plugin metadata and configuration.

    All plugins must provide this metadata for discovery and management.
    """

    name: str = Field(..., description="Unique plugin identifier")
    version: str = Field(..., description="Plugin version (semver recommended)")
    description: str = Field(..., description="Human-readable plugin description")
    author: str = Field(default="Unknown", description="Plugin author")
    requires_core_version: str = Field(
        default=">=0.1.0", description="Required core framework version"
    )
    dependencies: list[str] = Field(
        default_factory=list, description="List of required plugin dependencies"
    )
    enabled: bool = Field(default=True, description="Whether plugin is enabled")
    target_os: list[str] = Field(
        default_factory=lambda: ["any"],
        description="Target operating systems: 'ios', 'android', 'any', or combination"
    )

    class Config:
        """Pydantic configuration."""

        frozen = True  # Make metadata immutable after creation


class PluginBase(ABC):
    """
    Abstract base class for all plugins.

    Plugin developers must inherit from this class and implement all abstract methods.
    The plugin lifecycle follows this sequence:
    1. __init__() - Plugin instantiation
    2. initialize() - Plugin setup and resource allocation
    3. execute() - Plugin main functionality
    4. cleanup() - Plugin teardown and resource cleanup
    """

    def __init__(self, core_api: Any) -> None:
        """
        Initialize the plugin with access to core API.

        Args:
            core_api: CoreAPI instance providing shared functionality
        """
        self.core_api = core_api
        self._status = PluginStatus.LOADED

    @property
    @abstractmethod
    def metadata(self) -> PluginMetadata:
        """
        Return plugin metadata.

        Returns:
            PluginMetadata: Plugin information and configuration
        """
        pass

    @abstractmethod
    def initialize(self) -> None:
        """
        Initialize the plugin.

        Called once after plugin is loaded. Use this for:
        - Setting up resources
        - Validating dependencies
        - Registering event handlers

        Raises:
            Exception: If initialization fails
        """
        pass

    @abstractmethod
    def execute(self, *args: Any, **kwargs: Any) -> Any:
        """
        Execute the plugin's main functionality.

        This is called when the plugin is invoked by the user or system.

        Args:
            *args: Positional arguments
            **kwargs: Keyword arguments

        Returns:
            Any: Plugin execution result

        Raises:
            Exception: If execution fails
        """
        pass

    @abstractmethod
    def cleanup(self) -> None:
        """
        Clean up plugin resources.

        Called when plugin is unloaded or application exits. Use this for:
        - Closing file handles
        - Releasing network connections
        - Saving state
        """
        pass

    @property
    def status(self) -> PluginStatus:
        """Get current plugin status."""
        return self._status

    @status.setter
    def status(self, value: PluginStatus) -> None:
        """Set plugin status."""
        self._status = value

    def __repr__(self) -> str:
        """String representation of the plugin."""
        return f"<Plugin: {self.metadata.name} v{self.metadata.version} [{self.status.value}]>"
