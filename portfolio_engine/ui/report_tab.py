"""
portfolio_engine/ui/report_tab.py

ReportTab — 报告导出 Tab（Phase 4 实现）。
"""

from __future__ import annotations

import math
from pathlib import Path

from pyqtgraph.Qt import QtCore, QtWidgets

_BG  = "#1e1e2e"
_FG  = "#cdd6f4"
_MUT = "#6c7086"
_ACC = "#4fc3f7"
_POS = "#a6e3a1"
_NEG = "#f38ba8"
_YEL = "#f9e2af"

_CARD_STYLE = "background: #181825; border-radius: 6px; padding: 6px;"


def _item(text: str) -> QtWidgets.QTableWidgetItem:
    item = QtWidgets.QTableWidgetItem(str(text))
    item.setTextAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
    return item


class ReportTab(QtWidgets.QWidget):
    """报告导出 Tab（Phase 4 实现）。"""

    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self._performance    = None
        self._allocation     = None
        self._risk           = None
        self._attribution    = None
        self._rebalance_hist = None
        self._factor_signal  = None
        self._init_ui()

    # ------------------------------------------------------------------ #
    #  UI 构建
    # ------------------------------------------------------------------ #

    def _init_ui(self) -> None:
        root = QtWidgets.QVBoxLayout(self)
        root.setContentsMargins(6, 6, 6, 6)
        root.setSpacing(6)

        root.addWidget(self._build_header())

        self._placeholder = QtWidgets.QLabel("运行分析后将在此显示报告摘要")
        self._placeholder.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self._placeholder.setStyleSheet(f"color: {_MUT}; font-size: 13px;")
        root.addWidget(self._placeholder, stretch=1)

        self._content = QtWidgets.QWidget()
        cv = QtWidgets.QVBoxLayout(self._content)
        cv.setContentsMargins(0, 0, 0, 0)
        cv.setSpacing(6)

        summary_row = QtWidgets.QHBoxLayout()
        summary_row.setSpacing(6)
        summary_row.addWidget(self._build_perf_card(), stretch=1)
        summary_row.addWidget(self._build_factor_card(), stretch=1)
        cv.addLayout(summary_row)

        reb_lbl = QtWidgets.QLabel("最近调仓记录（最新 10 条）")
        reb_lbl.setStyleSheet(f"color: {_MUT}; font-size: 11px; font-weight: bold;")
        cv.addWidget(reb_lbl)
        cv.addWidget(self._build_rebalance_table())
        cv.addWidget(self._build_export_bar())

        self._content.hide()
        root.addWidget(self._content, stretch=1)

    def _build_header(self) -> QtWidgets.QWidget:
        bar = QtWidgets.QWidget()
        bar.setStyleSheet("background: #181825; border-radius: 4px;")
        h = QtWidgets.QHBoxLayout(bar)
        h.setContentsMargins(10, 4, 10, 4)
        self._lbl_portfolio = QtWidgets.QLabel("组合：—")
        self._lbl_portfolio.setStyleSheet(
            f"color: {_FG}; font-size: 14px; font-weight: bold;"
        )
        self._lbl_computed_at = QtWidgets.QLabel("—")
        self._lbl_computed_at.setStyleSheet(f"color: {_MUT}; font-size: 11px;")
        h.addWidget(self._lbl_portfolio)
        h.addStretch()
        h.addWidget(self._lbl_computed_at)
        return bar

    def _build_perf_card(self) -> QtWidgets.QGroupBox:
        box = QtWidgets.QGroupBox("绩效摘要")
        box.setStyleSheet(
            f"QGroupBox {{ {_CARD_STYLE} color: {_MUT}; font-size: 11px; }}"
            "QGroupBox::title { subcontrol-origin: margin; padding: 0 4px; }"
        )
        grid = QtWidgets.QGridLayout(box)
        grid.setSpacing(4)
        metrics = [
            ("年化收益",  "annual_return",  "{:.2%}",  True),
            ("Sharpe",    "sharpe_ratio",   "{:.3f}",  True),
            ("最大回撤",  "max_drawdown",   "{:.2%}",  False),
            ("Calmar",    "calmar_ratio",   "{:.3f}",  True),
            ("年化波动率","volatility",     "{:.2%}",  None),
            ("总收益",    "total_return",   "{:.2%}",  True),
            ("日胜率",    "win_rate",       "{:.2%}",  None),
        ]
        self._perf_labels: dict[str, QtWidgets.QLabel] = {}
        for i, (name, key, fmt, _pg) in enumerate(metrics):
            lbl_name = QtWidgets.QLabel(name)
            lbl_name.setStyleSheet(f"color: {_MUT}; font-size: 10px;")
            lbl_val = QtWidgets.QLabel("—")
            lbl_val.setStyleSheet(
                f"color: {_FG}; font-size: 13px; font-weight: bold;"
            )
            lbl_val.setAlignment(QtCore.Qt.AlignmentFlag.AlignRight)
            grid.addWidget(lbl_name, i, 0)
            grid.addWidget(lbl_val,  i, 1)
            self._perf_labels[key] = lbl_val
        return box

    def _build_factor_card(self):
        box = QtWidgets.QGroupBox("因子信号")
        box.setStyleSheet(
            "QGroupBox { background: #181825; border-radius: 6px; padding: 6px;"
            " color: #6c7086; font-size: 11px; }"
            "QGroupBox::title { subcontrol-origin: margin; padding: 0 4px; }"
        )
        grid = QtWidgets.QGridLayout(box)
        grid.setSpacing(4)
        self._factor_labels = {}
        rows_meta = [
            ("因子名称",    "factor_name"),
            ("IC 均值",     "ic_mean"),
            ("RankIC 均值", "rank_ic_mean"),
            ("ICIR",        "icir"),
            ("RankICIR",    "rank_icir"),
            ("信号强度",    "signal_strength"),
        ]
        for i, (name, key) in enumerate(rows_meta):
            ln = QtWidgets.QLabel(name)
            ln.setStyleSheet("color: #6c7086; font-size: 10px;")
            lv = QtWidgets.QLabel("—")
            lv.setStyleSheet("color: #cdd6f4; font-size: 13px; font-weight: bold;")
            lv.setAlignment(QtCore.Qt.AlignmentFlag.AlignRight)
            grid.addWidget(ln, i, 0)
            grid.addWidget(lv, i, 1)
            self._factor_labels[key] = lv
        n = len(rows_meta)
        wl = QtWidgets.QLabel("建议权重")
        wl.setStyleSheet("color: #6c7086; font-size: 10px;")
        grid.addWidget(wl, n, 0, 1, 2)
        self._factor_weight_table = QtWidgets.QTableWidget(0, 2)
        self._factor_weight_table.setHorizontalHeaderLabels(["槽位", "权重"])
        self._factor_weight_table.horizontalHeader().setSectionResizeMode(
            QtWidgets.QHeaderView.ResizeMode.Stretch)
        self._factor_weight_table.verticalHeader().setVisible(False)
        self._factor_weight_table.setEditTriggers(
            QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
        self._factor_weight_table.setFixedHeight(120)
        self._factor_weight_table.setStyleSheet("font-size: 11px;")
        grid.addWidget(self._factor_weight_table, n + 1, 0, 1, 2)
        return box

    def _build_rebalance_table(self):
        tbl = QtWidgets.QTableWidget(0, 5)
        tbl.setHorizontalHeaderLabels(["调仓时间","槽位","调前权重","调后权重","原因"])
        tbl.horizontalHeader().setSectionResizeMode(
            QtWidgets.QHeaderView.ResizeMode.Stretch)
        tbl.verticalHeader().setVisible(False)
        tbl.setEditTriggers(QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
        tbl.setFixedHeight(180)
        tbl.setStyleSheet("font-size: 11px;")
        self._reb_table = tbl
        return tbl

    def _build_export_bar(self):
        bar = QtWidgets.QWidget()
        bar.setStyleSheet("background: #181825; border-radius: 4px;")
        h = QtWidgets.QHBoxLayout(bar)
        h.setContentsMargins(8, 4, 8, 4)
        h.setSpacing(8)
        def _mk(text, slot):
            btn = QtWidgets.QPushButton(text)
            btn.setStyleSheet(
                "QPushButton { background: #313244; color: #cdd6f4;"
                " border-radius: 4px; padding: 4px 12px; font-size: 12px; }"
                "QPushButton:hover { background: #45475a; }"
                "QPushButton:pressed { background: #585b70; }"
            )
            btn.clicked.connect(slot)
            return btn
        h.addWidget(_mk("导出 Excel 报告", self._on_export_excel))
        h.addWidget(_mk("导出净值 CSV",    self._on_export_nav_csv))
        h.addWidget(_mk("导出权重 CSV",    self._on_export_weight_csv))
        h.addStretch()
        self._export_status = QtWidgets.QLabel("")
        self._export_status.setStyleSheet("color: #6c7086; font-size: 11px;")
        h.addWidget(self._export_status)
        return bar

    # ------------------------------------------------------------------ #
    #  公开接口
    # ------------------------------------------------------------------ #

    def update_all(self, performance=None, allocation=None, risk=None,
                   attribution=None, rebalance_history=None, factor_signal=None):
        if performance       is not None: self._performance    = performance
        if allocation        is not None: self._allocation     = allocation
        if risk              is not None: self._risk           = risk
        if attribution       is not None: self._attribution    = attribution
        if rebalance_history is not None: self._rebalance_hist = rebalance_history
        if factor_signal     is not None: self._factor_signal  = factor_signal
        self.refresh()

    def refresh(self):
        if self._performance is None and self._allocation is None:
            return
        self._refresh_header()
        self._refresh_perf_card()
        self._refresh_factor_card()
        self._refresh_rebalance_table()
        self._placeholder.hide()
        self._content.show()

    def clear(self):
        self._performance = self._allocation = self._risk = None
        self._attribution = self._rebalance_hist = self._factor_signal = None
        for lbl in self._perf_labels.values():
            lbl.setText("—")
        for lbl in self._factor_labels.values():
            lbl.setText("—")
        self._reb_table.setRowCount(0)
        self._factor_weight_table.setRowCount(0)
        self._lbl_portfolio.setText("组合：—")
        self._lbl_computed_at.setText("—")
        self._export_status.setText("")
        self._content.hide()
        self._placeholder.show()

    # ------------------------------------------------------------------ #
    #  内部刷新
    # ------------------------------------------------------------------ #

    def _refresh_header(self):
        perf = self._performance
        if perf is None:
            return
        name = getattr(perf, "portfolio_name", "—")
        self._lbl_portfolio.setText("组合：" + name)
        ct = getattr(perf, "computed_at", None)
        if ct:
            self._lbl_computed_at.setText("计算时间：" + ct.strftime("%Y-%m-%d %H:%M:%S"))

    def _refresh_perf_card(self):
        perf = self._performance
        if perf is None:
            return
        fmt_map = {
            "annual_return": ("{:.2%}", True),
            "sharpe_ratio":  ("{:.3f}", True),
            "max_drawdown":  ("{:.2%}", False),
            "calmar_ratio":  ("{:.3f}", True),
            "volatility":    ("{:.2%}", None),
            "total_return":  ("{:.2%}", True),
            "win_rate":      ("{:.2%}", None),
        }
        for key, (fmt, positive_good) in fmt_map.items():
            lbl = self._perf_labels.get(key)
            if lbl is None:
                continue
            val = getattr(perf, key, float("nan"))
            if val is None or (isinstance(val, float) and math.isnan(val)):
                lbl.setText("—")
                continue
            text = fmt.format(val)
            if positive_good is True:
                color = "#a6e3a1" if val >= 0 else "#f38ba8"
            elif positive_good is False:
                color = "#f38ba8" if val < 0 else "#a6e3a1"
            else:
                color = "#cdd6f4"
            lbl.setText(text)
            lbl.setStyleSheet("color: " + color + "; font-size: 13px; font-weight: bold;")

    def _refresh_factor_card(self):
        sig = self._factor_signal
        if sig is None:
            for lbl in self._factor_labels.values():
                lbl.setText("—")
            self._factor_weight_table.setRowCount(0)
            return

        def _s(key, val, fmt="{:.4f}", cbs=False):
            lbl = self._factor_labels.get(key)
            if lbl is None:
                return
            if val is None or (isinstance(val, float) and math.isnan(val)):
                lbl.setText("—")
                return
            text = fmt.format(val) if not isinstance(val, str) else val
            color = "#cdd6f4"
            if cbs:
                color = "#a6e3a1" if val >= 0 else "#f38ba8"
            lbl.setText(text)
            lbl.setStyleSheet("color: " + color + "; font-size: 13px; font-weight: bold;")

        _s("factor_name",  getattr(sig, "factor_name",  "—"), "{}")
        _s("ic_mean",      getattr(sig, "ic_mean",      float("nan")), "{:.4f}", True)
        _s("rank_ic_mean", getattr(sig, "rank_ic_mean", float("nan")), "{:.4f}", True)
        _s("icir",         getattr(sig, "icir",         float("nan")), "{:.3f}", True)
        _s("rank_icir",    getattr(sig, "rank_icir",    float("nan")), "{:.3f}", True)

        strength = getattr(sig, "signal_strength", float("nan"))
        if not math.isnan(strength):
            c = "#a6e3a1" if strength >= 0.6 else ("#f9e2af" if strength >= 0.3 else "#f38ba8")
            lbl = self._factor_labels.get("signal_strength")
            if lbl:
                lbl.setText(f"{strength:.2f}")
                lbl.setStyleSheet("color: " + c + "; font-size: 13px; font-weight: bold;")

        weights = getattr(sig, "suggested_weights", {}) or {}
        self._factor_weight_table.setRowCount(0)
        for slot, w in sorted(weights.items(), key=lambda x: -x[1]):
            row = self._factor_weight_table.rowCount()
            self._factor_weight_table.insertRow(row)
            self._factor_weight_table.setItem(row, 0, _item(slot))
            self._factor_weight_table.setItem(row, 1, _item(f"{w:.2%}"))

    def _refresh_rebalance_table(self):
        history = self._rebalance_hist
        self._reb_table.setRowCount(0)
        if not history:
            return
        for rec in list(reversed(history))[:10]:
            all_slots = sorted(
                set(list(rec.prev_weights.keys()) | list(rec.new_weights.keys()))
            )
            for slot in all_slots:
                prev = rec.prev_weights.get(slot, 0.0)
                new  = rec.new_weights.get(slot, 0.0)
                row  = self._reb_table.rowCount()
                self._reb_table.insertRow(row)
                self._reb_table.setItem(row, 0, _item(rec.triggered_at.strftime("%Y-%m-%d")))
                self._reb_table.setItem(row, 1, _item(slot))
                self._reb_table.setItem(row, 2, _item(f"{prev:.2%}"))
                self._reb_table.setItem(row, 3, _item(f"{new:.2%}"))
                self._reb_table.setItem(row, 4, _item(rec.reason))

    # ------------------------------------------------------------------ #
    #  导出
    # ------------------------------------------------------------------ #

    def _on_export_excel(self):
        path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, "导出 Excel 报告", "", "Excel 文件 (*.xlsx)")
        if not path:
            return
        try:
            from ..utils.export_utils import export_excel
            from pathlib import Path
            export_excel(
                path=Path(path),
                performance=self._performance,
                allocation=self._allocation,
                risk=self._risk,
                attribution=self._attribution,
                rebalance_history=self._rebalance_hist,
            )
            self._export_status.setText("已导出：" + path)
            self._export_status.setStyleSheet("color: #a6e3a1; font-size: 11px;")
        except Exception as e:
            self._export_status.setText("导出失败：" + str(e))
            self._export_status.setStyleSheet("color: #f38ba8; font-size: 11px;")

    def _on_export_nav_csv(self):
        path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, "导出净值 CSV", "", "CSV 文件 (*.csv)")
        if not path:
            return
        try:
            if self._performance is None or self._performance.nav_series is None:
                raise ValueError("无净值数据")
            from ..utils.export_utils import export_csv
            from pathlib import Path
            export_csv(self._performance.nav_series, Path(path))
            self._export_status.setText("已导出：" + path)
            self._export_status.setStyleSheet("color: #a6e3a1; font-size: 11px;")
        except Exception as e:
            self._export_status.setText("导出失败：" + str(e))
            self._export_status.setStyleSheet("color: #f38ba8; font-size: 11px;")

    def _on_export_weight_csv(self):
        path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, "导出权重 CSV", "", "CSV 文件 (*.csv)")
        if not path:
            return
        try:
            if self._allocation is None or not self._allocation.weights:
                raise ValueError("无权重数据")
            import pandas as pd
            from ..utils.export_utils import export_csv
            from pathlib import Path
            s = pd.Series(self._allocation.weights, name="weight")
            export_csv(s, Path(path))
            self._export_status.setText("已导出：" + path)
            self._export_status.setStyleSheet("color: #a6e3a1; font-size: 11px;")
        except Exception as e:
            self._export_status.setText("导出失败：" + str(e))
            self._export_status.setStyleSheet("color: #f38ba8; font-size: 11px;")
