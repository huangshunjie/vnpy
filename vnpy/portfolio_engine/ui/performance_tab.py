"""
portfolio_engine/ui/performance_tab.py

PerformanceTab — 组合绩效 Tab。

Phase 2 实现：
  - 左侧：净值曲线 + 回撤曲线（pyqtgraph，双子图）
  - 右侧：绩效指标统计表（指标 / 数值）
"""

from __future__ import annotations

import math

import pyqtgraph as pg
from pyqtgraph.Qt import QtCore, QtWidgets

_BG      = "#1e1e2e"
_FG      = "#cdd6f4"
_NAV_CLR = "#4fc3f7"
_DD_CLR  = "#f38ba8"
_ZERO    = "#45475a"

_STATS_ROWS = [
    ("年化收益率",  "annual_return",  "{:.2%}"),
    ("总收益率",    "total_return",   "{:.2%}"),
    ("Sharpe",     "sharpe_ratio",   "{:.3f}"),
    ("Calmar",     "calmar_ratio",   "{:.3f}"),
    ("最大回撤",    "max_drawdown",   "{:.2%}"),
    ("年化波动率",  "volatility",     "{:.2%}"),
    ("日胜率",     "win_rate",       "{:.2%}"),
]


class PerformanceTab(QtWidgets.QWidget):
    """组合绩效 Tab（Phase 2 实现）。"""

    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self._plot_items: list = []
        self._init_ui()

    # ------------------------------------------------------------------ #
    #  UI
    # ------------------------------------------------------------------ #

    def _init_ui(self) -> None:
        root = QtWidgets.QHBoxLayout(self)
        root.setContentsMargins(4, 4, 4, 4)
        root.setSpacing(6)

        # 左：图表
        left = QtWidgets.QVBoxLayout()
        left.setContentsMargins(0, 0, 0, 0)

        self._glw = pg.GraphicsLayoutWidget()
        self._glw.setBackground(_BG)
        self._nav_plot = self._glw.addPlot(row=0, col=0, title="净值曲线")
        self._nav_plot.setLabel("left", "净值")
        self._nav_plot.showGrid(x=True, y=True, alpha=0.2)
        self._nav_plot.addLine(y=1.0, pen=pg.mkPen(_ZERO, width=1,
                               style=QtCore.Qt.PenStyle.DashLine))

        self._dd_plot = self._glw.addPlot(row=1, col=0, title="回撤")
        self._dd_plot.setLabel("left", "回撤")
        self._dd_plot.setXLink(self._nav_plot)
        self._dd_plot.showGrid(x=True, y=True, alpha=0.2)
        self._dd_plot.addLine(y=0, pen=pg.mkPen(_ZERO, width=1))
        self._glw.ci.layout.setRowStretchFactor(0, 3)
        self._glw.ci.layout.setRowStretchFactor(1, 1)

        self._placeholder = QtWidgets.QLabel("运行分析后将在此显示绩效图表")
        self._placeholder.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self._placeholder.setStyleSheet("color: #6c7086; font-size: 13px;")
        left.addWidget(self._placeholder, stretch=1)
        left.addWidget(self._glw, stretch=1)
        self._glw.hide()

        root.addLayout(left, stretch=3)

        # 右：统计表
        right = QtWidgets.QVBoxLayout()
        right.setContentsMargins(0, 0, 0, 0)
        right.setSpacing(4)

        title = QtWidgets.QLabel("绩效统计")
        title.setStyleSheet("color: #6c7086; font-size: 11px; font-weight: bold;")
        right.addWidget(title)

        self._stats_table = QtWidgets.QTableWidget(len(_STATS_ROWS), 2)
        self._stats_table.setHorizontalHeaderLabels(["指标", "数值"])
        self._stats_table.horizontalHeader().setStretchLastSection(True)
        self._stats_table.verticalHeader().setVisible(False)
        self._stats_table.setEditTriggers(
            QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers
        )
        self._stats_table.setFixedWidth(220)
        for i, (label, _, _) in enumerate(_STATS_ROWS):
            self._stats_table.setItem(i, 0, _item(label, bold=True))
            self._stats_table.setItem(i, 1, _item("—"))

        right.addWidget(self._stats_table)
        right.addStretch()
        root.addLayout(right, stretch=1)

    # ------------------------------------------------------------------ #
    #  公开接口
    # ------------------------------------------------------------------ #

    def update_performance(self, stats) -> None:
        """接收 PerformanceStats，刷新图表和统计表。"""
        self._update_stats_table(stats)
        if stats.is_valid and stats.nav_series is not None:
            self._draw_charts(stats.nav_series)
            self._placeholder.hide()
            self._glw.show()

    def clear(self) -> None:
        for i in range(self._stats_table.rowCount()):
            self._stats_table.setItem(i, 1, _item("—"))
        self._clear_plots()
        self._glw.hide()
        self._placeholder.show()

    # ------------------------------------------------------------------ #
    #  内部
    # ------------------------------------------------------------------ #

    def _update_stats_table(self, stats) -> None:
        for i, (_, key, fmt) in enumerate(_STATS_ROWS):
            val = getattr(stats, key, float("nan"))
            if val is None or (isinstance(val, float) and math.isnan(val)):
                text  = "—"
                color = _FG
            else:
                text = fmt.format(val)
                if key in ("annual_return", "total_return",
                           "sharpe_ratio", "calmar_ratio", "win_rate"):
                    color = "#a6e3a1" if val >= 0 else "#f38ba8"
                elif key == "max_drawdown":
                    color = "#f38ba8" if val < 0 else "#a6e3a1"
                else:
                    color = _FG
            item = _item(text)
            item.setForeground(pg.mkColor(color))
            self._stats_table.setItem(i, 1, item)

    def _clear_plots(self) -> None:
        self._nav_plot.clear()
        self._dd_plot.clear()
        self._nav_plot.addLine(y=1.0, pen=pg.mkPen(_ZERO, width=1,
                               style=QtCore.Qt.PenStyle.DashLine))
        self._dd_plot.addLine(y=0, pen=pg.mkPen(_ZERO, width=1))
        self._plot_items.clear()

    def _draw_charts(self, nav_series) -> None:
        import pandas as pd
        self._clear_plots()
        nav = nav_series.dropna()
        if nav.empty:
            return

        xs = [ts.timestamp() for ts in pd.to_datetime(nav.index)]
        ys = nav.values.tolist()

        self._nav_plot.plot(xs, ys, pen=pg.mkPen(_NAV_CLR, width=2))

        rolling_peak = nav.cummax()
        dd = (nav / rolling_peak - 1.0).values.tolist()
        dd_curve = self._dd_plot.plot(xs, dd, pen=pg.mkPen(_DD_CLR, width=1))
        zero_line = self._dd_plot.plot(xs, [0.0] * len(xs), pen=pg.mkPen(None))
        fill = pg.FillBetweenItem(dd_curve, zero_line,
                                   brush=pg.mkBrush(_DD_CLR + "44"))
        self._dd_plot.addItem(fill)
        self._plot_items.append(fill)


def _item(text: str, bold: bool = False) -> QtWidgets.QTableWidgetItem:
    item = QtWidgets.QTableWidgetItem(str(text))
    item.setTextAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
    if bold:
        f = item.font()
        f.setBold(True)
        item.setFont(f)
    return item
