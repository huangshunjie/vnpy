"""
factor_research/ui/stability_tab.py

StabilityTab -- Factor stability analysis Tab.

Layout (three sub-plots):
  Plot 1: Monthly IC heatmap (year x month, colour = mean IC)
  Plot 2: Annual IC statistics bar chart (IC mean + ICIR per year)
  Plot 3: IC autocorrelation function (ACF, lag 1..20)

Data flow (zero new events):
  widget._on_plot_ready("ic_series") -> stability_tab.update_stability(IcStats)
"""

from __future__ import annotations

import math

import numpy as np
import pyqtgraph as pg
from pyqtgraph.Qt import QtCore, QtWidgets

from ..engine.stability_engine import StabilityEngine
from ..model import IcStats

_BG       = "#1e1e2e"
_FG       = "#cdd6f4"
_NEG_MAX  = "#ef5350"
_BAR_IC   = "#4fc3f7"
_BAR_ICIR = "#a6e3a1"
_BAR_ACF_POS = "#89dceb"
_BAR_ACF_NEG = "#f38ba8"
_CONF_CLR    = "#fab387"


def _ic_color(ic_val: float, vmax: float = 0.10) -> str:
    """Map IC value to hex colour: red (neg) -> dark (0) -> blue (pos)."""
    if math.isnan(ic_val):
        return "#2a2a3e"
    t = max(-1.0, min(1.0, ic_val / max(vmax, 1e-6)))
    if t >= 0:
        r = int(30 + (79  - 30) * (1 - t))
        g = int(30 + (195 - 30) * (1 - t))
        b = int(46 + (247 - 46) * t)
    else:
        t = -t
        r = int(30 + (239 - 30) * t)
        g = int(30 + (83  - 30) * (1 - t))
        b = int(46 + (78  - 46) * (1 - t))
    return f"#{r:02x}{g:02x}{b:02x}"


