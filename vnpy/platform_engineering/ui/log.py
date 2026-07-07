"""
platform_engineering/ui/log.py
LogTab — Phase 2
订阅平台所有事件，滚动显示日志流
"""
from __future__ import annotations
from datetime import datetime
from typing import TYPE_CHECKING, List

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QComboBox, QFrame, QTableWidget,
    QTableWidgetItem, QHeaderView, QAbstractItemView,
    QLineEdit,
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QColor, QBrush

if TYPE_CHECKING:
    from ..engine_main import PlatformEngine

from ..event import (
    EVENT_PE_METRIC_UPDATED, EVENT_PE_ALERT_TRIGGERED,
    EVENT_PE_ALERT_RESOLVED, EVENT_PE_HEALTH_UPDATED,
    EVENT_PE_TASK_CREATED, EVENT_PE_TASK_STARTED,
    EVENT_PE_TASK_COMPLETED, EVENT_PE_TASK_FAILED,
    EVENT_PE_TASK_CANCELLED, EVENT_PE_TASK_TIMEOUT,
    EVENT_PE_DEPLOY_CREATED, EVENT_PE_DEPLOY_STAGED,
    EVENT_PE_DEPLOY_LIVE, EVENT_PE_DEPLOY_PAUSED,
    EVENT_PE_DEPLOY_ROLLED_BACK, EVENT_PE_DEPLOY_RETIRED,
    EVENT_PE_CONFIG_CREATED, EVENT_PE_CONFIG_UPDATED,
    EVENT_PE_CONFIG_ROLLED_BACK,
    EVENT_PE_USER_CREATED, EVENT_PE_LOGIN_SUCCESS,
    EVENT_PE_LOGIN_FAILED, EVENT_PE_PERMISSION_DENIED,
    EVENT_PE_AUDIT_LOGGED,
    EVENT_PE_ENGINE_STARTED, EVENT_PE_ENGINE_STOPPED,
    EVENT_PE_ERROR, EVENT_PE_LOG,
)

# level colour map
_EV_LEVEL = {
    EVENT_PE_ALERT_TRIGGERED:  ("ERROR",   "#ff4d4f"),
    EVENT_PE_ALERT_RESOLVED:   ("INFO",    "#52c41a"),
    EVENT_PE_TASK_FAILED:      ("ERROR",   "#ff4d4f"),
    EVENT_PE_TASK_TIMEOUT:     ("WARN",    "#faad14"),
    EVENT_PE_DEPLOY_ROLLED_BACK: ("WARN",  "#faad14"),
    EVENT_PE_PERMISSION_DENIED:("ERROR",   "#ff4d4f"),
    EVENT_PE_LOGIN_FAILED:     ("WARN",    "#faad14"),
    EVENT_PE_ERROR:            ("ERROR",   "#ff4d4f"),
}
_DEFAULT_LEVEL = ("INFO", "#1890ff")

_ALL_EVENTS = [
    EVENT_PE_METRIC_UPDATED, EVENT_PE_ALERT_TRIGGERED,
    EVENT_PE_ALERT_RESOLVED, EVENT_PE_HEALTH_UPDATED,
    EVENT_PE_TASK_CREATED, EVENT_PE_TASK_STARTED,
    EVENT_PE_TASK_COMPLETED, EVENT_PE_TASK_FAILED,
    EVENT_PE_TASK_CANCELLED, EVENT_PE_TASK_TIMEOUT,
    EVENT_PE_DEPLOY_CREATED, EVENT_PE_DEPLOY_STAGED,
    EVENT_PE_DEPLOY_LIVE, EVENT_PE_DEPLOY_PAUSED,
    EVENT_PE_DEPLOY_ROLLED_BACK, EVENT_PE_DEPLOY_RETIRED,
    EVENT_PE_CONFIG_CREATED, EVENT_PE_CONFIG_UPDATED,
    EVENT_PE_CONFIG_ROLLED_BACK,
    EVENT_PE_USER_CREATED, EVENT_PE_LOGIN_SUCCESS,
    EVENT_PE_LOGIN_FAILED, EVENT_PE_PERMISSION_DENIED,
    EVENT_PE_AUDIT_LOGGED,
    EVENT_PE_ENGINE_STARTED, EVENT_PE_ENGINE_STOPPED,
    EVENT_PE_ERROR, EVENT_PE_LOG,
]

