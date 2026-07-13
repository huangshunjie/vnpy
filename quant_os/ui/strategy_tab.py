"""
quant_os/ui/strategy_tab.py

StrategyTab — 策略调度流视图（Phase 4）。
"""

from __future__ import annotations

from vnpy.trader.ui import QtCore, QtWidgets

from ..model.strategy_model import TriggerStatus, TriggerType, FlowStage

_PANEL_BG = "#181825"
_BORDER   = "#45475a"
_FG       = "#cdd6f4"
_MUT      = "#6c7086"
_GRN      = "#a6e3a1"
_YLW      = "#f9e2af"
_RED      = "#f38ba8"
_BLU      = "#89b4fa"
_ORG      = "#fab387"

_STATUS_COLOR = {
    TriggerStatus.PENDING.value:   _MUT,
    TriggerStatus.RUNNING.value:   _BLU,
    TriggerStatus.COMPLETED.value: _GRN,
    TriggerStatus.FAILED.value:    _RED,
    TriggerStatus.SKIPPED.value:   _ORG,
}

_RULE_COLS = [
    ("规则名称", 160), ("触发类型", 110), ("来源模块", 110),
    ("目标模块", 160), ("状态",      60),
]
_HIST_COLS = [
    ("Record ID", 90), ("规则名称", 130), ("触发类型", 100),
    ("状态",       70), ("耗时(ms)",  70), ("完成阶段", 200), ("错误", 140),
]


def _item(text: str, color: str = _FG) -> QtWidgets.QTableWidgetItem:
    from vnpy.trader.ui import QtGui
    it = QtWidgets.QTableWidgetItem(str(text))
    it.setTextAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
    it.setForeground(QtGui.QColor(color))
    return it


def _item_left(text: str, color: str = _FG) -> QtWidgets.QTableWidgetItem:
    from vnpy.trader.ui import QtGui
    it = QtWidgets.QTableWidgetItem(str(text))
    it.setTextAlignment(
        QtCore.Qt.AlignmentFlag.AlignLeft | QtCore.Qt.AlignmentFlag.AlignVCenter
    )
    it.setForeground(QtGui.QColor(color))
    return it


