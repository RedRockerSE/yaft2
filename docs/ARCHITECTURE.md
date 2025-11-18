# YAFT Architecture Documentation

## Overview

YAFT (Yet Another Framework Tool) is a plugin-based application framework designed with extensibility, maintainability, and developer experience as primary goals. This document explains the architectural decisions, design patterns, and implementation details.

## Design Principles

### 1. Loose Coupling

**Goal**: Plugins should not depend on each other or core implementation details.

**Implementation**:
- Plugins only depend on `PluginBase` interface
- All shared functionality provided through `CoreAPI`
- Inter-plugin communication through shared data store
- No direct plugin-to-plugin references

### 2. High Cohesion

**Goal**: Each component should have a single, well-defined responsibility.

**Implementation**:
- `PluginBase`: Defines plugin interface
- `PluginManager`: Handles plugin lifecycle
- `CoreAPI`: Provides shared services
- `CLI`: User interface layer

### 3. Dependency Inversion

**Goal**: High-level modules should not depend on low-level modules.

**Implementation**:
- Plugins depend on abstractions (PluginBase)
- CoreAPI injected into plugins (dependency injection)
- No concrete dependencies between plugins

### 4. Open/Closed Principle

**Goal**: Open for extension, closed for modification.

**Implementation**:
- New plugins add functionality without changing core
- Plugin interface is stable and versioned
- Core functionality extended through CoreAPI

## Architecture Layers

```
┌───────────────────────────────────────────────────────┐
│                 Presentation Layer                     │
│                   (CLI Interface)                      │
│                                                        │
│  - Command parsing (Typer)                            │
│  - Output formatting (Rich)                           │
│  - User interaction                                   │
└────────────────────┬──────────────────────────────────┘
                     │
                     ▼
┌───────────────────────────────────────────────────────┐
│                 Application Layer                      │
│                  (Plugin Manager)                      │
│                                                        │
│  - Plugin discovery                                   │
│  - Lifecycle management                               │
│  - Dependency resolution                              │
│  - Error handling                                     │
└────────────────────┬──────────────────────────────────┘
                     │
                     ▼
┌───────────────────────────────────────────────────────┐
│                  Service Layer                         │
│                    (Core API)                          │
│                                                        │
│  - Logging                                            │
│  - File I/O                                           │
│  - Configuration management                           │
│  - Shared data storage                                │
└────────────────────┬──────────────────────────────────┘
                     │
                     ▼
┌───────────────────────────────────────────────────────┐
│                  Domain Layer                          │
│                (Plugin Interface)                      │
│                                                        │
│  - PluginBase (abstract interface)                   │
│  - PluginMetadata (configuration)                     │
│  - PluginStatus (state management)                    │
└───────────────────────────────────────────────────────┘
```

## Core Components

### 1. PluginBase (Domain Layer)

**Responsibility**: Define the contract for all plugins.

**Key Design Decisions**:

- **Abstract Base Class**: Forces implementation of required methods
- **Property-based Metadata**: Immutable configuration using Pydantic
- **Status Tracking**: Explicit state machine for plugin lifecycle
- **CoreAPI Injection**: Dependency injection for loose coupling

```python
class PluginBase(ABC):
    @property
    @abstractmethod
    def metadata(self) -> PluginMetadata:
        pass

    @abstractmethod
    def initialize(self) -> None:
        pass

    @abstractmethod
    def execute(self, *args: Any, **kwargs: Any) -> Any:
        pass

    @abstractmethod
    def cleanup(self) -> None:
        pass
```

**Why Abstract Methods?**
- Compile-time checks for interface compliance
- Clear contract for plugin developers
- IDE autocomplete support
- Documentation through code

### 2. PluginManager (Application Layer)

**Responsibility**: Manage plugin lifecycle and discovery.

**Key Design Decisions**:

**Discovery Mechanism**:
- File system scanning for `.py` files
- Dynamic module loading with `importlib`
- Runtime inspection for `PluginBase` subclasses
- Works in both source and compiled executables

**Why importlib?**
- Native Python solution (no dependencies)
- Supports dynamic imports
- Works with PyInstaller
- Full control over import process

**Lifecycle Management**:
1. Discovery: Find plugin files
2. Loading: Import and instantiate
3. Initialization: Setup resources
4. Execution: Run plugin logic
5. Cleanup: Release resources

**Error Isolation**:
- Failed plugin doesn't crash application
- Status tracking for debugging
- Comprehensive error logging
- Graceful degradation

### 3. CoreAPI (Service Layer)

**Responsibility**: Provide shared functionality to plugins.

**Key Design Decisions**:

**Service Facade Pattern**:
- Single access point for core services
- Hides implementation complexity
- Easy to extend with new services
- Consistent interface for plugins

