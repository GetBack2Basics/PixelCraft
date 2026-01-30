# functions/pc_restore.py
import numpy as np
from osgeo import gdal

from qgis.core import QgsProject, QgsCoordinateReferenceSystem
from qgis.utils import iface
from PyQt5.QtWidgets import QMessageBox, QProgressDialog, QInputDialog, QLineEdit
from PyQt5.QtCore import Qt

from ..pc_config import settings
# --- CORRECTED: Import shared functions from the new utility file ---
from .pc_utils import (backup_raster, get_window_from_geom, create_mask_for_chunk,
                       update_vector_attributes, parse_value_string)

def run_restore():
    try:
        target_name = settings.get("raster_layer_name")
        source_name = settings.get("source_raster_layer_name")
        vector_name = settings.get("vector_layer_name")
        if not all([target_name, source_name, vector_name]):
            QMessageBox.critical(None, "Configuration Error", "Target, Source, and Vector layers must be set in Settings.")
            return
        target_layer = QgsProject.instance().mapLayersByName(target_name)[0]
        source_layer = QgsProject.instance().mapLayersByName(source_name)[0]
        vector_layer = QgsProject.instance().mapLayersByName(vector_name)[0]
        selected_features = vector_layer.selectedFeatures()
        if not selected_features:
            QMessageBox.warning(None, "No Selection", "Please select features to restore.")
            return
        changed_codes = _find_changed_codes(target_layer, source_layer, selected_features)
        codes_to_restore_str, ok = QInputDialog.getText(iface.mainWindow(), "Confirm Restore",
            "The following values in the target raster will be restored.\nEdit list or leave blank to restore all differences:",
            QLineEdit.Normal, ", ".join(map(str, sorted(changed_codes))))
        if not ok: return
        codes_to_restore = parse_value_string(codes_to_restore_str)
        total_cells_restored = _process_raster_restore(target_layer, source_layer, vector_layer, selected_features, codes_to_restore)
        if total_cells_restored is not None:
            QMessageBox.information(None, "Process Complete", f"Successfully restored {total_cells_restored} cells.")
    except Exception as e:
        print(f"ERROR in run_restore: {e}")
        QMessageBox.critical(None, "An Error Occurred", f"An unexpected error occurred during restore: {e}")

def _find_changed_codes(target_layer, source_layer, selected_features):
    print("Finding changed codes...")
    target_ds = gdal.Open(target_layer.dataProvider().dataSourceUri())
    source_ds = gdal.Open(source_layer.dataProvider().dataSourceUri())
    target_band = target_ds.GetRasterBand(1)
    source_band = source_ds.GetRasterBand(1)
    all_changed_codes = set()
    for feature in selected_features:
        geom = feature.geometry()
        x_off, y_off, x_size, y_size = get_window_from_geom(geom, target_ds)
        if x_size <= 0 or y_size <= 0: continue
        target_chunk = target_band.ReadAsArray(x_off, y_off, x_size, y_size)
        source_chunk = source_band.ReadAsArray(x_off, y_off, x_size, y_size)
        if target_chunk is None or source_chunk is None: continue
        mask = create_mask_for_chunk(geom, target_ds, (x_off, y_off, x_size, y_size))
        difference_mask = (target_chunk != source_chunk) & (mask == 1)
        changed_values = target_chunk[difference_mask]
        all_changed_codes.update(np.unique(changed_values))
    return all_changed_codes

def _process_raster_restore(target_layer, source_layer, vector_layer, selected_features, codes_to_restore):
    """
    Handles the core logic of restoring raster values from a source layer.
    """
    raster_path = target_layer.dataProvider().dataSourceUri()
    backup_raster(raster_path)
    
    progress = QProgressDialog("Restoring raster values...", "Cancel", 0, len(selected_features), iface.mainWindow())
    progress.setWindowModality(Qt.WindowModal); progress.setMinimumDuration(0)

    target_ds = gdal.OpenEx(raster_path, gdal.GA_Update, open_options=['IGNORE_COG_LAYOUT_BREAK=YES'])
    source_ds = gdal.Open(source_layer.dataProvider().dataSourceUri())
    target_band = target_ds.GetRasterBand(1); source_band = source_ds.GetRasterBand(1)
    
    total_cells_restored = 0
    
    try:
        for i, feature in enumerate(selected_features):
            progress.setValue(i)
            if progress.wasCanceled(): total_cells_restored = None; break
            cells_restored = _restore_raster_for_feature(feature, target_ds, target_band, source_band, codes_to_restore)
            if cells_restored > 0: total_cells_restored += cells_restored
        progress.setValue(len(selected_features))
    finally:
        target_ds.FlushCache(); target_ds, source_ds = None, None; progress.close()

    if total_cells_restored is not None:
        summary = f"Restored {total_cells_restored} cells."
        update_vector_attributes(vector_layer, selected_features, summary, status="Restored")
        
        # --- CORRECTED: Safely clear the render cache ---
        # Check if the renderer exists and has the setCacheImage method before calling it.
        renderer = target_layer.renderer()
        if renderer and hasattr(renderer, 'setCacheImage'):
            renderer.setCacheImage(None)
            
        target_layer.dataProvider().reload()
        iface.mapCanvas().refreshAllLayers()
        
    return total_cells_restored

def _restore_raster_for_feature(feature, target_ds, target_band, source_band, codes_to_restore):
    geom = feature.geometry()
    x_off, y_off, x_size, y_size = get_window_from_geom(geom, target_ds)
    if x_size <= 0 or y_size <= 0: return 0
    target_chunk = target_band.ReadAsArray(x_off, y_off, x_size, y_size)
    source_chunk = source_band.ReadAsArray(x_off, y_off, x_size, y_size)
    if target_chunk is None or source_chunk is None: return 0
    mask = create_mask_for_chunk(geom, target_ds, (x_off, y_off, x_size, y_size))
    if codes_to_restore:
        condition = (np.isin(target_chunk, codes_to_restore)) & (mask == 1)
    else:
        condition = (target_chunk != source_chunk) & (mask == 1)
    cells_to_restore = np.sum(condition)
    if cells_to_restore > 0:
        target_chunk[condition] = source_chunk[condition]
        target_band.WriteArray(target_chunk, x_off, y_off)
    return cells_to_restore