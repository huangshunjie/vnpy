"""
screening/ui/condition_widget.py

Condition Builder Widget — 可视化条件树编辑器（Phase 3）。

支持：
  - 添加 AND / OR / NOT 逻辑组节点
  - 添加条件叶节点（字段 / 运算符 / 值）
  - 删除节点
  - 保存 / 加载条件规则
  - 实时显示条件表达式
"""

from __future__ import annotations
from typing import Optional

from vnpy.trader.ui import QtWidgets, QtCore

from ..constant import (
    ConditionOperator, CompareOperator, ConditionFieldType
)
from ..model.condition import (
    ConditionTree, ConditionGroup, ConditionLeaf, ConditionNode
)

_PANEL  = "#181825"
_PANEL2 = "#11111b"
_BORDER = "#45475a"
_FG     = "#cdd6f4"
_MUT    = "#6c7086"
_GRN    = "#a6e3a1"
_BLU    = "#89b4fa"
_YLW    = "#f9e2af"
_RED    = "#f38ba8"
_ORG    = "#fab387"

_LABEL  = f"color:{_FG};font-size:11px;"
_INPUT  = (f"background:{_PANEL2};color:{_FG};border:1px solid {_BORDER};"
           f"border-radius:3px;padding:3px 6px;font-size:11px;")
_SECTION = f"color:{_GRN};font-size:11px;font-weight:bold;"

# 预定义字段列表（字段名, 字段类型, 描述）
_FIELDS = [
    ("close",         ConditionFieldType.TECHNICAL,   "收盘价"),
    ("ma5",           ConditionFieldType.TECHNICAL,   "MA5"),
    ("ma10",          ConditionFieldType.TECHNICAL,   "MA10"),
    ("ma20",          ConditionFieldType.TECHNICAL,   "MA20"),
    ("ma60",          ConditionFieldType.TECHNICAL,   "MA60"),
    ("ma120",         ConditionFieldType.TECHNICAL,   "MA120"),
    ("ma250",         ConditionFieldType.TECHNICAL,   "MA250"),
    ("rsi14",         ConditionFieldType.TECHNICAL,   "RSI14"),
    ("ema12",         ConditionFieldType.TECHNICAL,   "EMA12"),
    ("ema26",         ConditionFieldType.TECHNICAL,   "EMA26"),
    ("volatility20",  ConditionFieldType.RISK,        "波动率(20日年化)"),
    ("avg_turnover20",ConditionFieldType.CAPITAL,     "日均成交额(20日)"),
    ("turnover",      ConditionFieldType.CAPITAL,     "成交额"),
    ("volume",        ConditionFieldType.CAPITAL,     "成交量"),
    ("roe",           ConditionFieldType.FUNDAMENTAL, "ROE"),
    ("pe",            ConditionFieldType.FUNDAMENTAL, "PE"),
    ("pb",            ConditionFieldType.FUNDAMENTAL, "PB"),
    ("eps",           ConditionFieldType.FUNDAMENTAL, "EPS"),
    ("revenue_growth",ConditionFieldType.FUNDAMENTAL, "营收增速"),
]

_OP_LABELS = {
    CompareOperator.GT:  ">",
    CompareOperator.GTE: ">=",
    CompareOperator.LT:  "<",
    CompareOperator.LTE: "<=",
    CompareOperator.EQ:  "==",
    CompareOperator.NEQ: "!=",
}

_OP_NODE_LABELS = {
    ConditionOperator.AND: "AND",
    ConditionOperator.OR:  "OR",
    ConditionOperator.NOT: "NOT",
}


def _small_btn(text: str, color: str = _MUT) -> QtWidgets.QPushButton:
    b = QtWidgets.QPushButton(text)
    b.setStyleSheet(
        f"QPushButton{{background:#313244;color:{color};"
        f"border:1px solid {_BORDER};border-radius:3px;"
        f"padding:2px 8px;font-size:10px;}}"
        f"QPushButton:hover{{background:#45475a;}}"
    )
    b.setMaximumHeight(22)
    return b


