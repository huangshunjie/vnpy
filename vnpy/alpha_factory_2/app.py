"""
alpha_factory_2/app.py

AlphaFactory2App — VeighNa App 注册（Phase 1）。
"""

from vnpy.trader.app import BaseApp
from .constant import APP_NAME, APP_PATH
from .dispatcher import AlphaFactoryEngine


class AlphaFactory2App(BaseApp):
    app_name     = APP_NAME
    app_module   = "vnpy.alpha_factory_2"
    app_path     = APP_PATH
    display_name = "Alpha Factory 2.0  工业化Alpha生产系统"
    engine_class = AlphaFactoryEngine
    widget_name  = "AlphaFactoryWidget"
    icon_name    = ""
