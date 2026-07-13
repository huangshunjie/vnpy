"""
portfolio_engine/ui/overview_tab.py

OverviewTab -- 组合概览 Tab。

Phase 2 实现：
  - 顶部关键指标摘要行（年化收益 / Sharpe / MDD / Calmar / 波动率）
  - 净值曲线折线图（pyqtgraph）
  - 回撤曲线折线图（叠加在净值图下方）
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

_METRICS = [
    ("年化收益", "annual_return",  "{:.2%}"),
    ("Sharpe",  "sharpe_ratio",   "{:.3f}"),
    ("最大回撤", "max_drawdown",   "{:.2%}"),
    ("Calmar",  "calmar_ratio",   "{:.3f}"),
    ("波动率",  "volatility",     "{:.2%}"),
    ("日胜率",  "win_rate",       "{:.2%}"),
    ("总收益",  "total_return",   "{:.2%}"),
]


class OverviewTab(QtWidgets.QWidget):
    """组合概览 Tab（Phase 2 实现）。"""

    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self._plot_items: list = []
        self._init_ui()

    # ------------------------------------------------------------------ #
    #  UI
    # ------------------------------------------------------------------ #

    def _init_ui(self) -> None:
        root = QtWidgets.QVBoxLayout(self)
        root.setContentsMargins(4, 4, 4, 4)
        root.setSpacing(4)

        # 指标摘要行
        self._metrics_bar = self._build_metrics_bar()
        root.addWidget(self._metrics_bar)

        # 占位提示
        self._placeholder = QtWidgets.QLabel("运行分析后将在此显示组合净值曲线")
        self._placeholder.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self._placeholder.setStyleSheet("color: #6c7086; font-size: 13px;")
        root.addWidget(self._placeholder, stretch=1)

        # 图表容器
        self._glw = pg.GraphicsLayoutWidget()
        self._glw.setBackground(_BG)
        self._glw.hide()
        root.addWidget(self._glw, stretch=1)

        self._build_plots()

    def _build_metrics_bar(self) -> QtWidgets.QWidget:
        bar = QtWidgets.QWidget()
        bar.setStyleSheet("background: #181825; border-radius: 4px;")
        layout = QtWidgets.QHBoxLayout(bar)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(16)

        self._metric_labels: dict[str, QtWidgets.QLabel] = {}
        for label, key, _ in _METRICS:
            col = QtWidgets.QVBoxLayout()
            col.setSpacing(0)
            lbl_name = QtWidgets.QLabel(label)
            lbl_name.setStyleSheet("color: #6c7086; font-size: 10px;")
            lbl_name.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
            lbl_val = QtWidgets.QLabel("—")
            lbl_val.setStyleSheet(f"color: {_FG}; font-size: 14px; font-weight: bold;")
            lbl_val.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
            col.addWidget(lbl_name)
            col.addWidget(lbl_val)
            self._metric_labels[key] = lbl_val
            layout.addLayout(col)

        return bar

    def _build_plots(self) -> None:
        pg.setConfigOption("antialias", True)

        # NAV plot
        self._nav_plot = self._glw.addPlot(row=0, col=0, title="组合净值")
        self._nav_plot.setLabel("left", "净值")
        self._nav_plot.showGrid(x=True, y=True, alpha=0.2)
        self._nav_plot.addLine(y=1.0, pen=pg.mkPen(_ZERO, width=1,
                               style=QtCore.Qt.PenStyle.DashLine))

        # Drawdown plot
        self._dd_plot = self._glw.addPlot(row=1, col=0, title="回撤")
        self._dd_plot.setLabel("left", "回撤")
        self._dd_plot.setXLink(self._nav_plot)
        self._dd_plot.showGrid(x=True, y=True, alpha=0.2)
        self._dd_plot.addLine(y=0, pen=pg.mkPen(_ZERO, width=1))

        self._glw.ci.layout.setRowStretchFactor(0, 3)
        self._glw.ci.layout.setRowStretchFactor(1, 1)

    # ------------------------------------------------------------------ #
    #  公开接口
    # ------------------------------------------------------------------ #

    def update_performance(self, stats) -> None:
        """接收 PerformanceStats，刷新指标摘要行和图表。"""
        self._update_metrics(stats)
        if stats.is_valid and stats.nav_series is not None:
            self._draw_charts(stats.nav_series)
        self._placeholder.hide()
        self._glw.show()

    def clear(self) -> None:
        for lbl in self._metric_labels.values():
            lbl.setText("—")
            lbl.setStyleSheet(f"color: {_FG}; font-size: 14px; font-weight: bold;")
        self._clear_plots()
        self._glw.hide()
        self._placeholder.show()

    # ------------------------------------------------------------------ #
    #  内部
    # ------------------------------------------------------------------ #

    def _update_metrics(self, stats) -> None:
        for _, key, fmt in _METRICS:
            val = getattr(stats, key, float("nan"))
            lbl = self._metric_labels[key]
            if val is None or (isinstance(val, float) and math.isnan(val)):
                lbl.setText("—")
                lbl.setStyleSheet(f"color: {_FG}; font-size: 14px; font-weight: bold;")
                continue
            text = fmt.format(val)
            # 正负着色
            if key in ("annual_return", "total_return", "win_rate",
                       "sharpe_ratio", "calmar_ratio"):
                color = "#a6e3a1" if val >= 0 else "#f38ba8"
            elif key == "max_drawdown":
                color = "#f38ba8" if val < 0 else "#a6e3a1"
            else:
                color = _FG
            lbl.setText(text)
            lbl.setStyleSheet(
                f"color: {color}; font-size: 14px; font-weight: bold;"
            )

    def _clear_plots(self) -> None:
        for item in self._plot_items:
            try:
                item.getViewBox().removeItem(item)
            except Exception:
                pass
        self._plot_items.clear()
        self._nav_plot.clear()
        self._dd_plot.clear()
        self._nav_plot.addLine(y=1.0, pen=pg.mkPen(_ZERO, width=1,
                               style=QtCore.Qt.PenStyle.DashLine))
        self._dd_plot.addLine(y=0, pen=pg.mkPen(_ZERO, width=1))

    def _draw_charts(self, nav_series) -> None:
        self._clear_plots()
        import pandas as pd

        nav = nav_series.dropna()
        if nav.empty:
            return

        # x 轴：unix timestamp
        xs = [ts.timestamp() for ts in pd.to_datetime(nav.index)]
        ys = nav.values.tolist()

        # NAV 曲线
        curve_nav = self._nav_plot.plot(
            xs, ys,
            pen=pg.mkPen(_NAV_CLR, width=2),
            name="净值",
        )
        self._plot_items.append(curve_nav)

        # 回撤曲线
        rolling_peak = nav.cummax()
        dd = (nav / rolling_peak - 1.0).values.tolist()
        dd_fill = pg.FillBetweenItem(
            self._dd_plot.plot(xs, dd, pen=pg.mkPen(_DD_CLR, width=1)),
            self._dd_plot.plot(xs, [0.0] * len(xs),
                               pen=pg.mkPen(None)),
            brush=pg.mkBrush(_DD_CLR + "44"),
        )
        self._dd_plot.addItem(dd_fill)
        self._plot_items.append(dd_fill)

        # x 轴格式化为日期
        for plot in (self._nav_plot, self._dd_plot):
            ax = plot.getAxis("bottom")
            ax.setStyle(tickFont=pg.QtGui.QFont("monospace", 8))
