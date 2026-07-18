"""
strategy_condition/ui/condition_editor.py
条件树可视化编辑器 — QTreeWidget + 参数面板
"""
from __future__ import annotations
from typing import Optional, Tuple

from vnpy.trader.ui import QtWidgets, QtCore, QtGui

from ..constant import (NodeOp, ConditionCategory, ConditionIndicator,
                         SignalType)
from ..core.condition import (
    Condition, condition_from_dict,
    cond_ma_slope, cond_weekly_ma_slope, cond_ma_alignment, cond_new_high_n,
    cond_pullback_pct, cond_pullback_from_high, cond_pullback_to_ma,
    cond_macd_golden, cond_macd_death, cond_rsi_range, cond_return_n_days,
    cond_volume_ratio, cond_volume_price_up, cond_volume_shrink,
    cond_continuous_rise, cond_limit_up_count, cond_big_yang_count,
    cond_kline_strength, cond_atr_ratio, cond_boll_width,
    cond_stop_loss, cond_take_profit, cond_trailing_stop,
    cond_max_hold_days, cond_ma_break_down, cond_macd_death_sell,
)
from ..core.condition_tree import ConditionNode

# ── 颜色 ──────────────────────────────────────────────────────────────
_BG   = "#1e1e2e"; _PAN2 = "#11111b"; _BORD = "#45475a"
_FG   = "#cdd6f4"; _MUT  = "#6c7086"; _BLU  = "#89b4fa"
_GRN  = "#a6e3a1"; _YLW  = "#f9e2af"; _RED  = "#f38ba8"
_MAV  = "#cba6f7"; _PNK  = "#f5c2e7"

# ── 条件元数据表 ──────────────────────────────────────────────────────
# (显示名, factory_fn, 默认参数描述)
_COND_META = {
    ConditionIndicator.MA_SLOPE:          ("MA斜率向上",     cond_ma_slope,          {"ma_period":20,"slope_window":10,"min_slope":0.0}),
    ConditionIndicator.WEEKLY_MA_SLOPE:   ("13周均线向上",   cond_weekly_ma_slope,   {"ma_period":13,"slope_window":5,"min_slope":0.0}),
    ConditionIndicator.MA_ALIGNMENT:      ("均线多头排列",   cond_ma_alignment,      {}),
    ConditionIndicator.NEW_HIGH_N:        ("N日新高突破",    cond_new_high_n,        {"n":20}),
    ConditionIndicator.PULLBACK_PCT:      ("跌幅回调",       cond_pullback_pct,      {"window":10,"min_drop":-8.0,"max_drop":-2.0}),
    ConditionIndicator.PULLBACK_FROM_HIGH:("从高点回撤",     cond_pullback_from_high,{"window":20,"min_drop":-10.0,"max_drop":-2.0}),
    ConditionIndicator.PULLBACK_TO_MA:    ("回踩均线",       cond_pullback_to_ma,    {"ma_period":20,"tol_pct":2.0}),
    ConditionIndicator.MACD_GOLDEN:       ("MACD 金叉",      cond_macd_golden,       {"fast":12,"slow":26,"signal":9}),
    ConditionIndicator.MACD_DEATH:        ("MACD 死叉",      cond_macd_death,        {"fast":12,"slow":26,"signal":9}),
    ConditionIndicator.RSI_RANGE:         ("RSI 范围",       cond_rsi_range,         {"period":14,"min_rsi":30.0,"max_rsi":70.0}),
    ConditionIndicator.RETURN_N_DAYS:     ("N日收益率",      cond_return_n_days,     {"n":10,"min_return":5.0}),
    ConditionIndicator.VOLUME_RATIO:      ("量比过滤",       cond_volume_ratio,      {"period":20,"min_ratio":1.5}),
    ConditionIndicator.VOLUME_PRICE_UP:   ("放量上涨",       cond_volume_price_up,   {"period":20,"min_ratio":1.5,"min_chg":1.0}),
    ConditionIndicator.VOLUME_SHRINK:     ("缩量调整",       cond_volume_shrink,     {"period":20,"max_ratio":0.7}),
    ConditionIndicator.CONTINUOUS_RISE:   ("连续上涨",       cond_continuous_rise,   {"window":10,"min_days":3}),
    ConditionIndicator.LIMIT_UP_COUNT:    ("涨停次数",       cond_limit_up_count,    {"window":20,"min_count":1}),
    ConditionIndicator.BIG_YANG_COUNT:    ("大阳线次数",     cond_big_yang_count,    {"window":20,"min_count":2,"min_pct":3.0}),
    ConditionIndicator.KLINE_STRENGTH:    ("K线综合强度",    cond_kline_strength,    {"min_score":0.4}),
    ConditionIndicator.ATR_RATIO:         ("ATR振幅",        cond_atr_ratio,         {"period":14,"min_ratio":1.0}),
    ConditionIndicator.BOLL_WIDTH:        ("布林带宽度",     cond_boll_width,        {"period":20,"min_width":0.05}),
    ConditionIndicator.STOP_LOSS:         ("固定止损",       cond_stop_loss,         {"pct":8.0}),
    ConditionIndicator.TAKE_PROFIT:       ("固定止盈",       cond_take_profit,       {"pct":15.0}),
    ConditionIndicator.TRAILING_STOP:     ("追踪止盈",       cond_trailing_stop,     {"take_profit":15.0,"trail_drawdown":10.0}),
    ConditionIndicator.MAX_HOLD_DAYS:     ("最大持仓天数",   cond_max_hold_days,     {"days":60}),
    ConditionIndicator.MA_BREAK_DOWN:     ("跌破均线",       cond_ma_break_down,     {"ma_period":20}),
    ConditionIndicator.MACD_DEATH_SELL:   ("MACD死叉卖出",   cond_macd_death_sell,   {"fast":12,"slow":26,"signal":9}),
}


