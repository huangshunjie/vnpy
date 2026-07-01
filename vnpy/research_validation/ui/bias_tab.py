"""
research_validation/ui/bias_tab.py

BiasTab — 偏差检测结果展示（Phase 5 实现）。

顶部：总体通过/失败 + KPI 卡片
中部：警告列表表格
底部：详细报告文本
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

_TABLE_COLS = [
    ("严重性",   70),
    ("类型",     110),
    ("期索引",   60),
    ("描述",     340),
]


def _item(text: str, color: str = _FG) -> QtWidgets.QTableWidgetItem:
    from vnpy.trader.ui import QtGui
    it = QtWidgets.QTableWidgetItem(str(text))
    it.setTextAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
    it.setForeground(QtGui.QColor(color))
    return it


def _item_left(text: str, color: str = _FG) -> QtWidgets.QTableWidgetItem:
    from vnpy.trader.ui import QtGui
    it = QtWidgets.QTableWidgetItem(str(text))
    it.setTextAlignment(
        QtCore.Qt.AlignmentFlag.AlignLeft | QtCore.Qt.AlignmentFlag.AlignVCenter
    )
    it.setForeground(QtGui.QColor(color))
    return it


class BiasTab(QtWidgets.QWidget):
    """偏差检测结果展示 Tab（Phase 5）。"""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._summary = None
        self._init_ui()

    def _init_ui(self) -> None:
        root = QtWidgets.QVBoxLayout(self)
        root.setContentsMargins(6, 6, 6, 6)
        root.setSpacing(6)

        root.addWidget(self._build_verdict_bar())
        root.addWidget(self._build_kpi_bar())

        splitter = QtWidgets.QSplitter(QtCore.Qt.Orientation.Vertical)
        splitter.addWidget(self._build_table_panel())
        splitter.addWidget(self._build_detail_panel())
        splitter.setSizes([300, 200])
        root.addWidget(splitter, stretch=1)

    # ------------------------------------------------------------------ #

    def _build_verdict_bar(self) -> QtWidgets.QWidget:
        bar = QtWidgets.QWidget()
        bar.setFixedHeight(52)
        bar.setStyleSheet(f"background: {_PANEL_BG}; border-radius: 4px;")
        h = QtWidgets.QHBoxLayout(bar)
        h.setContentsMargins(16, 6, 16, 6)

        self._lbl_verdict = QtWidgets.QLabel("偏差检测  —  待运行")
        self._lbl_verdict.setStyleSheet(
            f"color: {_MUT}; font-size: 18px; font-weight: bold;"
        )
        h.addWidget(self._lbl_verdict)
        h.addStretch()

        self._lbl_score_val = QtWidgets.QLabel("")
        self._lbl_score_val.setStyleSheet(
            f"color: {_MUT}; font-size: 13px;"
        )
        h.addWidget(self._lbl_score_val)
        return bar

    def _build_kpi_bar(self) -> QtWidgets.QWidget:
        bar = QtWidgets.QWidget()
        bar.setFixedHeight(66)
        bar.setStyleSheet(f"background: {_PANEL_BG}; border-radius: 4px;")
        h = QtWidgets.QHBoxLayout(bar)
        h.setContentsMargins(14, 6, 14, 6)
        h.setSpacing(24)

        kpis = [
            ("偏差评分",        "—", _YLW),
            ("Critical 警告",  "—", _RED),
            ("Warning 警告",   "—", _YLW),
            ("Look-ahead 违规", "—", _RED),
            ("Data Leakage",   "—", _RED),
            ("Survivorship",   "—", _YLW),
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

    def _build_table_panel(self) -> QtWidgets.QWidget:
        w = QtWidgets.QWidget()
        w.setStyleSheet(f"background: {_PANEL_BG}; border-radius: 4px;")
        v = QtWidgets.QVBoxLayout(w)
        v.setContentsMargins(8, 6, 8, 6)
        v.setSpacing(3)

        lbl = QtWidgets.QLabel("偏差警告列表")
        lbl.setStyleSheet(f"color: {_MUT}; font-size: 10px;")
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
        v.addWidget(self._tbl, stretch=1)
        return w

    def _build_detail_panel(self) -> QtWidgets.QWidget:
        w = QtWidgets.QWidget()
        w.setStyleSheet(f"background: {_PANEL_BG}; border-radius: 4px;")
        v = QtWidgets.QVBoxLayout(w)
        v.setContentsMargins(8, 6, 8, 6)
        v.setSpacing(3)

        lbl = QtWidgets.QLabel("详细报告")
        lbl.setStyleSheet(f"color: {_MUT}; font-size: 10px;")
        v.addWidget(lbl)

        self._txt_detail = QtWidgets.QTextEdit()
        self._txt_detail.setReadOnly(True)
        self._txt_detail.setStyleSheet(
            f"QTextEdit {{ background: #11111b; color: {_FG};"
            f" font-size: 11px; font-family: monospace;"
            f" border: 1px solid {_BORDER}; border-radius: 3px; }}"
        )
        v.addWidget(self._txt_detail, stretch=1)
        return w

    # ------------------------------------------------------------------ #

    def update_summary(self, summary) -> None:
        self._summary = summary
        self._update_verdict(summary)
        self._update_kpi(summary)
        self._update_table(summary)
        self._txt_detail.setText(summary.to_text())

    def set_lookahead_status(self, violations: list[dict]) -> None:
        if not violations:
            self._kpi["Look-ahead 违规"].setText("0")
            self._kpi["Look-ahead 违规"].setStyleSheet(
                f"color: {_GRN}; font-size: 12px; font-weight: bold;"
            )
        else:
            self._kpi["Look-ahead 违规"].setText(str(len(violations)))

    def clear(self) -> None:
        self._summary = None
        self._lbl_verdict.setText("偏差检测  —  待运行")
        self._lbl_verdict.setStyleSheet(
            f"color: {_MUT}; font-size: 18px; font-weight: bold;"
        )
        self._lbl_score_val.setText("")
        for lbl in self._kpi.values():
            lbl.setText("—")
        self._tbl.setRowCount(0)
        self._txt_detail.clear()

    # ------------------------------------------------------------------ #

    def _update_verdict(self, s) -> None:
        if s.passed:
            text  = "偏差检测  PASS  —  未检测到严重偏差"
            color = _GRN
        else:
            text  = "偏差检测  FAIL  —  发现严重偏差，请修正后重新验证"
            color = _RED
        self._lbl_verdict.setText(text)
        self._lbl_verdict.setStyleSheet(
            f"color: {color}; font-size: 16px; font-weight: bold;"
        )
        self._lbl_score_val.setText(
            f"偏差评分 {s.bias_score:.1f}/100（越低越好）"
        )
        score_color = _GRN if s.bias_score < 20 else (
                      _YLW if s.bias_score < 50 else _RED)
        self._lbl_score_val.setStyleSheet(
            f"color: {score_color}; font-size: 13px;"
        )

    def _update_kpi(self, s) -> None:
        score_color = _GRN if s.bias_score < 20 else (
                      _YLW if s.bias_score < 50 else _RED)
        self._kpi["偏差评分"      ].setText(f"{s.bias_score:.1f}")
        self._kpi["偏差评分"      ].setStyleSheet(
            f"color: {score_color}; font-size: 12px; font-weight: bold;"
        )
        self._kpi["Critical 警告" ].setText(str(s.n_critical))
        self._kpi["Critical 警告" ].setStyleSheet(
            f"color: {_RED if s.n_critical > 0 else _GRN};"
            f" font-size: 12px; font-weight: bold;"
        )
        warn_n = s.n_total - s.n_critical
        self._kpi["Warning 警告"  ].setText(str(warn_n))
        self._kpi["Look-ahead 违规"].setText(str(s.lookahead_count))
        self._kpi["Look-ahead 违规"].setStyleSheet(
            f"color: {_RED if s.lookahead_count > 0 else _GRN};"
            f" font-size: 12px; font-weight: bold;"
        )
        self._kpi["Data Leakage"  ].setText(str(s.leakage_count))
        self._kpi["Data Leakage"  ].setStyleSheet(
            f"color: {_RED if s.leakage_count > 0 else _GRN};"
            f" font-size: 12px; font-weight: bold;"
        )
        surv_str = "是" if s.survivorship_risk else "否"
        surv_col = _YLW if s.survivorship_risk else _GRN
        self._kpi["Survivorship"  ].setText(surv_str)
        self._kpi["Survivorship"  ].setStyleSheet(
            f"color: {surv_col}; font-size: 12px; font-weight: bold;"
        )

    def _update_table(self, s) -> None:
        self._tbl.setRowCount(0)
        if not s.warnings:
            self._tbl.insertRow(0)
            self._tbl.setItem(0, 0, _item("—",   _GRN))
            self._tbl.setItem(0, 1, _item("—",   _GRN))
            self._tbl.setItem(0, 2, _item("—",   _MUT))
            self._tbl.setItem(0, 3, _item_left("未检测到偏差问题", _GRN))
            return

        for w in s.warnings:
            row = self._tbl.rowCount()
            self._tbl.insertRow(row)
            sev_color = _RED if w.is_critical else _YLW
            sev_text  = "CRITICAL" if w.is_critical else "WARNING"
            loc_text  = str(w.period) if w.period >= 0 else "—"
            self._tbl.setItem(row, 0, _item(sev_text,   sev_color))
            self._tbl.setItem(row, 1, _item(w.bias_type, _MUT))
            self._tbl.setItem(row, 2, _item(loc_text,    _MUT))
            self._tbl.setItem(row, 3, _item_left(w.description, _FG))
