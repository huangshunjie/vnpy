"""
K-Line Behavior Lab - 独立启动器

直接启动K-Line Behavior Lab应用
"""
import sys
from PySide6.QtWidgets import QApplication
from vnpy.event import EventEngine
from vnpy.trader.engine import MainEngine
from vnpy.kline_behavior_lab.widget import KLineBehaviorLabWidget


def main():
    """启动K-Line Behavior Lab"""
    # 创建Qt应用
    app = QApplication(sys.argv)
    app.setApplicationName("K-Line Behavior Lab")
    
    # 创建引擎
    event_engine = EventEngine()
    main_engine = MainEngine(event_engine)
    
    # 注册K-Line Behavior Lab应用
    from vnpy.kline_behavior_lab import KLineBehaviorLabApp
    main_engine.add_app(KLineBehaviorLabApp)
    
    # 创建主窗口
    widget = KLineBehaviorLabWidget(main_engine, event_engine)
    widget.show()
    
    # 启动应用
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
