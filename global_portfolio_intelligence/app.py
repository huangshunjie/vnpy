"""
global_portfolio_intelligence/app.py

GlobalPortfolioIntelligenceApp — VeighNa App 注册入口。
在 run.py 中通过 main_engine.add_app(GlobalPortfolioIntelligenceApp) 注册。
"""
from vnpy.trader.app import BaseApp

from .constant import APP_NAME
from .engine import GlobalPortfolioEngine


class GlobalPortfolioIntelligenceApp(BaseApp):
    """全局组合智能系统 App。"""

    app_name     = APP_NAME
    app_module   = "vnpy.global_portfolio_intelligence"
    app_path     = __file__
    display_name = "Global Portfolio Intelligence 全局组合智能"
    engine_class = GlobalPortfolioEngine
    widget_name  = "GlobalPortfolioWidget"
    icon_name    = ""
