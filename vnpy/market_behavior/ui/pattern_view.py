"""
market_behavior/ui/pattern_view.py  —  K线形态视图 Tab（完整实现）
"""
from __future__ import annotations
from vnpy.trader.ui import QtWidgets, QtCore, QtGui

_BG    = "#1e1e2e"
_PANEL = "#181825"
_PAN2  = "#11111b"
_BORD  = "#45475a"
_FG    = "#cdd6f4"
_MUT   = "#6c7086"
_BLU   = "#89b4fa"
_GRN   = "#a6e3a1"
_YLW   = "#f9e2af"
_RED   = "#f38ba8"
_MAV   = "#cba6f7"
_ORG   = "#fab387"

_TBL_SS = (
    f"QTableWidget{{background:{_PAN2};color:{_FG};"
    f"border:none;gridline-color:{_BORD};font-size:14px;}}"
    f"QTableWidget::item{{padding:4px 8px;}}"
    f"QTableWidget::item:selected{{background:{_BLU};color:#1e1e2e;}}"
    f"QHeaderView::section{{background:{_PANEL};color:{_MUT};"
    f"border:none;border-bottom:1px solid {_BORD};"
    f"padding:4px 8px;font-size:14px;font-weight:bold;}}"
)

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

# 形态类型 -> 颜色映射
PATTERN_COLOR = {
    # 单K
    "big_yang":      _GRN,
    "big_yin":       _RED,
    "hammer":        _GRN,
    "shooting_star": _RED,
    "doji":          _YLW,
    "long_upper":    _RED,
    "long_lower":    _GRN,
    "high_wave":     _YLW,
    # 组合
    "morning_star":  _GRN,
    "evening_star":  _RED,
    "three_soldiers":_GRN,
    "three_crows":   _RED,
    "bullish_engulf":_GRN,
    "bearish_engulf":_RED,
    # 突破
    "new_high":      _BLU,
    "new_low":       _RED,
    "vol_breakout":  _MAV,
    "ma_breakout":   _BLU,
    # 连续行为
    "continuous_rise":_GRN,
    "continuous_fall":_RED,
}

CATEGORY_META = [
    ("单K形态  Single Candle", _BLU, [
        "big_yang","big_yin","hammer","shooting_star",
        "doji","long_upper","long_lower","high_wave",
    ]),
    ("K线组合  Sequence", _GRN, [
        "morning_star","evening_star","three_soldiers",
        "three_crows","bullish_engulf","bearish_engulf",
    ]),
    ("突破信号  Breakout", _YLW, [
        "new_high","new_low","vol_breakout","ma_breakout",
    ]),
    ("连续行为  Continuous", _ORG, [
        "continuous_rise","continuous_fall",
    ]),
]

PATTERN_CN = {
    "big_yang":       "大阳线",
    "big_yin":        "大阴线",
    "hammer":         "锤子线",
    "shooting_star":  "流星线",
    "doji":           "十字星",
    "long_upper":     "长上影",
    "long_lower":     "长下影",
    "high_wave":      "高波动",
    "morning_star":   "早晨之星",
    "evening_star":   "黄昏之星",
    "three_soldiers": "三白兵",
    "three_crows":    "三黑鸦",
    "bullish_engulf": "看涨吞没",
    "bearish_engulf": "看跌吞没",
    "new_high":       "N日新高",
    "new_low":        "N日新低",
    "vol_breakout":   "量能突破",
    "ma_breakout":    "均线突破",
    "continuous_rise":"连续上涨",
    "continuous_fall":"连续下跌",
}