class LeafRow(QtWidgets.QWidget):
    """单行条件叶节点 UI。"""

    deleted = QtCore.Signal(object)

    def __init__(self, leaf: Optional[ConditionLeaf] = None, parent=None) -> None:
        super().__init__(parent)
        self.setStyleSheet(
            f"background:{_PANEL2};border:1px solid {_BORDER};border-radius:3px;"
        )
        h = QtWidgets.QHBoxLayout(self)
        h.setContentsMargins(6, 3, 6, 3)
        h.setSpacing(6)

        self._field_combo = QtWidgets.QComboBox()
        self._field_combo.setStyleSheet(_INPUT)
        self._field_combo.setFixedWidth(140)
        for fname, ftype, fdesc in _FIELDS:
            self._field_combo.addItem(fdesc, (fname, ftype))

        self._op_combo = QtWidgets.QComboBox()
        self._op_combo.setStyleSheet(_INPUT)
        self._op_combo.setFixedWidth(56)
        for op, label in _OP_LABELS.items():
            self._op_combo.addItem(label, op)

        self._value_edit = QtWidgets.QLineEdit()
        self._value_edit.setStyleSheet(_INPUT)
        self._value_edit.setFixedWidth(90)
        self._value_edit.setPlaceholderText("值/字段名")

        self._is_field_chk = QtWidgets.QCheckBox("字段")
        self._is_field_chk.setStyleSheet(f"color:{_MUT};font-size:10px;")

        self._del_btn = _small_btn("✕", _RED)
        self._del_btn.clicked.connect(lambda: self.deleted.emit(self))

        h.addWidget(self._field_combo)
        h.addWidget(self._op_combo)
        h.addWidget(self._value_edit)
        h.addWidget(self._is_field_chk)
        h.addWidget(self._del_btn)
        h.addStretch()

        if leaf:
            self._apply_leaf(leaf)

    def _apply_leaf(self, leaf: ConditionLeaf) -> None:
        for i in range(self._field_combo.count()):
            if self._field_combo.itemData(i)[0] == leaf.field_name:
                self._field_combo.setCurrentIndex(i)
                break
        for i in range(self._op_combo.count()):
            if self._op_combo.itemData(i) == leaf.operator:
                self._op_combo.setCurrentIndex(i)
                break
        self._value_edit.setText(str(leaf.value) if leaf.value is not None else "")
        self._is_field_chk.setChecked(leaf.value_is_field)

    def to_leaf(self) -> ConditionLeaf:
        fname, ftype = self._field_combo.currentData()
        op_raw = self._op_combo.currentData()
        # Qt 有时将枚举 data 退化为其底层值（字符串），强制转回枚举
        if isinstance(op_raw, CompareOperator):
            op = op_raw
        else:
            op = CompareOperator(str(op_raw))
        raw = self._value_edit.text().strip()
        is_field = self._is_field_chk.isChecked()
        value: object = raw if is_field else (float(raw) if raw else 0.0)
        return ConditionLeaf(
            field_name=fname,
            field_type=ftype,
            operator=op,
            value=value,
            value_is_field=is_field,
        )


