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
    EVENT_RO_EXP_STARTED, EVENT_RO_EXP_COMPLETED, EVENT_RO_EXP_FAILED,
    EVENT_RO_RUN_CREATED, EVENT_RO_RUN_COMPLETED, EVENT_RO_RUN_FAILED,
    EVENT_RO_PL_CREATED, EVENT_RO_PL_STARTED, EVENT_RO_PL_COMPLETED, EVENT_RO_PL_FAILED,
    EVENT_RO_RPT_CREATED, EVENT_RO_RPT_PUBLISHED,
    EVENT_RO_KB_CREATED, EVENT_RO_KB_UPDATED,
    EVENT_RO_DS_CREATED, EVENT_RO_DS_REGISTERED,
    EVENT_RO_ML_REGISTERED, EVENT_RO_ML_DEPLOYED,
    EVENT_RO_FT_REGISTERED,
    EVENT_RO_ST_REGISTERED,
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
    EVENT_RO_EXP_CREATED,  EVENT_RO_EXP_UPDATED,    EVENT_RO_EXP_DELETED,
    EVENT_RO_EXP_STARTED,  EVENT_RO_EXP_COMPLETED,  EVENT_RO_EXP_FAILED,
    EVENT_RO_RUN_CREATED,  EVENT_RO_RUN_COMPLETED,  EVENT_RO_RUN_FAILED,
    EVENT_RO_PL_CREATED,   EVENT_RO_PL_STARTED,
    EVENT_RO_PL_COMPLETED, EVENT_RO_PL_FAILED,
    EVENT_RO_RPT_CREATED,  EVENT_RO_RPT_PUBLISHED,
    EVENT_RO_KB_CREATED,   EVENT_RO_KB_UPDATED,
    EVENT_RO_DS_CREATED,   EVENT_RO_DS_REGISTERED,
    EVENT_RO_ML_REGISTERED, EVENT_RO_ML_DEPLOYED,
    EVENT_RO_FT_REGISTERED,
    EVENT_RO_ST_REGISTERED,
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


# =================================================================
# StatGrid  — 3×3 KPI grid
# =================================================================

