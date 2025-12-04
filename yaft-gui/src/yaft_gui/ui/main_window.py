"""Main application window."""

from pathlib import Path
from typing import Optional
from PySide6.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QLabel,
    QLineEdit,
    QFileDialog,
    QCheckBox,
    QGroupBox,
    QMessageBox,
    QProgressBar,
)
from PySide6.QtCore import Qt, QProcess, Slot
from PySide6.QtGui import QFont

from yaft_gui.core.yaft_interface import YAFTInterface
from yaft_gui.ui.plugin_list import PluginListWidget
from yaft_gui.ui.output_viewer import OutputViewer


class YAFTMainWindow(QMainWindow):
    """Main application window for YAFT GUI."""

    def __init__(self):
        super().__init__()
        self.yaft_interface: Optional[YAFTInterface] = None
        self.process: Optional[QProcess] = None
        self._setup_ui()
        self._initialize_yaft()

    def _setup_ui(self):
        """Initialize UI components."""
        self.setWindowTitle("YAFT Forensic Analysis Tool - GUI")
        self.setMinimumSize(1000, 800)

        # Central widget
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setSpacing(10)

        # Header section
        header = self._create_header()
        main_layout.addWidget(header)

        # File selection section
        file_section = self._create_file_section()
        main_layout.addWidget(file_section)

        # Plugin selection section
        self.plugin_widget = PluginListWidget()
        main_layout.addWidget(self.plugin_widget)

        # Export options section
        export_section = self._create_export_section()
        main_layout.addWidget(export_section)

        # Output viewer
        self.output_viewer = OutputViewer()
        main_layout.addWidget(self.output_viewer, stretch=1)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        main_layout.addWidget(self.progress_bar)

        # Action buttons
        button_section = self._create_button_section()
        main_layout.addLayout(button_section)

        # Status bar
        self.statusBar().showMessage("Ready")

    def _create_header(self) -> QWidget:
        """Create header section with title and version."""
        header = QWidget()
        layout = QVBoxLayout(header)
        layout.setContentsMargins(10, 10, 10, 10)

        title = QLabel("YAFT Forensic Analysis Tool")
        title.setFont(QFont("Segoe UI", 16, QFont.Bold))
        title.setStyleSheet("color: #2c3e50;")
        layout.addWidget(title)

        subtitle = QLabel("Graphical User Interface for Plugin Execution")
        subtitle.setFont(QFont("Segoe UI", 10))
        subtitle.setStyleSheet("color: #7f8c8d;")
        layout.addWidget(subtitle)

        self.version_label = QLabel("YAFT Core: Not detected")
        self.version_label.setFont(QFont("Segoe UI", 9))
        self.version_label.setStyleSheet("color: #95a5a6;")
        layout.addWidget(self.version_label)

        return header

    def _create_file_section(self) -> QGroupBox:
        """Create file selection section."""
        group = QGroupBox("Extraction File")
        layout = QHBoxLayout(group)

        label = QLabel("ZIP File:")
        label.setMinimumWidth(80)
        layout.addWidget(label)

        self.zip_path_edit = QLineEdit()
        self.zip_path_edit.setPlaceholderText("Select forensic extraction ZIP file...")
        self.zip_path_edit.setReadOnly(True)
        layout.addWidget(self.zip_path_edit)

        self.browse_btn = QPushButton("Browse...")
        self.browse_btn.clicked.connect(self._browse_zip_file)
        self.browse_btn.setMinimumWidth(100)
        layout.addWidget(self.browse_btn)

        return group

    def _create_export_section(self) -> QGroupBox:
        """Create export options section."""
        group = QGroupBox("Export Options")
        layout = QHBoxLayout(group)

        self.html_export_check = QCheckBox("HTML Export")
        self.html_export_check.setToolTip("Generate HTML reports alongside markdown")
        layout.addWidget(self.html_export_check)

        self.pdf_export_check = QCheckBox("PDF Export")
        self.pdf_export_check.setToolTip("Generate PDF reports (requires WeasyPrint)")
        layout.addWidget(self.pdf_export_check)

        layout.addStretch()

        return group

    def _create_button_section(self) -> QHBoxLayout:
        """Create action button section."""
        layout = QHBoxLayout()
        layout.addStretch()

        self.refresh_plugins_btn = QPushButton("Refresh Plugins")
        self.refresh_plugins_btn.clicked.connect(self._load_plugins)
        self.refresh_plugins_btn.setMinimumWidth(120)
        layout.addWidget(self.refresh_plugins_btn)

        self.clear_output_btn = QPushButton("Clear Output")
        self.clear_output_btn.clicked.connect(self.output_viewer.clear)
        self.clear_output_btn.setMinimumWidth(120)
        layout.addWidget(self.clear_output_btn)

        self.execute_btn = QPushButton("Execute Analysis")
        self.execute_btn.clicked.connect(self._execute_analysis)
        self.execute_btn.setMinimumWidth(150)
        self.execute_btn.setStyleSheet(
            """
            QPushButton {
                background-color: #007bff;
                color: white;
                font-weight: bold;
                padding: 8px;
            }
            QPushButton:hover {
                background-color: #0056b3;
            }
            QPushButton:disabled {
                background-color: #6c757d;
            }
            """
        )
        layout.addWidget(self.execute_btn)

        self.stop_btn = QPushButton("Stop")
        self.stop_btn.clicked.connect(self._stop_execution)
        self.stop_btn.setEnabled(False)
        self.stop_btn.setMinimumWidth(100)
        self.stop_btn.setStyleSheet(
            """
            QPushButton {
                background-color: #dc3545;
                color: white;
                font-weight: bold;
                padding: 8px;
            }
            QPushButton:hover {
                background-color: #c82333;
            }
            QPushButton:disabled {
                background-color: #6c757d;
            }
            """
        )
        layout.addWidget(self.stop_btn)

        return layout

    def _initialize_yaft(self):
        """Initialize YAFT interface and load plugins."""
        try:
            self.yaft_interface = YAFTInterface()

            if not self.yaft_interface.is_available():
                QMessageBox.warning(
                    self,
                    "YAFT Not Found",
                    "YAFT executable not found or not working.\n\n"
                    "Please ensure yaft.exe is in the same directory as this GUI tool.",
                )
                self.statusBar().showMessage("YAFT executable not found")
                return

            # Get version
            try:
                version = self.yaft_interface.get_version()
                self.version_label.setText(f"YAFT Core: v{version}")
            except RuntimeError:
                self.version_label.setText("YAFT Core: Version unknown")

            # Load plugins
            self._load_plugins()

        except FileNotFoundError as e:
            QMessageBox.warning(
                self,
                "YAFT Not Found",
                f"Could not locate YAFT executable:\n\n{e}",
            )
            self.statusBar().showMessage("YAFT executable not found")

    def _load_plugins(self):
        """Load available plugins from YAFT."""
        if not self.yaft_interface:
            return

        self.statusBar().showMessage("Loading plugins...")

        try:
            plugins = self.yaft_interface.get_available_plugins()

            if not plugins:
                QMessageBox.information(
                    self,
                    "No Plugins",
                    "No plugins found. Please ensure YAFT has plugins installed.",
                )
                self.statusBar().showMessage("No plugins found")
                return

            self.plugin_widget.load_plugins(plugins)
            self.statusBar().showMessage(f"Loaded {len(plugins)} plugins")

        except RuntimeError as e:
            QMessageBox.critical(
                self,
                "Plugin Load Error",
                f"Failed to load plugins:\n\n{e}",
            )
            self.statusBar().showMessage("Failed to load plugins")

    @Slot()
    def _browse_zip_file(self):
        """Open file dialog to select ZIP extraction file."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Forensic Extraction ZIP File",
            "",
            "ZIP Files (*.zip);;All Files (*.*)",
        )

        if file_path:
            self.zip_path_edit.setText(file_path)
            self.statusBar().showMessage(f"Selected: {Path(file_path).name}")

    @Slot()
    def _execute_analysis(self):
        """Execute YAFT analysis with selected plugins."""
        # Validate inputs
        if not self.zip_path_edit.text():
            QMessageBox.warning(
                self,
                "No ZIP File",
                "Please select a forensic extraction ZIP file.",
            )
            return

        selected_plugins = self.plugin_widget.get_selected_plugins()
        if not selected_plugins:
            QMessageBox.warning(
                self,
                "No Plugins Selected",
                "Please select at least one plugin to execute.",
            )
            return

        # Validate ZIP file
        zip_path = self.zip_path_edit.text()
        if not self.yaft_interface.validate_zip_file(zip_path):
            QMessageBox.warning(
                self,
                "Invalid ZIP File",
                "The selected file is not a valid ZIP archive.",
            )
            return

        # Build command
        try:
            cmd = self.yaft_interface.build_command(
                zip_file=zip_path,
                plugins=selected_plugins,
                html_export=self.html_export_check.isChecked(),
                pdf_export=self.pdf_export_check.isChecked(),
            )
        except ValueError as e:
            QMessageBox.critical(
                self,
                "Command Build Error",
                f"Failed to build command:\n\n{e}",
            )
            return

        # Clear output and start execution
        self.output_viewer.clear()
        self.output_viewer.append_system_message(
            f"Executing: {' '.join(cmd)}", "info"
        )
        self.output_viewer.append_system_message("-" * 80, "info")

        # Setup process
        self.process = QProcess(self)
        self.process.readyReadStandardOutput.connect(self._handle_stdout)
        self.process.readyReadStandardError.connect(self._handle_stderr)
        self.process.finished.connect(self._process_finished)

        # Update UI state
        self.execute_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.browse_btn.setEnabled(False)
        self.refresh_plugins_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setMaximum(0)  # Indeterminate progress
        self.statusBar().showMessage("Executing analysis...")

        # Start process
        self.process.start(cmd[0], cmd[1:])

    @Slot()
    def _stop_execution(self):
        """Stop the running process."""
        if self.process and self.process.state() == QProcess.Running:
            reply = QMessageBox.question(
                self,
                "Stop Execution",
                "Are you sure you want to stop the current analysis?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )

            if reply == QMessageBox.Yes:
                self.process.kill()
                self.output_viewer.append_system_message(
                    "\nExecution stopped by user.", "warning"
                )

    @Slot()
    def _handle_stdout(self):
        """Handle stdout from YAFT process."""
        if self.process:
            data = self.process.readAllStandardOutput()
            text = bytes(data).decode("utf-8", errors="replace")
            self.output_viewer.append_stdout(text)

    @Slot()
    def _handle_stderr(self):
        """Handle stderr from YAFT process."""
        if self.process:
            data = self.process.readAllStandardError()
            text = bytes(data).decode("utf-8", errors="replace")
            self.output_viewer.append_stderr(text)

    @Slot(int, QProcess.ExitStatus)
    def _process_finished(self, exit_code: int, exit_status: QProcess.ExitStatus):
        """Handle process completion."""
        # Update UI state
        self.execute_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.browse_btn.setEnabled(True)
        self.refresh_plugins_btn.setEnabled(True)
        self.progress_bar.setVisible(False)

        # Show completion message
        if exit_status == QProcess.NormalExit and exit_code == 0:
            self.output_viewer.append_system_message(
                "\nAnalysis completed successfully.", "success"
            )
            self.statusBar().showMessage("Analysis completed successfully")
        elif exit_status == QProcess.CrashExit:
            self.output_viewer.append_system_message(
                "\nProcess crashed or was terminated.", "error"
            )
            self.statusBar().showMessage("Process terminated")
        else:
            self.output_viewer.append_system_message(
                f"\nProcess exited with code {exit_code}.", "error"
            )
            self.statusBar().showMessage(f"Process exited with code {exit_code}")

    def closeEvent(self, event):
        """Handle window close event."""
        if self.process and self.process.state() == QProcess.Running:
            reply = QMessageBox.question(
                self,
                "Close Application",
                "Analysis is still running. Are you sure you want to close?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )

            if reply == QMessageBox.Yes:
                self.process.kill()
                event.accept()
            else:
                event.ignore()
        else:
            event.accept()
