# utils.py
"""
Contains helper functions used across the application, such as checking for
admin rights and finding the path for the settings file.
"""
import os
import sys
import ctypes
import subprocess
from config import TASK_NAME, APP_NAME, SETTINGS_FILE_NAME

def is_admin():
    """Check if the script is running with administrative privileges."""
    # This is specific to Windows
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

def get_settings_path():
    """Returns the full, platform-independent path to the settings file."""
    if sys.platform == "win32":
        # Use APPDATA directory on Windows
        app_data_path = os.path.join(os.environ['APPDATA'], APP_NAME)
    elif sys.platform == "darwin": # macOS
        # Use Library/Application Support on macOS
        app_data_path = os.path.join(os.path.expanduser('~/Library/Application Support'), APP_NAME)
    else: # Linux/Unix
        # Use .config directory on Linux
        app_data_path = os.path.join(os.path.expanduser('~/.config'), APP_NAME)
    
    # Ensure the directory exists
    os.makedirs(app_data_path, exist_ok=True)
    return os.path.join(app_data_path, SETTINGS_FILE_NAME)

def check_startup_task():
    """Check if the startup task exists in Windows Task Scheduler."""
    if sys.platform != "win32":
        return False
    try:
        # The 'startupinfo' part hides the console window that would otherwise pop up.
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.wShowWindow = subprocess.SW_HIDE
        # This command will throw an error if the task doesn't exist, which is caught below.
        subprocess.check_output(
            f'schtasks /query /tn "{TASK_NAME}"', 
            stderr=subprocess.STDOUT, 
            shell=True,
            startupinfo=startupinfo
        )
        return True
    except subprocess.CalledProcessError:
        return False
