# functions/pc_inspector.py
from PyQt5.QtCore import pyqtSignal
from qgis.core import QgsProject, QgsRaster, QgsCoordinateTransform
from qgis.gui import QgsMapToolEmitPoint

from ..pc_config import settings

class PixelInspectorTool(QgsMapToolEmitPoint):
    """
    A QGIS map tool that tracks the cursor and emits the values of both the
    configured Target and Source raster layers at the cursor's location.
    """
    # The signal now emits a dictionary with two potential keys.
    values_updated = pyqtSignal(dict)

    def __init__(self, canvas):
        super().__init__(canvas)
        self.canvas = canvas
        self.target_layer = None
        self.source_layer = None
        self._active = False

    def activate(self):
        super().activate()
        self._load_configured_layers() # Note the plural
        self._active = True
        print("TOOL: Pixel Inspector activated.")

    def deactivate(self):
        super().deactivate()
        self._active = False
        print("TOOL: Pixel Inspector deactivated.")

    def _load_configured_layers(self):
        """Loads both the target and source layer objects from settings."""
        target_name = settings.get("raster_layer_name")
        source_name = settings.get("source_raster_layer_name")

        target_layers = QgsProject.instance().mapLayersByName(target_name) if target_name else []
        source_layers = QgsProject.instance().mapLayersByName(source_name) if source_name else []
        
        self.target_layer = target_layers[0] if target_layers else None
        self.source_layer = source_layers[0] if source_layers else None

    def _sample_layer(self, layer, point_in_canvas_crs):
        """Helper function to sample a single raster layer, handling CRS."""
        if not layer:
            return None

        try:
            # Transform point from canvas CRS to layer's CRS
            canvas_crs = self.canvas.mapSettings().destinationCrs()
            layer_crs = layer.crs()
            point_in_layer_crs = point_in_canvas_crs

            if canvas_crs != layer_crs:
                transform = QgsCoordinateTransform(canvas_crs, layer_crs, QgsProject.instance())
                point_in_layer_crs = transform.transform(point_in_canvas_crs)
            
            # Sample the raster value at the point
            ident = layer.dataProvider().identify(point_in_layer_crs, QgsRaster.IdentifyFormatValue)
            if ident and ident.isValid():
                return ident.results().get(1) # Value for Band 1
        except Exception as e:
            print(f"INSPECTOR: Error sampling layer '{layer.name()}': {e}")
        
        return None

    def canvasMoveEvent(self, event):
        """Called on every mouse move; samples both layers and emits the results."""
        if not self._active:
            return

        point = event.mapPoint()
        
        # Sample both layers using the helper function
        target_value = self._sample_layer(self.target_layer, point)
        source_value = self._sample_layer(self.source_layer, point)
        
        # Emit a dictionary containing both values
        self.values_updated.emit({
            'target_value': target_value,
            'source_value': source_value
        })