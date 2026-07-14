"""
market_behavior/ui/factor_view.py  —  行为因子视图 Tab（完整实现）
"""
from __future__ import annotations
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
_RED   = "#f38ba8"
_MAV   = "#cba6f7"
_ORG   = "#fab387"

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

FACTOR_META = [
    ("rise_days",        "上涨天数",      _GRN,  "近期上涨天数占比，越高越强"),
    ("fall_days",        "下跌天数",      _RED,  "近期下跌天数占比，越低越强"),
    ("limit_up_count",   "涨停次数",      _BLU,  "近期涨停次数，强势信号"),
    ("limit_down_count", "跌停次数",      _RED,  "近期跌停次数，弱势信号"),
    ("big_yang_count",   "大阳线次数",    _YLW,  "近期大阳线次数，放量上涨"),
    ("long_upper_count", "长上影次数",    _ORG,  "近期长上影K线，压力信号"),
    ("breakout_count",   "突破次数",      _MAV,  "近期创新高/突破均线次数"),
    ("volatility",       "波动强度",      _ORG,  "近期平均振幅，越高越活跃"),
    ("kline_strength",   "综合强度",      _BLU,  "综合评分 0~1，越高越强"),
]

LABEL_COLOR = {
    "trend_strong":    _GRN,
    "continuous_rise": _GRN,
    "breakout":        _BLU,
    "consolidation":   _YLW,
    "reversal":        _ORG,
    "high_volatility": _ORG,
    "limit_dense":     _MAV,
    "trend_weak":      _RED,
}


class FactorCard(QtWidgets.QWidget):
    """单个因子卡片：名称 + 数值 + 进度条 + 说明。"""

    def __init__(self, key: str, name: str, color: str, desc: str, parent=None):
        super().__init__(parent)
        self._key   = key
        self._color = color
        self.setStyleSheet(
            f"background:{_PANEL};border:1px solid {color};"
            f"border-radius:6px;")
        self.setMinimumHeight(90)

        v = QtWidgets.QVBoxLayout(self)
        v.setContentsMargins(10, 8, 10, 8)
        v.setSpacing(4)

        # 名称 + 数值 同行
        top = QtWidgets.QHBoxLayout()
        self._name_lbl = _lbl(name, color, 14, True)
        top.addWidget(self._name_lbl)
        top.addStretch()
        self._val_lbl = _lbl("—", _FG, 14, True)
        top.addWidget(self._val_lbl)
        v.addLayout(top)

        # 进度条
        self._bar = QtWidgets.QProgressBar()
        self._bar.setRange(0, 100)
        self._bar.setValue(0)
        self._bar.setFixedHeight(6)
        self._bar.setTextVisible(False)
        self._bar.setStyleSheet(
            f"QProgressBar{{background:{_PAN2};border:none;border-radius:3px;}}"
            f"QProgressBar::chunk{{background:{color};border-radius:3px;}}")
        v.addWidget(self._bar)

        # 描述
        v.addWidget(_lbl(desc, _MUT, 14))

    def update_value(self, norm_val: float, raw_val: float):
        """norm_val 0~1，raw_val 原始值。"""
        self._bar.setValue(int(norm_val * 100))
        # 显示格式：百分比或整数或小数
        key = self._key
        if key in ("rise_days", "fall_days"):
            self._val_lbl.setText(f"{raw_val*100:.0f}%")
        elif key in ("limit_up_count", "limit_down_count",
                     "big_yang_count", "long_upper_count"):
            self._val_lbl.setText(f"{int(raw_val)} 次")
        elif key == "volatility":
            self._val_lbl.setText(f"{raw_val:.2f}%")
        elif key == "kline_strength":
            self._val_lbl.setText(f"{raw_val:.3f}")
        else:
            self._val_lbl.setText(f"{raw_val:.2f}")

    def reset(self):
        self._bar.setValue(0)
        self._val_lbl.setText("—")


