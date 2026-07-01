"""
factor_research/ui/overview_tab.py

OverviewTab — 因子概览 Tab。

布局（上下分区）：
┌─────────────────────────────────────────┐
│  合约信息区（QFormLayout）                │
│  vt_symbol / interval / 时间范围 / 条数   │
├─────────────────────────────────────────┤
│  OHLCV 统计摘要表（QTableWidget）         │
│  列：字段 / 均值 / 标准差 / 最小 / 最大 /  │
│       缺失数 / 缺失率                     │
└─────────────────────────────────────────┘

数据来源：
  dispatcher → EVENT_FACTOR_PLOT_READY {"tab":"overview", "payload": OverviewSummary}
  由 FactorResearchWidget 接收后调用 self.overview_tab.update_summary(summary)

设计原则：
  - Tab 不持有 Engine 引用，不访问数据库
  - 所有数据通过 update_summary() 方法注入
  - 空状态显示占位提示文字
"""

from __future__ import annotations

from vnpy.trader.ui import QtCore, QtWidgets

from ..model import OverviewSummary


# 统计表格列定义：(列标题, 对齐方式)
_STAT_COLUMNS: list[tuple[str, QtCore.Qt.AlignmentFlag]] = [
    ("字段",   QtCore.Qt.AlignmentFlag.AlignLeft),
    ("均值",   QtCore.Qt.AlignmentFlag.AlignRight),
    ("标准差", QtCore.Qt.AlignmentFlag.AlignRight),
    ("最小值", QtCore.Qt.AlignmentFlag.AlignRight),
    ("最大值", QtCore.Qt.AlignmentFlag.AlignRight),
    ("缺失数", QtCore.Qt.AlignmentFlag.AlignRight),
    ("缺失率", QtCore.Qt.AlignmentFlag.AlignRight),
]


class OverviewTab(QtWidgets.QWidget):
    """因子概览 Tab。"""

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

        # 上方：合约信息区
        root.addWidget(self._build_info_group())

        # 下方：统计摘要表
        root.addWidget(self._build_stat_group(), stretch=1)

    def _build_info_group(self) -> QtWidgets.QGroupBox:
        group = QtWidgets.QGroupBox("合约信息")
        form = QtWidgets.QFormLayout(group)
        form.setLabelAlignment(QtCore.Qt.AlignmentFlag.AlignRight)
        form.setSpacing(6)
        form.setContentsMargins(8, 8, 8, 8)

        def _label(text: str = "—") -> QtWidgets.QLabel:
            lbl = QtWidgets.QLabel(text)
            lbl.setTextInteractionFlags(
                QtCore.Qt.TextInteractionFlag.TextSelectableByMouse
            )
            return lbl

        self.lbl_symbol    = _label()
        self.lbl_interval  = _label()
        self.lbl_start     = _label()
        self.lbl_end       = _label()
        self.lbl_bars      = _label()
        self.lbl_range     = _label()

        form.addRow("合约代码", self.lbl_symbol)
        form.addRow("K线周期", self.lbl_interval)
        form.addRow("数据开始", self.lbl_start)
        form.addRow("数据结束", self.lbl_end)
        form.addRow("总条数",   self.lbl_bars)
        form.addRow("跨度(天)", self.lbl_range)

        return group

    def _build_stat_group(self) -> QtWidgets.QGroupBox:
        group = QtWidgets.QGroupBox("OHLCV 统计摘要")
        layout = QtWidgets.QVBoxLayout(group)
        layout.setContentsMargins(4, 4, 4, 4)

        self.stat_table = QtWidgets.QTableWidget(0, len(_STAT_COLUMNS))
        self.stat_table.setHorizontalHeaderLabels(
            [col for col, _ in _STAT_COLUMNS]
        )
        self.stat_table.verticalHeader().setVisible(False)
        self.stat_table.setEditTriggers(
            QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers
        )
        self.stat_table.setSelectionBehavior(
            QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows
        )
        self.stat_table.setAlternatingRowColors(True)
        self.stat_table.horizontalHeader().setSectionResizeMode(
            QtWidgets.QHeaderView.ResizeMode.Stretch
        )

        # 占位提示行（无数据时显示）
        self._placeholder = QtWidgets.QLabel(
            "暂无数据\n请在左侧配置区填写参数后点击「运行」"
        )
        self._placeholder.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)

        layout.addWidget(self._placeholder)
        layout.addWidget(self.stat_table)
        self.stat_table.hide()

        return group

    # ------------------------------------------------------------------ #
    #  公开接口（由 FactorResearchWidget 调用）
    # ------------------------------------------------------------------ #

    def update_summary(self, summary: OverviewSummary) -> None:
        """
        将 OverviewSummary 数据渲染到 Tab 中。
        此方法在 Qt 主线程中调用（Signal/Slot 保证）。
        """
        self._update_info(summary)
        self._update_stat_table(summary)

    def clear(self) -> None:
        """重置 Tab 到空状态。"""
        for lbl in (
            self.lbl_symbol, self.lbl_interval, self.lbl_start,
            self.lbl_end, self.lbl_bars, self.lbl_range,
        ):
            lbl.setText("—")
        self.stat_table.setRowCount(0)
        self.stat_table.hide()
        self._placeholder.show()

    # ------------------------------------------------------------------ #
    #  内部渲染
    # ------------------------------------------------------------------ #

    def _update_info(self, summary: OverviewSummary) -> None:
        interval_map = {"d": "日线", "1h": "小时线", "1m": "分钟线", "w": "周线"}
        self.lbl_symbol.setText(summary.vt_symbol)
        self.lbl_interval.setText(
            interval_map.get(summary.interval, summary.interval)
        )
        self.lbl_start.setText(str(summary.data_start) if summary.data_start else "—")
        self.lbl_end.setText(str(summary.data_end)   if summary.data_end   else "—")
        self.lbl_bars.setText(str(summary.total_bars))
        self.lbl_range.setText(str(summary.date_range_days))

    def _update_stat_table(self, summary: OverviewSummary) -> None:
        if not summary.column_stats:
            self.stat_table.hide()
            self._placeholder.show()
            return

        self._placeholder.hide()
        self.stat_table.show()

        rows = summary.column_stats
        self.stat_table.setRowCount(len(rows))

        for row_idx, stat in enumerate(rows):
            values = [
                stat.name,
                f"{stat.mean:,.4f}",
                f"{stat.std:,.4f}",
                f"{stat.min_val:,.4f}",
                f"{stat.max_val:,.4f}",
                str(stat.missing_count),
                f"{stat.missing_pct:.2%}",
            ]
            for col_idx, (value, (_, align)) in enumerate(
                zip(values, _STAT_COLUMNS)
            ):
                item = QtWidgets.QTableWidgetItem(value)
                item.setTextAlignment(
                    int(align | QtCore.Qt.AlignmentFlag.AlignVCenter)
                )
                self.stat_table.setItem(row_idx, col_idx, item)
