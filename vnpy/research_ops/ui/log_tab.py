"""
research_ops/ui/log_tab.py  — Phase 1 骨架
"""
from __future__ import annotations
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QTextEdit, QPushButton, QLabel,
)
from PySide6.QtGui import QFont, QColor, QTextCharFormat, QTextCursor
from PySide6.QtCore import Qt

from vnpy.event import Event
from ..main_engine import ResearchOpsEngine
from ..event import EVENT_RO_LOG, EVENT_RO_ERROR


class LogTab(QWidget):
    def __init__(self, engine: ResearchOpsEngine, parent=None):
        super().__init__(parent)
        self._engine = engine
        self._init_ui()
        self._register_events()

    def _init_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(6, 6, 6, 6)

        bar = QHBoxLayout()
        bar.addWidget(QLabel("系统日志"))
        bar.addStretch()
        self._btn_clear = QPushButton("清空")
        self._btn_clear.setFixedWidth(60)
        bar.addWidget(self._btn_clear)
        root.addLayout(bar)

        self._text = QTextEdit()
        self._text.setReadOnly(True)
        self._text.setFont(QFont("Consolas", 10))
        root.addWidget(self._text)

        self._btn_clear.clicked.connect(self._text.clear)

    def _register_events(self):
        ee = self._engine.event_engine
        ee.register(EVENT_RO_LOG,   self._on_log)
        ee.register(EVENT_RO_ERROR, self._on_error)

    def _on_log(self, event: Event):
        self._append(str(event.data), QColor("#212529"))

    def _on_error(self, event: Event):
        self._append(f"[ERROR] {event.data}", QColor("#dc3545"))

    def _append(self, msg: str, color: QColor):
        fmt = QTextCharFormat()
        fmt.setForeground(color)
        cursor = self._text.textCursor()
        cursor.movePosition(QTextCursor.End)
        cursor.insertText(msg + "\n", fmt)
        self._text.setTextCursor(cursor)
        self._text.ensureCursorVisible()

    def append_log(self, msg: str):
        self._append(msg, QColor("#212529"))
