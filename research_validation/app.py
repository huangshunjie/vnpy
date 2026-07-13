"""
research_validation/app.py

ResearchValidationApp — 向 VeighNa MainEngine 注册本 App。

VeighNa 的 MainWindow.init_menu() 会自动遍历所有已注册 App，
在"功能"菜单下按 display_name 创建菜单项，无需手动修改 mainwindow.py。

使用方式（在 run.py 中）：
    from vnpy.research_validation import ResearchValidationApp
    main_engine.add_app(ResearchValidationApp)
"""

from pathlib import Path

from vnpy.trader.app import BaseApp

from .dispatcher import ResearchValidationEngine


class ResearchValidationApp(BaseApp):
    """Research Validation System（研究验证体系 2.0）App 注册入口。"""

    app_name:     str  = "ResearchValidation"
    app_module:   str  = "vnpy.research_validation"
    app_path:     Path = Path(__file__).parent
    display_name: str  = "研究验证体系"
    engine_class: type = ResearchValidationEngine
    widget_name:  str  = "ValidationWidget"
    icon_name:    str  = ""
