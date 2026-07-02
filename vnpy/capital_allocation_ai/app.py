"""
capital_allocation_ai/app.py

Capital Allocation Intelligence System — VeighNa App 注册。
"""

from __future__ import annotations

from vnpy.trader.app import BaseApp

from .constant import APP_NAME, APP_PATH
from .dispatcher import CapitalAllocationEngine


class CapitalAllocationApp(BaseApp):
    """Capital Allocation Intelligence System App。"""

    app_name     = APP_NAME
    app_module   = "vnpy.capital_allocation_ai"
    app_path     = APP_PATH
    display_name = "Capital Allocation AI"
    engine_class = CapitalAllocationEngine
    widget_name  = "CapitalAllocationWidget"
    icon_name    = ""
