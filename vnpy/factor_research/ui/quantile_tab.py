"""
factor_research/ui/quantile_tab.py

QuantileTab — 分层收益 Tab。

图表布局（上下两个 PyQtGraph 子图）：
  上图：Q1～Q5 累计收益折线（渐变色） + Long-Short 红色虚线
  下图：各档年化收益柱状图（正蓝/负橙） + 单调性评分标注

工具栏（图表上方）：
  ☑Q1 ☑Q2 ☑Q3 ☑Q4 ☑Q5 ☑Long-Short ☑年化收益 [重置缩放] + 信息标签

颜色设计（Q1→Q5 蓝色渐变，Low→High）：
  Q1 = #AECBF0（浅蓝）
  Q2 = #7FAFD9
  Q3 = #5B9BD5（中蓝）
  Q4 = #3A7AB5
  Q5 = #1A5794（深蓝）
  Long-Short = #E53935（红）
"""

from __future__ import annotations

import math

import numpy as np
import pyqtgraph as pg

from vnpy.trader.ui import QtCore, QtWidgets

from ..model import QuantileResult


_Q_COLORS = ["#AECBF0", "#7FAFD9", "#5B9BD5", "#3A7AB5", "#1A5794"]
_LS_COLOR  = "#E53935"
_POS_COLOR = "#5B9BD5"
_NEG_COLOR = "#ED7D31"
_ZERO_CLR  = "#888888"
_BAR_W     = 0.55


class _DateAxisItem(pg.AxisItem):
    """unix 秒 → YYYY-MM-DD。"""

    def tickStrings(self, values, scale, spacing):
        from datetime import datetime, timezone
        out = []
        for v in values:
            try:
                out.append(datetime.fromtimestamp(v, tz=timezone.utc).strftime("%Y-%m-%d"))
            except Exception:
                out.append("")
        return out


