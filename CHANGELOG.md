### Changelog - Version 1.3

This update introduces bug fixes and new features.


### Added

- Added a new feature, app will now remember its position on close, when opened again it would go to that position again.

### Changed

- Change the exe to require elevation (Needed for CPU temp.).
### Fixed
- Fixed a bug where start with system would not work.
- Fixed a bug where on start the app would load with default size and not resize.




### Changelog - Version 1.2

This update introduces significant new functionality, a major code refactor for improved maintainability, and several user experience enhancements.

#### Features

*   **Run on Startup**: A new option has been added to the "General Settings" tab to allow the application to run automatically when Windows starts.
    
    *   This feature uses the Windows Task Scheduler to create a task that runs the application with the highest privileges, ensuring all monitoring features (like CPU temperature) work correctly.
        
    *   When enabled for the first time, the application will copy itself to a permanent location in C:\\Program Files\\R.A.P.L. GROUP Monitor\\ and will seamlessly restart from the new location.
        

#### Refactoring

*   **Code Modularity**: The entire application has been refactored from a single script into a modular structure to improve organization and readability. The new file structure is:
    
    *   main.py: The main entry point for the application.
        
    *   main\_window.py: Contains the logic and UI for the main monitor window.
        
    *   settings\_dialog.py: Contains the logic and UI for the settings window.
        
    *   utils.py: Includes helper functions like checking for admin rights.
        
    *   config.py: Stores application-wide constants like the name and version.
        
    *   icon.py: Stores the Base64-encoded application icon.
        

#### UI/UX Improvements

*   **Icon Consistency**: The application icon is now correctly applied to the main window, the settings dialog, all message boxes, and the system tray, providing a consistent look and feel, especially for the packaged .exe file.
    
*   **Cleaner Main Window**: The "R.A.P.L. GROUP" branding has been moved from the main UI into the "About" section within the settings dialog for a cleaner interface.