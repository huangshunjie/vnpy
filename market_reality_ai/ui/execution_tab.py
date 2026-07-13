"""
market_reality_ai/ui/execution_tab.py

Phase 2: Execution Reality Monitor.
"""
from __future__ import annotations
from datetime import datetime

from vnpy.trader.ui import QtCore, QtWidgets, QtGui
from vnpy.trader.engine import MainEngine, EventEngine

from ..constant import APP_NAME
from ..event import EVENT_EXECUTION_SIMULATED, EVENT_SLIPPAGE_RECORDED

_BG = "#1e1e2e"; _DARK = "#181825"; _BORDER = "#45475a"
_FG = "#cdd6f4"; _MUT  = "#6c7086"; _HEAD   = "#313244"
_GRN = "#a6e3a1"; _YLW = "#f9e2af"; _RED = "#f38ba8"
_ORG = "#fab387"; _MAV = "#cba6f7"; _CYN = "#89dceb"; _BLUE = "#89b4fa"


def _lbl(t, s=""):
    w = QtWidgets.QLabel(t); w.setStyleSheet(s); return w


def _btn(t, color, slot, h=30, fs=10):
    b = QtWidgets.QPushButton(t); b.setFixedHeight(h)
    b.setStyleSheet(
        f"QPushButton{{background:{color};color:#1e1e2e;font-weight:bold;"
        f"border:none;border-radius:4px;padding:0 12px;font-size:{fs}px;}}"
        f"QPushButton:hover{{opacity:0.85;}}"
        f"QPushButton:disabled{{background:#45475a;color:#6c7086;}}")
    b.clicked.connect(slot); return b


