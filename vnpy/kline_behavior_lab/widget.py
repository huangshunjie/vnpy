"""
kline_behavior_lab/widget.py

K-Line Behavior Lab 主窗口
"""
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

from vnpy.trader.ui import QtWidgets
from vnpy.trader.engine import MainEngine, EventEngine

# 导入已开发的BehaviorResearchTab
from vnpy.quant_research.ui.behavior_tab import BehaviorResearchTab
from vnpy.quant_research.engine import ResearchEngine


class KLineBehaviorLabWidget(QWidget):
    """K-Line Behavior Lab 主窗口"""
    
    def __init__(self, main_engine: MainEngine, event_engine: EventEngine):
        super().__init__()
        
        self.main_engine = main_engine
        self.event_engine = event_engine
        self.engine = main_engine.get_engine("KLineBehaviorLab")
        
        # 创建或获取ResearchEngine实例
        self.research_engine = self._get_research_engine()
        
        self.init_ui()
    
    def _get_research_engine(self) -> ResearchEngine:
        """获取或创建ResearchEngine实例"""
        try:
            # 尝试从quant_research应用获取
            research_engine = self.main_engine.get_engine("QuatResearch")
            if research_engine:
                return research_engine
        except:
            pass
        
        # 创建新的ResearchEngine实例
        return ResearchEngine(self.main_engine, self.event_engine)
    
    def init_ui(self):
        """初始化UI"""
        self.setWindowTitle("K-Line Behavior Lab - K线行为研究实验室")
        self.resize(1400, 900)
        
        # 主布局
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # 主内容区 - 直接使用已开发的BehaviorResearchTab
        self.behavior_tab = BehaviorResearchTab(self.research_engine, self)
        layout.addWidget(self.behavior_tab)
        
        self.setLayout(layout)
    
    def _create_header(self) -> QWidget:
        """创建标题栏"""
        header = QWidget()
        header.setStyleSheet("""
            QWidget {
                background-color: #1e1e1e;
                border-bottom: 2px solid #0d6efd;
            }
        """)
        header.setFixedHeight(60)
        
        layout = QVBoxLayout(header)
        layout.setContentsMargins(20, 10, 20, 10)
        
        # 标题
        title = QLabel("🔬 K-Line Market Behavior Lab")
        title.setFont(QFont("", 16, QFont.Bold))
        title.setStyleSheet("color: white; border: none;")
        layout.addWidget(title)
        
        # 副标题
        subtitle = QLabel(f"K线行为研究实验室 | {self.engine.get_feature_count()}个特征 | {self.engine.get_template_count()}个模板")
        subtitle.setFont(QFont("", 10))
        subtitle.setStyleSheet("color: #a0a0a0; border: none;")
        layout.addWidget(subtitle)
        
        return header
    
    def show(self):
        """显示窗口"""
        super().show()
        self.engine.write_log("K-Line Behavior Lab opened")
