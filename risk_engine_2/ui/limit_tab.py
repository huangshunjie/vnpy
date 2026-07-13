"""
risk_engine_2/ui/limit_tab.py

LimitTab — 限制配置表单 + 实时校验结果（Phase 2 实现）。

上半部：限制规则配置表单（新增 / 修改 / 启用/禁用）
下半部：实时校验结果表格（每次 EVENT_RISK_UPDATE 后刷新）
"""

from __future__ import annotations

from vnpy.trader.ui import QtCore, QtWidgets

from ..constant import LimitType, RiskLevel, RiskAction
from ..model.limit_model import RiskLimit, LimitCheckResult, LimitReport

_DARK_BG  = "#1e1e2e"
_PANEL_BG = "#181825"
_BORDER   = "#45475a"
_FG       = "#cdd6f4"
_MUT      = "#6c7086"
_GRN      = "#a6e3a1"
_YLW      = "#f9e2af"
_RED      = "#f38ba8"
_BLU      = "#89b4fa"

_RESULT_COLS = [
    ("规则 ID",    120),
    ("类型",        80),
    ("标的/行业",   90),
    ("当前值",      80),
    ("预警线",      70),
    ("硬限制",      70),
    ("使用率",      70),
    ("状态",        70),
    ("消息",       260),
]

_LEVEL_COLOR = {
    RiskLevel.NORMAL:   _GRN,
    RiskLevel.WARNING:  _YLW,
    RiskLevel.CRITICAL: "#fab387",
    RiskLevel.BREACH:   _RED,
}

_INPUT_STYLE = (
    "QDoubleSpinBox, QSpinBox, QComboBox, QLineEdit {"
    " background: #313244; color: #cdd6f4; border: 1px solid #45475a;"
    " border-radius: 3px; padding: 2px 6px; font-size: 12px; }"
)


def _item(text: str, color: str = _FG) -> QtWidgets.QTableWidgetItem:
    from vnpy.trader.ui import QtGui
    item = QtWidgets.QTableWidgetItem(str(text))
    item.setTextAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
    item.setForeground(QtGui.QColor(color))
    return item


