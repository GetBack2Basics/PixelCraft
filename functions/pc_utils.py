# functions/pc_utils.py
import os
import shutil
import datetime
from osgeo import gdal, ogr

from qgis.core import QgsProject, Qgis, QgsCoordinateReferenceSystem, edit
from PyQt5.QtWidgets import QMessageBox

from ..pc_config import settings

def backup_raster(raster_path):
    """Creates a timestamped backup of the raster file before modification."""
    backup_count = settings.get("backup_count", 5)
    if backup_count == 0: return
    try:
        base_dir = os.path.dirname(raster_path)
        filename = os.path.basename(raster_path)
        backup_dir = os.path.join(base_dir, "backups")
        os.makedirs(backup_dir, exist_ok=True)
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"{os.path.splitext(filename)[0]}_{timestamp}{os.path.splitext(filename)[1]}"
        backup_path = os.path.join(backup_dir, backup_name)
        shutil.copy2(raster_path, backup_path)
        print(f"Created backup: {backup_path}")
        backups = sorted([f for f in os.listdir(backup_dir) if f.startswith(os.path.splitext(filename)[0])])
        while len(backups) > backup_count:
            oldest_backup = os.path.join(backup_dir, backups.pop(0))
            os.remove(oldest_backup)
            print(f"Removed old backup: {oldest_backup}")
    except Exception as e:
        print(f"Could not create backup: {e}")

def parse_value_string(value_str):
    """Parses a string like "1, 2, 5-7" into a list of integers [1, 2, 5, 6, 7]."""
    values = set()
    parts = value_str.split(',')
    for part in parts:
        part = part.strip()
        if '-' in part:
            start, end = map(int, part.split('-'))
            values.update(range(start, end + 1))
        elif part:
            values.add(int(part))
    return list(values)

def get_window_from_geom(geom, gdal_ds):
    """Calculates the raster pixel window (offset, size) from a geometry's bounding box."""
    gt = gdal_ds.GetGeoTransform()
    inv_gt = gdal.InvGeoTransform(gt)
    if not inv_gt: raise Exception("Invalid geotransform in raster layer.")
    bbox = geom.boundingBox()
    ulx, uly = gdal.ApplyGeoTransform(inv_gt, bbox.xMinimum(), bbox.yMaximum())
    lrx, lry = gdal.ApplyGeoTransform(inv_gt, bbox.xMaximum(), bbox.yMinimum())
    px_w = int(lrx - ulx) + 1
    px_h = int(lry - uly) + 1
    px_x = int(ulx)
    px_y = int(uly)
    return (px_x, px_y, px_w, px_h)

def create_mask_for_chunk(geom, gdal_ds, window):
    """Creates a boolean mask array for just the specified raster window."""
    x_offset, y_offset, x_size, y_size = window
    mem_driver = gdal.GetDriverByName('MEM')
    mask_ds = mem_driver.Create('', x_size, y_size, 1, gdal.GDT_Byte)
    gt = gdal_ds.GetGeoTransform()
    chunk_gt = (gt[0] + x_offset * gt[1], gt[1], 0, gt[3] + y_offset * gt[5], 0, gt[5])
    mask_ds.SetGeoTransform(chunk_gt)
    mask_ds.SetProjection(gdal_ds.GetProjection())
    ogr_geom = ogr.CreateGeometryFromWkt(geom.asWkt())
    temp_vector_ds = ogr.GetDriverByName('Memory').CreateDataSource('temp')
    srs = ogr.osr.SpatialReference()
    srs.ImportFromWkt(gdal_ds.GetProjection())
    temp_layer = temp_vector_ds.CreateLayer('poly', geom_type=ogr.wkbPolygon, srs=srs)
    temp_feature = ogr.Feature(temp_layer.GetLayerDefn())
    temp_feature.SetGeometry(ogr_geom)
    temp_layer.CreateFeature(temp_feature)
    gdal.RasterizeLayer(mask_ds, [1], temp_layer, burn_values=[1])
    mask_array = mask_ds.GetRasterBand(1).ReadAsArray()
    return mask_array

def update_vector_attributes(vector_layer, processed_features, combined_summary, status="Applied"):
    """
    Updates the attribute table for the specified features to log the edit.
    Now uses robust left-truncation for the summary field.
    """
    editor = settings.get("user_account_name", "Unknown")
    edit_date = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    try:
        with edit(vector_layer):
            for feature in processed_features:
                fid = feature.id()
                
                fields = vector_layer.fields()
                status_idx = fields.lookupField(settings.get("status_field", "status"))
                editor_idx = fields.lookupField(settings.get("editor_field", "editor"))
                date_idx = fields.lookupField(settings.get("edit_date_field", "edit_date"))
                summary_idx = fields.lookupField(settings.get("edit_summary_field", "edit_sum"))

                if status_idx != -1: vector_layer.changeAttributeValue(fid, status_idx, status)
                if editor_idx != -1: vector_layer.changeAttributeValue(fid, editor_idx, editor)
                if date_idx != -1: vector_layer.changeAttributeValue(fid, date_idx, edit_date)

                # --- CORRECTED: Bulletproof Smart Append Logic ---
                if combined_summary and summary_idx != -1:
                    max_length = fields.field(summary_idx).length()
                    existing_summary = feature.attribute(summary_idx)
                    
                    # 1. Construct the full potential string
                    full_potential_summary = ""
                    if existing_summary and str(existing_summary).strip():
                        full_potential_summary = f"{existing_summary}; {combined_summary}"
                    else:
                        full_potential_summary = combined_summary
                    
                    # 2. If it's too long, truncate from the LEFT, keeping the newest data
                    if len(full_potential_summary) > max_length:
                        # Keep the last (max_length - 3) characters and prepend "..."
                        final_summary = "..." + full_potential_summary[-(max_length - 3):]
                    else:
                        final_summary = full_potential_summary
                    
                    vector_layer.changeAttributeValue(fid, summary_idx, final_summary)
    
    except Exception as e:
        commit_errors = vector_layer.commitErrors()
        error_details = "\n".join(commit_errors) if commit_errors else str(e)
        QMessageBox.critical(None, "Attribute Update Failed", 
                             f"Could not save attribute changes to '{vector_layer.name()}'.\n\nDetails: {error_details}")