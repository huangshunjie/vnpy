"""
risk_engine_2/app.py

RiskEngine2App — 向 VeighNa MainEngine 注册 Risk Engine 2.0。

使用方式（在 run.py 中）：
    from vnpy.risk_engine_2 import RiskEngine2App
    main_engine.add_app(RiskEngine2App)
"""

from pathlib import Path

from vnpy.trader.app import BaseApp

from .dispatcher import RiskEngine2


class RiskEngine2App(BaseApp):
    """Risk Engine 2.0（机构级风控系统）App 注册入口。"""

    app_name:     str  = "RiskEngine2"
    app_module:   str  = "vnpy.risk_engine_2"
    app_path:     Path = Path(__file__).parent
    display_name: str  = "Risk Engine 2.0"
    engine_class: type = RiskEngine2
    widget_name:  str  = "RiskEngineWidget"
    icon_name:    str  = ""