class ConditionWidget(QtWidgets.QWidget):
    """条件构建面板（Phase 3 完整实现）。"""

    def __init__(self, engine=None, parent=None) -> None:
        super().__init__(parent)
        self._engine = engine
        self._leaf_rows: list[LeafRow] = []
        self._operator = ConditionOperator.AND
        self._init_ui()

    def _sep(self) -> QtWidgets.QFrame:
        s = QtWidgets.QFrame()
        s.setFrameShape(QtWidgets.QFrame.Shape.HLine)
        s.setStyleSheet(f"border:none;border-top:1px solid {_BORDER};")
        return s

    def _section(self, text: str) -> QtWidgets.QLabel:
        lbl = QtWidgets.QLabel(text)
        lbl.setStyleSheet(_SECTION)
        return lbl

    # ── UI 构建 ───────────────────────────────────────────────────────

    def _init_ui(self) -> None:
        self.setStyleSheet(f"background:{_PANEL};")
        root = QtWidgets.QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(8)

        title = QtWidgets.QLabel("Condition Builder  条件构建器")
        title.setStyleSheet(f"color:{_GRN};font-size:13px;font-weight:bold;")
        root.addWidget(title)
        root.addWidget(self._sep())

        # ── 顶层逻辑运算符 ────────────────────────────────────────────
        op_row = QtWidgets.QHBoxLayout()
        op_row.addWidget(QtWidgets.QLabel("条件组合方式：", styleSheet=_LABEL))
        self._op_combo = QtWidgets.QComboBox()
        self._op_combo.setStyleSheet(_INPUT)
        self._op_combo.setFixedWidth(80)
        for op, label in _OP_NODE_LABELS.items():
            self._op_combo.addItem(label, op)
        self._op_combo.currentIndexChanged.connect(self._on_op_changed)
        op_row.addWidget(self._op_combo)
        op_row.addStretch()
        root.addLayout(op_row)

        # ── 条件列表区 ────────────────────────────────────────────────
        root.addWidget(self._section("条件列表"))
        scroll = QtWidgets.QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet(
            f"QScrollArea{{background:{_PANEL2};border:1px solid {_BORDER};"
            f"border-radius:4px;}}"
        )
        self._leaf_container = QtWidgets.QWidget()
        self._leaf_container.setStyleSheet(f"background:{_PANEL2};")
        self._leaf_layout = QtWidgets.QVBoxLayout(self._leaf_container)
        self._leaf_layout.setContentsMargins(6, 6, 6, 6)
        self._leaf_layout.setSpacing(4)
        self._leaf_layout.addStretch()
        scroll.setWidget(self._leaf_container)
        scroll.setMinimumHeight(180)
        root.addWidget(scroll)

        # ── 添加/清空按钮 ─────────────────────────────────────────────
        add_row = QtWidgets.QHBoxLayout()
        btn_add = _small_btn("+ 添加条件", _GRN)
        btn_add.clicked.connect(self._on_add_leaf)
        btn_clear = _small_btn("清空", _RED)
        btn_clear.clicked.connect(self._on_clear)
        add_row.addWidget(btn_add)
        add_row.addWidget(btn_clear)
        add_row.addStretch()
        root.addLayout(add_row)

        root.addWidget(self._sep())

        # ── 表达式预览 ────────────────────────────────────────────────
        root.addWidget(self._section("条件预览"))
        self._expr_label = QtWidgets.QLabel("(无条件)")
        self._expr_label.setStyleSheet(
            f"color:{_YLW};font-size:10px;"
            f"background:{_PANEL2};border:1px solid {_BORDER};"
            f"border-radius:3px;padding:4px 6px;"
        )
        self._expr_label.setWordWrap(True)
        self._expr_label.setMinimumHeight(40)
        root.addWidget(self._expr_label)

        root.addWidget(self._sep())

        # ── 配置名称 + 保存/加载 ──────────────────────────────────────
        root.addWidget(self._section("规则管理"))
        name_row = QtWidgets.QHBoxLayout()
        name_row.addWidget(QtWidgets.QLabel("规则名：", styleSheet=_LABEL))
        self._name_edit = QtWidgets.QLineEdit("default")
        self._name_edit.setStyleSheet(_INPUT)
        name_row.addWidget(self._name_edit, stretch=1)
        root.addLayout(name_row)

        btn_row = QtWidgets.QHBoxLayout()
        btn_save = _small_btn("保存规则", _BLU)
        btn_load = _small_btn("加载规则", _ORG)
        btn_save.clicked.connect(self._on_save)
        btn_load.clicked.connect(self._on_load)
        btn_row.addWidget(btn_save)
        btn_row.addWidget(btn_load)
        btn_row.addStretch()
        root.addLayout(btn_row)

        self._status_label = QtWidgets.QLabel("")
        self._status_label.setStyleSheet(f"color:{_MUT};font-size:10px;")
        root.addWidget(self._status_label)

        root.addStretch()

    # ── 事件回调 ──────────────────────────────────────────────────────

    def _on_op_changed(self, _: int) -> None:
        op_raw = self._op_combo.currentData()
        if isinstance(op_raw, ConditionOperator):
            self._operator = op_raw
        else:
            self._operator = ConditionOperator(str(op_raw))
        self._refresh_expr()

    def _on_add_leaf(self) -> None:
        row = LeafRow()
        row.deleted.connect(self._on_delete_leaf)
        row.destroyed.connect(self._refresh_expr)
        self._leaf_rows.append(row)
        idx = self._leaf_layout.count() - 1
        self._leaf_layout.insertWidget(idx, row)
        self._refresh_expr()

    def _on_delete_leaf(self, row: LeafRow) -> None:
        if row in self._leaf_rows:
            self._leaf_rows.remove(row)
        row.deleteLater()
        self._refresh_expr()

    def _on_clear(self) -> None:
        for row in list(self._leaf_rows):
            row.deleteLater()
        self._leaf_rows.clear()
        self._refresh_expr()

    def _on_save(self) -> None:
        tree = self.get_tree()
        tree.name = self._name_edit.text().strip() or "default"
        if self._engine:
            try:
                self._engine.repository.save_condition_tree(tree)
                if self._engine.condition_engine:
                    self._engine.condition_engine.set_tree(tree)
                self._set_status(f"已保存：{tree.name}", _GRN)
            except Exception as e:
                self._set_status(f"保存失败：{e}", _RED)

    def _on_load(self) -> None:
        name = self._name_edit.text().strip() or "default"
        if self._engine:
            try:
                tree = self._engine.repository.load_condition_tree(name)
                if tree:
                    self._apply_tree(tree)
                    self._set_status(f"已加载：{name}", _GRN)
                else:
                    self._set_status(f"未找到规则：{name}", _YLW)
            except Exception as e:
                self._set_status(f"加载失败：{e}", _RED)

    # ── 数据操作 ──────────────────────────────────────────────────────

    def _apply_tree(self, tree: ConditionTree) -> None:
        """将 ConditionTree 反显到 UI。"""
        self._on_clear()
        if tree.root is None:
            return
        self._name_edit.setText(tree.name)

        root = tree.root
        if isinstance(root, ConditionGroup):
            idx = self._op_combo.findData(root.operator)
            if idx >= 0:
                self._op_combo.setCurrentIndex(idx)
            for child in root.children:
                if isinstance(child, ConditionLeaf):
                    row = LeafRow(leaf=child)
                    row.deleted.connect(self._on_delete_leaf)
                    self._leaf_rows.append(row)
                    self._leaf_layout.insertWidget(
                        self._leaf_layout.count() - 1, row
                    )
        self._refresh_expr()

    def _refresh_expr(self) -> None:
        tree = self.get_tree()
        from ..utils.expression import tree_to_expression
        expr = tree_to_expression(tree)
        self._expr_label.setText(expr or "(无条件)")

    def _set_status(self, msg: str, color: str = _MUT) -> None:
        self._status_label.setText(msg)
        self._status_label.setStyleSheet(f"color:{color};font-size:10px;")

    # ── 公开接口 ──────────────────────────────────────────────────────

    def get_tree(self) -> ConditionTree:
        """读取当前 UI 状态，返回 ConditionTree。"""
        name = self._name_edit.text().strip() or "default"
        group = ConditionGroup(operator=self._operator)
        for row in self._leaf_rows:
            try:
                group.add_child(row.to_leaf())
            except Exception:
                pass
        return ConditionTree(root=group, name=name)

    def get_expression(self) -> str:
        from ..utils.expression import tree_to_expression
        return tree_to_expression(self.get_tree())
