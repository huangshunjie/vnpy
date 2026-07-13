"""
screening/app.py

Quant Screening Platform -- VeighNa App registration (Phase 1).
"""

from vnpy.trader.app import BaseApp
from .constant import APP_NAME, APP_PATH
from .engine import ScreeningEngine


class ScreeningApp(BaseApp):
    """Quant Screening Platform App."""

    app_name     = APP_NAME
    app_module   = "vnpy.screening"
    app_path     = APP_PATH
    display_name = "Quant Screening Platform  量化条件选股"
    engine_class = ScreeningEngine
    widget_name  = "ScreeningWidget"
    icon_name    = ""
