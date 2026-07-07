"""
temporal_intelligence_ai/app.py

TemporalIntelligenceApp — VeighNa App 注册入口。
"""
from vnpy.trader.app import BaseApp

from .constant import APP_NAME
from .temporal_engine import TemporalEngine


class TemporalIntelligenceApp(BaseApp):
    """时间智能系统 App。"""

    app_name     = APP_NAME
    app_module   = "vnpy.temporal_intelligence_ai"
    app_path     = __file__
    display_name = "Temporal Intelligence AI  时间智能系统"
    engine_class = TemporalEngine
    widget_name  = "TemporalIntelligenceWidget"
    icon_name    = ""
