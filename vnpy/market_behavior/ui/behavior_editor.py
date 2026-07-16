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
_RED   = "#f38ba8"

_BTN = ("QPushButton{background:%s;color:#1e1e2e;border:none;border-radius:4px;"
        "padding:6px 16px;font-size:14px;font-weight:bold;}"
        "QPushButton:hover{background:%s;}"
        "QPushButton:disabled{background:#313244;color:#6c7086;}")

def _mkbtn(text, bg, hov):
    b = QtWidgets.QPushButton(text)
    b.setStyleSheet(_BTN % (bg, hov))
    return b

def _lbl(text, color=_FG, size=14, bold=False):
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
             f"border-radius:4px;padding:4px 8px;font-size:14px;}}"
             f"QComboBox QAbstractItemView{{background:{_PAN2};color:{_FG};"
             f"selection-background-color:{_BLU};selection-color:#1e1e2e;}}")
_SPIN_SS  = (f"QDoubleSpinBox,QSpinBox{{background:{_PAN2};color:{_FG};"
             f"border:1px solid {_BORD};border-radius:4px;padding:4px 6px;font-size:14px;}}")
_DE_SS    = (f"QDateEdit{{background:{_PAN2};color:{_FG};border:1px solid {_BORD};"
             f"border-radius:4px;padding:4px;font-size:14px;}}")
_CHK_SS   = f"QCheckBox{{color:{_FG};font-size:14px;background:transparent;border:none;}}"