def _spin_ss(bg: str = _PAN2) -> str:
    return (f"QDoubleSpinBox,QSpinBox{{background:{bg};color:{_FG};"
            f"border:1px solid {_BORD};border-radius:4px;"
            f"padding:3px 6px;font-size:13px;}}")


def _lbl(text: str, color: str = _FG, size: int = 13) -> QtWidgets.QLabel:
    w = QtWidgets.QLabel(text)
    w.setStyleSheet(f"color:{color};font-size:{size}px;"
                    f"background:transparent;border:none;")
    return w


class ParamPanel(QtWidgets.QWidget):
    params_changed = QtCore.Signal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._widgets: dict = {}
        self._layout = QtWidgets.QVBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(6)
        self._layout.addWidget(_lbl("选择条件后显示参数", _MUT, 12))

    def load(self, indicator: ConditionIndicator,
             current_params: Optional[dict] = None) -> None:
        self._widgets.clear()
        while self._layout.count():
            item = self._layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        if indicator not in _COND_META:
            self._layout.addWidget(_lbl("无可配置参数", _MUT, 12))
            return
        _, _, default_params = _COND_META[indicator]
        merged = {**default_params, **(current_params or {})}
        ss = _spin_ss()
        for key, val in merged.items():
            self._layout.addWidget(_lbl(self._param_label(key), _MUT, 12))
            if isinstance(val, float):
                sp = QtWidgets.QDoubleSpinBox()
                sp.setRange(-9999.0, 9999.0); sp.setValue(val)
                sp.setDecimals(2); sp.setSingleStep(0.5)
                sp.setStyleSheet(ss); sp.valueChanged.connect(self._emit)
                self._widgets[key] = sp; self._layout.addWidget(sp)
            elif isinstance(val, int):
                sp = QtWidgets.QSpinBox()
                sp.setRange(1, 9999); sp.setValue(val)
                sp.setStyleSheet(ss); sp.valueChanged.connect(self._emit)
                self._widgets[key] = sp; self._layout.addWidget(sp)
            elif isinstance(val, list):
                edit = QtWidgets.QLineEdit(str(val))
                edit.setStyleSheet(
                    f"QLineEdit{{background:{_PAN2};color:{_FG};"
                    f"border:1px solid {_BORD};border-radius:4px;"
                    f"padding:3px 6px;font-size:13px;}}")
                edit.textChanged.connect(self._emit)
                self._widgets[key] = edit; self._layout.addWidget(edit)
        self._layout.addWidget(_lbl("权重 weight", _MUT, 12))
        wsp = QtWidgets.QDoubleSpinBox()
        wsp.setRange(0.1, 5.0); wsp.setValue(1.0)
        wsp.setSingleStep(0.1); wsp.setDecimals(1)
        wsp.setStyleSheet(ss); wsp.valueChanged.connect(self._emit)
        self._widgets["weight"] = wsp; self._layout.addWidget(wsp)
        self._layout.addStretch()

    def get_params(self) -> dict:
        result = {}
        for key, w in self._widgets.items():
            if isinstance(w, QtWidgets.QDoubleSpinBox):
                result[key] = w.value()
            elif isinstance(w, QtWidgets.QSpinBox):
                result[key] = w.value()
            elif isinstance(w, QtWidgets.QLineEdit):
                try: result[key] = eval(w.text())
                except Exception: result[key] = w.text()
        return result

    def _emit(self) -> None:
        self.params_changed.emit(self.get_params())

    @staticmethod
    def _param_label(key: str) -> str:
        return {
            "ma_period":"MA周期","slope_window":"斜率窗口","min_slope":"最小斜率",
            "n":"天数N","window":"窗口(天)","min_drop":"最小跌幅(%)","max_drop":"最大跌幅(%)",
            "tol_pct":"偏差容忍(%)","fast":"快线","slow":"慢线","signal":"信号线",
            "period":"计算周期","min_rsi":"RSI下限","max_rsi":"RSI上限",
            "min_return":"最小收益(%)","min_ratio":"量比下限","max_ratio":"量比上限",
            "min_chg":"涨幅下限(%)","min_days":"最少上涨天数","min_count":"最少次数",
            "min_pct":"最小涨幅(%)","min_score":"最小得分","pct":"触发比例(%)",
            "take_profit":"止盈触发(%)","trail_drawdown":"追踪回撤(%)",
            "days":"最大天数","std_mult":"标准差倍数","min_width":"最小带宽",
            "periods":"均线列表","weight":"权重",
        }.get(key, key)


