"""
market_regime_ai/ui/volatility_tab.py  (Phase 3)

VolatilityTab — 波动率面板。
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
_ORG    = "#fab387"

_VOL_COLORS = {
    "low":     _GRN,
    "normal":  _FG,
    "high":    _YLW,
    "extreme": _RED,
}


class VolatilityTab(QtWidgets.QWidget):
    """波动率面板（Phase 3）。"""

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
        root.addWidget(self._build_detail_panel())
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
        self._regime_blk  = self._kpi("Vol Regime",   "NORMAL", _FG)
        self._vol20_blk   = self._kpi("Vol 20",       "---",    _FG)
        self._vol60_blk   = self._kpi("Vol 60",       "---",    _FG)
        self._realized_blk = self._kpi("Realized Vol", "---",   _FG)
        self._pct_blk     = self._kpi("Percentile",   "---",    _FG)
        self._ratio_blk   = self._kpi("Vol Ratio",    "---",    _FG)
        self._spike_blk   = self._kpi("Spike",        "NO",     _GRN)
        for w in [self._regime_blk, self._vol20_blk, self._vol60_blk,
                  self._realized_blk, self._pct_blk, self._ratio_blk,
                  self._spike_blk]:
            h.addWidget(w)
        h.addStretch()
        return row

    def _kpi(self, title, value, color):
        w = QtWidgets.QWidget()
        w.setStyleSheet("border: none; background: transparent;")
        v = QtWidgets.QVBoxLayout(w)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(2)
        tl = QtWidgets.QLabel(title)
        tl.setStyleSheet(f"color: {_MUT}; font-size: 9px; border: none;")
        vl = QtWidgets.QLabel(value)
        vl.setStyleSheet(
            f"color: {color}; font-size: 15px; font-weight: bold; border: none;")
        v.addWidget(tl)
        v.addWidget(vl)
        w._vl = vl
        return w

    # ── 详细面板 ──────────────────────────────────────────────────────

    def _build_detail_panel(self) -> QtWidgets.QWidget:
        panel = QtWidgets.QWidget()
        panel.setStyleSheet(
            f"background: {_PANEL}; border-radius: 8px;"
            f" border: 1px solid {_BORDER};")
        v = QtWidgets.QVBoxLayout(panel)
        v.setContentsMargins(14, 12, 14, 12)
        v.setSpacing(8)
        title = QtWidgets.QLabel("Volatility Details  波动率详情")
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
        h.setSpacing(8)
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
            st = self._engine.get_vol_state()
        except Exception:
            return
        self._update_kpi(st)
        self._update_detail(st)

    def _update_kpi(self, st) -> None:
        regime = st.regime.value
        color  = _VOL_COLORS.get(regime, _FG)
        self._regime_blk._vl.setText(regime.upper())
        self._regime_blk._vl.setStyleSheet(
            f"color: {color}; font-size: 15px; font-weight: bold; border: none;")
        self._vol20_blk._vl.setText(f"{st.rolling_vol_20:.2%}")
        self._vol60_blk._vl.setText(f"{st.rolling_vol_60:.2%}")
        self._realized_blk._vl.setText(f"{st.realized_vol:.2%}")
        self._pct_blk._vl.setText(f"{st.vol_percentile:.1%}")
        ratio = st.vol_ratio
        ratio_color = _RED if ratio > 1.3 else (_GRN if ratio < 0.8 else _FG)
        self._ratio_blk._vl.setText(f"{ratio:.2f}x")
        self._ratio_blk._vl.setStyleSheet(
            f"color: {ratio_color}; font-size: 15px; font-weight: bold; border: none;")
        spike = st.meta.get("spike", False)
        self._spike_blk._vl.setText("YES" if spike else "NO")
        self._spike_blk._vl.setStyleSheet(
            f"color: {_RED if spike else _GRN}; font-size: 15px;"
            f" font-weight: bold; border: none;")

    def _update_detail(self, st) -> None:
        rows = [
            ("Vol Regime",     st.regime.value),
            ("Rolling Vol 20", f"{st.rolling_vol_20:.4f}"),
            ("Rolling Vol 60", f"{st.rolling_vol_60:.4f}"),
            ("Realized Vol",   f"{st.realized_vol:.4f}"),
            ("Vol Percentile", f"{st.vol_percentile:.4f}"),
            ("Vol Ratio",      f"{st.vol_ratio:.4f}"),
            ("Regime Shifted", str(st.regime_shifted)),
            ("Avg Vol",        str(st.meta.get("avg_vol", "---"))),
            ("Spike",          str(st.meta.get("spike",   False))),
            ("Updated At",     str(st.updated_at)[:19]),
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
        regime = data.get("regime", "normal")
        color  = _VOL_COLORS.get(regime, _FG)
        self._regime_blk._vl.setText(regime.upper())
        self._regime_blk._vl.setStyleSheet(
            f"color: {color}; font-size: 15px; font-weight: bold; border: none;")
        self._vol20_blk._vl.setText(
            f"{float(data.get('rolling_vol_20', 0)):.2%}")
        self._pct_blk._vl.setText(
            f"{float(data.get('vol_percentile', 0)):.1%}")
