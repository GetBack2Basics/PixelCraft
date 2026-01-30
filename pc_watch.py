# pc_watch.py
import os
from PyQt5.QtCore import QObject, pyqtSignal, QFileSystemWatcher
from qgis.core import Qgis
from qgis.utils import iface

from .pc_config import settings

class LayerWatcher(QObject):
    """
    A service that monitors raster layer files for external changes and
    triggers a reload in QGIS. It uses Qt's non-polling QFileSystemWatcher.
    """
    # Signal emitted when the list of watched files changes.
    # The payload is a list of the basenames of the files being watched.
    watch_status_changed = pyqtSignal(list)

    def __init__(self):
        super().__init__()
        self._watchers = {}  # {layer_id: (watcher, path)}
        self._watched_paths = set()

    def start_watching_configured_layers(self):
        """
        Reads layer names from settings and starts watching them.
        Returns True if at least one layer was successfully watched.
        """
        print("WATCHER: Attempting to watch configured layers...")
        layers_to_watch = [
            settings.get("raster_layer_name"),
            settings.get("source_raster_layer_name")
        ]
        
        # Filter out any duplicate or empty names
        unique_layer_names = set(filter(None, layers_to_watch))
        
        success_count = 0
        for layer_name in unique_layer_names:
            if self._watch_layer_by_name(layer_name):
                success_count += 1
        
        return success_count > 0

    def stop_all_watching(self):
        """Stops all active file watchers."""
        print("WATCHER: Stopping all file watching.")
        for layer_id, (watcher, path) in self._watchers.items():
            watcher.removePath(path)
            watcher.fileChanged.disconnect()
        
        self._watchers.clear()
        self._watched_paths.clear()
        self.watch_status_changed.emit([]) # Emit empty list

    def get_watched_files(self):
        """Returns a list of basenames of the files currently being watched."""
        return [os.path.basename(path) for path in self._watched_paths]

    def _watch_layer_by_name(self, layer_name):
        """Internal helper to find a layer by name and start watching it."""
        from qgis.core import QgsProject
        layers = QgsProject.instance().mapLayersByName(layer_name)
        if not layers:
            print(f"WATCHER: Layer '{layer_name}' not found in project.")
            return False

        layer = layers[0]
        layer_id = layer.id()

        # Avoid watching the same layer twice
        if layer_id in self._watchers:
            return True

        path = layer.dataProvider().dataSourceUri()
        if not os.path.isfile(path):
            iface.messageBar().pushMessage(
                "PixelCraft Watcher",
                f"Cannot watch '{layer.name()}' as it is not a local file.",
                level=Qgis.Warning, duration=5)
            return False

        watcher = QFileSystemWatcher([path])
        # Use a lambda to pass the layer object to the reload slot
        watcher.fileChanged.connect(lambda p, l=layer: self._on_file_changed(p, l))
        
        self._watchers[layer_id] = (watcher, path)
        self._watched_paths.add(path)
        
        print(f"WATCHER: Now watching '{os.path.basename(path)}'")
        self.watch_status_changed.emit(self.get_watched_files())
        return True

    def _on_file_changed(self, path, layer):
        """Slot that is called when a watched file is modified."""
        print(f"WATCHER: File change detected for '{os.path.basename(path)}'. Reloading layer '{layer.name()}'.")
        
        # It's good practice to re-add the path, as some systems
        # remove it from the watcher after the first signal.
        watcher = self._watchers.get(layer.id())[0]
        if watcher:
            watcher.addPath(path)

        # Reload the layer's data and refresh the map canvas
        layer.dataProvider().reload()
        layer.triggerRepaint()
        iface.messageBar().pushMessage(
            "PixelCraft",
            f"Layer '{layer.name()}' was reloaded due to external file change.",
            level=Qgis.Success, duration=3)