"""
risk_engine_2/ui/report_tab.py

ReportTab — 归因报告卡片 + 贡献分解表格（Phase 4 实现）。

顶部：组合级汇总卡片（PnL / Beta / MaxDD / 策略数 / 因子数）
中部：三栏 Tab（策略 / 因子 / 行业）贡献表格
底部：文本归因摘要 + 手动触发归因按钮
"""

from __future__ import annotations

from vnpy.trader.ui import QtCore, QtWidgets

from ..model.risk_model import AttributionResult, RiskContribution

_DARK_BG  = "#1e1e2e"
_PANEL_BG = "#181825"
_BORDER   = "#45475a"
_FG       = "#cdd6f4"
_MUT      = "#6c7086"
_GRN      = "#a6e3a1"
_YLW      = "#f9e2af"
_RED      = "#f38ba8"
_BLU      = "#89b4fa"
_ORG      = "#fab387"

_CONTRIB_COLS = [
    ("来源",        120),
    ("PnL 贡献",     90),
    ("贡献%",        70),
    ("风险贡献%",    80),
    ("权重",         65),
    ("Beta 贡献",    80),
    ("正/负",        55),
]


def _item(text: str, color: str = _FG) -> QtWidgets.QTableWidgetItem:
    from vnpy.trader.ui import QtGui
    item = QtWidgets.QTableWidgetItem(str(text))
    item.setTextAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
    item.setForeground(QtGui.QColor(color))
    return item


