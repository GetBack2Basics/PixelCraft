# ui/pc_dock.py
from PyQt5.QtWidgets import (QDockWidget, QWidget, QVBoxLayout, QPushButton, 
                             QGridLayout, QLabel, QFrame, QHBoxLayout)
from qgis.utils import iface

# Import UI components and config
from .pc_settings_dialog import SettingsDialog
from ..pc_config import metadata, settings

# Import the Inspector Tool
from ..functions.pc_inspector import PixelInspectorTool

# Import all placeholder and implemented functions
from ..functions.pc_apply_codes import run_apply_codes
from ..functions.pc_batch_edit import run_batch_edit
from ..functions.pc_restore import run_restore # The newly implemented function
from ..functions.pc_trace_pixel import run_trace_pixel
from ..functions.pc_add_selections import run_add_selections
from ..functions.pc_difference_calc import run_difference_calc

class PixelCraftDock(QDockWidget):
    def __init__(self, layer_watcher, parent=None):
        title = metadata.get('general', {}).get('name', 'Plugin')
        super().__init__(title, parent)
        self.setObjectName("PixelCraftDock")
        
        self.watcher = layer_watcher
        self.is_watching = False

        self.main_widget = QWidget()
        self.main_layout = QVBoxLayout(self.main_widget)
        self.main_layout.setContentsMargins(4, 4, 4, 4)
        self.main_layout.setSpacing(4)
        
        # --- Consolidated Inspector Area ---
        self.inspector_frame = QFrame()
        self.inspector_frame.setFrameShape(QFrame.StyledPanel)
        inspector_layout = QHBoxLayout(self.inspector_frame)
        inspector_layout.setContentsMargins(2, 2, 2, 2)
        inspector_layout.setSpacing(5)
        inspector_layout.addWidget(QLabel("<b>Inspector (T/S):</b>"))
        self.inspector_value_label = QLabel("-- / --")
        self.inspector_value_label.setStyleSheet("font-family: Consolas, 'Courier New', monospace;")
        inspector_layout.addWidget(self.inspector_value_label)
        inspector_layout.addStretch()
        self.main_layout.addWidget(self.inspector_frame)
        
        # --- Main Button Grid ---
        button_layout = QGridLayout()
        button_layout.setSpacing(2)
        self.btn_apply_codes = QPushButton("Apply Codes")
        self.btn_batch_edit = QPushButton("Batch Edit")
        self.btn_restore = QPushButton("Restore")
        self.btn_trace_pixel = QPushButton("Trace Pixel")
        self.btn_add_selections = QPushButton("Add Selections")
        self.btn_difference_calc = QPushButton("Difference Calc")
        
        button_layout.addWidget(self.btn_apply_codes, 0, 0)
        button_layout.addWidget(self.btn_batch_edit, 0, 1)
        button_layout.addWidget(self.btn_restore, 1, 0)
        button_layout.addWidget(self.btn_trace_pixel, 1, 1)
        button_layout.addWidget(self.btn_add_selections, 2, 0)
        button_layout.addWidget(self.btn_difference_calc, 2, 1)
        self.main_layout.addLayout(button_layout)

        # --- Consolidated Utility and Status Bar ---
        utility_layout = QHBoxLayout()
        utility_layout.setContentsMargins(0, 2, 0, 0)
        utility_layout.setSpacing(4)
        self.btn_watch = QPushButton("Watch")
        self.btn_watch.setCheckable(True)
        self.btn_settings = QPushButton("Settings")
        self.watch_status_label = QLabel("Watcher OFF")
        self.watch_status_label.setStyleSheet("font-size: 8pt; color: grey;")

        utility_layout.addWidget(self.btn_watch)
        utility_layout.addWidget(self.btn_settings)
        utility_layout.addWidget(self.watch_status_label)
        utility_layout.addStretch()
        self.main_layout.addLayout(utility_layout)
        
        self.main_layout.addStretch()
        self.setWidget(self.main_widget)
        
        self.inspector_tool = None
        self._previous_tool = None
        self._setup_inspector_tool()

        self.apply_tooltips()
        self.connect_signals()

        if settings.get("auto_watch_layers", True):
            self.btn_watch.setChecked(True)
            self.toggle_watching_service()

    def _setup_inspector_tool(self):
        canvas = iface.mapCanvas()
        if canvas:
            self.inspector_tool = PixelInspectorTool(canvas)
            self.inspector_tool.values_updated.connect(self._update_inspector_display)
            self.visibilityChanged.connect(self._on_visibility_changed)

    def _on_visibility_changed(self, visible):
        canvas = iface.mapCanvas()
        if not canvas or not self.inspector_tool:
            return

        if visible:
            self._previous_tool = canvas.mapTool()
            canvas.setMapTool(self.inspector_tool)
        else:
            if canvas.mapTool() is self.inspector_tool:
                canvas.setMapTool(self._previous_tool)

    def _update_inspector_display(self, data):
        target_val = data.get('target_value')
        source_val = data.get('source_value')
        target_str = f"{int(target_val)}" if target_val is not None else "--"
        source_str = f"{int(source_val)}" if source_val is not None else "--"
        self.inspector_value_label.setText(f"{target_str} / {source_str}")

    def apply_tooltips(self):
        tooltips = metadata.get('tooltips', {})
        self.btn_apply_codes.setToolTip(tooltips.get('apply_codes', ''))
        self.btn_batch_edit.setToolTip(tooltips.get('batch_edit', ''))
        self.btn_restore.setToolTip(tooltips.get('restore', ''))
        self.btn_trace_pixel.setToolTip(tooltips.get('trace_pixel', ''))
        self.btn_add_selections.setToolTip(tooltips.get('add_selections', ''))
        self.btn_difference_calc.setToolTip(tooltips.get('difference_calc', ''))
        self.btn_settings.setToolTip(tooltips.get('settings', ''))
        self.btn_watch.setToolTip(tooltips.get('watch', ''))
        self.inspector_frame.setToolTip(tooltips.get('inspector', ''))

    def connect_signals(self):
        self.btn_apply_codes.clicked.connect(run_apply_codes)
        self.btn_batch_edit.clicked.connect(run_batch_edit)
        self.btn_restore.clicked.connect(run_restore) # <-- CORRECTLY CONNECTED
        self.btn_trace_pixel.clicked.connect(run_trace_pixel)
        self.btn_add_selections.clicked.connect(run_add_selections)
        self.btn_difference_calc.clicked.connect(run_difference_calc)
        self.btn_settings.clicked.connect(self.open_settings)
        self.btn_watch.clicked.connect(self.toggle_watching_service)
        self.watcher.watch_status_changed.connect(self.update_watch_status_display)

    def open_settings(self):
        dialog = SettingsDialog(self)
        dialog.exec_()
        if self.inspector_tool:
            self.inspector_tool._load_configured_layers()

    def toggle_watching_service(self):
        if self.btn_watch.isChecked():
            success = self.watcher.start_watching_configured_layers()
            if not success:
                self.btn_watch.setChecked(False)
        else:
            self.watcher.stop_all_watching()

    def update_watch_status_display(self, watched_files):
        if watched_files:
            self.watch_status_label.setText(f"Watching {len(watched_files)} file(s)")
            self.watch_status_label.setStyleSheet("font-size: 8pt; color: green;")
            self.btn_watch.setChecked(True)
        else:
            self.watch_status_label.setText("Watcher OFF")
            self.watch_status_label.setStyleSheet("font-size: 8pt; color: grey;")
            self.btn_watch.setChecked(False)