"""
live_production/app.py

LiveProductionApp — VeighNa App 注册（Phase 1）。
"""

from vnpy.trader.app import BaseApp
from .constant import APP_NAME, APP_PATH
from .dispatcher import LiveProductionEngine


class LiveProductionApp(BaseApp):
    app_name    = APP_NAME
    app_module  = __module__
    app_path    = APP_PATH
    display_name = "实盘生产系统  Live Production"
    engine_class = LiveProductionEngine
    widget_name  = "LiveProductionWidget"
    icon_name    = ""
