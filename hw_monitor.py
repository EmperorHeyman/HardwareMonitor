import sys
import psutil
import os
import json
from PyQt5.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout,
                             QLabel, QGroupBox, QSizePolicy, QPushButton,
                             QDialog, QSlider, QCheckBox, QRadioButton,
                             QButtonGroup, QComboBox, QMessageBox, QScrollArea,
                             QSystemTrayIcon, QAction, QMenu, QStyle)
from PyQt5.QtCore import QTimer, Qt, pyqtSignal
from PyQt5.QtGui import QFont, QColor, QPalette, QIcon
import qdarktheme

# Attempt to import pynvml for NVIDIA GPU monitoring
try:
    from pynvml import (
        nvmlInit,
        nvmlShutdown,
        nvmlDeviceGetCount,
        nvmlDeviceGetHandleByIndex,
        nvmlDeviceGetName,
        nvmlDeviceGetUtilizationRates,
        nvmlDeviceGetTemperature,
        nvmlDeviceGetMemoryInfo,
        NVMLError,
        NVML_TEMPERATURE_GPU
    )
    nvmlInit()
    NVML_AVAILABLE = True
except NVMLError as error:
    print(f"NVIDIA NVML Error: {error}. NVIDIA GPU monitoring will be unavailable.")
    NVML_AVAILABLE = False
except ImportError:
    print("pynvml not found. Please install it using 'pip install pynvml'. NVIDIA GPU monitoring will be unavailable.")
    NVML_AVAILABLE = False

# Attempt to import WinTmp for CPU temperature monitoring
try:
    import WinTmp
    WINTMP_AVAILABLE = True
except ImportError:
    print("WinTmp not found. Please install it if you want CPU temperature monitoring. Using psutil for CPU temp (may show N/A).")
    WINTMP_AVAILABLE = False
except Exception as e:
    print(f"Error importing WinTmp: {e}. Using psutil for CPU temp (may show N/A).")
    WINTMP_AVAILABLE = False

# --- Settings file paths ---
APP_NAME = "R.A.P.L. GROUP Monitor"
SETTINGS_FILE_NAME = "settings.json"

def get_settings_path():
    """Returns the full path to the settings file."""
    if sys.platform == "win32":
        app_data_path = os.path.join(os.environ['APPDATA'], APP_NAME)
    elif sys.platform == "darwin": # macOS
        app_data_path = os.path.join(os.path.expanduser('~/Library/Application Support'), APP_NAME)
    else: # Linux/Unix
        app_data_path = os.path.join(os.path.expanduser('~/.config'), APP_NAME)
    
    os.makedirs(app_data_path, exist_ok=True)
    return os.path.join(app_data_path, SETTINGS_FILE_NAME)

