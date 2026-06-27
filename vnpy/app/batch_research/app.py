"""
BatchResearch App 注册入口

向 VeighNa MainEngine 注册本 App，并声明 GUI 入口 Widget。
"""

from pathlib import Path

from vnpy.trader.app import BaseApp

from .engine import BatchResearchEngine


class BatchResearchApp(BaseApp):
    """"""

    app_name: str = "BatchResearch"
    app_module: str = "vnpy.app.batch_research"
    app_path: Path = Path(__file__).parent
    display_name: str = "批量回测研究"
    engine_class: type = BatchResearchEngine
    widget_name: str = "BatchResearchWidget"
    icon_name: str = ""
