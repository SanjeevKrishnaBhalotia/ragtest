#!/usr/bin/env python3
"""
LocalRAG - A Secure, Local-First RAG Application
Main application entry point with PyQt6 GUI
"""

import sys
import os
from pathlib import Path

# Add app directory to Python path
app_dir = Path(__file__).parent
sys.path.insert(0, str(app_dir))

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QDir
from PyQt6.QtGui import QIcon

# Import main window
from ui.main_window import MainWindow
from utils.logger import setup_logger

def main():
    """Main application entry point"""
    # Set up logging
    logger = setup_logger()

    # Create QApplication
    app = QApplication(sys.argv)
    app.setApplicationName("LocalRAG")
    app.setApplicationVersion("1.0.0")
    app.setOrganizationName("LocalRAG")

    # Set application style
    app.setStyle("Fusion")

    try:
        # Create and show main window
        main_window = MainWindow()
        main_window.show()

        logger.info("LocalRAG application started successfully")

        # Start event loop
        return app.exec()

    except Exception as e:
        logger.error(f"Failed to start LocalRAG application: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