class StatGrid(QWidget):
    def __init__(self, engine, parent=None):
        super().__init__(parent)
        self._engine = engine
        self._cards: List[KpiCard] = []
        self._init_ui()

    def _init_ui(self):
        root = QVBoxLayout(self); root.setContentsMargins(0,0,0,0)
        hdr = QHBoxLayout()
        lbl = QLabel("\U0001f4ca  \u5e73\u53f0\u6982\u89c8")
        lbl.setStyleSheet("font-size:14px;font-weight:bold;color:#1a1f36;")
        hdr.addWidget(lbl); hdr.addStretch()
        self._ts = QLabel("")
        self._ts.setStyleSheet("font-size:11px;color:#adb5bd;")
        hdr.addWidget(self._ts)
        root.addLayout(hdr)

        grid = QGridLayout(); grid.setSpacing(10)
        for i, d in enumerate(CARD_DEFS):
            card = KpiCard(d["icon"], d["label"], "0", d["color"])
            grid.addWidget(card, i // 3, i % 3)
            self._cards.append(card)
        root.addLayout(grid)
        self.refresh()

    def refresh(self):
        try:
            s = self._engine.get_platform_stats()
        except Exception:
            return
        for card, d in zip(self._cards, CARD_DEFS):
            sec  = s.get(d["sec"], {})
            val  = sec.get(d["key"], 0)
            card.update_value(str(val))
        self._ts.setText(
            "\u66f4\u65b0: " + datetime.now().strftime("%H:%M:%S"))


# =================================================================
# ActivityItem  — single timeline row
# =================================================================

class ActivityItem(QFrame):
    def __init__(self, ts: str, icon: str, text: str,
                 color: str = C_BLUE, parent=None):
        super().__init__(parent)
        self.setFrameShape(QFrame.NoFrame)
        self.setStyleSheet(
            "ActivityItem{background:transparent;border:none;}"
            "ActivityItem:hover{background:#f8f9fa;border-radius:6px;}")
        lay = QHBoxLayout(self)
        lay.setContentsMargins(4, 2, 4, 2)
        lay.setSpacing(8)

        dot = QLabel("●")
        dot.setStyleSheet(
            "color:" + color + ";font-size:10px;"
            "background:transparent;border:none;")
        dot.setFixedWidth(14)
        lay.addWidget(dot)

        icon_lbl = QLabel(icon)
        icon_lbl.setStyleSheet(
            "font-size:14px;background:transparent;border:none;")
        icon_lbl.setFixedWidth(22)
        lay.addWidget(icon_lbl)

        text_lbl = QLabel(text)
        text_lbl.setWordWrap(True)
        text_lbl.setStyleSheet(
            "font-size:12px;color:#1a1f36;"
            "background:transparent;border:none;")
        lay.addWidget(text_lbl, 1)

        ts_lbl = QLabel(ts)
        ts_lbl.setStyleSheet(
            "font-size:11px;color:#adb5bd;"
            "background:transparent;border:none;")
        ts_lbl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        ts_lbl.setFixedWidth(60)
        lay.addWidget(ts_lbl)


# =================================================================
# ActivityFeed  — scrollable event timeline
# =================================================================

class ActivityFeed(QWidget):
    MAX_ITEMS = 60

    def __init__(self, engine, parent=None):
        super().__init__(parent)
        self._engine = engine
        self._items: List[Dict] = []   # {ts, icon, text, color}
        self._init_ui()
        self._register_events()

    def _init_ui(self):
        root = QVBoxLayout(self); root.setContentsMargins(0,0,0,0)

        hdr = QHBoxLayout()
        lbl = QLabel("\U0001f4f0  \u6700\u8fd1\u6d3b\u52a8")
        lbl.setStyleSheet("font-size:14px;font-weight:bold;color:#1a1f36;")
        hdr.addWidget(lbl); hdr.addStretch()
        self._btn_clear = QPushButton("\u6e05\u7a7a")
        self._btn_clear.setFixedSize(52, 22)
        self._btn_clear.setStyleSheet("font-size:11px;")
        self._btn_clear.clicked.connect(self._clear)
        hdr.addWidget(self._btn_clear)
        root.addLayout(hdr)

        sep = QFrame(); sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet("color:#dee2e6;"); root.addWidget(sep)

        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setFrameShape(QFrame.NoFrame)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._content = QWidget()
        self._content.setStyleSheet("background:#fff;")
        self._feed_lay = QVBoxLayout(self._content)
        self._feed_lay.setContentsMargins(4, 4, 4, 4)
        self._feed_lay.setSpacing(2)
        self._feed_lay.addStretch()
        self._scroll.setWidget(self._content)
        root.addWidget(self._scroll, 1)

        self._empty_lbl = QLabel("\u6682\u65e0\u6d3b\u52a8\u8bb0\u5f55")
        self._empty_lbl.setStyleSheet(
            "color:#adb5bd;font-size:13px;"
            "background:transparent;border:none;")
        self._empty_lbl.setAlignment(Qt.AlignCenter)
        self._feed_lay.insertWidget(0, self._empty_lbl)

    _EV_MAP = {
        EVENT_RO_EXP_CREATED:     ("🧪", "新实验创建",    C_BLUE),
        EVENT_RO_EXP_UPDATED:     ("🧪", "实验已更新",    C_BLUE),
        EVENT_RO_EXP_DELETED:     ("🧪", "实验已删除",    C_GRAY),
        EVENT_RO_RUN_CREATED:     ("▶",  "运行已启动",    C_GREEN),
        EVENT_RO_RUN_COMPLETED:   ("✅", "运行已完成",    C_GREEN),
        EVENT_RO_RUN_FAILED:      ("❌", "运行失败",      C_RED),
        EVENT_RO_PL_CREATED:      ("🔄", "Pipeline 创建", C_GOLD),
        EVENT_RO_PL_STARTED:      ("🔄", "Pipeline 启动", C_ORANGE),
        EVENT_RO_PL_COMPLETED:    ("✅", "Pipeline 完成", C_GREEN),
        EVENT_RO_PL_FAILED:       ("❌", "Pipeline 失败", C_RED),
        EVENT_RO_RPT_CREATED:     ("📝", "报告创建",      C_BLUE),
        EVENT_RO_RPT_PUBLISHED:   ("📤", "报告已发布",    C_GREEN),
        EVENT_RO_KB_CREATED:      ("🧠", "知识条目新增",  C_TEAL),
        EVENT_RO_KB_UPDATED:      ("🧠", "知识条目更新",  C_TEAL),
        EVENT_RO_DS_CREATED:      ("🗄",  "数据集创建",    C_PURPLE),
        EVENT_RO_DS_REGISTERED:   ("🗄",  "数据集注册",    C_PURPLE),
        EVENT_RO_ML_REGISTERED:("🤖", "模型注册",      C_PURPLE),
        EVENT_RO_ML_DEPLOYED:  ("🚀", "模型部署",      C_GREEN),
        EVENT_RO_FT_REGISTERED: ("📐", "特征注册",      C_TEAL),
        EVENT_RO_ST_REGISTERED:("📈", "策略注册",      C_GREEN),
    }

    def _register_events(self):
        ee = self._engine.event_engine
        for ev_type, (icon, text, color) in self._EV_MAP.items():
            def _make_cb(i=icon, t=text, c=color):
                def _cb(_=None):
                    self._push(i, t, c)
                return _cb
            ee.register(ev_type, _make_cb())

    def _push(self, icon: str, text: str, color: str):
        ts = datetime.now().strftime("%H:%M:%S")
        self._items.insert(0, {"ts": ts, "icon": icon,
                                "text": text, "color": color})
        if len(self._items) > self.MAX_ITEMS:
            self._items = self._items[:self.MAX_ITEMS]
        self._rebuild()

    def _rebuild(self):
        # remove all except stretch
        while self._feed_lay.count() > 0:
            item = self._feed_lay.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if not self._items:
            lbl = QLabel("\u6682\u65e0\u6d3b\u52a8\u8bb0\u5f55")
            lbl.setStyleSheet(
                "color:#adb5bd;font-size:13px;"
                "background:transparent;border:none;")
            lbl.setAlignment(Qt.AlignCenter)
            self._feed_lay.addWidget(lbl)
        else:
            for d in self._items:
                row = ActivityItem(d["ts"], d["icon"],
                                   d["text"], d["color"])
                self._feed_lay.addWidget(row)
        self._feed_lay.addStretch()
        # auto-scroll to top
        self._scroll.verticalScrollBar().setValue(0)

    def _clear(self):
        self._items.clear(); self._rebuild()

    def push_manual(self, icon: str, text: str, color: str = C_BLUE):
        self._push(icon, text, color)


# =================================================================
# AlertRow  — single alert item
# =================================================================

class AlertRow(QFrame):
    def __init__(self, level: str, icon: str, title: str,
                 detail: str, color: str, parent=None):
        super().__init__(parent)
        self.setFrameShape(QFrame.StyledPanel)
        self.setStyleSheet(
            "AlertRow{background:#fff8f8;border-left:4px solid " + color + ";"
            "border-radius:4px;margin:2px 0;}"
        )
        lay = QHBoxLayout(self); lay.setContentsMargins(10, 6, 10, 6)
        lay.setSpacing(8)

        icon_lbl = QLabel(icon)
        icon_lbl.setStyleSheet(
            "font-size:18px;background:transparent;border:none;")
        icon_lbl.setFixedWidth(26)
        lay.addWidget(icon_lbl)

        text_lay = QVBoxLayout(); text_lay.setSpacing(2)
        title_lbl = QLabel(title)
        title_lbl.setStyleSheet(
            "font-size:13px;font-weight:bold;color:#1a1f36;"
            "background:transparent;border:none;")
        text_lay.addWidget(title_lbl)
        detail_lbl = QLabel(detail)
        detail_lbl.setStyleSheet(
            "font-size:11px;color:#6c757d;"
            "background:transparent;border:none;")
        text_lay.addWidget(detail_lbl)
        lay.addLayout(text_lay, 1)

        badge = QLabel(level)
        badge.setFixedHeight(20)
        badge.setStyleSheet(
            "padding:1px 8px;border-radius:9px;"
            "background:" + color + "22;color:" + color + ";"
            "font-size:11px;border:1px solid " + color + "44;"
            "background:transparent;"
        )
        lay.addWidget(badge)


# =================================================================
# AlertPanel  — collects alerts from engine stats
# =================================================================

class AlertPanel(QWidget):
    def __init__(self, engine, parent=None):
        super().__init__(parent)
        self._engine = engine
        self._init_ui()
        self.refresh()

    def _init_ui(self):
        root = QVBoxLayout(self); root.setContentsMargins(0, 0, 0, 0)
        hdr = QHBoxLayout()
        lbl = QLabel("\u26a0\ufe0f  \u544a\u8b66 & \u5f85\u529e")
        lbl.setStyleSheet("font-size:14px;font-weight:bold;color:#1a1f36;")
        hdr.addWidget(lbl); hdr.addStretch()
        self._count_lbl = QLabel("0")
        self._count_lbl.setStyleSheet(
            "padding:1px 8px;border-radius:9px;"
            "background:#dc354522;color:#dc3545;"
            "font-size:12px;border:1px solid #dc354544;")
        hdr.addWidget(self._count_lbl)
        root.addLayout(hdr)

        sep = QFrame(); sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet("color:#dee2e6;"); root.addWidget(sep)

        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setFrameShape(QFrame.NoFrame)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._inner = QWidget()
        self._inner.setStyleSheet("background:#f8f9fa;")
        self._inner_lay = QVBoxLayout(self._inner)
        self._inner_lay.setContentsMargins(4, 4, 4, 4)
        self._inner_lay.setSpacing(4)
        self._inner_lay.addStretch()
        self._scroll.setWidget(self._inner)
        root.addWidget(self._scroll, 1)

    def refresh(self):
        # remove everything except trailing stretch
        while self._inner_lay.count() > 0:
            item = self._inner_lay.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        alerts: List[Dict] = []
        try:
            s = self._engine.get_platform_stats()
        except Exception:
            self._inner_lay.addStretch(); return

        pl = s.get("pipeline", {})
        if pl.get("failed", 0):
            alerts.append({
                "level": "ERROR", "icon": "\u274c",
                "title": "Pipeline \u5931\u8d25",
                "detail": str(pl["failed"]) + " \u4e2a Pipeline \u5904\u4e8e\u5931\u8d25\u72b6\u6001",
                "color": C_RED,
            })
        if pl.get("running", 0):
            alerts.append({
                "level": "INFO", "icon": "\u26a1",
                "title": "Pipeline \u8fd0\u884c\u4e2d",
                "detail": str(pl["running"]) + " \u4e2a Pipeline \u6b63\u5728\u6267\u884c",
                "color": C_ORANGE,
            })

        kb = s.get("knowledge", {})
        if kb.get("unresolved_cases", 0):
            alerts.append({
                "level": "WARN", "icon": "\u26a0",
                "title": "\u672a\u89e3\u51b3\u5931\u8d25\u6848\u4f8b",
                "detail": str(kb["unresolved_cases"]) + " \u4e2a\u6848\u4f8b\u5f85\u5904\u7406",
                "color": C_GOLD,
            })

        rpt = s.get("report", {})
        drafts = rpt.get("reports", 0) - rpt.get("published", 0)
        if drafts > 0:
            alerts.append({
                "level": "INFO", "icon": "\u270f",
                "title": "\u8349\u7a3f\u62a5\u544a",
                "detail": str(drafts) + " \u4e2a\u62a5\u544a\u5c1a\u672a\u53d1\u5e03",
                "color": C_BLUE,
            })

        exp = s.get("experiment", {})
        if exp.get("running", 0):
            alerts.append({
                "level": "INFO", "icon": "\U0001f9ea",
                "title": "\u5b9e\u9a8c\u8fd0\u884c\u4e2d",
                "detail": str(exp["running"]) + " \u6b21\u8fd0\u884c\u6b63\u5728\u8fdb\u884c",
                "color": C_BLUE,
            })

        if not alerts:
            ok = QLabel("\u2705  \u6240\u6709\u7cfb\u7edf\u8fd0\u884c\u6b63\u5e38")
            ok.setStyleSheet(
                "color:#198754;font-size:13px;"
                "background:transparent;border:none;")
            ok.setAlignment(Qt.AlignCenter)
            self._inner_lay.addWidget(ok)
        else:
            for a in alerts:
                row = AlertRow(a["level"], a["icon"],
                               a["title"], a["detail"], a["color"])
                self._inner_lay.addWidget(row)

        self._inner_lay.addStretch()
        self._count_lbl.setText(str(len(alerts)))
        if alerts:
            self._count_lbl.setStyleSheet(
                "padding:1px 8px;border-radius:9px;"
                "background:#dc354522;color:#dc3545;"
                "font-size:12px;border:1px solid #dc354544;")
        else:
            self._count_lbl.setStyleSheet(
                "padding:1px 8px;border-radius:9px;"
                "background:#19875422;color:#198754;"
                "font-size:12px;border:1px solid #19875444;")


# =================================================================
# DashboardTab  — main widget
# =================================================================

class DashboardTab(QWidget):
    def __init__(self, engine, parent=None):
        super().__init__(parent)
        self._engine = engine
        self._init_ui()
        self._register_events()

    def _init_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(8)

        # ── top bar ───────────────────────────────────────────────
        top = QHBoxLayout()
        title = QLabel("\U0001f4ca  ResearchOps Dashboard")
        title.setStyleSheet(
            "font-size:16px;font-weight:bold;color:#1a1f36;")
        top.addWidget(title)
        top.addStretch()
        self._btn_refresh = QPushButton("\U0001f504  \u5237\u65b0")
        self._btn_refresh.setFixedHeight(28)
        self._btn_refresh.clicked.connect(self._do_refresh)
        top.addWidget(self._btn_refresh)
        self._auto_lbl = QLabel("\u81ea\u52a8\u5237\u65b0: 30s")
        self._auto_lbl.setStyleSheet("color:#6c757d;font-size:11px;")
        top.addWidget(self._auto_lbl)
        root.addLayout(top)

        # ── header stat strip ─────────────────────────────────────
        strip = QHBoxLayout(); strip.setSpacing(6)
        self._strip_cards: List[KpiCard] = []
        for icon, label, color in [
            ("🧪", "实验",     C_BLUE),
            ("▶",  "运行",     C_GREEN),
            ("🤖", "模型",     C_PURPLE),
            ("📈", "策略",     C_GREEN),
            ("🔄", "Pipeline", C_GOLD),
            ("📝", "报告",     C_BLUE),
        ]:
            c = KpiCard(icon, label, "0", color)
            c.setFixedHeight(90)
            strip.addWidget(c)
            self._strip_cards.append(c)
        root.addLayout(strip)

        # ── main body: left=grid+alerts, right=feed ───────────────
        sp = QSplitter(Qt.Horizontal)
        sp.setChildrenCollapsible(False)

        left = QWidget()
        left_l = QVBoxLayout(left); left_l.setContentsMargins(0,0,0,0)
        left_l.setSpacing(8)

        self._grid = StatGrid(self._engine)
        left_l.addWidget(self._grid)

        self._alerts = AlertPanel(self._engine)
        self._alerts.setMinimumHeight(160)
        left_l.addWidget(self._alerts, 1)

        sp.addWidget(left)

        right = QWidget()
        right_l = QVBoxLayout(right); right_l.setContentsMargins(0,0,0,0)
        self._feed = ActivityFeed(self._engine)
        right_l.addWidget(self._feed, 1)
        sp.addWidget(right)

        sp.setSizes([640, 320])
        sp.setStretchFactor(0, 2)
        sp.setStretchFactor(1, 1)
        root.addWidget(sp, 1)

        # ── status bar ────────────────────────────────────────────
        self._status = QLabel("\u5c31\u7eea")
        self._status.setStyleSheet("color:#6c757d;font-size:11px;")
        root.addWidget(self._status)

        # ── auto-refresh timer ────────────────────────────────────
        self._timer = QTimer(self)
        self._timer.setInterval(30_000)
        self._timer.timeout.connect(self._do_refresh)
        self._timer.start()

        self._do_refresh()

    # ── event wiring ──────────────────────────────────────────────

    def _register_events(self):
        ee = self._engine.event_engine
        for ev in EVENT_ALL:
            ee.register(ev, self._on_any_event)

    def _on_any_event(self, _=None):
        self._do_refresh()

    # ── refresh ───────────────────────────────────────────────────

    def _do_refresh(self):
        try:
            s = self._engine.get_platform_stats()
        except Exception:
            self._set_status("\u83b7\u53d6\u7edf\u8ba1\u5931\u8d25")
            return

        # strip cards
        strip_map = [
            ("experiment", "experiments"),
            ("experiment", "runs"),
            ("registry",   "models"),
            ("registry",   "strategies"),
            ("pipeline",   "pipelines"),
            ("report",     "reports"),
        ]
        for card, (sec, key) in zip(self._strip_cards, strip_map):
            card.update_value(str(s.get(sec, {}).get(key, 0)))

        # grid + alerts
        self._grid.refresh()
        self._alerts.refresh()

        self._set_status(
            "\u4e0a\u6b21\u5237\u65b0: " + datetime.now().strftime("%H:%M:%S"))

    def _set_status(self, msg: str):
        self._status.setText(msg)
