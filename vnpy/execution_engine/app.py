"""
execution_engine/app.py

ExecutionEngineApp — 向 VeighNa MainEngine 注册本 App。

使用方式（在 run.py 中）：
    from vnpy.execution_engine import ExecutionEngineApp
    main_engine.add_app(ExecutionEngineApp)
"""

from pathlib import Path

from vnpy.trader.app import BaseApp

from .dispatcher import ExecutionEngine


class ExecutionEngineApp(BaseApp):
    """Execution Engine（交易执行系统）App 注册入口。"""

    app_name:     str  = "ExecutionEngine"
    app_module:   str  = "vnpy.execution_engine"
    app_path:     Path = Path(__file__).parent
    display_name: str  = "交易执行系统"
    engine_class: type = ExecutionEngine
    widget_name:  str  = "ExecutionWidget"
    icon_name:    str  = ""
