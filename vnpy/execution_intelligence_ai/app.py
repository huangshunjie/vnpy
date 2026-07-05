"""
execution_intelligence_ai/app.py

Execution Intelligence 2.0 — VeighNa App 注册。
"""

from pathlib import Path
from vnpy.trader.app import BaseApp
from .constant import APP_NAME


class ExecutionIntelligenceApp(BaseApp):
    """Execution Intelligence 2.0 App 注册。"""

    app_name     = APP_NAME
    app_module   = "vnpy.execution_intelligence_ai"
    app_path     = Path(__file__).parent
    display_name = "Execution Intelligence AI  执行智能系统"
    icon_name    = "execution.ico"
    widget_name  = "ExecutionIntelligenceWidget"

    # engine_class 在 engine.py 中定义，延迟导入避免循环
    @property
    def engine_class(self):
        from .dispatcher import ExecutionIntelligenceEngine
        return ExecutionIntelligenceEngine