class FactorViewTab(QtWidgets.QWidget):
    """
    行为因子视图 Tab。
    上半部：9个因子卡片（3×3网格）
    下半部：标签列表 + 全市场分布表格
    """

    def __init__(self, engine=None, parent=None):
        super().__init__(parent)
        self._engine  = engine
        self._cards   = {}
        self._init_ui()

    def _init_ui(self):
        self.setStyleSheet(f"background:{_BG};")
        root = QtWidgets.QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(12)

        # 标题行
        title_row = QtWidgets.QHBoxLayout()
        title_row.addWidget(_lbl("行为因子视图  Factor View", _MAV, 15, True))
        title_row.addStretch()
        self._sym_label = _lbl("未选择股票", _MUT, 14)
        title_row.addWidget(self._sym_label)
        root.addLayout(title_row)

        root.addWidget(_hline())

        # 9个因子卡片（3列）
        grid = QtWidgets.QGridLayout()
        grid.setSpacing(10)
        for i, (key, name, color, desc) in enumerate(FACTOR_META):
            card = FactorCard(key, name, color, desc)
            self._cards[key] = card
            grid.addWidget(card, i // 3, i % 3)
        root.addLayout(grid)

        root.addWidget(_hline())

        # 下半部：左=标签，右=最近分析记录
        bottom = QtWidgets.QHBoxLayout()
        bottom.setSpacing(12)
        bottom.addWidget(self._build_label_panel(), stretch=1)
        bottom.addWidget(self._build_history_panel(), stretch=2)
        root.addLayout(bottom, stretch=1)

    def _build_label_panel(self) -> QtWidgets.QWidget:
        w = QtWidgets.QWidget()
        w.setStyleSheet(
            f"background:{_PANEL};border:1px solid {_BORD};border-radius:6px;")
        v = QtWidgets.QVBoxLayout(w)
        v.setContentsMargins(14, 12, 14, 12)
        v.setSpacing(8)
        v.addWidget(_lbl("行为标签  Labels", _GRN, 14, True))
        v.addWidget(_hline())

        self._label_container = QtWidgets.QWidget()
        self._label_container.setStyleSheet(f"background:transparent;")
        self._label_flow = QtWidgets.QVBoxLayout(self._label_container)
        self._label_flow.setContentsMargins(0, 0, 0, 0)
        self._label_flow.setSpacing(6)
        self._label_flow.addStretch()

        scroll = QtWidgets.QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet(f"QScrollArea{{border:none;background:{_PANEL};}}")
        scroll.setWidget(self._label_container)
        v.addWidget(scroll, stretch=1)

        v.addWidget(_hline())
        self._label_hint = _lbl("运行选股后自动更新", _MUT, 14)
        v.addWidget(self._label_hint)
        return w

    def _build_history_panel(self) -> QtWidgets.QWidget:
        w = QtWidgets.QWidget()
        w.setStyleSheet(
            f"background:{_PANEL};border:1px solid {_BORD};border-radius:6px;")
        v = QtWidgets.QVBoxLayout(w)
        v.setContentsMargins(14, 12, 14, 12)
        v.setSpacing(8)
        v.addWidget(_lbl("扫描记录  Scan History（近期结果）", _BLU, 14, True))
        v.addWidget(_hline())

        self._history_table = QtWidgets.QTableWidget()
        self._history_table.setColumnCount(6)
        self._history_table.setHorizontalHeaderLabels(
            ["代码", "综合强度", "上涨%", "突破次数", "涨停", "标签"])
        self._history_table.setStyleSheet(
            f"QTableWidget{{background:{_PAN2};color:{_FG};"
            f"border:none;gridline-color:{_BORD};font-size:14px;}}"
            f"QTableWidget::item{{padding:4px 6px;}}"
            f"QTableWidget::item:selected{{background:{_BLU};color:#1e1e2e;}}"
            f"QHeaderView::section{{background:{_PANEL};color:{_MUT};"
            f"border:none;border-bottom:1px solid {_BORD};padding:4px;font-size:14px;}}")
        self._history_table.horizontalHeader().setStretchLastSection(True)
        self._history_table.setSelectionBehavior(
            QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
        self._history_table.setEditTriggers(
            QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
        self._history_table.verticalHeader().setVisible(False)
        v.addWidget(self._history_table, stretch=1)
        return w

    # ── 对外接口 ────────────────────────────────────────────────────

    def show_symbol(self, symbol: str, factors: list, labels: list):
        """显示单只股票的因子和标签。factors 是 FactorResult 列表。"""
        self._sym_label.setText(f"当前股票：{symbol}")

        # 因子卡片
        fmap = {f.factor_type.value: f for f in factors}
        for key, card in self._cards.items():
            if key in fmap:
                f = fmap[key]
                card.update_value(f.norm_value, f.value)
            else:
                card.reset()

        # 标签
        for i in reversed(range(self._label_flow.count() - 1)):
            item = self._label_flow.itemAt(i)
            if item and item.widget():
                item.widget().deleteLater()

        if labels:
            for lt_val, score in labels:
                row = QtWidgets.QHBoxLayout()
                color = LABEL_COLOR.get(lt_val, _FG)
                dot = _lbl("●", color, 14)
                name = _lbl(lt_val, _FG, 14)
                pct  = _lbl(f"{score*100:.0f}%", color, 14, True)
                bar  = QtWidgets.QProgressBar()
                bar.setRange(0, 100)
                bar.setValue(int(score * 100))
                bar.setFixedHeight(5)
                bar.setTextVisible(False)
                bar.setStyleSheet(
                    f"QProgressBar{{background:{_PAN2};border:none;border-radius:2px;}}"
                    f"QProgressBar::chunk{{background:{color};border-radius:2px;}}")
                col = QtWidgets.QWidget()
                col.setStyleSheet("background:transparent;")
                cv  = QtWidgets.QVBoxLayout(col)
                cv.setContentsMargins(0, 0, 0, 0)
                cv.setSpacing(2)
                nr = QtWidgets.QHBoxLayout()
                nr.addWidget(dot)
                nr.addWidget(name)
                nr.addStretch()
                nr.addWidget(pct)
                cv.addLayout(nr)
                cv.addWidget(bar)
                self._label_flow.insertWidget(self._label_flow.count() - 1, col)
        else:
            self._label_flow.insertWidget(
                self._label_flow.count() - 1,
                _lbl("暂无标签", _MUT))

    def append_scan_row(self, sym: str, strength: float, rise_pct: float,
                        breakout: float, limit_up: float, labels: list):
        """向扫描记录表格追加一行。"""
        r = self._history_table.rowCount()
        self._history_table.insertRow(r)

        def _item(text, color=_FG):
            item = QtWidgets.QTableWidgetItem(text)
            item.setForeground(QtGui.QColor(color) if hasattr(QtWidgets, 'QTableWidgetItem') else QtCore.Qt.GlobalColor.white)
            return item

        self._history_table.setItem(r, 0, QtWidgets.QTableWidgetItem(sym))
        self._history_table.setItem(r, 1, QtWidgets.QTableWidgetItem(f"{strength:.3f}"))
        self._history_table.setItem(r, 2, QtWidgets.QTableWidgetItem(f"{rise_pct*100:.0f}%"))
        self._history_table.setItem(r, 3, QtWidgets.QTableWidgetItem(f"{breakout:.1f}"))
        self._history_table.setItem(r, 4, QtWidgets.QTableWidgetItem(f"{int(limit_up)}"))
        self._history_table.setItem(r, 5, QtWidgets.QTableWidgetItem(", ".join(labels)))

    def clear_history(self):
        self._history_table.setRowCount(0)