"""
market_regime_ai/app.py

Market Regime Intelligence System — VeighNa App 注册（Phase 1）。
"""

from vnpy.trader.app import BaseApp
from .constant import APP_NAME, APP_PATH
from .dispatcher import MarketRegimeEngine


class MarketRegimeApp(BaseApp):
    """Market Regime Intelligence System App。"""

    app_name     = APP_NAME
    app_module   = "vnpy.market_regime_ai"
    app_path     = APP_PATH
    display_name = "Market Regime AI  市场状态智能"
    engine_class = MarketRegimeEngine
    widget_name  = "MarketRegimeWidget"
    icon_name    = ""