class ExecutionTab(QtWidgets.QWidget):
    """Execution Reality Monitor — Phase 2."""

    def __init__(self, main_engine=None, event_engine=None, parent=None):
        super().__init__(parent)
        self._main_engine  = main_engine
        self._event_engine = event_engine
        self._engine       = (main_engine.get_engine(APP_NAME)
                               if main_engine else None)
        self._records: list[dict] = []
        self._init_ui()
        if event_engine:
            event_engine.register(
                EVENT_EXECUTION_SIMULATED, self._on_execution_simulated)
            event_engine.register(
                EVENT_SLIPPAGE_RECORDED, self._on_slippage_recorded)

    def _init_ui(self):
        self.setStyleSheet(f"background:{_DARK};")
        vb = QtWidgets.QVBoxLayout(self)
        vb.setContentsMargins(10, 10, 10, 10); vb.setSpacing(8)
        vb.addWidget(self._build_kpi_bar())
        body = QtWidgets.QHBoxLayout(); body.setSpacing(8)
        body.addWidget(self._build_control_panel(), stretch=0)
        body.addWidget(self._build_record_table(),  stretch=1)
        vb.addLayout(body)
        vb.addWidget(self._build_stats_bar())

    def _build_kpi_bar(self):
        w = QtWidgets.QWidget(); w.setFixedHeight(68)
        w.setStyleSheet(
            f"background:{_HEAD};border-radius:5px;border:1px solid {_BORDER};")
        h = QtWidgets.QHBoxLayout(w)
        h.setContentsMargins(12, 6, 12, 6); h.setSpacing(8)
        h.addWidget(_lbl("Execution Reality",
                         f"color:{_ORG};font-size:11px;font-weight:bold;"
                         f"border:none;background:transparent;"))
        sep = QtWidgets.QFrame()
        sep.setFrameShape(QtWidgets.QFrame.Shape.VLine)
        sep.setStyleSheet(f"background:{_BORDER};border:none;")
        h.addWidget(sep)
        self._kpi: dict[str, QtWidgets.QLabel] = {}
        for key, label, color in [
            ("avg_slip",    "Avg Slippage",  _YLW),
            ("fill_rate",   "Fill Rate",     _GRN),
            ("rejection",   "Rejection",     _RED),
            ("latency",     "Avg Latency",   _CYN),
            ("reality_gap", "Reality Gap",   _MAV),
        ]:
            cell = QtWidgets.QWidget()
            cell.setStyleSheet(
                f"background:{_DARK};border-radius:4px;border:none;")
            cv = QtWidgets.QVBoxLayout(cell)
            cv.setContentsMargins(10, 6, 10, 6); cv.setSpacing(2)
            lk = _lbl(label,
                       f"color:{_MUT};font-size:9px;"
                       f"border:none;background:transparent;")
            lk.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
            lv = _lbl("--",
                       f"color:{color};font-size:14px;font-weight:bold;"
                       f"border:none;background:transparent;")
            lv.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
            cv.addWidget(lk); cv.addWidget(lv)
            self._kpi[key] = lv; h.addWidget(cell, stretch=1)
        h.addStretch()
        self._total_lbl = _lbl("Simulations: 0",
                                f"color:{_MUT};font-size:9px;"
                                f"border:none;background:transparent;")
        h.addWidget(self._total_lbl)
        return w

    def _build_control_panel(self):
        panel = QtWidgets.QWidget(); panel.setFixedWidth(235)
        panel.setStyleSheet(
            f"background:{_HEAD};border-radius:5px;border:1px solid {_BORDER};")
        vb = QtWidgets.QVBoxLayout(panel)
        vb.setContentsMargins(14, 14, 14, 14); vb.setSpacing(7)
        vb.addWidget(_lbl("Order Parameters",
                          f"color:{_CYN};font-size:10px;font-weight:bold;"
                          f"border:none;background:transparent;"))
        self._inputs: dict[str, QtWidgets.QLineEdit] = {}
        le_style = (
            f"QLineEdit{{background:{_BG};color:{_FG};"
            f"border:1px solid {_BORDER};border-radius:3px;"
            f"padding:0 6px;font-size:10px;}}"
            f"QLineEdit:focus{{border:1px solid {_CYN};}}")
        lbl_style = (f"color:{_MUT};font-size:9px;"
                     f"border:none;background:transparent;")
        for key, label, default in [
            ("symbol",       "Symbol",       "BTCUSDT"),
            ("market_price", "Market Price", "50000.0"),
            ("order_size",   "Order Size",   "100.0"),
            ("adv",          "ADV",          "50000.0"),
            ("volatility",   "Volatility",   "0.02"),
            ("spread_bps",   "Spread (bps)", "5.0"),
        ]:
            vb.addWidget(_lbl(label, lbl_style))
            le = QtWidgets.QLineEdit(default)
            le.setFixedHeight(26); le.setStyleSheet(le_style)
            vb.addWidget(le); self._inputs[key] = le
        vb.addWidget(_lbl("Direction", lbl_style))
        self._dir_combo = QtWidgets.QComboBox()
        self._dir_combo.addItems(["Buy (+1)", "Sell (-1)"])
        self._dir_combo.setFixedHeight(26)
        cb_style = (f"QComboBox{{background:{_BG};color:{_FG};"
                    f"border:1px solid {_BORDER};border-radius:3px;"
                    f"padding:0 6px;font-size:10px;}}"
                    f"QComboBox::drop-down{{border:none;}}")
        self._dir_combo.setStyleSheet(cb_style); vb.addWidget(self._dir_combo)
        vb.addWidget(_lbl("Regime", lbl_style))
        self._regime_combo = QtWidgets.QComboBox()
        self._regime_combo.addItems(["normal","stressed","illiquid","crisis"])
        self._regime_combo.setFixedHeight(26)
        self._regime_combo.setStyleSheet(cb_style); vb.addWidget(self._regime_combo)
        vb.addSpacing(4)
        vb.addWidget(_btn("▶  Simulate One",    _GRN, self._on_simulate_one, h=28))
        vb.addWidget(_btn("▶▶ Simulate × 10",   _BLUE, self._on_simulate_ten, h=28))
        vb.addWidget(_btn("▶▶▶ Simulate × 100", _ORG, self._on_simulate_hundred, h=28))
        vb.addSpacing(4)
        vb.addWidget(_btn("Clear Records", _MUT, self._on_clear, h=24, fs=9))
        vb.addStretch()
        self._status_lbl = _lbl("Ready", lbl_style)
        vb.addWidget(self._status_lbl)
        return panel

    def _build_record_table(self):
        w = QtWidgets.QWidget(); w.setStyleSheet(f"background:{_DARK};")
        vb = QtWidgets.QVBoxLayout(w)
        vb.setContentsMargins(0, 0, 0, 0); vb.setSpacing(4)
        hdr = QtWidgets.QHBoxLayout()
        hdr.addWidget(_lbl("Execution Records",
                           f"color:{_YLW};font-size:10px;font-weight:bold;"
                           f"border:none;background:transparent;"))
        hdr.addStretch()
        self._rec_count_lbl = _lbl("0 records",
                                    f"color:{_MUT};font-size:9px;"
                                    f"border:none;background:transparent;")
        hdr.addWidget(self._rec_count_lbl); vb.addLayout(hdr)
        cols = ["Time","Symbol","Dir","Size","Order Px","Realized Px",
                "Slip bps","Fill %","Lat ms","Rejected","Regime"]
        self._table = QtWidgets.QTableWidget(0, len(cols))
        self._table.setHorizontalHeaderLabels(cols)
        self._table.setEditTriggers(
            QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
        self._table.setSelectionBehavior(
            QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
        self._table.setAlternatingRowColors(True)
        self._table.horizontalHeader().setStretchLastSection(True)
        self._table.verticalHeader().setVisible(False)
        self._table.setShowGrid(False)
        self._table.setStyleSheet(
            f"QTableWidget{{background:{_BG};color:{_FG};"
            f"border:1px solid {_BORDER};font-size:9px;}}"
            f"QTableWidget::item{{padding:2px 5px;}}"
            f"QTableWidget::item:selected{{background:{_HEAD};}}"
            f"QTableWidget::item:alternate{{background:#1a1a2e;}}"
            f"QHeaderView::section{{background:{_HEAD};color:{_MUT};"
            f"border:none;border-right:1px solid {_BORDER};"
            f"font-size:9px;padding:3px 5px;}}")
        for i, cw in enumerate([78,85,36,65,95,95,74,58,70,58,75]):
            self._table.setColumnWidth(i, cw)
        vb.addWidget(self._table)
        return w

    def _build_stats_bar(self):
        w = QtWidgets.QWidget(); w.setFixedHeight(42)
        w.setStyleSheet(
            f"background:{_HEAD};border-radius:4px;border:1px solid {_BORDER};")
        h = QtWidgets.QHBoxLayout(w)
        h.setContentsMargins(14, 5, 14, 5); h.setSpacing(18)
        h.addWidget(_lbl("Stats",
                         f"color:{_MUT};font-size:9px;font-weight:bold;"
                         f"border:none;background:transparent;"))
        self._stat_lbls: dict[str, QtWidgets.QLabel] = {}
        for key, label, color in [
            ("p50",    "p50 Slip",    _GRN),
            ("p95",    "p95 Slip",    _YLW),
            ("n_rej",  "Rejected",    _RED),
            ("n_fill", "Partial Fill",_ORG),
            ("phase",  "Phase",       _MAV),
        ]:
            cell = QtWidgets.QWidget()
            cell.setStyleSheet("background:transparent;border:none;")
            ch = QtWidgets.QHBoxLayout(cell)
            ch.setContentsMargins(0, 0, 0, 0); ch.setSpacing(4)
            ch.addWidget(_lbl(f"{label}:",
                              f"color:{_MUT};font-size:9px;"
                              f"border:none;background:transparent;"))
            lv = _lbl("--",
                       f"color:{color};font-size:10px;font-weight:bold;"
                       f"border:none;background:transparent;")
            ch.addWidget(lv); self._stat_lbls[key] = lv; h.addWidget(cell)
        self._stat_lbls["phase"].setText("2")
        h.addStretch()
        return w

    # ── order params helper ───────────────────────────────────────────
    def _build_order_params(self) -> dict:
        def _f(k):
            try: return float(self._inputs[k].text())
            except ValueError: return 0.0
        return {
            "symbol":       self._inputs["symbol"].text().strip() or "UNKNOWN",
            "direction":    1 if self._dir_combo.currentIndex() == 0 else -1,
            "order_size":   _f("order_size"),
            "market_price": _f("market_price"),
            "adv":          _f("adv"),
            "volatility":   _f("volatility"),
            "spread_bps":   _f("spread_bps"),
            "regime":       self._regime_combo.currentText(),
        }

    # ── slots ─────────────────────────────────────────────────────────
    def _on_simulate_one(self):
        if not self._engine:
            self._status_lbl.setText("No engine"); return
        self._engine.simulate_execution(self._build_order_params())
        self._status_lbl.setText(
            f"[{str(datetime.now())[11:19]}] Simulated 1 order")

    def _on_simulate_ten(self):
        if not self._engine: return
        self._engine.simulate_batch([self._build_order_params()] * 10,
                                     seed_start=1000)
        self._status_lbl.setText(
            f"[{str(datetime.now())[11:19]}] Simulated 10 orders")

    def _on_simulate_hundred(self):
        if not self._engine: return
        self._engine.simulate_batch([self._build_order_params()] * 100,
                                     seed_start=2000)
        self._status_lbl.setText(
            f"[{str(datetime.now())[11:19]}] Simulated 100 orders")

    def _on_clear(self):
        self._records.clear(); self._table.setRowCount(0)
        self._rec_count_lbl.setText("0 records")
        self._total_lbl.setText("Simulations: 0")
        for lv in self._kpi.values(): lv.setText("--")
        for lv in self._stat_lbls.values(): lv.setText("--")
        self._stat_lbls["phase"].setText("2")

    # ── event handlers ────────────────────────────────────────────────
    def _on_execution_simulated(self, event):
        d = event.data or {}; es = d.get("execution_state", {})
        n = es.get("total_simulations", 0)
        self._total_lbl.setText(f"Simulations: {n}")
        def _fmt(v, suffix=""): return f"{v}{suffix}" if v is not None else "--"
        self._kpi["avg_slip"].setText(_fmt(round(es.get("avg_slippage_bps", 0), 2), " bps"))
        self._kpi["fill_rate"].setText(f"{es.get('avg_fill_rate', 0):.1%}")
        self._kpi["rejection"].setText(f"{es.get('rejection_rate', 0):.1%}")
        self._kpi["latency"].setText(_fmt(round(es.get("avg_latency_ms", 0), 1), " ms"))
        self._kpi["reality_gap"].setText(_fmt(round(es.get("reality_gap_bps", 0), 2), " bps"))
        self._stat_lbls["p50"].setText(f"{es.get('p50_slippage_bps', 0):.2f}bps")
        self._stat_lbls["p95"].setText(f"{es.get('p95_slippage_bps', 0):.2f}bps")
        self._stat_lbls["n_rej"].setText(str(es.get("total_rejected", 0)))
        n_partial = sum(1 for r in self._records
                        if 0.0 < r.get("fill_rate", 1.0) < 0.99)
        self._stat_lbls["n_fill"].setText(str(n_partial))

    def _on_slippage_recorded(self, event):
        d = event.data or {}
        self._records.append(d)
        if len(self._records) > 500:
            self._records = self._records[-500:]
        self._add_table_row(d)
        self._rec_count_lbl.setText(f"{len(self._records)} records")

    def _add_table_row(self, d: dict):
        row = self._table.rowCount(); self._table.insertRow(row)
        ts   = str(d.get("timestamp", ""))[-8:]
        dirv = "B" if d.get("direction", 1) > 0 else "S"
        vals = [
            ts,
            str(d.get("symbol", "")),
            dirv,
            f"{d.get('order_size', 0):.0f}",
            f"{d.get('order_price', 0):.4f}",
            f"{d.get('realized_price', 0):.4f}",
            f"{d.get('slippage_bps', 0):.2f}",
            f"{d.get('fill_rate', 1.0):.1%}",
            f"{d.get('latency_ms', 0):.1f}",
            "REJ" if d.get("rejected") else "OK",
            str(d.get("regime", "normal")),
        ]
        rej = d.get("rejected"); part = 0.0 < d.get("fill_rate", 1.0) < 0.99
        for col, val in enumerate(vals):
            item = QtWidgets.QTableWidgetItem(val)
            item.setTextAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
            if rej:
                item.setForeground(QtGui.QColor(_RED))
            elif part:
                item.setForeground(QtGui.QColor(_ORG))
            self._table.setItem(row, col, item)
        self._table.scrollToBottom()
        if self._table.rowCount() > 200:
            self._table.removeRow(0)

    def closeEvent(self, event):
        if self._event_engine:
            try:
                self._event_engine.unregister(
                    EVENT_EXECUTION_SIMULATED, self._on_execution_simulated)
                self._event_engine.unregister(
                    EVENT_SLIPPAGE_RECORDED, self._on_slippage_recorded)
            except Exception:
                pass
        super().closeEvent(event)