class StabilityTab(QtWidgets.QWidget):
    """Factor stability analysis Tab."""

    _MONTH_LABELS = ["Jan","Feb","Mar","Apr","May","Jun",
                     "Jul","Aug","Sep","Oct","Nov","Dec"]

    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self._ic_stats: IcStats | None = None
        self._plot_items: list = []
        self._init_ui()

    def _init_ui(self) -> None:
        root = QtWidgets.QVBoxLayout(self)
        root.setContentsMargins(4, 4, 4, 4)
        root.setSpacing(4)

        self.lbl_info = QtWidgets.QLabel("尚无数据")
        self.lbl_info.setStyleSheet(f"color:{_FG}; font-size:12px;")
        root.addWidget(self.lbl_info)

        self._placeholder = QtWidgets.QLabel("运行分析后将在此显示因子稳定性图表")
        self._placeholder.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self._placeholder.setStyleSheet("color: #6c7086; font-size: 14px;")
        root.addWidget(self._placeholder, stretch=1)

        self._glw = pg.GraphicsLayoutWidget()
        self._glw.setBackground(_BG)
        self._glw.hide()
        root.addWidget(self._glw, stretch=1)

        self._build_plots()

    def _build_plots(self) -> None:
        pg.setConfigOption("antialias", True)

        self._heat_plot = self._glw.addPlot(row=0, col=0, title="月度 IC 热力图")
        self._heat_plot.setLabel("bottom", "月份")
        self._heat_plot.setLabel("left", "年份")
        self._heat_plot.showGrid(x=False, y=False)

        self._annual_plot = self._glw.addPlot(row=1, col=0, title="年度 IC 统计")
        self._annual_plot.setLabel("bottom", "年份")
        self._annual_plot.setLabel("left", "IC 均值 / ICIR")
        self._annual_plot.showGrid(x=False, y=True, alpha=0.3)
        self._annual_plot.addLegend(offset=(10, 10))

        self._acf_plot = self._glw.addPlot(row=2, col=0, title="IC 自相关函数（ACF）")
        self._acf_plot.setLabel("bottom", "滞后期（天）")
        self._acf_plot.setLabel("left", "ACF")
        self._acf_plot.showGrid(x=False, y=True, alpha=0.3)
        self._acf_plot.addLine(y=0, pen=pg.mkPen(_FG, width=1))

        self._glw.ci.layout.setRowStretchFactor(0, 5)
        self._glw.ci.layout.setRowStretchFactor(1, 3)
        self._glw.ci.layout.setRowStretchFactor(2, 3)

    # ------------------------------------------------------------------ #
    #  Public interface
    # ------------------------------------------------------------------ #

    def update_stability(self, stats: IcStats) -> None:
        self._ic_stats = stats
        data = StabilityEngine.compute_all(stats, acf_max_lag=20)
        self._render(stats, data["heatmap"], data["annual"], data["acf"])

    def clear(self) -> None:
        self._ic_stats = None
        self._clear_plots()
        self.lbl_info.setText("尚无数据")
        self._glw.hide()
        self._placeholder.show()

    # ------------------------------------------------------------------ #
    #  Rendering
    # ------------------------------------------------------------------ #

    def _clear_plots(self) -> None:
        self._plot_items.clear()
        self._heat_plot.clear()
        self._annual_plot.clear()
        self._acf_plot.clear()
        self._acf_plot.addLine(y=0, pen=pg.mkPen(_FG, width=1))

    def _render(self, stats, heatmap_df, annual_df, acf_df) -> None:
        self._clear_plots()
        self._draw_heatmap(heatmap_df)
        self._draw_annual(annual_df)
        self._draw_acf(acf_df, stats.sample_size)
        self.lbl_info.setText(
            f"{stats.vt_symbol}  {stats.factor_name}  "
            f"样本 {stats.sample_size} 期  "
            f"IC均值 {stats.ic_mean:.4f}  ICIR {stats.icir:.4f}"
        )
        self._placeholder.hide()
        self._glw.show()

    # ------------------------------------------------------------------ #
    #  Heatmap
    # ------------------------------------------------------------------ #

    def _draw_heatmap(self, matrix_df) -> None:
        if matrix_df is None or matrix_df.empty:
            lbl = pg.TextItem("（IC 序列不足以构建热力图）", color=_FG, anchor=(0.5, 0.5))
            lbl.setPos(6, 0)
            self._heat_plot.addItem(lbl)
            self._plot_items.append(lbl)
            return

        years  = list(matrix_df.index)
        n_years  = len(years)
        n_months = 12

        vals     = matrix_df.values.flatten()
        abs_vals = [abs(v) for v in vals if not np.isnan(v)]
        vmax     = float(np.percentile(abs_vals, 90)) if abs_vals else 0.05
        vmax     = max(vmax, 0.01)

        cell_w, cell_h = 1.0, 1.0

        for yi, year in enumerate(years):
            for mi in range(n_months):
                month = mi + 1
                ic_val = (
                    matrix_df.loc[year, month]
                    if (year in matrix_df.index and month in matrix_df.columns)
                    else float("nan")
                )
                color = _ic_color(ic_val, vmax)
                x = mi * cell_w
                y = yi * cell_h
                rect = QtWidgets.QGraphicsRectItem(x, y, cell_w - 0.05, cell_h - 0.05)
                rect.setBrush(pg.mkBrush(color))
                rect.setPen(pg.mkPen(None))
                self._heat_plot.addItem(rect)
                self._plot_items.append(rect)

                if not math.isnan(ic_val):
                    txt = pg.TextItem(f"{ic_val:.2f}", color=_FG, anchor=(0.5, 0.5))
                    txt.setPos(x + cell_w / 2, y + cell_h / 2)
                    txt.setFont(pg.QtGui.QFont("monospace", 7))
                    self._heat_plot.addItem(txt)
                    self._plot_items.append(txt)

        x_ticks = [(float(i), lbl) for i, lbl in enumerate(self._MONTH_LABELS)]
        y_ticks  = [(float(i), str(y)) for i, y in enumerate(years)]
        self._heat_plot.getAxis("bottom").setTicks([x_ticks])
        self._heat_plot.getAxis("left").setTicks([y_ticks])
        self._heat_plot.setXRange(-0.5, n_months - 0.5, padding=0.02)
        self._heat_plot.setYRange(-0.5, n_years  - 0.5, padding=0.02)

        legend = pg.TextItem(
            f"深蓝=IC>{vmax:.2f}  深红=IC<-{vmax:.2f}  暗色=IC≈0",
            color="#888888", anchor=(0, 1),
        )
        legend.setFont(pg.QtGui.QFont("monospace", 8))
        legend.setPos(0, -0.3)
        self._heat_plot.addItem(legend)
        self._plot_items.append(legend)

    # ------------------------------------------------------------------ #
    #  Annual bar chart
    # ------------------------------------------------------------------ #

    def _draw_annual(self, annual_df) -> None:
        if annual_df is None or annual_df.empty:
            return

        years     = annual_df["年份"].tolist()
        ic_vals   = annual_df["IC 均值"].tolist()
        icir_vals = [v if v is not None else float("nan")
                     for v in annual_df["ICIR"].tolist()]
        n = len(years)
        w = 0.35
        xs = np.arange(n, dtype=float)

        for x, v in zip(xs, ic_vals):
            color = _BAR_IC if v >= 0 else _NEG_MAX
            bar = pg.BarGraphItem(
                x=[x - w / 2], height=[v], width=w * 0.95,
                brush=pg.mkBrush(color), pen=pg.mkPen(None),
            )
            self._annual_plot.addItem(bar)
            self._plot_items.append(bar)

        for x, v in zip(xs, icir_vals):
            if math.isnan(v):
                continue
            color = _BAR_ICIR if v >= 0 else "#f9e2af"
            bar = pg.BarGraphItem(
                x=[x + w / 2], height=[v], width=w * 0.95,
                brush=pg.mkBrush(color), pen=pg.mkPen(None),
            )
            self._annual_plot.addItem(bar)
            self._plot_items.append(bar)

        self._annual_plot.addLine(
            y=0, pen=pg.mkPen(_FG, width=1, style=QtCore.Qt.PenStyle.DashLine)
        )

        ticks = [(float(i), str(y)) for i, y in enumerate(years)]
        self._annual_plot.getAxis("bottom").setTicks([ticks])
        self._annual_plot.setXRange(-0.8, n - 0.2, padding=0)

        # legend colour swatches
        ic_swatch  = pg.BarGraphItem(x=[0], height=[0], width=0, brush=pg.mkBrush(_BAR_IC))
        ici_swatch = pg.BarGraphItem(x=[0], height=[0], width=0, brush=pg.mkBrush(_BAR_ICIR))
        leg = self._annual_plot.legend
        if leg:
            leg.addItem(ic_swatch,  "IC 均值")
            leg.addItem(ici_swatch, "ICIR")
            self._plot_items += [ic_swatch, ici_swatch]

    # ------------------------------------------------------------------ #
    #  ACF bar chart
    # ------------------------------------------------------------------ #

    def _draw_acf(self, acf_df, sample_size: int) -> None:
        if acf_df is None or acf_df.empty:
            return

        lags = acf_df["滞后期"].tolist()
        acfs = acf_df["ACF"].tolist()

        for lag, acf_val in zip(lags, acfs):
            color = _BAR_ACF_POS if acf_val >= 0 else _BAR_ACF_NEG
            bar = pg.BarGraphItem(
                x=[float(lag)], height=[acf_val], width=0.7,
                brush=pg.mkBrush(color), pen=pg.mkPen(None),
            )
            self._acf_plot.addItem(bar)
            self._plot_items.append(bar)

        if sample_size > 1:
            conf = 1.96 / math.sqrt(sample_size)
            for sign in (1, -1):
                line = self._acf_plot.addLine(
                    y=sign * conf,
                    pen=pg.mkPen(_CONF_CLR, width=1,
                                 style=QtCore.Qt.PenStyle.DashLine),
                )
                self._plot_items.append(line)
            ann = pg.TextItem(
                f"95% CI: ±{conf:.3f}", color=_CONF_CLR, anchor=(0, 0),
            )
            ann.setFont(pg.QtGui.QFont("monospace", 8))
            ann.setPos(1, conf + 0.01)
            self._acf_plot.addItem(ann)
            self._plot_items.append(ann)

        self._acf_plot.setXRange(0, len(lags) + 1, padding=0.02)

    # ------------------------------------------------------------------ #
    #  Public interface
    # ------------------------------------------------------------------ #

    def update_stability(self, stats: IcStats) -> None:
        self._ic_stats = stats
        data = StabilityEngine.compute_all(stats, acf_max_lag=20)
        self._render(stats, data["heatmap"], data["annual"], data["acf"])

    def clear(self) -> None:
        self._ic_stats = None
        self._clear_plots()
        self.lbl_info.setText("尚无数据")
        self._glw.hide()
        self._placeholder.show()

    # ------------------------------------------------------------------ #
    #  Rendering
    # ------------------------------------------------------------------ #

    def _clear_plots(self) -> None:
        self._plot_items.clear()
        self._heat_plot.clear()
        self._annual_plot.clear()
        self._acf_plot.clear()
        self._acf_plot.addLine(y=0, pen=pg.mkPen(_FG, width=1))

    def _render(self, stats, heatmap_df, annual_df, acf_df) -> None:
        self._clear_plots()
        self._draw_heatmap(heatmap_df)
        self._draw_annual(annual_df)
        self._draw_acf(acf_df, stats.sample_size)
        self.lbl_info.setText(
            f"{stats.vt_symbol}  {stats.factor_name}  "
            f"样本 {stats.sample_size} 期  "
            f"IC均值 {stats.ic_mean:.4f}  ICIR {stats.icir:.4f}"
        )
        self._placeholder.hide()
        self._glw.show()

    # ------------------------------------------------------------------ #
    #  Heatmap
    # ------------------------------------------------------------------ #

    def _draw_heatmap(self, matrix_df) -> None:
        if matrix_df is None or matrix_df.empty:
            lbl = pg.TextItem("（IC 序列不足以构建热力图）", color=_FG, anchor=(0.5, 0.5))
            lbl.setPos(6, 0)
            self._heat_plot.addItem(lbl)
            self._plot_items.append(lbl)
            return

        years  = list(matrix_df.index)
        n_years  = len(years)
        n_months = 12

        vals     = matrix_df.values.flatten()
        abs_vals = [abs(v) for v in vals if not np.isnan(v)]
        vmax     = float(np.percentile(abs_vals, 90)) if abs_vals else 0.05
        vmax     = max(vmax, 0.01)

        cell_w, cell_h = 1.0, 1.0

        for yi, year in enumerate(years):
            for mi in range(n_months):
                month = mi + 1
                ic_val = (
                    matrix_df.loc[year, month]
                    if (year in matrix_df.index and month in matrix_df.columns)
                    else float("nan")
                )
                color = _ic_color(ic_val, vmax)
                x = mi * cell_w
                y = yi * cell_h
                rect = QtWidgets.QGraphicsRectItem(x, y, cell_w - 0.05, cell_h - 0.05)
                rect.setBrush(pg.mkBrush(color))
                rect.setPen(pg.mkPen(None))
                self._heat_plot.addItem(rect)
                self._plot_items.append(rect)

                if not math.isnan(ic_val):
                    txt = pg.TextItem(f"{ic_val:.2f}", color=_FG, anchor=(0.5, 0.5))
                    txt.setPos(x + cell_w / 2, y + cell_h / 2)
                    txt.setFont(pg.QtGui.QFont("monospace", 7))
                    self._heat_plot.addItem(txt)
                    self._plot_items.append(txt)

        x_ticks = [(float(i), lbl) for i, lbl in enumerate(self._MONTH_LABELS)]
        y_ticks  = [(float(i), str(y)) for i, y in enumerate(years)]
        self._heat_plot.getAxis("bottom").setTicks([x_ticks])
        self._heat_plot.getAxis("left").setTicks([y_ticks])
        self._heat_plot.setXRange(-0.5, n_months - 0.5, padding=0.02)
        self._heat_plot.setYRange(-0.5, n_years  - 0.5, padding=0.02)

        legend = pg.TextItem(
            f"深蓝=IC>{vmax:.2f}  深红=IC<-{vmax:.2f}  暗色=IC≈0",
            color="#888888", anchor=(0, 1),
        )
        legend.setFont(pg.QtGui.QFont("monospace", 8))
        legend.setPos(0, -0.3)
        self._heat_plot.addItem(legend)
        self._plot_items.append(legend)

    # ------------------------------------------------------------------ #
    #  Annual bar chart
    # ------------------------------------------------------------------ #

    def _draw_annual(self, annual_df) -> None:
        if annual_df is None or annual_df.empty:
            return

        years     = annual_df["年份"].tolist()
        ic_vals   = annual_df["IC 均值"].tolist()
        icir_vals = [v if v is not None else float("nan")
                     for v in annual_df["ICIR"].tolist()]
        n = len(years)
        w = 0.35
        xs = np.arange(n, dtype=float)

        for x, v in zip(xs, ic_vals):
            color = _BAR_IC if v >= 0 else _NEG_MAX
            bar = pg.BarGraphItem(
                x=[x - w / 2], height=[v], width=w * 0.95,
                brush=pg.mkBrush(color), pen=pg.mkPen(None),
            )
            self._annual_plot.addItem(bar)
            self._plot_items.append(bar)

        for x, v in zip(xs, icir_vals):
            if math.isnan(v):
                continue
            color = _BAR_ICIR if v >= 0 else "#f9e2af"
            bar = pg.BarGraphItem(
                x=[x + w / 2], height=[v], width=w * 0.95,
                brush=pg.mkBrush(color), pen=pg.mkPen(None),
            )
            self._annual_plot.addItem(bar)
            self._plot_items.append(bar)

        self._annual_plot.addLine(
            y=0, pen=pg.mkPen(_FG, width=1, style=QtCore.Qt.PenStyle.DashLine)
        )

        ticks = [(float(i), str(y)) for i, y in enumerate(years)]
        self._annual_plot.getAxis("bottom").setTicks([ticks])
        self._annual_plot.setXRange(-0.8, n - 0.2, padding=0)

        # legend colour swatches
        ic_swatch  = pg.BarGraphItem(x=[0], height=[0], width=0, brush=pg.mkBrush(_BAR_IC))
        ici_swatch = pg.BarGraphItem(x=[0], height=[0], width=0, brush=pg.mkBrush(_BAR_ICIR))
        leg = self._annual_plot.legend
        if leg:
            leg.addItem(ic_swatch,  "IC 均值")
            leg.addItem(ici_swatch, "ICIR")
            self._plot_items += [ic_swatch, ici_swatch]

    # ------------------------------------------------------------------ #
    #  ACF bar chart
    # ------------------------------------------------------------------ #

    def _draw_acf(self, acf_df, sample_size: int) -> None:
        if acf_df is None or acf_df.empty:
            return

        lags = acf_df["滞后期"].tolist()
        acfs = acf_df["ACF"].tolist()

        for lag, acf_val in zip(lags, acfs):
            color = _BAR_ACF_POS if acf_val >= 0 else _BAR_ACF_NEG
            bar = pg.BarGraphItem(
                x=[float(lag)], height=[acf_val], width=0.7,
                brush=pg.mkBrush(color), pen=pg.mkPen(None),
            )
            self._acf_plot.addItem(bar)
            self._plot_items.append(bar)

        if sample_size > 1:
            conf = 1.96 / math.sqrt(sample_size)
            for sign in (1, -1):
                line = self._acf_plot.addLine(
                    y=sign * conf,
                    pen=pg.mkPen(_CONF_CLR, width=1,
                                 style=QtCore.Qt.PenStyle.DashLine),
                )
                self._plot_items.append(line)
            ann = pg.TextItem(
                f"95% CI: ±{conf:.3f}", color=_CONF_CLR, anchor=(0, 0),
            )
            ann.setFont(pg.QtGui.QFont("monospace", 8))
            ann.setPos(1, conf + 0.01)
            self._acf_plot.addItem(ann)
            self._plot_items.append(ann)

        self._acf_plot.setXRange(0, len(lags) + 1, padding=0.02)
