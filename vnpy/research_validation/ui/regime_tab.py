"""
research_validation/ui/regime_tab.py

RegimeTab — 市场状态识别结果展示（Phase 3 实现）。

顶部：状态分布 KPI 卡片（Bull/Bear/Sideways 占比）
中部左：各状态 IC 对比表格
中部右：ASCII 条形图（IC 可视化）
底部：状态时间轴（滚动文本，按期显示状态序列）
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
_PNK      = "#f5c2e7"

_REGIME_COLOR = {
    "BULL":     _GRN,
    "BEAR":     _RED,
    "SIDEWAYS": _YLW,
    "UNKNOWN":  _MUT,
}
_REGIME_CHAR = {
    "BULL":     "▲",
    "BEAR":     "▼",
    "SIDEWAYS": "─",
    "UNKNOWN":  "?",
}

_TABLE_COLS = [
    ("市场状态",    80),
    ("样本数",      60),
    ("IC 均值",     80),
    ("IC 标准差",   80),
    ("IC IR",       70),
    ("IC t-stat",   80),
    ("IC 胜率",     70),
    ("显著性",      60),
]


def _item(text: str, color: str = _FG) -> QtWidgets.QTableWidgetItem:
    from vnpy.trader.ui import QtGui
    it = QtWidgets.QTableWidgetItem(str(text))
    it.setTextAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
    it.setForeground(QtGui.QColor(color))
    return it


class RegimeTab(QtWidgets.QWidget):
    """市场状态识别结果展示 Tab（Phase 3）。"""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._summary = None
        self._init_ui()

    def _init_ui(self) -> None:
        root = QtWidgets.QVBoxLayout(self)
        root.setContentsMargins(6, 6, 6, 6)
        root.setSpacing(6)

        root.addWidget(self._build_kpi_bar())

        mid = QtWidgets.QSplitter(QtCore.Qt.Orientation.Horizontal)
        mid.addWidget(self._build_table_panel())
        mid.addWidget(self._build_chart_panel())
        mid.setSizes([520, 380])
        root.addWidget(mid, stretch=1)

        root.addWidget(self._build_timeline_bar())

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
            ("Bull 占比",        "—",  _GRN),
            ("Bear 占比",        "—",  _RED),
            ("Sideways 占比",    "—",  _YLW),
            ("Bull IC",          "—",  _GRN),
            ("Bear IC",          "—",  _RED),
            ("Sideways IC",      "—",  _YLW),
            ("跨状态一致性",     "待验证", _MUT),
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

        lbl = QtWidgets.QLabel("各市场状态因子 IC 统计")
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

    def _build_chart_panel(self) -> QtWidgets.QWidget:
        w = QtWidgets.QWidget()
        w.setStyleSheet(f"background: {_PANEL_BG}; border-radius: 4px;")
        v = QtWidgets.QVBoxLayout(w)
        v.setContentsMargins(8, 6, 8, 6)
        v.setSpacing(3)

        lbl = QtWidgets.QLabel("IC 对比图（Bull ▲  Bear ▼  Sideways ─）")
        lbl.setStyleSheet(f"color: {_MUT}; font-size: 10px;")
        v.addWidget(lbl)

        self._txt_chart = QtWidgets.QTextEdit()
        self._txt_chart.setReadOnly(True)
        self._txt_chart.setStyleSheet(
            f"QTextEdit {{ background: #11111b; color: {_FG};"
            f" font-size: 11px; font-family: monospace;"
            f" border: 1px solid {_BORDER}; border-radius: 3px; }}"
        )
        v.addWidget(self._txt_chart, stretch=1)
        return w

    def _build_timeline_bar(self) -> QtWidgets.QWidget:
        w = QtWidgets.QWidget()
        w.setFixedHeight(90)
        w.setStyleSheet(f"background: {_PANEL_BG}; border-radius: 4px;")
        v = QtWidgets.QVBoxLayout(w)
        v.setContentsMargins(8, 4, 8, 4)
        v.setSpacing(2)

        lbl = QtWidgets.QLabel("市场状态时间轴（▲=Bull  ▼=Bear  ─=Sideways  ?=Unknown）")
        lbl.setStyleSheet(f"color: {_MUT}; font-size: 10px;")
        v.addWidget(lbl)

        self._txt_timeline = QtWidgets.QTextEdit()
        self._txt_timeline.setReadOnly(True)
        self._txt_timeline.setStyleSheet(
            f"QTextEdit {{ background: #11111b; color: {_FG};"
            f" font-size: 10px; font-family: monospace;"
            f" border: 1px solid {_BORDER}; border-radius: 3px; }}"
        )
        v.addWidget(self._txt_timeline)
        return w

    # ------------------------------------------------------------------ #
    #  公开接口
    # ------------------------------------------------------------------ #

    def update_summary(self, summary) -> None:
        """接收 RegimeSummary 并刷新 UI。"""
        self._summary = summary
        self._update_kpi(summary)
        self._update_table(summary)
        self._update_chart(summary)
        self._update_timeline(summary)

    def clear(self) -> None:
        self._summary = None
        for lbl in self._kpi.values():
            lbl.setText("—")
        self._tbl.setRowCount(0)
        self._txt_chart.clear()
        self._txt_timeline.clear()

    # ------------------------------------------------------------------ #
    #  内部渲染
    # ------------------------------------------------------------------ #

    def _update_kpi(self, s) -> None:
        self._kpi["Bull 占比"    ].setText(f"{s.bull_pct:.1%}")
        self._kpi["Bear 占比"    ].setText(f"{s.bear_pct:.1%}")
        self._kpi["Sideways 占比"].setText(f"{s.sideways_pct:.1%}")

        def _ic_label(r) -> str:
            return f"{r.ic_mean:+.4f}" if r and r.sample_count > 0 else "—"

        self._kpi["Bull IC"    ].setText(_ic_label(s.bull_result))
        self._kpi["Bear IC"    ].setText(_ic_label(s.bear_result))
        self._kpi["Sideways IC"].setText(_ic_label(s.sideways_result))

        # 跨状态一致性：三个状态 IC 均值同号（或显著）
        valid = [r for r in s.all_results if r.sample_count >= 5]
        if not valid:
            consistency = "无数据"
            c_color = _MUT
        else:
            pos_count = sum(1 for r in valid if r.ic_mean > 0)
            if pos_count == len(valid):
                consistency = "全正向"
                c_color = _GRN
            elif pos_count == 0:
                consistency = "全负向"
                c_color = _RED
            else:
                consistency = f"{pos_count}/{len(valid)} 正向"
                c_color = _YLW

        self._kpi["跨状态一致性"].setText(consistency)
        self._kpi["跨状态一致性"].setStyleSheet(
            f"color: {c_color}; font-size: 12px; font-weight: bold;"
        )

    def _update_table(self, s) -> None:
        self._tbl.setRowCount(0)
        for r in s.all_results:
            if r.sample_count == 0:
                continue
            row = self._tbl.rowCount()
            self._tbl.insertRow(row)

            label  = r.regime.value.upper()
            color  = _REGIME_COLOR.get(label, _FG)
            ic_col = _GRN if r.ic_mean > 0 else _RED
            sig    = "★" if r.is_significant else " "

            self._tbl.setItem(row, 0, _item(label,              color))
            self._tbl.setItem(row, 1, _item(str(r.sample_count), _MUT))
            self._tbl.setItem(row, 2, _item(f"{r.ic_mean:+.4f}", ic_col))
            self._tbl.setItem(row, 3, _item(f"{r.ic_std:.4f}",   _FG))
            self._tbl.setItem(row, 4, _item(f"{r.ic_ir:.3f}",    _FG))
            self._tbl.setItem(row, 5, _item(f"{r.ic_t_stat:.2f}", _FG))
            self._tbl.setItem(row, 6, _item(f"{r.win_rate:.1%}", _FG))
            self._tbl.setItem(row, 7, _item(sig,
                _GRN if r.is_significant else _MUT))

    def _update_chart(self, s) -> None:
        """ASCII 水平条形图：各状态 IC 可视化。"""
        results = [r for r in s.all_results if r.sample_count > 0]
        if not results:
            self._txt_chart.setText("暂无数据。")
            return

        max_ic = max(abs(r.ic_mean) for r in results) or 1.0
        bar_w  = 28

        lines = [
            "  状态       IC 均值 条形图（|<——|  0  |——>|）",
            "  " + "─" * 56,
        ]
        for r in results:
            label   = r.regime.value.upper()
            color_c = _REGIME_COLOR.get(label, _FG)
            ch      = _REGIME_CHAR.get(label, "?")
            frac    = r.ic_mean / max_ic
            bar_len = int(abs(frac) * bar_w)
            if r.ic_mean >= 0:
                bar = " " * bar_w + "|" + ch * bar_len
            else:
                bar = " " * (bar_w - bar_len) + ch * bar_len + "|"

            sig_marker = " *" if r.is_significant else "  "
            lines.append(
                f"  {label:8s}  {r.ic_mean:+.4f}{sig_marker}  {bar}"
            )

        lines.append("  " + "─" * 56)
        lines.append("  (* = t-stat > 1.96，5% 显著)")

        best = s.best_regime
        if best:
            lines.append(
                f"  最佳状态：{best.label}  IC={best.ic_mean:+.4f}"
                f"  IR={best.ic_ir:.3f}  n={best.sample_count}"
            )
        self._txt_chart.setText("\n".join(lines))

    def _update_timeline(self, s) -> None:
        """将状态标签序列渲染为文本时间轴（每行 60 期）。"""
        labels = s.regime_labels
        if not labels:
            self._txt_timeline.setText("暂无状态标注。")
            return

        row_w  = 60
        chunks = []
        for i in range(0, len(labels), row_w):
            batch = labels[i : i + row_w]
            chars = "".join(
                _REGIME_CHAR.get(lb.regime.value.upper(), "?")
                for lb in batch
            )
            start_date = str(batch[0].date)[:10]
            end_date   = str(batch[-1].date)[:10]
            chunks.append(f"  {start_date}  {chars}  {end_date}")

        self._txt_timeline.setText("\n".join(chunks))
