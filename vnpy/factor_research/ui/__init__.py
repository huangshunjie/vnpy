"""
factor_research/ui/__init__.py

ui 子包入口。

VeighNa MainWindow.init_menu() 通过：
    import_module(app.app_module + ".ui")
    getattr(ui_module, app.widget_name)
动态加载 Widget，因此必须在此处导出 FactorResearchWidget。
"""

from .widget import FactorResearchWidget

__all__ = ["FactorResearchWidget"]
