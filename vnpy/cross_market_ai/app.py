"""
cross_market_ai/app.py

Cross-Market Intelligence System — VeighNa App 注册。
Phase 1: 完整注册，集成 VeighNa Trader 菜单。
"""
from pathlib import Path

from vnpy.trader.app import BaseApp

from .constant import APP_NAME
from .engine import CrossMarketEngine


class CrossMarketApp(BaseApp):
    app_name     = APP_NAME
    app_module   = "vnpy.cross_market_ai"
    app_path     = Path(__file__).parent
    display_name = "Cross-Market AI  跨市场智能系统"
    engine_class = CrossMarketEngine
    widget_name  = "CrossMarketWidget"
    icon_name    = ""