class QuantileTab(QtWidgets.QWidget):
    """分层收益 Tab（PyQtGraph）。"""

    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self._q_labels: list[str] = []
        self._init_ui()

    # ------------------------------------------------------------------ #
    #  UI 构建
    # ------------------------------------------------------------------ #

    def _init_ui(self) -> None:
        root = QtWidgets.QVBoxLayout(self)
        root.setContentsMargins(4, 4, 4, 4)
        root.setSpacing(4)
        root.addWidget(self._build_toolbar())
        root.addWidget(self._build_chart(), stretch=1)

    def _build_toolbar(self) -> QtWidgets.QWidget:
        bar = QtWidgets.QWidget(self)
        layout = QtWidgets.QHBoxLayout(bar)
        layout.setContentsMargins(4, 0, 4, 0)
        layout.setSpacing(8)

        self._chk_q: list[QtWidgets.QCheckBox] = []
        for i, color in enumerate(_Q_COLORS, 1):
            chk = QtWidgets.QCheckBox(f"Q{i}")
            chk.setChecked(True)
            chk.setStyleSheet(f"color: {color}; font-weight: bold;")
            chk.toggled.connect(self._on_visibility_changed)
            self._chk_q.append(chk)
            layout.addWidget(chk)

        self.chk_ls  = QtWidgets.QCheckBox("L-S")
        self.chk_ls.setChecked(True)
        self.chk_ls.setStyleSheet(f"color: {_LS_COLOR}; font-weight: bold;")
        self.chk_ls.toggled.connect(self._on_visibility_changed)

        self.chk_bar = QtWidgets.QCheckBox("年化收益")
        self.chk_bar.setChecked(True)
        self.chk_bar.toggled.connect(self._on_visibility_changed)

        btn_reset = QtWidgets.QPushButton("重置缩放")
        btn_reset.setFixedWidth(80)
        btn_reset.clicked.connect(self._reset_zoom)

        self.lbl_info = QtWidgets.QLabel("")
        self.lbl_info.setAlignment(QtCore.Qt.AlignmentFlag.AlignRight)

        layout.addWidget(self.chk_ls)
        layout.addWidget(self.chk_bar)
        layout.addWidget(btn_reset)
        layout.addStretch()
        layout.addWidget(self.lbl_info)
        return bar

    def _build_chart(self) -> QtWidgets.QWidget:
        container = QtWidgets.QWidget(self)
        v = QtWidgets.QVBoxLayout(container)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(0)

        self._placeholder = QtWidgets.QLabel(
            "暂无数据\n请在左侧配置区填写参数后点击「运行」"
        )
        self._placeholder.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)

        pg.setConfigOptions(antialias=True, background="#1E1E1E", foreground="#CCCCCC")
        self._glw = pg.GraphicsLayoutWidget()

        # ── 上图：累计收益折线 ──
        self._plot_cum = self._glw.addPlot(
            row=0, col=0,
            axisItems={"bottom": _DateAxisItem(orientation="bottom")},
            title="各档位累计收益",
        )
        self._plot_cum.showGrid(x=True, y=True, alpha=0.3)
        self._plot_cum.setLabel("left", "累计收益")
        self._plot_cum.addLegend(offset=(10, 10))

        self._zero_cum = pg.InfiniteLine(
            pos=0, angle=0,
            pen=pg.mkPen(color=_ZERO_CLR,
                         style=QtCore.Qt.PenStyle.DashLine, width=1),
        )
        self._plot_cum.addItem(self._zero_cum)

        self._curves_q: list[pg.PlotDataItem] = []
        for i, color in enumerate(_Q_COLORS):
            curve = self._plot_cum.plot(
                [], [], name=f"Q{i+1}",
                pen=pg.mkPen(color=color, width=1.8),
            )
            self._curves_q.append(curve)

        self._curve_ls = self._plot_cum.plot(
            [], [], name="Long-Short",
            pen=pg.mkPen(color=_LS_COLOR, width=2,
                         style=QtCore.Qt.PenStyle.DashLine),
        )

        # ── 下图：年化收益柱状图 ──
        self._plot_ann = self._glw.addPlot(
            row=1, col=0,
            title="各档位年化收益",
        )
        self._plot_ann.showGrid(x=False, y=True, alpha=0.3)
        self._plot_ann.setLabel("left", "年化收益")
        self._plot_ann.setLabel("bottom", "档位")

        self._zero_ann = pg.InfiniteLine(
            pos=0, angle=0,
            pen=pg.mkPen(color=_ZERO_CLR,
                         style=QtCore.Qt.PenStyle.DashLine, width=1),
        )
        self._plot_ann.addItem(self._zero_ann)

        self._bar_ann_pos = pg.BarGraphItem(
            x=[], height=[], width=_BAR_W, brush=_POS_COLOR, pen=None,
        )
        self._bar_ann_neg = pg.BarGraphItem(
            x=[], height=[], width=_BAR_W, brush=_NEG_COLOR, pen=None,
        )
        self._plot_ann.addItem(self._bar_ann_pos)
        self._plot_ann.addItem(self._bar_ann_neg)

        # 单调性评分文本标注
        self._mono_text = pg.TextItem(text="", color="#FFEB3B", anchor=(1, 0))
        self._plot_ann.addItem(self._mono_text)

        # Long-Short 年化柱（独立颜色）
        self._bar_ls = pg.BarGraphItem(
            x=[], height=[], width=_BAR_W, brush=_LS_COLOR, pen=None,
        )
        self._plot_ann.addItem(self._bar_ls)

        self._glw.ci.layout.setRowStretchFactor(0, 3)
        self._glw.ci.layout.setRowStretchFactor(1, 2)

        v.addWidget(self._placeholder)
        v.addWidget(self._glw)
        self._glw.hide()
        return container

    # ------------------------------------------------------------------ #
    #  公开接口
    # ------------------------------------------------------------------ #

    def update_quantile(self, result: QuantileResult) -> None:
        """将 QuantileResult 渲染到图表。Qt 主线程调用。"""
        if not result.is_valid():
            return

        self._q_labels = result.quantile_labels
        n = len(self._q_labels)

        # ── 上图：累计折线 ──
        for i, ql in enumerate(self._q_labels):
            cum = result.cumulative_returns.get(ql)
            if cum is not None and not cum.empty:
                x, y = self._series_to_xy(cum)
                self._curves_q[i].setData(x, y)
            else:
                self._curves_q[i].setData([], [])

        # 隐藏多余曲线（如分档数 < 5）
        for i in range(n, len(self._curves_q)):
            self._curves_q[i].setData([], [])

        # Long-Short 曲线
        if result.long_short_series is not None and not result.long_short_series.empty:
            x_ls, y_ls = self._series_to_xy(result.long_short_series)
            self._curve_ls.setData(x_ls, y_ls)
        else:
            self._curve_ls.setData([], [])

        # ── 下图：年化收益柱 ──
        x_pos = np.arange(1, n + 1, dtype=float)
        ann_vals = np.array(
            [result.annualized_returns.get(ql, float("nan")) for ql in self._q_labels],
            dtype=float,
        )
        self._set_bar_split(self._bar_ann_pos, self._bar_ann_neg, x_pos, ann_vals)

        # Long-Short 年化（放在 x = n+1）
        ls_ann = result.long_short_annualized
        if not math.isnan(ls_ann):
            self._bar_ls.setOpts(x=[n + 1.5], height=[ls_ann], width=_BAR_W)
        else:
            self._bar_ls.setOpts(x=[], height=[], width=_BAR_W)

        # x 轴刻度标签
        tick_labels = [(i + 1, ql) for i, ql in enumerate(self._q_labels)]
        tick_labels.append((n + 1.5, "L-S"))
        self._plot_ann.getAxis("bottom").setTicks([tick_labels])

        # 单调性评分文本
        if not math.isnan(result.monotonicity_score):
            self._mono_text.setText(
                f"单调性={result.monotonicity_score:.3f}"
            )
            view_range = self._plot_ann.viewRange()
            self._mono_text.setPos(n + 1.5, view_range[1][1])
        else:
            self._mono_text.setText("")

        # 信息标签
        self.lbl_info.setText(
            f"{result.vt_symbol}  {result.factor_name}  lag={result.lag}  "
            f"样本={result.sample_size}  "
            f"单调性={result.monotonicity_score:.3f}  "
            f"L-S年化={result.long_short_annualized:.2%}"
        )

        self._on_visibility_changed()
        self._placeholder.hide()
        self._glw.show()
        self._reset_zoom()

    def clear(self) -> None:
        """重置到空状态。"""
        for curve in self._curves_q:
            curve.setData([], [])
        self._curve_ls.setData([], [])
        empty = np.array([])
        for bar in (self._bar_ann_pos, self._bar_ann_neg, self._bar_ls):
            bar.setOpts(x=empty, height=empty)
        self._mono_text.setText("")
        self.lbl_info.setText("")
        self._glw.hide()
        self._placeholder.show()

    # ------------------------------------------------------------------ #
    #  工具栏回调
    # ------------------------------------------------------------------ #

    def _on_visibility_changed(self) -> None:
        for i, chk in enumerate(self._chk_q):
            if i < len(self._curves_q):
                self._curves_q[i].setVisible(chk.isChecked())
        show_ls  = self.chk_ls.isChecked()
        show_bar = self.chk_bar.isChecked()
        self._curve_ls.setVisible(show_ls)
        self._plot_ann.setVisible(show_bar)
        self._bar_ls.setVisible(show_ls and show_bar)

    def _reset_zoom(self) -> None:
        self._plot_cum.autoRange()
        self._plot_ann.autoRange()

    # ------------------------------------------------------------------ #
    #  内部工具
    # ------------------------------------------------------------------ #

    @staticmethod
    def _series_to_xy(
        series: "pd.Series",
    ) -> tuple[np.ndarray, np.ndarray]:
        clean = series.dropna()
        if clean.empty:
            return np.array([]), np.array([])
        x = np.array([ts.timestamp() for ts in clean.index], dtype=np.float64)
        y = clean.values.astype(np.float64)
        return x, y

    @staticmethod
    def _set_bar_split(
        bar_pos: pg.BarGraphItem,
        bar_neg: pg.BarGraphItem,
        x: np.ndarray,
        y: np.ndarray,
    ) -> None:
        valid = ~np.isnan(y)
        xv, yv = x[valid], y[valid]
        pos = yv >= 0
        bar_pos.setOpts(x=xv[pos],  height=yv[pos],  width=_BAR_W)
        bar_neg.setOpts(x=xv[~pos], height=yv[~pos], width=_BAR_W)
