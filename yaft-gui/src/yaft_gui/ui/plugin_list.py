"""Plugin selection widget."""

from typing import List, Dict
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QLabel,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont


class PluginListWidget(QWidget):
    """Widget for selecting YAFT plugins with checkboxes."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        """Initialize UI components."""
        layout = QVBoxLayout(self)

        # Header
        header = QLabel("Select Plugins to Execute:")
        header.setFont(QFont("Segoe UI", 10, QFont.Bold))
        layout.addWidget(header)

        # List widget with checkboxes
        self.list_widget = QListWidget()
        self.list_widget.setAlternatingRowColors(True)
        layout.addWidget(self.list_widget)

        # Status label
        self.status_label = QLabel("No plugins loaded")
        self.status_label.setStyleSheet("color: #666; font-size: 9pt;")
        layout.addWidget(self.status_label)

        # Select all / Deselect all buttons
        button_layout = QHBoxLayout()

        self.select_all_btn = QPushButton("Select All")
        self.select_all_btn.clicked.connect(self.select_all)
        button_layout.addWidget(self.select_all_btn)

        self.deselect_all_btn = QPushButton("Deselect All")
        self.deselect_all_btn.clicked.connect(self.deselect_all)
        button_layout.addWidget(self.deselect_all_btn)

        button_layout.addStretch()
        layout.addLayout(button_layout)

    def add_plugin(self, name: str, version: str, description: str):
        """
        Add plugin to the list with checkbox.

        Args:
            name: Plugin class name
            version: Plugin version
            description: Plugin description
        """
        display_text = f"{name} (v{version})\n  {description}"
        item = QListWidgetItem(display_text)
        item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
        item.setCheckState(Qt.Unchecked)
        item.setData(Qt.UserRole, name)  # Store plugin class name
        self.list_widget.addItem(item)

        self._update_status()

    def load_plugins(self, plugins: List[Dict[str, str]]):
        """
        Load multiple plugins into the list.

        Args:
            plugins: List of plugin dictionaries with 'name', 'version', 'description'
        """
        self.list_widget.clear()

        for plugin in plugins:
            self.add_plugin(
                name=plugin["name"],
                version=plugin["version"],
                description=plugin["description"],
            )

        self._update_status()

    def get_selected_plugins(self) -> List[str]:
        """
        Get list of selected plugin names.

        Returns:
            List of plugin class names that are checked
        """
        selected = []
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            if item.checkState() == Qt.Checked:
                selected.append(item.data(Qt.UserRole))
        return selected

    def select_all(self):
        """Check all plugins in the list."""
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            item.setCheckState(Qt.Checked)
        self._update_status()

    def deselect_all(self):
        """Uncheck all plugins in the list."""
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            item.setCheckState(Qt.Unchecked)
        self._update_status()

    def get_plugin_count(self) -> int:
        """Get total number of plugins in the list."""
        return self.list_widget.count()

    def get_selected_count(self) -> int:
        """Get number of selected plugins."""
        return len(self.get_selected_plugins())

    def _update_status(self):
        """Update status label with plugin counts."""
        total = self.get_plugin_count()
        selected = self.get_selected_count()

        if total == 0:
            self.status_label.setText("No plugins loaded")
        else:
            self.status_label.setText(f"{selected} of {total} plugins selected")

    def clear(self):
        """Clear all plugins from the list."""
        self.list_widget.clear()
        self._update_status()
