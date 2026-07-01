"""
factor_research/ui/correlation_tab.py

CorrelationTab -- Factor IC correlation heatmap Tab.

Layout:
┌──────────────────────────────────────────────────┐
│  toolbar: [清空] factor_count_label  info_label   │
├───────────────────────────────┬──────────────────┤
│  Heatmap (N×N Pearson corr)   │  IC series lines  │
│  (PyQtGraph manual grid)      │  (per factor)     │
└───────────────────────────────┴──────────────────┘

Data flow:
  widget._on_plot_ready("correlation") -> feed_ic(IcStats)
  Each call accumulates one factor's IC series.
  When >= 2 factors are collected, recompute and redraw.

Threshold: default 0.70 (highlighted in heatmap cells).
"""

from __future__ import annotations

import math

import numpy as np
import pyqtgraph as pg
from pyqtgraph.Qt import QtCore, QtWidgets

from ..engine.redundancy_engine import CorrelationResult, RedundancyEngine
from ..model import IcStats

_BG       = "#1e1e2e"
_FG       = "#cdd6f4"
_POS_CLR  = "#4fc3f7"   # high positive corr -> blue
_NEG_CLR  = "#ef5350"   # high negative corr -> red
_DIAG_CLR = "#313244"   # diagonal (self-corr = 1)
_GRID_CLR = "#45475a"
_LINE_PALETTE = [
    "#4fc3f7", "#a6e3a1", "#fab387",
    "#f38ba8", "#cba6f7", "#f9e2af",
]

_DEFAULT_THRESHOLD = 0.70


def _corr_color(v: float) -> str:
    """Pearson corr [-1, 1] -> hex colour (red=neg, blue=pos)."""
    if math.isnan(v):
        return "#313244"
    t = max(-1.0, min(1.0, v))
    if t >= 0:
        r = int(30  + (30  - 30) * t)
        g = int(30  + (195 - 30) * t)
        b = int(46  + (247 - 46) * t)
    else:
        t = -t
        r = int(30  + (239 - 30) * t)
        g = int(30  + (30  - 30) * t)
        b = int(46  + (46  - 46) * t)
    return f"#{r:02x}{g:02x}{b:02x}"


