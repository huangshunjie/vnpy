"""
market_regime_ai/ui/trend_tab.py  (Phase 3)

TrendTab — 趋势面板。
"""

from __future__ import annotations
from vnpy.trader.ui import QtCore, QtWidgets, QtGui

_PANEL  = "#181825"
_BORDER = "#45475a"
_FG     = "#cdd6f4"
_MUT    = "#6c7086"
_GRN    = "#a6e3a1"
_RED    = "#f38ba8"
_YLW    = "#f9e2af"
_MAV    = "#cba6f7"
_BLU    = "#89b4fa"

_DIR_COLORS = {
    "strong_up":   _GRN,
    "weak_up":     "#74c7ec",
    "flat":        _MUT,
    "weak_down":   _YLW,
    "strong_down": _RED,
}

_DIR_LABELS = {
    "strong_up":   "Strong Up  强势上涨",
    "weak_up":     "Weak Up  弱势上涨",
    "flat":        "Flat  横盘",
    "weak_down":   "Weak Down  弱势下跌",
    "strong_down": "Strong Down  强势下跌",
}


class TrendTab(QtWidgets.QWidget):
    """趋势面板（Phase 3）。"""

    def __init__(self, engine=None, parent=None) -> None:
        super().__init__(parent)
        self._engine = engine
        self._init_ui()

    def set_engine(self, engine) -> None:
        self._engine = engine

    def _init_ui(self) -> None:
        root = QtWidgets.QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(10)
        root.addWidget(self._build_kpi_row())
        mid = QtWidgets.QHBoxLayout()
        mid.setSpacing(10)
        mid.addWidget(self._build_gauges_panel(), stretch=1)
        mid.addWidget(self._build_detail_panel(), stretch=1)
        root.addLayout(mid)
        root.addWidget(self._build_action_bar())

    # ── KPI 行 ────────────────────────────────────────────────────────

    def _build_kpi_row(self) -> QtWidgets.QWidget:
        row = QtWidgets.QWidget()
        row.setFixedHeight(90)
        row.setStyleSheet(
            f"background: {_PANEL}; border-radius: 8px;"
            f" border: 1px solid {_BORDER};")
        h = QtWidgets.QHBoxLayout(row)
        h.setContentsMargins(20, 10, 20, 10)
        h.setSpacing(36)
        self._dir_blk        = self._kpi("趋势方向",   "FLAT",  _MUT, big=True)
        self._strength_blk   = self._kpi("趋势强度",   "0.00",  _FG)
        self._persistence_blk= self._kpi("趋势持续性", "0.00",  _FG)
        self._adx_blk        = self._kpi("ADX",        "0.0",   _FG)
        self._r2_blk         = self._kpi("R²",         "0.000", _FG)
        self._bars_blk       = self._kpi("持续 Bars",  "0",     _FG)
        for w in [self._dir_blk, self._strength_blk, self._persistence_blk,
                  self._adx_blk, self._r2_blk, self._bars_blk]:
            h.addWidget(w)
        h.addStretch()
        return row

    def _kpi(self, title, value, color, big=False):
        w = QtWidgets.QWidget()
        w.setStyleSheet("border: none; background: transparent;")
        v = QtWidgets.QVBoxLayout(w)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(2)
        tl = QtWidgets.QLabel(title)
        tl.setStyleSheet(f"color: {_MUT}; font-size: 9px; border: none;")
        size = "17px" if big else "15px"
        vl = QtWidgets.QLabel(value)
        vl.setStyleSheet(
            f"color: {color}; font-size: {size}; font-weight: bold; border: none;")
        v.addWidget(tl)
        v.addWidget(vl)
        w._vl = vl
        return w

    # ── 强度仪表盘 ────────────────────────────────────────────────────

    def _build_gauges_panel(self) -> QtWidgets.QWidget:
        panel = QtWidgets.QWidget()
        panel.setStyleSheet(
            f"background: {_PANEL}; border-radius: 8px;"
            f" border: 1px solid {_BORDER};")
        v = QtWidgets.QVBoxLayout(panel)
        v.setContentsMargins(14, 12, 14, 12)
        v.setSpacing(10)
        title = QtWidgets.QLabel("Trend Gauges  强度仪表")
        title.setStyleSheet(
            f"color: {_MAV}; font-size: 11px; font-weight: bold; border: none;")
        v.addWidget(title)
        v.addWidget(self._sep())

        self._strength_bar   = self._gauge_row("趋势强度",   _GRN)
        self._persist_bar    = self._gauge_row("趋势持续性", _BLU)
        self._r2_bar         = self._gauge_row("R²",         _MAV)
        self._adx_bar_widget = self._gauge_row("ADX(×100)",  _YLW)

        for widget in [self._strength_bar[0], self._persist_bar[0],
                       self._r2_bar[0],       self._adx_bar_widget[0]]:
            v.addWidget(widget)
        v.addStretch()
        return panel

    def _gauge_row(self, label, color):
        row = QtWidgets.QWidget()
        row.setStyleSheet("background: transparent; border: none;")
        h = QtWidgets.QHBoxLayout(row)
        h.setContentsMargins(0, 0, 0, 0)
        h.setSpacing(8)
        lbl = QtWidgets.QLabel(label)
        lbl.setFixedWidth(72)
        lbl.setStyleSheet(f"color: {_MUT}; font-size: 10px; border: none;")
        bar = QtWidgets.QProgressBar()
        bar.setRange(0, 100)
        bar.setValue(0)
        bar.setTextVisible(False)
        bar.setFixedHeight(12)
        bar.setStyleSheet(f"""
            QProgressBar {{ background: #11111b; border-radius: 6px;
                border: 1px solid {_BORDER}; }}
            QProgressBar::chunk {{ background: {color}; border-radius: 6px; }}
        """)
        val_lbl = QtWidgets.QLabel("0.00")
        val_lbl.setFixedWidth(40)
        val_lbl.setStyleSheet(f"color: {_FG}; font-size: 10px; border: none;")
        val_lbl.setAlignment(QtCore.Qt.AlignmentFlag.AlignRight)
        h.addWidget(lbl)
        h.addWidget(bar, stretch=1)
        h.addWidget(val_lbl)
        return row, bar, val_lbl

    # ── 详情面板 ──────────────────────────────────────────────────────

    def _build_detail_panel(self) -> QtWidgets.QWidget:
        panel = QtWidgets.QWidget()
        panel.setStyleSheet(
            f"background: {_PANEL}; border-radius: 8px;"
            f" border: 1px solid {_BORDER};")
        v = QtWidgets.QVBoxLayout(panel)
        v.setContentsMargins(14, 12, 14, 12)
        v.setSpacing(8)
        title = QtWidgets.QLabel("Trend Details  趋势详情")
        title.setStyleSheet(
            f"color: {_MAV}; font-size: 11px; font-weight: bold; border: none;")
        v.addWidget(title)
        v.addWidget(self._sep())
        self._detail_table = QtWidgets.QTableWidget(0, 2)
        self._detail_table.setHorizontalHeaderLabels(["指标", "值"])
        self._detail_table.horizontalHeader().setSectionResizeMode(
            QtWidgets.QHeaderView.ResizeMode.Stretch)
        self._detail_table.setEditTriggers(
            QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
        self._detail_table.verticalHeader().setVisible(False)
        self._detail_table.setStyleSheet(f"""
            QTableWidget {{ background: #11111b; color: {_FG};
                border: 1px solid {_BORDER}; gridline-color: {_BORDER};
                font-size: 11px; }}
            QHeaderView::section {{ background: #313244; color: {_MUT};
                padding: 4px; border: none; font-size: 10px; }}
        """)
        v.addWidget(self._detail_table, stretch=1)
        return panel

    def _build_action_bar(self) -> QtWidgets.QWidget:
        bar = QtWidgets.QWidget()
        bar.setFixedHeight(44)
        h = QtWidgets.QHBoxLayout(bar)
        h.setContentsMargins(0, 0, 0, 0)
        btn = self._btn("Refresh  刷新", _MUT)
        btn.clicked.connect(self.refresh)
        h.addWidget(btn)
        h.addStretch()
        return bar

    def _btn(self, text, color):
        b = QtWidgets.QPushButton(text)
        b.setStyleSheet(f"""
            QPushButton {{ background: transparent; color: {color};
                border: 1px solid {color}; border-radius: 4px;
                padding: 6px 18px; font-size: 12px; }}
            QPushButton:hover {{ background: {color}22; }}
        """)
        return b

    def _sep(self):
        s = QtWidgets.QFrame()
        s.setFrameShape(QtWidgets.QFrame.Shape.HLine)
        s.setStyleSheet(f"border: none; border-top: 1px solid {_BORDER};")
        return s

    # ── 刷新 ──────────────────────────────────────────────────────────

    def refresh(self) -> None:
        if self._engine is None:
            return
        try:
            st = self._engine.get_trend_state()
        except Exception:
            return
        self._update_kpi(st)
        self._update_gauges(st)
        self._update_detail(st)

    def _update_kpi(self, st) -> None:
        direction = st.direction.value
        color     = _DIR_COLORS.get(direction, _MUT)
        label     = _DIR_LABELS.get(direction, direction.upper())
        self._dir_blk._vl.setText(label)
        self._dir_blk._vl.setStyleSheet(
            f"color: {color}; font-size: 15px; font-weight: bold; border: none;")
        self._strength_blk._vl.setText(f"{st.strength:.3f}")
        self._persistence_blk._vl.setText(f"{st.persistence:.3f}")
        self._adx_blk._vl.setText(f"{st.adx:.1f}")
        self._r2_blk._vl.setText(f"{st.r_squared:.3f}")
        self._bars_blk._vl.setText(str(st.bars_in_trend))

    def _update_gauges(self, st) -> None:
        def _set(triple, val, scale=1.0):
            _, bar, lbl = triple
            bar.setValue(int(min(100, val * scale * 100)))
            lbl.setText(f"{val:.3f}")
        _set(self._strength_bar,   st.strength)
        _set(self._persist_bar,    st.persistence)
        _set(self._r2_bar,         st.r_squared)
        _set(self._adx_bar_widget, st.adx / 100.0)

    def _update_detail(self, st) -> None:
        rows = [
            ("Direction",    st.direction.value),
            ("Strength",     f"{st.strength:.4f}"),
            ("Persistence",  f"{st.persistence:.4f}"),
            ("ADX",          f"{st.adx:.2f}"),
            ("Slope",        f"{st.slope:.8f}"),
            ("R²",           f"{st.r_squared:.4f}"),
            ("Bars in Trend", str(st.bars_in_trend)),
            ("Updated At",   str(st.updated_at)[:19]),
        ]
        self._detail_table.setRowCount(len(rows))
        for i, (k, v) in enumerate(rows):
            ki = QtWidgets.QTableWidgetItem(k)
            vi = QtWidgets.QTableWidgetItem(v)
            ki.setTextAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
            vi.setTextAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
            self._detail_table.setItem(i, 0, ki)
            self._detail_table.setItem(i, 1, vi)

    def update_from_event(self, data: dict) -> None:
        direction = data.get("direction", "flat")
        color     = _DIR_COLORS.get(direction, _MUT)
        label     = _DIR_LABELS.get(direction, direction.upper())
        self._dir_blk._vl.setText(label)
        self._dir_blk._vl.setStyleSheet(
            f"color: {color}; font-size: 15px; font-weight: bold; border: none;")
        self._strength_blk._vl.setText(
            f"{float(data.get('strength', 0)):.3f}")