class ConditionTreeEditor(QtWidgets.QWidget):
    """条件树可视化编辑器（树控件 + 参数面板）"""

    tree_changed = QtCore.Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._tree_data: Optional[ConditionNode] = None
        self._init_ui()

    def _init_ui(self) -> None:
        h = QtWidgets.QHBoxLayout(self)
        h.setContentsMargins(0, 0, 0, 0)
        h.setSpacing(8)

        # 左：树控件
        self._qtree = QtWidgets.QTreeWidget()
        self._qtree.setHeaderHidden(True)
        self._qtree.setStyleSheet(
            f"QTreeWidget{{background:{_PAN2};color:{_FG};"
            f"border:1px solid {_BORD};border-radius:4px;font-size:13px;}}"
            f"QTreeWidget::item{{padding:4px 2px;}}"
            f"QTreeWidget::item:hover{{background:#313244;}}"
            f"QTreeWidget::item:selected{{background:{_BLU};color:#1e1e2e;}}"
            f"QScrollBar:vertical{{background:{_PAN2};width:8px;border:none;}}"
            f"QScrollBar::handle:vertical{{background:{_BORD};border-radius:4px;}}"
        )
        self._qtree.setContextMenuPolicy(
            QtCore.Qt.ContextMenuPolicy.CustomContextMenu)
        self._qtree.customContextMenuRequested.connect(self._show_context_menu)
        self._qtree.currentItemChanged.connect(self._on_item_selected)
        h.addWidget(self._qtree, 3)

        # 右：参数面板
        right = QtWidgets.QWidget()
        right.setStyleSheet(f"background:{_BG};")
        rv = QtWidgets.QVBoxLayout(right)
        rv.setContentsMargins(8, 4, 0, 0)
        rv.setSpacing(4)
        rv.addWidget(_lbl("参数设置", _YLW, 13))
        sep = QtWidgets.QFrame()
        sep.setFrameShape(QtWidgets.QFrame.Shape.HLine)
        sep.setStyleSheet(f"border:none;border-top:1px solid {_BORD};")
        rv.addWidget(sep)

        self._param_panel = ParamPanel()
        scroll = QtWidgets.QScrollArea()
        scroll.setWidget(self._param_panel)
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet(
            f"QScrollArea{{background:{_BG};border:none;}}"
            f"QScrollBar:vertical{{background:{_PAN2};width:8px;border:none;}}"
            f"QScrollBar::handle:vertical{{background:{_BORD};border-radius:4px;}}"
        )
        rv.addWidget(scroll, 1)

        apply_btn = QtWidgets.QPushButton("✓  应用参数")
        apply_btn.setStyleSheet(
            f"QPushButton{{background:{_GRN};color:#1e1e2e;"
            f"border:none;border-radius:4px;padding:6px 14px;"
            f"font-size:13px;font-weight:bold;}}"
            f"QPushButton:hover{{background:#b9f0b2;}}"
        )
        apply_btn.clicked.connect(self._apply_params)
        rv.addWidget(apply_btn)
        h.addWidget(right, 2)

    # ── 公开接口 ──────────────────────────────────────────────────────

    def load_tree(self, node: ConditionNode) -> None:
        self._tree_data = node
        self._qtree.clear()
        root_item = self._build_qtree_item(node)
        self._qtree.addTopLevelItem(root_item)
        self._qtree.expandAll()

    def get_tree(self) -> Optional[ConditionNode]:
        return self._tree_data

    def add_condition(self, indicator: ConditionIndicator) -> None:
        if self._tree_data is None or indicator not in _COND_META:
            return
        _, factory, _ = _COND_META[indicator]
        leaf = ConditionNode.leaf(factory())
        target = self._tree_data
        if target.op != NodeOp.LEAF:
            target.add_child(leaf)
            self.load_tree(self._tree_data)
            self.tree_changed.emit()

    # ── 构建 QTreeWidgetItem ──────────────────────────────────────────

    def _build_qtree_item(self, node: ConditionNode) -> QtWidgets.QTreeWidgetItem:
        if node.op == NodeOp.LEAF:
            cond = node.condition
            name = cond.display_name() if cond else "?"
            cat  = cond.category      if cond else None
            item = QtWidgets.QTreeWidgetItem([f"  {name}"])
            item.setData(0, QtCore.Qt.ItemDataRole.UserRole, node)
            item.setForeground(0, QtGui.QColor(self._cat_color(cat)))
            return item

        op_colors = {NodeOp.AND: _GRN, NodeOp.OR: _YLW, NodeOp.NOT: _RED}
        item = QtWidgets.QTreeWidgetItem([f"[{node.op.value}]  {node.label}"])
        item.setData(0, QtCore.Qt.ItemDataRole.UserRole, node)
        item.setForeground(0, QtGui.QColor(op_colors.get(node.op, _FG)))
        f = QtGui.QFont(); f.setBold(True)
        item.setFont(0, f)
        for child in node.children:
            item.addChild(self._build_qtree_item(child))
        return item

    # ── 右键菜单 ──────────────────────────────────────────────────────

    def _show_context_menu(self, pos) -> None:
        item = self._qtree.itemAt(pos)
        if item is None:
            return
        node: ConditionNode = item.data(0, QtCore.Qt.ItemDataRole.UserRole)
        menu = QtWidgets.QMenu(self)
        menu.setStyleSheet(
            f"QMenu{{background:{_PAN2};color:{_FG};"
            f"border:1px solid {_BORD};font-size:13px;}}"
            f"QMenu::item{{padding:6px 20px;}}"
            f"QMenu::item:selected{{background:{_BLU};color:#1e1e2e;}}"
        )
        if node.op != NodeOp.LEAF:
            menu.addAction("＋ 添加 AND 子树",
                           lambda: self._add_op_node(node, NodeOp.AND))
            menu.addAction("＋ 添加 OR 子树",
                           lambda: self._add_op_node(node, NodeOp.OR))
            menu.addSeparator()
        if item.parent() is not None:
            menu.addAction("🗑  删除此节点",
                           lambda: self._delete_node(node))
        menu.exec(self._qtree.viewport().mapToGlobal(pos))

    def _add_op_node(self, parent: ConditionNode, op: NodeOp) -> None:
        label = "AND 条件组" if op == NodeOp.AND else "OR 条件组"
        parent.add_child(ConditionNode(op=op, label=label))
        self.load_tree(self._tree_data)
        self.tree_changed.emit()

    def _delete_node(self, node: ConditionNode) -> None:
        def _remove(par: ConditionNode) -> bool:
            for i, ch in enumerate(par.children):
                if ch is node:
                    par.children.pop(i)
                    return True
                if _remove(ch):
                    return True
            return False
        if self._tree_data:
            _remove(self._tree_data)
            self.load_tree(self._tree_data)
            self.tree_changed.emit()

    # ── 参数面板联动 ──────────────────────────────────────────────────

    def _on_item_selected(self, current, _prev) -> None:
        if current is None:
            return
        node: ConditionNode = current.data(0, QtCore.Qt.ItemDataRole.UserRole)
        if node and node.op == NodeOp.LEAF and node.condition:
            self._param_panel.load(node.condition.indicator,
                                   node.condition.params)

    def _apply_params(self) -> None:
        item = self._qtree.currentItem()
        if item is None:
            return
        node: ConditionNode = item.data(0, QtCore.Qt.ItemDataRole.UserRole)
        if node and node.op == NodeOp.LEAF and node.condition:
            p = self._param_panel.get_params()
            node.condition.params = {k: v for k, v in p.items() if k != "weight"}
            node.condition.weight = p.get("weight", 1.0)
            self.load_tree(self._tree_data)
            self.tree_changed.emit()

    # ── 工具 ──────────────────────────────────────────────────────────

    @staticmethod
    def _cat_color(cat) -> str:
        if cat is None:
            return _FG
        return {
            ConditionCategory.TREND:      _GRN,
            ConditionCategory.PULLBACK:   _BLU,
            ConditionCategory.MOMENTUM:   _YLW,
            ConditionCategory.VOLUME:     _MAV,
            ConditionCategory.KLINE:      _PNK,
            ConditionCategory.VOLATILITY: "#94e2d5",
            ConditionCategory.EXIT:       _RED,
        }.get(cat, _FG)
