"""
quant_research/app.py

QuantResearchApp — VeighNa App 注册入口。
"""
from vnpy.trader.app import BaseApp

from .constant import APP_NAME
from .engine import ResearchEngine


class QuantResearchApp(BaseApp):
    """量化研究平台 App。"""

    app_name     = APP_NAME
    app_module   = "vnpy.quant_research"
    app_path     = __file__
    display_name = "Quant Research Platform  量化研究平台"
    engine_class = ResearchEngine
    widget_name  = "ResearchPlatformWidget"
    icon_name    = ""
