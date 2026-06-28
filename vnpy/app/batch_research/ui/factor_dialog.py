"""
ui/factor_dialog.py

因子分析对话框 — 在完成批量回测后，对结果做多因子截面分析。

功能：
  - 勾选要使用的因子（内置 ResultFactor）
  - 选择对标收益列（total_return / annual_return / sharpe_ratio）
  - 设置综合评分权重（等权 / 自定义）
  - 设置选股数量（Top N）
  - 点击"运行分析"后显示：
      Tab 1: 因子 IC / RankIC 表
      Tab 2: 分层收益表（最佳 IC 因子）
      Tab 3: 因子相关矩阵
      Tab 4: 综合排名（composite_score + factor_rank + selected）

接收 list[BatchBacktestResult]，不依赖旧 BacktestResult。
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from vnpy.trader.ui import QtCore, QtWidgets

if TYPE_CHECKING:
    from ..batch_result import BatchBacktestResult


_BUILTIN_RESULT_FACTORS = [
    ("sharpe_ratio",          "夏普比率",     True),
    ("total_return",          "总收益%",      True),
    ("annual_return",         "年化收益%",    True),
    ("max_ddpercent",         "最大回撤%",    True),
    ("calmar_ratio",          "卡玛比率",     True),
    ("annual_volatility",     "年化波动率%",  False),
    ("win_rate",              "日胜率%",      False),
    ("profit_factor",         "盈利因子",     False),
    ("return_drawdown_ratio", "收益/回撤比",  False),
    ("ewm_sharpe",            "EWM夏普",      False),
    ("daily_trade_count",     "日均交易次数", False),
]

_RETURN_COLS = ["total_return", "annual_return", "sharpe_ratio"]


class FactorAnalysisDialog(QtWidgets.QDialog):
    """
    因子分析对话框，接收 list[BatchBacktestResult]。

    综合排名路径：FactorEngine.run() 直读 BatchBacktestResult 字段。
    IC/分层/相关矩阵路径：用 pandas 直接计算，不走旧 calculate()。
    """

    def __init__(
        self,
        results: "list[BatchBacktestResult]",
        bars_map: dict | None = None,
        parent: QtWidgets.QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("多因子截面分析")
        self.setMinimumSize(960, 680)
        self.resize(1040, 740)

        self._results  = results
        self._bars_map = bars_map or {}

        self._init_ui()

    # ------------------------------------------------------------------ #
    #  UI construction
    # ------------------------------------------------------------------ #

    def _init_ui(self) -> None:
        left = QtWidgets.QWidget()
        left.setFixedWidth(260)
        left_vbox = QtWidgets.QVBoxLayout(left)
        left_vbox.setContentsMargins(4, 4, 4, 4)
        left_vbox.setSpacing(6)

        rf_group = QtWidgets.QGroupBox("绩效因子")
        rf_layout = QtWidgets.QVBoxLayout(rf_group)
        self._rf_checks: dict[str, QtWidgets.QCheckBox] = {}
        for name, label, default in _BUILTIN_RESULT_FACTORS:
            cb = QtWidgets.QCheckBox(label)
            cb.setChecked(default)
            rf_layout.addWidget(cb)
            self._rf_checks[name] = cb

        ret_group = QtWidgets.QGroupBox("对标收益列（IC 分析）")
        ret_layout = QtWidgets.QVBoxLayout(ret_group)
        self._return_combo = QtWidgets.QComboBox()
        self._return_combo.addItems(_RETURN_COLS)
        ret_layout.addWidget(self._return_combo)

        layer_layout = QtWidgets.QHBoxLayout()
        layer_layout.addWidget(QtWidgets.QLabel("分层数："))
        self._layer_spin = QtWidgets.QSpinBox()
        self._layer_spin.setRange(2, 20)
        self._layer_spin.setValue(5)
        layer_layout.addWidget(self._layer_spin)
        layer_layout.addStretch()

        rank_group = QtWidgets.QGroupBox("综合排名 / 选股")
        rank_layout = QtWidgets.QVBoxLayout(rank_group)
        self._equal_weight_rb  = QtWidgets.QRadioButton("均等权重")
        self._custom_weight_rb = QtWidgets.QRadioButton("夏普x4 / 卡玛x3 / 胜率x2 / 收益x1")
        self._equal_weight_rb.setChecked(True)
        top_n_layout = QtWidgets.QHBoxLayout()
        top_n_layout.addWidget(QtWidgets.QLabel("选股 Top N："))
        self._top_n_spin = QtWidgets.QSpinBox()
        self._top_n_spin.setRange(1, 500)
        self._top_n_spin.setValue(20)
        top_n_layout.addWidget(self._top_n_spin)
        top_n_layout.addStretch()
        rank_layout.addWidget(self._equal_weight_rb)
        rank_layout.addWidget(self._custom_weight_rb)
        rank_layout.addLayout(top_n_layout)

        self._run_btn = QtWidgets.QPushButton("运行分析")
        self._run_btn.setFixedHeight(32)
        self._run_btn.clicked.connect(self._run_analysis)

        left_vbox.addWidget(rf_group)
        left_vbox.addWidget(ret_group)
        left_vbox.addLayout(layer_layout)
        left_vbox.addWidget(rank_group)
        left_vbox.addWidget(self._run_btn)
        left_vbox.addStretch()

        self._tabs = QtWidgets.QTabWidget()
        self._ic_table    = _ResultTable(["因子", "IC (Pearson)", "RankIC (Spearman)", "RankIC |绝对值|"])
        self._layer_table = _ResultTable(["层", "数量", "均值收益%", "中位收益%", "标准差%"])
        self._corr_table  = _ResultTable([])
        self._rank_table  = _ResultTable([
            "综合排名", "股票代码", "名称", "综合评分",
            "夏普比率", "总收益%", "年化收益%", "最大回撤%",
            "卡玛比率", "日胜率%", "是否选中",
        ])
        self._tabs.addTab(self._ic_table,    "IC / RankIC")
        self._tabs.addTab(self._layer_table, "分层收益")
        self._tabs.addTab(self._corr_table,  "相关矩阵")
        self._tabs.addTab(self._rank_table,  "综合排名")

        self._status_label = QtWidgets.QLabel(f"就绪：{len(self._results)} 只股票")
        close_btn = QtWidgets.QPushButton("关闭")
        close_btn.clicked.connect(self.close)
        bottom = QtWidgets.QHBoxLayout()
        bottom.addWidget(self._status_label, 1)
        bottom.addWidget(close_btn)

        h_splitter = QtWidgets.QSplitter(QtCore.Qt.Orientation.Horizontal)
        h_splitter.addWidget(left)
        h_splitter.addWidget(self._tabs)
        h_splitter.setStretchFactor(0, 0)
        h_splitter.setStretchFactor(1, 1)

        vbox = QtWidgets.QVBoxLayout(self)
        vbox.addWidget(h_splitter)
        vbox.addLayout(bottom)

    # ------------------------------------------------------------------ #
    #  Analysis execution
    # ------------------------------------------------------------------ #

    def _run_analysis(self) -> None:
        self._run_btn.setEnabled(False)
        self._status_label.setText("运行中…")
        QtWidgets.QApplication.processEvents()
        try:
            self._do_analysis()
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "分析失败", str(e))
            self._status_label.setText(f"分析失败：{e}")
        finally:
            self._run_btn.setEnabled(True)

    def _do_analysis(self) -> None:
        from ..factor.factor_engine import FactorEngine
        from ..factor.factor_template import (
            SharpeRatioFactor, TotalReturnFactor, AnnualReturnFactor,
            MaxDrawdownFactor, CalmarRatioFactor, ReturnDrawdownRatioFactor,
            EwmSharpeFactor, TradingFrequencyFactor,
        )

        _rf_cls_map = {
            "sharpe_ratio":          SharpeRatioFactor,
            "total_return":          TotalReturnFactor,
            "annual_return":         AnnualReturnFactor,
            "max_ddpercent":         MaxDrawdownFactor,
            "calmar_ratio":          CalmarRatioFactor,
            "return_drawdown_ratio": ReturnDrawdownRatioFactor,
            "ewm_sharpe":            EwmSharpeFactor,
            "daily_trade_count":     TradingFrequencyFactor,
        }

        selected_names = [n for n, cb in self._rf_checks.items() if cb.isChecked()]
        if not selected_names:
            raise ValueError("请至少勾选一个绩效因子")

        if self._custom_weight_rb.isChecked():
            weights = {"sharpe_ratio": 4.0, "calmar_ratio": 3.0,
                       "win_rate": 2.0, "total_return": 1.0}
        else:
            weights = {name: 1.0 for name in selected_names}

        top_n = self._top_n_spin.value()

        # Tab 4: 综合排名（run() 路径，直读 BatchBacktestResult 字段）
        rank_engine = FactorEngine()
        for name in selected_names:
            if name in _rf_cls_map:
                rank_engine.register(_rf_cls_map[name]())

        rank_engine.run(self._results, weights=weights, selector_top_n=top_n)

        self._rank_table.clear_rows()
        ranked = sorted(
            [r for r in self._results if r.factor_rank is not None],
            key=lambda r: r.factor_rank,
        )
        unranked = [r for r in self._results if r.factor_rank is None]
        for r in ranked:
            self._rank_table.add_row([
                str(r.factor_rank) if r.factor_rank is not None else "-", r.vt_symbol, r.name or "-",
                f"{r.composite_score:.3f}" if r.composite_score is not None else "-", f"{r.sharpe_ratio:.3f}",
                f"{r.total_return:.2f}", f"{r.annual_return:.2f}",
                f"{r.max_ddpercent:.2f}", f"{r.calmar_ratio:.3f}",
                f"{r.win_rate:.2f}", "YES" if r.selected else "",
            ])
        for r in unranked:
            self._rank_table.add_row(
                ["-", r.vt_symbol, r.name or "-"] + ["-"] * 8
            )

        # IC / 分层 / 相关矩阵（pandas 直接计算，不走旧 calculate()）
        return_col = self._return_combo.currentText()
        n_layers   = self._layer_spin.value()
        success    = [r for r in self._results if r.status == "success"]
        if not success:
            self._status_label.setText("无成功结果，跳过 IC/分层分析")
            self._tabs.setCurrentIndex(3)
            return

        import pandas as pd
        rows: dict[str, dict] = {}
        for r in success:
            row: dict = {}
            for name in selected_names:
                raw = getattr(r, name, None)
                if raw is not None:
                    try:
                        row[name] = float(raw)
                    except (TypeError, ValueError):
                        pass
            rcol_val = getattr(r, return_col, 0.0)
            try:
                row[return_col] = float(rcol_val)
            except (TypeError, ValueError):
                row[return_col] = 0.0
            rows[r.vt_symbol] = row
        fdf = pd.DataFrame(rows).T
        factor_cols = [c for c in selected_names if c in fdf.columns]

        # Tab 1: IC
        self._ic_table.clear_rows()
        for col in factor_cols:
            if return_col not in fdf.columns:
                self._ic_table.add_row([col, "N/A", "N/A", "N/A"])
                continue
            aligned = pd.concat([fdf[col], fdf[return_col]], axis=1).dropna()
            if len(aligned) < 3:
                self._ic_table.add_row([col, "N/A", "N/A", "N/A"])
                continue
            ic  = aligned.iloc[:, 0].corr(aligned.iloc[:, 1], method="pearson")
            ric = aligned.iloc[:, 0].corr(aligned.iloc[:, 1], method="spearman")
            fmt = lambda v: f"{v:.4f}" if v == v else "N/A"
            self._ic_table.add_row([col, fmt(ic), fmt(ric),
                                    fmt(abs(ric)) if ric == ric else "N/A"])

        # Tab 2: 分层
        self._layer_table.clear_rows()
        if factor_cols and return_col in fdf.columns:
            try:
                rank_ics = {
                    c: abs(fdf[c].corr(fdf[return_col], method="spearman") or 0)
                    for c in factor_cols
                }
                best = max(rank_ics, key=lambda c: rank_ics[c])
                df2 = fdf[[best, return_col]].dropna().copy()
                df2["_layer"] = pd.qcut(df2[best], q=n_layers,
                                        labels=False, duplicates="drop")
                for lid in sorted(df2["_layer"].dropna().unique()):
                    grp = df2[df2["_layer"] == lid]
                    self._layer_table.add_row([
                        str(int(lid) + 1), str(len(grp)),
                        f"{grp[return_col].mean():.2f}",
                        f"{grp[return_col].median():.2f}",
                        f"{grp[return_col].std():.2f}",
                    ])
            except Exception as e:
                self._layer_table.add_row([f"分层失败：{e}", "", "", "", ""])

        # Tab 3: 相关矩阵
        try:
            corr = fdf[factor_cols].corr(method="spearman")
            cols = list(corr.columns)
            self._corr_table.setColumnCount(len(cols) + 1)
            self._corr_table.setHorizontalHeaderLabels(["因子"] + cols)
            self._corr_table.clear_rows()
            for idx in corr.index:
                self._corr_table.add_row(
                    [idx] + [f"{corr.loc[idx, c]:.3f}" for c in cols]
                )
        except Exception as e:
            self._corr_table.clear_rows()
            self._corr_table.add_row([f"相关矩阵失败：{e}"])

        n_sel = sum(1 for r in self._results if getattr(r, 'selected', False))
        self._status_label.setText(
            f"完成：{len(success)} 只有效，{len(factor_cols)} 个因子，"
            f"对标={return_col}，选中 {n_sel} 只"
        )
        self._tabs.setCurrentIndex(3)


# ------------------------------------------------------------------ #
#  简单表格辅助类
# ------------------------------------------------------------------ #

class _ResultTable(QtWidgets.QTableWidget):

    def __init__(self, headers: list[str]) -> None:
        super().__init__()
        if headers:
            self.setColumnCount(len(headers))
            self.setHorizontalHeaderLabels(headers)
        self.verticalHeader().setVisible(False)
        self.setEditTriggers(self.EditTrigger.NoEditTriggers)
        self.setAlternatingRowColors(True)
        self.setSortingEnabled(True)
        self.horizontalHeader().setStretchLastSection(True)
        self.setSelectionBehavior(self.SelectionBehavior.SelectRows)

    def clear_rows(self) -> None:
        self.setRowCount(0)

    def add_row(self, values: list[str]) -> None:
        row = self.rowCount()
        self.insertRow(row)
        for col, val in enumerate(values):
            item = QtWidgets.QTableWidgetItem(str(val))
            item.setTextAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
            self.setItem(row, col, item)
