"""
execution_intelligence_ai/ui/log_tab.py  (Phase 1)

LogTab — 执行日志流面板。
"""
from __future__ import annotations
from vnpy.trader.ui import QtWidgets, QtCore, QtGui


class LogTab(QtWidgets.QWidget):
    """执行日志面板（Phase 1 完整实现）。"""

    def __init__(self, engine=None, parent=None) -> None:
        super().__init__(parent)
        self._engine = engine
        self._init_ui()

    def set_engine(self, engine) -> None:
        self._engine = engine

    def _init_ui(self) -> None:
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(6)

        hdr = QtWidgets.QLabel("Execution Log  执行日志")
        hdr.setStyleSheet("color:#cba6f7; font-size:12px; font-weight:bold;")
        layout.addWidget(hdr)

        self._log_text = QtWidgets.QPlainTextEdit()
        self._log_text.setReadOnly(True)
        self._log_text.setMaximumBlockCount(2000)
        self._log_text.setFont(QtGui.QFont("Consolas", 9))
        self._log_text.setStyleSheet(
            "QPlainTextEdit { background:#11111b; color:#cdd6f4; "
            "border:1px solid #45475a; border-radius:4px; }")
        layout.addWidget(self._log_text)

        btn_clear = QtWidgets.QPushButton("Clear  清空")
        btn_clear.setFixedWidth(100)
        btn_clear.setStyleSheet(
            "QPushButton { background:transparent; color:#6c7086; "
            "border:1px solid #45475a; border-radius:4px; padding:4px 10px; }"
            "QPushButton:hover { background:#313244; }")
        btn_clear.clicked.connect(self._log_text.clear)
        layout.addWidget(btn_clear)

    def append(self, msg: str) -> None:
        self._log_text.appendPlainText(msg)
        sb = self._log_text.verticalScrollBar()
        sb.setValue(sb.maximum())

    def refresh(self) -> None:
        if self._engine is None:
            return
        try:
            logs = self._engine.get_logs(limit=200)
            self._log_text.clear()
            for line in logs:
                self._log_text.appendPlainText(line)
        except Exception:
            pass
