R.A.P.L. GROUP System Monitor
=============================

Overview
--------

The R.A.P.L. GROUP System Monitor is a lightweight, customizable, and open-source application designed to display real-time performance statistics of your CPU, RAM, and NVIDIA GPUs. It runs as a small, frameless window that can be placed on any monitor, making it ideal for multi-monitor setups or as a subtle overlay.


![Screenshot 2025-06-20 175217](https://github.com/user-attachments/assets/94203ba4-e223-47c1-b736-f38cfd4f943f)
![Screenshot 2025-06-20 175134](https://github.com/user-attachments/assets/6e297f45-3fc4-4fe8-adf9-1e5c1c845e63)
![Screenshot 2025-06-20 182330](https://github.com/user-attachments/assets/34d52164-c9b1-4968-8318-2b39404b605f)


Features
--------

*   **Real-time Monitoring:** Displays CPU usage, temperature, frequency, RAM usage, and NVIDIA GPU usage, temperature, and VRAM.
    
*   **Customizable Visibility:** Toggle the visibility of entire sections (CPU, RAM, GPUs) or individual metrics (e.g., CPU frequency, GPU VRAM).
    
*   **Adjustable Refresh Rate:** Choose between Fast (0.5s), Normal (1.5s), and Slow (3s) update intervals.
    
*   **Window Customization:**
    
    *   **Frameless Design:** No standard window title bar.
        
    *   **Adjustable Transparency:** Control the window's opacity.
        
    *   **Always on Top:** Keep the monitor window visible above other applications.
        
    *   **Click-through Mode:** Make the window transparent to mouse clicks for seamless interaction with applications beneath it.
        
    *   **Draggable:** Easily reposition the window by dragging (when click-through is disabled).
        
*   **System Tray Integration:** Access settings and control the application (show/hide, exit) from a convenient system tray icon.
    
*   **Theme Support:** Utilizes pyqtdarktheme for various dark and light themes.
    
*   **Settings Persistence:** Your preferences are saved automatically to your user's AppData directory and loaded on startup.
    
*   **Open Source:** Free to use, modify, and distribute.
    

Installation
------------

1.  git clone [https://github.com/EmperorHeyman/HardwareMonitor/tree/main](https://github.com/EmperorHeyman/HardwareMonitor.git)
    
2.  pip install PyQt5 psutil pynvml pyqtdarktheme WinTmp
    
    *   PyQt5: For the graphical user interface.
        
    *   psutil: For cross-platform system information.
        
    *   pynvml: For NVIDIA GPU monitoring. (Requires NVIDIA GPU drivers installed.)
        
    *   pyqtdarktheme: For theme customization.
        
    *   WinTmp: For more reliable CPU temperature on Windows.
        

Usage
-----

1.  python hw\_monitor.py
    
2.  **Administrator Privileges (for CPU Temp):**For accurate CPU temperature readings, it is recommended to run the application with administrator privileges. Right-click on your hw\_monitor.py file (or its shortcut) and select "Run as administrator."
    
3.  **Positioning the Window:**Drag the frameless window to your desired position on any monitor (ensure "Enable Click-through" is _disabled_ in settings if you want to drag it).
    
4.  **Accessing Settings:**
    
    *   Click the **⚙ (gear) icon** in the top-right of the application window.
        
    *   **Right-click** on the **system tray icon** (looks like a gear) and select "Open Settings".
        
    *   **Double-click** the **system tray icon**.
        
5.  **Click-through Mode:**If you enable "Click-through" in the settings, the application window will become non-interactive to mouse clicks. You _must_ use the system tray icon to open settings or close the app when this mode is active.
    

Contributing
------------

Contributions are welcome! If you have ideas for new features, improvements, or bug fixes, feel free to fork the repository on GitHub and submit a pull request.


License
-------

This project is released under a permissive open-source license. Please refer to the LICENSE.md file for details.

**R.A.P.L. GROUP**

### Why I've made This Software
I was looking for something not demanding, light, and modular that I could just stick on my 3rd monitor and leave it there... I didn't find anything that fit my needs, so I made this.
