"""
quant_os/app.py

QuantOSApp — 向 VeighNa MainEngine 注册 Quant OS。

使用方式（在 run.py 中）：
    from vnpy.quant_os import QuantOSApp
    main_engine.add_app(QuantOSApp)
"""

from pathlib import Path

from vnpy.trader.app import BaseApp

from .dispatcher import QuantOSEngine


class QuantOSApp(BaseApp):
    """Quant OS — 量化操作系统 App 注册入口。"""

    app_name:     str  = "QuantOS"
    app_module:   str  = "vnpy.quant_os"
    app_path:     Path = Path(__file__).parent
    display_name: str  = "量化操作系统"
    engine_class: type = QuantOSEngine
    widget_name:  str  = "QuantOSWidget"
    icon_name:    str  = ""
