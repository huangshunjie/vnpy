"""
alpha_factory_2/ui/screening_tab.py

ScreeningTab — Alpha 筛选面板（Phase 4）。

布局：
  顶部：KPI 栏（总筛选 / 通过 / 拒绝 / 通过率 / 退役数）
  中部：左侧阈值设置面板 / 右侧筛选记录表 + 退役记录表
  底部：操作栏（全流水线 / 筛选 / 刷新）
"""

from __future__ import annotations

from vnpy.trader.ui import QtCore, QtWidgets

_PANEL_BG = "#181825"
_BORDER   = "#45475a"
_FG       = "#cdd6f4"
_MUT      = "#6c7086"
_GRN      = "#a6e3a1"
_YLW      = "#f9e2af"
_RED      = "#f38ba8"
_BLU      = "#89b4fa"
_MAV      = "#cba6f7"
_ORG      = "#fab387"

_REC_COLS = [
    ("记录ID",       90),
    ("Alpha ID",    110),
    ("结果",          60),
    ("总分",          70),
    ("失败规则",      260),
    ("时间",         130),
]
_RET_COLS = [
    ("Alpha ID",    110),
    ("退役原因",     200),
    ("总分",          70),
    ("IC",            60),
    ("连续次数",       60),
    ("退役时间",      130),
]


def _item(text, color=_FG):
    from vnpy.trader.ui import QtGui
    it = QtWidgets.QTableWidgetItem(str(text))
    it.setTextAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
    it.setForeground(QtGui.QColor(color))
    return it


def _item_left(text, color=_FG):
    from vnpy.trader.ui import QtGui
    it = QtWidgets.QTableWidgetItem(str(text))
    it.setTextAlignment(
        QtCore.Qt.AlignmentFlag.AlignLeft | QtCore.Qt.AlignmentFlag.AlignVCenter)
    it.setForeground(QtGui.QColor(color))
    return it


class _ThresholdRow(QtWidgets.QWidget):
    def __init__(self, label: str, default: float,
                 min_v: float, max_v: float, step: float = 0.01,
                 parent=None) -> None:
        super().__init__(parent)
        self.setStyleSheet("border: none;")
        h = QtWidgets.QHBoxLayout(self)
        h.setContentsMargins(0, 0, 0, 0)
        h.setSpacing(6)
        lbl = QtWidgets.QLabel(label)
        lbl.setStyleSheet(f"color: {_MUT}; font-size: 10px; min-width: 110px;")
        self._spin = QtWidgets.QDoubleSpinBox()
        self._spin.setRange(min_v, max_v)
        self._spin.setSingleStep(step)
        self._spin.setValue(default)
        self._spin.setDecimals(3)
        self._spin.setStyleSheet(
            f"QDoubleSpinBox {{ background: #11111b; color: {_FG};"
            f" border: 1px solid {_BORDER}; border-radius: 3px;"
            f" padding: 2px 4px; font-size: 11px; }}"
        )
        h.addWidget(lbl)
        h.addWidget(self._spin, stretch=1)

    @property
    def value(self) -> float:
        return self._spin.value()


