"""
strategy_lifecycle_ai/ui/performance_tab.py  (Phase 2)

PerformanceTab — 策略表现仪表盘（完整实现）。
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

_RATING_COLORS = {
    "excellent": _GRN, "good": _BLU,
    "neutral": _MUT, "weak": _RED, "unknown": _MUT,
}


class PerformanceTab(QtWidgets.QWidget):
    """策略表现仪表盘（Phase 2 完整实现）。"""

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
        mid.addWidget(self._build_multiperiod_panel(), stretch=1)
        mid.addWidget(self._build_ranking_panel(),     stretch=1)
        root.addLayout(mid)
        root.addWidget(self._build_action_bar())

    def _build_kpi_row(self):
        row = QtWidgets.QWidget()
        row.setFixedHeight(90)
        row.setStyleSheet(
            f"background: {_PANEL}; border-radius: 8px; border: 1px solid {_BORDER};")
        h = QtWidgets.QHBoxLayout(row)
        h.setContentsMargins(20, 10, 20, 10)
        h.setSpacing(32)
        self._sharpe_blk  = self._kpi("Sharpe",       "---", _MUT, big=True)
        self._sortino_blk = self._kpi("Sortino",      "---", _MUT)
        self._calmar_blk  = self._kpi("Calmar",       "---", _MUT)
        self._dd_blk      = self._kpi("Max Drawdown", "---", _MUT)
        self._wr_blk      = self._kpi("Win Rate",     "---", _MUT)
        self._ann_blk     = self._kpi("Ann Return",   "---", _MUT)
        self._rating_blk  = self._kpi("Rating",       "---", _MUT)
        for w in [self._sharpe_blk, self._sortino_blk, self._calmar_blk,
                  self._dd_blk, self._wr_blk, self._ann_blk, self._rating_blk]:
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
        v.addWidget(tl)
        v.addWidget(vl)
        w._vl = vl
        return w

    def _build_multiperiod_panel(self):
        panel = QtWidgets.QWidget()
        panel.setStyleSheet(
            f"background: {_PANEL}; border-radius: 8px; border: 1px solid {_BORDER};")
        v = QtWidgets.QVBoxLayout(panel)
        v.setContentsMargins(14, 12, 14, 12)
        v.setSpacing(8)
        t1 = QtWidgets.QLabel("Multi-Period Analysis  多周期统计")
        t1.setStyleSheet(
            f"color: {_MAV}; font-size: 11px; font-weight: bold; border: none;")
        v.addWidget(t1)
        v.addWidget(self._sep())
        self._period_table = QtWidgets.QTableWidget(3, 5)
        self._period_table.setHorizontalHeaderLabels(
            ["周期", "Sharpe", "MaxDD", "WinRate", "AnnReturn"])
        self._period_table.setVerticalHeaderLabels(["Daily", "Weekly", "Monthly"])
        self._period_table.horizontalHeader().setSectionResizeMode(
            QtWidgets.QHeaderView.ResizeMode.Stretch)
        self._period_table.setEditTriggers(
            QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
        self._period_table.setFixedHeight(130)
        self._period_table.setStyleSheet(
            f"QTableWidget {{ background: #11111b; color: {_FG}; "
            f"border: 1px solid {_BORDER}; gridline-color: {_BORDER}; font-size: 11px; }}"
            f"QHeaderView::section {{ background: #313244; color: {_MUT}; "
            f"padding: 4px; border: none; font-size: 10px; }}"
        )
        v.addWidget(self._period_table)
        t2 = QtWidgets.QLabel("Detail Metrics  详细指标")
        t2.setStyleSheet(
            f"color: {_MAV}; font-size: 11px; font-weight: bold; border: none;")
        v.addWidget(t2)
        v.addWidget(self._sep())
        self._detail_table = QtWidgets.QTableWidget(0, 2)
        self._detail_table.setHorizontalHeaderLabels(["指标", "值"])
        self._detail_table.horizontalHeader().setSectionResizeMode(
            QtWidgets.QHeaderView.ResizeMode.Stretch)
        self._detail_table.setEditTriggers(
            QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
        self._detail_table.verticalHeader().setVisible(False)
        self._detail_table.setStyleSheet(
            f"QTableWidget {{ background: #11111b; color: {_FG}; "
            f"border: 1px solid {_BORDER}; gridline-color: {_BORDER}; font-size: 11px; }}"
            f"QHeaderView::section {{ background: #313244; color: {_MUT}; "
            f"padding: 4px; border: none; font-size: 10px; }}"
        )
        v.addWidget(self._detail_table, stretch=1)
        return panel

    def _build_ranking_panel(self):
        panel = QtWidgets.QWidget()
        panel.setStyleSheet(
            f"background: {_PANEL}; border-radius: 8px; border: 1px solid {_BORDER};")
        v = QtWidgets.QVBoxLayout(panel)
        v.setContentsMargins(14, 12, 14, 12)
        v.setSpacing(8)
        title = QtWidgets.QLabel("Performance Ranking  绩效排名")
        title.setStyleSheet(
            f"color: {_MAV}; font-size: 11px; font-weight: bold; border: none;")
        v.addWidget(title)
        v.addWidget(self._sep())
        self._rank_table = QtWidgets.QTableWidget(0, 6)
        self._rank_table.setHorizontalHeaderLabels(
            ["策略 ID", "Sharpe", "MaxDD", "WinRate", "评级", "样本数"])
        self._rank_table.horizontalHeader().setSectionResizeMode(
            QtWidgets.QHeaderView.ResizeMode.Stretch)
        self._rank_table.setEditTriggers(
            QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
        self._rank_table.setSelectionBehavior(
            QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
        self._rank_table.verticalHeader().setVisible(False)
        self._rank_table.setAlternatingRowColors(True)
        self._rank_table.setStyleSheet(
            f"QTableWidget {{ background: #11111b; color: {_FG}; "
            f"border: 1px solid {_BORDER}; gridline-color: {_BORDER}; font-size: 11px; }}"
            f"QHeaderView::section {{ background: #313244; color: {_MUT}; "
            f"padding: 4px; border: none; font-size: 10px; }}"
            f"QTableWidget::item:alternate {{ background: #181825; }}"
        )
        self._rank_table.cellClicked.connect(self._on_rank_clicked)
        v.addWidget(self._rank_table, stretch=1)
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
        refresh_btn = self._btn("Refresh  刷新", _MUT)
        refresh_btn.clicked.connect(self.refresh)
        h.addWidget(refresh_btn)
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
            self._refresh_ranking()
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
            ids = [s.strategy_id for s in strategies]
            if current in ids:
                combo.setCurrentText(current)
            elif strategies:
                combo.setCurrentIndex(0)
            combo.blockSignals(False)
        except Exception:
            pass

    def _refresh_ranking(self):
        try:
            ranking = self._engine.get_performance_ranking(top_n=20)
        except Exception:
            return
        self._rank_table.setRowCount(0)
        for rec in ranking:
            row = self._rank_table.rowCount()
            self._rank_table.insertRow(row)
            rating = rec.get("rating", "unknown")
            rc     = _RATING_COLORS.get(rating, _MUT)
            sharpe = rec.get("sharpe", 0.0)
            sh_c   = _GRN if sharpe >= 1.0 else (_RED if sharpe < 0 else _MUT)
            items  = [
                rec.get("strategy_id", ""),
                f"{sharpe:.3f}",
                f"{rec.get('max_drawdown', 0.0):.2%}",
                f"{rec.get('win_rate', 0.0):.1%}",
                rating.upper(),
                str(rec.get("sample_count", 0)),
            ]
            colors = [_FG, sh_c, _MUT, _MUT, rc, _MUT]
            for col, (text, color) in enumerate(zip(items, colors)):
                item = QtWidgets.QTableWidgetItem(text)
                item.setTextAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
                item.setForeground(QtGui.QColor(color))
                self._rank_table.setItem(row, col, item)

    def _refresh_detail(self, strategy_id):
        try:
            state = self._engine.get_performance_state(strategy_id)
        except Exception:
            return
        self._update_kpi(state)
        self._update_multiperiod(state)
        self._update_detail_table(state)
        self._status_lbl.setText(f"Strategy: {strategy_id}")

    def _update_kpi(self, state):
        sh   = state.sharpe
        sh_c = _GRN if sh >= 1.0 else (_RED if sh < 0 else _MUT)
        self._sharpe_blk._vl.setText(f"{sh:.3f}")
        self._sharpe_blk._vl.setStyleSheet(
            f"color: {sh_c}; font-size: 18px; font-weight: bold; border: none;")
        self._sortino_blk._vl.setText(
            f"{state.sortino:.3f}" if state.sortino < 900 else ">900")
        self._calmar_blk._vl.setText(f"{state.calmar:.3f}")
        dd   = state.max_drawdown
        dd_c = _RED if dd > 0.2 else (_YLW if dd > 0.1 else _GRN)
        self._dd_blk._vl.setText(f"{dd:.2%}")
        self._dd_blk._vl.setStyleSheet(
            f"color: {dd_c}; font-size: 14px; font-weight: bold; border: none;")
        self._wr_blk._vl.setText(f"{state.win_rate:.1%}")
        self._ann_blk._vl.setText(f"{state.ann_return:.2%}")
        rating = state.rating.value
        rc = _RATING_COLORS.get(rating, _MUT)
        self._rating_blk._vl.setText(rating.upper())
        self._rating_blk._vl.setStyleSheet(
            f"color: {rc}; font-size: 14px; font-weight: bold; border: none;")

    def _update_multiperiod(self, state):
        mp = state.multi_period
        for row, key in enumerate(["daily", "weekly", "monthly"]):
            data = mp.get(key, {})
            vals = [
                key.capitalize(),
                f"{data.get('sharpe', 0.0):.3f}",
                f"{data.get('max_drawdown', 0.0):.2%}",
                f"{data.get('win_rate', 0.0):.1%}",
                f"{data.get('ann_return', 0.0):.2%}",
            ]
            for col, text in enumerate(vals):
                item = QtWidgets.QTableWidgetItem(text)
                item.setTextAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
                self._period_table.setItem(row, col, item)

    def _update_detail_table(self, state):
        rows = [
            ("Strategy ID",   state.strategy_id),
            ("Sharpe",        f"{state.sharpe:.4f}"),
            ("Sortino",       f"{state.sortino:.4f}"),
            ("Calmar",        f"{state.calmar:.4f}"),
            ("Max Drawdown",  f"{state.max_drawdown:.4f}"),
            ("Win Rate",      f"{state.win_rate:.4f}"),
            ("Profit Factor", f"{state.profit_factor:.4f}"),
            ("Ann Return",    f"{state.ann_return:.4f}"),
            ("Cum Return",    f"{state.cum_return:.4f}"),
            ("Turnover",      f"{state.turnover:.4f}"),
            ("Trade Count",   str(state.trade_count)),
            ("Sample Count",  str(state.sample_count)),
            ("Rating",        state.rating.value),
            ("Updated At",    str(state.updated_at)[:19]),
        ]
        self._detail_table.setRowCount(len(rows))
        for i, (k, v) in enumerate(rows):
            ki = QtWidgets.QTableWidgetItem(k)
            vi = QtWidgets.QTableWidgetItem(v)
            ki.setTextAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
            vi.setTextAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
            self._detail_table.setItem(i, 0, ki)
            self._detail_table.setItem(i, 1, vi)

    def _on_strategy_changed(self, strategy_id):
        if strategy_id:
            self._current_strategy = strategy_id
            self._refresh_detail(strategy_id)

    def _on_rank_clicked(self, row, _col):
        item = self._rank_table.item(row, 0)
        if item:
            sid = item.text()
            self._strategy_combo.setCurrentText(sid)
            self._refresh_detail(sid)

    def update_from_event(self, data):
        sid = data.get("strategy_id", "")
        if not sid:
            return
        try:
            state = self._engine.get_performance_state(sid)
            self._update_kpi(state)
            self._refresh_ranking()
        except Exception:
            pass
