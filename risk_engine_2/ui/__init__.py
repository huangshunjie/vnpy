"""
risk_engine_2/ui/__init__.py

导出 UI 组件，供 VeighNa MainWindow 通过 getattr(ui_module, widget_name) 加载。
"""

from .widget import RiskEngineWidget
from .overview_tab import OverviewTab
from .exposure_tab import ExposureTab
from .drawdown_tab import DrawdownTab
from .limit_tab import LimitTab
from .alert_tab import AlertTab
from .report_tab import ReportTab

__all__ = [
    "RiskEngineWidget",
    "OverviewTab",
    "ExposureTab",
    "DrawdownTab",
    "LimitTab",
    "AlertTab",
    "ReportTab",
]
