"""
strategy_condition/app.py
VeighNa App 注册入口
"""
from vnpy.trader.app import BaseApp
from .constant import APP_NAME, APP_PATH
from .engine_main import StrategyConditionEngine


class StrategyConditionApp(BaseApp):
    """量化策略条件引擎 App"""

    app_name     = APP_NAME
    app_module   = APP_PATH
    app_path     = APP_PATH
    display_name = "Strategy Condition Engine  量化策略条件引擎"
    engine_class = StrategyConditionEngine
    widget_name  = "StrategyConditionWidget"
    icon_name    = ""
