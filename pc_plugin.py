# pc_plugin.py
from PyQt5.QtWidgets import QAction, QMenu
from qgis.utils import iface

from .ui.pc_dock import PixelCraftDock
from .pc_config import metadata
from .pc_watch import LayerWatcher

class PixelCraftPlugin:
    def __init__(self, iface):
        # ... (init method is unchanged) ...
        self.iface = iface
        self.plugin_name = metadata.get('general', {}).get('name', 'Plugin')
        menu_group_name = metadata.get('menu', {}).get('group', 'Plugins')
        self.menu_name = f"&{menu_group_name}"
        self.layer_watcher = LayerWatcher()
        self.dock_widget = None
        self.menu = None
        self.action = None


    def initGui(self):
        # ... (initGui method is unchanged) ...
        menu_object_name = f"mMenu{self.menu_name.replace('&', '')}"
        self.menu = self.iface.pluginMenu().findChild(QMenu, menu_object_name)
        if not self.menu:
            self.menu = QMenu(self.menu_name, self.iface.pluginMenu())
            self.menu.setObjectName(menu_object_name)
            self.iface.pluginMenu().addMenu(self.menu)

        self.action = QAction(self.plugin_name, self.iface.mainWindow())
        self.action.triggered.connect(self.run)
        self.menu.addAction(self.action)

    def unload(self):
        """Clean up resources when the plugin is unloaded."""
        self.layer_watcher.stop_all_watching()
        
        # --- ENSURE MAP TOOL IS UNSET ---
        # If the dock widget and its inspector tool exist, deactivate it
        if self.dock_widget and self.dock_widget.inspector_tool:
            canvas = self.iface.mapCanvas()
            if canvas.mapTool() == self.dock_widget.inspector_tool:
                # Restore the previous tool or a default pan tool
                if self.dock_widget._previous_tool:
                    canvas.setMapTool(self.dock_widget._previous_tool)
                else: # Fallback in case there was no previous tool
                    from qgis.gui import QgsMapToolPan
                    canvas.setMapTool(QgsMapToolPan(canvas))

        if self.action:
            self.menu.removeAction(self.action)
        if self.dock_widget:
            self.iface.removeDockWidget(self.dock_widget)
            self.dock_widget.deleteLater()
            self.dock_widget = None

    def run(self):
        # ... (run method is unchanged) ...
        if not self.dock_widget:
            self.dock_widget = PixelCraftDock(self.layer_watcher, self.iface.mainWindow())
        
        self.iface.addDockWidget(1, self.dock_widget)
        self.dock_widget.show()