class PatternViewTab(QtWidgets.QWidget):
    """
    K线形态视图 Tab。
    左：形态分类 + 当前触发统计
    右：全量形态识别结果表格
    """

    def __init__(self, engine=None, parent=None):
        super().__init__(parent)
        self._engine       = engine
        self._count_labels = {}   # pattern_key -> QLabel (显示触发数)
        self._init_ui()

    def _init_ui(self):
        self.setStyleSheet(f"background:{_BG};")
        root = QtWidgets.QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(10)

        # 标题行
        title_row = QtWidgets.QHBoxLayout()
        title_row.addWidget(_lbl("K线形态视图  Pattern View", _MAV, 15, True))
        title_row.addStretch()
        self._sym_lbl = _lbl("未选择股票", _MUT, 14)
        title_row.addWidget(self._sym_lbl)
        root.addLayout(title_row)
        root.addWidget(_hline())

        # 主体：左栏（分类统计） + 右栏（结果表格）
        body = QtWidgets.QSplitter(QtCore.Qt.Orientation.Horizontal)
        body.setStyleSheet(f"QSplitter::handle{{background:{_BORD};width:2px;}}")
        body.addWidget(self._build_left())
        body.addWidget(self._build_right())
        body.setStretchFactor(0, 1)
        body.setStretchFactor(1, 2)
        root.addWidget(body, stretch=1)

    def _build_left(self) -> QtWidgets.QWidget:
        w = QtWidgets.QWidget()
        w.setStyleSheet(
            f"background:{_PANEL};border:1px solid {_BORD};border-radius:6px;")
        v = QtWidgets.QVBoxLayout(w)
        v.setContentsMargins(14, 14, 14, 14)
        v.setSpacing(4)

        title = _lbl("形态分类统计  Categories", _MAV, 14, True)
        title.setMinimumHeight(32)
        v.addWidget(title)
        v.addWidget(_hline())

        for cat_name, cat_color, keys in CATEGORY_META:
            cat_lbl = _lbl(cat_name, cat_color, 14, True)
            cat_lbl.setMinimumHeight(32)
            v.addWidget(cat_lbl)
            for key in keys:
                row_w = QtWidgets.QWidget()
                row_w.setMinimumHeight(30)
                row_w.setStyleSheet("background:transparent;")
                row = QtWidgets.QHBoxLayout(row_w)
                row.setContentsMargins(4, 0, 4, 0)
                row.setSpacing(4)
                cn = PATTERN_CN.get(key, key)
                lbl_name = _lbl(f"  {cn}", _FG, 14)
                lbl_name.setMinimumHeight(30)
                row.addWidget(lbl_name)
                row.addStretch()
                cnt_lbl = _lbl("0", PATTERN_COLOR.get(key, _FG), 14, True)
                cnt_lbl.setMinimumHeight(30)
                self._count_labels[key] = cnt_lbl
                row.addWidget(cnt_lbl)
                v.addWidget(row_w)
            v.addWidget(_hline())

        v.addStretch()
        return w

    def _build_right(self) -> QtWidgets.QWidget:
        w = QtWidgets.QWidget()
        w.setStyleSheet(
            f"background:{_PANEL};border:1px solid {_BORD};border-radius:6px;")
        v = QtWidgets.QVBoxLayout(w)
        v.setContentsMargins(14, 14, 14, 14)
        v.setSpacing(8)

        hdr = QtWidgets.QHBoxLayout()
        hdr.addWidget(_lbl("形态识别结果  Detection Results", _BLU, 14, True))
        hdr.addStretch()
        self._total_lbl = _lbl("共 0 条", _MUT)
        hdr.addWidget(self._total_lbl)
        v.addLayout(hdr)
        v.addWidget(_hline())

        self._result_table = QtWidgets.QTableWidget()
        self._result_table.setColumnCount(5)
        self._result_table.setHorizontalHeaderLabels(
            ["股票代码", "形态类型", "中文名称", "强度/置信", "检测时间"])
        self._result_table.setStyleSheet(_TBL_SS)
        self._result_table.horizontalHeader().setStretchLastSection(True)
        self._result_table.setSelectionBehavior(
            QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
        self._result_table.setEditTriggers(
            QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
        self._result_table.verticalHeader().setVisible(False)
        v.addWidget(self._result_table, stretch=1)

        return w

    # ── 对外接口 ────────────────────────────────────────────────────

    def show_patterns(self, symbol: str, patterns: list, sequences: list,
                      breakouts: list):
        """
        显示单只股票的形态识别结果。
        patterns:  list of PatternResult
        sequences: list of SequenceResult
        breakouts: list of BreakoutResult
        """
        self._sym_lbl.setText(f"当前股票：{symbol}")

        # 重置计数
        for lbl in self._count_labels.values():
            lbl.setText("0")

        counts = {}
        all_rows = []

        for p in patterns:
            key = p.pattern_type.value if hasattr(p.pattern_type, "value") else str(p.pattern_type)
            counts[key] = counts.get(key, 0) + 1
            all_rows.append((symbol, key, PATTERN_CN.get(key, key),
                             f"{p.strength:.2f}" if hasattr(p, "strength") else "—",
                             str(p.dt)[:10] if hasattr(p, "dt") else "—"))

        for s in sequences:
            key = s.sequence_type.value if hasattr(s.sequence_type, "value") else str(s.sequence_type)
            counts[key] = counts.get(key, 0) + 1
            all_rows.append((symbol, key, PATTERN_CN.get(key, key),
                             f"{s.strength:.2f}" if hasattr(s, "strength") else "—",
                             str(s.dt)[:10] if hasattr(s, "dt") else "—"))

        for b in breakouts:
            key = b.breakout_type.value if hasattr(b.breakout_type, "value") else str(b.breakout_type)
            counts[key] = counts.get(key, 0) + 1
            all_rows.append((symbol, key, PATTERN_CN.get(key, key),
                             f"{b.strength:.2f}" if hasattr(b, "strength") else "—",
                             str(b.dt)[:10] if hasattr(b, "dt") else "—"))

        # 更新计数标签
        for key, cnt in counts.items():
            if key in self._count_labels:
                self._count_labels[key].setText(str(cnt))

        # 填充结果表格
        self._result_table.setRowCount(0)
        for sym, key, cn, strength, dt in all_rows:
            row = self._result_table.rowCount()
            self._result_table.insertRow(row)
            color = PATTERN_COLOR.get(key, _FG)
            for col, text in enumerate([sym, key, cn, strength, dt]):
                item = QtWidgets.QTableWidgetItem(text)
                item.setForeground(QtGui.QColor(color if col in (1, 2) else _FG))
                self._result_table.setItem(row, col, item)

        self._total_lbl.setText(f"共 {len(all_rows)} 条")
        self._result_table.resizeColumnsToContents()

    def append_event(self, symbol: str, event_type: str, dt: str):
        """向结果表格追加一条事件。"""
        row = self._result_table.rowCount()
        self._result_table.insertRow(row)
        color = _GRN if "rise" in event_type or "up" in event_type else _RED
        for col, text in enumerate([symbol, event_type,
                                     PATTERN_CN.get(event_type, event_type),
                                     "—", dt]):
            item = QtWidgets.QTableWidgetItem(text)
            item.setForeground(QtGui.QColor(color if col in (1, 2) else _FG))
            self._result_table.setItem(row, col, item)
        total = self._result_table.rowCount()
        self._total_lbl.setText(f"共 {total} 条")

    def clear(self):
        self._result_table.setRowCount(0)
        self._total_lbl.setText("共 0 条")
        for lbl in self._count_labels.values():
            lbl.setText("0")
        self._sym_lbl.setText("未选择股票")