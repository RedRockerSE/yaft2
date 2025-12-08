"""
Analyze Core API to extract method signatures and docstrings.

This script is used to generate documentation for the Core API.
"""

import ast
import inspect
from pathlib import Path


def extract_method_info(source_file: Path) -> list[dict]:
    """Extract method signatures and docstrings from source file."""
    with open(source_file, encoding="utf-8") as f:
        source = f.read()

    tree = ast.parse(source)
    methods = []

    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == "CoreAPI":
            for item in node.body:
                if isinstance(item, ast.FunctionDef):
                    # Skip private methods
                    if item.name.startswith("_"):
                        continue

                    # Extract signature
                    args = []
                    for arg in item.args.args:
                        if arg.arg == "self":
                            continue
                        # Get annotation if available
                        annotation = ""
                        if arg.annotation:
                            annotation = ast.unparse(arg.annotation)
                        args.append(f"{arg.arg}: {annotation}" if annotation else arg.arg)

                    # Extract return annotation
                    returns = ""
                    if item.returns:
                        returns = ast.unparse(item.returns)

                    # Extract docstring
                    docstring = ast.get_docstring(item) or ""

                    methods.append({
                        "name": item.name,
                        "args": args,
                        "returns": returns,
                        "docstring": docstring,
                        "signature": f"{item.name}({', '.join(args)})",
                    })

    return methods


def categorize_methods(methods: list[dict]) -> dict[str, list[dict]]:
    """Categorize methods by functionality."""
    categories = {
        "Logging": [],
        "Output & Display": [],
        "Case Management": [],
        "ZIP File Handling": [],
        "File Search": [],
        "Data Format Parsing": [],
        "SQLite & Database": [],
        "BLOB Handling": [],
        "Forensic Analysis": [],
        "Report Generation": [],
        "Export Functions": [],
        "Configuration": [],
        "Plugin System": [],
        "User Input": [],
        "Shared Data": [],
        "Other": [],
    }

    for method in methods:
        name = method["name"]

        # Categorize by method name patterns
        if name.startswith("log_"):
            categories["Logging"].append(method)
        elif name.startswith("print_"):
            categories["Output & Display"].append(method)
        elif "case" in name or "examiner" in name or "evidence" in name:
            categories["Case Management"].append(method)
        elif name.startswith("set_zip") or name.startswith("get_current_zip") or name.startswith("close_zip"):
            categories["ZIP File Handling"].append(method)
        elif "zip" in name and ("list" in name or "read" in name or "extract" in name or "display" in name):
            categories["ZIP File Handling"].append(method)
        elif "find_files" in name:
            categories["File Search"].append(method)
        elif "plist" in name or "xml" in name or name.startswith("parse_"):
            categories["Data Format Parsing"].append(method)
        elif "sqlite" in name or "query" in name or "sqlcipher" in name or "decrypt" in name:
            categories["SQLite & Database"].append(method)
        elif "blob" in name:
            categories["BLOB Handling"].append(method)
        elif "keychain" in name or "locksettings" in name or "keystore" in name or "extraction" in name or "detect" in name:
            categories["Forensic Analysis"].append(method)
        elif "report" in name or "markdown" in name:
            categories["Report Generation"].append(method)
        elif "export" in name or "pdf" in name or "html" in name or "json" in name or "csv" in name:
            categories["Export Functions"].append(method)
        elif "config" in name or "profile" in name:
            categories["Configuration"].append(method)
        elif "plugin" in name or "updater" in name:
            categories["Plugin System"].append(method)
        elif "input" in name or "confirm" in name or "prompt" in name:
            categories["User Input"].append(method)
        elif "shared_data" in name:
            categories["Shared Data"].append(method)
        else:
            categories["Other"].append(method)

    # Remove empty categories
    return {k: v for k, v in categories.items() if v}


def main():
    """Main function."""
    api_file = Path(__file__).parent.parent / "src" / "yaft" / "core" / "api.py"
    methods = extract_method_info(api_file)

    print(f"Total public methods: {len(methods)}\n")

    categorized = categorize_methods(methods)

    for category, method_list in categorized.items():
        print(f"\n{'=' * 60}")
        print(f"{category} ({len(method_list)} methods)")
        print(f"{'=' * 60}")
        for method in method_list:
            print(f"\n  {method['signature']}")
            if method["returns"]:
                print(f"    Returns: {method['returns']}")
            if method["docstring"]:
                # First line of docstring
                first_line = method["docstring"].split("\n")[0].strip()
                print(f"    - {first_line}")


if __name__ == "__main__":
    main()
