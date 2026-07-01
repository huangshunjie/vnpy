"""
factor_research/app.py

FactorResearchApp — 向 VeighNa MainEngine 注册本 App。

VeighNa 的 MainWindow.init_menu() 会自动遍历所有已注册 App，
在"功能"菜单下按 display_name 创建菜单项，无需手动修改 mainwindow.py。

使用方式（在 run.py 中）：
    from vnpy.factor_research import FactorResearchApp
    main_engine.add_app(FactorResearchApp)
"""

from pathlib import Path

from vnpy.trader.app import BaseApp

from .dispatcher import FactorResearchEngine


class FactorResearchApp(BaseApp):
    """Factor Research（因子研究工作台）App 注册入口。"""

    app_name: str = "FactorResearch"
    app_module: str = "vnpy.factor_research"
    app_path: Path = Path(__file__).parent
    display_name: str = "因子研究工作台"
    engine_class: type = FactorResearchEngine
    widget_name: str = "FactorResearchWidget"
    icon_name: str = ""
