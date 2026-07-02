"""
strategy_lifecycle_ai/ui/evolution_tab.py  (Phase 4)

EvolutionTab — 策略进化图谱面板（完整实现）。
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

_TYPE_COLORS = {
    "none":           _MUT,
    "param_mutation": _BLU,
    "weight_adjust":  _YLW,
    "recombination":  _ORG,
    "cloning":        _GRN,
}


class EvolutionTab(QtWidgets.QWidget):
    """策略进化图谱面板（Phase 4 完整实现）。"""

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
        mid.addWidget(self._build_candidate_panel(), stretch=1)
        mid.addWidget(self._build_history_panel(),   stretch=1)
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
        self._total_blk   = self._kpi("Total Evolutions", "0",   _MAV, big=True)
        self._success_blk = self._kpi("Success Rate",     "---", _MUT)
        self._improve_blk = self._kpi("Avg Improvement",  "---", _MUT)
        self._cand_blk    = self._kpi("Candidates",       "0",   _MUT)
        self._strong_blk  = self._kpi("Strong Peers",     "0",   _GRN)
        for w in [self._total_blk, self._success_blk, self._improve_blk,
                  self._cand_blk, self._strong_blk]:
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

    def _build_candidate_panel(self):
        panel = QtWidgets.QWidget()
        panel.setStyleSheet(
            f"background: {_PANEL}; border-radius: 8px; border: 1px solid {_BORDER};")
        v = QtWidgets.QVBoxLayout(panel)
        v.setContentsMargins(14, 12, 14, 12)
        v.setSpacing(8)
        t = QtWidgets.QLabel("Evolution Candidates  进化候选")
        t.setStyleSheet(
            f"color: {_MAV}; font-size: 11px; font-weight: bold; border: none;")
        v.addWidget(t); v.addWidget(self._sep())
        self._cand_table = QtWidgets.QTableWidget(0, 6)
        self._cand_table.setHorizontalHeaderLabels(
            ["策略 ID", "Evo Score", "Sharpe", "Decay", "天数", "建议类型"])
        self._cand_table.horizontalHeader().setSectionResizeMode(
            QtWidgets.QHeaderView.ResizeMode.Stretch)
        self._cand_table.setEditTriggers(
            QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
        self._cand_table.setSelectionBehavior(
            QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
        self._cand_table.verticalHeader().setVisible(False)
        self._cand_table.setAlternatingRowColors(True)
        self._cand_table.setStyleSheet(
            f"QTableWidget {{ background:#11111b; color:{_FG}; border:1px solid {_BORDER}; gridline-color:{_BORDER}; font-size:11px; }}"
            f"QHeaderView::section {{ background:#313244; color:{_MUT}; padding:4px; border:none; font-size:10px; }}"
            f"QTableWidget::item:alternate {{ background:#181825; }}"
        )
        self._cand_table.cellClicked.connect(self._on_cand_clicked)
        v.addWidget(self._cand_table, stretch=1)
        return panel

    def _build_history_panel(self):
        panel = QtWidgets.QWidget()
        panel.setStyleSheet(
            f"background: {_PANEL}; border-radius: 8px; border: 1px solid {_BORDER};")
        v = QtWidgets.QVBoxLayout(panel)
        v.setContentsMargins(14, 12, 14, 12)
        v.setSpacing(8)
        t1 = QtWidgets.QLabel("Evolution History  进化历史")
        t1.setStyleSheet(
            f"color: {_MAV}; font-size: 11px; font-weight: bold; border: none;")
        v.addWidget(t1); v.addWidget(self._sep())
        self._hist_table = QtWidgets.QTableWidget(0, 7)
        self._hist_table.setHorizontalHeaderLabels(
            ["ID", "类型", "Sh前", "Sh后", "改善", "成功", "时间"])
        self._hist_table.horizontalHeader().setSectionResizeMode(
            QtWidgets.QHeaderView.ResizeMode.Stretch)
        self._hist_table.setEditTriggers(
            QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
        self._hist_table.verticalHeader().setVisible(False)
        self._hist_table.setFixedHeight(200)
        self._hist_table.setStyleSheet(
            f"QTableWidget {{ background:#11111b; color:{_FG}; border:1px solid {_BORDER}; gridline-color:{_BORDER}; font-size:11px; }}"
            f"QHeaderView::section {{ background:#313244; color:{_MUT}; padding:4px; border:none; font-size:10px; }}"
        )
        v.addWidget(self._hist_table)
        t2 = QtWidgets.QLabel("Params Diff  参数变化")
        t2.setStyleSheet(
            f"color: {_MAV}; font-size: 11px; font-weight: bold; border: none;")
        v.addWidget(t2); v.addWidget(self._sep())
        self._params_table = QtWidgets.QTableWidget(0, 3)
        self._params_table.setHorizontalHeaderLabels(["参数", "进化前", "进化后"])
        self._params_table.horizontalHeader().setSectionResizeMode(
            QtWidgets.QHeaderView.ResizeMode.Stretch)
        self._params_table.setEditTriggers(
            QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
        self._params_table.verticalHeader().setVisible(False)
        self._params_table.setStyleSheet(
            f"QTableWidget {{ background:#11111b; color:{_FG}; border:1px solid {_BORDER}; gridline-color:{_BORDER}; font-size:11px; }}"
            f"QHeaderView::section {{ background:#313244; color:{_MUT}; padding:4px; border:none; font-size:10px; }}"
        )
        v.addWidget(self._params_table, stretch=1)
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
            f"QComboBox {{ background:#11111b; color:{_FG}; "
            f"border:1px solid {_BORDER}; border-radius:4px; "
            f"padding:4px 8px; font-size:11px; }}"
            f"QComboBox::drop-down {{ border:none; }}"
            f"QComboBox QAbstractItemView {{ background:#11111b; "
            f"color:{_FG}; border:1px solid {_BORDER}; }}"
        )
        self._strategy_combo.currentTextChanged.connect(self._on_strategy_changed)
        h.addWidget(self._strategy_combo)
        btn_r = self._btn("Refresh  刷新", _MUT)
        btn_r.clicked.connect(self.refresh)
        btn_e = self._btn("Evolve  触发进化", _MAV)
        btn_e.clicked.connect(self._on_manual_evolve)
        h.addWidget(btn_r); h.addWidget(btn_e)
        h.addStretch()
        self._status_lbl = QtWidgets.QLabel("")
        self._status_lbl.setStyleSheet(f"color: {_MUT}; font-size: 11px;")
        h.addWidget(self._status_lbl)
        return bar

    def _btn(self, text, color):
        b = QtWidgets.QPushButton(text)
        b.setStyleSheet(
            f"QPushButton {{ background:transparent; color:{color}; "
            f"border:1px solid {color}; border-radius:4px; "
            f"padding:5px 16px; font-size:11px; }}"
            f"QPushButton:hover {{ background:{color}22; }}"
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
            sid = self._current_strategy or self._strategy_combo.currentText()
            if sid:
                self._refresh_history(sid)
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

    def _refresh_kpi(self):
        try:
            evo_summ = self._engine._evolution.summary()
            strong   = self._engine.get_strong_strategies()
            total = evo_summ.get("total_evolutions", 0)
            sr    = evo_summ.get("success_rate", 0.0)
            cands = evo_summ.get("candidates", 0)
            self._total_blk._vl.setText(str(total))
            sr_c = _GRN if sr >= 0.6 else (_YLW if sr >= 0.3 else _MUT)
            self._success_blk._vl.setText(f"{sr:.1%}")
            self._success_blk._vl.setStyleSheet(
                f"color:{sr_c}; font-size:14px; font-weight:bold; border:none;")
            self._cand_blk._vl.setText(str(cands))
            self._strong_blk._vl.setText(str(len(strong)))
            self._strong_blk._vl.setStyleSheet(
                f"color:{_GRN if strong else _MUT}; font-size:14px; font-weight:bold; border:none;")
            all_imp = []
            for hist in self._engine._evolution.get_all_histories():
                all_imp.extend(hist.get_improvement_series())
            if all_imp:
                avg_imp = sum(all_imp) / len(all_imp)
                imp_c = _GRN if avg_imp > 0 else _RED
                self._improve_blk._vl.setText(f"{avg_imp:+.4f}")
                self._improve_blk._vl.setStyleSheet(
                    f"color:{imp_c}; font-size:14px; font-weight:bold; border:none;")
        except Exception:
            pass

    def _refresh_candidates(self):
        try:
            candidates = self._engine.get_evolution_candidates(top_n=20)
        except Exception:
            return
        self._cand_table.setRowCount(0)
        from vnpy.strategy_lifecycle_ai.utils.evolution_utils import select_evolution_type
        for c in candidates:
            row = self._cand_table.rowCount()
            self._cand_table.insertRow(row)
            etype = select_evolution_type(
                c.get("sharpe", 0), c.get("decay_score", 0), c.get("live_days", 0))
            tc   = _TYPE_COLORS.get(etype.value, _MUT)
            sc   = c.get("evo_score", 0)
            sc_c = _GRN if sc > 0.6 else (_YLW if sc > 0.3 else _MUT)
            items = [
                c.get("strategy_id", ""),
                f"{sc:.3f}",
                f"{c.get('sharpe', 0):.3f}",
                f"{c.get('decay_score', 0):.3f}",
                str(c.get("live_days", 0)),
                etype.value.replace("_", " ").upper(),
            ]
            colors = [_FG, sc_c, _MUT, _MUT, _MUT, tc]
            for col, (text, color) in enumerate(zip(items, colors)):
                item = QtWidgets.QTableWidgetItem(text)
                item.setTextAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
                item.setForeground(QtGui.QColor(color))
                self._cand_table.setItem(row, col, item)

    def _refresh_history(self, strategy_id):
        try:
            history = self._engine.get_evolution_history(strategy_id, limit=20)
        except Exception:
            return
        self._hist_table.setRowCount(0)
        for rec in reversed(history):
            row = self._hist_table.rowCount()
            self._hist_table.insertRow(row)
            etype   = rec.get("evolution_type", "none")
            tc      = _TYPE_COLORS.get(etype, _MUT)
            success = rec.get("success", False)
            imp     = rec.get("improvement", 0.0)
            imp_c   = _GRN if imp > 0 else (_RED if imp < 0 else _MUT)
            items = [
                rec.get("evolution_id", "")[-8:],
                etype.replace("_", " ").upper(),
                f"{rec.get('sharpe_before', 0):.3f}",
                f"{rec.get('sharpe_after', 0):.3f}",
                f"{imp:+.4f}",
                "OK" if success else "--",
                rec.get("evolved_at", "")[:10],
            ]
            colors = [_MUT, tc, _MUT, _MUT, imp_c, _GRN if success else _MUT, _MUT]
            for col, (text, color) in enumerate(zip(items, colors)):
                item = QtWidgets.QTableWidgetItem(text)
                item.setTextAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
                item.setForeground(QtGui.QColor(color))
                self._hist_table.setItem(row, col, item)
        if history:
            self._show_params_diff(history[-1])
        self._status_lbl.setText(f"Strategy: {strategy_id}")

    def _show_params_diff(self, rec):
        before   = rec.get("params_before", {})
        after    = rec.get("params_after",  {})
        all_keys = sorted(set(list(before.keys()) + list(after.keys())))
        self._params_table.setRowCount(len(all_keys))
        for i, k in enumerate(all_keys):
            v_b = before.get(k, "—"); v_a = after.get(k, "—")
            changed = str(v_b) != str(v_a)
            ki = QtWidgets.QTableWidgetItem(k)
            bi = QtWidgets.QTableWidgetItem(str(v_b))
            ai = QtWidgets.QTableWidgetItem(str(v_a))
            for item in [ki, bi, ai]:
                item.setTextAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
            if changed:
                ai.setForeground(QtGui.QColor(_GRN))
                bi.setForeground(QtGui.QColor(_MUT))
            self._params_table.setItem(i, 0, ki)
            self._params_table.setItem(i, 1, bi)
            self._params_table.setItem(i, 2, ai)

    def _on_strategy_changed(self, sid):
        if sid:
            self._current_strategy = sid
            self._refresh_history(sid)

    def _on_cand_clicked(self, row, _col):
        item = self._cand_table.item(row, 0)
        if item:
            sid = item.text()
            self._strategy_combo.setCurrentText(sid)
            self._refresh_history(sid)

    def _on_manual_evolve(self):
        sid = self._strategy_combo.currentText()
        if not sid or self._engine is None:
            return
        try:
            record = self._engine.evolve_strategy(
                sid, params={}, trigger_reason="manual_ui")
            self._status_lbl.setText(
                f"Evolved {sid}  type={record.evolution_type.value}")
            self.refresh()
        except Exception as e:
            self._status_lbl.setText(f"Error: {e}")

    def update_from_event(self, data):
        self._refresh_kpi()
        sid = data.get("strategy_id", "")
        if sid:
            self._refresh_history(sid)
