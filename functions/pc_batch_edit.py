# functions/pc_batch_edit.py
from qgis.core import QgsProject, edit
from qgis.utils import iface
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QFormLayout, QHBoxLayout,
                             QLineEdit, QTextEdit, QComboBox, QMessageBox, QPushButton)

from ..pc_config import settings
# Import the function we will call directly from this dialog
from .pc_apply_codes import run_apply_codes

class BatchEditDialog(QDialog):
    """
    A dialog for editing attributes for multiple features at once.
    This dialog now contains the logic to either update attributes or
    update attributes AND apply changes to the raster.
    """
    def __init__(self, vector_layer, parent=None):
        super().__init__(parent)
        self.setWindowTitle("PixelCraft - Batch Edit")
        self.layer = vector_layer
        self.setMinimumWidth(400)

        # This will store which action the user chose
        self.chosen_action = None

        # --- UI Widgets ---
        self.orig_vals_edit = QLineEdit()
        self.orig_vals_edit.setPlaceholderText("e.g., 41, 42, 50-55")
        self.new_val_edit = QLineEdit()
        self.new_val_edit.setPlaceholderText("e.g., 90")
        self.note_edit = QTextEdit()
        self.note_edit.setPlaceholderText("Add optional notes about this edit.")
        self.status_combo = QComboBox()

        # --- Layout ---
        layout = QVBoxLayout(self)
        form_layout = QFormLayout()
        form_layout.addRow("Original Value(s):", self.orig_vals_edit)
        form_layout.addRow("New Value:", self.new_val_edit)
        form_layout.addRow("Status:", self.status_combo)
        form_layout.addRow("Note:", self.note_edit)
        layout.addLayout(form_layout)

        # --- CORRECTED: Custom Buttons ---
        # We replace the standard QDialogButtonBox with our own custom buttons
        button_layout = QHBoxLayout()
        self.update_button = QPushButton("Update Codes")
        self.update_button.setToolTip("Update the attributes of the selected vector features only.")
        
        self.apply_button = QPushButton("Apply Codes")
        self.apply_button.setToolTip("Update attributes AND apply the changes to the raster.")
        self.apply_button.setDefault(True)

        self.cancel_button = QPushButton("Cancel")
        
        button_layout.addStretch() # Pushes buttons to the right
        button_layout.addWidget(self.update_button)
        button_layout.addWidget(self.apply_button)
        button_layout.addWidget(self.cancel_button)
        layout.addLayout(button_layout)

        # --- Connections ---
        self.update_button.clicked.connect(self.handle_update_codes)
        self.apply_button.clicked.connect(self.handle_apply_codes)
        self.cancel_button.clicked.connect(self.reject)

        self._populate_initial_values()

    def _populate_initial_values(self):
        """Pre-fills dialog fields based on the selected features."""
        features = self.layer.selectedFeatures()
        
        def get_unique_vals(field_name):
            if not field_name: return {""}
            return {f.attribute(field_name) for f in features}

        status_options = [s.strip() for s in settings.get("status_values", "").split(',') if s.strip()]
        self.status_combo.addItems(status_options if status_options else ["Pending"])

        fields_to_check = {
            self.orig_vals_edit: settings.get("orig_vals_field"),
            self.new_val_edit: settings.get("new_val_field"),
            self.note_edit: settings.get("note_field"),
            self.status_combo: settings.get("status_field")
        }

        for widget, field_name in fields_to_check.items():
            unique_values = get_unique_vals(field_name)
            if len(unique_values) == 1:
                value = unique_values.pop()
                if isinstance(widget, QLineEdit): widget.setText(str(value or ''))
                elif isinstance(widget, QTextEdit): widget.setText(str(value or ''))
                elif isinstance(widget, QComboBox): widget.setCurrentText(str(value or ''))
            else:
                if isinstance(widget, (QLineEdit, QTextEdit)):
                    widget.setPlaceholderText("<multiple values>")

    def _update_feature_attributes(self):
        """
        A helper function that applies the current dialog values to the
        selected vector features. Returns True on success, False on failure.
        """
        values = {
            "orig_vals": self.orig_vals_edit.text(),
            "new_val": self.new_val_edit.text(),
            "note": self.note_edit.toPlainText(),
            "status": self.status_combo.currentText()
        }
        
        field_map = {
            "orig_vals": settings.get("orig_vals_field"),
            "new_val": settings.get("new_val_field"),
            "note": settings.get("note_field"),
            "status": settings.get("status_field")
        }

        try:
            with edit(self.layer):
                for feature in self.layer.selectedFeatures():
                    for key, field_name in field_map.items():
                        if field_name:
                            self.layer.changeAttributeValue(feature.id(), self.layer.fields().lookupField(field_name), values[key])
            return True
        except Exception as e:
            QMessageBox.critical(None, "Update Failed", f"Could not update attributes: {e}")
            return False

    def handle_update_codes(self):
        """Action for the 'Update Codes' button."""
        if self._update_feature_attributes():
            QMessageBox.information(None, "Attributes Updated", 
                                    "Attributes have been updated.\n\nClick 'Apply Codes' on the main dock to modify the raster.")
            self.chosen_action = 'update'
            self.accept() # Close the dialog

    def handle_apply_codes(self):
        """Action for the 'Apply Codes' button."""
        if self._update_feature_attributes():
            self.chosen_action = 'apply'
            self.accept() # Close the dialog

def run_batch_edit():
    """
    Main entry point for the 'Batch Edit' button.
    Opens the dialog and then, if requested, triggers the raster update.
    """
    vector_layer_name = settings.get("vector_layer_name")
    if not vector_layer_name:
        QMessageBox.critical(None, "Configuration Error", "Vector Layer must be set in Settings.")
        return

    vector_layer = QgsProject.instance().mapLayersByName(vector_layer_name)
    if not vector_layer:
        QMessageBox.critical(None, "Layer Not Found", f"The layer '{vector_layer_name}' could not be found.")
        return
    vector_layer = vector_layer[0]

    if vector_layer.selectedFeatureCount() == 0:
        QMessageBox.warning(None, "No Selection", "Please select one or more features to edit.")
        return

    # --- Run Dialog and Check User's Choice ---
    dialog = BatchEditDialog(vector_layer, iface.mainWindow())
    result = dialog.exec_()

    # Only proceed if the dialog was accepted (not cancelled)
    if result == QDialog.Accepted:
        # If the user chose to apply codes, call the other function now
        if dialog.chosen_action == 'apply':
            print("Batch Edit successful. Now triggering Apply Codes...")
            run_apply_codes()