class StrategyTab(QtWidgets.QWidget):
    """策略调度流视图（Phase 4）。"""

    def __init__(self, os_engine=None, parent=None) -> None:
        super().__init__(parent)
        self._os_engine = os_engine
        self._init_ui()

    def set_os_engine(self, os_engine) -> None:
        self._os_engine = os_engine

    def _init_ui(self) -> None:
        root = QtWidgets.QVBoxLayout(self)
        root.setContentsMargins(6, 6, 6, 6)
        root.setSpacing(6)
        root.addWidget(self._build_kpi_bar())
        root.addWidget(self._build_pipeline_bar())
        sp = QtWidgets.QSplitter(QtCore.Qt.Orientation.Horizontal)
        sp.addWidget(self._build_rule_panel())
        sp.addWidget(self._build_history_panel())
        sp.setSizes([460, 700])
        root.addWidget(sp, stretch=1)
        root.addWidget(self._build_action_bar())

    def _build_kpi_bar(self) -> QtWidgets.QWidget:
        bar = QtWidgets.QWidget()
        bar.setFixedHeight(66)
        bar.setStyleSheet(f"background: {_PANEL_BG}; border-radius: 4px;")
        h = QtWidgets.QHBoxLayout(bar)
        h.setContentsMargins(16, 6, 16, 6)
        h.setSpacing(24)
        kpis = [
            ("触发规则数", "0", _FG),
            ("总触发次数", "0", _FG),
            ("成功",       "0", _GRN),
            ("失败",       "0", _RED),
            ("成功率",     "---", _BLU),
            ("已调度策略", "0", _YLW),
        ]
        self._kpi: dict[str, QtWidgets.QLabel] = {}
        for name, val, color in kpis:
            col = QtWidgets.QVBoxLayout()
            col.setSpacing(1)
            ln = QtWidgets.QLabel(name)
            ln.setStyleSheet(f"color: {_MUT}; font-size: 10px;")
            ln.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
            lv = QtWidgets.QLabel(val)
            lv.setStyleSheet(f"color: {color}; font-size: 14px; font-weight: bold;")
            lv.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
            col.addWidget(ln)
            col.addWidget(lv)
            self._kpi[name] = lv
            h.addLayout(col)
        h.addStretch()
        return bar

    def _build_pipeline_bar(self) -> QtWidgets.QWidget:
        bar = QtWidgets.QWidget()
        bar.setFixedHeight(38)
        bar.setStyleSheet(f"background: {_PANEL_BG}; border-radius: 4px;")
        h = QtWidgets.QHBoxLayout(bar)
        h.setContentsMargins(16, 4, 16, 4)
        stages = [
            ("Factor", _BLU), ("Strategy", _GRN), ("Portfolio", _YLW),
            ("Execution", _ORG), ("Risk", _RED), ("Feedback", _MUT),
        ]
        def lbl(t, c):
            l = QtWidgets.QLabel(t)
            l.setStyleSheet(f"color: {c}; font-size: 11px; font-weight: bold;")
            return l
        h.addWidget(lbl("调度链路 Dispatch Pipeline: ", _MUT))
        for i, (name, color) in enumerate(stages):
            h.addWidget(lbl(name, color))
            if i < len(stages) - 1:
                h.addWidget(lbl("  ->  ", _BORDER))
        h.addStretch()
        return bar

    def _build_rule_panel(self) -> QtWidgets.QWidget:
        w = QtWidgets.QWidget()
        w.setStyleSheet(f"background: {_PANEL_BG}; border-radius: 4px;")
        v = QtWidgets.QVBoxLayout(w)
        v.setContentsMargins(8, 6, 8, 6)
        v.setSpacing(3)
        lbl = QtWidgets.QLabel("触发规则 Trigger Rules")
        lbl.setStyleSheet(f"color: {_MUT}; font-size: 10px;")
        v.addWidget(lbl)
        self._tbl_rule = QtWidgets.QTableWidget(0, len(_RULE_COLS))
        self._tbl_rule.setHorizontalHeaderLabels([c[0] for c in _RULE_COLS])
        for i, (_, w_) in enumerate(_RULE_COLS):
            self._tbl_rule.setColumnWidth(i, w_)
        self._tbl_rule.horizontalHeader().setStretchLastSection(True)
        self._tbl_rule.verticalHeader().setVisible(False)
        self._tbl_rule.setEditTriggers(
            QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
        self._tbl_rule.setSelectionBehavior(
            QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
        self._tbl_rule.setStyleSheet("font-size: 12px;")
        v.addWidget(self._tbl_rule, stretch=1)
        return w

    def _build_history_panel(self) -> QtWidgets.QWidget:
        w = QtWidgets.QWidget()
        w.setStyleSheet(f"background: {_PANEL_BG}; border-radius: 4px;")
        v = QtWidgets.QVBoxLayout(w)
        v.setContentsMargins(8, 6, 8, 6)
        v.setSpacing(3)
        lbl = QtWidgets.QLabel("触发历史 Trigger History (last 100)")
        lbl.setStyleSheet(f"color: {_MUT}; font-size: 10px;")
        v.addWidget(lbl)
        self._tbl_hist = QtWidgets.QTableWidget(0, len(_HIST_COLS))
        self._tbl_hist.setHorizontalHeaderLabels([c[0] for c in _HIST_COLS])
        for i, (_, w_) in enumerate(_HIST_COLS):
            self._tbl_hist.setColumnWidth(i, w_)
        self._tbl_hist.horizontalHeader().setStretchLastSection(True)
        self._tbl_hist.verticalHeader().setVisible(False)
        self._tbl_hist.setEditTriggers(
            QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
        self._tbl_hist.setStyleSheet("font-size: 12px;")
        v.addWidget(self._tbl_hist, stretch=1)
        return w

    def _build_action_bar(self) -> QtWidgets.QWidget:
        bar = QtWidgets.QWidget()
        bar.setFixedHeight(46)
        bar.setStyleSheet(f"background: {_PANEL_BG}; border-radius: 4px;")
        h = QtWidgets.QHBoxLayout(bar)
        h.setContentsMargins(12, 6, 12, 6)
        h.setSpacing(8)
        def _btn(label, color, slot):
            b = QtWidgets.QPushButton(label)
            b.setStyleSheet(
                f"QPushButton {{ background: transparent; color: {color};"
                f" border: 1px solid {color}; border-radius: 3px;"
                f" padding: 4px 12px; font-size: 12px; }}"
                f"QPushButton:hover {{ background: {color}22; }}"
            )
            b.clicked.connect(slot)
            return b
        h.addWidget(_btn("手动触发 Manual Trigger",  _GRN, self._on_manual_trigger))
        h.addWidget(_btn("启用规则 Enable Rule",     _BLU, self._on_enable_rule))
        h.addWidget(_btn("禁用规则 Disable Rule",    _YLW, self._on_disable_rule))
        h.addWidget(_btn("因子更新 Factor Update",   _ORG, self._on_factor_trigger))
        h.addStretch()
        btn_r = QtWidgets.QPushButton("刷新 Refresh")
        btn_r.setStyleSheet(
            f"QPushButton {{ background: transparent; color: {_MUT};"
            f" border: 1px solid {_BORDER}; border-radius: 3px;"
            f" padding: 4px 12px; font-size: 12px; }}"
            f"QPushButton:hover {{ background: {_BORDER}33; }}"
        )
        btn_r.clicked.connect(self.refresh)
        h.addWidget(btn_r)
        return bar

    # ------------------------------------------------------------------ #
    #  公开接口
    # ------------------------------------------------------------------ #

    def refresh(self) -> None:
        if self._os_engine is None:
            return
        orch = self._os_engine.orchestrator
        self._refresh_rules(orch.get_all_rules())
        self._refresh_history(orch.get_recent_records(100))
        self._refresh_kpi(orch)

    def on_trigger(self, event_type: str, data: dict) -> None:
        self.refresh()

    # ------------------------------------------------------------------ #
    #  按钮回调
    # ------------------------------------------------------------------ #

    def _selected_rule_id(self):
        row = self._tbl_rule.currentRow()
        if row < 0:
            return None
        it = self._tbl_rule.item(row, 0)
        return it.data(QtCore.Qt.ItemDataRole.UserRole) if it else None

    def _on_manual_trigger(self) -> None:
        rule_id = self._selected_rule_id()
        if rule_id and self._os_engine:
            self._os_engine.trigger(rule_id, payload={"source": "manual"})
            self.refresh()

    def _on_enable_rule(self) -> None:
        rule_id = self._selected_rule_id()
        if rule_id and self._os_engine:
            self._os_engine.orchestrator.enable_rule(rule_id)
            self.refresh()

    def _on_disable_rule(self) -> None:
        rule_id = self._selected_rule_id()
        if rule_id and self._os_engine:
            self._os_engine.orchestrator.disable_rule(rule_id)
            self.refresh()

    def _on_factor_trigger(self) -> None:
        if self._os_engine:
            self._os_engine.trigger_by_type(
                TriggerType.FACTOR_UPDATE,
                payload={"source": "manual_factor_update"},
            )
            self.refresh()

    # ------------------------------------------------------------------ #
    #  内部渲染
    # ------------------------------------------------------------------ #

    def _refresh_rules(self, rules) -> None:
        self._tbl_rule.setRowCount(0)
        for rule in rules:
            row = self._tbl_rule.rowCount()
            self._tbl_rule.insertRow(row)
            en_color = _GRN if rule.enabled else _MUT
            en_text  = "启用 ON" if rule.enabled else "禁用 OFF"
            targets  = ", ".join(rule.target_modules) if rule.target_modules else "---"
            it_name  = _item_left(rule.name, _FG)
            it_name.setData(QtCore.Qt.ItemDataRole.UserRole, rule.rule_id)
            self._tbl_rule.setItem(row, 0, it_name)
            self._tbl_rule.setItem(row, 1, _item(rule.trigger_type.value, _BLU))
            self._tbl_rule.setItem(row, 2, _item(rule.source_module or "---", _MUT))
            self._tbl_rule.setItem(row, 3, _item_left(targets, _MUT))
            self._tbl_rule.setItem(row, 4, _item(en_text, en_color))

    def _refresh_history(self, records) -> None:
        self._tbl_hist.setRowCount(0)
        for rec in reversed(records):
            row = self._tbl_hist.rowCount()
            self._tbl_hist.insertRow(row)
            st_color = _STATUS_COLOR.get(rec.status.value, _FG)
            stages   = " -> ".join(s.value for s in rec.stages_completed) or "---"
            rule     = (self._os_engine.orchestrator.get_rule(rec.rule_id)
                        if self._os_engine else None)
            rule_name = rule.name if rule else rec.rule_id
            self._tbl_hist.setItem(row, 0, _item(rec.record_id,             _MUT))
            self._tbl_hist.setItem(row, 1, _item_left(rule_name,            _FG))
            self._tbl_hist.setItem(row, 2, _item(rec.trigger_type.value,    _BLU))
            self._tbl_hist.setItem(row, 3, _item(rec.status.value.upper(),  st_color))
            self._tbl_hist.setItem(row, 4, _item(f"{rec.elapsed_ms:.0f}",   _FG))
            self._tbl_hist.setItem(row, 5, _item_left(stages,               _MUT))
            self._tbl_hist.setItem(row, 6, _item_left(rec.error_msg or "---",
                _RED if rec.error_msg else _MUT))

    def _refresh_kpi(self, orch) -> None:
        summ = orch.summary()
        t    = summ["triggers"]
        sr   = f"{t['success_rate']:.1%}" if t["total"] else "---"
        scheduled = sum(
            1 for s in orch.get_all_strategy_records() if s.is_scheduled
        )
        self._kpi["触发规则数"].setText(str(summ["rules"]))
        self._kpi["总触发次数"].setText(str(t["total"]))
        self._kpi["成功"      ].setText(str(t["completed"]))
        self._kpi["失败"      ].setText(str(t["failed"]))
        self._kpi["成功率"    ].setText(sr)
        self._kpi["已调度策略"].setText(str(scheduled))
        fail_c = _RED if t["failed"] > 0 else _MUT
        self._kpi["失败"].setStyleSheet(
            f"color: {fail_c}; font-size: 14px; font-weight: bold;"
        )
