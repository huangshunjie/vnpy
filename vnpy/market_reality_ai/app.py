"""
market_reality_ai/app.py

Market Reality Simulation System — VeighNa App 注册。
Phase 1: 完整注册，集成 VeighNa Trader 菜单。
"""
from vnpy.trader.app import BaseApp
from .constant import APP_NAME
from .engine_main import RealitySimulationEngine


class MarketRealityApp(BaseApp):
    app_name     = APP_NAME
    app_module   = "vnpy.market_reality_ai"
    app_path     = __file__
    display_name = "Market Reality AI  市场现实仿真系统"
    engine_class = RealitySimulationEngine
    widget_name  = "RealitySimulationWidget"
    icon_name    = ""
