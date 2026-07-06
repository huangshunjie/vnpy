"""
cross_market_ai/ui/log_tab.py

Log Tab — 系统日志流。
Phase 1: 功能完整，显示引擎日志。
"""
from __future__ import annotations

from vnpy.event import EventEngine
from vnpy.trader.engine import MainEngine
from vnpy.trader.ui import QtWidgets, QtCore


class LogTab(QtWidgets.QWidget):
    """跨市场系统日志流。"""

    def __init__(self, main_engine: MainEngine, event_engine: EventEngine) -> None:
        super().__init__()
        self._init_ui()

    def _init_ui(self) -> None:
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)

        toolbar = QtWidgets.QHBoxLayout()
        btn_clear = QtWidgets.QPushButton("清空日志")
        btn_clear.clicked.connect(self._on_clear)
        toolbar.addWidget(btn_clear)
        toolbar.addStretch()
        layout.addLayout(toolbar)

        self._text = QtWidgets.QTextEdit()
        self._text.setReadOnly(True)
        self._text.setStyleSheet(
            "background: #1e1e1e; color: #d4d4d4; "
            "font-family: Consolas, monospace; font-size: 12px;"
        )
        layout.addWidget(self._text)

    def append_log(self, line: str) -> None:
        self._text.append(line)
        self._text.verticalScrollBar().setValue(
            self._text.verticalScrollBar().maximum()
        )

    def _on_clear(self) -> None:
        self._text.clear()
