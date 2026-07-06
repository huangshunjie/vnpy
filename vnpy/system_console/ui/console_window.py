"""
system_console/ui/console_window.py

SystemConsoleWindow — 主控台窗口。
布局: KPI条 + 18模块卡片(按Layer分组) + 事件流 + 日志
"""
from __future__ import annotations
from datetime import datetime
from collections import defaultdict
from vnpy.trader.ui import QtCore, QtWidgets, QtGui
from vnpy.trader.engine import MainEngine, EventEngine
from ..constant import APP_NAME, MODULE_REGISTRY, ModuleState, ConsoleStatus
from ..event import (
    EVENT_MODULE_STATE_CHANGED, EVENT_SYSTEM_STATE_UPDATED,
    EVENT_CONSOLE_LOG, EVENT_DASHBOARD_TICK,
    EVENT_MODULE_ERROR, EVENT_ALL_STARTED, EVENT_ALL_STOPPED,
)
from .module_card import ModuleCard

_BG = "#1e1e2e"; _DARK = "#181825"; _BORDER = "#45475a"; _FG = "#cdd6f4"
_MUT = "#6c7086"; _GRN = "#a6e3a1"; _YLW = "#f9e2af"; _RED = "#f38ba8"
_MAV = "#cba6f7"; _HEAD = "#313244"; _CYN = "#89dceb"; _ORG = "#fab387"
_TEA = "#94e2d5"; _BLUE = "#89b4fa"

_LAYER_COLORS = {
    0: "#89dceb", 1: "#cba6f7", 2: "#f38ba8", 3: "#fab387",
    4: "#a6e3a1", 5: "#f9e2af", 6: "#89b4fa", 7: "#6c7086",
}
_LAYER_NAMES = {
    0: "Data",    1: "Signal",    2: "Portfolio / Risk", 3: "Strategy",
    4: "Execution",5: "Learning", 6: "Global",           7: "Infrastructure",
}
_TBL = (
    "QTableWidget{background:#181825;color:#cdd6f4;border:none;"
    "gridline-color:#45475a;font-size:9px;}"
    "QTableWidget::item{padding:2px 4px;}"
    "QTableWidget::item:alternate{background:#1e1e2e;}"
    "QHeaderView::section{background:#313244;color:#6c7086;border:none;"
    "border-bottom:1px solid #45475a;padding:2px 4px;font-size:8px;}"
)

def _lbl(t, s=""):
    w = QtWidgets.QLabel(t); w.setStyleSheet(s); return w

def _btn(t, color, slot, h=32, fs=11):
    b = QtWidgets.QPushButton(t); b.setFixedHeight(h)
    b.setStyleSheet(
        f"QPushButton{{background:{color};color:#1e1e2e;font-weight:bold;"
        f"border:none;border-radius:4px;padding:0 12px;font-size:{fs}px;}}"
        f"QPushButton:hover{{opacity:0.85;}}"
        f"QPushButton:disabled{{background:#45475a;color:#6c7086;}}")
    b.clicked.connect(slot); return b


