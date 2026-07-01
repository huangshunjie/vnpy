"""
factor_research/ui/ic_tab.py

IcTab — IC 统计 Tab。

布局（上下两区）：
┌──────────────────────────────────────────────┐
│  计算参数信息区（QFormLayout）                  │
│  合约 / 因子名 / 动量窗口 / 持有期 / 样本数      │
├──────────────────────────────────────────────┤
│  IC / RankIC 统计对比表（QTableWidget）         │
│  行：IC_mean / IC_std / ICIR / 胜率            │
│  列：IC（Pearson） / RankIC（Spearman）         │
└──────────────────────────────────────────────┘

数据来源：
  dispatcher → EVENT_FACTOR_PLOT_READY {"tab":"ic", "payload": IcStats}
  由 FactorResearchWidget 调用 self.ic_tab.update_stats(stats)

设计原则：
  - Tab 不持有 Engine 引用，不访问数据库
  - 所有数据通过 update_stats() 注入
  - 数值格式：保留 4 位小数；百分比保留 2 位
  - ICIR 颜色标注：|ICIR| ≥ 1.0 标绿（好），< 0.5 标红（差）
"""

from __future__ import annotations

import math

from vnpy.trader.ui import QtCore, QtWidgets

from ..model import IcStats


# IC 统计表行定义：(行标题, IC 属性名, RankIC 属性名, 格式化函数)
_ROWS: list[tuple[str, str, str, str]] = [
    ("IC 均值",      "ic_mean",            "rank_ic_mean",            "float4"),
    ("IC 标准差",    "ic_std",             "rank_ic_std",             "float4"),
    ("ICIR",         "icir",               "rank_icir",               "icir"),
    ("IC > 0 胜率",  "ic_positive_rate",   "rank_ic_positive_rate",   "pct"),
]

_COL_HEADERS = ["统计量", "IC（Pearson）", "RankIC（Spearman）"]


def _fmt(value: float, fmt: str) -> str:
    if math.isnan(value):
        return "—"
    if fmt == "float4":
        return f"{value:.4f}"
    if fmt == "pct":
        return f"{value:.2%}"
    if fmt == "icir":
        return f"{value:.4f}"
    return str(value)


