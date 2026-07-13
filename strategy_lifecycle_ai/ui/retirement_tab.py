"""
strategy_lifecycle_ai/ui/retirement_tab.py  (Phase 5)

RetirementTab — 策略退役管理面板（完整实现）。
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

_REASON_COLORS = {
    "manual":           _MUT,
    "persistent_decay": _ORG,
    "negative_sharpe":  _RED,
    "drawdown_breach":  _RED,
    "low_activity":     _YLW,
}


class RetirementTab(QtWidgets.QWidget):
    """策略退役管理面板（Phase 5 完整实现）。"""

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
        mid.addWidget(self._build_candidates_panel(), stretch=1)
        mid.addWidget(self._build_history_panel(),    stretch=1)
        root.addLayout(mid)
        root.addWidget(self._build_action_bar())

    def _build_kpi_row(self):
        row = QtWidgets.QWidget()
        row.setFixedHeight(90)
        row.setStyleSheet(
            f"background:{_PANEL}; border-radius:8px; border:1px solid {_BORDER};")
        h = QtWidgets.QHBoxLayout(row)
        h.setContentsMargins(20, 10, 20, 10)
        h.setSpacing(32)
        self._retired_blk  = self._kpi("Retired",    "0", _RED, big=True)
        self._archived_blk = self._kpi("Archived",   "0", _MUT)
        self._cand_blk     = self._kpi("Candidates", "0", _YLW)
        self._decay_blk    = self._kpi("By Decay",   "0", _ORG)
        self._sharpe_blk   = self._kpi("By Sharpe",  "0", _RED)
        self._dd_blk       = self._kpi("By DD",      "0", _RED)
        for w in [self._retired_blk, self._archived_blk, self._cand_blk,
                  self._decay_blk, self._sharpe_blk, self._dd_blk]:
            h.addWidget(w)
        h.addStretch()
        return row

    def _kpi(self, title, value, color, big=False):
        w = QtWidgets.QWidget()
        w.setStyleSheet("border:none; background:transparent;")
        v = QtWidgets.QVBoxLayout(w)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(2)
        tl = QtWidgets.QLabel(title)
        tl.setStyleSheet(f"color:{_MUT}; font-size:9px; border:none;")
        vl = QtWidgets.QLabel(value)
        vl.setStyleSheet(
            f"color:{color}; font-size:{'18px' if big else '14px'};"
            f" font-weight:bold; border:none;")
        v.addWidget(tl); v.addWidget(vl)
        w._vl = vl
        return w

    def _build_candidates_panel(self):
        panel = QtWidgets.QWidget()
        panel.setStyleSheet(
            f"background:{_PANEL}; border-radius:8px; border:1px solid {_BORDER};")
        v = QtWidgets.QVBoxLayout(panel)
        v.setContentsMargins(14, 12, 14, 12)
        v.setSpacing(8)
        t = QtWidgets.QLabel("Retirement Candidates  退役候选")
        t.setStyleSheet(
            f"color:{_MAV}; font-size:11px; font-weight:bold; border:none;")
        v.addWidget(t); v.addWidget(self._sep())
        self._cand_table = QtWidgets.QTableWidget(0, 5)
        self._cand_table.setHorizontalHeaderLabels(
            ["策略 ID", "触发原因", "Sharpe", "DD", "衰减天"])
        self._cand_table.horizontalHeader().setSectionResizeMode(
            QtWidgets.QHeaderView.ResizeMode.Stretch)
        self._cand_table.setEditTriggers(
            QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
        self._cand_table.setSelectionBehavior(
            QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
        self._cand_table.verticalHeader().setVisible(False)
        self._cand_table.setAlternatingRowColors(True)
        self._cand_table.setStyleSheet(
            f"QTableWidget {{background:#11111b;color:{_FG};border:1px solid {_BORDER};"
            f"gridline-color:{_BORDER};font-size:11px;}}"
            f"QHeaderView::section {{background:#313244;color:{_MUT};"
            f"padding:4px;border:none;font-size:10px;}}"
            f"QTableWidget::item:alternate {{background:#181825;}}"
        )
        v.addWidget(self._cand_table, stretch=1)
        return panel

    def _build_history_panel(self):
        panel = QtWidgets.QWidget()
        panel.setStyleSheet(
            f"background:{_PANEL}; border-radius:8px; border:1px solid {_BORDER};")
        v = QtWidgets.QVBoxLayout(panel)
        v.setContentsMargins(14, 12, 14, 12)
        v.setSpacing(8)
        t = QtWidgets.QLabel("Retirement History  退役历史")
        t.setStyleSheet(
            f"color:{_MAV}; font-size:11px; font-weight:bold; border:none;")
        v.addWidget(t); v.addWidget(self._sep())
        self._hist_table = QtWidgets.QTableWidget(0, 6)
        self._hist_table.setHorizontalHeaderLabels(
            ["策略 ID", "原因", "Sharpe", "DD", "衰减天", "归档"])
        self._hist_table.horizontalHeader().setSectionResizeMode(
            QtWidgets.QHeaderView.ResizeMode.Stretch)
        self._hist_table.setEditTriggers(
            QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
        self._hist_table.verticalHeader().setVisible(False)
        self._hist_table.setAlternatingRowColors(True)
        self._hist_table.setStyleSheet(
            f"QTableWidget {{background:#11111b;color:{_FG};border:1px solid {_BORDER};"
            f"gridline-color:{_BORDER};font-size:11px;}}"
            f"QHeaderView::section {{background:#313244;color:{_MUT};"
            f"padding:4px;border:none;font-size:10px;}}"
            f"QTableWidget::item:alternate {{background:#181825;}}"
        )
        v.addWidget(self._hist_table, stretch=1)
        return panel

    def _build_action_bar(self):
        bar = QtWidgets.QWidget()
        bar.setFixedHeight(44)
        h = QtWidgets.QHBoxLayout(bar)
        h.setContentsMargins(0, 0, 0, 0)
        h.setSpacing(8)
        h.addWidget(QtWidgets.QLabel("Strategy:"))
        self._strategy_combo = QtWidgets.QComboBox()
        self._strategy_combo.setMinimumWidth(180)
        self._strategy_combo.setStyleSheet(
            f"QComboBox {{background:#11111b;color:{_FG};"
            f"border:1px solid {_BORDER};border-radius:4px;"
            f"padding:4px 8px;font-size:11px;}}"
            f"QComboBox::drop-down {{border:none;}}"
            f"QComboBox QAbstractItemView {{background:#11111b;"
            f"color:{_FG};border:1px solid {_BORDER};}}"
        )
        h.addWidget(self._strategy_combo)
        for text, color, slot in [
            ("Refresh  刷新",  _MUT, self.refresh),
            ("Retire  退役",   _RED, self._on_manual_retire),
            ("Restore  恢复",  _GRN, self._on_restore),
            ("Archive  归档",  _MUT, self._on_archive),
        ]:
            btn = self._btn(text, color)
            btn.clicked.connect(slot)
            h.addWidget(btn)
        h.addStretch()
        self._status_lbl = QtWidgets.QLabel("")
        self._status_lbl.setStyleSheet(f"color:{_MUT}; font-size:11px;")
        h.addWidget(self._status_lbl)
        return bar

    def _btn(self, text, color):
        b = QtWidgets.QPushButton(text)
        b.setStyleSheet(
            f"QPushButton {{background:transparent;color:{color};"
            f"border:1px solid {color};border-radius:4px;"
            f"padding:5px 14px;font-size:11px;}}"
            f"QPushButton:hover {{background:{color}22;}}"
        )
        return b

    def _sep(self):
        s = QtWidgets.QFrame()
        s.setFrameShape(QtWidgets.QFrame.Shape.HLine)
        s.setStyleSheet(f"border:none; border-top:1px solid {_BORDER};")
        return s

    def refresh(self):
        if self._engine is None:
            return
        try:
            self._refresh_strategy_list()
            self._refresh_kpi()
            self._refresh_candidates()
            self._refresh_history()
        except Exception as e:
            self._status_lbl.setText(f"Error: {e}")

    def _refresh_strategy_list(self):
        try:
            strategies = self._engine.get_all_strategies()
            combo = self._strategy_combo
            current = combo.currentText()
            combo.blockSignals(True); combo.clear()
            for s in strategies:
                combo.addItem(s.strategy_id)
            if current in [s.strategy_id for s in strategies]:
                combo.setCurrentText(current)
            elif strategies:
                combo.setCurrentIndex(0)
            combo.blockSignals(False)
        except Exception:
            pass

    def _refresh_kpi(self):
        try:
            ret_list = self._engine.get_retired_strategies()
            arc_list = self._engine.get_archived_strategies()
            cands    = self._engine.auto_screen_retirement()
            by_r     = self._engine._retirement.count_by_reason()
            self._retired_blk._vl.setText(str(len(ret_list)))
            self._archived_blk._vl.setText(str(len(arc_list)))
            self._cand_blk._vl.setText(str(len(cands)))
            self._decay_blk._vl.setText(str(by_r.get("persistent_decay", 0)))
            self._sharpe_blk._vl.setText(str(by_r.get("negative_sharpe", 0)))
            self._dd_blk._vl.setText(str(by_r.get("drawdown_breach", 0)))
        except Exception:
            pass

    def _refresh_candidates(self):
        try:
            cands = self._engine.auto_screen_retirement()
        except Exception:
            return
        self._cand_table.setRowCount(0)
        for ev in cands:
            row = self._cand_table.rowCount()
            self._cand_table.insertRow(row)
            reason = ev.primary_reason.value
            rc = _REASON_COLORS.get(reason, _MUT)
            items = [
                ev.strategy_id,
                reason.replace("_", " ").upper(),
                f"{ev.sharpe:.3f}",
                f"{ev.max_drawdown:.2%}",
                str(ev.decay_days),
            ]
            colors = [_FG, rc, _MUT, _MUT, _MUT]
            for col, (text, color) in enumerate(zip(items, colors)):
                item = QtWidgets.QTableWidgetItem(text)
                item.setTextAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
                item.setForeground(QtGui.QColor(color))
                self._cand_table.setItem(row, col, item)

    def _refresh_history(self):
        try:
            history = self._engine.get_retirement_history(limit=30)
        except Exception:
            return
        self._hist_table.setRowCount(0)
        for rec in reversed(history):
            row = self._hist_table.rowCount()
            self._hist_table.insertRow(row)
            reason = rec.get("reason", "manual")
            rc     = _REASON_COLORS.get(reason, _MUT)
            arch   = rec.get("archived", False)
            items  = [
                rec.get("strategy_id", ""),
                reason.replace("_", " ").upper(),
                f"{rec.get('sharpe_at_exit', 0):.3f}",
                f"{rec.get('drawdown_at_exit', 0):.2%}",
                str(rec.get("decay_days", 0)),
                "YES" if arch else "no",
            ]
            colors = [_FG, rc, _MUT, _MUT, _MUT, _GRN if arch else _MUT]
            for col, (text, color) in enumerate(zip(items, colors)):
                item = QtWidgets.QTableWidgetItem(text)
                item.setTextAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
                item.setForeground(QtGui.QColor(color))
                self._hist_table.setItem(row, col, item)

    def _on_manual_retire(self):
        sid = self._strategy_combo.currentText()
        if not sid or self._engine is None:
            return
        try:
            record = self._engine.execute_retirement(sid, "manual", "manual_ui")
            self._status_lbl.setText(f"Retired: {sid}" if record else f"Failed: {sid}")
            self.refresh()
        except Exception as e:
            self._status_lbl.setText(f"Error: {e}")

    def _on_restore(self):
        sid = self._strategy_combo.currentText()
        if not sid or self._engine is None:
            return
        try:
            ok = self._engine.restore_strategy(sid)
            self._status_lbl.setText(f"Restored: {sid}" if ok else f"{sid} not retired")
            self.refresh()
        except Exception as e:
            self._status_lbl.setText(f"Error: {e}")

    def _on_archive(self):
        sid = self._strategy_combo.currentText()
        if not sid or self._engine is None:
            return
        try:
            record = self._engine.archive_strategy(sid)
            self._status_lbl.setText(f"Archived: {sid}" if record else f"{sid} not retired")
            self.refresh()
        except Exception as e:
            self._status_lbl.setText(f"Error: {e}")

    def update_from_event(self, data):
        self._refresh_kpi()
        self._refresh_history()
