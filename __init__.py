# __init__.py

def classFactory(iface):
    """Load PixelCraftPlugin class from file pc_plugin.py"""
    from .pc_plugin import PixelCraftPlugin
    return PixelCraftPlugin(iface)