class SystemConsoleWindow(QtWidgets.QMainWindow):
    """系统主控台主窗口。"""

    widget_name = APP_NAME

    def __init__(self, main_engine: MainEngine,
                 event_engine: EventEngine) -> None:
        super().__init__()
        self._main_engine  = main_engine
        self._event_engine = event_engine
        self._engine       = main_engine.get_engine(APP_NAME)
        self._cards: dict[str, ModuleCard] = {}
        self._init_ui()
        self._init_menu()
        self._register_events()
        self._timer = QtCore.QTimer(self)
        self._timer.timeout.connect(self._on_tick)
        self._timer.start(3000)

    # ── UI construction ────────────────────────────────────────────────
    def _init_ui(self) -> None:
        self.setWindowTitle("System Console  全系统主控台  18 Modules")
        self.resize(1600, 980)
        self.setStyleSheet(f"background:{_BG};color:{_FG};")
        central = QtWidgets.QWidget()
        self.setCentralWidget(central)
        vb = QtWidgets.QVBoxLayout(central)
        vb.setContentsMargins(8, 8, 8, 8); vb.setSpacing(8)
        vb.addWidget(self._build_kpi_bar())
        vb.addWidget(self._build_cards_area(), stretch=1)
        vb.addWidget(self._build_bottom_panel())

    def _build_kpi_bar(self) -> QtWidgets.QWidget:
        w = QtWidgets.QWidget(); w.setFixedHeight(80)
        w.setStyleSheet(
            f"background:{_DARK};border-radius:6px;border:1px solid {_BORDER};")
        h = QtWidgets.QHBoxLayout(w)
        h.setContentsMargins(20, 8, 20, 8); h.setSpacing(18)
        self._kpi: dict[str, QtWidgets.QLabel] = {}
        for key, txt, color in [
            ("health",  "Health",       _GRN),
            ("status",  "Status",       _CYN),
            ("running", "Running",      _BLUE),
            ("stopped", "Stopped",      _MUT),
            ("errors",  "Errors",       _RED),
            ("tput",    "Events/min",   _TEA),
            ("latency", "Avg Lat ms",   _YLW),
            ("events",  "Total Events", _FG),
            ("terror",  "Total Errors", _ORG),
        ]:
            cell = QtWidgets.QWidget()
            cell.setStyleSheet("background:transparent;border:none;")
            cv = QtWidgets.QVBoxLayout(cell)
            cv.setContentsMargins(0,0,0,0); cv.setSpacing(2)
            lk = _lbl(txt, f"color:{_MUT};font-size:9px;border:none;background:transparent;")
            lk.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
            lv = _lbl("--", f"color:{color};font-size:16px;font-weight:bold;"
                       f"border:none;background:transparent;")
            lv.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
            cv.addWidget(lk); cv.addWidget(lv)
            self._kpi[key] = lv; h.addWidget(cell)
        h.addStretch()
        btn_col = QtWidgets.QVBoxLayout(); btn_col.setSpacing(6)
        btn_col.addWidget(_btn("▶  Start All", _GRN, self._on_start_all))
        btn_col.addWidget(_btn("■  Stop All",  _RED, self._on_stop_all))
        h.addLayout(btn_col)
        self._ts_lbl = _lbl("--", f"color:{_MUT};font-size:8px;"
                             f"border:none;background:transparent;")
        self._ts_lbl.setAlignment(
            QtCore.Qt.AlignmentFlag.AlignRight |
            QtCore.Qt.AlignmentFlag.AlignBottom)
        h.addWidget(self._ts_lbl)
        return w

    def _build_cards_area(self) -> QtWidgets.QWidget:
        scroll = QtWidgets.QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet(
            f"QScrollArea{{background:transparent;border:none;}}"
            f"QScrollBar:vertical{{background:{_DARK};width:8px;border:none;}}"
            f"QScrollBar::handle:vertical{{background:{_BORDER};border-radius:4px;}}")
        inner = QtWidgets.QWidget()
        inner.setStyleSheet("background:transparent;")
        vb = QtWidgets.QVBoxLayout(inner)
        vb.setContentsMargins(4, 4, 4, 4); vb.setSpacing(10)

        layers: dict[int, list[dict]] = defaultdict(list)
        for meta in MODULE_REGISTRY:
            layers[meta["layer"]].append(meta)

        for lid in sorted(layers.keys()):
            mods  = layers[lid]
            lc    = _LAYER_COLORS.get(lid, _MUT)
            lname = _LAYER_NAMES.get(lid, f"Layer {lid}")
            # layer header bar
            sep = QtWidgets.QWidget(); sep.setFixedHeight(26)
            sep.setStyleSheet(
                f"background:{_HEAD};border-radius:3px;border:none;")
            sh = QtWidgets.QHBoxLayout(sep)
            sh.setContentsMargins(12, 0, 8, 0)
            sh.addWidget(_lbl(
                f"Layer {lid}  —  {lname}  ({len(mods)} modules)",
                f"color:{lc};font-size:10px;font-weight:bold;border:none;"))
            sh.addStretch()
            sh.addWidget(_btn("▶ Start layer", lc,
                              lambda c, l=lid: self._on_start_layer(l),
                              h=20, fs=9))
            sh.addWidget(_btn("■ Stop layer",  _RED,
                              lambda c, l=lid: self._on_stop_layer(l),
                              h=20, fs=9))
            vb.addWidget(sep)
            # cards row
            row_w = QtWidgets.QWidget()
            row_w.setStyleSheet("background:transparent;border:none;")
            rh = QtWidgets.QHBoxLayout(row_w)
            rh.setContentsMargins(0, 0, 0, 0); rh.setSpacing(8)
            for meta in mods:
                card = ModuleCard(key=meta["key"], label=meta["label"],
                                  display=meta["display"], layer=meta["layer"])
                card.start_requested.connect(self._on_card_start)
                card.stop_requested.connect(self._on_card_stop)
                self._cards[meta["key"]] = card
                rh.addWidget(card)
            rh.addStretch()
            vb.addWidget(row_w)
        vb.addStretch()
        scroll.setWidget(inner)
        return scroll

    def _build_bottom_panel(self) -> QtWidgets.QWidget:
        w = QtWidgets.QWidget(); w.setFixedHeight(200)
        w.setStyleSheet("background:transparent;")
        h = QtWidgets.QHBoxLayout(w)
        h.setContentsMargins(0,0,0,0); h.setSpacing(8)
        h.addWidget(self._build_event_stream(), stretch=1)
        h.addWidget(self._build_log_panel(),    stretch=1)
        return w

    def _build_event_stream(self) -> QtWidgets.QWidget:
        w = QtWidgets.QWidget()
        w.setStyleSheet(
            f"background:{_DARK};border-radius:5px;border:1px solid {_BORDER};")
        vb = QtWidgets.QVBoxLayout(w)
        vb.setContentsMargins(10,8,10,8); vb.setSpacing(4)
        hdr = QtWidgets.QHBoxLayout()
        hdr.addWidget(_lbl("Module State Changes",
                           f"color:{_CYN};font-size:10px;font-weight:bold;border:none;"))
        hdr.addStretch()
        hdr.addWidget(_btn("Clear", _MUT, self._on_clear_events, h=22, fs=9))
        vb.addLayout(hdr)
        self._event_tbl = QtWidgets.QTableWidget(0, 4)
        self._event_tbl.setHorizontalHeaderLabels(["Time","Module","State","Info"])
        self._event_tbl.verticalHeader().setVisible(False)
        self._event_tbl.setEditTriggers(
            QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
        self._event_tbl.setAlternatingRowColors(True)
        self._event_tbl.horizontalHeader().setSectionResizeMode(
            QtWidgets.QHeaderView.ResizeMode.ResizeToContents)
        self._event_tbl.horizontalHeader().setStretchLastSection(True)
        self._event_tbl.setStyleSheet(_TBL)
        vb.addWidget(self._event_tbl)
        return w

    def _build_log_panel(self) -> QtWidgets.QWidget:
        w = QtWidgets.QWidget()
        w.setStyleSheet(
            f"background:{_DARK};border-radius:5px;border:1px solid {_BORDER};")
        vb = QtWidgets.QVBoxLayout(w)
        vb.setContentsMargins(10,8,10,8); vb.setSpacing(4)
        hdr = QtWidgets.QHBoxLayout()
        hdr.addWidget(_lbl("Console Log",
                           f"color:{_YLW};font-size:10px;font-weight:bold;border:none;"))
        hdr.addStretch()
        hdr.addWidget(_btn("Clear", _MUT, self._on_clear_log, h=22, fs=9))
        vb.addLayout(hdr)
        self._log_txt = QtWidgets.QPlainTextEdit()
        self._log_txt.setReadOnly(True)
        self._log_txt.setMaximumBlockCount(800)
        self._log_txt.setFont(QtGui.QFont("Consolas", 9))
        self._log_txt.setStyleSheet(
            f"QPlainTextEdit{{background:{_BG};color:{_MUT};"
            f"border:1px solid {_BORDER};border-radius:3px;}}")
        vb.addWidget(self._log_txt)
        return w

    # ── menu ──────────────────────────────────────────────────────────
    def _init_menu(self) -> None:
        mb = self.menuBar()
        mb.setStyleSheet(
            f"QMenuBar{{background:{_DARK};color:{_FG};border:none;}}"
            f"QMenuBar::item:selected{{background:{_HEAD};}}"
            f"QMenu{{background:{_DARK};color:{_FG};border:1px solid {_BORDER};}}"
            f"QMenu::item:selected{{background:{_HEAD};}}")
        m = mb.addMenu("System")
        m.addAction("Start All").triggered.connect(self._on_start_all)
        m.addAction("Stop All").triggered.connect(self._on_stop_all)
        m.addSeparator()
        m.addAction("Force Refresh").triggered.connect(self._on_tick)
        m.addSeparator()
        m.addAction("Close").triggered.connect(self.close)
        mv = mb.addMenu("View")
        mv.addAction("Clear Events").triggered.connect(self._on_clear_events)
        mv.addAction("Clear Log").triggered.connect(self._on_clear_log)
        ml = mb.addMenu("By Layer")
        for lid, name in _LAYER_NAMES.items():
            sub = ml.addMenu(f"Layer {lid}  {name}")
            sub.addAction("Start").triggered.connect(
                lambda c, l=lid: self._on_start_layer(l))
            sub.addAction("Stop").triggered.connect(
                lambda c, l=lid: self._on_stop_layer(l))

    # ── VeighNa event registration ─────────────────────────────────────
    def _register_events(self) -> None:
        self._evs = [
            EVENT_SYSTEM_STATE_UPDATED, EVENT_DASHBOARD_TICK,
            EVENT_MODULE_STATE_CHANGED, EVENT_MODULE_ERROR,
            EVENT_CONSOLE_LOG, EVENT_ALL_STARTED, EVENT_ALL_STOPPED,
        ]
        for ev in self._evs:
            self._event_engine.register(ev, self._dispatch_event)

    def _dispatch_event(self, event) -> None:
        et = event.type; d = event.data or {}
        if et in (EVENT_SYSTEM_STATE_UPDATED, EVENT_DASHBOARD_TICK):
            self._update_kpi(d)
        elif et == EVENT_MODULE_STATE_CHANGED:
            self._append_event_row(
                d.get("key",""), d.get("new",""), d.get("old",""), "")
        elif et == EVENT_MODULE_ERROR:
            self._append_event_row(
                d.get("key",""), "error", "", d.get("error",""))
        elif et == EVENT_CONSOLE_LOG:
            line = d.get("line","")
            if line: self._append_log(line)
        elif et in (EVENT_ALL_STARTED, EVENT_ALL_STOPPED):
            self._append_log(
                f"[{str(datetime.now())[11:19]}]  {et}  "
                f"count={d.get('count','')}")

    # ── slots ──────────────────────────────────────────────────────────
    def _on_start_all(self) -> None:
        if self._engine is None: return
        self._engine.init(); self._engine.start()
        self._engine.start_all()

    def _on_stop_all(self) -> None:
        if self._engine: self._engine.stop_all()

    def _on_start_layer(self, lid: int) -> None:
        if self._engine is None: return
        for meta in MODULE_REGISTRY:
            if meta["layer"] == lid:
                self._engine.start_module(meta["key"])

    def _on_stop_layer(self, lid: int) -> None:
        if self._engine is None: return
        for meta in MODULE_REGISTRY:
            if meta["layer"] == lid:
                self._engine.stop_module(meta["key"])

    def _on_card_start(self, key: str) -> None:
        if self._engine: self._engine.start_module(key)

    def _on_card_stop(self, key: str) -> None:
        if self._engine: self._engine.stop_module(key)

    def _on_tick(self) -> None:
        if self._engine is None: return
        try:
            state = self._engine.tick()
            self._update_kpi(state.to_dict())
            self._refresh_cards()
        except Exception:
            pass

    def _on_clear_events(self) -> None:
        self._event_tbl.setRowCount(0)

    def _on_clear_log(self) -> None:
        self._log_txt.clear()

    # ── refresh helpers ────────────────────────────────────────────────
    def _update_kpi(self, d: dict) -> None:
        hs   = float(d.get("health_score", 100.0))
        hs_c = _GRN if hs >= 80 else (_YLW if hs >= 50 else _RED)
        self._kpi["health"].setText(f"{hs:.1f}")
        self._kpi["health"].setStyleSheet(
            f"color:{hs_c};font-size:16px;font-weight:bold;"
            f"border:none;background:transparent;")
        status = d.get("status","idle")
        sc = {"running":_GRN,"partial":_YLW,"error":_RED,
              "idle":_MUT,"stopping":_YLW}.get(status, _MUT)
        self._kpi["status"].setText(status)
        self._kpi["status"].setStyleSheet(
            f"color:{sc};font-size:16px;font-weight:bold;"
            f"border:none;background:transparent;")
        self._kpi["running"].setText(str(d.get("running_count","--")))
        self._kpi["stopped"].setText(str(d.get("stopped_count","--")))
        err_n = int(d.get("error_count", 0))
        self._kpi["errors"].setText(str(err_n))
        if err_n > 0:
            self._kpi["errors"].setStyleSheet(
                f"color:{_RED};font-size:16px;font-weight:bold;"
                f"border:none;background:transparent;")
        self._kpi["tput"].setText(
            f'{float(d.get("system_tput",0)):.1f}')
        self._kpi["latency"].setText(
            f'{float(d.get("avg_latency",0)):.0f}')
        self._kpi["events"].setText(str(d.get("total_events","--")))
        self._kpi["terror"].setText(str(d.get("total_errors","--")))
        self._ts_lbl.setText(f'Updated: {d.get("updated_at","")}')

    def _refresh_cards(self) -> None:
        if self._engine is None: return
        for key, entry in self._engine.get_all_modules().items():
            card = self._cards.get(key)
            if card: card.refresh(entry.to_dict())

    def _append_event_row(self, key: str, new: str,
                           old: str, info: str) -> None:
        tbl = self._event_tbl
        row = tbl.rowCount(); tbl.insertRow(row)
        ts = str(datetime.now())[11:19]
        sc = {"running":_GRN,"error":_RED,"starting":_YLW,
              "stopping":_YLW,"stopped":_MUT}.get(new, _FG)
        for col, txt in enumerate([ts, key, new, info]):
            it = QtWidgets.QTableWidgetItem(txt)
            it.setTextAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
            if col == 2: it.setForeground(QtGui.QColor(sc))
            tbl.setItem(row, col, it)
        if tbl.rowCount() > 200: tbl.removeRow(0)
        tbl.scrollToBottom()

    def _append_log(self, line: str) -> None:
        self._log_txt.appendPlainText(line)
        sb = self._log_txt.verticalScrollBar()
        sb.setValue(sb.maximum())

    def closeEvent(self, event) -> None:
        self._timer.stop()
        for ev in getattr(self, "_evs", []):
            try: self._event_engine.unregister(ev, self._dispatch_event)
            except Exception: pass
        super().closeEvent(event)
