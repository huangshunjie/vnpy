"""
market_reality_ai/ui/log_tab.py

Phase 1: Simulation Log Stream — 已在 Phase 1 可用。
"""
from __future__ import annotations
from vnpy.trader.ui import QtWidgets, QtGui


class LogTab(QtWidgets.QWidget):
    """
    Simulation Log Stream Tab.
    Phase 1 即时可用：接收并显示所有 eRS_* 事件的日志行。
    """

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setStyleSheet("background:#181825;")
        vb = QtWidgets.QVBoxLayout(self)
        vb.setContentsMargins(10, 8, 10, 8); vb.setSpacing(6)

        hdr = QtWidgets.QHBoxLayout()
        title = QtWidgets.QLabel("Simulation Log Stream")
        title.setStyleSheet(
            "color:#f9e2af;font-size:11px;font-weight:bold;"
            "border:none;background:transparent;")
        hdr.addWidget(title); hdr.addStretch()
        clear_btn = QtWidgets.QPushButton("Clear")
        clear_btn.setFixedHeight(24)
        clear_btn.setStyleSheet(
            "QPushButton{background:#45475a;color:#cdd6f4;"
            "border:none;border-radius:3px;font-size:9px;padding:0 8px;}"
            "QPushButton:hover{background:#585b70;}")
        clear_btn.clicked.connect(self._clear)
        hdr.addWidget(clear_btn)
        vb.addLayout(hdr)

        self._txt = QtWidgets.QPlainTextEdit()
        self._txt.setReadOnly(True)
        self._txt.setMaximumBlockCount(3000)
        self._txt.setFont(QtGui.QFont("Consolas", 9))
        self._txt.setStyleSheet(
            "QPlainTextEdit{background:#1e1e2e;color:#6c7086;"
            "border:1px solid #45475a;border-radius:3px;}")
        vb.addWidget(self._txt)

    def append(self, line: str, level: str = "INFO") -> None:
        c = {"INFO": "#6c7086", "WARNING": "#f9e2af",
             "CRITICAL": "#f38ba8", "ERROR": "#f38ba8"}.get(level, "#6c7086")
        self._txt.appendHtml(f'<span style="color:{c};">{line}</span>')
        sb = self._txt.verticalScrollBar()
        sb.setValue(sb.maximum())

    def _clear(self) -> None:
        self._txt.clear()