# ── 条件分组（Phase 10.1）format: (label, cond_type, default, unit, hint)
COND_GROUPS = [
    ("📈 趋势行为  Trend", [
        ("  连续上涨  continuous",    "continuous",    3.00, "天数",     "末尾连续收涨 >= N 天"),
        ("  上涨天数  rise_days",     "rise_days",     0.50, "0-1比率",  "窗口内上涨天数占比 >= N"),
        ("  均线多头  ma_alignment",  "ma_alignment",  0.00, "（无阈值）", "MA5>MA10>MA20>MA60 多头排列"),
        ("  趋势斜率  trend_slope",   "trend_slope",   0.10, "% / 天",   "MA20斜率 >= N%/天，正值代表上升"),
    ]),
    ("🔥 强势行为  Momentum", [
        ("  综合强度  kline_strength","kline_strength", 0.40, "0-1得分",  "行为因子综合强度 >= N"),
        ("  大涨次数  rise_pct",      "rise_pct",       3.00, "% 涨幅",   "单日涨幅 >= N%，窗口内至少1次"),
        ("  N日收益   return_n_days", "return_n_days", 10.00, "% 收益",   "过去N日累计涨幅 >= N%"),
    ]),
    ("🚀 突破行为  Breakout", [
        ("  突破次数  breakout_count","breakout_count", 3.00, "次数",     "窗口内突破新高/均线 >= N次"),
        ("  新高突破  new_high_n",    "new_high_n",     0.00, "（无阈值）", "收盘价突破N日最高价"),
    ]),
    ("🕯 K线形态  Pattern", [
        ("  大阳线数  big_yang_count","big_yang_count", 2.00, "次（根）",  "窗口内大阳线根数 >= N"),
    ]),
    ("📊 量价行为  Volume", [
        ("  放量上涨  volume_price_confirm","volume_price_confirm",1.50,"倍（均量）","涨幅>=3%且成交量>=均量N倍"),
    ]),
    ("🔥 涨停行为  Limit", [
        ("  涨停次数  limit_up_count","limit_up_count", 1.00, "次数",     "窗口内涨停次数 >= N"),
    ]),
    ("🌊 波动行为  Volatility", [
        ("  波动强度  volatility",    "volatility",     2.00, "% 振幅",    "日均振幅 >= N%"),
        ("  ATR振幅   atr_ratio",     "atr_ratio",      1.00, "% (ATR/价)","ATR占收盘价的比例 >= N%"),
        ("  布林带宽  boll_width",    "boll_width",     0.05, "宽度比",    "布林带宽度(上下轨/中轨) >= N"),
    ]),
    ("⚡ 技术指标  Indicator", [
        ("  MACD金叉  macd_golden",   "macd_golden",    0.00, "（无阈值）", "日线MACD DIF上穿DEA（金叉）"),
        ("  MACD死叉  macd_death",    "macd_death",     0.00, "（无阈值）", "日线MACD DIF下穿DEA（死叉）"),
        ("  RSI范围   rsi_range",     "rsi_range",     30.00, "RSI下限",   "RSI(14)在[N, 70]范围内，N=下限"),
        ("  回踩检测  pullback",      "pullback",       -5.0, "% 跌幅",    "近期跌幅在合理范围，表示健康回踩"),
    ]),
    ("📅 周线指标  Weekly", [
        ("  13周均线↑ weekly_ma_slope","weekly_ma_slope",0.00,"（无阈值）","周线MA(13)斜率向上"),
    ]),
]
# 向后兼容
COND_OPTIONS = [item for _, group in COND_GROUPS for item in group]


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
        self.cond_type.setFixedWidth(270)
        for group_name, items in COND_GROUPS:
            # 分组标题（灰色、不可选）
            self.cond_type.addItem(group_name, None)
            header_idx = self.cond_type.count() - 1
            item = self.cond_type.model().item(header_idx)
            item.setEnabled(False)
            from vnpy.trader.ui import QtGui as _QtGui
            item.setForeground(_QtGui.QColor("#6c7086"))
            # 分组内条件
            for label, val, default, unit, hint in items:
                self.cond_type.addItem(label, (val, default, unit, hint))
        self.cond_type.currentIndexChanged.connect(self._on_type_changed)
        lay.addWidget(self.cond_type)

        lay.addWidget(_lbl("阈值", _MUT))
        self.threshold = QtWidgets.QDoubleSpinBox()
        self.threshold.setStyleSheet(_SPIN_SS)
        self.threshold.setRange(0.0, 9999.0)
        self.threshold.setValue(0.4)
        self.threshold.setSingleStep(0.05)
        self.threshold.setFixedWidth(100)
        lay.addWidget(self.threshold)

        self._hint_lbl = QtWidgets.QLabel("")
        self._hint_lbl.setStyleSheet(
            "color:#f9e2af;font-size:14px;background:transparent;border:none;")
        self._hint_lbl.setMinimumWidth(270)
        lay.addWidget(self._hint_lbl)

        lay.addWidget(_lbl("权重", _MUT))
        self.weight = QtWidgets.QDoubleSpinBox()
        self.weight.setStyleSheet(_SPIN_SS)
        self.weight.setRange(0.1, 10.0)
        self.weight.setValue(1.0)
        self.weight.setSingleStep(0.1)
        self.weight.setFixedWidth(85)
        lay.addWidget(self.weight)

        lay.addStretch()

        btn = _mkbtn("×", "#f38ba8", "#f5a0b8")
        btn.setFixedSize(28, 28)
        btn.clicked.connect(lambda: self.sig_remove.emit(self))
        lay.addWidget(btn)

        self._on_type_changed(0)

    def _on_type_changed(self, idx):
        data = self.cond_type.currentData()
        if data is None:
            # 选中了分组标题，自动跳到下一个可选项
            next_idx = idx + 1
            while next_idx < self.cond_type.count():
                if self.cond_type.itemData(next_idx) is not None:
                    self.cond_type.setCurrentIndex(next_idx)
                    return
                next_idx += 1
            return
        data = self.cond_type.currentData()
        if data is None:
            return
        _, default, unit, hint = data
        self.threshold.setValue(default)
        self._hint_lbl.setText(f"[单位:{unit}]  {hint}")

    def get_condition(self):
        return {
            "cond_type": self.cond_type.currentData()[0],
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
        v.addWidget(_lbl("股票池  Stock Pool", _BLU, 14, True))
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
            f"font-size:14px;padding:6px;}}")
        self._sym_edit.setFixedHeight(76)
        v.addWidget(self._sym_edit)

        v.addWidget(_hline())
        _time_hdr = QtWidgets.QHBoxLayout()
        _time_hdr.setContentsMargins(0, 0, 0, 0)
        _time_hdr.addWidget(_lbl("时间范围", _MUT))
        self._bars_hint = QtWidgets.QLabel("")
        self._bars_hint.setStyleSheet("color:#a6e3a1;font-size:14px;background:transparent;")
        _time_hdr.addWidget(self._bars_hint)
        _time_hdr.addStretch()
        v.addLayout(_time_hdr)
        row = QtWidgets.QHBoxLayout()
        self._dt_start = QtWidgets.QDateEdit()
        self._dt_end   = QtWidgets.QDateEdit()
        for de, ago in [(self._dt_start, 180), (self._dt_end, 0)]:
            de.setDate(QtCore.QDate.currentDate().addDays(-ago))
            de.setCalendarPopup(True)
            de.setStyleSheet(_DE_SS)
        self._dt_start.dateChanged.connect(self._update_bars_hint)
        self._dt_end.dateChanged.connect(self._update_bars_hint)
        row.addWidget(self._dt_start)
        row.addWidget(_lbl("~", _MUT))
        row.addWidget(self._dt_end)
        v.addLayout(row)
        self._update_bars_hint()

        v.addWidget(_hline())
        v.addWidget(_lbl("因子窗口（根）", _MUT))
        self._window_sp = QtWidgets.QSpinBox()
        self._window_sp.setRange(5, 4200)
        self._window_sp.setValue(20)
        self._window_sp.setStyleSheet(_SPIN_SS)
        v.addWidget(self._window_sp)

        v.addStretch()
        return w

    def _update_bars_hint(self, *_) -> None:
        """根据当前选择的起止日期估算交易日数并更新提示标签。"""
        import datetime as _dt
        d1 = self._dt_start.date()
        d2 = self._dt_end.date()
        start = _dt.date(d1.year(), d1.month(), d1.day())
        end   = _dt.date(d2.year(), d2.month(), d2.day())
        if end <= start:
            self._bars_hint.setText("（日期无效）")
            return
        days  = (end - start).days
        # 按交易日约占自然日 5/7 估算，精确到±5根左右
        bars  = int(days * 5 / 7)
        self._bars_hint.setText(f"（约 {bars} 根）")


    def _build_center(self):
        w = self._panel(_GRN)
        v = QtWidgets.QVBoxLayout(w)
        v.setContentsMargins(14, 14, 14, 14)
        v.setSpacing(8)

        hdr = QtWidgets.QHBoxLayout()
        hdr.addWidget(_lbl("条件编辑器  Conditions", _GRN, 14, True))
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
        v.addWidget(_lbl("参数设置  Parameters", _YLW, 14, True))
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
        for label, val, *_ in COND_OPTIONS[:4]:
            self._sort_cb.addItem(label, val)
        v.addWidget(self._sort_cb)

        self._sort_desc_chk = QtWidgets.QCheckBox("降序（强→弱）")
        self._sort_desc_chk.setChecked(True)
        self._sort_desc_chk.setStyleSheet(_CHK_SS)
        v.addWidget(self._sort_desc_chk)

        v.addWidget(_hline())
        v.addWidget(_lbl("回测卖出设置", _YLW, 13, True))

        v.addWidget(_lbl("最大持仓天数", _MUT))
        self._hold_sp = QtWidgets.QSpinBox()
        self._hold_sp.setRange(1, 120)
        self._hold_sp.setValue(20)
        self._hold_sp.setStyleSheet(_SPIN_SS)
        self._hold_sp.setToolTip("超过此天数强制卖出（兜底）")
        v.addWidget(self._hold_sp)

        v.addWidget(_lbl("止盈触发（%，盈利达到）", _MUT))
        self._tp_sp = QtWidgets.QDoubleSpinBox()
        self._tp_sp.setRange(0.0, 200.0)
        self._tp_sp.setValue(15.0)
        self._tp_sp.setSingleStep(1.0)
        self._tp_sp.setDecimals(1)
        self._tp_sp.setStyleSheet(_SPIN_SS)
        self._tp_sp.setToolTip("盈利达到N%后，启动追踪止盈（0=不启用）")
        v.addWidget(self._tp_sp)

        v.addWidget(_lbl("追踪止盈回撤（%，从最高点）", _MUT))
        self._tp_trail_sp = QtWidgets.QDoubleSpinBox()
        self._tp_trail_sp.setRange(0.0, 50.0)
        self._tp_trail_sp.setValue(10.0)
        self._tp_trail_sp.setSingleStep(1.0)
        self._tp_trail_sp.setDecimals(1)
        self._tp_trail_sp.setStyleSheet(_SPIN_SS)
        self._tp_trail_sp.setToolTip("触发止盈后，从最高点回撤N%时卖出")
        v.addWidget(self._tp_trail_sp)

        v.addWidget(_lbl("止损触发（%，亏损达到）", _MUT))
        self._sl_sp = QtWidgets.QDoubleSpinBox()
        self._sl_sp.setRange(0.0, 50.0)
        self._sl_sp.setValue(7.0)
        self._sl_sp.setSingleStep(0.5)
        self._sl_sp.setDecimals(1)
        self._sl_sp.setStyleSheet(_SPIN_SS)
        self._sl_sp.setToolTip("亏损达到N%时止损卖出（0=不启用）")
        v.addWidget(self._sl_sp)

        v.addWidget(_lbl("最少K线数（过滤新股）", _MUT))
        self._minbars_sp = QtWidgets.QSpinBox()
        self._minbars_sp.setRange(10, 500)
        self._minbars_sp.setValue(60)
        self._minbars_sp.setStyleSheet(_SPIN_SS)
        v.addWidget(self._minbars_sp)

        v.addWidget(_hline())
        v.addWidget(_lbl("交易成本设置", _RED, 14, True))

        v.addWidget(_lbl("手续费率（万，买入）", _MUT))
        self._comm_sp = QtWidgets.QDoubleSpinBox()
        self._comm_sp.setRange(0.0, 100.0)
        self._comm_sp.setValue(3.0)
        self._comm_sp.setSingleStep(0.5)
        self._comm_sp.setDecimals(1)
        self._comm_sp.setStyleSheet(_SPIN_SS)
        self._comm_sp.setToolTip("默认3（即万分之三，0.03%）")
        v.addWidget(self._comm_sp)

        v.addWidget(_lbl("印花税率（千，卖出）", _MUT))
        self._stamp_sp = QtWidgets.QDoubleSpinBox()
        self._stamp_sp.setRange(0.0, 100.0)
        self._stamp_sp.setValue(1.0)
        self._stamp_sp.setSingleStep(0.5)
        self._stamp_sp.setDecimals(1)
        self._stamp_sp.setStyleSheet(_SPIN_SS)
        self._stamp_sp.setToolTip("默认1（即千分之一，0.1%），仅卖出时收取")
        v.addWidget(self._stamp_sp)

        v.addWidget(_lbl("滑点（万，买卖合计）", _MUT))
        self._slip_sp = QtWidgets.QDoubleSpinBox()
        self._slip_sp.setRange(0.0, 50.0)
        self._slip_sp.setValue(2.0)
        self._slip_sp.setSingleStep(0.5)
        self._slip_sp.setDecimals(1)
        self._slip_sp.setStyleSheet(_SPIN_SS)
        self._slip_sp.setToolTip("买卖合计滑点，默认2万（即买入+卖出各笡1万）")
        v.addWidget(self._slip_sp)

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
        self._btn_screen.setFixedWidth(150)
        self._btn_screen.clicked.connect(self._on_screen)
        h.addWidget(self._btn_screen)

        self._btn_bt = _mkbtn("历史回测  ◆", _GRN, "#c0f0bc")
        self._btn_bt.setFixedWidth(150)
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
            "take_profit":       self._tp_sp.value(),
            "trail_drawdown":    self._tp_trail_sp.value(),
            "stop_loss":         self._sl_sp.value(),
            "min_bars":   self._minbars_sp.value(),
            "comm_rate":   self._comm_sp.value()  / 10000,
            "stamp_rate":  self._stamp_sp.value() / 10000,
            "slip_rate":   self._slip_sp.value()  / 10000,
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