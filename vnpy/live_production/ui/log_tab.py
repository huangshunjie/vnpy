"""live_production/ui/log_tab.py — Logs Tab（Phase 1 占位）。"""
from vnpy.trader.ui import QtCore, QtWidgets

class LogTab(QtWidgets.QWidget):
    def __init__(self, engine=None, parent=None):
        super().__init__(parent)
        self._engine = engine
        v = QtWidgets.QVBoxLayout(self)
        v.setContentsMargins(6, 6, 6, 6)

        lbl = QtWidgets.QLabel("系统日志 Logs")
        lbl.setStyleSheet("color: #6c7086; font-size: 10px;")
        v.addWidget(lbl)

        self._txt = QtWidgets.QTextEdit()
        self._txt.setReadOnly(True)
        self._txt.setStyleSheet(
            "QTextEdit { background: #11111b; color: #cdd6f4;"
            " font-size: 11px; font-family: monospace;"
            " border: 1px solid #45475a; border-radius: 3px; }"
        )
        v.addWidget(self._txt, stretch=1)

    def set_engine(self, engine) -> None:
        self._engine = engine

    def append(self, msg: str) -> None:
        self._txt.append(msg)
        sb = self._txt.verticalScrollBar()
        sb.setValue(sb.maximum())

    def refresh(self) -> None:
        pass
