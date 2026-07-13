"""
backtest_bridge/app.py
"""
from vnpy.trader.app import BaseApp
from .constant import APP_NAME
from .engine import BacktestBridgeEngine


class BacktestBridgeApp(BaseApp):
    app_name     = APP_NAME
    app_module   = "vnpy.backtest_bridge"
    app_path     = __file__
    display_name = "Backtest Bridge  信号回测桥"
    engine_class = BacktestBridgeEngine
    widget_name  = "BacktestBridgeWidget"
    icon_name    = ""
