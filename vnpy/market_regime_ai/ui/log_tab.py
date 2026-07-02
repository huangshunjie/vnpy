"""
market_regime_ai/ui/log_tab.py  (Phase 1)

LogTab — 日志面板（Phase 1）。
"""

from __future__ import annotations
from vnpy.trader.ui import QtCore, QtWidgets

_PANEL_BG = "#181825"
_BORDER   = "#45475a"
_FG       = "#cdd6f4"
_MUT      = "#6c7086"
_GRN      = "#a6e3a1"


class LogTab(QtWidgets.QWidget):
    """日志面板（Phase 1 可用）。"""

    def __init__(self, engine=None, parent=None) -> None:
        super().__init__(parent)
        self._engine = engine
        self._init_ui()

    def set_engine(self, engine) -> None:
        self._engine = engine

    def _init_ui(self) -> None:
        v = QtWidgets.QVBoxLayout(self)
        v.setContentsMargins(8, 8, 8, 8)
        v.setSpacing(6)

        lbl = QtWidgets.QLabel("Engine Logs  引擎日志")
        lbl.setStyleSheet(f"color: {_MUT}; font-size: 10px;")
        v.addWidget(lbl)

        self._log_text = QtWidgets.QPlainTextEdit()
        self._log_text.setReadOnly(True)
        self._log_text.setStyleSheet(
            f"background: #11111b; color: {_GRN};"
            f" border: 1px solid {_BORDER}; border-radius: 4px;"
            f" font-family: Consolas, monospace; font-size: 11px;"
        )
        v.addWidget(self._log_text, stretch=1)

        bar = QtWidgets.QWidget()
        bar.setFixedHeight(38)
        h = QtWidgets.QHBoxLayout(bar)
        h.setContentsMargins(0, 0, 0, 0)
        h.setSpacing(6)
        refresh_btn = QtWidgets.QPushButton("刷新 Refresh")
        refresh_btn.setStyleSheet(
            f"QPushButton {{ background: transparent; color: {_MUT};"
            f" border: 1px solid {_BORDER}; border-radius: 3px;"
            f" padding: 4px 14px; font-size: 12px; }}"
            f"QPushButton:hover {{ color: {_FG}; }}"
        )
        refresh_btn.clicked.connect(self.refresh)
        clear_btn = QtWidgets.QPushButton("清空 Clear")
        clear_btn.setStyleSheet(refresh_btn.styleSheet())
        clear_btn.clicked.connect(self._log_text.clear)
        h.addWidget(refresh_btn)
        h.addWidget(clear_btn)
        h.addStretch()
        v.addWidget(bar)

    def refresh(self) -> None:
        if self._engine is None:
            return
        try:
            logs = self._engine.get_logs(limit=200)
        except Exception:
            return
        self._log_text.setPlainText("\n".join(logs))
        sb = self._log_text.verticalScrollBar()
        sb.setValue(sb.maximum())

    def append_log(self, msg: str) -> None:
        self._log_text.appendPlainText(msg)
        sb = self._log_text.verticalScrollBar()
        sb.setValue(sb.maximum())
