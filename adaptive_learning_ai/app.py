"""
adaptive_learning_ai/app.py

AdaptiveLearningApp — VeighNa App 注册入口。
"""
from vnpy.trader.app import BaseApp

from .constant import APP_NAME
from .engine import GlobalLearningEngine


class AdaptiveLearningApp(BaseApp):
    """自适应学习系统 App。"""

    app_name     = APP_NAME
    app_module   = "vnpy.adaptive_learning_ai"
    app_path     = __file__
    display_name = "Adaptive Learning AI  自适应学习系统"
    engine_class = GlobalLearningEngine
    widget_name  = "AdaptiveLearningWidget"
    icon_name    = ""