class LimitTab(QtWidgets.QWidget):
    """限制配置 + 实时校验结果 Tab（Phase 2）。"""

    limit_added   = QtCore.Signal(object)   # RiskLimit
    limit_removed = QtCore.Signal(str)       # limit_id

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._results: list[LimitCheckResult] = []
        self._init_ui()

    def _init_ui(self) -> None:
        root = QtWidgets.QVBoxLayout(self)
        root.setContentsMargins(6, 6, 6, 6)
        root.setSpacing(6)

        # 顶部：汇总状态条
        root.addWidget(self._build_summary_bar())

        # 中部：拆分 左=配置 右=结果
        splitter = QtWidgets.QSplitter(QtCore.Qt.Orientation.Horizontal)
        splitter.addWidget(self._build_config_panel())
        splitter.addWidget(self._build_result_table())
        splitter.setSizes([340, 800])
        root.addWidget(splitter, stretch=1)

    # ------------------------------------------------------------------ #
    #  子区域构建
    # ------------------------------------------------------------------ #

    def _build_summary_bar(self) -> QtWidgets.QWidget:
        bar = QtWidgets.QWidget()
        bar.setFixedHeight(56)
        bar.setStyleSheet(f"background: {_PANEL_BG}; border-radius: 4px;")
        h = QtWidgets.QHBoxLayout(bar)
        h.setContentsMargins(12, 4, 12, 4)
        h.setSpacing(24)

        cards = [
            ("整体风险",   "—",   _FG),
            ("阻断笔数",   "0",   _RED),
            ("预警笔数",   "0",   _YLW),
            ("规则总数",   "—",   _FG),
        ]
        self._summary_lbls: dict[str, QtWidgets.QLabel] = {}
        for name, val, color in cards:
            col = QtWidgets.QVBoxLayout()
            col.setSpacing(0)
            ln = QtWidgets.QLabel(name)
            ln.setStyleSheet(f"color: {_MUT}; font-size: 10px;")
            ln.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
            lv = QtWidgets.QLabel(val)
            lv.setStyleSheet(f"color: {color}; font-size: 14px; font-weight: bold;")
            lv.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
            col.addWidget(ln)
            col.addWidget(lv)
            self._summary_lbls[name] = lv
            h.addLayout(col)
        h.addStretch()
        return bar

    def _build_config_panel(self) -> QtWidgets.QGroupBox:
        box = QtWidgets.QGroupBox("添加/修改限制规则")
        box.setStyleSheet(
            f"QGroupBox {{ color: {_FG}; font-size: 12px; font-weight: bold;"
            f" border: 1px solid {_BORDER}; border-radius: 4px; margin-top: 6px; }}"
            f"QGroupBox::title {{ subcontrol-origin: margin; padding: 0 4px; }}"
        )
        form = QtWidgets.QFormLayout(box)
        form.setContentsMargins(10, 18, 10, 10)
        form.setSpacing(7)
        form.setLabelAlignment(QtCore.Qt.AlignmentFlag.AlignRight)
        lbl_s = f"color: {_MUT}; font-size: 11px;"

        # 规则 ID
        self._edt_id = QtWidgets.QLineEdit()
        self._edt_id.setPlaceholderText("自动生成或自定义")
        self._edt_id.setStyleSheet(_INPUT_STYLE)
        form.addRow(self._lbl("规则ID：", lbl_s), self._edt_id)

        # 类型
        self._cmb_type = QtWidgets.QComboBox()
        for lt in LimitType:
            self._cmb_type.addItem(lt.value, lt)
        self._cmb_type.setStyleSheet(_INPUT_STYLE)
        form.addRow(self._lbl("类型：", lbl_s), self._cmb_type)

        # 标的（单票规则）
        self._edt_symbol = QtWidgets.QLineEdit()
        self._edt_symbol.setPlaceholderText("空=全组合")
        self._edt_symbol.setStyleSheet(_INPUT_STYLE)
        form.addRow(self._lbl("标的：", lbl_s), self._edt_symbol)

        # 行业
        self._edt_industry = QtWidgets.QLineEdit()
        self._edt_industry.setPlaceholderText("空=最大行业")
        self._edt_industry.setStyleSheet(_INPUT_STYLE)
        form.addRow(self._lbl("行业：", lbl_s), self._edt_industry)

        # 预警线
        self._spn_warn = self._dbl(0.0, 100.0, 0.15, 4)
        form.addRow(self._lbl("预警线：", lbl_s), self._spn_warn)

        # 硬限制
        self._spn_hard = self._dbl(0.0, 100.0, 0.25, 4)
        form.addRow(self._lbl("硬限制：", lbl_s), self._spn_hard)

        # 动作
        self._cmb_action = QtWidgets.QComboBox()
        for ra in RiskAction:
            self._cmb_action.addItem(ra.value, ra)
        self._cmb_action.setStyleSheet(_INPUT_STYLE)
        form.addRow(self._lbl("动作：", lbl_s), self._cmb_action)

        # 启用
        self._chk_enabled = QtWidgets.QCheckBox("启用")
        self._chk_enabled.setChecked(True)
        self._chk_enabled.setStyleSheet(f"color: {_FG}; font-size: 12px;")
        form.addRow(self._chk_enabled)

        # 添加按钮
        btn_add = QtWidgets.QPushButton("添加规则")
        btn_add.setStyleSheet(
            f"QPushButton {{ background: {_BLU}; color: #1e1e2e; border-radius: 4px;"
            f" padding: 5px; font-size: 12px; font-weight: bold; }}"
            f"QPushButton:hover {{ background: #b4befe; }}"
        )
        btn_add.clicked.connect(self._on_add_limit)
        form.addRow(btn_add)

        return box

    def _build_result_table(self) -> QtWidgets.QWidget:
        w = QtWidgets.QWidget()
        v = QtWidgets.QVBoxLayout(w)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(2)

        lbl = QtWidgets.QLabel("实时校验结果（每次成交后更新）")
        lbl.setStyleSheet(f"color: {_MUT}; font-size: 10px; padding-left: 4px;")
        v.addWidget(lbl)

        self._tbl = QtWidgets.QTableWidget(0, len(_RESULT_COLS))
        self._tbl.setHorizontalHeaderLabels([c[0] for c in _RESULT_COLS])
        for i, (_, w_) in enumerate(_RESULT_COLS):
            self._tbl.setColumnWidth(i, w_)
        self._tbl.horizontalHeader().setStretchLastSection(True)
        self._tbl.verticalHeader().setVisible(False)
        self._tbl.setEditTriggers(
            QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers
        )
        self._tbl.setSelectionBehavior(
            QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows
        )
        self._tbl.setStyleSheet("font-size: 12px;")
        v.addWidget(self._tbl)
        return w

    # ------------------------------------------------------------------ #
    #  公开接口（供 widget.py 调用）
    # ------------------------------------------------------------------ #

    def update_report(self, report: LimitReport) -> None:
        """刷新校验结果（每次 EVENT_RISK_UPDATE 后调用）。"""
        self._results = list(report.results)
        self._refresh_table()
        self._refresh_summary(report)

    def clear(self) -> None:
        self._tbl.setRowCount(0)

    # ------------------------------------------------------------------ #
    #  内部渲染
    # ------------------------------------------------------------------ #

    def _refresh_table(self) -> None:
        self._tbl.setRowCount(0)
        for res in self._results:
            row = self._tbl.rowCount()
            self._tbl.insertRow(row)
            color = _LEVEL_COLOR.get(res.risk_level, _FG)

            self._tbl.setItem(row, 0, _item(res.limit_id,                   _MUT))
            self._tbl.setItem(row, 1, _item(res.limit_type.value,            _FG))
            scope = res.symbol or "全组合"
            self._tbl.setItem(row, 2, _item(scope,                           _FG))
            self._tbl.setItem(row, 3, _item(f"{res.current_value:.4f}",     color))
            self._tbl.setItem(row, 4, _item(f"{res.warning_threshold:.4f}", _MUT))
            self._tbl.setItem(row, 5, _item(f"{res.hard_limit:.4f}",        _MUT))
            pct = res.utilization_pct
            pct_color = _RED if pct >= 1.0 else (_YLW if pct >= 0.8 else _GRN)
            self._tbl.setItem(row, 6, _item(f"{pct:.1%}",                 pct_color))
            self._tbl.setItem(row, 7, _item(res.status_str,               color))
            self._tbl.setItem(row, 8, _item(res.message,                    _FG))

    def _refresh_summary(self, report: LimitReport) -> None:
        level_color = _LEVEL_COLOR.get(report.overall_level, _FG)
        self._summary_lbls["整体风险"].setText(report.overall_level.value)
        self._summary_lbls["整体风险"].setStyleSheet(
            f"color: {level_color}; font-size: 14px; font-weight: bold;"
        )
        self._summary_lbls["阻断笔数"].setText(str(report.blocked_count))
        self._summary_lbls["预警笔数"].setText(str(report.warning_count))
        self._summary_lbls["规则总数"].setText(str(len(report.results)))

    def _on_add_limit(self) -> None:
        import uuid
        limit_id = self._edt_id.text().strip() or str(uuid.uuid4())[:8]
        limit = RiskLimit(
            limit_id          = limit_id,
            limit_type        = self._cmb_type.currentData(),
            symbol            = self._edt_symbol.text().strip(),
            industry          = self._edt_industry.text().strip(),
            warning_threshold = self._spn_warn.value(),
            hard_limit        = self._spn_hard.value(),
            action            = self._cmb_action.currentData(),
            enabled           = self._chk_enabled.isChecked(),
        )
        self.limit_added.emit(limit)

    # ------------------------------------------------------------------ #
    #  工具
    # ------------------------------------------------------------------ #

    @staticmethod
    def _lbl(text: str, style: str) -> QtWidgets.QLabel:
        l = QtWidgets.QLabel(text)
        l.setStyleSheet(style)
        return l

    @staticmethod
    def _dbl(lo, hi, val, dec) -> QtWidgets.QDoubleSpinBox:
        spn = QtWidgets.QDoubleSpinBox()
        spn.setRange(lo, hi)
        spn.setValue(val)
        spn.setDecimals(dec)
        spn.setStyleSheet(_INPUT_STYLE)
        return spn
