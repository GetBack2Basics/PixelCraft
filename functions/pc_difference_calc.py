# functions/pc_difference_calc.py
import numpy as np
from osgeo import gdal, ogr, osr

from qgis.core import (QgsProject, QgsVectorLayer, QgsFeature, QgsField, edit,
                       QgsGeometry, QgsCategorizedSymbolRenderer, QgsSymbol,
                       QgsRendererCategory, QgsWkbTypes)
from qgis.utils import iface
from PyQt5.QtWidgets import QMessageBox, QProgressDialog
from PyQt5.QtCore import QVariant, Qt

from ..pc_config import settings

def run_difference_calc():
    """
    Main function called by the button. Validates that settings are configured
    and then calls the core calculation function.
    """
    try:
        target_name = settings.get("raster_layer_name")
        source_name = settings.get("source_raster_layer_name")
        if not all([target_name, source_name]):
            QMessageBox.critical(None, "Configuration Error", "Target and Source Raster layers must be set in Settings.")
            return

        print("PixelCraft: Starting 'Difference Calc' process...")
        # --- CORRECTED: The core function now fetches its own layers ---
        diff_layer = _calculate_differences_optimized()

        if diff_layer:
            QgsProject.instance().addMapLayer(diff_layer)
            QMessageBox.information(None, "Process Complete", f"Difference layer '{diff_layer.name()}' created successfully.")
        else:
            QMessageBox.information(None, "No Differences Found", "The rasters are identical.")

    except Exception as e:
        print(f"ERROR in run_difference_calc: {e}")
        QMessageBox.critical(None, "An Error Occurred", f"An unexpected error occurred during difference calculation: {e}")


def _calculate_differences_optimized():
    """
    Calculates differences by processing the rasters in memory-efficient chunks.
    This version fetches its own fresh layer objects to avoid caching issues.
    """
    # --- CORRECTED: Get fresh layer objects at the moment of execution ---
    target_name = settings.get("raster_layer_name")
    source_name = settings.get("source_raster_layer_name")
    
    target_layer_list = QgsProject.instance().mapLayersByName(target_name)
    source_layer_list = QgsProject.instance().mapLayersByName(source_name)

    if not target_layer_list or not source_layer_list:
        QMessageBox.critical(None, "Layer Not Found", "Configured Target or Source Raster not found in project.")
        return None
        
    target_layer = target_layer_list[0]
    source_layer = source_layer_list[0]
    
    # --- The rest of the logic can now proceed safely ---
    target_ds = gdal.Open(target_layer.dataProvider().dataSourceUri())
    source_ds = gdal.Open(source_layer.dataProvider().dataSourceUri())
    
    if not target_ds or not source_ds:
        raise IOError("Could not open one or both raster files with GDAL.")

    target_band = target_ds.GetRasterBand(1)
    source_band = source_ds.GetRasterBand(1)
    
    x_size, y_size = target_ds.RasterXSize, target_ds.RasterYSize
    geotransform = target_ds.GetGeoTransform()
    projection = target_ds.GetProjection()

    layer_name = f"{target_layer.name()}_diff"
    existing = QgsProject.instance().mapLayersByName(layer_name)
    if existing: QgsProject.instance().removeMapLayer(existing[0])
    
    vl = QgsVectorLayer(f"Polygon?crs={target_layer.crs().authid()}", layer_name, "memory")
    provider = vl.dataProvider()
    provider.addAttributes([
        QgsField("orig_val", QVariant.Int),
        QgsField("new_val", QVariant.Int),
        QgsField("change", QVariant.String)
    ])
    vl.updateFields()

    progress = QProgressDialog("Calculating differences...", "Cancel", 0, y_size, iface.mainWindow())
    progress.setWindowModality(Qt.WindowModal)
    progress.setMinimumDuration(0)

    chunk_size = 512
    total_features = 0
    with edit(vl):
        for y in range(0, y_size, chunk_size):
            progress.setValue(y)
            if progress.wasCanceled(): break

            rows_to_read = min(chunk_size, y_size - y)
            target_chunk = target_band.ReadAsArray(0, y, x_size, rows_to_read)
            source_chunk = source_band.ReadAsArray(0, y, x_size, rows_to_read)
            
            diff_mask = target_chunk != source_chunk
            
            nodata_val = target_band.GetNoDataValue()
            if nodata_val is not None:
                diff_mask[target_chunk == nodata_val] = False
                diff_mask[source_chunk == nodata_val] = False

            if not np.any(diff_mask): continue

            mem_driver = gdal.GetDriverByName('MEM')
            diff_ds = mem_driver.Create('', x_size, rows_to_read, 1, gdal.GDT_Byte)
            chunk_geotransform = list(geotransform)
            chunk_geotransform[3] = geotransform[3] + y * geotransform[5]
            diff_ds.SetGeoTransform(tuple(chunk_geotransform))
            diff_ds.SetProjection(projection)
            diff_band = diff_ds.GetRasterBand(1)
            diff_band.WriteArray(diff_mask.astype(np.uint8))
            
            ogr_ds = ogr.GetDriverByName('Memory').CreateDataSource('temp_ogr')
            srs = osr.SpatialReference(); srs.ImportFromWkt(projection)
            ogr_layer = ogr_ds.CreateLayer('poly', srs=srs, geom_type=ogr.wkbPolygon)
            field_defn = ogr.FieldDefn('value', ogr.OFTInteger)
            ogr_layer.CreateField(field_defn)

            gdal.Polygonize(diff_band, diff_band, ogr_layer, 0, [], callback=None)
            
            for ogr_feat in ogr_layer:
                total_features += 1
                geom = ogr_feat.GetGeometryRef()
                qgs_geom = QgsGeometry.fromWkt(geom.ExportToWkt())
                
                centroid = qgs_geom.centroid().asPoint()
                inv_gt = gdal.InvGeoTransform(geotransform)
                px, py = gdal.ApplyGeoTransform(inv_gt, centroid.x(), centroid.y())
                
                local_py = int(py) - y
                local_px = int(px)
                
                orig_val, new_val = -999, -999
                if 0 <= local_py < source_chunk.shape[0] and 0 <= local_px < source_chunk.shape[1]:
                    orig_val = int(source_chunk[local_py, local_px])
                    new_val = int(target_chunk[local_py, local_px])
                
                change_type = "Increase" if new_val > orig_val else "Decrease"
                
                feat = QgsFeature()
                feat.setGeometry(qgs_geom)
                feat.setAttributes([orig_val, new_val, change_type])
                provider.addFeature(feat)

    progress.setValue(y_size)
    progress.close()
    
    if progress.wasCanceled() or total_features == 0:
        return None

    _apply_styling(vl)
    return vl

def _apply_styling(layer):
    """Applies a default categorized style to the difference layer."""
    categories = []
    symbol_increase = QgsSymbol.defaultSymbol(QgsWkbTypes.PolygonGeometry)
    symbol_increase.setColor(Qt.blue)
    symbol_increase.setOpacity(0.6)
    categories.append(QgsRendererCategory("Increase", symbol_increase, "Increase"))
    
    symbol_decrease = QgsSymbol.defaultSymbol(QgsWkbTypes.PolygonGeometry)
    symbol_decrease.setColor(Qt.red)
    symbol_decrease.setOpacity(0.6)
    categories.append(QgsRendererCategory("Decrease", symbol_decrease, "Decrease"))
    
    renderer = QgsCategorizedSymbolRenderer("change", categories)
    layer.setRenderer(renderer)
    layer.triggerRepaint()