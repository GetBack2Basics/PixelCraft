# ui/pc_dock.py
from PyQt5.QtWidgets import (QDockWidget, QWidget, QVBoxLayout, QPushButton, 
                             QGridLayout, QLabel, QFrame, QHBoxLayout)

from .pc_settings_dialog import SettingsDialog
from ..pc_config import metadata

# Import all placeholder functions
from ..functions.pc_apply_codes import run_apply_codes
from ..functions.pc_batch_edit import run_batch_edit
from ..functions.pc_restore import run_restore
from ..functions.pc_trace_pixel import run_trace_pixel
from ..functions.pc_add_selections import run_add_selections
from ..functions.pc_difference_calc import run_difference_calc

class PixelCraftDock(QDockWidget):
    def __init__(self, parent=None):
        title = metadata.get('general', {}).get('name', 'Plugin')
        super().__init__(title, parent)
        self.setObjectName("PixelCraftDock")
        
        self.main_widget = QWidget()
        self.main_layout = QVBoxLayout(self.main_widget)
        
        # --- Inspector Area ---
        self.inspector_frame = QFrame()
        self.inspector_frame.setFrameShape(QFrame.StyledPanel)
        inspector_layout = QGridLayout(self.inspector_frame)
        inspector_layout.addWidget(QLabel("<b>Inspector:</b>"), 0, 0)
        inspector_layout.addWidget(QLabel("--"), 0, 1)
        self.main_layout.addWidget(self.inspector_frame)
        
        # --- Main Button Grid ---
        button_layout = QGridLayout()
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
        
        # --- Utility Buttons ---
        utility_layout = QHBoxLayout()
        self.btn_watch = QPushButton("Watch")
        self.btn_settings = QPushButton("Settings")
        utility_layout.addWidget(self.btn_watch)
        utility_layout.addWidget(self.btn_settings)
        self.main_layout.addLayout(utility_layout)
        
        self.main_layout.addStretch()
        self.setWidget(self.main_widget)
        
        self.apply_tooltips()
        self.connect_signals()

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
        self.btn_restore.clicked.connect(run_restore)
        self.btn_trace_pixel.clicked.connect(run_trace_pixel)
        self.btn_add_selections.clicked.connect(run_add_selections)
        self.btn_difference_calc.clicked.connect(run_difference_calc)
        self.btn_settings.clicked.connect(self.open_settings)

    def open_settings(self):
        dialog = SettingsDialog(self)
        dialog.exec_()