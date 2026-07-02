"""
market_regime_ai/ui/liquidity_tab.py  (Phase 3)

LiquidityTab — 流动性面板。
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
_CYN    = "#89dceb"

_LIQ_COLORS = {
    "high":     _GRN,
    "normal":   _FG,
    "low":      _YLW,
    "very_low": _RED,
}

_LIQ_LABELS = {
    "high":     "High  高流动性",
    "normal":   "Normal  正常",
    "low":      "Low  低流动性",
    "very_low": "Very Low  极低流动性",
}


class LiquidityTab(QtWidgets.QWidget):
    """流动性面板（Phase 3）。"""

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
        mid.addWidget(self._build_scores_panel(), stretch=1)
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
        self._level_blk    = self._kpi("流动性水平",   "NORMAL", _FG, big=True)
        self._ill_blk      = self._kpi("非流动性评分", "0.00",   _FG)
        self._volr_blk     = self._kpi("成交量比率",   "1.00x",  _FG)
        self._spread_blk   = self._kpi("价差代理",     "---",    _FG)
        self._turn_blk     = self._kpi("换手率比率",   "---",    _FG)
        self._volpct_blk   = self._kpi("成交量分位",   "---",    _FG)
        for w in [self._level_blk, self._ill_blk, self._volr_blk,
                  self._spread_blk, self._turn_blk, self._volpct_blk]:
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

    # ── 评分条 ────────────────────────────────────────────────────────

    def _build_scores_panel(self) -> QtWidgets.QWidget:
        panel = QtWidgets.QWidget()
        panel.setStyleSheet(
            f"background: {_PANEL}; border-radius: 8px;"
            f" border: 1px solid {_BORDER};")
        v = QtWidgets.QVBoxLayout(panel)
        v.setContentsMargins(14, 12, 14, 12)
        v.setSpacing(10)
        title = QtWidgets.QLabel("Liquidity Scores  流动性评分")
        title.setStyleSheet(
            f"color: {_MAV}; font-size: 11px; font-weight: bold; border: none;")
        v.addWidget(title)
        v.addWidget(self._sep())

        self._ill_bar    = self._score_row("非流动性",   _RED)
        self._volr_bar   = self._score_row("成交量比率", _GRN)
        self._spread_bar = self._score_row("价差代理",   _YLW)
        self._turn_bar   = self._score_row("换手率",     _CYN)

        for row, _, _ in [self._ill_bar, self._volr_bar,
                          self._spread_bar, self._turn_bar]:
            v.addWidget(row)
        v.addStretch()
        return panel

    def _score_row(self, label, color):
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
        val_lbl.setFixedWidth(44)
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
        title = QtWidgets.QLabel("Liquidity Details  流动性详情")
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
            st = self._engine.get_liq_state()
        except Exception:
            return
        self._update_kpi(st)
        self._update_scores(st)
        self._update_detail(st)

    def _update_kpi(self, st) -> None:
        level = st.level.value
        color = _LIQ_COLORS.get(level, _FG)
        label = _LIQ_LABELS.get(level, level.upper())
        self._level_blk._vl.setText(label)
        self._level_blk._vl.setStyleSheet(
            f"color: {color}; font-size: 15px; font-weight: bold; border: none;")
        ill = st.illiquidity_score
        ill_color = _RED if ill > 0.7 else (_YLW if ill > 0.4 else _GRN)
        self._ill_blk._vl.setText(f"{ill:.3f}")
        self._ill_blk._vl.setStyleSheet(
            f"color: {ill_color}; font-size: 15px; font-weight: bold; border: none;")
        self._volr_blk._vl.setText(f"{st.volume_ratio:.2f}x")
        self._spread_blk._vl.setText(f"{st.spread_proxy:.5f}")
        self._turn_blk._vl.setText(f"{st.turnover_ratio:.2f}x")
        self._volpct_blk._vl.setText(f"{st.vol_percentile:.1%}")

    def _update_scores(self, st) -> None:
        def _set(triple, val):
            _, bar, lbl = triple
            bar.setValue(int(min(100, val * 100)))
            lbl.setText(f"{val:.3f}")
        _set(self._ill_bar,    st.illiquidity_score)
        vol_r_norm = min(1.0, st.volume_ratio / 3.0)
        _set(self._volr_bar,   vol_r_norm)
        spread_norm = min(1.0, st.spread_proxy * 20)
        _set(self._spread_bar, spread_norm)
        turn_norm = min(1.0, st.turnover_ratio / 3.0)
        _set(self._turn_bar,   turn_norm)

    def _update_detail(self, st) -> None:
        rows = [
            ("Level",            st.level.value),
            ("Illiquidity Score", f"{st.illiquidity_score:.4f}"),
            ("Volume Ratio",     f"{st.volume_ratio:.4f}"),
            ("Turnover Ratio",   f"{st.turnover_ratio:.4f}"),
            ("Spread Proxy",     f"{st.spread_proxy:.6f}"),
            ("Vol Percentile",   f"{st.vol_percentile:.4f}"),
            ("Amihud",           str(st.meta.get("amihud", "---"))),
            ("Has Volume Data",  str(st.meta.get("has_volume", False))),
            ("Updated At",       str(st.updated_at)[:19]),
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
        level = data.get("level", "normal")
        color = _LIQ_COLORS.get(level, _FG)
        label = _LIQ_LABELS.get(level, level.upper())
        self._level_blk._vl.setText(label)
        self._level_blk._vl.setStyleSheet(
            f"color: {color}; font-size: 15px; font-weight: bold; border: none;")
        ill = float(data.get("illiquidity_score", 0.0))
        self._ill_blk._vl.setText(f"{ill:.3f}")
