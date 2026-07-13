"""
quant_research/ui/log_tab.py  — Phase 1 空框架
"""
from __future__ import annotations
from PySide6.QtWidgets import QWidget, QVBoxLayout, QTextEdit


class LogTab(QWidget):
    def __init__(self, engine, parent=None):
        super().__init__(parent)
        self.engine = engine
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        self._log_edit = QTextEdit()
        self._log_edit.setReadOnly(True)
        self._log_edit.setPlaceholderText("系统日志将在此显示...")
        layout.addWidget(self._log_edit)

    def append(self, msg: str) -> None:
        self._log_edit.append(msg)
