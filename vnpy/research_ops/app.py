"""
research_ops/app.py

ResearchOpsApp — VeighNa 插件注册入口。
菜单路径：功能 → Quant Research Platform 2.0
"""
from vnpy.trader.app import BaseApp

from .constant import APP_NAME
from .main_engine import ResearchOpsEngine


class ResearchOpsApp(BaseApp):
    app_name     = APP_NAME
    app_module   = "vnpy.research_ops"
    app_path     = __file__
    display_name = "ResearchOps Platform 2.0  机构级量化研发操作系统"
    engine_class = ResearchOpsEngine
    widget_name  = "ResearchOpsWidget"
    icon_name    = ""
