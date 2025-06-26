# main_window.py
"""
Defines the main application window class, SystemMonitorApp.
This class is responsible for the main UI, data monitoring, and event handling.
"""
import sys
import os
import json
import psutil
import subprocess
import shutil
import base64

from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QGroupBox, 
                             QPushButton, QMessageBox, QSystemTrayIcon, QAction, 
                             QMenu, QApplication)
from PyQt5.QtCore import QTimer, Qt
from PyQt5.QtGui import QFont, QPalette, QIcon, QPixmap
import qdarktheme

# Local imports from other project files
from ui.settings_dialog import SettingsDialog
from utils import is_admin, get_settings_path
from config import APP_NAME, TASK_NAME
from ui.icon import BASE64_APP_ICON_DATA

# --- Hardware Monitoring Imports ---

# Attempt to import pynvml for NVIDIA GPU monitoring
try:
    from pynvml import (nvmlInit, nvmlShutdown, nvmlDeviceGetCount, 
                        nvmlDeviceGetHandleByIndex, nvmlDeviceGetName, 
                        nvmlDeviceGetUtilizationRates, nvmlDeviceGetTemperature, 
                        nvmlDeviceGetMemoryInfo, NVMLError, NVML_TEMPERATURE_GPU)
    nvmlInit()
    NVML_AVAILABLE = True
except (ImportError, NVMLError) as e:
    print(f"NVIDIA (pynvml) Error: {e}. GPU monitoring will be unavailable.")
    NVML_AVAILABLE = False

# Attempt to import WinTmp for CPU temperature on Windows
try:
    import WinTmp
    WINTMP_AVAILABLE = True
except ImportError:
    print("WinTmp not found. CPU temperature monitoring may be unavailable on Windows.")
    WINTMP_AVAILABLE = False


