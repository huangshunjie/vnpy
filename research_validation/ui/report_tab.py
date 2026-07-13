"""research_validation/ui/report_tab.py

ReportTab - 验证报告汇总与导出。

布局：
  顶部工具栏：[导出 CSV] [导出文本] 状态标签
  左侧：综合评分卡 + 各模块汇总表
  右侧：详细文本报告（可滚动）
"""
from __future__ import annotations
import csv
import math
from datetime import datetime

from vnpy.trader.ui import QtCore, QtGui, QtWidgets

_BG       = "#1e1e2e"
_PANEL_BG = "#181825"
_BORDER   = "#45475a"
_FG       = "#cdd6f4"
_MUT      = "#6c7086"
_GRN      = "#a6e3a1"
_YLW      = "#f9e2af"
_RED      = "#f38ba8"
_BLU      = "#89b4fa"


def _c(val: float, lo: float, hi: float) -> str:
    """Green if val>=hi, yellow if >=lo, else red."""
    return _GRN if val >= hi else (_YLW if val >= lo else _RED)


def _pct(v: float) -> str:
    return f"{v:.2%}"

def _f4(v: float) -> str:
    if math.isnan(v):
        return "—"
    return f"{v:+.4f}"

def _f2(v: float) -> str:
    if math.isnan(v):
        return "—"
    return f"{v:.2f}"


