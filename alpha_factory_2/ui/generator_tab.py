"""
alpha_factory_2/ui/generator_tab.py

GeneratorTab — Alpha 生成控制面板（Phase 2）。

布局：
  左侧（260px）：生成参数控制面板
    - Alpha 类型选择
    - 权重采样方法
    - 生成数量 / 负权重开关
    - 因子多选列表
    - 生成按钮
  右侧：Alpha 列表表（已生成的 Alpha）
"""

from __future__ import annotations

from vnpy.trader.ui import QtCore, QtWidgets

from ..constant import AlphaType

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

_TYPE_OPTIONS = [
    ("随机组合  RANDOM",        AlphaType.RANDOM.value),
    ("线性组合  LINEAR_COMBO",  AlphaType.LINEAR_COMBO.value),
    ("加权组合  WEIGHTED",      AlphaType.WEIGHTED.value),
]
_WEIGHT_METHODS = ["dirichlet", "uniform", "random_sign"]

_ALPHA_COLS = [
    ("Alpha ID",   110),
    ("类型 Type",   90),
    ("因子数",      60),
    ("表达式 Expr", 260),
    ("状态 Status", 80),
    ("生成时间",   130),
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


class GeneratorTab(QtWidgets.QWidget):
    """Alpha 生成控制面板（Phase 2）。"""

    def __init__(self, engine=None, parent=None) -> None:
        super().__init__(parent)
        self._engine = engine
        self._init_ui()

    def set_engine(self, engine) -> None:
        self._engine = engine
        self._load_factors()

    # ------------------------------------------------------------------ #
    #  UI 构建
    # ------------------------------------------------------------------ #

    def _init_ui(self) -> None:
        root = QtWidgets.QHBoxLayout(self)
        root.setContentsMargins(6, 6, 6, 6)
        root.setSpacing(6)
        root.addWidget(self._build_control_panel(), stretch=0)
        root.addWidget(self._build_alpha_table(),   stretch=1)

    def _build_control_panel(self) -> QtWidgets.QWidget:
        panel = QtWidgets.QWidget()
        panel.setFixedWidth(264)
        panel.setStyleSheet(
            f"background: {_PANEL_BG}; border-radius: 6px;"
            f" border: 1px solid {_BORDER};"
        )
        v = QtWidgets.QVBoxLayout(panel)
        v.setContentsMargins(12, 12, 12, 12)
        v.setSpacing(8)

        # 标题
        t = QtWidgets.QLabel("Alpha 生成控制  Generator")
        t.setStyleSheet(
            f"color: {_MAV}; font-size: 14px; font-weight: bold; border: none;")
        v.addWidget(t)
        v.addWidget(self._sep())

        # Alpha 类型
        v.addWidget(self._lbl("Alpha 类型  Type"))
        self._cmb_type = QtWidgets.QComboBox()
        for label, val in _TYPE_OPTIONS:
            self._cmb_type.addItem(label, val)
        self._cmb_type.setStyleSheet(self._cmb_style())
        v.addWidget(self._cmb_type)

        # 权重方法
        v.addWidget(self._lbl("权重方法  Weight Method"))
        self._cmb_weight = QtWidgets.QComboBox()
        for m in _WEIGHT_METHODS:
            self._cmb_weight.addItem(m)
        self._cmb_weight.setStyleSheet(self._cmb_style())
        v.addWidget(self._cmb_weight)

        # 生成数量
        row_n = QtWidgets.QHBoxLayout()
        row_n.addWidget(self._lbl("生成数量  Count"))
        self._spin_n = QtWidgets.QSpinBox()
        self._spin_n.setRange(1, 500)
        self._spin_n.setValue(10)
        self._spin_n.setStyleSheet(
            f"background: #11111b; color: {_FG}; border: 1px solid {_BORDER};"
            f" border-radius: 3px; padding: 2px 6px;"
        )
        row_n.addWidget(self._spin_n)
        v.addLayout(row_n)

        # 负权重
        self._chk_neg = QtWidgets.QCheckBox("允许负权重  Allow Negative")
        self._chk_neg.setStyleSheet(f"color: {_MUT}; font-size: 12px; border: none;")
        v.addWidget(self._chk_neg)

        v.addWidget(self._sep())

        # 因子过滤器
        v.addWidget(self._lbl("因子池过滤  Factor Filter"))
        self._txt_filter = QtWidgets.QLineEdit()
        self._txt_filter.setPlaceholderText("输入关键词过滤...")
        self._txt_filter.setStyleSheet(
            f"background: #11111b; color: {_FG}; border: 1px solid {_BORDER};"
            f" border-radius: 3px; padding: 4px 8px; font-size: 13px;"
        )
        self._txt_filter.textChanged.connect(self._on_filter_changed)
        v.addWidget(self._txt_filter)

        # 因子列表
        self._lst_factors = QtWidgets.QListWidget()
        self._lst_factors.setSelectionMode(
            QtWidgets.QAbstractItemView.SelectionMode.MultiSelection)
        self._lst_factors.setStyleSheet(
            f"QListWidget {{ background: #11111b; color: {_BLU};"
            f" font-size: 13px; border: 1px solid {_BORDER}; border-radius: 3px; }}"
            f"QListWidget::item:selected {{ background: {_MAV}33; }}"
        )
        self._lst_factors.setFixedHeight(200)
        v.addWidget(self._lst_factors)

        # 因子选择提示
        self._lbl_sel = QtWidgets.QLabel("选中 0 个（空=全部）")
        self._lbl_sel.setStyleSheet(f"color: {_MUT}; font-size: 11px; border: none;")
        self._lst_factors.itemSelectionChanged.connect(self._on_selection_changed)
        v.addWidget(self._lbl_sel)

        v.addWidget(self._sep())
        v.addStretch()

        # 生成按钮
        btn = QtWidgets.QPushButton("▶ 生成  Generate")
        btn.setStyleSheet(
            f"QPushButton {{ background: {_MAV}; color: #1e1e2e;"
            f" border: 1px solid {_MAV}; border-radius: 4px;"
            f" padding: 8px 0px; font-size: 15px; font-weight: bold; }}"
            f"QPushButton:hover {{ background: {_MAV}44; }}"
        )
        btn.clicked.connect(self._on_generate)
        v.addWidget(btn)

        # 清空按钮
        btn_clr = QtWidgets.QPushButton("清空  Clear")
        btn_clr.setStyleSheet(
            f"QPushButton {{ background: transparent; color: {_MUT};"
            f" border: 1px solid {_BORDER}; border-radius: 4px;"
            f" padding: 4px 0px; font-size: 13px; }}"
        )
        btn_clr.clicked.connect(self._on_clear)
        v.addWidget(btn_clr)

        return panel

    def _build_alpha_table(self) -> QtWidgets.QWidget:
        w = QtWidgets.QWidget()
        w.setStyleSheet(f"background: {_PANEL_BG}; border-radius: 4px;")
        v = QtWidgets.QVBoxLayout(w)
        v.setContentsMargins(8, 6, 8, 6)
        v.setSpacing(3)

        top = QtWidgets.QHBoxLayout()
        lbl = QtWidgets.QLabel("已生成 Alpha  Generated Alphas")
        lbl.setStyleSheet(f"color: {_MUT}; font-size: 12px;")
        top.addWidget(lbl)
        top.addStretch()
        self._lbl_count = QtWidgets.QLabel("0 个")
        self._lbl_count.setStyleSheet(
            f"color: {_MAV}; font-size: 13px; font-weight: bold;")
        top.addWidget(self._lbl_count)
        v.addLayout(top)

        self._tbl = QtWidgets.QTableWidget(0, len(_ALPHA_COLS))
        self._tbl.setHorizontalHeaderLabels([c[0] for c in _ALPHA_COLS])
        for i, (_, w_) in enumerate(_ALPHA_COLS):
            self._tbl.setColumnWidth(i, w_)
        self._tbl.horizontalHeader().setStretchLastSection(True)
        self._tbl.verticalHeader().setVisible(False)
        self._tbl.setEditTriggers(
            QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
        self._tbl.setSelectionBehavior(
            QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
        self._tbl.setStyleSheet("font-size: 13px;")
        v.addWidget(self._tbl, stretch=1)
        return w

    # ------------------------------------------------------------------ #
    #  公开接口
    # ------------------------------------------------------------------ #

    def refresh(self) -> None:
        if self._engine is None:
            return
        alphas = list(self._engine._alphas.values())
        self._render_alphas(alphas)

    # ------------------------------------------------------------------ #
    #  因子列表加载
    # ------------------------------------------------------------------ #

    def _load_factors(self) -> None:
        if self._engine is None:
            return
        factors = self._engine._factor_loader.list_available_factors()
        self._all_factors = factors
        self._populate_factor_list(factors)

    def _populate_factor_list(self, factors: list[str]) -> None:
        self._lst_factors.clear()
        for f in factors:
            self._lst_factors.addItem(f)

    def _on_filter_changed(self, text: str) -> None:
        if not hasattr(self, '_all_factors'):
            return
        filtered = [f for f in self._all_factors
                    if text.upper() in f.upper()]
        self._populate_factor_list(filtered)

    def _on_selection_changed(self) -> None:
        n = len(self._lst_factors.selectedItems())
        self._lbl_sel.setText(f"选中 {n} 个（空=全部）")

    # ------------------------------------------------------------------ #
    #  按钮回调
    # ------------------------------------------------------------------ #

    def _on_generate(self) -> None:
        if self._engine is None:
            QtWidgets.QMessageBox.warning(self, "未初始化", "请先启动 Alpha Factory 引擎。")
            return

        alpha_type    = self._cmb_type.currentData()
        weight_method = self._cmb_weight.currentText()
        n             = self._spin_n.value()
        allow_neg     = self._chk_neg.isChecked()

        selected = [item.text() for item in self._lst_factors.selectedItems()]
        factors  = selected if selected else None

        alphas = self._engine.batch_generate(
            n              = n,
            factors        = factors,
            alpha_type     = alpha_type,
            weight_method  = weight_method,
            allow_negative = allow_neg,
        )
        self._render_alphas(list(self._engine._alphas.values()))

    def _on_clear(self) -> None:
        self._tbl.setRowCount(0)
        self._lbl_count.setText("0 个")

    # ------------------------------------------------------------------ #
    #  渲染
    # ------------------------------------------------------------------ #

    def _render_alphas(self, alphas: list) -> None:
        self._tbl.setRowCount(0)
        for a in reversed(alphas):
            row = self._tbl.rowCount()
            self._tbl.insertRow(row)
            self._tbl.setItem(row, 0, _item(a.alpha_id,         _MAV))
            self._tbl.setItem(row, 1, _item(a.alpha_type.value, _BLU))
            self._tbl.setItem(row, 2, _item(len(a.factors),     _FG))
            self._tbl.setItem(row, 3, _item_left(a.expression,  _MUT))
            self._tbl.setItem(row, 4, _item(a.status.value,     _GRN))
            self._tbl.setItem(row, 5, _item(str(a.created_at)[:19], _MUT))
        self._lbl_count.setText(f"{len(alphas)} 个")

    # ------------------------------------------------------------------ #
    #  样式工具
    # ------------------------------------------------------------------ #

    def _lbl(self, text: str) -> QtWidgets.QLabel:
        l = QtWidgets.QLabel(text)
        l.setStyleSheet(f"color: {_MUT}; font-size: 12px; border: none;")
        return l

    def _sep(self) -> QtWidgets.QFrame:
        s = QtWidgets.QFrame()
        s.setFrameShape(QtWidgets.QFrame.Shape.HLine)
        s.setStyleSheet(f"border: none; border-top: 1px solid {_BORDER};")
        return s

    def _cmb_style(self) -> str:
        return (
            f"QComboBox {{ background: #11111b; color: {_FG};"
            f" border: 1px solid {_BORDER}; border-radius: 3px;"
            f" padding: 3px 8px; font-size: 13px; }}"
            f"QComboBox::drop-down {{ border: none; }}"
            f"QComboBox QAbstractItemView {{ background: #11111b;"
            f" color: {_FG}; border: 1px solid {_BORDER}; }}"
        )
