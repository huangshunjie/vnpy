"""
research_validation/ui/walkforward_tab.py

WalkForwardTab — Walk Forward Analysis 结果展示（Phase 2 实现）。

顶部：跨窗口汇总 KPI 卡片（avg test IC / IR / 过拟合评分 / 稳健性判断）
中部：逐窗口结果表格（Train IC / Test IC / 衰减率 / Sharpe）
底部：ASCII IC 趋势图（Train vs Test）
"""

from __future__ import annotations

from vnpy.trader.ui import QtCore, QtWidgets

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

_TABLE_COLS = [
    ("窗口",        55),
    ("训练起",       90),
    ("训练止",       90),
    ("测试起",       90),
    ("测试止",       90),
    ("Train IC",    80),
    ("Test IC",     80),
    ("IC 衰减",     80),
    ("Train Sharpe", 90),
    ("Test Sharpe",  90),
]


def _item(text: str, color: str = _FG) -> QtWidgets.QTableWidgetItem:
    from vnpy.trader.ui import QtGui
    it = QtWidgets.QTableWidgetItem(str(text))
    it.setTextAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
    it.setForeground(QtGui.QColor(color))
    return it


class WalkForwardTab(QtWidgets.QWidget):
    """Walk Forward Analysis 结果展示 Tab（Phase 2）。"""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._results  = []
        self._summary  = None
        self._init_ui()

    def _init_ui(self) -> None:
        root = QtWidgets.QVBoxLayout(self)
        root.setContentsMargins(6, 6, 6, 6)
        root.setSpacing(6)

        root.addWidget(self._build_kpi_bar())

        splitter = QtWidgets.QSplitter(QtCore.Qt.Orientation.Vertical)
        splitter.addWidget(self._build_table())
        splitter.addWidget(self._build_chart_area())
        splitter.setSizes([380, 200])
        root.addWidget(splitter, stretch=1)

    # ------------------------------------------------------------------ #
    #  子区域构建
    # ------------------------------------------------------------------ #

    def _build_kpi_bar(self) -> QtWidgets.QWidget:
        bar = QtWidgets.QWidget()
        bar.setFixedHeight(72)
        bar.setStyleSheet(f"background: {_PANEL_BG}; border-radius: 4px;")
        h = QtWidgets.QHBoxLayout(bar)
        h.setContentsMargins(14, 6, 14, 6)
        h.setSpacing(28)

        kpis = [
            ("窗口数",         "—", _FG),
            ("avg Train IC",   "—", _FG),
            ("avg Test IC",    "—", _BLU),
            ("IC IR (Test)",   "—", _BLU),
            ("IC t-stat",      "—", _FG),
            ("Test 胜率",      "—", _FG),
            ("过拟合评分",     "—", _YLW),
            ("稳健性判断",     "待验证", _MUT),
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
                f"color: {color}; font-size: 12px; font-weight: bold;"
            )
            lv.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
            col.addWidget(ln)
            col.addWidget(lv)
            self._kpi[name] = lv
            h.addLayout(col)
        h.addStretch()
        return bar

    def _build_table(self) -> QtWidgets.QWidget:
        w = QtWidgets.QWidget()
        v = QtWidgets.QVBoxLayout(w)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(3)

        lbl = QtWidgets.QLabel("逐窗口验证结果")
        lbl.setStyleSheet(f"color: {_MUT}; font-size: 10px; padding-left: 4px;")
        v.addWidget(lbl)

        self._tbl = QtWidgets.QTableWidget(0, len(_TABLE_COLS))
        self._tbl.setHorizontalHeaderLabels([c[0] for c in _TABLE_COLS])
        for i, (_, w_) in enumerate(_TABLE_COLS):
            self._tbl.setColumnWidth(i, w_)
        self._tbl.horizontalHeader().setStretchLastSection(True)
        self._tbl.verticalHeader().setVisible(False)
        self._tbl.setEditTriggers(
            QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers
        )
        self._tbl.setStyleSheet("font-size: 12px;")
        v.addWidget(self._tbl)
        return w

    def _build_chart_area(self) -> QtWidgets.QWidget:
        w = QtWidgets.QWidget()
        w.setStyleSheet(f"background: {_PANEL_BG}; border-radius: 4px;")
        v = QtWidgets.QVBoxLayout(w)
        v.setContentsMargins(8, 6, 8, 6)

        lbl = QtWidgets.QLabel("IC 趋势图（Train ▓ vs Test ░）")
        lbl.setStyleSheet(f"color: {_MUT}; font-size: 10px;")
        v.addWidget(lbl)

        self._txt_chart = QtWidgets.QTextEdit()
        self._txt_chart.setReadOnly(True)
        self._txt_chart.setStyleSheet(
            f"QTextEdit {{ background: #11111b; color: {_FG};"
            f" font-size: 11px; font-family: monospace;"
            f" border: 1px solid {_BORDER}; border-radius: 3px; }}"
        )
        v.addWidget(self._txt_chart)
        return w

    # ------------------------------------------------------------------ #
    #  公开接口
    # ------------------------------------------------------------------ #

    def update_results(self, results: list, summary) -> None:
        """接收 WalkForwardResult 列表 + WalkForwardSummary 并刷新 UI。"""
        self._results = results
        self._summary = summary
        self._update_kpi(summary)
        self._update_table(results)
        self._update_chart(results)

    def clear(self) -> None:
        self._results.clear()
        self._summary = None
        for lbl in self._kpi.values():
            lbl.setText("—")
        self._tbl.setRowCount(0)
        self._txt_chart.clear()

    # ------------------------------------------------------------------ #
    #  内部渲染
    # ------------------------------------------------------------------ #

    def _update_kpi(self, s) -> None:
        if s is None:
            return
        ic_color  = _GRN if s.avg_test_ic > 0.02 else (
                    _YLW if s.avg_test_ic > 0 else _RED)
        ir_color  = _GRN if s.test_ic_ir > 0.3 else (
                    _YLW if s.test_ic_ir > 0 else _RED)
        of_color  = _RED if s.overfit_score >= 40 else (
                    _YLW if s.overfit_score >= 20 else _GRN)
        vd_color  = _GRN if s.is_robust else (
                    _RED if s.avg_test_ic <= 0 else _YLW)

        self._kpi["窗口数"      ].setText(str(s.n_windows))
        self._kpi["avg Train IC"].setText(f"{s.avg_train_ic:.4f}")
        self._kpi["avg Test IC" ].setText(f"{s.avg_test_ic:.4f}")
        self._kpi["avg Test IC" ].setStyleSheet(
            f"color: {ic_color}; font-size: 12px; font-weight: bold;"
        )
        self._kpi["IC IR (Test)"].setText(f"{s.test_ic_ir:.3f}")
        self._kpi["IC IR (Test)"].setStyleSheet(
            f"color: {ir_color}; font-size: 12px; font-weight: bold;"
        )
        self._kpi["IC t-stat"   ].setText(f"{s.test_ic_t_stat:.2f}")
        self._kpi["Test 胜率"   ].setText(f"{s.test_win_rate:.1%}")
        self._kpi["过拟合评分"  ].setText(f"{s.overfit_score:.1f}")
        self._kpi["过拟合评分"  ].setStyleSheet(
            f"color: {of_color}; font-size: 12px; font-weight: bold;"
        )
        self._kpi["稳健性判断"  ].setText(
            "PASS" if s.is_robust else ("FAIL" if s.avg_test_ic <= 0 else "WARN")
        )
        self._kpi["稳健性判断"  ].setStyleSheet(
            f"color: {vd_color}; font-size: 12px; font-weight: bold;"
        )

    def _update_table(self, results: list) -> None:
        self._tbl.setRowCount(0)
        for r in results:
            row = self._tbl.rowCount()
            self._tbl.insertRow(row)

            ic_color    = _GRN if r.test_ic > 0 else _RED
            decay_color = _GRN if r.ic_decay < 0.2 else (
                          _YLW if r.ic_decay < 0.5 else _RED)

            self._tbl.setItem(row, 0, _item(str(r.window_idx),                        _MUT))
            self._tbl.setItem(row, 1, _item(str(r.train_start)[:10],                  _MUT))
            self._tbl.setItem(row, 2, _item(str(r.train_end)[:10],                    _MUT))
            self._tbl.setItem(row, 3, _item(str(r.test_start)[:10],                   _MUT))
            self._tbl.setItem(row, 4, _item(str(r.test_end)[:10],                     _MUT))
            self._tbl.setItem(row, 5, _item(f"{r.train_ic:.4f}",                      _FG))
            self._tbl.setItem(row, 6, _item(f"{r.test_ic:.4f}",                 ic_color))
            self._tbl.setItem(row, 7, _item(f"{r.ic_decay:.2%}",           decay_color))
            self._tbl.setItem(row, 8, _item(f"{r.train_sharpe:.3f}",                  _FG))
            self._tbl.setItem(row, 9, _item(f"{r.test_sharpe:.3f}",             ic_color))

    def _update_chart(self, results: list) -> None:
        """ASCII 双行 IC 趋势图（Train 上 / Test 下）。"""
        if not results:
            self._txt_chart.setText("暂无数据。")
            return

        train_ics = [r.train_ic for r in results]
        test_ics  = [r.test_ic  for r in results]

        height = 6
        all_vals = train_ics + test_ics
        max_v  = max(abs(v) for v in all_vals) or 1.0

        def _bar(val: float, ch: str) -> str:
            l = int(abs(val) / max_v * 16)
            sign = "+" if val >= 0 else "-"
            return f"{sign}{ch * l:<16}"

        lines = ["  Window  Train IC ▓             Test IC ░", "  " + "─" * 52]
        for i, r in enumerate(results):
            train_bar = _bar(r.train_ic, "▓")
            test_bar  = _bar(r.test_ic,  "░")
            lines.append(
                f"  [{i:02d}]     {train_bar}  {r.train_ic:+.4f}"
                f"   {test_bar}  {r.test_ic:+.4f}"
            )
        lines.append("  " + "─" * 52)
        self._txt_chart.setText("\n".join(lines))
