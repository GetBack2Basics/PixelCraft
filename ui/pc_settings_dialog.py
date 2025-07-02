# ui/pc_settings_dialog.py
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QDialogButtonBox, QLabel)
from ..pc_config import settings, save_settings

class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("PixelCraft Settings")
        
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Settings will be configured here."))
        
        self.button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        
        layout.addWidget(self.button_box)
        
    def accept(self):
        save_settings(settings)
        super().accept()