class ReportTab(QtWidgets.QWidget):
    """验证报告 Tab - 汇总评分、各模块数据、CSV 导出。"""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._result = None
        self._init_ui()

    # ------------------------------------------------------------------ #

    def _init_ui(self) -> None:
        root = QtWidgets.QVBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(6)
        root.addWidget(self._build_toolbar())
        splitter = QtWidgets.QSplitter(QtCore.Qt.Orientation.Horizontal)
        splitter.addWidget(self._build_left())
        splitter.addWidget(self._build_right())
        splitter.setSizes([420, 560])
        root.addWidget(splitter, stretch=1)

    def _build_toolbar(self) -> QtWidgets.QWidget:
        bar = QtWidgets.QWidget()
        h = QtWidgets.QHBoxLayout(bar)
        h.setContentsMargins(0, 0, 0, 0)
        h.setSpacing(8)

        btn_csv = QtWidgets.QPushButton("导出 CSV")
        btn_csv.setFixedHeight(28)
        btn_csv.clicked.connect(self._export_csv)

        btn_txt = QtWidgets.QPushButton("导出文本报告")
        btn_txt.setFixedHeight(28)
        btn_txt.clicked.connect(self._export_txt)

        self._lbl_status = QtWidgets.QLabel("暂无验证结果，请先点击「开始验证」")
        self._lbl_status.setStyleSheet(f"color: {_MUT}; font-size: 11px;")

        h.addWidget(btn_csv)
        h.addWidget(btn_txt)
        h.addWidget(self._lbl_status)
        h.addStretch()
        return bar

    def _build_left(self) -> QtWidgets.QWidget:
        w = QtWidgets.QWidget()
        w.setStyleSheet(f"background: {_PANEL_BG}; border-radius: 6px;")
        v = QtWidgets.QVBoxLayout(w)
        v.setContentsMargins(10, 10, 10, 10)
        v.setSpacing(8)

        # 评分卡
        v.addWidget(self._build_score_card())

        sep = QtWidgets.QFrame()
        sep.setFrameShape(QtWidgets.QFrame.Shape.HLine)
        sep.setStyleSheet(f"color: {_BORDER};")
        v.addWidget(sep)

        # 各模块汇总表
        lbl = QtWidgets.QLabel("各模块验证结果")
        lbl.setStyleSheet(f"color: {_MUT}; font-size: 10px;")
        v.addWidget(lbl)

        self._tbl = QtWidgets.QTableWidget(5, 3)
        self._tbl.setHorizontalHeaderLabels(["模块", "关键指标", "结论"])
        self._tbl.verticalHeader().setVisible(False)
        self._tbl.setEditTriggers(
            QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers
        )
        self._tbl.setSelectionBehavior(
            QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows
        )
        self._tbl.horizontalHeader().setSectionResizeMode(
            1, QtWidgets.QHeaderView.ResizeMode.Stretch
        )
        self._tbl.setColumnWidth(0, 110)
        self._tbl.setColumnWidth(2, 70)
        self._tbl.setAlternatingRowColors(True)
        self._tbl.setStyleSheet("font-size: 11px;")
        self._tbl.verticalHeader().setDefaultSectionSize(26)

        _MODULES = [
            "滚动验证 Walk Forward",
            "样本外测试 OOS Testing",
            "市场状态 Regime Detection",
            "稳定性测试 Stability Test",
            "偏差检测 Bias Detection",
        ]
        for i, name in enumerate(_MODULES):
            it = QtWidgets.QTableWidgetItem(name)
            it.setForeground(QtGui.QColor(_FG))
            self._tbl.setItem(i, 0, it)
            self._tbl.setItem(i, 1, QtWidgets.QTableWidgetItem("—"))
            self._tbl.setItem(i, 2, QtWidgets.QTableWidgetItem("—"))

        v.addWidget(self._tbl, stretch=1)
        return w

    def _build_score_card(self) -> QtWidgets.QWidget:
        w = QtWidgets.QWidget()
        grid = QtWidgets.QGridLayout(w)
        grid.setSpacing(6)
        grid.setContentsMargins(0, 0, 0, 0)

        self._lbl_verdict = QtWidgets.QLabel("Alpha 真实性 — 待验证")
        self._lbl_verdict.setStyleSheet(
            f"color: {_MUT}; font-size: 15px; font-weight: bold;"
        )
        self._lbl_verdict.setWordWrap(True)
        grid.addWidget(self._lbl_verdict, 0, 0, 1, 4)

        kpi_defs = [
            ("综合评分",   "_kpi_score"),
            ("WF IC",      "_kpi_wf"),
            ("OOS IC",     "_kpi_oos"),
            ("Regime",     "_kpi_reg"),
            ("稳定性",     "_kpi_stab"),
            ("过拟合",     "_kpi_of"),
            ("IC半衰期",   "_kpi_hl"),
            ("偏差",       "_kpi_bias"),
        ]
        for idx, (title, attr) in enumerate(kpi_defs):
            col_w = QtWidgets.QWidget()
            col_w.setStyleSheet(
                f"background: #313244; border-radius: 4px;"
            )
            col_v = QtWidgets.QVBoxLayout(col_w)
            col_v.setContentsMargins(6, 4, 6, 4)
            col_v.setSpacing(1)
            ln = QtWidgets.QLabel(title)
            ln.setStyleSheet(f"color: {_MUT}; font-size: 9px;")
            ln.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
            lv = QtWidgets.QLabel("—")
            lv.setStyleSheet(f"color: {_FG}; font-size: 12px; font-weight: bold;")
            lv.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
            col_v.addWidget(ln)
            col_v.addWidget(lv)
            setattr(self, attr, lv)
            grid.addWidget(col_w, 1 + idx // 4, idx % 4)

        return w

    def _build_right(self) -> QtWidgets.QWidget:
        w = QtWidgets.QWidget()
        w.setStyleSheet(f"background: {_PANEL_BG}; border-radius: 6px;")
        v = QtWidgets.QVBoxLayout(w)
        v.setContentsMargins(10, 10, 10, 10)
        v.setSpacing(4)
        lbl = QtWidgets.QLabel("详细报告")
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

    def update_result(self, result) -> None:
        self._result = result
        self._render_score_card(result)
        self._render_table(result)
        self._render_text(result)
        ts = str(getattr(result, "computed_at", ""))[:19]
        fn = getattr(result, "factor_name", "-")
        self._lbl_status.setText(f"因子：{fn}    验证完成：{ts}")
        self._lbl_status.setStyleSheet(f"color: {_GRN}; font-size: 11px;")

    def clear(self) -> None:
        self._result = None
        self._lbl_verdict.setText("Alpha 真实性 — 待验证")
        self._lbl_verdict.setStyleSheet(
            f"color: {_MUT}; font-size: 15px; font-weight: bold;"
        )
        for attr in ("_kpi_score","_kpi_wf","_kpi_oos","_kpi_reg",
                     "_kpi_stab","_kpi_of","_kpi_hl","_kpi_bias"):
            getattr(self, attr).setText("-")
            getattr(self, attr).setStyleSheet(
                f"color: {_FG}; font-size: 12px; font-weight: bold;"
            )
        for row in range(self._tbl.rowCount()):
            self._tbl.setItem(row, 1, QtWidgets.QTableWidgetItem("-"))
            it = QtWidgets.QTableWidgetItem("-")
            it.setForeground(QtGui.QColor(_MUT))
            self._tbl.setItem(row, 2, it)
        self._txt.clear()
        self._lbl_status.setText("暂无验证结果，请先点击「开始验证」")
        self._lbl_status.setStyleSheet(f"color: {_MUT}; font-size: 11px;")

    def _render_score_card(self, r) -> None:
        score   = getattr(r, "overall_score", 0.0)
        is_real = getattr(r, "is_real_alpha", False)
        if is_real:
            vt, vc = "Alpha 真实性  PASS  真实 Alpha", _GRN
        elif score >= 40:
            vt, vc = "Alpha 真实性  WARN  可疑，建议进一步验证", _YLW
        else:
            vt, vc = "Alpha 真实性  FAIL  无效或数据质量差", _RED
        self._lbl_verdict.setText(vt)
        self._lbl_verdict.setStyleSheet(
            f"color: {vc}; font-size: 15px; font-weight: bold;"
        )
        def _set(attr, text, color):
            lb = getattr(self, attr)
            lb.setText(text)
            lb.setStyleSheet(f"color: {color}; font-size: 12px; font-weight: bold;")
        _set("_kpi_score", f"{score:.1f}", _c(score, 50, 70))
        wf = getattr(r, "wf_summary", None)
        if wf:
            _set("_kpi_wf", f"{wf.avg_test_ic:+.3f}", _c(wf.avg_test_ic, 0, 0.02))
        oos = getattr(r, "oos_result", None)
        if oos:
            _set("_kpi_oos", f"{oos.oos_ic:+.3f}", _c(oos.oos_ic, 0, 0.02))
            of = oos.overfit_ratio
            of_str = "inf" if of == float("inf") else f"{of:.1f}x"
            of_c = _GRN if (of != float("inf") and of <= 1.5) else (
                   _YLW if (of != float("inf") and of <= 3.0) else _RED)
            _set("_kpi_of", of_str, of_c)
        rs = getattr(r, "regime_summary", None)
        if rs:
            valid = [x for x in rs.all_results if x.sample_count >= 5]
            pos = sum(1 for x in valid if x.ic_mean > 0)
            _set("_kpi_reg", f"{pos}/{len(valid)}", _GRN if pos==len(valid) else _YLW)
        stab = getattr(r, "stability_summary", None)
        if stab:
            _set("_kpi_stab", stab.stability_level, _c(stab.stability_score, 40, 60))
            _set("_kpi_hl", f"{stab.ic_decay_halflife:.1f}期", _c(stab.ic_decay_halflife, 2, 5))
        bias = getattr(r, "bias_summary", None)
        if bias:
            bc = _GRN if bias.passed else _RED
            _set("_kpi_bias", "PASS" if bias.passed else f"FAIL({bias.n_critical})", bc)

    def _render_table(self, r) -> None:
        def _row(row, metric, verdict, color):
            self._tbl.setItem(row, 1, QtWidgets.QTableWidgetItem(metric))
            it = QtWidgets.QTableWidgetItem(verdict)
            it.setForeground(QtGui.QColor(color))
            self._tbl.setItem(row, 2, it)
        wf = getattr(r, "wf_summary", None)
        if wf:
            _row(0, f"test_IC={wf.avg_test_ic:+.4f}  IR={wf.test_ic_ir:.3f}  overfit={wf.overfit_score:.1f}",
                 "PASS" if wf.is_robust else "WARN", _GRN if wf.is_robust else _YLW)
        oos = getattr(r, "oos_result", None)
        if oos:
            of = oos.overfit_ratio
            of_s = "inf" if of==float("inf") else f"{of:.2f}x"
            ok = oos.oos_ic > 0.01 and of != float("inf") and of <= 3.0
            _row(1, f"IS={oos.is_ic:+.4f}  OOS={oos.oos_ic:+.4f}  overfit={of_s}",
                 "PASS" if ok else "FAIL", _GRN if ok else _RED)
        rs = getattr(r, "regime_summary", None)
        if rs:
            valid = [x for x in rs.all_results if x.sample_count >= 5]
            pos = sum(1 for x in valid if x.ic_mean > 0)
            _row(2, f"牛={rs.bull_pct:.0%}  熊={rs.bear_pct:.0%}  震荡={rs.sideways_pct:.0%}",
                 f"{pos}/{len(valid)} pos", _GRN if pos==len(valid) else _YLW)
        stab = getattr(r, "stability_summary", None)
        if stab:
            _row(3, f"{stab.stability_level}  IC={stab.overall_ic_mean:+.4f}  hl={stab.ic_decay_halflife:.1f}",
                 f"score={stab.stability_score:.1f}", _GRN if stab.stability_score>=60 else _YLW)
        bias = getattr(r, "bias_summary", None)
        if bias:
            _row(4, f"Critical={bias.n_critical}  look_ahead={bias.lookahead_count}  leakage={bias.leakage_count}",
                 "PASS" if bias.passed else "FAIL", _GRN if bias.passed else _RED)
    def _render_text(self, r) -> None:
        score   = getattr(r, "overall_score", 0.0)
        is_real = getattr(r, "is_real_alpha", False)
        factor  = getattr(r, "factor_name", "-")
        ts      = str(getattr(r, "computed_at", "-"))[:19]
        sep     = "=" * 58
        sep2    = "-" * 40
        lines = [
            sep,
            "  研究验证体系 2.0  验证报告",
            sep,
            f"  因子名称    : {factor}",
            f"  验证时间    : {ts}",
            f"  综合评分    : {score:.1f} / 100",
            f"  Alpha 判断  : {'真实 Alpha' if is_real else '可疑 / 无效'}",
            "",
        ]
        wf = getattr(r, "wf_summary", None)
        if wf:
            lines += [sep2, "  滚动验证 Walk Forward",
                f"  滚动窗口数   : {wf.n_windows}",
                f"  样本内均IC   : {wf.avg_train_ic:+.4f}",
                f"  样本外均IC   : {wf.avg_test_ic:+.4f}",
                f"  样本外IC_IR  : {wf.test_ic_ir:.4f}",
                f"  过拟合评分   : {wf.overfit_score:.1f}",
                f"  结论         : {'稳健' if wf.is_robust else '不稳健'}  {wf.verdict}", ""]
        oos = getattr(r, "oos_result", None)
        if oos:
            of = oos.overfit_ratio
            of_s = "inf" if of == float("inf") else f"{of:.2f}x"
            lines += [sep2, "  样本外测试 OOS Testing",
                f"  样本内 IC    : {oos.is_ic:+.4f}",
                f"  样本外 IC    : {oos.oos_ic:+.4f}",
                f"  样本内Sharpe : {oos.is_sharpe:.4f}",
                f"  样本外Sharpe : {oos.oos_sharpe:.4f}",
                f"  过拟合比率   : {of_s}  (<=1.5x 为佳)", ""]
        rs = getattr(r, "regime_summary", None)
        if rs:
            lines += [sep2, "  市场状态 Regime Detection",
                f"  牛市占比     : {rs.bull_pct:.1%}",
                f"  熊市占比     : {rs.bear_pct:.1%}",
                f"  震荡市占比   : {rs.sideways_pct:.1%}"]
            for x in rs.all_results:
                if x.sample_count >= 5:
                    lines.append(f"  {x.regime.value:<10} IC={x.ic_mean:+.4f}  IR={x.ic_ir:.3f}  n={x.sample_count}")
            lines.append("")
        stab = getattr(r, "stability_summary", None)
        if stab:
            lines += [sep2, "  稳定性测试 Stability Test",
                f"  稳定性等级   : {stab.stability_level}",
                f"  稳定性评分   : {stab.stability_score:.1f}",
                f"  整体IC均值   : {stab.overall_ic_mean:+.4f}",
                f"  整体IC_IR    : {stab.overall_ic_ir:.4f}",
                f"  胜率         : {stab.overall_win_rate:.1%}",
                f"  IC衰减半衰期 : {stab.ic_decay_halflife:.1f} 期",
                f"  Lag-1自相关  : {stab.lag1_autocorr:+.4f}", ""]
        bias = getattr(r, "bias_summary", None)
        if bias:
            lines += [sep2, "  偏差检测 Bias Detection",
                f"  结论         : {'PASS' if bias.passed else 'FAIL'}",
                f"  偏差评分     : {bias.bias_score:.1f}",
                f"  严重偏差数   : {bias.n_critical}",
                f"  前视偏差次数 : {bias.lookahead_count}",
                f"  数据泄漏次数 : {bias.leakage_count}",
                f"  幸存者偏差   : {'有' if bias.survivorship_risk else '无'}"]
            if hasattr(bias, "warnings") and bias.warnings:
                lines.append("  警告详情：")
                for w in bias.warnings:
                    sev = "WARNING" if w.severity == "warning" else "CRITICAL"
                    lines.append(f"    [{sev}] {w.bias_type}: {w.description}")
            lines.append("")
        from datetime import datetime as _dt
        lines += [sep, f"  报告生成时间: {_dt.now().strftime('%Y-%m-%d %H:%M:%S')}", sep]
        self._txt.setPlainText("\n".join(lines))

    def _export_csv(self) -> None:
        if self._result is None:
            QtWidgets.QMessageBox.information(self, "提示", "暂无验证结果可导出")
            return
        r = self._result
        path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, "导出验证结果 CSV", "", "CSV (*.csv)"
        )
        if not path:
            return
        rows = [["指标", "数值", "说明"],
                ["因子名称", getattr(r,"factor_name","-"), ""],
                ["综合评分", f"{getattr(r,'overall_score',0):.1f}", "0~100"],
                ["Alpha判断", "真实" if getattr(r,"is_real_alpha",False) else "可疑/无效", ""]]
        wf = getattr(r, "wf_summary", None)
        if wf:
            rows += [["WF-窗口数", wf.n_windows, ""],
                     ["WF-样本内IC", f"{wf.avg_train_ic:+.4f}", ""],
                     ["WF-样本外IC", f"{wf.avg_test_ic:+.4f}", ""],
                     ["WF-样本外ICIR", f"{wf.test_ic_ir:.4f}", ">=0.5佳"],
                     ["WF-过拟合评分", f"{wf.overfit_score:.1f}", ""]]
        oos = getattr(r, "oos_result", None)
        if oos:
            of = oos.overfit_ratio
            rows += [["OOS-样本内IC", f"{oos.is_ic:+.4f}", ""],
                     ["OOS-样本外IC", f"{oos.oos_ic:+.4f}", ""],
                     ["OOS-过拟合比率", "inf" if of==float("inf") else f"{of:.2f}x", "<=1.5x佳"]]
        stab = getattr(r, "stability_summary", None)
        if stab:
            rows += [["稳定性等级", stab.stability_level, ""],
                     ["稳定性评分", f"{stab.stability_score:.1f}", ">=60佳"],
                     ["IC衰减半衰期", f"{stab.ic_decay_halflife:.1f}", "期"]]
        bias = getattr(r, "bias_summary", None)
        if bias:
            rows += [["偏差检测", "PASS" if bias.passed else "FAIL", ""],
                     ["严重偏差数", bias.n_critical, ""]]
        import csv
        try:
            with open(path, "w", newline="", encoding="utf-8-sig") as f:
                csv.writer(f).writerows(rows)
            QtWidgets.QMessageBox.information(self, "导出成功", f"已保存到：\n{path}")
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "导出失败", str(e))

    def _export_txt(self) -> None:
        if self._result is None:
            QtWidgets.QMessageBox.information(self, "提示", "暂无验证结果可导出")
            return
        path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, "导出文本报告", "", "文本文件 (*.txt)"
        )
        if not path:
            return
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write(self._txt.toPlainText())
            QtWidgets.QMessageBox.information(self, "导出成功", f"已保存到：\n{path}")
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "导出失败", str(e))