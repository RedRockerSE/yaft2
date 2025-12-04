"""Real-time output viewer widget."""

from PySide6.QtWidgets import QTextEdit, QWidget, QVBoxLayout, QLabel
from PySide6.QtCore import Qt, Slot
from PySide6.QtGui import QFont, QTextCursor, QColor, QTextCharFormat


class OutputViewer(QWidget):
    """Widget for displaying real-time command output."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()
        self._setup_formats()

    def _setup_ui(self):
        """Initialize UI components."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Header
        header = QLabel("Execution Output:")
        header.setFont(QFont("Segoe UI", 10, QFont.Bold))
        layout.addWidget(header)

        # Text edit for output
        self.text_edit = QTextEdit()
        self.text_edit.setReadOnly(True)
        self.text_edit.setFont(QFont("Consolas", 9))  # Monospace font
        self.text_edit.setLineWrapMode(QTextEdit.WidgetWidth)
        layout.addWidget(self.text_edit)

    def _setup_formats(self):
        """Setup text formatting for different output types."""
        # Standard output (black)
        self.stdout_format = QTextCharFormat()
        self.stdout_format.setForeground(QColor("#000000"))

        # Error output (red)
        self.stderr_format = QTextCharFormat()
        self.stderr_format.setForeground(QColor("#dc3545"))

        # Success markers (green)
        self.success_format = QTextCharFormat()
        self.success_format.setForeground(QColor("#28a745"))

        # Warning markers (orange)
        self.warning_format = QTextCharFormat()
        self.warning_format.setForeground(QColor("#fd7e14"))

        # Info markers (blue)
        self.info_format = QTextCharFormat()
        self.info_format.setForeground(QColor("#007bff"))

    @Slot(str)
    def append_stdout(self, text: str):
        """
        Append stdout text with appropriate formatting.

        Args:
            text: Text to append
        """
        cursor = self.text_edit.textCursor()
        cursor.movePosition(QTextCursor.End)

        # Detect markers and apply formatting
        if "[OK]" in text or "Success" in text or "successfully" in text.lower():
            cursor.insertText(text, self.success_format)
        elif "[WARNING]" in text or "Warning:" in text:
            cursor.insertText(text, self.warning_format)
        elif "[INFO]" in text or "Info:" in text:
            cursor.insertText(text, self.info_format)
        else:
            cursor.insertText(text, self.stdout_format)

        self.text_edit.setTextCursor(cursor)
        self.text_edit.ensureCursorVisible()

    @Slot(str)
    def append_stderr(self, text: str):
        """
        Append stderr text in red.

        Args:
            text: Error text to append
        """
        cursor = self.text_edit.textCursor()
        cursor.movePosition(QTextCursor.End)
        cursor.insertText(text, self.stderr_format)
        self.text_edit.setTextCursor(cursor)
        self.text_edit.ensureCursorVisible()

    def append_system_message(self, text: str, message_type: str = "info"):
        """
        Append a system message with formatting.

        Args:
            text: Message text
            message_type: Type of message ('info', 'success', 'warning', 'error')
        """
        cursor = self.text_edit.textCursor()
        cursor.movePosition(QTextCursor.End)

        format_map = {
            "info": self.info_format,
            "success": self.success_format,
            "warning": self.warning_format,
            "error": self.stderr_format,
        }

        text_format = format_map.get(message_type, self.stdout_format)
        cursor.insertText(f"{text}\n", text_format)

        self.text_edit.setTextCursor(cursor)
        self.text_edit.ensureCursorVisible()

    def clear(self):
        """Clear all output text."""
        self.text_edit.clear()

    def get_text(self) -> str:
        """Get all output text."""
        return self.text_edit.toPlainText()

    def save_to_file(self, file_path: str):
        """
        Save output to file.

        Args:
            file_path: Path to save file
        """
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(self.get_text())
