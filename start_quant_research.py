"""
量化研究平台 - 独立启动脚本

直接启动量化研究平台，无需打开完整的VN Trader
"""

from PySide6.QtWidgets import QApplication
import sys

# 设置路径
sys.path.insert(0, r'c:\Users\11229\Documents\GitHub\vnpy')

from vnpy.event import EventEngine
from vnpy.trader.engine import MainEngine
from vnpy.quant_research.engine import ResearchEngine
from vnpy.quant_research.ui.widget import ResearchPlatformWidget

def main():
    """启动量化研究平台"""
    print("=" * 60)
    print("启动量化研究平台...")
    print("=" * 60)
    
    # 创建应用
    app = QApplication(sys.argv)
    app.setApplicationName("量化研究平台")
    
    # 创建引擎
    event_engine = EventEngine()
    main_engine = MainEngine(event_engine)
    
    # 创建研究引擎
    research_engine = ResearchEngine(main_engine, event_engine)
    
    # 创建并显示主窗口
    research_widget = ResearchPlatformWidget(main_engine, event_engine)
    research_widget.setWindowTitle("VeighNa 量化研究平台")
    research_widget.showMaximized()
    
    print("量化研究平台已启动！")
    print("=" * 60)
    
    # 运行应用
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
