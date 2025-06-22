# settings_dialog.py
"""
Defines the SettingsDialog class for the application's settings window.
This class handles all the UI and logic for changing application settings.
"""

import sys
import base64
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, QGroupBox, 
                             QPushButton, QSlider, QCheckBox, QRadioButton,
                             QButtonGroup, QComboBox, QMessageBox, QScrollArea, QWidget)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QIcon, QPixmap, QFont
import qdarktheme

from ui.icon import BASE64_APP_ICON_DATA
from config import APP_VERSION
from utils import check_startup_task

class SettingsDialog(QDialog):
    # Signals to notify the main window of changes
    refresh_interval_changed = pyqtSignal(int)
    opacity_changed = pyqtSignal(float)
    always_on_top_changed = pyqtSignal(bool)
    click_through_changed = pyqtSignal(bool)
    theme_changed = pyqtSignal(str)
    element_visibility_changed = pyqtSignal(dict)
    startup_changed = pyqtSignal(bool)

    def __init__(self, parent=None, initial_settings=None):
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.setGeometry(200, 200, 450, 650)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        
        # Set the window icon
        app_icon_pixmap = QPixmap()
        app_icon_pixmap.loadFromData(base64.b64decode(BASE64_APP_ICON_DATA))
        self.setWindowIcon(QIcon(app_icon_pixmap))

        self.initial_settings = initial_settings if initial_settings else {}
        self.current_visibility_settings = self.initial_settings.get('visibility', {})

        self.init_ui()
        self.load_initial_settings()
        qdarktheme.setup_theme(self.initial_settings.get('theme', 'dark'))

    def init_ui(self):
        main_layout = QVBoxLayout()
        scroll_area = QScrollArea(self)
        scroll_area_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_area_widget)

        # General Settings Group
        general_group = QGroupBox("General Settings")
        general_layout = QVBoxLayout()
        
        if sys.platform == "win32":
            self.startup_checkbox = QCheckBox("Run when Windows starts")
            self.startup_checkbox.setToolTip("Moves app to Program Files and uses Task Scheduler to launch with admin rights.")
            general_layout.addWidget(self.startup_checkbox)

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
        
        self.always_on_top_checkbox = QCheckBox("Always on Top")
        general_layout.addWidget(self.always_on_top_checkbox)

        # Transparency/Opacity
        opacity_layout = QHBoxLayout()
        opacity_label = QLabel("Transparency:")
        self.opacity_value_label = QLabel("100%")
        opacity_layout.addWidget(opacity_label)
        opacity_layout.addWidget(self.opacity_value_label)
        general_layout.addLayout(opacity_layout)

        self.opacity_slider = QSlider(Qt.Horizontal)
        self.opacity_slider.setRange(10, 100)
        self.opacity_slider.setSingleStep(1)
        self.opacity_slider.setToolTip("Adjust window opacity (10% to 100%)")
        self.opacity_slider.valueChanged.connect(self.update_opacity_label)
        general_layout.addWidget(self.opacity_slider)

        self.click_through_checkbox = QCheckBox("Enable Click-through (Disables interaction)")
        self.click_through_checkbox.setToolTip("Makes the window transparent to mouse input. Use Tray Icon to open settings again.")
        self.click_through_checkbox.stateChanged.connect(self.warn_click_through)
        general_layout.addWidget(self.click_through_checkbox)

        general_group.setLayout(general_layout)
        scroll_layout.addWidget(general_group)

        # Theme Settings Group
        theme_group = QGroupBox("Theme Settings")
        theme_layout = QVBoxLayout()
        theme_label = QLabel("Select Theme:")
        theme_layout.addWidget(theme_label)
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(qdarktheme.get_themes())
        self.theme_combo.setToolTip("Select the application theme.")
        theme_layout.addWidget(self.theme_combo)
        theme_group.setLayout(theme_layout)
        scroll_layout.addWidget(theme_group)

        # Element Visibility Group
        visibility_group = QGroupBox("Element Visibility")
        visibility_layout = QVBoxLayout()
        self.visibility_checkboxes = {
            'cpu_group': QCheckBox("Show CPU Section"), 'ram_group': QCheckBox("Show RAM Section"),
            'gpu_groups': QCheckBox("Show GPU Section(s)"), 'cpu_usage': QCheckBox("Show CPU Usage"),
            'cpu_temp': QCheckBox("Show CPU Temp"), 'cpu_freq': QCheckBox("Show CPU Freq"),
            'gpu_usage': QCheckBox("Show GPU Usage"), 'gpu_temp': QCheckBox("Show GPU Temp"),
            'gpu_vram': QCheckBox("Show GPU VRAM")
        }
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
        
        self.rapl_label = QLabel("R.A.P.L. GROUP")
        self.rapl_label.setAlignment(Qt.AlignCenter)
        self.rapl_label.setFont(QFont("Inter", 7))
        self.rapl_label.setStyleSheet("color: #888888;")
        about_layout.addWidget(self.rapl_label)

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
        if sys.platform == "win32":
            self.startup_checkbox.setChecked(check_startup_task())
            
        interval = self.initial_settings.get('refresh_interval', 1500)
        radio_button = self.refresh_group.button(interval)
        if radio_button:
            radio_button.setChecked(True)
        else:
            self.normal_radio.setChecked(True)

        opacity = int(self.initial_settings.get('opacity', 1.0) * 100)
        self.opacity_slider.setValue(opacity)
        self.update_opacity_label(opacity)

        self.always_on_top_checkbox.setChecked(self.initial_settings.get('always_on_top', True))

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
        # Emit signals for the main window to handle
        self.refresh_interval_changed.emit(self.refresh_group.checkedId())
        self.opacity_changed.emit(self.opacity_slider.value() / 100.0)
        self.always_on_top_changed.emit(self.always_on_top_checkbox.isChecked())
        self.click_through_changed.emit(self.click_through_checkbox.isChecked())
        self.theme_changed.emit(self.theme_combo.currentText())
        
        if sys.platform == "win32":
            self.startup_changed.emit(self.startup_checkbox.isChecked())

        visibility_settings = {key: checkbox.isChecked() for key, checkbox in self.visibility_checkboxes.items()}
        self.element_visibility_changed.emit(visibility_settings)

        self.accept()

    def show_about_dialog(self):
        QMessageBox.about(self, "About R.A.P.L. GROUP Monitor",
            f"<h3>R.A.P.L. GROUP System Monitor</h3>"
            f"<p>Version: {APP_VERSION}</p>"
            "<p>A simple, customizable system performance monitoring application.</p>"
            "<p>Developed by R.A.P.L. GROUP</p>"
            "<p>Special thanks to psutil and pynvml libraries.</p>"
        )
