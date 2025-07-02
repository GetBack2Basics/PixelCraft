# pc_plugin.py
from PyQt5.QtWidgets import QAction, QMenu
from qgis.utils import iface

from .ui.pc_dock import PixelCraftDock
from .pc_config import metadata

class PixelCraftPlugin:
    def __init__(self, iface):
        self.iface = iface
        self.plugin_name = metadata.get('general', {}).get('name', 'Plugin')
        menu_group_name = metadata.get('menu', {}).get('group', 'Plugins')
        self.menu_name = f"&{menu_group_name}"
        self.dock_widget = None
        self.menu = None
        self.action = None

    def initGui(self):
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
        if self.action:
            self.menu.removeAction(self.action)
        if self.dock_widget:
            self.iface.removeDockWidget(self.dock_widget)
            self.dock_widget.deleteLater()
            self.dock_widget = None

    def run(self):
        if not self.dock_widget:
            self.dock_widget = PixelCraftDock(self.iface.mainWindow())
        
        self.iface.addDockWidget(1, self.dock_widget)
        self.dock_widget.show()