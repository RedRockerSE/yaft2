"""
YAFT Plugin Profile Editor

A standalone GUI application for creating and editing YAFT plugin profiles.
This tool allows users to visually select plugins and create TOML profile files
for use with the YAFT forensic analysis tool.

Usage:
    python profile_editor.py

Requirements:
    - Python 3.12+
    - tkinter (usually included with Python)
    - toml package (pip install toml)
"""

import os
import sys
import tkinter as tk
from tkinter import ttk, messagebox, filedialog, scrolledtext
from pathlib import Path
from typing import List, Dict, Optional
import importlib.util
import inspect


class PluginInfo:
    """Information about a discovered plugin."""

    def __init__(self, class_name: str, file_path: str, metadata: Optional[Dict] = None):
        self.class_name = class_name
        self.file_path = file_path
        self.metadata = metadata or {}
        self.description = metadata.get("description", "") if metadata else ""
        self.version = metadata.get("version", "") if metadata else ""
        self.author = metadata.get("author", "") if metadata else ""


class PluginDiscovery:
    """Discovers plugins from the plugins directory."""

    def __init__(self, plugins_dir: Path):
        self.plugins_dir = plugins_dir

    def discover_plugins(self) -> List[PluginInfo]:
        """Discover all plugins in the plugins directory."""
        plugins = []

        if not self.plugins_dir.exists():
            return plugins

        # Scan for Python files
        for py_file in self.plugins_dir.glob("*.py"):
            # Skip private files and __init__.py
            if py_file.name.startswith("_"):
                continue

            try:
                # Try to import and inspect the module
                plugin_info = self._inspect_plugin_file(py_file)
                if plugin_info:
                    plugins.append(plugin_info)
            except Exception as e:
                print(f"Warning: Could not inspect {py_file.name}: {e}")
                # Still add it as a basic plugin
                # Extract potential class name from filename
                class_name = self._guess_class_name(py_file.stem)
                plugins.append(PluginInfo(class_name, str(py_file)))

        return sorted(plugins, key=lambda p: p.class_name)

    def _inspect_plugin_file(self, file_path: Path) -> Optional[PluginInfo]:
        """Inspect a plugin file to extract class name and metadata."""
        try:
            # Read the file to find class definitions
            content = file_path.read_text(encoding='utf-8')

            # Simple parsing to find classes that might inherit from PluginBase
            class_name = None
            for line in content.split('\n'):
                line = line.strip()
                if line.startswith('class ') and 'PluginBase' in line:
                    # Extract class name
                    class_part = line.split('(')[0]
                    class_name = class_part.replace('class ', '').strip(':').strip()
                    break

            if class_name:
                # Try to extract metadata from docstring or comments
                metadata = self._extract_metadata(content, class_name)
                return PluginInfo(class_name, str(file_path), metadata)

        except Exception as e:
            print(f"Error inspecting {file_path}: {e}")

        return None

    def _guess_class_name(self, filename: str) -> str:
        """Guess plugin class name from filename."""
        # Convert snake_case to PascalCase and add Plugin suffix if not present
        parts = filename.split('_')
        class_name = ''.join(word.capitalize() for word in parts)
        if not class_name.endswith('Plugin'):
            class_name += 'Plugin'
        return class_name

    def _extract_metadata(self, content: str, class_name: str) -> Dict:
        """Extract metadata from plugin file content."""
        metadata = {}

        # Try to find docstring
        lines = content.split('\n')
        in_class = False
        docstring_start = False
        docstring_lines = []

        for i, line in enumerate(lines):
            if f'class {class_name}' in line:
                in_class = True
                continue

            if in_class and '"""' in line:
                if not docstring_start:
                    docstring_start = True
                    docstring_lines.append(line.split('"""')[1] if '"""' in line else '')
                else:
                    # End of docstring
                    docstring_lines.append(line.split('"""')[0] if '"""' in line else '')
                    break
            elif in_class and docstring_start:
                docstring_lines.append(line.strip())

        if docstring_lines:
            metadata['description'] = ' '.join(docstring_lines).strip()

        # Try to find version, author in metadata property
        for line in lines:
            if 'version=' in line and '"' in line:
                version = line.split('"')[1] if '"' in line else ''
                if version:
                    metadata['version'] = version
            if 'author=' in line and '"' in line:
                author = line.split('"')[1] if '"' in line else ''
                if author:
                    metadata['author'] = author

        return metadata


