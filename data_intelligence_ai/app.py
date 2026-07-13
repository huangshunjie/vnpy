"""
data_intelligence_ai/app.py

DataIntelligenceApp — VeighNa App 注册入口。
"""
from vnpy.trader.app import BaseApp

from .constant import APP_NAME
from .engine import GlobalDataEngine


class DataIntelligenceApp(BaseApp):
    """数据智能系统 App。"""

    app_name     = APP_NAME
    app_module   = "vnpy.data_intelligence_ai"
    app_path     = __file__
    display_name = "Data Intelligence AI  数据智能系统"
    engine_class = GlobalDataEngine
    widget_name  = "DataIntelligenceWidget"
    icon_name    = ""
