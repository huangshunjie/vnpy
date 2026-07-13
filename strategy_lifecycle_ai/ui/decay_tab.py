"""
strategy_lifecycle_ai/ui/decay_tab.py  (Phase 3)

DecayTab — 衰减监控面板（完整实现）。
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
_BLU    = "#89b4fa"

_LEVEL_COLORS = {
    "none": _MUT, "mild": _BLU,
    "moderate": _YLW, "severe": _ORG, "critical": _RED,
}


class DecayTab(QtWidgets.QWidget):
    """衰减监控面板（Phase 3 完整实现）。"""

    def __init__(self, engine=None, parent=None) -> None:
        super().__init__(parent)
        self._engine           = engine
        self._current_strategy = ""
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
        mid.addWidget(self._build_monitor_panel(), stretch=1)
        mid.addWidget(self._build_detail_panel(),  stretch=1)
        root.addLayout(mid)
        root.addWidget(self._build_action_bar())

    def _build_kpi_row(self):
        row = QtWidgets.QWidget()
        row.setFixedHeight(90)
        row.setStyleSheet(
            f"background: {_PANEL}; border-radius: 8px; border: 1px solid {_BORDER};")
        h = QtWidgets.QHBoxLayout(row)
        h.setContentsMargins(20, 10, 20, 10)
        h.setSpacing(28)
        self._score_blk  = self._kpi("Decay Score",  "---",  _MUT, big=True)
        self._level_blk  = self._kpi("Decay Level",  "NONE", _MUT)
        self._sh_blk     = self._kpi("Sharpe Slope", "---",  _MUT)
        self._dd_blk     = self._kpi("DD Expansion", "---",  _MUT)
        self._ic_blk     = self._kpi("IC Decay",     "---",  _MUT)
        self._ps_blk     = self._kpi("Perf Slope",   "---",  _MUT)
        self._days_blk   = self._kpi("Decay Days",   "0",    _MUT)
        for w in [self._score_blk, self._level_blk, self._sh_blk,
                  self._dd_blk, self._ic_blk, self._ps_blk, self._days_blk]:
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
        vl = QtWidgets.QLabel(value)
        vl.setStyleSheet(
            f"color: {color}; font-size: {'18px' if big else '14px'};"
            f" font-weight: bold; border: none;")
        v.addWidget(tl); v.addWidget(vl)
        w._vl = vl
        return w

    def _build_monitor_panel(self):
        panel = QtWidgets.QWidget()
        panel.setStyleSheet(
            f"background: {_PANEL}; border-radius: 8px; border: 1px solid {_BORDER};")
        v = QtWidgets.QVBoxLayout(panel)
        v.setContentsMargins(14, 12, 14, 12)
        v.setSpacing(8)
        t = QtWidgets.QLabel("Decay Monitor  衰减监控表")
        t.setStyleSheet(
            f"color: {_MAV}; font-size: 11px; font-weight: bold; border: none;")
        v.addWidget(t); v.addWidget(self._sep())
        self._monitor_table = QtWidgets.QTableWidget(0, 6)
        self._monitor_table.setHorizontalHeaderLabels(
            ["策略 ID", "等级", "评分", "Sh斜率", "DD扩张", "持续天"])
        self._monitor_table.horizontalHeader().setSectionResizeMode(
            QtWidgets.QHeaderView.ResizeMode.Stretch)
        self._monitor_table.setEditTriggers(
            QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
        self._monitor_table.setSelectionBehavior(
            QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
        self._monitor_table.verticalHeader().setVisible(False)
        self._monitor_table.setAlternatingRowColors(True)
        self._monitor_table.setStyleSheet(
            f"QTableWidget {{ background:#11111b; color:{_FG}; border:1px solid {_BORDER}; gridline-color:{_BORDER}; font-size:11px; }}"
            f"QHeaderView::section {{ background:#313244; color:{_MUT}; padding:4px; border:none; font-size:10px; }}"
            f"QTableWidget::item:alternate {{ background:#181825; }}"
        )
        self._monitor_table.cellClicked.connect(self._on_monitor_clicked)
        v.addWidget(self._monitor_table, stretch=1)
        self._monitor_count = QtWidgets.QLabel("0 decaying")
        self._monitor_count.setStyleSheet(f"color: {_MUT}; font-size: 10px; border: none;")
        v.addWidget(self._monitor_count)
        return panel

    def _build_detail_panel(self):
        panel = QtWidgets.QWidget()
        panel.setStyleSheet(
            f"background: {_PANEL}; border-radius: 8px; border: 1px solid {_BORDER};")
        v = QtWidgets.QVBoxLayout(panel)
        v.setContentsMargins(14, 12, 14, 12)
        v.setSpacing(8)
        t1 = QtWidgets.QLabel("Decay Detail  衰减详情")
        t1.setStyleSheet(
            f"color: {_MAV}; font-size: 11px; font-weight: bold; border: none;")
        v.addWidget(t1); v.addWidget(self._sep())
        self._detail_table = QtWidgets.QTableWidget(0, 2)
        self._detail_table.setHorizontalHeaderLabels(["指标", "值"])
        self._detail_table.horizontalHeader().setSectionResizeMode(
            QtWidgets.QHeaderView.ResizeMode.Stretch)
        self._detail_table.setEditTriggers(
            QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
        self._detail_table.verticalHeader().setVisible(False)
        self._detail_table.setFixedHeight(260)
        self._detail_table.setStyleSheet(
            f"QTableWidget {{ background:#11111b; color:{_FG}; border:1px solid {_BORDER}; gridline-color:{_BORDER}; font-size:11px; }}"
            f"QHeaderView::section {{ background:#313244; color:{_MUT}; padding:4px; border:none; font-size:10px; }}"
        )
        v.addWidget(self._detail_table)
        t2 = QtWidgets.QLabel("Decay History  历史记录")
        t2.setStyleSheet(
            f"color: {_MAV}; font-size: 11px; font-weight: bold; border: none;")
        v.addWidget(t2); v.addWidget(self._sep())
        self._history_table = QtWidgets.QTableWidget(0, 5)
        self._history_table.setHorizontalHeaderLabels(["Bar", "等级", "评分", "Sh斜率", "时间"])
        self._history_table.horizontalHeader().setSectionResizeMode(
            QtWidgets.QHeaderView.ResizeMode.Stretch)
        self._history_table.setEditTriggers(
            QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
        self._history_table.verticalHeader().setVisible(False)
        self._history_table.setStyleSheet(
            f"QTableWidget {{ background:#11111b; color:{_FG}; border:1px solid {_BORDER}; gridline-color:{_BORDER}; font-size:11px; }}"
            f"QHeaderView::section {{ background:#313244; color:{_MUT}; padding:4px; border:none; font-size:10px; }}"
        )
        v.addWidget(self._history_table, stretch=1)
        return panel

    def _build_action_bar(self):
        bar = QtWidgets.QWidget()
        bar.setFixedHeight(44)
        h = QtWidgets.QHBoxLayout(bar)
        h.setContentsMargins(0, 0, 0, 0)
        h.setSpacing(8)
        h.addWidget(QtWidgets.QLabel("Strategy:"))
        self._strategy_combo = QtWidgets.QComboBox()
        self._strategy_combo.setMinimumWidth(200)
        self._strategy_combo.setStyleSheet(
            f"QComboBox {{ background: #11111b; color: {_FG}; "
            f"border: 1px solid {_BORDER}; border-radius: 4px; "
            f"padding: 4px 8px; font-size: 11px; }}"
            f"QComboBox::drop-down {{ border: none; }}"
            f"QComboBox QAbstractItemView {{ background: #11111b; "
            f"color: {_FG}; border: 1px solid {_BORDER}; }}"
        )
        self._strategy_combo.currentTextChanged.connect(self._on_strategy_changed)
        h.addWidget(self._strategy_combo)
        btn = self._btn("Refresh  刷新", _MUT)
        btn.clicked.connect(self.refresh)
        h.addWidget(btn)
        h.addStretch()
        self._status_lbl = QtWidgets.QLabel("")
        self._status_lbl.setStyleSheet(f"color: {_MUT}; font-size: 11px;")
        h.addWidget(self._status_lbl)
        return bar

    def _btn(self, text, color):
        b = QtWidgets.QPushButton(text)
        b.setStyleSheet(
            f"QPushButton {{ background: transparent; color: {color}; "
            f"border: 1px solid {color}; border-radius: 4px; "
            f"padding: 5px 16px; font-size: 11px; }}"
            f"QPushButton:hover {{ background: {color}22; }}"
        )
        return b

    def _sep(self):
        s = QtWidgets.QFrame()
        s.setFrameShape(QtWidgets.QFrame.Shape.HLine)
        s.setStyleSheet(f"border: none; border-top: 1px solid {_BORDER};")
        return s

    def refresh(self):
        if self._engine is None:
            return
        try:
            self._refresh_strategy_list()
            self._refresh_monitor()
            sid = self._current_strategy or self._strategy_combo.currentText()
            if sid:
                self._refresh_detail(sid)
        except Exception as e:
            self._status_lbl.setText(f"Error: {e}")

    def _refresh_strategy_list(self):
        try:
            strategies = self._engine.get_all_strategies()
            combo = self._strategy_combo
            current = combo.currentText()
            combo.blockSignals(True)
            combo.clear()
            for s in strategies:
                combo.addItem(s.strategy_id)
            if current in [s.strategy_id for s in strategies]:
                combo.setCurrentText(current)
            elif strategies:
                combo.setCurrentIndex(0)
            combo.blockSignals(False)
        except Exception:
            pass

    def _refresh_monitor(self):
        try:
            decaying = self._engine.get_decaying_strategies()
        except Exception:
            return
        self._monitor_table.setRowCount(0)
        for ds in decaying:
            row = self._monitor_table.rowCount()
            self._monitor_table.insertRow(row)
            level = ds.decay_level.value
            lc    = _LEVEL_COLORS.get(level, _MUT)
            sc    = _RED if ds.decay_score > 0.55 else (_YLW if ds.decay_score > 0.35 else _MUT)
            items = [
                ds.strategy_id, level.upper(),
                f"{ds.decay_score:.3f}", f"{ds.sharpe_slope:.5f}",
                f"{ds.dd_expansion:.4f}", str(ds.decay_days),
            ]
            colors = [_FG, lc, sc, _MUT, _MUT, _MUT]
            for col, (text, color) in enumerate(zip(items, colors)):
                item = QtWidgets.QTableWidgetItem(text)
                item.setTextAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
                item.setForeground(QtGui.QColor(color))
                self._monitor_table.setItem(row, col, item)
        self._monitor_count.setText(f"{len(decaying)} decaying")

    def _refresh_detail(self, strategy_id):
        try:
            ds = self._engine.get_decay_state(strategy_id)
        except Exception:
            return
        self._update_kpi(ds)
        self._update_detail_table(ds)
        self._update_history_table(strategy_id)
        self._status_lbl.setText(f"Strategy: {strategy_id}")

    def _update_kpi(self, ds):
        score = ds.decay_score
        level = ds.decay_level.value
        lc    = _LEVEL_COLORS.get(level, _MUT)
        sc    = _RED if score > 0.55 else (_YLW if score > 0.35 else _GRN)
        self._score_blk._vl.setText(f"{score:.3f}")
        self._score_blk._vl.setStyleSheet(
            f"color: {sc}; font-size: 18px; font-weight: bold; border: none;")
        self._level_blk._vl.setText(level.upper())
        self._level_blk._vl.setStyleSheet(
            f"color: {lc}; font-size: 14px; font-weight: bold; border: none;")
        sh_c = _RED if ds.sharpe_slope < -0.005 else _GRN
        self._sh_blk._vl.setText(f"{ds.sharpe_slope:.5f}")
        self._sh_blk._vl.setStyleSheet(
            f"color: {sh_c}; font-size: 14px; font-weight: bold; border: none;")
        dd_c = _RED if ds.dd_expansion > 0.01 else _GRN
        self._dd_blk._vl.setText(f"{ds.dd_expansion:.4f}")
        self._dd_blk._vl.setStyleSheet(
            f"color: {dd_c}; font-size: 14px; font-weight: bold; border: none;")
        ic_c = _RED if ds.ic_decay_proxy > 0.6 else _MUT
        self._ic_blk._vl.setText(f"{ds.ic_decay_proxy:.4f}")
        self._ic_blk._vl.setStyleSheet(
            f"color: {ic_c}; font-size: 14px; font-weight: bold; border: none;")
        ps_c = _RED if ds.perf_slope < -0.005 else _MUT
        self._ps_blk._vl.setText(f"{ds.perf_slope:.5f}")
        self._ps_blk._vl.setStyleSheet(
            f"color: {ps_c}; font-size: 14px; font-weight: bold; border: none;")
        days_c = _RED if ds.decay_days >= 5 else (_YLW if ds.decay_days >= 2 else _MUT)
        self._days_blk._vl.setText(str(ds.decay_days))
        self._days_blk._vl.setStyleSheet(
            f"color: {days_c}; font-size: 14px; font-weight: bold; border: none;")

    def _update_detail_table(self, ds):
        rows = [
            ("Strategy ID",        ds.strategy_id),
            ("Decay Level",        ds.decay_level.value.upper()),
            ("Decay Score",        f"{ds.decay_score:.6f}"),
            ("Sharpe Slope",       f"{ds.sharpe_slope:.6f}"),
            ("DD Expansion",       f"{ds.dd_expansion:.6f}"),
            ("IC Decay Proxy",     f"{ds.ic_decay_proxy:.6f}"),
            ("Perf Slope",         f"{ds.perf_slope:.6f}"),
            ("Decay Days",         str(ds.decay_days)),
            ("Regime Sensitivity", f"{ds.regime_sensitivity:.4f}"),
            ("Level Changed",      str(ds.level_changed)),
            ("Prev Level",         ds.prev_level.value.upper()),
            ("Detected At",        str(ds.detected_at)[:19]),
        ]
        self._detail_table.setRowCount(len(rows))
        for i, (k, v_) in enumerate(rows):
            ki = QtWidgets.QTableWidgetItem(k)
            vi = QtWidgets.QTableWidgetItem(v_)
            ki.setTextAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
            vi.setTextAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
            self._detail_table.setItem(i, 0, ki)
            self._detail_table.setItem(i, 1, vi)

    def _update_history_table(self, strategy_id):
        try:
            history = self._engine.get_decay_history(strategy_id, limit=20)
        except Exception:
            return
        self._history_table.setRowCount(0)
        for rec in reversed(history):
            row = self._history_table.rowCount()
            self._history_table.insertRow(row)
            level = rec.get("decay_level", "none")
            lc    = _LEVEL_COLORS.get(level, _MUT)
            items = [
                str(rec.get("bar_index", "")),
                level.upper(),
                f"{rec.get('decay_score', 0.0):.3f}",
                f"{rec.get('sharpe_slope', 0.0):.5f}",
                rec.get("detected_at", "")[:10],
            ]
            for col, text in enumerate(items):
                item = QtWidgets.QTableWidgetItem(text)
                item.setTextAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
                if col == 1:
                    item.setForeground(QtGui.QColor(lc))
                self._history_table.setItem(row, col, item)

    def _on_strategy_changed(self, sid):
        if sid:
            self._current_strategy = sid
            self._refresh_detail(sid)

    def _on_monitor_clicked(self, row, _col):
        item = self._monitor_table.item(row, 0)
        if item:
            sid = item.text()
            self._strategy_combo.setCurrentText(sid)
            self._refresh_detail(sid)

    def update_from_event(self, data):
        self._refresh_monitor()
        sid = data.get("strategy_id", "")
        if sid:
            try:
                ds = self._engine.get_decay_state(sid)
                self._update_kpi(ds)
            except Exception:
                pass
