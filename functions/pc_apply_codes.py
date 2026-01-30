# functions/pc_apply_codes.py
import numpy as np
from osgeo import gdal

from qgis.core import QgsProject, QgsCoordinateTransform, QgsCoordinateReferenceSystem
from qgis.utils import iface
from PyQt5.QtWidgets import QMessageBox, QProgressDialog
from PyQt5.QtCore import Qt

from ..pc_config import settings
# --- CORRECTED: Import shared functions from the new utility file ---
from .pc_utils import (backup_raster, get_window_from_geom, create_mask_for_chunk,
                       update_vector_attributes, parse_value_string)

def run_apply_codes():
    try:
        target_raster_name = settings.get("raster_layer_name")
        vector_layer_name = settings.get("vector_layer_name")
        if not target_raster_name or not vector_layer_name:
            QMessageBox.critical(None, "Configuration Error", "Target Raster and Vector Layer must be set in Settings.")
            return
        target_layer_obj = QgsProject.instance().mapLayersByName(target_raster_name)
        vector_layer_obj = QgsProject.instance().mapLayersByName(vector_layer_name)
        if not target_layer_obj or not vector_layer_obj:
            QMessageBox.critical(None, "Layer Not Found", "Configured raster or vector layer not found in project.")
            return
        target_layer = target_layer_obj[0]
        vector_layer = vector_layer_obj[0]
        selected_features = vector_layer.selectedFeatures()
        if not selected_features:
            QMessageBox.warning(None, "No Selection", "Please select one or more features to apply edits.")
            return
        print("PixelCraft: Starting 'Apply Codes' process...")
        total_cells_changed = _process_raster_update(target_layer, vector_layer, selected_features)
        if total_cells_changed is not None:
            if total_cells_changed > 0:
                QMessageBox.information(None, "Process Complete", f"Successfully applied edits. Total cells changed: {total_cells_changed}")
            else:
                QMessageBox.information(None, "Process Complete", "Process ran, but no matching raster cells were found to change.")
    except Exception as e:
        print(f"ERROR in run_apply_codes: {e}")
        QMessageBox.critical(None, "An Error Occurred", f"An unexpected error occurred: {e}")

def _process_raster_update(target_layer, vector_layer, selected_features):
    """
    Handles the core logic by processing the raster in efficient chunks.
    """
    raster_path = target_layer.dataProvider().dataSourceUri()
    backup_raster(raster_path)
    
    feature_count = len(selected_features)
    progress_dialog = QProgressDialog("Applying raster edits...", "Cancel", 0, feature_count, iface.mainWindow())
    progress_dialog.setWindowModality(Qt.WindowModal)
    progress_dialog.setMinimumDuration(0)

    gdal_options = ['IGNORE_COG_LAYOUT_BREAK=YES']
    gdal_ds = gdal.OpenEx(raster_path, gdal.GA_Update, open_options=gdal_options)
    if not gdal_ds: raise IOError(f"Could not open raster file for writing: {raster_path}")
    gdal_band = gdal_ds.GetRasterBand(1)
    
    total_cells_changed = 0
    all_edit_summaries = []

    try:
        for i, feature in enumerate(selected_features):
            progress_dialog.setValue(i)
            if progress_dialog.wasCanceled():
                total_cells_changed = None; break
            cells_changed, summary = _update_raster_for_feature_optimized(feature, vector_layer, gdal_ds, gdal_band)
            if cells_changed > 0:
                total_cells_changed += cells_changed
                all_edit_summaries.append(summary)
        progress_dialog.setValue(feature_count)
    finally:
        gdal_ds.FlushCache(); gdal_ds = None; progress_dialog.close()

    if total_cells_changed is not None:
        update_vector_attributes(vector_layer, selected_features, "; ".join(all_edit_summaries), status="Applied")
        
        # --- CORRECTED: Safely clear the render cache ---
        # Check if the renderer exists and has the setCacheImage method before calling it.
        renderer = target_layer.renderer()
        if renderer and hasattr(renderer, 'setCacheImage'):
            renderer.setCacheImage(None)
            
        target_layer.dataProvider().reload()
        iface.mapCanvas().refreshAllLayers()
        
    return total_cells_changed
def _update_raster_for_feature_optimized(feature, vector_layer, gdal_ds, gdal_band):
    orig_vals_field = settings.get("orig_vals_field", "orig_vals")
    new_val_field = settings.get("new_val_field", "new_val")
    orig_vals_str = feature.attribute(orig_vals_field)
    new_val = feature.attribute(new_val_field)
    if orig_vals_str is None or new_val is None: return 0, None
    try:
        orig_vals_list = parse_value_string(str(orig_vals_str))
        new_val = int(new_val)
    except (ValueError, TypeError): return 0, None
    geom = feature.geometry()
    if geom.isEmpty(): return 0, None
    vector_crs = vector_layer.crs(); raster_crs = QgsCoordinateReferenceSystem(gdal_ds.GetProjection())
    if vector_crs != raster_crs:
        transform = QgsCoordinateTransform(vector_crs, raster_crs, QgsProject.instance())
        geom.transform(transform)
    x_offset, y_offset, x_size, y_size = get_window_from_geom(geom, gdal_ds)
    if x_size <= 0 or y_size <= 0: return 0, None
    raster_chunk = gdal_band.ReadAsArray(x_offset, y_offset, x_size, y_size)
    if raster_chunk is None: return 0, None
    mask_array = create_mask_for_chunk(geom, gdal_ds, (x_offset, y_offset, x_size, y_size))
    condition = (np.isin(raster_chunk, orig_vals_list)) & (mask_array == 1)
    cells_changed = np.sum(condition)
    if cells_changed > 0:
        raster_chunk[condition] = new_val
        gdal_band.WriteArray(raster_chunk, x_offset, y_offset)
        summary = f"Changed {cells_changed} cells from [{orig_vals_str}] to {new_val}"
        return cells_changed, summary
    return 0, None