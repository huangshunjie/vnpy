"""
system_console/app.py
"""
from vnpy.trader.app import BaseApp
from .constant import APP_NAME
from .engine import SystemConsoleEngine


class SystemConsoleApp(BaseApp):
    app_name     = APP_NAME
    app_module   = "vnpy.system_console"
    app_path     = __file__
    display_name = "System Console  全系统主控台"
    engine_class = SystemConsoleEngine
    widget_name  = "SystemConsoleWindow"
    icon_name    = ""
