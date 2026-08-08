"""
kline_behavior_lab/app.py

K-Line Behavior Lab VeighNa应用入口
"""
from vnpy.trader.app import BaseApp
from .constant import APP_NAME, APP_PATH
from .engine import KLineBehaviorLabEngine


class KLineBehaviorLabApp(BaseApp):
    """
    K-Line Market Behavior Lab
    
    K线市场行为研究实验室
    - 67个K线特征
    - 8个研究模板
    - 智能条件验证
    - 灵活采样策略
    """
    
    app_name = APP_NAME
    app_module = APP_PATH
    app_path = APP_PATH
    display_name = "K-Line Behavior Lab  K线行为研究实验室"
    engine_class = KLineBehaviorLabEngine
    widget_name = "KLineBehaviorLabWidget"
    icon_name = "behavior.ico"
