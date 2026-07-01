"""research_validation/ui/report_tab.py — 验证报告导出（Phase 1 占位）。"""
from __future__ import annotations
from vnpy.trader.ui import QtWidgets


class ReportTab(QtWidgets.QWidget):
    """完整验证报告 Tab（Phase 5 实现）。"""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        v = QtWidgets.QVBoxLayout(self)
        v.setContentsMargins(16, 16, 16, 16)
        lbl = QtWidgets.QLabel(
            "Report（验证报告）\n\nPhase 5 实现：\n"
            "  • 完整验证摘要（PDF/CSV 导出）\n"
            "  • Alpha 真实性综合评分\n"
            "  • 各模块结果汇总表格\n"
            "  • 偏差检测结论"
        )
        lbl.setStyleSheet("color: #6c7086; font-size: 13px;")
        v.addWidget(lbl)
        v.addStretch()
