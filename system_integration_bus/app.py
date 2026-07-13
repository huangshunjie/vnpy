"""
system_integration_bus/app.py
"""
from vnpy.trader.app import BaseApp
from .constant import APP_NAME
from .engine import SystemBusEngine


class SystemIntegrationBusApp(BaseApp):
    app_name     = APP_NAME
    app_module   = "vnpy.system_integration_bus"
    app_path     = __file__
    display_name = "System Integration Bus  系统集成总线"
    engine_class = SystemBusEngine
    widget_name  = "SystemBusWidget"
    icon_name    = ""
