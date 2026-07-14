"""
market_behavior/app.py
MarketBehaviorApp — VeighNa App 接入
"""
from vnpy.trader.app import BaseApp
from .constant import APP_NAME, APP_PATH
from .engine_main import MarketBehaviorEngine


class MarketBehaviorApp(BaseApp):
    """Quant Market Behavior Engine App."""

    app_name     = APP_NAME
    app_module   = APP_PATH
    app_path     = APP_PATH
    display_name = "Market Behavior Engine  量化市场行为分析引擎"
    engine_class = MarketBehaviorEngine
    widget_name  = "MarketBehaviorWidget"
    icon_name    = ""
