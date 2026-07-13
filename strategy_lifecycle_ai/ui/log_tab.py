"""
strategy_lifecycle_ai/ui/log_tab.py  (Phase 1 Stub)

LogTab — 事件日志流面板。
"""

from __future__ import annotations
from vnpy.trader.ui import QtCore, QtWidgets

_PANEL  = "#181825"
_BORDER = "#45475a"
_FG     = "#cdd6f4"
_MUT    = "#6c7086"
_MAV    = "#cba6f7"
_GRN    = "#a6e3a1"


class LogTab(QtWidgets.QWidget):
    """事件日志流面板（Phase 1）。"""

    def __init__(self, engine=None, parent=None) -> None:
        super().__init__(parent)
        self._engine = engine
        self._init_ui()

    def set_engine(self, engine) -> None:
        self._engine = engine

    def _init_ui(self) -> None:
        root = QtWidgets.QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(8)

        title = QtWidgets.QLabel("Event Log Stream  事件日志流")
        title.setStyleSheet(
            f"color: {_MAV}; font-size: 13px; font-weight: bold;")
        root.addWidget(title)

        self._log_view = QtWidgets.QPlainTextEdit()
        self._log_view.setReadOnly(True)
        self._log_view.setStyleSheet(f"""
            QPlainTextEdit {{
                background: #11111b; color: {_FG};
                border: 1px solid {_BORDER}; border-radius: 4px;
                font-family: Consolas, monospace; font-size: 11px;
            }}
        """)
        root.addWidget(self._log_view, stretch=1)

        bar = QtWidgets.QHBoxLayout()
        btn = QtWidgets.QPushButton("Refresh  刷新")
        btn.setStyleSheet(f"""
            QPushButton {{ background: transparent; color: {_MUT};
                border: 1px solid {_MUT}; border-radius: 4px;
                padding: 4px 16px; font-size: 11px; }}
            QPushButton:hover {{ background: {_MUT}22; }}
        """)
        btn.clicked.connect(self.refresh)
        clr = QtWidgets.QPushButton("Clear  清空")
        clr.setStyleSheet(btn.styleSheet())
        clr.clicked.connect(self._log_view.clear)
        bar.addWidget(btn)
        bar.addWidget(clr)
        bar.addStretch()
        root.addLayout(bar)

    def refresh(self) -> None:
        if self._engine is None:
            return
        try:
            logs = self._engine.get_logs(limit=500)
            self._log_view.setPlainText("\n".join(logs))
            sb = self._log_view.verticalScrollBar()
            sb.setValue(sb.maximum())
        except Exception:
            pass

    def append_log(self, msg: str) -> None:
        self._log_view.appendPlainText(msg)
        sb = self._log_view.verticalScrollBar()
        sb.setValue(sb.maximum())