class CorrelationTab(QtWidgets.QWidget):
    """Factor IC correlation matrix heatmap Tab."""

    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self._ic_list: list[IcStats] = []
        self._result: CorrelationResult | None = None
        self._plot_items: list = []
        self._line_items: list = []
        self._threshold = _DEFAULT_THRESHOLD
        self._init_ui()

    # ------------------------------------------------------------------ #
    #  UI
    # ------------------------------------------------------------------ #

    def _init_ui(self) -> None:
        root = QtWidgets.QVBoxLayout(self)
        root.setContentsMargins(4, 4, 4, 4)
        root.setSpacing(4)
        root.addWidget(self._build_toolbar())

        self._placeholder = QtWidgets.QLabel(
            "每运行一个因子后，其 IC 序列将在此累积。\n"
            "积累 ≥ 2 个因子后自动绘制相关矩阵热力图。"
        )
        self._placeholder.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self._placeholder.setStyleSheet("color: #6c7086; font-size: 13px;")
        root.addWidget(self._placeholder, stretch=1)

        self._glw = pg.GraphicsLayoutWidget()
        self._glw.setBackground(_BG)
        self._glw.hide()
        root.addWidget(self._glw, stretch=1)

        self._build_plots()

    def _build_toolbar(self) -> QtWidgets.QWidget:
        bar = QtWidgets.QWidget()
        layout = QtWidgets.QHBoxLayout(bar)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        btn_clear = QtWidgets.QPushButton("清空因子列表")
        btn_clear.setFixedHeight(26)
        btn_clear.clicked.connect(self.clear)

        self.lbl_count = QtWidgets.QLabel("已积累 0 个因子")
        self.lbl_count.setStyleSheet(f"color:{_FG};")

        self.spin_threshold = QtWidgets.QDoubleSpinBox()
        self.spin_threshold.setRange(0.50, 0.99)
        self.spin_threshold.setSingleStep(0.05)
        self.spin_threshold.setValue(_DEFAULT_THRESHOLD)
        self.spin_threshold.setDecimals(2)
        self.spin_threshold.setFixedWidth(70)
        self.spin_threshold.setToolTip("高相关阈值（|r| ≥ 此值视为冗余）")
        self.spin_threshold.valueChanged.connect(self._on_threshold_changed)

        self.lbl_info = QtWidgets.QLabel("")
        self.lbl_info.setStyleSheet("color: #6c7086; font-size: 11px;")

        layout.addWidget(btn_clear)
        layout.addWidget(QtWidgets.QLabel("冗余阈值"))
        layout.addWidget(self.spin_threshold)
        layout.addWidget(self.lbl_count)
        layout.addStretch()
        layout.addWidget(self.lbl_info)
        return bar

    def _build_plots(self) -> None:
        pg.setConfigOption("antialias", True)
        self._heat_plot = self._glw.addPlot(row=0, col=0, title="IC 序列 Pearson 相关矩阵")
        self._heat_plot.setAspectLocked(True)
        self._heat_plot.showGrid(x=False, y=False)
        self._heat_plot.getAxis("bottom").setStyle(
            tickFont=pg.QtGui.QFont("monospace", 8)
        )
        self._heat_plot.getAxis("left").setStyle(
            tickFont=pg.QtGui.QFont("monospace", 8)
        )

        self._line_plot = self._glw.addPlot(row=0, col=1, title="IC 时序对比")
        self._line_plot.setLabel("bottom", "时间")
        self._line_plot.setLabel("left", "IC")
        self._line_plot.showGrid(x=True, y=True, alpha=0.2)
        self._line_plot.addLegend(offset=(10, 10))

        self._glw.ci.layout.setColumnStretchFactor(0, 1)
        self._glw.ci.layout.setColumnStretchFactor(1, 2)

    # ------------------------------------------------------------------ #
    #  Public interface
    # ------------------------------------------------------------------ #

    def feed_ic(self, stats: IcStats) -> None:
        """Accumulate one factor's IcStats. Recompute when >= 2 factors."""
        if stats.ic_series is None or stats.ic_series.dropna().empty:
            return
        # replace existing entry for same factor_name
        self._ic_list = [s for s in self._ic_list
                         if s.factor_name != stats.factor_name]
        self._ic_list.append(stats)
        self._recompute()

    def clear(self) -> None:
        self._ic_list.clear()
        self._result = None
        self._clear_plots()
        self.lbl_count.setText("已积累 0 个因子")
        self.lbl_info.setText("")
        self._glw.hide()
        self._placeholder.show()

    # ------------------------------------------------------------------ #
    #  Internal
    # ------------------------------------------------------------------ #

    def _on_threshold_changed(self, value: float) -> None:
        self._threshold = value
        if self._result is not None:
            self._recompute()

    def _recompute(self) -> None:
        n = len(self._ic_list)
        self.lbl_count.setText(f"已积累 {n} 个因子")
        if n < 1:
            return
        self._result = RedundancyEngine.compute(
            self._ic_list, threshold=self._threshold
        )
        self._render()

    def _clear_plots(self) -> None:
        for item in self._plot_items:
            try:
                self._heat_plot.removeItem(item)
            except Exception:
                pass
        self._plot_items.clear()
        for item in self._line_items:
            try:
                self._line_plot.removeItem(item)
            except Exception:
                pass
        self._line_items.clear()
        self._heat_plot.clear()
        self._line_plot.clear()

    def _render(self) -> None:
        if self._result is None:
            return
        self._clear_plots()
        self._draw_heatmap(self._result)
        self._draw_lines()
        n   = len(self._result.factor_names)
        red = len(RedundancyEngine.redundant_only(self._result))
        self.lbl_info.setText(
            f"{n} 个因子  对齐样本 {self._result.n_samples} 期  "
            f"冗余对 {red} / {len(self._result.redundant_pairs)}"
        )
        self._placeholder.hide()
        self._glw.show()

    # ------------------------------------------------------------------ #
    #  Heatmap
    # ------------------------------------------------------------------ #

    def _draw_heatmap(self, result: CorrelationResult) -> None:
        names = result.factor_names
        n     = len(names)
        corr  = result.corr_matrix
        cell  = 1.0

        for i, row_name in enumerate(names):
            for j, col_name in enumerate(names):
                v     = float(corr.loc[row_name, col_name])
                color = _corr_color(v)
                rect  = QtWidgets.QGraphicsRectItem(
                    j * cell, i * cell, cell - 0.04, cell - 0.04
                )
                rect.setBrush(pg.mkBrush(color))
                # highlight redundant off-diagonal cells with a border
                if i != j and abs(v) >= result.threshold:
                    rect.setPen(pg.mkPen("#ffd700", width=2))
                else:
                    rect.setPen(pg.mkPen(None))
                self._heat_plot.addItem(rect)
                self._plot_items.append(rect)

                # value text
                txt_color = "#ffffff" if abs(v) > 0.5 else _FG
                txt = pg.TextItem(
                    f"{v:.2f}", color=txt_color, anchor=(0.5, 0.5)
                )
                txt.setFont(pg.QtGui.QFont("monospace", 8))
                txt.setPos(j * cell + cell / 2, i * cell + cell / 2)
                self._heat_plot.addItem(txt)
                self._plot_items.append(txt)

        # axis ticks: abbreviated factor names
        short = [self._short_name(nm) for nm in names]
        x_ticks = [(float(j) + 0.5, short[j]) for j in range(n)]
        y_ticks  = [(float(i) + 0.5, short[i]) for i in range(n)]
        self._heat_plot.getAxis("bottom").setTicks([x_ticks])
        self._heat_plot.getAxis("left").setTicks([y_ticks])
        self._heat_plot.setXRange(0, n, padding=0.02)
        self._heat_plot.setYRange(0, n, padding=0.02)

        # colour scale legend
        leg = pg.TextItem(
            f"深蓝=r≈+1  深红=r≈-1  金框=|r|≥{result.threshold:.2f}",
            color="#888888", anchor=(0, 0),
        )
        leg.setFont(pg.QtGui.QFont("monospace", 8))
        leg.setPos(0, n + 0.05)
        self._heat_plot.addItem(leg)
        self._plot_items.append(leg)

    # ------------------------------------------------------------------ #
    #  IC time-series overlay
    # ------------------------------------------------------------------ #

    def _draw_lines(self) -> None:
        if not self._ic_list:
            return
        self._line_plot.addLegend(offset=(10, 10))
        for idx, stats in enumerate(self._ic_list):
            if stats.ic_series is None:
                continue
            sr = stats.ic_series.dropna()
            if sr.empty:
                continue
            import pandas as pd
            xs = [ts.timestamp() for ts in pd.to_datetime(sr.index)]
            ys = sr.values.tolist()
            color = _LINE_PALETTE[idx % len(_LINE_PALETTE)]
            curve = self._line_plot.plot(
                xs, ys,
                pen=pg.mkPen(color, width=1.5),
                name=self._short_name(stats.factor_name),
            )
            self._line_items.append(curve)

        # zero line
        zero = self._line_plot.addLine(
            y=0, pen=pg.mkPen(_FG, width=1,
                              style=QtCore.Qt.PenStyle.DashLine)
        )
        self._line_items.append(zero)

        # format x-axis as date
        self._line_plot.getAxis("bottom").setStyle(
            tickFont=pg.QtGui.QFont("monospace", 8)
        )

    # ------------------------------------------------------------------ #
    #  Helpers
    # ------------------------------------------------------------------ #

    @staticmethod
    def _short_name(name: str, max_len: int = 16) -> str:
        return name if len(name) <= max_len else name[:max_len - 2] + ".."