class ProfileEditorApp:
    """Main GUI application for editing plugin profiles."""

    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("YAFT Plugin Profile Editor")
        self.root.geometry("900x700")

        # Determine paths
        self.base_dir = Path(__file__).parent.parent.parent
        self.plugins_dir = self.base_dir / "plugins"
        self.profiles_dir = self.base_dir / "profiles"

        # Ensure profiles directory exists
        self.profiles_dir.mkdir(exist_ok=True)

        # Plugin discovery
        self.discovery = PluginDiscovery(self.plugins_dir)
        self.plugins: List[PluginInfo] = []
        self.selected_plugins: List[str] = []

        # Current profile data
        self.current_profile_name = ""
        self.current_profile_description = ""
        self.current_profile_path: Optional[Path] = None

        # Create UI
        self._create_ui()

        # Load plugins
        self._load_plugins()

    def _create_ui(self):
        """Create the user interface."""
        # Configure style
        style = ttk.Style()
        style.theme_use('clam')

        # Main container
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(2, weight=1)

        # Title
        title_label = ttk.Label(
            main_frame,
            text="YAFT Plugin Profile Editor",
            font=("Helvetica", 16, "bold")
        )
        title_label.grid(row=0, column=0, pady=(0, 10), sticky=tk.W)

        # Profile info section
        self._create_profile_info_section(main_frame)

        # Plugin selection section
        self._create_plugin_selection_section(main_frame)

        # Selected plugins section
        self._create_selected_plugins_section(main_frame)

        # Action buttons
        self._create_action_buttons(main_frame)

        # Status bar
        self.status_var = tk.StringVar(value="Ready")
        status_bar = ttk.Label(
            main_frame,
            textvariable=self.status_var,
            relief=tk.SUNKEN,
            anchor=tk.W
        )
        status_bar.grid(row=5, column=0, sticky=(tk.W, tk.E), pady=(10, 0))

    def _create_profile_info_section(self, parent):
        """Create profile information input section."""
        info_frame = ttk.LabelFrame(parent, text="Profile Information", padding="10")
        info_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        info_frame.columnconfigure(1, weight=1)

        # Profile name
        ttk.Label(info_frame, text="Profile Name:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.name_var = tk.StringVar()
        name_entry = ttk.Entry(info_frame, textvariable=self.name_var, width=40)
        name_entry.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=(10, 0), pady=5)

        # Profile description
        ttk.Label(info_frame, text="Description:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.description_var = tk.StringVar()
        description_entry = ttk.Entry(info_frame, textvariable=self.description_var, width=40)
        description_entry.grid(row=1, column=1, sticky=(tk.W, tk.E), padx=(10, 0), pady=5)

    def _create_plugin_selection_section(self, parent):
        """Create available plugins selection section."""
        selection_frame = ttk.LabelFrame(parent, text="Available Plugins", padding="10")
        selection_frame.grid(row=2, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        selection_frame.columnconfigure(0, weight=1)
        selection_frame.rowconfigure(0, weight=1)

        # Create treeview with scrollbar
        tree_frame = ttk.Frame(selection_frame)
        tree_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        tree_frame.columnconfigure(0, weight=1)
        tree_frame.rowconfigure(0, weight=1)

        # Scrollbars
        vsb = ttk.Scrollbar(tree_frame, orient="vertical")
        hsb = ttk.Scrollbar(tree_frame, orient="horizontal")

        # Treeview
        self.plugins_tree = ttk.Treeview(
            tree_frame,
            columns=("file", "description"),
            yscrollcommand=vsb.set,
            xscrollcommand=hsb.set,
            selectmode="extended"
        )

        vsb.config(command=self.plugins_tree.yview)
        hsb.config(command=self.plugins_tree.xview)

        # Configure columns
        self.plugins_tree.heading("#0", text="Plugin Class Name")
        self.plugins_tree.heading("file", text="File")
        self.plugins_tree.heading("description", text="Description")

        self.plugins_tree.column("#0", width=250, minwidth=150)
        self.plugins_tree.column("file", width=200, minwidth=100)
        self.plugins_tree.column("description", width=350, minwidth=200)

        # Grid layout
        self.plugins_tree.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        vsb.grid(row=0, column=1, sticky=(tk.N, tk.S))
        hsb.grid(row=1, column=0, sticky=(tk.W, tk.E))

        # Buttons for plugin management
        button_frame = ttk.Frame(selection_frame)
        button_frame.grid(row=1, column=0, sticky=tk.W, pady=(10, 0))

        ttk.Button(
            button_frame,
            text="Add Selected →",
            command=self._add_selected_plugins
        ).grid(row=0, column=0, padx=5)

        ttk.Button(
            button_frame,
            text="Add All →",
            command=self._add_all_plugins
        ).grid(row=0, column=1, padx=5)

        ttk.Button(
            button_frame,
            text="Refresh Plugin List",
            command=self._load_plugins
        ).grid(row=0, column=2, padx=5)

    def _create_selected_plugins_section(self, parent):
        """Create selected plugins list section."""
        selected_frame = ttk.LabelFrame(parent, text="Selected Plugins (Execution Order)", padding="10")
        selected_frame.grid(row=3, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        selected_frame.columnconfigure(0, weight=1)

        # Listbox with scrollbar
        list_frame = ttk.Frame(selected_frame)
        list_frame.grid(row=0, column=0, sticky=(tk.W, tk.E))
        list_frame.columnconfigure(0, weight=1)

        scrollbar = ttk.Scrollbar(list_frame, orient="vertical")
        self.selected_listbox = tk.Listbox(
            list_frame,
            height=8,
            yscrollcommand=scrollbar.set,
            selectmode=tk.SINGLE
        )
        scrollbar.config(command=self.selected_listbox.yview)

        self.selected_listbox.grid(row=0, column=0, sticky=(tk.W, tk.E))
        scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))

        # Buttons for list management
        button_frame = ttk.Frame(selected_frame)
        button_frame.grid(row=1, column=0, sticky=tk.W, pady=(10, 0))

        ttk.Button(
            button_frame,
            text="Move Up",
            command=self._move_up
        ).grid(row=0, column=0, padx=5)

        ttk.Button(
            button_frame,
            text="Move Down",
            command=self._move_down
        ).grid(row=0, column=1, padx=5)

        ttk.Button(
            button_frame,
            text="Remove",
            command=self._remove_selected
        ).grid(row=0, column=2, padx=5)

        ttk.Button(
            button_frame,
            text="Clear All",
            command=self._clear_all
        ).grid(row=0, column=3, padx=5)

    def _create_action_buttons(self, parent):
        """Create main action buttons."""
        button_frame = ttk.Frame(parent)
        button_frame.grid(row=4, column=0, sticky=(tk.W, tk.E), pady=(0, 10))

        ttk.Button(
            button_frame,
            text="New Profile",
            command=self._new_profile,
            width=15
        ).grid(row=0, column=0, padx=5)

        ttk.Button(
            button_frame,
            text="Load Profile...",
            command=self._load_profile,
            width=15
        ).grid(row=0, column=1, padx=5)

        ttk.Button(
            button_frame,
            text="Save Profile",
            command=self._save_profile,
            width=15
        ).grid(row=0, column=2, padx=5)

        ttk.Button(
            button_frame,
            text="Save As...",
            command=self._save_profile_as,
            width=15
        ).grid(row=0, column=3, padx=5)

        ttk.Button(
            button_frame,
            text="Exit",
            command=self.root.quit,
            width=15
        ).grid(row=0, column=4, padx=5)

    def _load_plugins(self):
        """Load and display available plugins."""
        self.status_var.set("Loading plugins...")
        self.root.update()

        # Clear existing items
        for item in self.plugins_tree.get_children():
            self.plugins_tree.delete(item)

        # Discover plugins
        self.plugins = self.discovery.discover_plugins()

        # Populate tree
        for plugin in self.plugins:
            filename = Path(plugin.file_path).name
            description = plugin.description[:100] + "..." if len(plugin.description) > 100 else plugin.description

            self.plugins_tree.insert(
                "",
                tk.END,
                text=plugin.class_name,
                values=(filename, description)
            )

        self.status_var.set(f"Loaded {len(self.plugins)} plugins from {self.plugins_dir}")

    def _add_selected_plugins(self):
        """Add selected plugins to the selected list."""
        selection = self.plugins_tree.selection()
        if not selection:
            messagebox.showwarning("No Selection", "Please select one or more plugins to add.")
            return

        for item in selection:
            class_name = self.plugins_tree.item(item, "text")
            if class_name not in self.selected_plugins:
                self.selected_plugins.append(class_name)
                self.selected_listbox.insert(tk.END, class_name)

        self.status_var.set(f"Added {len(selection)} plugin(s)")

    def _add_all_plugins(self):
        """Add all plugins to the selected list."""
        added = 0
        for plugin in self.plugins:
            if plugin.class_name not in self.selected_plugins:
                self.selected_plugins.append(plugin.class_name)
                self.selected_listbox.insert(tk.END, plugin.class_name)
                added += 1

        self.status_var.set(f"Added {added} plugin(s)")

    def _move_up(self):
        """Move selected plugin up in the list."""
        selection = self.selected_listbox.curselection()
        if not selection:
            return

        index = selection[0]
        if index == 0:
            return

        # Swap in list
        self.selected_plugins[index], self.selected_plugins[index - 1] = \
            self.selected_plugins[index - 1], self.selected_plugins[index]

        # Update listbox
        self._update_selected_listbox()
        self.selected_listbox.selection_set(index - 1)

    def _move_down(self):
        """Move selected plugin down in the list."""
        selection = self.selected_listbox.curselection()
        if not selection:
            return

        index = selection[0]
        if index >= len(self.selected_plugins) - 1:
            return

        # Swap in list
        self.selected_plugins[index], self.selected_plugins[index + 1] = \
            self.selected_plugins[index + 1], self.selected_plugins[index]

        # Update listbox
        self._update_selected_listbox()
        self.selected_listbox.selection_set(index + 1)

    def _remove_selected(self):
        """Remove selected plugin from the list."""
        selection = self.selected_listbox.curselection()
        if not selection:
            return

        index = selection[0]
        del self.selected_plugins[index]
        self._update_selected_listbox()

        self.status_var.set("Plugin removed")

    def _clear_all(self):
        """Clear all selected plugins."""
        if self.selected_plugins:
            if messagebox.askyesno("Clear All", "Remove all selected plugins?"):
                self.selected_plugins.clear()
                self._update_selected_listbox()
                self.status_var.set("All plugins cleared")

    def _update_selected_listbox(self):
        """Update the selected plugins listbox."""
        self.selected_listbox.delete(0, tk.END)
        for plugin in self.selected_plugins:
            self.selected_listbox.insert(tk.END, plugin)

    def _new_profile(self):
        """Create a new profile."""
        if self.selected_plugins or self.name_var.get() or self.description_var.get():
            if not messagebox.askyesno("New Profile", "Clear current profile and start new?"):
                return

        self.name_var.set("")
        self.description_var.set("")
        self.selected_plugins.clear()
        self._update_selected_listbox()
        self.current_profile_path = None

        self.status_var.set("New profile created")

    def _load_profile(self):
        """Load an existing profile."""
        filename = filedialog.askopenfilename(
            title="Load Profile",
            initialdir=self.profiles_dir,
            filetypes=[("TOML files", "*.toml"), ("All files", "*.*")]
        )

        if not filename:
            return

        try:
            import toml

            with open(filename, 'r', encoding='utf-8') as f:
                data = toml.load(f)

            # Validate profile structure
            if 'profile' not in data:
                messagebox.showerror("Invalid Profile", "Profile file must contain a [profile] section.")
                return

            profile = data['profile']

            # Load profile data
            self.name_var.set(profile.get('name', ''))
            self.description_var.set(profile.get('description', ''))

            self.selected_plugins = profile.get('plugins', [])
            self._update_selected_listbox()

            self.current_profile_path = Path(filename)

            self.status_var.set(f"Loaded profile: {Path(filename).name}")

        except Exception as e:
            messagebox.showerror("Error", f"Failed to load profile:\n{str(e)}")

    def _save_profile(self):
        """Save the current profile."""
        if self.current_profile_path:
            self._save_to_file(self.current_profile_path)
        else:
            self._save_profile_as()

    def _save_profile_as(self):
        """Save the current profile with a new name."""
        # Validate inputs
        name = self.name_var.get().strip()
        if not name:
            messagebox.showwarning("Missing Name", "Please enter a profile name.")
            return

        if not self.selected_plugins:
            messagebox.showwarning("No Plugins", "Please select at least one plugin.")
            return

        # Suggest filename from profile name
        suggested_name = name.lower().replace(' ', '_') + '.toml'

        filename = filedialog.asksaveasfilename(
            title="Save Profile As",
            initialdir=self.profiles_dir,
            initialfile=suggested_name,
            defaultextension=".toml",
            filetypes=[("TOML files", "*.toml"), ("All files", "*.*")]
        )

        if not filename:
            return

        self._save_to_file(Path(filename))

    def _save_to_file(self, filepath: Path):
        """Save profile to a file."""
        try:
            import toml

            # Build profile data
            profile_data = {
                'profile': {
                    'name': self.name_var.get().strip(),
                    'description': self.description_var.get().strip() or None,
                    'plugins': self.selected_plugins
                }
            }

            # Remove None values
            if profile_data['profile']['description'] is None:
                del profile_data['profile']['description']

            # Write to file
            with open(filepath, 'w', encoding='utf-8') as f:
                toml.dump(profile_data, f)

            self.current_profile_path = filepath
            self.status_var.set(f"Profile saved: {filepath.name}")
            messagebox.showinfo("Success", f"Profile saved successfully:\n{filepath}")

        except Exception as e:
            messagebox.showerror("Error", f"Failed to save profile:\n{str(e)}")


def main():
    """Main entry point for the application."""
    try:
        import toml
    except ImportError:
        print("Error: The 'toml' package is required.")
        print("Install it with: pip install toml")
        print("Or: uv pip install toml")
        sys.exit(1)

    root = tk.Tk()
    app = ProfileEditorApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