class SettingsDialog(QDialog):
    refresh_interval_changed = pyqtSignal(int)
    opacity_changed = pyqtSignal(float)
    always_on_top_changed = pyqtSignal(bool)
    click_through_changed = pyqtSignal(bool)
    theme_changed = pyqtSignal(str)
    element_visibility_changed = pyqtSignal(dict)

    def __init__(self, parent=None, initial_settings=None):
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.setGeometry(200, 200, 450, 600)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)

        self.initial_settings = initial_settings if initial_settings else {}
        self.current_visibility_settings = self.initial_settings.get('visibility', {})

        self.init_ui()
        self.load_initial_settings()
        qdarktheme.setup_theme(self.initial_settings.get('theme', 'dark')) # Apply theme to settings dialog

    def init_ui(self):
        main_layout = QVBoxLayout()
        scroll_area = QScrollArea(self)
        scroll_area_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_area_widget)

        # General Settings Group
        general_group = QGroupBox("General Settings")
        general_layout = QVBoxLayout()

        # Refresh Interval
        refresh_label = QLabel("Refresh Interval:")
        general_layout.addWidget(refresh_label)
        self.refresh_group = QButtonGroup(self)
        self.fast_radio = QRadioButton("Fast (0.5s)")
        self.normal_radio = QRadioButton("Normal (1.5s)")
        self.slow_radio = QRadioButton("Slow (3s)")
        self.refresh_group.addButton(self.fast_radio, 500)
        self.refresh_group.addButton(self.normal_radio, 1500)
        self.refresh_group.addButton(self.slow_radio, 3000)
        general_layout.addWidget(self.fast_radio)
        general_layout.addWidget(self.normal_radio)
        general_layout.addWidget(self.slow_radio)
        
        # Always on Top
        self.always_on_top_checkbox = QCheckBox("Always on Top")
        general_layout.addWidget(self.always_on_top_checkbox)

        # Transparency/Opacity
        opacity_layout = QHBoxLayout()
        opacity_label = QLabel("Transparency:")
        self.opacity_value_label = QLabel("100%") # Label to display percentage
        opacity_layout.addWidget(opacity_label)
        opacity_layout.addWidget(self.opacity_value_label)
        general_layout.addLayout(opacity_layout)

        self.opacity_slider = QSlider(Qt.Horizontal)
        self.opacity_slider.setMinimum(10) # 10% opacity
        self.opacity_slider.setMaximum(100) # 100% opacity
        self.opacity_slider.setSingleStep(1)
        self.opacity_slider.setToolTip("Adjust window opacity (10% to 100%)")
        self.opacity_slider.valueChanged.connect(self.update_opacity_label) # Connect signal
        general_layout.addWidget(self.opacity_slider)

        # Click-through
        self.click_through_checkbox = QCheckBox("Enable Click-through (Warning: Disables dragging/button clicks)")
        self.click_through_checkbox.setToolTip("Makes the window transparent to mouse input. To interact again, use the System Tray Icon to open settings.")
        general_layout.addWidget(self.click_through_checkbox)
        self.click_through_checkbox.stateChanged.connect(self.warn_click_through)

        general_group.setLayout(general_layout)
        scroll_layout.addWidget(general_group)

        # Theme Settings Group
        theme_group = QGroupBox("Theme Settings")
        theme_layout = QVBoxLayout()
        theme_label = QLabel("Select Theme:")
        theme_layout.addWidget(theme_label)
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(qdarktheme.get_themes()) # Get available themes
        self.theme_combo.setToolTip("Select the application theme.")
        theme_layout.addWidget(self.theme_combo)
        theme_group.setLayout(theme_layout)
        scroll_layout.addWidget(theme_group)

        # Element Visibility Group
        visibility_group = QGroupBox("Element Visibility")
        visibility_layout = QVBoxLayout()
        self.visibility_checkboxes = {}

        # Main sections
        self.visibility_checkboxes['cpu_group'] = QCheckBox("Show CPU Section")
        self.visibility_checkboxes['ram_group'] = QCheckBox("Show RAM Section")
        self.visibility_checkboxes['gpu_groups'] = QCheckBox("Show GPU Section(s)")
        
        # Detailed CPU elements
        self.visibility_checkboxes['cpu_usage'] = QCheckBox("Show CPU Usage")
        self.visibility_checkboxes['cpu_temp'] = QCheckBox("Show CPU Temp")
        self.visibility_checkboxes['cpu_freq'] = QCheckBox("Show CPU Freq")

        # Detailed GPU elements
        self.visibility_checkboxes['gpu_usage'] = QCheckBox("Show GPU Usage")
        self.visibility_checkboxes['gpu_temp'] = QCheckBox("Show GPU Temp")
        self.visibility_checkboxes['gpu_vram'] = QCheckBox("Show GPU VRAM")

        for key, checkbox in self.visibility_checkboxes.items():
            visibility_layout.addWidget(checkbox)
            checkbox.setChecked(self.current_visibility_settings.get(key, True))

        visibility_group.setLayout(visibility_layout)
        scroll_layout.addWidget(visibility_group)

        # About Section
        about_group = QGroupBox("About")
        about_layout = QVBoxLayout()
        about_btn = QPushButton("About R.A.P.L. GROUP Monitor")
        about_btn.clicked.connect(self.show_about_dialog)
        about_layout.addWidget(about_btn)
        about_group.setLayout(about_layout)
        scroll_layout.addWidget(about_group)


        scroll_area.setWidgetResizable(True)
        scroll_area.setWidget(scroll_area_widget)
        main_layout.addWidget(scroll_area)


        # Action Buttons
        button_layout = QHBoxLayout()
        apply_button = QPushButton("Apply")
        cancel_button = QPushButton("Cancel")
        
        apply_button.clicked.connect(self.apply_settings)
        cancel_button.clicked.connect(self.reject)

        button_layout.addStretch(1)
        button_layout.addWidget(apply_button)
        button_layout.addWidget(cancel_button)
        main_layout.addLayout(button_layout)

        self.setLayout(main_layout)

    def update_opacity_label(self, value):
        self.opacity_value_label.setText(f"{value}%")

    def load_initial_settings(self):
        # Load refresh interval
        interval = self.initial_settings.get('refresh_interval', 1500)
        if interval == 500:
            self.fast_radio.setChecked(True)
        elif interval == 3000:
            self.slow_radio.setChecked(True)
        else:
            self.normal_radio.setChecked(True)

        # Load opacity
        opacity = int(self.initial_settings.get('opacity', 1.0) * 100)
        self.opacity_slider.setValue(opacity)
        self.update_opacity_label(opacity) # Update label immediately

        # Load Always on Top
        self.always_on_top_checkbox.setChecked(self.initial_settings.get('always_on_top', True))

        # Click-through is NOT loaded from settings to ensure interactivity on startup
        # self.click_through_checkbox.setChecked(self.initial_settings.get('click_through', False))

        # Load theme
        initial_theme = self.initial_settings.get('theme', 'dark')
        index = self.theme_combo.findText(initial_theme)
        if index != -1:
            self.theme_combo.setCurrentIndex(index)

    def warn_click_through(self, state):
        if state == Qt.Checked:
            QMessageBox.warning(self, "Click-through Enabled",
                "Enabling click-through makes the window transparent to mouse input.\n"
                "You WILL NOT be able to drag the window or click its buttons while this is active.\n"
                "To interact with the window again, you will need to open settings from the System Tray Icon."
            )

    def apply_settings(self):
        self.refresh_interval_changed.emit(self.refresh_group.checkedId())
        self.opacity_changed.emit(self.opacity_slider.value() / 100.0)
        self.always_on_top_changed.emit(self.always_on_top_checkbox.isChecked())
        self.click_through_changed.emit(self.click_through_checkbox.isChecked())
        self.theme_changed.emit(self.theme_combo.currentText())

        visibility_settings = {key: checkbox.isChecked() for key, checkbox in self.visibility_checkboxes.items()}
        self.element_visibility_changed.emit(visibility_settings)

        self.accept()

    def show_about_dialog(self):
        QMessageBox.about(self, "About R.A.P.L. GROUP Monitor",
            "<h3>R.A.P.L. GROUP System Monitor</h3>"
            "<p>Version: 1.0</p>"
            "<p>A simple, customizable system performance monitoring application.</p>"
            "<p>Developed by R.A.P.L. GROUP</p>"
            "<p>Special thanks to psutil and pynvml libraries.</p>"
        )