class SystemMonitorApp(QWidget):
    def __init__(self):
        super().__init__()
        
        # --- Set Application Icon ---
        app_icon_pixmap = QPixmap()
        app_icon_pixmap.loadFromData(base64.b64decode(BASE64_APP_ICON_DATA))
        self.app_icon = QIcon(app_icon_pixmap)
        self.setWindowIcon(self.app_icon)

        self.setWindowTitle(APP_NAME)
        self.setGeometry(100, 100, 300, 400)

        # Default settings
        self.settings = {
            'refresh_interval': 1500, 'opacity': 1.0, 'always_on_top': True,
            'click_through': False, 'theme': 'dark', 'first_run_completed': False,
            'window_pos_x': None, 'window_pos_y': None,
            'visibility': { 
                'cpu_group': True, 'ram_group': True, 'gpu_groups': True,
                'cpu_usage': True, 'cpu_temp': True, 'cpu_freq': True,
                'gpu_usage': True, 'gpu_temp': True, 'gpu_vram': True
            }
        }
        self.load_settings()

        # Restore window position if available from settings
        pos_x = self.settings.get('window_pos_x')
        pos_y = self.settings.get('window_pos_y')
        if pos_x is not None and pos_y is not None:
            self.move(pos_x, pos_y)

        # For window dragging
        self._start_pos = None

        # --- CORRECT INITIALIZATION ORDER ---
        # 1. Initialize the UI elements first.
        self.init_ui()

        # 2. Now apply settings to the created UI and window.
        self.setWindowFlags(Qt.Window | Qt.FramelessWindowHint | Qt.BypassWindowManagerHint)
        self.update_always_on_top(self.settings['always_on_top'])
        self.setWindowOpacity(self.settings['opacity'])
        self.update_click_through(self.settings['click_through'])
        self.apply_visibility_settings(self.settings['visibility'])
        self.adjustSize()

        # 3. Set up the rest of the application components.
        self.create_tray_icon()
        self.start_monitoring()

        # 4. Show first-run message if needed.
        if not self.settings.get('first_run_completed', False):
            self.show_first_run_message()

    def init_ui(self):
        self.main_layout = QVBoxLayout()
        self.main_layout.setContentsMargins(15, 15, 15, 15)
        self.main_layout.setSpacing(10)
        qdarktheme.setup_theme(self.settings['theme'])

        # --- Control Buttons ---
        self.control_row_layout = QHBoxLayout()
        self.control_row_layout.setContentsMargins(0, 0, 0, 0)
        self.control_row_layout.addStretch(1)
        
        button_style = """
            QPushButton { background-color: #505050; border: none; border-radius: 5px; color: #F0F0F0; font-weight: bold; }
            QPushButton:hover { background-color: #606060; }
            QPushButton:pressed { background-color: #404040; }
        """
        self.settings_btn = QPushButton("⚙", clicked=self.open_settings, toolTip="Open Settings")
        self.settings_btn.setFixedSize(25, 25)
        self.settings_btn.setStyleSheet(button_style)
        self.control_row_layout.addWidget(self.settings_btn)

        self.minimize_btn = QPushButton("-", clicked=self.showMinimized, toolTip="Minimize Window")
        self.minimize_btn.setFixedSize(25, 25)
        self.minimize_btn.setStyleSheet(button_style)
        self.control_row_layout.addWidget(self.minimize_btn)

        self.close_btn = QPushButton("X", clicked=QApplication.instance().quit, toolTip="Close Application")
        self.close_btn.setFixedSize(25, 25)
        self.close_btn.setStyleSheet(button_style.replace("#505050", "#E74C3C").replace("#606060", "#C0392B").replace("#404040", "#A93226"))
        self.control_row_layout.addWidget(self.close_btn)
        
        # --- CPU Section ---
        self.cpu_group = QGroupBox("CPU")
        self.cpu_layout = QVBoxLayout()
        self.cpu_layout.addLayout(self.control_row_layout)
        self.cpu_usage_label = QLabel("Usage: --%", toolTip="Current CPU utilization")
        self.cpu_temp_label = QLabel("Temp: --°C", toolTip="Current CPU temperature")
        self.cpu_freq_label = QLabel("Freq: -- MHz", toolTip="Current CPU frequency")
        self.set_font_and_color([self.cpu_usage_label, self.cpu_temp_label, self.cpu_freq_label])
        self.cpu_layout.addWidget(self.cpu_usage_label)
        self.cpu_layout.addWidget(self.cpu_temp_label)
        self.cpu_layout.addWidget(self.cpu_freq_label)
        self.cpu_group.setLayout(self.cpu_layout)
        self.main_layout.addWidget(self.cpu_group)

        # --- RAM Section ---
        self.ram_group = QGroupBox("RAM")
        self.ram_layout = QVBoxLayout()
        self.ram_usage_label = QLabel("Usage: -- GB / -- GB (--%)", toolTip="Current RAM usage")
        self.set_font_and_color([self.ram_usage_label])
        self.ram_layout.addWidget(self.ram_usage_label)
        self.ram_group.setLayout(self.ram_layout)
        self.main_layout.addWidget(self.ram_group)

        # --- GPU Section(s) ---
        self.gpu_groups = []
        self.gpu_labels = []
        if NVML_AVAILABLE:
            try:
                for i in range(nvmlDeviceGetCount()):
                    handle = nvmlDeviceGetHandleByIndex(i)
                    name = nvmlDeviceGetName(handle)
                    gpu_group = QGroupBox(f"{name}")
                    gpu_layout = QVBoxLayout()
                    usage = QLabel("Usage: --%", toolTip=f"{name} utilization")
                    temp = QLabel("Temp: --°C", toolTip=f"{name} temperature")
                    vram = QLabel("VRAM: -- MB / -- MB (--%)", toolTip=f"{name} VRAM usage")
                    self.set_font_and_color([usage, temp, vram])
                    gpu_layout.addWidget(usage)
                    gpu_layout.addWidget(temp)
                    gpu_layout.addWidget(vram)
                    gpu_group.setLayout(gpu_layout)
                    self.main_layout.addWidget(gpu_group)
                    self.gpu_groups.append(gpu_group)
                    self.gpu_labels.append({'usage': usage, 'temp': temp, 'vram': vram, 'handle': handle})
            except NVMLError as e:
                print(f"Error initializing GPU sections: {e}")
                self.main_layout.addWidget(QLabel("NVIDIA GPU info unavailable."))
        
        self.main_layout.addStretch(1)
        self.setLayout(self.main_layout)

    def set_font_and_color(self, labels):
        font = QFont("Inter", 10)
        for label in labels:
            label.setFont(font)
            label.setForegroundRole(QPalette.WindowText)

    # --- Settings and Core Logic ---

    def load_settings(self):
        settings_path = get_settings_path()
        if os.path.exists(settings_path):
            try:
                with open(settings_path, 'r') as f:
                    loaded_settings = json.load(f)
                    self.settings.update(loaded_settings)
                    # Safety: Always start non-interactive
                    self.settings['click_through'] = False 
            except json.JSONDecodeError as e:
                print(f"Error loading settings: {e}. Using defaults.")
        else:
            self.settings['first_run_completed'] = False

    def save_settings(self,move =False):
        settings_path = get_settings_path()
        settings_to_save = self.settings.copy()
        # Don't save click-through state to avoid starting in an uninteractive mode
        if 'click_through' in settings_to_save and move == False:
            del settings_to_save['click_through']
        try:
            with open(settings_path, 'w') as f:
                json.dump(settings_to_save, f, indent=4)
        except Exception as e:
            print(f"Error saving settings: {e}")

    def open_settings(self):
        dialog = SettingsDialog(self, initial_settings=self.settings)
        # Connect signals from the dialog to handler methods in this class
        dialog.refresh_interval_changed.connect(self.set_refresh_interval)
        dialog.opacity_changed.connect(self.setWindowOpacity)
        dialog.always_on_top_changed.connect(self.update_always_on_top)
        dialog.click_through_changed.connect(self.update_click_through)
        dialog.theme_changed.connect(self.set_theme)
        dialog.element_visibility_changed.connect(self.apply_visibility_settings)
        if sys.platform == "win32":
            dialog.startup_changed.connect(self.set_startup)
        dialog.exec_()
        self.save_settings()

    def start_monitoring(self):
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_stats)
        self.timer.start(self.settings['refresh_interval'])
        self.update_stats() # Initial update

    # --- System Tray Icon ---

    def create_tray_icon(self):
        self.tray_icon = QSystemTrayIcon(self)
        self.tray_icon.setIcon(self.app_icon)
        self.tray_icon.setToolTip(APP_NAME)
        menu = QMenu()
        menu.addAction("Open Settings", self.open_settings)
        menu.addAction("Exit", QApplication.instance().quit)
        self.tray_icon.setContextMenu(menu)
        self.tray_icon.activated.connect(self.tray_icon_activated)
        self.tray_icon.show()

    def tray_icon_activated(self, reason):
        if reason in (QSystemTrayIcon.Trigger, QSystemTrayIcon.DoubleClick):
            if self.isHidden():
                self.showNormal()
                self.activateWindow()
            else:
                self.hide()

    # --- Stats Update ---

    def update_stats(self):
        self.cpu_usage_label.setText(f"Usage: {psutil.cpu_percent(interval=None):.1f}%")
        
        cpu_temp_text = "N/A"
        if WINTMP_AVAILABLE:
            try:
                temp = WinTmp.CPU_Temp()
                if isinstance(temp, (int, float)):
                    cpu_temp_text = f"{temp:.0f}°C"
            except Exception as e:
                print(f"WinTmp Error: {e}")
        self.cpu_temp_label.setText(f"Temp: {cpu_temp_text}")

        cpu_freq = psutil.cpu_freq()
        self.cpu_freq_label.setText(f"Freq: {cpu_freq.current:.0f} MHz" if cpu_freq else "Freq: N/A")

        vm = psutil.virtual_memory()
        self.ram_usage_label.setText(f"Usage: {vm.used/1e9:.1f} GB / {vm.total/1e9:.1f} GB ({vm.percent:.1f}%)")

        if NVML_AVAILABLE:
            for gpu in self.gpu_labels:
                try:
                    handle = gpu['handle']
                    util = nvmlDeviceGetUtilizationRates(handle)
                    gpu['usage'].setText(f"Usage: {util.gpu}%")
                    temp = nvmlDeviceGetTemperature(handle, NVML_TEMPERATURE_GPU)
                    gpu['temp'].setText(f"Temp: {temp}°C")
                    mem = nvmlDeviceGetMemoryInfo(handle)
                    gpu['vram'].setText(f"VRAM: {mem.used/1e6:.0f} MB / {mem.total/1e6:.0f} MB ({mem.used/mem.total*100:.1f}%)")
                except NVMLError as e:
                    print(f"NVML stats update error: {e}")
                    for label in gpu.values():
                        if isinstance(label, QLabel): label.setText("Error")

    # --- Settings Handlers ---

    def set_refresh_interval(self, interval_ms):
        self.settings['refresh_interval'] = interval_ms
        self.timer.setInterval(interval_ms)

    def set_theme(self, theme_name):
        self.settings['theme'] = theme_name
        qdarktheme.setup_theme(theme_name)

    def update_always_on_top(self, enable):
        self.settings['always_on_top'] = enable
        flags = self.windowFlags()
        if enable:
            self.setWindowFlags(flags | Qt.WindowStaysOnTopHint)
        else:
            self.setWindowFlags(flags & ~Qt.WindowStaysOnTopHint)
        self.show()

    def update_click_through(self, enable):
        self.settings['click_through'] = enable
        flags = self.windowFlags()
        if enable:
            self.setWindowFlags(flags | Qt.WindowTransparentForInput)
            self._start_pos = None
        else:
            self.setWindowFlags(flags & ~Qt.WindowTransparentForInput)
        self.show()
        self.update_button_visibility(enable)
        
    def apply_visibility_settings(self, visibility):
        self.settings['visibility'] = visibility
        self.cpu_group.setVisible(visibility.get('cpu_group', True))
        self.ram_group.setVisible(visibility.get('ram_group', True))
        
        show_gpus = visibility.get('gpu_groups', True)
        for gpu_group in self.gpu_groups:
            gpu_group.setVisible(show_gpus)

        self.cpu_usage_label.setVisible(visibility.get('cpu_usage', True))
        self.cpu_temp_label.setVisible(visibility.get('cpu_temp', True))
        self.cpu_freq_label.setVisible(visibility.get('cpu_freq', True))

        if show_gpus:
            for gpu_labels in self.gpu_labels:
                gpu_labels['usage'].setVisible(visibility.get('gpu_usage', True))
                gpu_labels['temp'].setVisible(visibility.get('gpu_temp', True))
                gpu_labels['vram'].setVisible(visibility.get('gpu_vram', True))
        
        self.adjustSize()

    def update_button_visibility(self, hide):
        for btn in [self.settings_btn, self.minimize_btn, self.close_btn]:
            btn.setVisible(not hide)

    # --- Startup Logic ---
    
    def set_startup(self, enable):
        def revert_checkbox():
            dialog = self.findChild(SettingsDialog)
            if dialog: dialog.startup_checkbox.setChecked(not enable)

        if not is_admin() or not getattr(sys, 'frozen', False):
            msg = "Administrator privileges are required." if not is_admin() else "This feature only works for the packaged (.exe) application."
            QMessageBox.warning(self, "Action Required", msg)
            revert_checkbox()
            return

        install_dir = os.path.join(os.environ['ProgramFiles'], APP_NAME)
        source_path = os.path.abspath(sys.executable)
        dest_path = os.path.join(install_dir, os.path.basename(source_path))

        try:
            if enable:
                if source_path.lower() != dest_path.lower():
                    os.makedirs(install_dir, exist_ok=True)
                    shutil.copy(source_path, dest_path)
                    command = f'schtasks /create /tn "{TASK_NAME}" /tr "\"{dest_path}\"" /sc onlogon /rl highest /f'
                    subprocess.run(command, check=True, shell=True, capture_output=True)
                    QMessageBox.information(self, "Restarting Application", f"App moved to:\n{dest_path}\n\nIt will now restart from the new location.")
                    subprocess.Popen([dest_path])
                    QApplication.instance().quit()
                else:
                    command = f'schtasks /create /tn "{TASK_NAME}" /tr "\"{dest_path}\"" /sc onlogon /rl highest /f'
                    subprocess.run(command, check=True, shell=True, capture_output=True)
            else:
                command = f'schtasks /delete /tn "{TASK_NAME}" /f'
                subprocess.run(command, check=True, shell=True, capture_output=True)
                QMessageBox.information(self, "Startup Disabled", "Startup task has been removed.")
        except Exception as e:
            QMessageBox.critical(self, "Task Scheduler Error", f"Failed to modify startup task: {e}")
            revert_checkbox()

    # --- Window Events ---

    def mousePressEvent(self, event):
        if not self.settings['click_through'] and event.button() == Qt.LeftButton:
            self._start_pos = event.globalPos() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if not self.settings['click_through'] and self._start_pos and event.buttons() == Qt.LeftButton:
            self.move(event.globalPos() - self._start_pos)
            event.accept()
            self.settings['window_pos_x'] = self.pos().x()
            self.settings['window_pos_y'] = self.pos().y()
            self.save_settings(move=True)

    def mouseReleaseEvent(self, event):
        self._start_pos = None
        event.accept()
    
    def closeEvent(self, event):
        # Store current window position before saving settings
        self.settings['window_pos_x'] = self.pos().x()
        self.settings['window_pos_y'] = self.pos().y()

        self.save_settings()
        if NVML_AVAILABLE:
            try:
                nvmlShutdown()
            except NVMLError as e:
                print(f"Error shutting down NVML: {e}")
        self.tray_icon.hide()
        event.accept()

    def show_first_run_message(self):
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("Welcome!")
        msg_box.setText("For full functionality (CPU temperature, startup settings), please run as administrator.")
        msg_box.setIcon(QMessageBox.Information)
        msg_box.exec_()
        self.settings['first_run_completed'] = True
        self.save_settings()
