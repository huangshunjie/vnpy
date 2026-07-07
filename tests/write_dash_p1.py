"""write_dash_p1.py — dashboard_tab.py Part1: imports + KPI card"""
import pathlib, ast

P = pathlib.Path(
    r"c:\Users\11229\Documents\GitHub\vnpy\vnpy\research_ops\ui\dashboard_tab.py"
)

PART1 = '''\
"""
research_ops/ui/dashboard_tab.py  Phase 8 - Dashboard
"""
from __future__ import annotations
from typing import Dict, Any, List, Optional
from datetime import datetime

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QPushButton, QLabel, QFrame, QScrollArea,
    QGroupBox, QSizePolicy, QTabWidget, QTableWidget,
    QTableWidgetItem, QHeaderView, QAbstractItemView,
    QSplitter,
)
from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QColor, QFont, QBrush, QPainter, QPen, QLinearGradient

from ..main_engine import ResearchOpsEngine
from ..event import (
    EVENT_RO_EXP_CREATED, EVENT_RO_EXP_UPDATED, EVENT_RO_EXP_DELETED,
    EVENT_RO_RUN_STARTED, EVENT_RO_RUN_COMPLETED, EVENT_RO_RUN_FAILED,
    EVENT_RO_PL_CREATED, EVENT_RO_PL_STARTED, EVENT_RO_PL_COMPLETED, EVENT_RO_PL_FAILED,
    EVENT_RO_RPT_CREATED, EVENT_RO_RPT_PUBLISHED,
    EVENT_RO_KB_CREATED, EVENT_RO_KB_UPDATED,
    EVENT_RO_DS_CREATED, EVENT_RO_DS_REGISTERED,
    EVENT_RO_MODEL_REGISTERED, EVENT_RO_MODEL_DEPLOYED,
    EVENT_RO_FEAT_REGISTERED,
    EVENT_RO_STRAT_REGISTERED,
)

# ── colour tokens ─────────────────────────────────────────────────
C_BLUE   = "#4a6cf7"
C_GREEN  = "#198754"
C_ORANGE = "#fd7e14"
C_RED    = "#dc3545"
C_PURPLE = "#9c27b0"
C_TEAL   = "#17a2b8"
C_GOLD   = "#ffc107"
C_GRAY   = "#6c757d"
C_INDIGO = "#6610f2"

CARD_DEFS: List[Dict] = [
    # (section, label, stat_key, color)
    {"sec":"experiment","label":"实验","key":"experiments","color":C_BLUE,   "icon":"🧪"},
    {"sec":"experiment","label":"运行次数","key":"runs",         "color":C_INDIGO,"icon":"▶"},
    {"sec":"experiment","label":"进行中",  "key":"running",     "color":C_ORANGE,"icon":"⚡"},
    {"sec":"registry",  "label":"模型",    "key":"models",      "color":C_PURPLE,"icon":"🤖"},
    {"sec":"registry",  "label":"特征",    "key":"features",    "color":C_TEAL,  "icon":"📐"},
    {"sec":"registry",  "label":"策略",    "key":"strategies",  "color":C_GREEN, "icon":"📈"},
    {"sec":"pipeline",  "label":"Pipeline","key":"pipelines",   "color":C_GOLD,  "icon":"🔄"},
    {"sec":"report",    "label":"报告",    "key":"reports",     "color":C_BLUE,  "icon":"📝"},
    {"sec":"knowledge", "label":"笔记",    "key":"notes",       "color":C_TEAL,  "icon":"🧠"},
]

EVENT_ALL = [
    EVENT_RO_EXP_CREATED, EVENT_RO_EXP_UPDATED, EVENT_RO_EXP_DELETED,
    EVENT_RO_RUN_STARTED,  EVENT_RO_RUN_COMPLETED, EVENT_RO_RUN_FAILED,
    EVENT_RO_PL_CREATED,   EVENT_RO_PL_STARTED,
    EVENT_RO_PL_COMPLETED, EVENT_RO_PL_FAILED,
    EVENT_RO_RPT_CREATED,  EVENT_RO_RPT_PUBLISHED,
    EVENT_RO_KB_CREATED,   EVENT_RO_KB_UPDATED,
    EVENT_RO_DS_CREATED,   EVENT_RO_DS_REGISTERED,
    EVENT_RO_MODEL_REGISTERED, EVENT_RO_MODEL_DEPLOYED,
    EVENT_RO_FEAT_REGISTERED,
    EVENT_RO_STRAT_REGISTERED,
]


# =================================================================
# KpiCard  — single metric tile
# =================================================================

class KpiCard(QFrame):
    def __init__(self, icon: str, label: str, value: str,
                 color: str = C_BLUE, parent=None):
        super().__init__(parent)
        self._color = color
        self.setFrameShape(QFrame.StyledPanel)
        self.setMinimumSize(130, 90)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setStyleSheet(
            "KpiCard{background:#fff;border:1px solid #e9ecef;"
            "border-radius:10px;}"
            "KpiCard:hover{border:1px solid " + color + ";}")
        lay = QVBoxLayout(self); lay.setContentsMargins(12, 10, 12, 10)
        lay.setSpacing(4)

        top = QHBoxLayout()
        self._icon_lbl = QLabel(icon)
        self._icon_lbl.setStyleSheet(
            "font-size:20px;background:transparent;border:none;")
        top.addWidget(self._icon_lbl)
        top.addStretch()
        self._trend = QLabel("")
        self._trend.setStyleSheet(
            "font-size:11px;color:" + color + ";background:transparent;border:none;")
        top.addWidget(self._trend)
        lay.addLayout(top)

        self._val_lbl = QLabel(value)
        self._val_lbl.setStyleSheet(
            "font-size:26px;font-weight:bold;color:" + color + ";"
            "background:transparent;border:none;")
        lay.addWidget(self._val_lbl)

        self._label_lbl = QLabel(label)
        self._label_lbl.setStyleSheet(
            "font-size:12px;color:#6c757d;"
            "background:transparent;border:none;")
        lay.addWidget(self._label_lbl)

        # coloured bottom bar
        self._bar = QFrame()
        self._bar.setFixedHeight(3)
        self._bar.setStyleSheet(
            "background:" + color + ";border-radius:2px;")
        lay.addWidget(self._bar)

    def update_value(self, value: str, trend: str = ""):
        self._val_lbl.setText(value)
        self._trend.setText(trend)
'''

ast.parse(PART1)
P.write_text(PART1, encoding="utf-8")
print("PART1 OK, lines:", len(PART1.splitlines()), "size:", P.stat().st_size)