class SystemMonitorApp(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(APP_NAME)
        self.setGeometry(100, 100, 300, 400)

        # Default settings for initial load
        self.settings = {
            'refresh_interval': 1500,
            'opacity': 1.0,
            'always_on_top': True,
            'click_through': False,
            'theme': 'dark',
            'first_run_completed': False, # New flag for first-time message
            'visibility': {
                'cpu_group': True, 'ram_group': True, 'gpu_groups': True,
                'cpu_usage': True, 'cpu_temp': True, 'cpu_freq': True,
                'gpu_usage': True, 'gpu_temp': True, 'gpu_vram': True
            }
        }
        self.load_settings() # Load settings from file on startup

        # Set initial window flags based on settings
        self.setWindowFlags(
            Qt.Window | Qt.FramelessWindowHint | Qt.BypassWindowManagerHint
        )
        if self.settings['always_on_top']:
            self.setWindowFlags(self.windowFlags() | Qt.WindowStaysOnTopHint)
        else:
            self.setWindowFlags(self.windowFlags() & ~Qt.WindowStaysOnTopHint)
        self.setWindowOpacity(self.settings['opacity'])
        # Initial application of click-through setting:
        if self.settings['click_through']:
            self.setWindowFlags(self.windowFlags() | Qt.WindowTransparentForInput)
        else:
            self.setWindowFlags(self.windowFlags() & ~Qt.WindowTransparentForInput)


        self._start_pos = None

        self.init_ui()
        self.create_tray_icon()
        self.apply_visibility_settings(self.settings['visibility'])
        self.start_monitoring()

        # Apply initial button visibility based on click_through state
        self.update_button_visibility(self.settings['click_through'])

        # Show first-time run message if it hasn't been shown before
        if not self.settings.get('first_run_completed', False):
            self.show_first_run_message()


    def load_settings(self):
        settings_path = get_settings_path()
        if os.path.exists(settings_path):
            try:
                with open(settings_path, 'r') as f:
                    loaded_settings = json.load(f)
                    self.settings.update(loaded_settings)
                    # Ensure 'click_through' always starts as False on load for safety
                    self.settings['click_through'] = False
            except Exception as e:
                print(f"Error loading settings: {e}. Using default settings.")
        else:
            print("Settings file not found. Using default settings.")
            # If settings file not found, it's the first run, so set flag to False
            self.settings['first_run_completed'] = False 


    def save_settings(self):
        settings_path = get_settings_path()
        settings_to_save = self.settings.copy()
        if 'click_through' in settings_to_save:
            del settings_to_save['click_through']
        try:
            with open(settings_path, 'w') as f:
                json.dump(settings_to_save, f, indent=4)
        except Exception as e:
            print(f"Error saving settings: {e}")

    def create_tray_icon(self):
        self.tray_icon = QSystemTrayIcon(self)
        
        # Try to load a specific SVG icon from qdarktheme's resources.
        # This path works if qdarktheme is installed and its resources are accessible.
        # Otherwise, fall back to a standard QStyle icon.
        # Note: ":/qdarktheme/themes/light_gray/light_gear.svg" is a QRC path, which
        # typically works with Qt's resource system if qdarktheme resources are compiled.
        # For a more robust direct file access, you might need to extract the SVG from the package.
        # For simplicity here, sticking to QRC path for qdarktheme icons if they are set up.
        
        # Fallback to standard system icon if qdarktheme's SVG loading fails or path is invalid
        try:
            # Attempt to use qdarktheme's icon loading if available and working
            icon = QIcon(qdarktheme.load_svg("light_gear.svg"))
        except Exception:
            # Fallback to a standard Qt icon
            icon = QApplication.style().standardIcon(QStyle.SP_ComputerIcon)
            
        self.tray_icon.setIcon(icon)
        self.tray_icon.setToolTip(APP_NAME)

        menu = QMenu()
        open_settings_action = QAction("Open Settings", self)
        open_settings_action.triggered.connect(self.open_settings)
        menu.addAction(open_settings_action)

        exit_action = QAction("Exit", self)
        exit_action.triggered.connect(self.close)
        menu.addAction(exit_action)

        self.tray_icon.setContextMenu(menu)
        self.tray_icon.activated.connect(self.tray_icon_activated)
        self.tray_icon.show()

    def tray_icon_activated(self, reason):
        if reason == QSystemTrayIcon.Trigger or reason == QSystemTrayIcon.DoubleClick:
            if self.isHidden():
                self.showNormal()
                self.activateWindow()
            else:
                self.hide()

    def init_ui(self):
        self.main_layout = QVBoxLayout()
        self.main_layout.setContentsMargins(15, 15, 15, 15)
        self.main_layout.setSpacing(10)

        qdarktheme.setup_theme(self.settings['theme'])

        self.control_row_layout = QHBoxLayout()
        self.control_row_layout.setContentsMargins(0, 0, 0, 0)
        self.control_row_layout.setSpacing(5)
        
        self.control_row_layout.addStretch(1) 

        self.settings_btn = QPushButton("⚙")
        self.settings_btn.setFixedSize(25, 25)
        self.settings_btn.clicked.connect(self.open_settings)
        self.settings_btn.setToolTip("Open Settings")
        self.settings_btn.setStyleSheet("""
            QPushButton {
                background-color: #505050;
                border: none;
                border-radius: 5px;
                color: #F0F0F0;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #606060;
            }
            QPushButton:pressed {
                background-color: #404040;
            }
        """)
        self.control_row_layout.addWidget(self.settings_btn)

        self.minimize_btn = QPushButton("-")
        self.minimize_btn.setFixedSize(25, 25) 
        self.minimize_btn.clicked.connect(self.showMinimized)
        self.minimize_btn.setToolTip("Minimize Window")
        self.minimize_btn.setStyleSheet("""
            QPushButton {
                background-color: #505050;
                border: none;
                border-radius: 5px;
                color: #F0F0F0;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #606060;
            }
            QPushButton:pressed {
                background-color: #404040;
            }
        """)
        self.control_row_layout.addWidget(self.minimize_btn)

        self.close_btn = QPushButton("X")
        self.close_btn.setFixedSize(25, 25)
        self.close_btn.clicked.connect(self.close)
        self.close_btn.setToolTip("Close Application")
        self.close_btn.setStyleSheet("""
            QPushButton {
                background-color: #E74C3C; /* Red */
                border: none;
                border-radius: 5px;
                color: #F0F0F0;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #C0392B; /* Darker red */
            }
            QPushButton:pressed {
                background-color: #A93226; /* Even darker red */
            }
        """)
        self.control_row_layout.addWidget(self.close_btn)

        self.cpu_group = QGroupBox("CPU")
        self.cpu_layout = QVBoxLayout()
        self.cpu_layout.addLayout(self.control_row_layout)
        
        self.cpu_usage_label = QLabel("Usage: --%")
        self.cpu_temp_label = QLabel("Temp: --°C")
        self.cpu_freq_label = QLabel("Freq: -- MHz")
        self.set_font_and_color([self.cpu_usage_label, self.cpu_temp_label, self.cpu_freq_label])
        
        self.cpu_usage_label.setToolTip("Current CPU utilization across all cores.")
        self.cpu_temp_label.setToolTip("Current CPU package temperature.")
        self.cpu_freq_label.setToolTip("Current CPU frequency.")
        
        self.cpu_layout.addWidget(self.cpu_usage_label)
        self.cpu_layout.addWidget(self.cpu_temp_label)
        self.cpu_layout.addWidget(self.cpu_freq_label)
        self.cpu_group.setLayout(self.cpu_layout)
        self.main_layout.addWidget(self.cpu_group)

        self.ram_group = QGroupBox("RAM")
        self.ram_layout = QVBoxLayout()
        self.ram_usage_label = QLabel("Usage: -- GB / -- GB (--%)")
        self.set_font_and_color([self.ram_usage_label])
        self.ram_usage_label.setToolTip("Current RAM usage (used/total) and percentage.")
        self.ram_layout.addWidget(self.ram_usage_label)
        self.ram_group.setLayout(self.ram_layout)
        self.main_layout.addWidget(self.ram_group)

        self.gpu_groups = []
        self.gpu_labels = []

        if NVML_AVAILABLE:
            try:
                device_count = nvmlDeviceGetCount()
                for i in range(device_count):
                    handle = nvmlDeviceGetHandleByIndex(i)
                    gpu_name = nvmlDeviceGetName(handle) 
                    
                    gpu_group = QGroupBox(f"{gpu_name}")
                    gpu_layout = QVBoxLayout()
                    
                    gpu_usage_label = QLabel("Usage: --%")
                    gpu_temp_label = QLabel("Temp: --°C")
                    gpu_vram_label = QLabel("VRAM: -- MB / -- MB (--%)")
                    
                    self.set_font_and_color([gpu_usage_label, gpu_temp_label, gpu_vram_label])
                    
                    gpu_usage_label.setToolTip(f"Current {gpu_name} utilization.")
                    gpu_temp_label.setToolTip(f"Current {gpu_name} temperature.")
                    gpu_vram_label.setToolTip(f"Current {gpu_name} VRAM usage (used/total) and percentage.")

                    gpu_layout.addWidget(gpu_usage_label)
                    gpu_layout.addWidget(gpu_temp_label)
                    gpu_layout.addWidget(gpu_vram_label)
                    
                    gpu_group.setLayout(gpu_layout)
                    self.main_layout.addWidget(gpu_group)
                    
                    self.gpu_groups.append(gpu_group)
                    self.gpu_labels.append({
                        'usage': gpu_usage_label,
                        'temp': gpu_temp_label,
                        'vram': gpu_vram_label,
                        'handle': handle
                    })
            except NVMLError as error:
                print(f"Error getting NVML device info: {error}")
                self.main_layout.addWidget(QLabel("NVIDIA GPU info unavailable."))
        else:
            self.main_layout.addWidget(QLabel("NVIDIA GPU monitoring not available (pynvml/NVML error)."))

        self.rapl_label = QLabel("R.A.P.L. GROUP")
        self.rapl_label.setAlignment(Qt.AlignCenter)
        rapl_font = QFont("Inter", 7)
        self.rapl_label.setFont(rapl_font)
        self.rapl_label.setStyleSheet("color: #888888;")
        self.main_layout.addWidget(self.rapl_label)

        self.setLayout(self.main_layout)

    def set_dark_theme(self):
        pass 

    def set_font_and_color(self, labels):
        font = QFont("Inter", 10)
        for label in labels:
            label.setFont(font)
            label.setForegroundRole(QPalette.WindowText) 

    def start_monitoring(self):
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_stats)
        self.timer.start(self.settings['refresh_interval'])

    def update_stats(self):
        cpu_percent = psutil.cpu_percent(interval=None)
        self.cpu_usage_label.setText(f"Usage: {cpu_percent:.1f}%")

        cpu_temp = "N/A"
        if WINTMP_AVAILABLE:
            try:
                temp = WinTmp.CPU_Temp()
                if isinstance(temp, (int, float)):
                    cpu_temp = f"{temp:.0f}°C"
                else:
                    cpu_temp = "N/A (WinTmp - invalid data)"
            except Exception as e:
                cpu_temp = "Error (WinTmp)"
                print(f"Error getting CPU temp from WinTmp: {e}")
        self.cpu_temp_label.setText(f"Temp: {cpu_temp}")

        cpu_freq = psutil.cpu_freq()
        if cpu_freq:
            self.cpu_freq_label.setText(f"Freq: {cpu_freq.current:.0f} MHz")
        else:
            self.cpu_freq_label.setText("Freq: N/A")

        vm = psutil.virtual_memory()
        total_ram_gb = vm.total / (1024**3)
        used_ram_gb = vm.used / (1024**3)
        ram_percent = vm.percent
        self.ram_usage_label.setText(f"Usage: {used_ram_gb:.1f} GB / {total_ram_gb:.1f} GB ({ram_percent:.1f}%)")

        if NVML_AVAILABLE:
            for i, gpu_info in enumerate(self.gpu_labels):
                try:
                    handle = gpu_info['handle']
                    
                    util = nvmlDeviceGetUtilizationRates(handle)
                    gpu_info['usage'].setText(f"Usage: {util.gpu}%")

                    temp = nvmlDeviceGetTemperature(handle, NVML_TEMPERATURE_GPU)
                    gpu_info['temp'].setText(f"Temp: {temp}°C")

                    memory = nvmlDeviceGetMemoryInfo(handle)
                    total_vram_mb = memory.total / (1024**2)
                    used_vram_mb = memory.used / (1024**2)
                    vram_percent = (memory.used / memory.total) * 100 if memory.total > 0 else 0
                    gpu_info['vram'].setText(f"VRAM: {used_vram_mb:.0f} MB / {total_vram_mb:.0f} MB ({vram_percent:.1f}%)")

                except NVMLError as error:
                    gpu_name_from_group = self.gpu_groups[i].title()
                    print(f"Error updating {gpu_name_from_group} stats: {error}")
                    gpu_info['usage'].setText("Usage: Error")
                    gpu_info['temp'].setText("Temp: Error")
                    gpu_info['vram'].setText("VRAM: Error")
                except Exception as e:
                    gpu_name_from_group = self.gpu_groups[i].title()
                    print(f"Unexpected error updating {gpu_name_from_group} stats: {e}")

    def open_settings(self):
        settings_dialog = SettingsDialog(self, initial_settings=self.settings)
        settings_dialog.refresh_interval_changed.connect(self.set_refresh_interval)
        settings_dialog.opacity_changed.connect(self.set_window_opacity)
        settings_dialog.always_on_top_changed.connect(self.set_always_on_top)
        settings_dialog.click_through_changed.connect(self.set_click_through)
        settings_dialog.theme_changed.connect(self.set_theme)
        settings_dialog.element_visibility_changed.connect(self.apply_visibility_settings)

        settings_dialog.exec_()
        self.save_settings()

    def set_refresh_interval(self, interval_ms):
        self.settings['refresh_interval'] = interval_ms
        self.timer.setInterval(interval_ms)

    def set_window_opacity(self, opacity):
        self.settings['opacity'] = opacity
        self.setWindowOpacity(opacity)

    def set_always_on_top(self, enable):
        self.settings['always_on_top'] = enable
        current_flags = self.windowFlags()
        if enable:
            self.setWindowFlags(current_flags | Qt.WindowStaysOnTopHint)
        else:
            self.setWindowFlags(current_flags & ~Qt.WindowStaysOnTopHint)
        self.show()

    def set_click_through(self, enable):
        self.settings['click_through'] = enable
        current_flags = self.windowFlags()
        if enable:
            self.setWindowFlags(current_flags | Qt.WindowTransparentForInput)
            self._start_pos = None
        else:
            self.setWindowFlags(current_flags & ~Qt.WindowTransparentForInput)
        self.show()
        self.update_button_visibility(enable)


    def set_theme(self, theme_name):
        self.settings['theme'] = theme_name
        qdarktheme.setup_theme(theme_name)

    def apply_visibility_settings(self, visibility_dict):
        self.settings['visibility'] = visibility_dict

        self.cpu_group.setVisible(visibility_dict.get('cpu_group', True))
        self.ram_group.setVisible(visibility_dict.get('ram_group', True))
        
        show_gpu_section = visibility_dict.get('gpu_groups', True)
        for gpu_group in self.gpu_groups:
            gpu_group.setVisible(show_gpu_section)

        self.cpu_usage_label.setVisible(visibility_dict.get('cpu_usage', True))
        self.cpu_temp_label.setVisible(visibility_dict.get('cpu_temp', True))
        self.cpu_freq_label.setVisible(visibility_dict.get('cpu_freq', True))

        if show_gpu_section:
            for gpu_labels_dict in self.gpu_labels:
                gpu_labels_dict['usage'].setVisible(visibility_dict.get('gpu_usage', True))
                gpu_labels_dict['temp'].setVisible(visibility_dict.get('gpu_temp', True))
                gpu_labels_dict['vram'].setVisible(visibility_dict.get('gpu_vram', True))
        
        self.adjustSize()

    def update_button_visibility(self, hide_buttons):
        """Hides or shows the control buttons based on click-through state."""
        self.settings_btn.setVisible(not hide_buttons)
        self.minimize_btn.setVisible(not hide_buttons)
        self.close_btn.setVisible(not hide_buttons)

    def mousePressEvent(self, event):
        if not self.settings['click_through'] and event.button() == Qt.LeftButton:
            self._start_pos = event.globalPos() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if not self.settings['click_through'] and event.buttons() == Qt.LeftButton and self._start_pos is not None:
            self.move(event.globalPos() - self._start_pos)
            event.accept()

    def mouseReleaseEvent(self, event):
        if not self.settings['click_through']:
            self._start_pos = None
        event.accept()
    
    def closeEvent(self, event):
        self.save_settings()
        if NVML_AVAILABLE:
            try:
                nvmlShutdown()
            except NVMLError as error:
                print(f"Error shutting down NVML: {error}")
        self.tray_icon.hide()
        event.accept()

    def show_first_run_message(self):
        msg_box = QMessageBox()
        msg_box.setWindowTitle("Welcome to R.A.P.L. GROUP Monitor!")
        msg_box.setText(
            "Thank you for using R.A.P.L. GROUP Monitor!\n\n"
            "This is an open-source project. Anyone can contribute or modify it via GitHub.\n"
            "For full CPU temperature visibility, please ensure the application is run with administrator privileges.\n\n"
            "You can access settings and control the application via the system tray icon."
        )
        msg_box.setIcon(QMessageBox.Information)
        msg_box.setStandardButtons(QMessageBox.Ok)
        msg_box.exec_()
        
        self.settings['first_run_completed'] = True
        self.save_settings()


if __name__ == '__main__':
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)

    ex = SystemMonitorApp()
    ex.show()
    sys.exit(app.exec_())