MAX_LOG_ROWS = 500


class LogEntry:
    __slots__ = ("ts", "level", "color", "event_type", "message")
    def __init__(self, ts, level, color, event_type, message):
        self.ts = ts; self.level = level; self.color = color
        self.event_type = event_type; self.message = message


class LogTab(QWidget):
    def __init__(self, engine=None, parent=None):
        super().__init__(parent)
        self._engine  = engine
        self._entries: List[LogEntry] = []
        self._paused  = False
        self._filter_level = "ALL"
        self._filter_kw    = ""
        self._init_ui()
        if engine:
            self._register_events()

    def _init_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(8)

        # header
        hdr = QHBoxLayout()
        title = QLabel("\U0001f4cb  Platform Logs")
        title.setStyleSheet("font-size:16px;font-weight:bold;color:#1a1f36;")
        hdr.addWidget(title); hdr.addStretch()

        self._kw_box = QLineEdit()
        self._kw_box.setPlaceholderText("\u5173\u952e\u8bcd\u8fc7\u6ee4")
        self._kw_box.setFixedHeight(26); self._kw_box.setFixedWidth(160)
        self._kw_box.textChanged.connect(self._on_kw_changed)
        hdr.addWidget(self._kw_box)

        self._level_combo = QComboBox()
        for lv in ("ALL", "INFO", "WARN", "ERROR"):
            self._level_combo.addItem(lv)
        self._level_combo.setFixedHeight(26)
        self._level_combo.currentTextChanged.connect(self._on_level_changed)
        hdr.addWidget(self._level_combo)

        self._btn_pause = QPushButton("\u23f8 \u6682\u505c")
        self._btn_pause.setCheckable(True)
        self._btn_pause.setFixedSize(68, 26)
        self._btn_pause.setStyleSheet(
            "background:#faad14;color:#fff;border-radius:4px;"
            "font-size:12px;border:none;")
        self._btn_pause.toggled.connect(self._on_pause)
        hdr.addWidget(self._btn_pause)

        btn_clear = QPushButton("\U0001f5d1 \u6e05\u7a7a")
        btn_clear.setFixedSize(68, 26)
        btn_clear.setStyleSheet(
            "background:#ff4d4f;color:#fff;border-radius:4px;"
            "font-size:12px;border:none;")
        btn_clear.clicked.connect(self._on_clear)
        hdr.addWidget(btn_clear)
        root.addLayout(hdr)

        # log table
        self._table = QTableWidget(0, 4)
        self._table.setHorizontalHeaderLabels(
            ["\u65f6\u95f4", "\u7ea7\u522b", "\u4e8b\u4ef6", "\u6d88\u606f"])
        hdr_view = self._table.horizontalHeader()
        hdr_view.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        hdr_view.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        hdr_view.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        hdr_view.setSectionResizeMode(3, QHeaderView.Stretch)
        self._table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._table.setAlternatingRowColors(True)
        self._table.verticalHeader().setVisible(False)
        self._table.setSelectionBehavior(QAbstractItemView.SelectRows)
        root.addWidget(self._table, 1)

        # status bar
        self._status = QLabel("0 \u6761\u65e5\u5fd7")
        self._status.setStyleSheet("font-size:11px;color:#8c8c8c;")
        root.addWidget(self._status)

    # ── event subscription ────────────────────────────────────────

    def _register_events(self):
        ee = self._engine.event_engine
        for ev_type in _ALL_EVENTS:
            ee.register(ev_type, self._on_event)

    def _on_event(self, event):
        if self._paused:
            return
        ev_type = event.type
        data    = event.data if hasattr(event, "data") else {}
        level, color = _EV_LEVEL.get(ev_type, _DEFAULT_LEVEL)
        if isinstance(data, dict):
            msg = data.get("msg", str(data)[:120])
        else:
            msg = str(data)[:120]
        entry = LogEntry(
            ts         = datetime.now(),
            level      = level,
            color      = color,
            event_type = ev_type,
            message    = msg,
        )
        self._entries.append(entry)
        if len(self._entries) > MAX_LOG_ROWS:
            self._entries = self._entries[-MAX_LOG_ROWS:]
        self._append_row(entry)

    # ── table helpers ─────────────────────────────────────────────

    def _append_row(self, entry: LogEntry):
        if not self._visible(entry):
            return
        r = self._table.rowCount()
        self._table.insertRow(r)
        self._table.setItem(r, 0,
            QTableWidgetItem(entry.ts.strftime("%H:%M:%S.%f")[:12]))
        li = QTableWidgetItem(entry.level)
        li.setForeground(QBrush(QColor(entry.color)))
        self._table.setItem(r, 1, li)
        short_ev = entry.event_type.split("_")[-1] if entry.event_type else ""
        self._table.setItem(r, 2, QTableWidgetItem(short_ev))
        self._table.setItem(r, 3, QTableWidgetItem(entry.message))
        # keep at bottom
        self._table.scrollToBottom()
        # trim
        if self._table.rowCount() > MAX_LOG_ROWS:
            self._table.removeRow(0)
        self._update_status()

    def _visible(self, entry: LogEntry) -> bool:
        if self._filter_level != "ALL" and entry.level != self._filter_level:
            return False
        if self._filter_kw and self._filter_kw not in entry.message.lower():
            return False
        return True

    def _rebuild_table(self):
        self._table.setRowCount(0)
        for entry in self._entries:
            if self._visible(entry):
                r = self._table.rowCount()
                self._table.insertRow(r)
                self._table.setItem(r, 0,
                    QTableWidgetItem(entry.ts.strftime("%H:%M:%S.%f")[:12]))
                li = QTableWidgetItem(entry.level)
                li.setForeground(QBrush(QColor(entry.color)))
                self._table.setItem(r, 1, li)
                short_ev = entry.event_type.split("_")[-1]
                self._table.setItem(r, 2, QTableWidgetItem(short_ev))
                self._table.setItem(r, 3, QTableWidgetItem(entry.message))
        self._table.scrollToBottom()
        self._update_status()

    def _update_status(self):
        self._status.setText(
            f"{self._table.rowCount()} \u6761\u663e\u793a  "
            f"/ \u5171 {len(self._entries)} \u6761")

    # ── controls ──────────────────────────────────────────────────

    def _on_pause(self, checked: bool):
        self._paused = checked
        self._btn_pause.setText(
            "\u25b6 \u7ee7\u7eed" if checked else "\u23f8 \u6682\u505c")

    def _on_clear(self):
        self._entries.clear()
        self._table.setRowCount(0)
        self._update_status()

    def _on_level_changed(self, level: str):
        self._filter_level = level
        self._rebuild_table()

    def _on_kw_changed(self, kw: str):
        self._filter_kw = kw.lower().strip()
        self._rebuild_table()

    # ── public ────────────────────────────────────────────────────

    def add_log(self, message: str, level: str = "INFO",
                event_type: str = "MANUAL") -> None:
        """手动写入一条日志。"""
        color_map = {"INFO": "#1890ff", "WARN": "#faad14", "ERROR": "#ff4d4f"}
        entry = LogEntry(
            ts=datetime.now(), level=level,
            color=color_map.get(level, "#1890ff"),
            event_type=event_type, message=message,
        )
        self._entries.append(entry)
        self._append_row(entry)