class ScreeningTab(QtWidgets.QWidget):
    """Alpha 筛选面板（Phase 4）。"""

    def __init__(self, engine=None, parent=None) -> None:
        super().__init__(parent)
        self._engine = engine
        self._init_ui()

    def set_engine(self, engine) -> None:
        self._engine = engine
        self._load_thresholds()

    def _init_ui(self) -> None:
        root = QtWidgets.QVBoxLayout(self)
        root.setContentsMargins(6, 6, 6, 6)
        root.setSpacing(6)
        root.addWidget(self._build_kpi_bar())
        mid = QtWidgets.QSplitter(QtCore.Qt.Orientation.Horizontal)
        mid.addWidget(self._build_threshold_panel())
        right = QtWidgets.QWidget()
        rv = QtWidgets.QVBoxLayout(right)
        rv.setContentsMargins(0, 0, 0, 0)
        rv.setSpacing(4)
        rv.addWidget(self._build_screening_table(), stretch=3)
        rv.addWidget(self._build_retire_table(),    stretch=2)
        mid.addWidget(right)
        mid.setSizes([270, 930])
        root.addWidget(mid, stretch=1)
        root.addWidget(self._build_action_bar())

    def _build_kpi_bar(self) -> QtWidgets.QWidget:
        bar = QtWidgets.QWidget()
        bar.setFixedHeight(66)
        bar.setStyleSheet(f"background: {_PANEL_BG}; border-radius: 4px;")
        h = QtWidgets.QHBoxLayout(bar)
        h.setContentsMargins(20, 6, 20, 6)
        h.setSpacing(32)
        kpis = [
            ("总筛选 Total",  "0", _FG),
            ("通过 Passed",   "0", _GRN),
            ("拒绝 Rejected", "0", _RED),
            ("通过率 Rate",   "---", _YLW),
            ("退役 Retired",  "0", _ORG),
        ]
        self._kpi: dict[str, QtWidgets.QLabel] = {}
        for name, val, color in kpis:
            col = QtWidgets.QVBoxLayout()
            col.setSpacing(1)
            ln = QtWidgets.QLabel(name)
            ln.setStyleSheet(f"color: {_MUT}; font-size: 10px;")
            ln.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
            lv = QtWidgets.QLabel(val)
            lv.setStyleSheet(
                f"color: {color}; font-size: 14px; font-weight: bold;")
            lv.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
            col.addWidget(ln); col.addWidget(lv)
            self._kpi[name] = lv
            h.addLayout(col)
        h.addStretch()
        return bar

    def _build_threshold_panel(self) -> QtWidgets.QWidget:
        panel = QtWidgets.QWidget()
        panel.setStyleSheet(
            f"background: {_PANEL_BG}; border-radius: 6px;"
            f" border: 1px solid {_BORDER};"
        )
        v = QtWidgets.QVBoxLayout(panel)
        v.setContentsMargins(12, 12, 12, 12)
        v.setSpacing(6)
        t = QtWidgets.QLabel("筛选阈值  Screening Rules")
        t.setStyleSheet(
            f"color: {_MAV}; font-size: 12px; font-weight: bold; border: none;")
        v.addWidget(t)
        v.addWidget(self._sep())
        self._row_ic    = _ThresholdRow("IC 最低  ic_min",        0.02,  -0.2,  0.5,  0.005)
        self._row_stab  = _ThresholdRow("IR 最低  stability_min", 0.0,   -2.0,  5.0,  0.1)
        self._row_decay = _ThresholdRow("半衰期  decay_min(日)",  2.0,    0.0,  20.0, 0.5)
        self._row_score = _ThresholdRow("总分  score_min",        0.20,   0.0,   1.0, 0.01)
        self._row_to    = _ThresholdRow("换手率上限  to_max",     0.95,   0.0,   1.0, 0.01)
        for row in (self._row_ic, self._row_stab, self._row_decay,
                    self._row_score, self._row_to):
            v.addWidget(row)
        v.addWidget(self._sep())
        lbl_ret = QtWidgets.QLabel("自动退役  Auto Retire")
        lbl_ret.setStyleSheet(
            f"color: {_ORG}; font-size: 11px; font-weight: bold; border: none;")
        v.addWidget(lbl_ret)
        self._row_ret_score  = _ThresholdRow("退役分数线",        0.15,  0.0,  1.0, 0.01)
        self._row_ret_ic     = _ThresholdRow("退役 IC 线",       -0.05, -0.5,  0.1, 0.005)
        self._row_ret_streak = QtWidgets.QSpinBox()
        self._row_ret_streak.setRange(1, 20)
        self._row_ret_streak.setValue(3)
        self._row_ret_streak.setStyleSheet(
            f"QSpinBox {{ background: #11111b; color: {_FG};"
            f" border: 1px solid {_BORDER}; border-radius: 3px;"
            f" padding: 2px 4px; font-size: 11px; }}"
        )
        streak_row = QtWidgets.QWidget()
        streak_row.setStyleSheet("border: none;")
        sh = QtWidgets.QHBoxLayout(streak_row)
        sh.setContentsMargins(0, 0, 0, 0)
        sl = QtWidgets.QLabel("连续次数  streak")
        sl.setStyleSheet(f"color: {_MUT}; font-size: 10px; min-width: 110px;")
        sh.addWidget(sl)
        sh.addWidget(self._row_ret_streak, stretch=1)
        for row in (self._row_ret_score, self._row_ret_ic):
            v.addWidget(row)
        v.addWidget(streak_row)
        v.addStretch()
        v.addWidget(self._sep())
        btn_apply = QtWidgets.QPushButton("应用阈值  Apply")
        btn_apply.setStyleSheet(
            f"QPushButton {{ background: {_MAV}22; color: {_MAV};"
            f" border: 1px solid {_MAV}; border-radius: 4px;"
            f" padding: 6px 0px; font-size: 12px; font-weight: bold; }}"
            f"QPushButton:hover {{ background: {_MAV}44; }}"
        )
        btn_apply.clicked.connect(self._on_apply_thresholds)
        v.addWidget(btn_apply)
        return panel

    def _build_screening_table(self) -> QtWidgets.QWidget:
        w = QtWidgets.QWidget()
        w.setStyleSheet(f"background: {_PANEL_BG}; border-radius: 4px;")
        v = QtWidgets.QVBoxLayout(w)
        v.setContentsMargins(8, 6, 8, 6)
        v.setSpacing(3)
        lbl = QtWidgets.QLabel("筛选记录  Screening Records")
        lbl.setStyleSheet(f"color: {_MUT}; font-size: 10px;")
        v.addWidget(lbl)
        self._tbl_rec = self._make_table(_REC_COLS)
        v.addWidget(self._tbl_rec, stretch=1)
        return w

    def _build_retire_table(self) -> QtWidgets.QWidget:
        w = QtWidgets.QWidget()
        w.setStyleSheet(f"background: {_PANEL_BG}; border-radius: 4px;")
        v = QtWidgets.QVBoxLayout(w)
        v.setContentsMargins(8, 6, 8, 6)
        v.setSpacing(3)
        lbl = QtWidgets.QLabel("退役记录  Retire Records")
        lbl.setStyleSheet(f"color: {_ORG}; font-size: 10px;")
        v.addWidget(lbl)
        self._tbl_ret = self._make_table(_RET_COLS)
        v.addWidget(self._tbl_ret, stretch=1)
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
                f" padding: 4px 14px; font-size: 12px; }}"
                f"QPushButton:hover {{ background: {color}22; }}"
            )
            b.clicked.connect(slot)
            return b

        h.addWidget(_btn("▶▶ 全流水线  Full Pipeline", _MAV, self._on_pipeline))
        h.addWidget(_btn("筛选  Screen Only",          _BLU, self._on_screen))
        h.addStretch()
        h.addWidget(_btn("刷新 Refresh",               _MUT, self.refresh))
        return bar

    def refresh(self) -> None:
        if self._engine is None:
            return
        se   = self._engine.screening_engine
        summ = se.summary()
        self._kpi["总筛选 Total" ].setText(str(summ["total_screened"]))
        self._kpi["通过 Passed"  ].setText(str(summ["passed"]))
        self._kpi["拒绝 Rejected"].setText(str(summ["rejected"]))
        rate = summ["pass_rate"]
        rate_c = _GRN if rate >= 0.5 else (_YLW if rate >= 0.3 else _RED)
        self._kpi["通过率 Rate"].setText(f"{rate:.1%}")
        self._kpi["通过率 Rate"].setStyleSheet(
            f"color: {rate_c}; font-size: 14px; font-weight: bold;")
        self._kpi["退役 Retired"].setText(str(summ["retired"]))
        self._render_records(se.get_screening_records(limit=200))
        self._render_retires(se.get_retire_records(limit=100))

    def _on_pipeline(self) -> None:
        if self._engine is None:
            QtWidgets.QMessageBox.warning(self, "未初始化", "请先启动 Alpha Factory 引擎。")
            return
        self._engine.run_full_pipeline(n=10)
        self.refresh()

    def _on_screen(self) -> None:
        if self._engine:
            self._engine.screen_alphas()
            self.refresh()

    def _on_apply_thresholds(self) -> None:
        if self._engine is None:
            return
        self._engine.update_screening_thresholds(
            ic_min        = self._row_ic.value,
            stability_min = self._row_stab.value,
            decay_min     = self._row_decay.value,
            score_min     = self._row_score.value,
            turnover_max  = self._row_to.value,
            retire_score  = self._row_ret_score.value,
            retire_ic     = self._row_ret_ic.value,
            retire_streak = self._row_ret_streak.value(),
        )

    def _load_thresholds(self) -> None:
        if self._engine is None:
            return
        t = self._engine.screening_engine.get_thresholds()
        self._row_ic.   _spin.setValue(t.get("ic_min",        0.02))
        self._row_stab. _spin.setValue(t.get("stability_min", 0.0))
        self._row_decay._spin.setValue(t.get("decay_min",     2.0))
        self._row_score._spin.setValue(t.get("score_min",     0.20))
        self._row_to.   _spin.setValue(t.get("turnover_max",  0.95))
        self._row_ret_score._spin.setValue(t.get("retire_score", 0.15))
        self._row_ret_ic.   _spin.setValue(t.get("retire_ic",   -0.05))
        self._row_ret_streak.setValue(t.get("retire_streak",   3))

    def _render_records(self, records: list) -> None:
        self._tbl_rec.setRowCount(0)
        for rec in reversed(records):
            row = self._tbl_rec.rowCount()
            self._tbl_rec.insertRow(row)
            color = _GRN if rec.passed else _RED
            self._tbl_rec.setItem(row, 0, _item(rec.record_id,            _MUT))
            self._tbl_rec.setItem(row, 1, _item(rec.alpha_id,             _MAV))
            self._tbl_rec.setItem(row, 2, _item("PASS" if rec.passed else "FAIL", color))
            self._tbl_rec.setItem(row, 3, _item(f"{rec.score:.4f}",       color))
            self._tbl_rec.setItem(row, 4, _item_left(rec.detail or "---", _MUT))
            self._tbl_rec.setItem(row, 5, _item(str(rec.ts)[:19],         _MUT))

    def _render_retires(self, records: list) -> None:
        self._tbl_ret.setRowCount(0)
        for rec in reversed(records):
            row = self._tbl_ret.rowCount()
            self._tbl_ret.insertRow(row)
            self._tbl_ret.setItem(row, 0, _item(rec.alpha_id,              _ORG))
            self._tbl_ret.setItem(row, 1, _item_left(rec.reason,           _RED))
            self._tbl_ret.setItem(row, 2, _item(f"{rec.score:.4f}",        _YLW))
            self._tbl_ret.setItem(row, 3, _item(f"{rec.ic:.4f}",           _YLW))
            self._tbl_ret.setItem(row, 4, _item(str(rec.streak),           _MUT))
            self._tbl_ret.setItem(row, 5, _item(str(rec.retired_at)[:19],  _MUT))

    def _make_table(self, cols: list) -> QtWidgets.QTableWidget:
        tbl = QtWidgets.QTableWidget(0, len(cols))
        tbl.setHorizontalHeaderLabels([c[0] for c in cols])
        for i, (_, w_) in enumerate(cols):
            tbl.setColumnWidth(i, w_)
        tbl.horizontalHeader().setStretchLastSection(True)
        tbl.verticalHeader().setVisible(False)
        tbl.setEditTriggers(
            QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
        tbl.setSelectionBehavior(
            QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
        tbl.setStyleSheet("font-size: 11px;")
        return tbl

    def _sep(self) -> QtWidgets.QFrame:
        s = QtWidgets.QFrame()
        s.setFrameShape(QtWidgets.QFrame.Shape.HLine)
        s.setStyleSheet(f"border: none; border-top: 1px solid {_BORDER};")
        return s
