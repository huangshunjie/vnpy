"""
research_validation/ui/__init__.py

导出 UI 组件，供 VeighNa MainWindow 通过 getattr(ui_module, widget_name) 加载。
"""

from .widget          import ValidationWidget
from .overview_tab    import OverviewTab
from .walkforward_tab import WalkForwardTab
from .oos_tab         import OOSTab
from .regime_tab      import RegimeTab
from .stability_tab   import StabilityTab
from .bias_tab        import BiasTab
from .report_tab      import ReportTab

__all__ = [
    "ValidationWidget",
    "OverviewTab",
    "WalkForwardTab",
    "OOSTab",
    "RegimeTab",
    "StabilityTab",
    "BiasTab",
    "ReportTab",
]
