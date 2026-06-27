"""
ui/factor_dialog.py

因子分析对话框 — 在完成批量回测后，对结果做多因子截面分析。

功能：
  - 勾选要使用的因子（内置 ResultFactor + BarFactor）
  - 选择对标收益列（total_return / annual_return / sharpe_ratio）
  - 点击"运行分析"后显示：
      Tab 1: 因子 IC / RankIC 表
      Tab 2: 分层收益表（最佳 IC 因子）
      Tab 3: 因子相关矩阵
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from vnpy.trader.ui import QtCore, QtWidgets

if TYPE_CHECKING:
    from ..task import BacktestResult


_BUILTIN_RESULT_FACTORS = [
    ("sharpe_ratio",            "夏普比率",      True),
    ("total_return",            "总收益%",       True),
    ("annual_return",           "年化收益%",     True),
    ("max_ddpercent",           "最大回撤%",     True),
    ("calmar_ratio",            "卡玛比率",      True),
    ("return_drawdown_ratio",   "收益/回撤比",   False),
    ("ewm_sharpe",              "EWM夏普",       False),
    ("daily_trade_count",       "日均交易次数",  False),
]

_BUILTIN_BAR_FACTORS = [
    ("price_momentum_60b",  "价格动量(60根)",  False),
    ("volatility_60b",      "实现波动率(60根)", False),
    ("rsi_14",              "RSI(14)",          False),
]

_RETURN_COLS = ["total_return", "annual_return", "sharpe_ratio"]


class FactorAnalysisDialog(QtWidgets.QDialog):
    """
    Factor analysis dialog.

    Receives a list[BacktestResult] and an optional bars_map;
    runs FactorEngine and displays results in three tabs.
    """

    def __init__(
        self,
        results: "list[BacktestResult]",
        bars_map: dict | None = None,
        parent: QtWidgets.QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("多因子截面分析")
        self.setMinimumSize(900, 640)
        self.resize(960, 700)

        self._results = results
        self._bars_map = bars_map or {}
        self._factor_df = None

        self._init_ui()

    # ------------------------------------------------------------------ #
    #  Build UI
    # ------------------------------------------------------------------ #

    def _init_ui(self) -> None:
        # Left panel: factor selection + options
        left = QtWidgets.QWidget()
        left.setFixedWidth(240)
        left_vbox = QtWidgets.QVBoxLayout(left)
        left_vbox.setContentsMargins(4, 4, 4, 4)

        # Result factor checkboxes
        rf_group = QtWidgets.QGroupBox("绩效因子")
        rf_layout = QtWidgets.QVBoxLayout(rf_group)
        self._rf_checks: dict[str, QtWidgets.QCheckBox] = {}
        for name, label, default in _BUILTIN_RESULT_FACTORS:
            cb = QtWidgets.QCheckBox(label)
            cb.setChecked(default)
            cb.setObjectName(name)
            rf_layout.addWidget(cb)
            self._rf_checks[name] = cb

        # Bar factor checkboxes
        bf_group = QtWidgets.QGroupBox("行情因子（需提供K线数据）")
        bf_layout = QtWidgets.QVBoxLayout(bf_group)
        self._bf_checks: dict[str, QtWidgets.QCheckBox] = {}
        for name, label, default in _BUILTIN_BAR_FACTORS:
            cb = QtWidgets.QCheckBox(label)
            cb.setChecked(default)
            cb.setObjectName(name)
            cb.setEnabled(bool(self._bars_map))
            bf_layout.addWidget(cb)
            self._bf_checks[name] = cb

        # Return column
        ret_group = QtWidgets.QGroupBox("对标收益列")
        ret_layout = QtWidgets.QVBoxLayout(ret_group)
        self._return_combo = QtWidgets.QComboBox()
        self._return_combo.addItems(_RETURN_COLS)
        ret_layout.addWidget(self._return_combo)

        # Layer count
        layer_layout = QtWidgets.QHBoxLayout()
        layer_layout.addWidget(QtWidgets.QLabel("分层数："))
        self._layer_spin = QtWidgets.QSpinBox()
        self._layer_spin.setRange(2, 20)
        self._layer_spin.setValue(5)
        layer_layout.addWidget(self._layer_spin)
        layer_layout.addStretch()

        # Run button
        self._run_btn = QtWidgets.QPushButton("运行分析")
        self._run_btn.clicked.connect(self._run_analysis)

        left_vbox.addWidget(rf_group)
        left_vbox.addWidget(bf_group)
        left_vbox.addWidget(ret_group)
        left_vbox.addLayout(layer_layout)
        left_vbox.addWidget(self._run_btn)
        left_vbox.addStretch()

        # Right panel: tabs for IC / Layer / Corr
        self._tabs = QtWidgets.QTabWidget()

        self._ic_table    = _ResultTable(["因子", "IC (Pearson)", "RankIC (Spearman)"])
        self._layer_table = _ResultTable(["层", "数量", "均值收益%", "中位收益%", "标准差%"])
        self._corr_table  = _ResultTable([])

        self._tabs.addTab(self._ic_table,    "IC / RankIC")
        self._tabs.addTab(self._layer_table, "分层收益")
        self._tabs.addTab(self._corr_table,  "相关矩阵")

        # Status label
        self._status_label = QtWidgets.QLabel(
            f"就绪：{len(self._results)} 只股票"
        )

        # Main layout
        h_splitter = QtWidgets.QSplitter(QtCore.Qt.Orientation.Horizontal)
        h_splitter.addWidget(left)
        h_splitter.addWidget(self._tabs)
        h_splitter.setStretchFactor(0, 0)
        h_splitter.setStretchFactor(1, 1)

        close_btn = QtWidgets.QPushButton("关闭")
        close_btn.clicked.connect(self.close)

        vbox = QtWidgets.QVBoxLayout(self)
        vbox.addWidget(h_splitter)
        vbox.addWidget(self._status_label)
        vbox.addWidget(close_btn, 0, QtCore.Qt.AlignmentFlag.AlignRight)

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
        from ..factor import FactorEngine
        from ..factor.factor_template import (
            SharpeRatioFactor, TotalReturnFactor, AnnualReturnFactor,
            MaxDrawdownFactor, CalmarRatioFactor, ReturnDrawdownRatioFactor,
            EwmSharpeFactor, TradingFrequencyFactor,
            PriceMomentumFactor, VolatilityFactor, RSIFactor,
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
        _bf_cls_map = {
            "price_momentum_60b": lambda: PriceMomentumFactor(60),
            "volatility_60b":     lambda: VolatilityFactor(60),
            "rsi_14":             lambda: RSIFactor(14),
        }

        engine = FactorEngine()

        for name, cb in self._rf_checks.items():
            if cb.isChecked() and name in _rf_cls_map:
                engine.register(_rf_cls_map[name]())

        if self._bars_map:
            for name, cb in self._bf_checks.items():
                if cb.isChecked() and name in _bf_cls_map:
                    engine.register(_bf_cls_map[name]())

        if not engine.factor_names:
            raise ValueError("请至少勾选一个因子")

        return_col = self._return_combo.currentText()
        n_layers   = self._layer_spin.value()

        df = engine.calculate(self._results, bars_map=self._bars_map)
        self._factor_df = df

        factor_cols = [c for c in engine.factor_names if c in df.columns]

        # ---- IC table ----
        pearson  = engine.cross_section_ic(df, return_col, "pearson")
        spearman = engine.cross_section_ic(df, return_col, "spearman")

        self._ic_table.clear_rows()
        for col in factor_cols:
            p = pearson.get(col, float("nan"))
            s = spearman.get(col, float("nan"))
            self._ic_table.add_row([
                col,
                f"{p:.4f}" if p == p else "N/A",
                f"{s:.4f}" if s == s else "N/A",
            ])

        # ---- Layer table ----
        try:
            best = spearman.abs().idxmax()
            layer_df = engine.layer_analysis(
                df, return_col=return_col,
                n_layers=n_layers, factor_col=best,
            )
            self._layer_table.clear_rows()
            self._layer_table.setHorizontalHeaderLabels([
                "层", "数量", "均值收益%", "中位收益%", "标准差%"
            ])
            for lid, row in layer_df.iterrows():
                self._layer_table.add_row([
                    str(lid),
                    str(int(row["count"])),
                    f"{row['mean_return']:.2f}",
                    f"{row['median_return']:.2f}",
                    f"{row['std_return']:.2f}",
                ])
        except Exception as e:
            self._layer_table.clear_rows()
            self._layer_table.add_row([f"分层失败：{e}", "", "", "", ""])

        # ---- Correlation table ----
        try:
            corr = engine.correlation_matrix(df, "spearman")
            cols = list(corr.columns)
            self._corr_table.setColumnCount(len(cols) + 1)
            self._corr_table.setHorizontalHeaderLabels(["因子"] + cols)
            self._corr_table.clear_rows()
            for idx in corr.index:
                row_data = [idx] + [f"{corr.loc[idx, c]:.3f}" for c in cols]
                self._corr_table.add_row(row_data)
        except Exception as e:
            self._corr_table.clear_rows()
            self._corr_table.add_row([f"相关矩阵失败：{e}"])

        n_valid = df[factor_cols[0]].notna().sum() if factor_cols else 0
        self._status_label.setText(
            f"分析完成：{len(df)} 只股票，{len(factor_cols)} 个因子，"
            f"有效数据 {n_valid} 只，对标列={return_col}"
        )
        self._tabs.setCurrentIndex(0)


# ------------------------------------------------------------------ #
#  Simple reusable table widget
# ------------------------------------------------------------------ #

class _ResultTable(QtWidgets.QTableWidget):
    """Minimal table used inside FactorAnalysisDialog."""

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

    def clear_rows(self) -> None:
        self.setRowCount(0)

    def add_row(self, values: list[str]) -> None:
        row = self.rowCount()
        self.insertRow(row)
        for col, val in enumerate(values):
            item = QtWidgets.QTableWidgetItem(str(val))
            item.setTextAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
            self.setItem(row, col, item)
