
## Context
This project aims to develop a python-based application that uses plugins for it's functionality. The aim is to devekop an app that can easily be extended with new functionality. Plugins may use common core functionality which should med exposed in the core application.

The App is called YaFT which stands for: Yet Another Forensic Tool

## Requirements
- Use Python version 3.13+
- CLI based user interface
- Colourcoded output
- Buildsystem with builds for Windows and Linux
- Pluginbased functionality with losely-coupled plugins. Investigate if it's possible to add plugins that the built executables could pickup. Plugins in form of python-scripts or some sort of built binaries is ok. Suggest the best and most dynamic solution
- The user needs to point out a zip-file that YaFT then will use to process using it's available plugins. Zip-file handling needed should be provided to plugins from the core functionality as described in [[ARCHITECTURE]]

### Added requirements 2025-11-05
- Core API should contain a report-method that plugins can call for a unified way of creating reports with findings and/or results. Report-format should be in markdown. Update all existing plugins to use this for reporting.

### Added requirements 2025-11-06
- iOSAppGUIDExtractorPlugin and iOSAppPermissionsExtractorPlugin currently depends on plistlib and sqlite3. Research and implement (if doable) the move of methods, using these dependencies, to the core-api. There might be future plugins that needs to parse plists and query sqlite-databases so this should be functionality exposed by the core-api. 
