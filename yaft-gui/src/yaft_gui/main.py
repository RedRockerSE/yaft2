"""Main entry point for YAFT GUI application."""

import sys
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt

from yaft_gui.ui.main_window import YAFTMainWindow


def main():
    """Run YAFT GUI application."""
    # Enable high DPI scaling
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps)

    # Create application
    app = QApplication(sys.argv)
    app.setApplicationName("YAFT GUI")
    app.setOrganizationName("YAFT")
    app.setApplicationVersion("1.0.0")

    # Set application style
    app.setStyle("Fusion")

    # Create and show main window
    window = YAFTMainWindow()
    window.show()

    # Run application
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