class ReportTab(QtWidgets.QWidget):
    """归因报告 Tab（Phase 4）。"""

    attribution_requested = QtCore.Signal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._result: AttributionResult | None = None
        self._init_ui()

    def _init_ui(self) -> None:
        root = QtWidgets.QVBoxLayout(self)
        root.setContentsMargins(6, 6, 6, 6)
        root.setSpacing(6)

        root.addWidget(self._build_kpi_bar())

        mid = QtWidgets.QSplitter(QtCore.Qt.Orientation.Vertical)
        mid.addWidget(self._build_contrib_tabs())
        mid.addWidget(self._build_text_area())
        mid.setSizes([420, 200])
        root.addWidget(mid, stretch=1)

        root.addWidget(self._build_action_bar())

    # ------------------------------------------------------------------ #
    #  子区域构建
    # ------------------------------------------------------------------ #

    def _build_kpi_bar(self) -> QtWidgets.QWidget:
        bar = QtWidgets.QWidget()
        bar.setFixedHeight(72)
        bar.setStyleSheet(f"background: {_PANEL_BG}; border-radius: 4px;")
        h = QtWidgets.QHBoxLayout(bar)
        h.setContentsMargins(12, 6, 12, 6)
        h.setSpacing(24)

        metrics = [
            ("总 PnL",        "—", _FG),
            ("组合 Beta",     "—", _BLU),
            ("最大回撤",      "—", _RED),
            ("最大回撤%",     "—", _RED),
            ("策略数",        "—", _FG),
            ("因子数",        "—", _FG),
            ("行业数",        "—", _FG),
            ("策略可解释%",   "—", _YLW),
        ]
        self._kpi: dict[str, QtWidgets.QLabel] = {}
        for name, val, color in metrics:
            col = QtWidgets.QVBoxLayout()
            col.setSpacing(1)
            ln = QtWidgets.QLabel(name)
            ln.setStyleSheet(f"color: {_MUT}; font-size: 10px;")
            ln.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
            lv = QtWidgets.QLabel(val)
            lv.setStyleSheet(f"color: {color}; font-size: 13px; font-weight: bold;")
            lv.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
            col.addWidget(ln)
            col.addWidget(lv)
            self._kpi[name] = lv
            h.addLayout(col)
        h.addStretch()
        return bar

    def _build_contrib_tabs(self) -> QtWidgets.QTabWidget:
        tabs = QtWidgets.QTabWidget()
        tabs.setStyleSheet(
            f"QTabWidget::pane {{ border: 1px solid {_BORDER}; border-radius: 4px; }}"
            f"QTabBar::tab {{ background: {_PANEL_BG}; color: {_MUT};"
            f" padding: 5px 14px; border-radius: 3px; margin-right: 2px; }}"
            f"QTabBar::tab:selected {{ background: #313244; color: {_FG}; }}"
        )

        self._tbl_strategy = self._make_table()
        self._tbl_factor   = self._make_table()
        self._tbl_industry = self._make_table()

        tabs.addTab(self._tbl_strategy, "策略贡献")
        tabs.addTab(self._tbl_factor,   "因子贡献")
        tabs.addTab(self._tbl_industry, "行业贡献")
        return tabs

    def _build_text_area(self) -> QtWidgets.QWidget:
        w = QtWidgets.QWidget()
        w.setStyleSheet(f"background: {_PANEL_BG}; border-radius: 4px;")
        v = QtWidgets.QVBoxLayout(w)
        v.setContentsMargins(8, 6, 8, 6)

        lbl = QtWidgets.QLabel("归因摘要")
        lbl.setStyleSheet(f"color: {_MUT}; font-size: 10px;")
        v.addWidget(lbl)

        self._txt = QtWidgets.QTextEdit()
        self._txt.setReadOnly(True)
        self._txt.setStyleSheet(
            f"QTextEdit {{ background: #11111b; color: {_FG};"
            f" font-size: 11px; font-family: monospace;"
            f" border: 1px solid {_BORDER}; border-radius: 3px; }}"
        )
        v.addWidget(self._txt)
        return w

    def _build_action_bar(self) -> QtWidgets.QWidget:
        w = QtWidgets.QWidget()
        w.setFixedHeight(42)
        h = QtWidgets.QHBoxLayout(w)
        h.setContentsMargins(0, 4, 0, 4)
        h.setSpacing(8)

        btn = QtWidgets.QPushButton("手动触发归因计算")
        btn.setStyleSheet(
            f"QPushButton {{ background: {_BLU}; color: #1e1e2e; border-radius: 4px;"
            f" padding: 5px 16px; font-size: 12px; font-weight: bold; }}"
            f"QPushButton:hover {{ background: #b4befe; }}"
        )
        btn.clicked.connect(self.attribution_requested.emit)

        self._lbl_last = QtWidgets.QLabel("最近归因：—")
        self._lbl_last.setStyleSheet(f"color: {_MUT}; font-size: 11px;")

        h.addWidget(btn)
        h.addWidget(self._lbl_last)
        h.addStretch()
        return w

    # ------------------------------------------------------------------ #
    #  公开接口
    # ------------------------------------------------------------------ #

    def update_result(self, result: AttributionResult) -> None:
        """刷新归因报告（每次 eAttributionResult 事件后调用）。"""
        self._result = result
        self._update_kpi(result)
        self._update_table(self._tbl_strategy, result.strategy_contribs)
        self._update_table(self._tbl_factor,   result.factor_contribs)
        self._update_table(self._tbl_industry, result.industry_contribs)
        self._txt.setText(result.to_text())
        self._lbl_last.setText(
            f"最近归因：{result.computed_at.strftime('%H:%M:%S')}"
            f"  PnL={result.total_pnl:+.2f}"
        )

    def clear(self) -> None:
        for lbl in self._kpi.values():
            lbl.setText("—")
        for tbl in (self._tbl_strategy, self._tbl_factor, self._tbl_industry):
            tbl.setRowCount(0)
        self._txt.clear()

    # ------------------------------------------------------------------ #
    #  内部渲染
    # ------------------------------------------------------------------ #

    def _update_kpi(self, r: AttributionResult) -> None:
        pnl_color = _GRN if r.total_pnl >= 0 else _RED
        dd_color  = _RED if r.max_drawdown_pct >= 0.10 else (
                    _YLW if r.max_drawdown_pct >= 0.05 else _FG)
        exp_color = _GRN if r.strategy_explained_pct >= 0.8 else (
                    _YLW if r.strategy_explained_pct >= 0.5 else _RED)

        self._kpi["总 PnL"      ].setText(f"{r.total_pnl:+.2f}")
        self._kpi["总 PnL"      ].setStyleSheet(
            f"color: {pnl_color}; font-size: 13px; font-weight: bold;"
        )
        self._kpi["组合 Beta"   ].setText(f"{r.portfolio_beta:.3f}")
        self._kpi["最大回撤"    ].setText(f"{r.max_drawdown:+.2f}")
        self._kpi["最大回撤%"   ].setText(f"{r.max_drawdown_pct:.2%}")
        self._kpi["最大回撤%"   ].setStyleSheet(
            f"color: {dd_color}; font-size: 13px; font-weight: bold;"
        )
        self._kpi["策略数"      ].setText(str(len(r.strategy_contribs)))
        self._kpi["因子数"      ].setText(str(len(r.factor_contribs)))
        self._kpi["行业数"      ].setText(str(len(r.industry_contribs)))
        self._kpi["策略可解释%" ].setText(f"{r.strategy_explained_pct:.1%}")
        self._kpi["策略可解释%" ].setStyleSheet(
            f"color: {exp_color}; font-size: 13px; font-weight: bold;"
        )

    def _update_table(
        self,
        tbl:   QtWidgets.QTableWidget,
        items: list[RiskContribution],
    ) -> None:
        tbl.setRowCount(0)
        for c in items:
            row = tbl.rowCount()
            tbl.insertRow(row)

            pnl_color = _GRN if c.pnl_contrib >= 0 else _RED
            rk_color  = _RED if c.risk_contrib_pct >= 0.3 else (
                         _YLW if c.risk_contrib_pct >= 0.15 else _FG)
            sign_str   = "▲" if c.is_positive else "▼"
            sign_color = _GRN if c.is_positive else _RED

            tbl.setItem(row, 0, _item(c.source_name,              _FG))
            tbl.setItem(row, 1, _item(f"{c.pnl_contrib:+.2f}",  pnl_color))
            tbl.setItem(row, 2, _item(f"{c.pnl_contrib_pct:+.1%}", pnl_color))
            tbl.setItem(row, 3, _item(f"{c.risk_contrib_pct:.1%}", rk_color))
            tbl.setItem(row, 4, _item(f"{c.weight:.2%}",           _MUT))
            tbl.setItem(row, 5, _item(f"{c.beta_contrib:.3f}",     _BLU))
            tbl.setItem(row, 6, _item(sign_str,                  sign_color))

    def _make_table(self) -> QtWidgets.QTableWidget:
        tbl = QtWidgets.QTableWidget(0, len(_CONTRIB_COLS))
        tbl.setHorizontalHeaderLabels([c[0] for c in _CONTRIB_COLS])
        for i, (_, w) in enumerate(_CONTRIB_COLS):
            tbl.setColumnWidth(i, w)
        tbl.horizontalHeader().setStretchLastSection(True)
        tbl.verticalHeader().setVisible(False)
        tbl.setEditTriggers(
            QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers
        )
        tbl.setSelectionBehavior(
            QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows
        )
        tbl.setStyleSheet("font-size: 12px;")
        return tbl
