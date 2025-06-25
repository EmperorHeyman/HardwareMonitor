# main.py
"""
The main entry point for the R.A.P.L. GROUP Monitor application.
This script initializes the QApplication and the main window.
"""

import sys
from PyQt5.QtWidgets import QApplication

# Import the main window class from its file
from ui.main_window import SystemMonitorApp

if __name__ == '__main__':
    # Create the application instance
    app = QApplication(sys.argv)
    
    # Setting this to False allows the app to keep running in the system tray
    # when the main window is hidden or closed. The app is quit via the tray icon menu.
    app.setQuitOnLastWindowClosed(False)

    # Create an instance of our main application window
    monitor_app = SystemMonitorApp()
    
    # Show the main window
    monitor_app.show()

    # Start the Qt event loop and handle the exit code
    sys.exit(app.exec_())
