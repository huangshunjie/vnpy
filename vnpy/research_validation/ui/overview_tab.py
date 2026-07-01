"""
research_validation/ui/overview_tab.py

OverviewTab — 验证总览仪表盘（Phase 5 实现）。
"""

from __future__ import annotations

from vnpy.trader.ui import QtCore, QtWidgets

_PANEL_BG = "#181825"
_BORDER   = "#45475a"
_FG       = "#cdd6f4"
_MUT      = "#6c7086"
_GRN      = "#a6e3a1"
_YLW      = "#f9e2af"
_RED      = "#f38ba8"
_BLU      = "#89b4fa"


class OverviewTab(QtWidgets.QWidget):
    """验证总览仪表盘（Phase 5）。"""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._result = None
        self._init_ui()

    def _init_ui(self) -> None:
        root = QtWidgets.QVBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(8)
        root.addWidget(self._build_alpha_verdict())
        root.addWidget(self._build_score_grid())
        mid = QtWidgets.QSplitter(QtCore.Qt.Orientation.Horizontal)
        mid.addWidget(self._build_module_table())
        mid.addWidget(self._build_summary_text())
        mid.setSizes([360, 540])
        root.addWidget(mid, stretch=1)

    def _build_alpha_verdict(self) -> QtWidgets.QWidget:
        bar = QtWidgets.QWidget()
        bar.setFixedHeight(64)
        bar.setStyleSheet(f"background: {_PANEL_BG}; border-radius: 6px;")
        h = QtWidgets.QHBoxLayout(bar)
        h.setContentsMargins(20, 8, 20, 8)
        self._lbl_alpha = QtWidgets.QLabel("Alpha 真实性  —  待验证")
        self._lbl_alpha.setStyleSheet(
            f"color: {_MUT}; font-size: 20px; font-weight: bold;"
        )
        h.addWidget(self._lbl_alpha)
        h.addStretch()
        self._lbl_overall = QtWidgets.QLabel("")
        self._lbl_overall.setStyleSheet(f"color: {_MUT}; font-size: 14px; font-weight: bold;")
        h.addWidget(self._lbl_overall)
        return bar

    def _build_score_grid(self) -> QtWidgets.QWidget:
        w = QtWidgets.QWidget()
        w.setFixedHeight(72)
        w.setStyleSheet(f"background: {_PANEL_BG}; border-radius: 4px;")
        h = QtWidgets.QHBoxLayout(w)
        h.setContentsMargins(14, 6, 14, 6)
        h.setSpacing(20)
        kpis = [
            ("综合评分",      "—", _BLU),
            ("Walk Forward", "—", _FG),
            ("OOS IC",       "—", _FG),
            ("Regime",       "—", _FG),
            ("稳定性",        "—", _FG),
            ("偏差检测",      "—", _FG),
            ("过拟合比率",    "—", _YLW),
            ("IC 半衰期",    "—", _YLW),
        ]
        self._kpi: dict[str, QtWidgets.QLabel] = {}
        for name, val, color in kpis:
            col = QtWidgets.QVBoxLayout()
            col.setSpacing(1)
            ln = QtWidgets.QLabel(name)
            ln.setStyleSheet(f"color: {_MUT}; font-size: 10px;")
            ln.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
            lv = QtWidgets.QLabel(val)
            lv.setStyleSheet(f"color: {color}; font-size: 12px; font-weight: bold;")
            lv.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
            col.addWidget(ln)
            col.addWidget(lv)
            self._kpi[name] = lv
            h.addLayout(col)
        h.addStretch()
        return w

    def _build_module_table(self) -> QtWidgets.QWidget:
        w = QtWidgets.QWidget()
        w.setStyleSheet(f"background: {_PANEL_BG}; border-radius: 4px;")
        v = QtWidgets.QVBoxLayout(w)
        v.setContentsMargins(10, 8, 10, 8)
        v.setSpacing(4)
        lbl = QtWidgets.QLabel("各模块详情")
        lbl.setStyleSheet(f"color: {_MUT}; font-size: 10px;")
        v.addWidget(lbl)
        self._tbl = QtWidgets.QTableWidget(5, 3)
        self._tbl.setHorizontalHeaderLabels(["模块", "关键指标", "状态"])
        self._tbl.verticalHeader().setVisible(False)
        self._tbl.setEditTriggers(
            QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers
        )
        self._tbl.setColumnWidth(0, 100)
        self._tbl.setColumnWidth(1, 160)
        self._tbl.horizontalHeader().setStretchLastSection(True)
        self._tbl.setStyleSheet("font-size: 12px;")
        from vnpy.trader.ui import QtGui
        rows = ["Walk Forward","OOS Testing","Regime Detection",
                "Stability Testing","Bias Detection"]
        for i, r in enumerate(rows):
            it = QtWidgets.QTableWidgetItem(r)
            it.setForeground(QtGui.QColor(_MUT))
            self._tbl.setItem(i, 0, it)
            self._tbl.setItem(i, 1, QtWidgets.QTableWidgetItem("—"))
            self._tbl.setItem(i, 2, QtWidgets.QTableWidgetItem("—"))
        v.addWidget(self._tbl, stretch=1)
        return w

    def _build_summary_text(self) -> QtWidgets.QWidget:
        w = QtWidgets.QWidget()
        w.setStyleSheet(f"background: {_PANEL_BG}; border-radius: 4px;")
        v = QtWidgets.QVBoxLayout(w)
        v.setContentsMargins(10, 8, 10, 8)
        v.setSpacing(3)
        lbl = QtWidgets.QLabel("验证摘要")
        lbl.setStyleSheet(f"color: {_MUT}; font-size: 10px;")
        v.addWidget(lbl)
        self._txt = QtWidgets.QTextEdit()
        self._txt.setReadOnly(True)
        self._txt.setStyleSheet(
            f"QTextEdit {{ background: #11111b; color: {_FG};"
            f" font-size: 11px; font-family: monospace;"
            f" border: 1px solid {_BORDER}; border-radius: 3px; }}"
        )
        v.addWidget(self._txt, stretch=1)
        return w

    # ------------------------------------------------------------------ #
    #  公开接口
    # ------------------------------------------------------------------ #

    def update_result(self, result) -> None:
        self._result = result
        self._update_verdict(result)
        self._update_kpis(result)
        self._update_table(result)
        self._update_summary(result)

    def clear(self) -> None:
        self._result = None
        self._lbl_alpha.setText("Alpha 真实性  —  待验证")
        self._lbl_alpha.setStyleSheet(
            f"color: {_MUT}; font-size: 20px; font-weight: bold;"
        )
        self._lbl_overall.setText("")
        for lbl in self._kpi.values():
            lbl.setText("—")
        for row in range(self._tbl.rowCount()):
            self._tbl.setItem(row, 1, QtWidgets.QTableWidgetItem("—"))
            self._tbl.setItem(row, 2, QtWidgets.QTableWidgetItem("—"))
        self._txt.clear()

    # ------------------------------------------------------------------ #
    #  内部渲染
    # ------------------------------------------------------------------ #

    def _update_verdict(self, r) -> None:
        score   = getattr(r, "overall_score", 0.0)
        is_real = getattr(r, "is_real_alpha", False)
        if is_real:
            text, color = "Alpha 真实性  PASS  —  真实 Alpha", _GRN
        elif score >= 40:
            text, color = "Alpha 真实性  WARN  —  可疑，需进一步验证", _YLW
        else:
            text, color = "Alpha 真实性  FAIL  —  Alpha 无效或数据质量差", _RED
        self._lbl_alpha.setText(text)
        self._lbl_alpha.setStyleSheet(
            f"color: {color}; font-size: 18px; font-weight: bold;"
        )
        sc = _GRN if score >= 70 else (_YLW if score >= 50 else _RED)
        self._lbl_overall.setText(f"综合评分  {score:.1f} / 100")
        self._lbl_overall.setStyleSheet(
            f"color: {sc}; font-size: 14px; font-weight: bold;"
        )

    def _update_kpis(self, r) -> None:
        score = getattr(r, "overall_score", 0.0)
        sc = _GRN if score >= 70 else (_YLW if score >= 50 else _RED)
        self._kpi["综合评分"].setText(f"{score:.1f}")
        self._kpi["综合评分"].setStyleSheet(
            f"color: {sc}; font-size: 12px; font-weight: bold;"
        )
        wf = getattr(r, "wf_summary", None)
        if wf:
            c = _GRN if wf.avg_test_ic > 0.02 else (_YLW if wf.avg_test_ic > 0 else _RED)
            self._kpi["Walk Forward"].setText(f"IC={wf.avg_test_ic:+.3f}")
            self._kpi["Walk Forward"].setStyleSheet(
                f"color: {c}; font-size: 12px; font-weight: bold;"
            )
        oos = getattr(r, "oos_result", None)
        if oos:
            c = _GRN if oos.oos_ic > 0.02 else (_YLW if oos.oos_ic > 0 else _RED)
            self._kpi["OOS IC"].setText(f"{oos.oos_ic:+.3f}")
            self._kpi["OOS IC"].setStyleSheet(
                f"color: {c}; font-size: 12px; font-weight: bold;"
            )
            of = oos.overfit_ratio
            of_str = "inf" if of == float("inf") else f"{of:.1f}x"
            of_c = _GRN if (of != float("inf") and of <= 1.5) else (
                   _YLW if (of != float("inf") and of <= 3.0) else _RED)
            self._kpi["过拟合比率"].setText(of_str)
            self._kpi["过拟合比率"].setStyleSheet(
                f"color: {of_c}; font-size: 12px; font-weight: bold;"
            )
        rs = getattr(r, "regime_summary", None)
        if rs:
            valid = [x for x in rs.all_results if x.sample_count >= 5]
            pos   = sum(1 for x in valid if x.ic_mean > 0)
            rc    = _GRN if pos == len(valid) else (_YLW if pos > 0 else _RED)
            self._kpi["Regime"].setText(f"{pos}/{len(valid)} pos")
            self._kpi["Regime"].setStyleSheet(
                f"color: {rc}; font-size: 12px; font-weight: bold;"
            )
        stab = getattr(r, "stability_summary", None)
        if stab:
            sc2 = _GRN if stab.stability_score >= 60 else (
                  _YLW if stab.stability_score >= 40 else _RED)
            self._kpi["稳定性"].setText(stab.stability_level)
            self._kpi["稳定性"].setStyleSheet(
                f"color: {sc2}; font-size: 12px; font-weight: bold;"
            )
            hl_c = _GRN if stab.ic_decay_halflife >= 5 else (
                   _YLW if stab.ic_decay_halflife >= 2 else _RED)
            self._kpi["IC 半衰期"].setText(f"{stab.ic_decay_halflife:.1f}期")
            self._kpi["IC 半衰期"].setStyleSheet(
                f"color: {hl_c}; font-size: 12px; font-weight: bold;"
            )
        bias = getattr(r, "bias_summary", None)
        if bias:
            bc = _GRN if bias.passed else _RED
            self._kpi["偏差检测"].setText("PASS" if bias.passed else f"FAIL({bias.n_critical})")
            self._kpi["偏差检测"].setStyleSheet(
                f"color: {bc}; font-size: 12px; font-weight: bold;"
            )

    def _update_table(self, r) -> None:
        from vnpy.trader.ui import QtGui

        def _set(row, metric, status, c=_FG):
            self._tbl.setItem(row, 1, QtWidgets.QTableWidgetItem(str(metric)))
            it = QtWidgets.QTableWidgetItem(str(status))
            it.setForeground(QtGui.QColor(c))
            self._tbl.setItem(row, 2, it)

        wf = getattr(r, "wf_summary", None)
        if wf:
            c = _GRN if wf.is_robust else _YLW
            _set(0, f"test_IC={wf.avg_test_ic:+.4f}  IR={wf.test_ic_ir:.3f}",
                 "PASS" if wf.is_robust else "WARN", c)
        oos = getattr(r, "oos_result", None)
        if oos:
            of = oos.overfit_ratio
            ok = oos.oos_ic > 0.01 and of != float("inf") and of <= 3.0
            _set(1, f"OOS_IC={oos.oos_ic:+.4f}  of={of if of==float('inf') else f'{of:.2f}x'}",
                 "PASS" if ok else "FAIL", _GRN if ok else _RED)
        rs = getattr(r, "regime_summary", None)
        if rs:
            valid = [x for x in rs.all_results if x.sample_count >= 5]
            pos = sum(1 for x in valid if x.ic_mean > 0)
            _set(2, f"B={rs.bull_pct:.0%} Ba={rs.bear_pct:.0%} S={rs.sideways_pct:.0%}",
                 f"{pos}/{len(valid)} pos", _GRN if pos == len(valid) else _YLW)
        stab = getattr(r, "stability_summary", None)
        if stab:
            _set(3, f"{stab.stability_level}  hl={stab.ic_decay_halflife:.1f}期",
                 f"score={stab.stability_score:.1f}",
                 _GRN if stab.stability_score >= 60 else _YLW)
        bias = getattr(r, "bias_summary", None)
        if bias:
            _set(4, f"Critical={bias.n_critical}  Total={bias.n_total}",
                 "PASS" if bias.passed else "FAIL",
                 _GRN if bias.passed else _RED)

    def _update_summary(self, r) -> None:
        score   = getattr(r, "overall_score", 0.0)
        is_real = getattr(r, "is_real_alpha", False)
        factor  = getattr(r, "factor_name", "—")
        ts      = str(getattr(r, "computed_at", "—"))[:19]
        lines   = [
            f"  因子名称  : {factor}",
            f"  计算时间  : {ts}",
            f"  综合评分  : {score:.1f} / 100",
            f"  Alpha 判断: {'真实 Alpha' if is_real else '可疑 / 无效'}",
            "",
        ]
        wf = getattr(r, "wf_summary", None)
        if wf:
            lines += [
                f"  [Walk Forward]  windows={wf.n_windows}",
                f"    avg_test_IC={wf.avg_test_ic:+.4f}  IR={wf.test_ic_ir:.3f}"
                f"  overfit={wf.overfit_score:.1f}",
                f"    {wf.verdict}",
                "",
            ]
        oos = getattr(r, "oos_result", None)
        if oos:
            of = oos.overfit_ratio
            of_str = "inf" if of == float("inf") else f"{of:.2f}x"
            lines += [
                f"  [OOS Testing]",
                f"    IS_IC={oos.is_ic:+.4f}  OOS_IC={oos.oos_ic:+.4f}",
                f"    IS_Sharpe={oos.is_sharpe:.3f}  OOS_Sharpe={oos.oos_sharpe:.3f}",
                f"    overfit_ratio={of_str}",
                "",
            ]
        stab = getattr(r, "stability_summary", None)
        if stab:
            lines += [
                f"  [Stability]  {stab.stability_level}  score={stab.stability_score:.1f}",
                f"    IC={stab.overall_ic_mean:+.4f}  IR={stab.overall_ic_ir:.3f}"
                f"  win={stab.overall_win_rate:.1%}",
                f"    halflife={stab.ic_decay_halflife:.1f}期  lag1_AC={stab.lag1_autocorr:+.3f}",
                "",
            ]
        bias = getattr(r, "bias_summary", None)
        if bias:
            lines += [
                f"  [Bias Detection]  {'PASS' if bias.passed else 'FAIL'}"
                f"  score={bias.bias_score:.1f}",
                f"    Critical={bias.n_critical}  Total={bias.n_total}",
                f"    look_ahead={bias.lookahead_count}"
                f"  leakage={bias.leakage_count}"
                f"  survivorship={'Y' if bias.survivorship_risk else 'N'}",
                "",
            ]
        self._txt.setText("\n".join(lines))
