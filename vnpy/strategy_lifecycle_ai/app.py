"""
strategy_lifecycle_ai/app.py  (Phase 1)

Strategy Lifecycle Intelligence System — VeighNa App 注册。
"""

from pathlib import Path

from vnpy.trader.app import BaseApp

from .constant import APP_NAME
from .dispatcher import LifecycleEngine


class StrategyLifecycleApp(BaseApp):
    """Strategy Lifecycle Intelligence System App。"""

    app_name    = APP_NAME
    app_module  = "vnpy.strategy_lifecycle_ai"
    app_path    = Path(__file__).parent
    display_name = "Strategy Lifecycle AI  策略生命周期智能系统"
    engine_class = LifecycleEngine
    widget_name  = "StrategyLifecycleWidget"
    icon_name    = "lifecycle.ico"
