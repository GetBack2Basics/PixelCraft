# ui/pc_settings_dialog.py
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QDialogButtonBox, QLabel, 
                             QTabWidget, QWidget, QFormLayout, QLineEdit,
                             QComboBox, QCheckBox, QSpinBox, QMessageBox)
from qgis.core import QgsProject, QgsRasterLayer, QgsVectorLayer
from qgis.gui import QgsFieldComboBox

from ..pc_config import settings, save_settings

class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("PixelCraft Settings")
        self.setMinimumSize(500, 450)
        
        main_layout = QVBoxLayout(self)
        tabs = QTabWidget()
        main_layout.addWidget(tabs)
        
        general_tab, layers_tab, behavior_tab = QWidget(), QWidget(), QWidget()
        tabs.addTab(general_tab, "General")
        tabs.addTab(layers_tab, "Layers & Fields")
        tabs.addTab(behavior_tab, "Behavior")

        self.populate_general_tab(general_tab)
        self.populate_layers_tab(layers_tab)
        self.populate_behavior_tab(behavior_tab)
        
        self.button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        main_layout.addWidget(self.button_box)

        self.load_initial_settings()

    def populate_general_tab(self, tab):
        layout = QFormLayout(tab)
        self.user_account_edit = QLineEdit()
        layout.addRow("User Account Name:", self.user_account_edit)
        self.backup_count_spin = QSpinBox()
        self.backup_count_spin.setRange(0, 100)
        layout.addRow("Backup Count:", self.backup_count_spin)
        
        # --- NEW: Add Status Values Configuration ---
        self.status_values_edit = QLineEdit()
        self.status_values_edit.setToolTip("Comma-separated list of values for the status dropdown.")
        layout.addRow("Status Options:", self.status_values_edit)

    def populate_layers_tab(self, tab):
        layout = QFormLayout(tab)
        self.raster_layer_combo = QComboBox()
        self.source_raster_combo = QComboBox()
        self.vector_layer_combo = QComboBox()
        
        raster_layers = [""] + [layer.name() for layer in QgsProject.instance().mapLayers().values() if isinstance(layer, QgsRasterLayer)]
        vector_layers = [""] + [layer.name() for layer in QgsProject.instance().mapLayers().values() if isinstance(layer, QgsVectorLayer)]
        
        self.raster_layer_combo.addItems(raster_layers)
        self.source_raster_combo.addItems(raster_layers)
        self.vector_layer_combo.addItems(vector_layers)
        
        layout.addRow("Target Raster Layer:", self.raster_layer_combo)
        layout.addRow("Source (Original) Raster:", self.source_raster_combo)
        layout.addRow("Vector (Editing) Layer:", self.vector_layer_combo)
        
        self.orig_vals_field = QgsFieldComboBox()
        self.new_val_field = QgsFieldComboBox()
        # --- NEW: Add Note and Status Field Combos ---
        self.note_field = QgsFieldComboBox()
        self.status_field = QgsFieldComboBox()
        
        layout.addRow("Original Values Field:", self.orig_vals_field)
        layout.addRow("New Value Field:", self.new_val_field)
        layout.addRow("Note Field:", self.note_field)
        layout.addRow("Status Field:", self.status_field)
        
        self.vector_layer_combo.currentTextChanged.connect(self.update_field_combos)

    def populate_behavior_tab(self, tab):
        layout = QFormLayout(tab)
        self.auto_watch_check = QCheckBox("Automatically watch layers for file changes")
        layout.addRow(self.auto_watch_check)

    def update_field_combos(self):
        layer_name = self.vector_layer_combo.currentText()
        layer = QgsProject.instance().mapLayersByName(layer_name)[0] if layer_name else None
        
        self.orig_vals_field.setLayer(layer)
        self.new_val_field.setLayer(layer)
        self.note_field.setLayer(layer)
        self.status_field.setLayer(layer)

    def load_initial_settings(self):
        self.user_account_edit.setText(settings.get("user_account_name", ""))
        self.backup_count_spin.setValue(settings.get("backup_count", 5))
        self.status_values_edit.setText(settings.get("status_values", "Pending,Applied,Rejected"))
        
        self.raster_layer_combo.setCurrentText(settings.get("raster_layer_name", ""))
        self.source_raster_combo.setCurrentText(settings.get("source_raster_layer_name", ""))
        self.vector_layer_combo.setCurrentText(settings.get("vector_layer_name", ""))
        
        self.orig_vals_field.setField(settings.get("orig_vals_field", ""))
        self.new_val_field.setField(settings.get("new_val_field", ""))
        self.note_field.setField(settings.get("note_field", ""))
        self.status_field.setField(settings.get("status_field", ""))
        
        self.auto_watch_check.setChecked(settings.get("auto_watch_layers", True))
        
    def accept(self):
        settings["user_account_name"] = self.user_account_edit.text()
        settings["backup_count"] = self.backup_count_spin.value()
        settings["status_values"] = self.status_values_edit.text()
        
        settings["raster_layer_name"] = self.raster_layer_combo.currentText()
        settings["source_raster_layer_name"] = self.source_raster_combo.currentText()
        settings["vector_layer_name"] = self.vector_layer_combo.currentText()
        settings["orig_vals_field"] = self.orig_vals_field.currentField()
        settings["new_val_field"] = self.new_val_field.currentField()
        settings["note_field"] = self.note_field.currentField()
        settings["status_field"] = self.status_field.currentField()
        
        settings["auto_watch_layers"] = self.auto_watch_check.isChecked()
        
        try:
            save_settings(settings)
            QMessageBox.information(self, "Settings Saved", "Your settings have been saved.")
            super().accept()
        except Exception as e:
            QMessageBox.critical(self, "Error Saving Settings", f"Could not save settings file:\n{e}")