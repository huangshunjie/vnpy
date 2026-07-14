"""
market_behavior/ui/behavior_editor.py  —  行为条件编辑器 Tab
"""
from __future__ import annotations
import datetime
from vnpy.trader.ui import QtWidgets, QtCore

_BG    = "#1e1e2e"
_PANEL = "#181825"
_PAN2  = "#11111b"
_BORD  = "#45475a"
_FG    = "#cdd6f4"
_MUT   = "#6c7086"
_BLU   = "#89b4fa"
_GRN   = "#a6e3a1"
_YLW   = "#f9e2af"
_MAV   = "#cba6f7"

_BTN = ("QPushButton{background:%s;color:#1e1e2e;border:none;border-radius:4px;"
        "padding:6px 16px;font-size:11px;font-weight:bold;}"
        "QPushButton:hover{background:%s;}"
        "QPushButton:disabled{background:#313244;color:#6c7086;}")

def _mkbtn(text, bg, hov):
    b = QtWidgets.QPushButton(text)
    b.setStyleSheet(_BTN % (bg, hov))
    return b

def _lbl(text, color=_FG, size=11, bold=False):
    w = QtWidgets.QLabel(text)
    w.setStyleSheet(f"color:{color};font-size:{size}px;"
                    f"font-weight:{'bold' if bold else 'normal'};"
                    f"background:transparent;border:none;")
    return w

def _hline():
    f = QtWidgets.QFrame()
    f.setFrameShape(QtWidgets.QFrame.Shape.HLine)
    f.setStyleSheet(f"border:none;border-top:1px solid {_BORD};")
    return f

_COMBO_SS = (f"QComboBox{{background:{_PAN2};color:{_FG};border:1px solid {_BORD};"
             f"border-radius:4px;padding:4px 8px;font-size:11px;}}"
             f"QComboBox QAbstractItemView{{background:{_PAN2};color:{_FG};"
             f"selection-background-color:{_BLU};selection-color:#1e1e2e;}}")
_SPIN_SS  = (f"QDoubleSpinBox,QSpinBox{{background:{_PAN2};color:{_FG};"
             f"border:1px solid {_BORD};border-radius:4px;padding:4px 6px;font-size:11px;}}")
_DE_SS    = (f"QDateEdit{{background:{_PAN2};color:{_FG};border:1px solid {_BORD};"
             f"border-radius:4px;padding:4px;font-size:11px;}}")
_CHK_SS   = f"QCheckBox{{color:{_FG};font-size:11px;background:transparent;border:none;}}"

COND_OPTIONS = [
    ("综合强度  kline_strength", "kline_strength", 0.40),
    ("上涨天数  rise_days",      "rise_days",      0.50),
    ("大涨次数  rise_pct",       "rise_pct",       3.00),
    ("大阳线数  big_yang_count", "big_yang_count", 2.00),
    ("涨停次数  limit_up_count", "limit_up_count", 1.00),
    ("突破次数  breakout_count", "breakout_count", 3.00),
    ("波动强度  volatility",     "volatility",     2.00),
    ("连续上涨  continuous",     "continuous",     3.00),
]


class ConditionRow(QtWidgets.QWidget):
    sig_remove = QtCore.Signal(object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"background:{_PAN2};border-radius:4px;")
        lay = QtWidgets.QHBoxLayout(self)
        lay.setContentsMargins(8, 4, 8, 4)
        lay.setSpacing(8)

        self.cond_type = QtWidgets.QComboBox()
        self.cond_type.setStyleSheet(_COMBO_SS)
        self.cond_type.setFixedWidth(220)
        for label, val, default in COND_OPTIONS:
            self.cond_type.addItem(label, val)
        self.cond_type.currentIndexChanged.connect(self._on_type_changed)
        lay.addWidget(self.cond_type)

        lay.addWidget(_lbl("阈值", _MUT))
        self.threshold = QtWidgets.QDoubleSpinBox()
        self.threshold.setStyleSheet(_SPIN_SS)
        self.threshold.setRange(0.0, 9999.0)
        self.threshold.setValue(0.4)
        self.threshold.setSingleStep(0.05)
        self.threshold.setFixedWidth(85)
        lay.addWidget(self.threshold)

        lay.addWidget(_lbl("权重", _MUT))
        self.weight = QtWidgets.QDoubleSpinBox()
        self.weight.setStyleSheet(_SPIN_SS)
        self.weight.setRange(0.1, 10.0)
        self.weight.setValue(1.0)
        self.weight.setSingleStep(0.1)
        self.weight.setFixedWidth(70)
        lay.addWidget(self.weight)

        lay.addStretch()

        btn = _mkbtn("×", "#f38ba8", "#f5a0b8")
        btn.setFixedSize(28, 28)
        btn.clicked.connect(lambda: self.sig_remove.emit(self))
        lay.addWidget(btn)

        self._on_type_changed(0)

    def _on_type_changed(self, idx):
        _, _, default = COND_OPTIONS[idx]
        self.threshold.setValue(default)

    def get_condition(self):
        return {
            "cond_type": self.cond_type.currentData(),
            "threshold": self.threshold.value(),
            "weight":    self.weight.value(),
        }


