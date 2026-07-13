"""capital_allocation_ai/ui/log_tab.py — 日志面板（Phase 1 占位）。"""
from vnpy.trader.ui import QtWidgets, QtCore

class LogTab(QtWidgets.QWidget):
    def __init__(self, engine=None, parent=None):
        super().__init__(parent)
        self._engine = engine
        v = QtWidgets.QVBoxLayout(self)
        lbl = QtWidgets.QLabel("System Logs  —  Phase 1 实现")
        lbl.setStyleSheet("color:#6c7086; font-size:14px;")
        lbl.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        v.addWidget(lbl)
        self._txt = QtWidgets.QPlainTextEdit()
        self._txt.setReadOnly(True)
        self._txt.setStyleSheet(
            "background:#11111b; color:#a6e3a1; font-family:monospace;"
            " font-size:11px; border:1px solid #45475a;"
        )
        v.addWidget(self._txt, stretch=1)

    def set_engine(self, engine):
        self._engine = engine

    def refresh(self):
        if self._engine is None:
            return
        logs = self._engine.get_logs(limit=200)
        self._txt.setPlainText("\n".join(logs))
        # 滚动到底部
        sb = self._txt.verticalScrollBar()
        sb.setValue(sb.maximum())
