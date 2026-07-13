"""
live_production/ui/recovery_tab.py

RecoveryTab — 恢复系统面板（Phase 3）。

布局：
  顶部：KPI 栏（恢复次数 / 成功率 / Checkpoint 数 / 当前阶段）
  中部：左侧 Checkpoint 列表 / 右侧恢复历史时间线
  底部：操作按钮栏
"""

from __future__ import annotations

from vnpy.trader.ui import QtCore, QtWidgets

from ..engine.recovery_engine import RecoveryPhase, RecoveryTrigger

_PANEL_BG = "#181825"
_BORDER   = "#45475a"
_FG       = "#cdd6f4"
_MUT      = "#6c7086"
_GRN      = "#a6e3a1"
_YLW      = "#f9e2af"
_RED      = "#f38ba8"
_BLU      = "#89b4fa"
_ORG      = "#fab387"

_PHASE_COLOR = {
    RecoveryPhase.IDLE.value:      _MUT,
    RecoveryPhase.PREPARING.value: _YLW,
    RecoveryPhase.RESTORING.value: _BLU,
    RecoveryPhase.VERIFYING.value: _ORG,
    RecoveryPhase.COMPLETED.value: _GRN,
    RecoveryPhase.FAILED.value:    _RED,
}

_CP_COLS = [
    ("文件名 Filename", 200),
    ("保存时间 Saved At", 150),
    ("大小 Size(KB)", 80),
]

_REC_COLS = [
    ("ID",         70),
    ("触发 Trigger", 110),
    ("阶段 Phase",   90),
    ("成功 OK",      50),
    ("耗时(s)",      60),
    ("订单数 Orders", 70),
    ("不一致 Diff",   70),
    ("开始时间",     140),
    ("错误 Error",   160),
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
        QtCore.Qt.AlignmentFlag.AlignLeft | QtCore.Qt.AlignmentFlag.AlignVCenter)
    it.setForeground(QtGui.QColor(color))
    return it


