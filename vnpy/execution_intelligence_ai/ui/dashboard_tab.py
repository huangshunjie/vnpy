"""
execution_intelligence_ai/ui/dashboard_tab.py  (Phase 1 stub)

DashboardTab — 执行总览面板（Phase 1 空占位）。
"""
from __future__ import annotations
from vnpy.trader.ui import QtWidgets


class DashboardTab(QtWidgets.QWidget):
    """执行总览面板。Phase 2+ 实现 KPI 卡片、执行队列、实时状态。"""

    def __init__(self, engine=None, parent=None) -> None:
        super().__init__(parent)
        self._engine = engine
        layout = QtWidgets.QVBoxLayout(self)
        lbl = QtWidgets.QLabel(
            "Dashboard  执行总览\n\n（Phase 2 实现）")
        lbl.setStyleSheet("color:#6c7086; font-size:18px;")
        lbl.setAlignment(__import__("vnpy.trader.ui", fromlist=["QtCore"])
                         .QtCore.Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(lbl)

    def set_engine(self, engine) -> None:
        self._engine = engine

    def refresh(self) -> None:
        pass