class BehaviorEditorTab(QtWidgets.QWidget):
    """
    行为条件编辑器 Tab。
    左：股票池 + 时间范围   中：条件列表   右：参数 + 运行
    """
    sig_run_screen   = QtCore.Signal(list, list, dict)
    sig_run_backtest = QtCore.Signal(list, list, dict)

    def __init__(self, engine=None, parent=None):
        super().__init__(parent)
        self._engine     = engine
        self._cond_rows  = []
        self._init_ui()

    # ── 构建 ────────────────────────────────────────────────────────

    def _init_ui(self):
        self.setStyleSheet(f"background:{_BG};")
        root = QtWidgets.QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(10)
        root.addWidget(_lbl("行为条件编辑器  Behavior Editor", _MAV, 15, True))

        sp = QtWidgets.QSplitter(QtCore.Qt.Orientation.Horizontal)
        sp.setStyleSheet(f"QSplitter::handle{{background:{_BORD};width:2px;}}")
        sp.addWidget(self._build_left())
        sp.addWidget(self._build_center())
        sp.addWidget(self._build_right())
        sp.setStretchFactor(0, 1)
        sp.setStretchFactor(1, 2)
        sp.setStretchFactor(2, 1)
        root.addWidget(sp, stretch=1)
        root.addWidget(self._build_run_bar())

    def _panel(self, border_color):
        w = QtWidgets.QWidget()
        w.setStyleSheet(
            f"background:{_PANEL};border:1px solid {border_color};border-radius:6px;")
        return w

    def _build_left(self):
        w = self._panel(_BLU)
        v = QtWidgets.QVBoxLayout(w)
        v.setContentsMargins(14, 14, 14, 14)
        v.setSpacing(8)
        v.addWidget(_lbl("股票池  Stock Pool", _BLU, 12, True))
        v.addWidget(_hline())

        v.addWidget(_lbl("板块筛选", _MUT))
        self._chk = {}
        for key, text, on in [
            ("main_sz", "深交所主板 000/002", True),
            ("gem",     "创业板 300/301",     True),
            ("main_ss", "上交所主板 600/601", True),
            ("star",    "科创板 688",         False),
        ]:
            c = QtWidgets.QCheckBox(text)
            c.setChecked(on)
            c.setStyleSheet(_CHK_SS)
            v.addWidget(c)
            self._chk[key] = c

        v.addWidget(_hline())
        v.addWidget(_lbl("自定义股票（逗号分隔，留空=全市场）", _MUT))
        self._sym_edit = QtWidgets.QPlainTextEdit()
        self._sym_edit.setPlaceholderText("例：000001,600036,300750")
        self._sym_edit.setStyleSheet(
            f"QPlainTextEdit{{background:{_PAN2};color:{_FG};"
            f"border:1px solid {_BORD};border-radius:4px;"
            f"font-size:11px;padding:6px;}}")
        self._sym_edit.setFixedHeight(76)
        v.addWidget(self._sym_edit)

        v.addWidget(_hline())
        v.addWidget(_lbl("时间范围", _MUT))
        row = QtWidgets.QHBoxLayout()
        self._dt_start = QtWidgets.QDateEdit()
        self._dt_end   = QtWidgets.QDateEdit()
        for de, ago in [(self._dt_start, 180), (self._dt_end, 0)]:
            de.setDate(QtCore.QDate.currentDate().addDays(-ago))
            de.setCalendarPopup(True)
            de.setStyleSheet(_DE_SS)
        row.addWidget(self._dt_start)
        row.addWidget(_lbl("~", _MUT))
        row.addWidget(self._dt_end)
        v.addLayout(row)

        v.addWidget(_hline())
        v.addWidget(_lbl("因子窗口（根）", _MUT))
        self._window_sp = QtWidgets.QSpinBox()
        self._window_sp.setRange(5, 250)
        self._window_sp.setValue(20)
        self._window_sp.setStyleSheet(_SPIN_SS)
        v.addWidget(self._window_sp)

        v.addStretch()
        return w

    def _build_center(self):
        w = self._panel(_GRN)
        v = QtWidgets.QVBoxLayout(w)
        v.setContentsMargins(14, 14, 14, 14)
        v.setSpacing(8)

        hdr = QtWidgets.QHBoxLayout()
        hdr.addWidget(_lbl("条件编辑器  Conditions", _GRN, 12, True))
        hdr.addStretch()
        btn_add = _mkbtn("+ 添加条件", _GRN, "#c0f0bc")
        btn_add.clicked.connect(self._add_condition)
        hdr.addWidget(btn_add)
        v.addLayout(hdr)
        v.addWidget(_hline())

        logic_row = QtWidgets.QHBoxLayout()
        logic_row.addWidget(_lbl("逻辑：", _MUT))
        self._rb_and = QtWidgets.QRadioButton("AND（全部满足）")
        self._rb_or  = QtWidgets.QRadioButton("OR（任一满足）")
        self._rb_and.setChecked(True)
        for rb in [self._rb_and, self._rb_or]:
            rb.setStyleSheet(_CHK_SS)
            logic_row.addWidget(rb)
        logic_row.addStretch()
        v.addLayout(logic_row)

        scroll = QtWidgets.QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet(f"QScrollArea{{border:none;background:{_BG};}}")
        self._cond_cont = QtWidgets.QWidget()
        self._cond_cont.setStyleSheet(f"background:{_BG};")
        self._cond_lay  = QtWidgets.QVBoxLayout(self._cond_cont)
        self._cond_lay.setContentsMargins(0, 0, 0, 0)
        self._cond_lay.setSpacing(6)
        self._cond_lay.addStretch()
        scroll.setWidget(self._cond_cont)
        v.addWidget(scroll, stretch=1)

        # 默认两条
        self._add_condition()
        self._add_condition()
        return w

    def _build_right(self):
        w = self._panel(_YLW)
        v = QtWidgets.QVBoxLayout(w)
        v.setContentsMargins(14, 14, 14, 14)
        v.setSpacing(8)
        v.addWidget(_lbl("参数设置  Parameters", _YLW, 12, True))
        v.addWidget(_hline())

        v.addWidget(_lbl("Top N 数量", _MUT))
        self._topn_sp = QtWidgets.QSpinBox()
        self._topn_sp.setRange(1, 500)
        self._topn_sp.setValue(30)
        self._topn_sp.setStyleSheet(_SPIN_SS)
        v.addWidget(self._topn_sp)

        v.addWidget(_lbl("排序依据", _MUT))
        self._sort_cb = QtWidgets.QComboBox()
        self._sort_cb.setStyleSheet(_COMBO_SS)
        for label, val, _ in COND_OPTIONS[:4]:
            self._sort_cb.addItem(label, val)
        v.addWidget(self._sort_cb)

        self._sort_desc_chk = QtWidgets.QCheckBox("降序（强→弱）")
        self._sort_desc_chk.setChecked(True)
        self._sort_desc_chk.setStyleSheet(_CHK_SS)
        v.addWidget(self._sort_desc_chk)

        v.addWidget(_hline())
        v.addWidget(_lbl("回测持有天数", _MUT))
        self._hold_sp = QtWidgets.QSpinBox()
        self._hold_sp.setRange(1, 60)
        self._hold_sp.setValue(5)
        self._hold_sp.setStyleSheet(_SPIN_SS)
        v.addWidget(self._hold_sp)

        v.addWidget(_lbl("最少K线数（过滤新股）", _MUT))
        self._minbars_sp = QtWidgets.QSpinBox()
        self._minbars_sp.setRange(10, 500)
        self._minbars_sp.setValue(60)
        self._minbars_sp.setStyleSheet(_SPIN_SS)
        v.addWidget(self._minbars_sp)

        v.addStretch()
        return w

    def _build_run_bar(self):
        w = QtWidgets.QWidget()
        w.setFixedHeight(50)
        w.setStyleSheet(
            f"background:{_PANEL};border:1px solid {_BORD};border-radius:6px;")
        h = QtWidgets.QHBoxLayout(w)
        h.setContentsMargins(16, 0, 16, 0)
        h.setSpacing(12)

        self._progress = QtWidgets.QProgressBar()
        self._progress.setRange(0, 100)
        self._progress.setValue(0)
        self._progress.setFixedHeight(8)
        self._progress.setStyleSheet(
            f"QProgressBar{{background:{_PAN2};border:none;border-radius:4px;}}"
            f"QProgressBar::chunk{{background:{_BLU};border-radius:4px;}}")
        self._progress.setTextVisible(False)
        h.addWidget(self._progress, stretch=1)

        self._status_lbl = _lbl("就绪", _MUT)
        h.addWidget(self._status_lbl)

        self._btn_screen = _mkbtn("运行选股  ▶", _BLU, "#b4d0fa")
        self._btn_screen.setFixedWidth(130)
        self._btn_screen.clicked.connect(self._on_screen)
        h.addWidget(self._btn_screen)

        self._btn_bt = _mkbtn("历史回测  ◆", _GRN, "#c0f0bc")
        self._btn_bt.setFixedWidth(130)
        self._btn_bt.clicked.connect(self._on_backtest)
        h.addWidget(self._btn_bt)

        return w

    # ── 条件增删 ────────────────────────────────────────────────────

    def _add_condition(self):
        row = ConditionRow()
        row.sig_remove.connect(self._remove_condition)
        self._cond_rows.append(row)
        self._cond_lay.insertWidget(self._cond_lay.count() - 1, row)

    def _remove_condition(self, row):
        if row in self._cond_rows:
            self._cond_rows.remove(row)
            self._cond_lay.removeWidget(row)
            row.deleteLater()

    # ── 收集参数 ────────────────────────────────────────────────────

    def _get_symbols(self):
        raw = self._sym_edit.toPlainText().strip()
        if raw:
            return [s.strip() for s in raw.replace("\uff0c", ",").split(",") if s.strip()]
        return []

    def _get_conditions(self):
        return [r.get_condition() for r in self._cond_rows]

    def _get_cfg(self):
        d = self._dt_start.date()
        e = self._dt_end.date()
        return {
            "start":      datetime.datetime(d.year(), d.month(), d.day()),
            "end":        datetime.datetime(e.year(), e.month(), e.day()),
            "window":     self._window_sp.value(),
            "top_n":      self._topn_sp.value(),
            "sort_by":    self._sort_cb.currentData(),
            "sort_desc":  self._sort_desc_chk.isChecked(),
            "hold_days":  self._hold_sp.value(),
            "min_bars":   self._minbars_sp.value(),
            "require_all": self._rb_and.isChecked(),
            "boards": {k: c.isChecked() for k, c in self._chk.items()},
        }

    # ── 运行 ────────────────────────────────────────────────────────

    def _on_screen(self):
        self._set_busy("扫描中...")
        self.sig_run_screen.emit(self._get_symbols(), self._get_conditions(), self._get_cfg())

    def _on_backtest(self):
        syms = self._get_symbols()
        if not syms:
            QtWidgets.QMessageBox.warning(self, "提示",
                "回测请在「自定义股票」框中输入至少一个代码。")
            return
        self._set_busy("回测中...")
        self.sig_run_backtest.emit(syms, self._get_conditions(), self._get_cfg())

    def _set_busy(self, msg):
        self._btn_screen.setEnabled(False)
        self._btn_bt.setEnabled(False)
        self._status_lbl.setText(msg)
        self._progress.setValue(10)

    def set_progress(self, val: int, msg: str = ""):
        self._progress.setValue(val)
        if msg:
            self._status_lbl.setText(msg)
        if val >= 100:
            self._btn_screen.setEnabled(True)
            self._btn_bt.setEnabled(True)