class RecoveryTab(QtWidgets.QWidget):
    """恢复系统面板（Phase 3）。"""

    def __init__(self, engine=None, parent=None) -> None:
        super().__init__(parent)
        self._engine = engine
        self._init_ui()

    def set_engine(self, engine) -> None:
        self._engine = engine

    # ------------------------------------------------------------------ #
    #  UI 构建
    # ------------------------------------------------------------------ #

    def _init_ui(self) -> None:
        root = QtWidgets.QVBoxLayout(self)
        root.setContentsMargins(6, 6, 6, 6)
        root.setSpacing(6)
        root.addWidget(self._build_kpi_bar())

        mid = QtWidgets.QSplitter(QtCore.Qt.Orientation.Horizontal)
        mid.addWidget(self._build_checkpoint_panel())
        mid.addWidget(self._build_history_panel())
        mid.setSizes([420, 760])
        root.addWidget(mid, stretch=1)

        root.addWidget(self._build_action_bar())

    def _build_kpi_bar(self) -> QtWidgets.QWidget:
        bar = QtWidgets.QWidget()
        bar.setFixedHeight(66)
        bar.setStyleSheet(f"background: {_PANEL_BG}; border-radius: 4px;")
        h = QtWidgets.QHBoxLayout(bar)
        h.setContentsMargins(16, 6, 16, 6)
        h.setSpacing(28)

        kpis = [
            ("当前阶段 Phase",     "IDLE",  _MUT),
            ("恢复总次数 Total",   "0",     _FG),
            ("成功次数 Success",   "0",     _GRN),
            ("失败次数 Failed",    "0",     _RED),
            ("成功率 Rate",        "---",   _BLU),
            ("Checkpoint 数量",    "0",     _YLW),
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

    def _build_checkpoint_panel(self) -> QtWidgets.QWidget:
        w = QtWidgets.QWidget()
        w.setStyleSheet(f"background: {_PANEL_BG}; border-radius: 4px;")
        v = QtWidgets.QVBoxLayout(w)
        v.setContentsMargins(8, 6, 8, 6)
        v.setSpacing(3)

        lbl = QtWidgets.QLabel("Checkpoint 列表")
        lbl.setStyleSheet(f"color: {_MUT}; font-size: 10px;")
        v.addWidget(lbl)

        self._tbl_cp = QtWidgets.QTableWidget(0, len(_CP_COLS))
        self._tbl_cp.setHorizontalHeaderLabels([c[0] for c in _CP_COLS])
        for i, (_, w_) in enumerate(_CP_COLS):
            self._tbl_cp.setColumnWidth(i, w_)
        self._tbl_cp.horizontalHeader().setStretchLastSection(True)
        self._tbl_cp.verticalHeader().setVisible(False)
        self._tbl_cp.setEditTriggers(
            QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
        self._tbl_cp.setSelectionBehavior(
            QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
        self._tbl_cp.setStyleSheet("font-size: 11px;")
        v.addWidget(self._tbl_cp, stretch=1)
        return w

    def _build_history_panel(self) -> QtWidgets.QWidget:
        w = QtWidgets.QWidget()
        w.setStyleSheet(f"background: {_PANEL_BG}; border-radius: 4px;")
        v = QtWidgets.QVBoxLayout(w)
        v.setContentsMargins(8, 6, 8, 6)
        v.setSpacing(3)

        lbl = QtWidgets.QLabel("恢复历史  Recovery History")
        lbl.setStyleSheet(f"color: {_MUT}; font-size: 10px;")
        v.addWidget(lbl)

        self._tbl_rec = QtWidgets.QTableWidget(0, len(_REC_COLS))
        self._tbl_rec.setHorizontalHeaderLabels([c[0] for c in _REC_COLS])
        for i, (_, w_) in enumerate(_REC_COLS):
            self._tbl_rec.setColumnWidth(i, w_)
        self._tbl_rec.horizontalHeader().setStretchLastSection(True)
        self._tbl_rec.verticalHeader().setVisible(False)
        self._tbl_rec.setEditTriggers(
            QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
        self._tbl_rec.setSelectionBehavior(
            QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
        self._tbl_rec.setStyleSheet("font-size: 11px;")
        v.addWidget(self._tbl_rec, stretch=1)

        # 步骤详情区
        lbl2 = QtWidgets.QLabel("步骤详情  Steps")
        lbl2.setStyleSheet(f"color: {_MUT}; font-size: 10px;")
        v.addWidget(lbl2)
        self._txt_steps = QtWidgets.QTextEdit()
        self._txt_steps.setReadOnly(True)
        self._txt_steps.setFixedHeight(100)
        self._txt_steps.setStyleSheet(
            f"QTextEdit {{ background: #11111b; color: {_FG};"
            f" font-size: 10px; font-family: monospace;"
            f" border: 1px solid {_BORDER}; border-radius: 3px; }}"
        )
        v.addWidget(self._txt_steps)
        self._tbl_rec.currentCellChanged.connect(self._on_record_selected)
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

        h.addWidget(_btn("保存 Checkpoint  Save", _YLW, self._on_save_cp))
        h.addWidget(_btn("手动恢复 Manual Recovery", _BLU, self._on_manual_recovery))
        h.addWidget(_btn("启动时恢复 Startup", _GRN, self._on_startup_recovery))
        h.addStretch()

        btn_r = QtWidgets.QPushButton("刷新 Refresh")
        btn_r.setStyleSheet(
            f"QPushButton {{ background: transparent; color: {_MUT};"
            f" border: 1px solid {_BORDER}; border-radius: 3px;"
            f" padding: 4px 12px; font-size: 12px; }}"
        )
        btn_r.clicked.connect(self.refresh)
        h.addWidget(btn_r)
        return bar

    # ------------------------------------------------------------------ #
    #  公开接口
    # ------------------------------------------------------------------ #

    def refresh(self) -> None:
        if self._engine is None:
            return
        re   = self._engine.recovery_engine
        summ = re.summary()

        phase = summ["phase"]
        color = _PHASE_COLOR.get(phase, _MUT)
        self._kpi["当前阶段 Phase"  ].setText(phase.upper())
        self._kpi["当前阶段 Phase"  ].setStyleSheet(
            f"color: {color}; font-size: 14px; font-weight: bold;")
        self._kpi["恢复总次数 Total"].setText(str(summ["total"]))
        self._kpi["成功次数 Success"].setText(str(summ["succeeded"]))
        self._kpi["失败次数 Failed" ].setText(str(summ["failed"]))
        total = summ["total"]
        rate  = f"{summ['succeeded']/total:.0%}" if total else "---"
        self._kpi["成功率 Rate"     ].setText(rate)
        self._kpi["Checkpoint 数量" ].setText(str(summ["checkpoint_count"]))

        self._refresh_checkpoints(re.list_checkpoints())
        self._refresh_records(re.get_records(limit=100))

    # ------------------------------------------------------------------ #
    #  按钮回调
    # ------------------------------------------------------------------ #

    def _on_save_cp(self) -> None:
        if self._engine:
            path = self._engine.save_checkpoint()
            self.refresh()

    def _on_manual_recovery(self) -> None:
        if self._engine:
            self._engine.trigger_recovery(RecoveryTrigger.MANUAL, "手动触发恢复")
            self.refresh()

    def _on_startup_recovery(self) -> None:
        if self._engine:
            self._engine.trigger_recovery(RecoveryTrigger.STARTUP, "启动恢复")
            self.refresh()

    def _on_record_selected(self, row, *_) -> None:
        if row < 0 or self._engine is None:
            return
        records = self._engine.recovery_engine.get_records(limit=100)
        records = list(reversed(records))
        if row >= len(records):
            return
        rec = records[row]
        lines = [s.to_line() for s in rec.steps]
        self._txt_steps.setPlainText("\n".join(lines))

    # ------------------------------------------------------------------ #
    #  内部渲染
    # ------------------------------------------------------------------ #

    def _refresh_checkpoints(self, cps: list) -> None:
        self._tbl_cp.setRowCount(0)
        for cp in cps:
            row = self._tbl_cp.rowCount()
            self._tbl_cp.insertRow(row)
            self._tbl_cp.setItem(row, 0, _item_left(cp.get("filename", ""), _FG))
            self._tbl_cp.setItem(row, 1, _item(cp.get("saved_at", "")[:19],  _MUT))
            self._tbl_cp.setItem(row, 2, _item(str(cp.get("size_kb", 0)),    _FG))

    def _refresh_records(self, records: list) -> None:
        self._tbl_rec.setRowCount(0)
        for rec in reversed(records):
            row = self._tbl_rec.rowCount()
            self._tbl_rec.insertRow(row)
            ok_color = _GRN if rec.success else _RED
            ok_text  = "YES" if rec.success else "NO"
            ph_color = _PHASE_COLOR.get(rec.phase.value, _MUT)
            self._tbl_rec.setItem(row, 0, _item(rec.record_id,                _MUT))
            self._tbl_rec.setItem(row, 1, _item(rec.trigger.value,             _BLU))
            self._tbl_rec.setItem(row, 2, _item(rec.phase.value,               ph_color))
            self._tbl_rec.setItem(row, 3, _item(ok_text,                       ok_color))
            self._tbl_rec.setItem(row, 4, _item(f"{rec.elapsed_seconds:.1f}",  _FG))
            self._tbl_rec.setItem(row, 5, _item(str(rec.orders_flagged),       _FG))
            self._tbl_rec.setItem(row, 6, _item(str(rec.inconsistencies),
                _RED if rec.inconsistencies > 0 else _MUT))
            self._tbl_rec.setItem(row, 7, _item(str(rec.started_at)[:19],      _MUT))
            self._tbl_rec.setItem(row, 8, _item_left(rec.error_msg or "---",
                _RED if rec.error_msg else _MUT))