class IcTab(QtWidgets.QWidget):
    """IC 统计 Tab。"""

    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self._init_ui()

    # ------------------------------------------------------------------ #
    #  UI 构建
    # ------------------------------------------------------------------ #

    def _init_ui(self) -> None:
        root = QtWidgets.QVBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(8)

        root.addWidget(self._build_info_group())
        root.addWidget(self._build_stats_group(), stretch=1)

    def _build_info_group(self) -> QtWidgets.QGroupBox:
        group = QtWidgets.QGroupBox("计算参数")
        form = QtWidgets.QFormLayout(group)
        form.setLabelAlignment(QtCore.Qt.AlignmentFlag.AlignRight)
        form.setSpacing(6)
        form.setContentsMargins(8, 8, 8, 8)

        def _lbl(text: str = "—") -> QtWidgets.QLabel:
            l = QtWidgets.QLabel(text)
            l.setTextInteractionFlags(
                QtCore.Qt.TextInteractionFlag.TextSelectableByMouse
            )
            return l

        self.lbl_symbol   = _lbl()
        self.lbl_factor   = _lbl()
        self.lbl_lag      = _lbl()
        self.lbl_samples  = _lbl()
        self.lbl_ic_len   = _lbl()

        form.addRow("合约代码", self.lbl_symbol)
        form.addRow("因子名称", self.lbl_factor)
        form.addRow("持有期(天)", self.lbl_lag)
        form.addRow("有效样本", self.lbl_samples)
        form.addRow("IC序列长度", self.lbl_ic_len)

        return group

    def _build_stats_group(self) -> QtWidgets.QGroupBox:
        group = QtWidgets.QGroupBox("IC / RankIC 统计对比")
        layout = QtWidgets.QVBoxLayout(group)
        layout.setContentsMargins(4, 4, 4, 4)

        self.stats_table = QtWidgets.QTableWidget(len(_ROWS), len(_COL_HEADERS))
        self.stats_table.setHorizontalHeaderLabels(_COL_HEADERS)
        self.stats_table.verticalHeader().setVisible(False)
        self.stats_table.setEditTriggers(
            QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers
        )
        self.stats_table.setSelectionBehavior(
            QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows
        )
        self.stats_table.setAlternatingRowColors(True)
        self.stats_table.horizontalHeader().setSectionResizeMode(
            QtWidgets.QHeaderView.ResizeMode.Stretch
        )
        # 预填行标题
        for row_idx, (row_label, *_) in enumerate(_ROWS):
            item = QtWidgets.QTableWidgetItem(row_label)
            item.setTextAlignment(
                int(QtCore.Qt.AlignmentFlag.AlignLeft
                    | QtCore.Qt.AlignmentFlag.AlignVCenter)
            )
            self.stats_table.setItem(row_idx, 0, item)

        self._placeholder = QtWidgets.QLabel(
            "暂无数据\n请在左侧配置区填写参数后点击「运行」"
        )
        self._placeholder.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)

        layout.addWidget(self._placeholder)
        layout.addWidget(self.stats_table)
        self.stats_table.hide()

        return group

    # ------------------------------------------------------------------ #
    #  公开接口
    # ------------------------------------------------------------------ #

    def update_stats(self, stats: IcStats) -> None:
        """
        将 IcStats 数据渲染到 Tab 中。
        在 Qt 主线程调用（Signal/Slot 保证）。
        """
        self._update_info(stats)
        self._update_table(stats)

    def clear(self) -> None:
        """重置到空状态。"""
        for lbl in (self.lbl_symbol, self.lbl_factor,
                    self.lbl_lag, self.lbl_samples, self.lbl_ic_len):
            lbl.setText("—")
        for row_idx in range(len(_ROWS)):
            for col_idx in (1, 2):
                item = self.stats_table.item(row_idx, col_idx)
                if item:
                    item.setText("—")
        self.stats_table.hide()
        self._placeholder.show()

    # ------------------------------------------------------------------ #
    #  内部渲染
    # ------------------------------------------------------------------ #

    def _update_info(self, stats: IcStats) -> None:
        self.lbl_symbol.setText(stats.vt_symbol)
        self.lbl_factor.setText(stats.factor_name)
        self.lbl_lag.setText(str(stats.lag))
        self.lbl_samples.setText(str(stats.sample_size))
        self.lbl_ic_len.setText(str(stats.ic_series_len))

    def _update_table(self, stats: IcStats) -> None:
        if not stats.is_valid():
            self.stats_table.hide()
            self._placeholder.show()
            return

        self._placeholder.hide()
        self.stats_table.show()

        for row_idx, (_, ic_attr, ric_attr, fmt) in enumerate(_ROWS):
            ic_val  = getattr(stats, ic_attr,  float("nan"))
            ric_val = getattr(stats, ric_attr, float("nan"))

            ic_item  = QtWidgets.QTableWidgetItem(_fmt(ic_val,  fmt))
            ric_item = QtWidgets.QTableWidgetItem(_fmt(ric_val, fmt))

            align = int(
                QtCore.Qt.AlignmentFlag.AlignRight
                | QtCore.Qt.AlignmentFlag.AlignVCenter
            )
            ic_item.setTextAlignment(align)
            ric_item.setTextAlignment(align)

            # ICIR 行颜色标注
            if fmt == "icir":
                for item, val in ((ic_item, ic_val), (ric_item, ric_val)):
                    self._apply_icir_color(item, val)

            self.stats_table.setItem(row_idx, 1, ic_item)
            self.stats_table.setItem(row_idx, 2, ric_item)

    @staticmethod
    def _apply_icir_color(
        item: QtWidgets.QTableWidgetItem,
        val: float,
    ) -> None:
        """
        ICIR 颜色规则：
          |ICIR| ≥ 1.0  → 绿色（因子有效）
          0.5 ≤ |ICIR| < 1.0 → 默认色
          |ICIR| < 0.5  → 红色（因子较弱）
        """
        from vnpy.trader.ui import QtGui
        if math.isnan(val):
            return
        abs_val = abs(val)
        if abs_val >= 1.0:
            item.setForeground(QtGui.QColor("#4CAF50"))   # 绿
        elif abs_val < 0.5:
            item.setForeground(QtGui.QColor("#F44336"))   # 红