**Provided Services**:
- **Logging**: Structured logging with Rich
- **Output**: Colored console output
- **I/O**: Safe file operations
- **Configuration**: Path management
- **Shared Data**: Inter-plugin communication
- **User Input**: Interactive prompts
- **ZIP File Handling**: Comprehensive ZIP operations for forensic analysis
- **Format Detection**: Automatic detection of Cellebrite/GrayKey formats
- **Data Parsing**: Built-in plist, XML, and SQLite parsing
- **Case Management**: Forensic case identifier tracking and organization
- **Report Generation**: Unified markdown/PDF report system
- **Plugin Updates**: Automatic plugin update and download system

**Why Rich Console?**
- Beautiful, consistent output
- Cross-platform color support
- Tables, panels, progress bars
- Production-ready formatting

### 4. CLI (Presentation Layer)

**Responsibility**: User interface and command routing.

**Key Design Decisions**:

**Typer Framework**:
- Type-safe command definitions
- Automatic help generation
- Argument validation
- Excellent developer experience

**Command Structure**:
- `list-plugins`: Discovery and status
- `info`: Plugin metadata
- `load/unload`: Manual lifecycle control
- `run`: Execute plugin
- `reload`: Hot reload in development

**Why Typer over argparse/click?**
- Modern, type-hint based
- Less boilerplate
- Better error messages
- Native async support

## Plugin Discovery Deep Dive

### Discovery Algorithm

```python
def discover_plugins(self) -> dict[str, type[PluginBase]]:
    1. Scan plugin directories
    2. Filter for *.py files (not starting with _)
    3. For each file:
        a. Load as Python module
        b. Inspect for classes
        c. Find PluginBase subclasses
        d. Validate plugin structure
    4. Return mapping of name -> class
```

### Why This Approach?

**Advantages**:
- No explicit registration needed
- Works with compiled executables
- Hot reload support (development)
- Plugin files are independent

**Alternatives Considered**:

1. **Entry Points** (setuptools):
   - Pros: Standard Python mechanism
   - Cons: Requires installation, complex for standalone executables

2. **Decorator Registration**:
   - Pros: Explicit, clear
   - Cons: Requires import of all modules, tight coupling

3. **Configuration Files**:
   - Pros: Centralized management
   - Cons: Manual registration, error-prone

### Making It Work in Executables

**Challenge**: PyInstaller bundles code, changing file system structure.

**Solution**:
1. Include `plugins/` directory in PyInstaller spec
2. Use `importlib` for dynamic imports (PyInstaller compatible)
3. Runtime directory creation in built executables
4. Plugin paths relative to executable location

```python
# In PyInstaller spec file
datas += [('plugins', 'plugins')]
```

## Plugin Communication

### Shared Data Store

**Purpose**: Allow plugins to share data without tight coupling.

**Implementation**:
```python
# Plugin A
self.core_api.set_shared_data("key", value)

# Plugin B
value = self.core_api.get_shared_data("key", default=None)
```

**Design Decisions**:
- Simple dict-based storage
- No persistence (in-memory only)
- Namespacing left to plugins (convention: "plugin_name.key")
- Thread-safe for future async support

**Alternatives Considered**:

1. **Event System**: More complex, harder to debug
2. **Message Queue**: Overkill for simple use cases
3. **Direct References**: Violates loose coupling

## Type Safety

### Why Pydantic for Metadata?

**Benefits**:
- Runtime validation
- Immutable configurations
- Excellent error messages
- JSON schema generation
- IDE support

```python
class PluginMetadata(BaseModel):
    name: str = Field(..., description="Unique plugin identifier")
    version: str = Field(..., description="Plugin version")

    class Config:
        frozen = True  # Immutable
```

### Type Hints Throughout

**Benefits**:
- Early error detection (mypy)
- Better IDE support
- Self-documenting code
- Easier refactoring

## Error Handling Strategy

### Layered Error Handling

1. **Plugin Level**: Catch and handle plugin-specific errors
2. **Manager Level**: Catch initialization/execution failures
3. **CLI Level**: Catch and display user-friendly errors

### Plugin Status Tracking

```python
class PluginStatus(str, Enum):
    UNLOADED = "unloaded"
    LOADED = "loaded"
    INITIALIZED = "initialized"
    ACTIVE = "active"
    ERROR = "error"
    DISABLED = "disabled"
```

**Benefits**:
- Explicit state machine
- Easy debugging
- Status displayed in CLI
- Enables monitoring

## Build System

### PyInstaller Configuration

**Requirements**:
1. Bundle Python interpreter
2. Include all dependencies
3. Support dynamic plugin loading
4. Cross-platform builds

**Spec File Approach**:
- Custom spec file for fine control
- Explicit data file inclusion
- Hidden import declarations
- Plugin directory bundling

```python
# Key parts of spec file
datas += [('plugins', 'plugins')]  # Include plugins
hiddenimports += ['yaft.core.*']    # Ensure imports work
```

### Why PyInstaller over alternatives?

**Alternatives Considered**:

1. **PyOxidizer**: Modern but complex, less plugin support
2. **Nuitka**: Faster but harder to configure
3. **cx_Freeze**: Less active development

**PyInstaller Chosen Because**:
- Mature, well-tested
- Good plugin support
- Extensive documentation
- Large community

## Extensibility Points

### Adding New Core Services

Extend `CoreAPI` with new methods:

```python
class CoreAPI:
    def new_service(self, param: str) -> Result:
        """New shared functionality."""
        pass
```

All plugins automatically gain access.

### Custom Plugin Discovery

Extend `PluginManager`:

```python
class CustomPluginManager(PluginManager):
    def discover_plugins(self) -> dict[str, type[PluginBase]]:
        # Custom discovery logic
        plugins = super().discover_plugins()
        # Add custom sources
        return plugins
```

### Alternative CLI Frameworks

Replace CLI layer without changing core:

```python
# Could use Flask, FastAPI, etc.
@app.route('/run/<plugin_name>')
def run_plugin(plugin_name):
    return plugin_manager.execute_plugin(plugin_name)
```

## Performance Considerations

### Plugin Loading

**Current**: Lazy loading - plugins loaded on demand
**Alternative**: Eager loading - all plugins at startup

**Decision**: Lazy loading
- Faster startup
- Lower memory usage
- Only load what's needed

### Caching

**Discovery Cache**: Results cached after first scan
**Import Cache**: Python's module cache used
**Data Cache**: Up to plugins (via CoreAPI)

### Scalability

**Current Scale**: Hundreds of plugins
**Bottlenecks**:
- File system scanning (mitigated by caching)
- Module imports (Python limitation)

**Future Improvements**:
- Parallel plugin loading
- Plugin metadata cache
- Lazy initialization

## Security Considerations

### Plugin Sandboxing

**Current**: No sandboxing - plugins run with full permissions

**Rationale**:
- Plugins are trusted (local installation)
- Sandboxing complex and restrictive
- Python's nature makes true sandboxing difficult

**For Production**: Consider:
- Plugin signing
- Permission system
- Resource limits

### Input Validation

**Plugin Metadata**: Validated by Pydantic
**User Input**: Sanitized by plugins
**File Paths**: Path traversal prevention in CoreAPI

## Testing Strategy

### Unit Tests

- Test each component in isolation
- Mock dependencies
- Cover edge cases

### Integration Tests

- Test plugin loading end-to-end
- Test CLI commands
- Test plugin execution

### Test Fixtures

```python
@pytest.fixture
def core_api(temp_dir):
    return CoreAPI(config_dir=temp_dir / "config")

@pytest.fixture
def plugin_manager(core_api, plugin_dir):
    return PluginManager(core_api, [plugin_dir])
```

## Future Enhancements

### Potential Improvements

1. **Async Support**: Native async plugin execution
2. **Plugin Versioning**: SemVer-based compatibility checks
3. **Plugin Repository**: Central plugin distribution
4. **GUI Interface**: Web-based plugin management
5. **Plugin Dependencies**: Automatic dependency resolution
6. **Hot Reload**: Live plugin updates without restart
7. **Plugin Metrics**: Performance monitoring
8. **Plugin Signing**: Security verification

### Backward Compatibility

**Promise**: Plugin interface (PluginBase) will remain stable
**Versioning**: Core version checked against plugin requirements
**Migration**: Deprecation warnings before breaking changes

## Lessons Learned

### What Worked Well

1. **Abstract interfaces**: Clear contracts
2. **Type hints**: Caught many bugs early
3. **Rich/Typer**: Excellent developer experience
4. **Pydantic**: Runtime validation prevented issues
5. **Comprehensive tests**: Confident refactoring

### What Could Be Improved

1. **Plugin dependencies**: Currently manual
2. **Error messages**: Could be more specific
3. **Performance**: Plugin loading could be faster
4. **Documentation**: Always room for improvement

## References

### Design Patterns Used

- **Dependency Injection**: CoreAPI injection
- **Abstract Factory**: Plugin creation
- **Facade**: CoreAPI simplifies core services
- **Strategy**: Plugin execution strategies
- **Observer**: (Future) Event system

### External Resources

- [Python Plugin Architecture](https://docs.python.org/3/library/importlib.html)
- [Rich Documentation](https://rich.readthedocs.io/)
- [Typer Documentation](https://typer.tiangolo.com/)
- [Pydantic Documentation](https://docs.pydantic.dev/)
- [PyInstaller Documentation](https://pyinstaller.org/)

## Conclusion

YAFT's architecture prioritizes:
1. **Extensibility**: Easy to add plugins
2. **Maintainability**: Clear separation of concerns
3. **Developer Experience**: Modern tools, good documentation
4. **Production Readiness**: Error handling, logging, testing

The architecture is designed to scale from small personal projects to larger applications while maintaining simplicity and clarity.
