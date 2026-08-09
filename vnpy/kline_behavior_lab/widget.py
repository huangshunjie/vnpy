"""
kline_behavior_lab/widget.py

K-Line Behavior Lab 主窗口
"""
from PySide6.QtWidgets import QWidget, QVBoxLayout, QTabWidget, QLabel
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

from vnpy.trader.ui import QtWidgets
from vnpy.trader.engine import MainEngine, EventEngine
from vnpy.quant_research.engine import ResearchEngine

# 延迟导入以避免循环依赖:
# kline_behavior_lab.ui.__init__ -> widget.py -> behavior_tab -> kline_behavior_lab.ui.pattern_stats_tab
# 使用函数内导入代替顶层导入


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
        # 延迟导入避免循环依赖
        from vnpy.quant_research.ui.behavior_tab import BehaviorResearchTab

        self.setWindowTitle("K-Line Behavior Lab - K线行为研究实验室")
        self.resize(1400, 900)
        
        # 主布局
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # 使用 QTabWidget 组织多个功能 Tab
        self.tab_widget = QTabWidget()
        self.tab_widget.setStyleSheet("""
            QTabWidget::pane {
                border: none;
            }
            QTabBar::tab {
                background-color: #2d2d2d;
                color: #a0a0a0;
                padding: 8px 20px;
                margin-right: 2px;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
                font-size: 12px;
            }
            QTabBar::tab:selected {
                background-color: #1e1e1e;
                color: #ffffff;
                border-bottom: 2px solid #0d6efd;
            }
            QTabBar::tab:hover {
                background-color: #383838;
                color: #e0e0e0;
            }
        """)
        
        # Tab 1: 研究工作台（原有功能）
        self.behavior_tab = BehaviorResearchTab(self.research_engine, self)
        self.tab_widget.addTab(self.behavior_tab, "🔬 研究工作台 Research")
        
        layout.addWidget(self.tab_widget)
        self.setLayout(layout)
    
    def refresh_pattern_stats(self):
        """刷新形态统计 - 委托给研究工作台内嵌的形态统计 tab"""
        if hasattr(self.behavior_tab, '_pattern_stats_tab'):
            self.behavior_tab._pattern_stats_tab.on_refresh()

    def on_research_complete(self, events_bars: dict, event_indices: dict):
        """研究完成回调 - 更新内嵌形态统计"""
        if hasattr(self.behavior_tab, '_pattern_stats_tab'):
            self.behavior_tab._pattern_stats_tab.update_stats(events_bars, event_indices)
    
    def show(self):
        """显示窗口"""
        super().show()
        # 通过main_engine记录日志（修复write_log调用）
        if self.main_engine:
            self.main_engine.write_log("K-Line Behavior Lab opened")
