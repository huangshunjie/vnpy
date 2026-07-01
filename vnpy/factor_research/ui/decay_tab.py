"""
factor_research/ui/decay_tab.py

DecayTab — IC Decay Tab。

图表布局（上下两个 PyQtGraph 子图）：
  上图：IC 均值柱状图（正蓝/负橙） + RankIC 均值折线（绿）+ 零轴参考线
  下图：ICIR 柱状图（正蓝/负橙）  + 最优持有期红色虚线标注

工具栏（图表上方）：
  ☑ IC均值   ☑ RankIC均值   ☑ ICIR   [重置缩放]
  右侧：合约 / 因子 / 最优持有期 信息标签

数据来源：
  dispatcher → EVENT_FACTOR_PLOT_READY {"tab":"decay", "payload": DecayResult}
  由 FactorResearchWidget 调用 self.decay_tab.update_decay(result)

柱状图实现：
  PyQtGraph 无内置 BarGraphItem 颜色分组，使用两个 BarGraphItem
  分别绘制正值（蓝）和负值（橙），宽度 0.6，居中于整数 lag。
"""

from __future__ import annotations

import math

import numpy as np
import pyqtgraph as pg

from vnpy.trader.ui import QtCore, QtWidgets

from ..model import DecayResult


class DecayTab(QtWidgets.QWidget):
    """IC Decay Tab（PyQtGraph 柱状图）。"""

    _COLOR_POS    = "#5B9BD5"   # 正值蓝
    _COLOR_NEG    = "#ED7D31"   # 负值橙
    _COLOR_RANK   = "#70AD47"   # RankIC 折线绿
    _COLOR_ZERO   = "#888888"   # 零轴灰
    _COLOR_BEST   = "#E53935"   # 最优 lag 红色虚线
    _BAR_WIDTH    = 0.55

    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
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
        layout.setSpacing(12)

        self.chk_ic     = QtWidgets.QCheckBox("IC 均值")
        self.chk_ric    = QtWidgets.QCheckBox("RankIC 均值")
        self.chk_icir   = QtWidgets.QCheckBox("ICIR")
        self.chk_ic.setChecked(True)
        self.chk_ric.setChecked(True)
        self.chk_icir.setChecked(True)

        self.chk_ic.toggled.connect(self._on_visibility_changed)
        self.chk_ric.toggled.connect(self._on_visibility_changed)
        self.chk_icir.toggled.connect(self._on_visibility_changed)

        btn_reset = QtWidgets.QPushButton("重置缩放")
        btn_reset.setFixedWidth(80)
        btn_reset.clicked.connect(self._reset_zoom)

        self.lbl_info = QtWidgets.QLabel("")
        self.lbl_info.setAlignment(QtCore.Qt.AlignmentFlag.AlignRight)

        layout.addWidget(self.chk_ic)
        layout.addWidget(self.chk_ric)
        layout.addWidget(self.chk_icir)
        layout.addWidget(btn_reset)
        layout.addStretch()
        layout.addWidget(self.lbl_info)
        return bar

    def _build_chart(self) -> QtWidgets.QWidget:
        container = QtWidgets.QWidget(self)
        v = QtWidgets.QVBoxLayout(container)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(0)

        # 占位提示
        self._placeholder = QtWidgets.QLabel(
            "暂无数据\n请在左侧配置区填写参数后点击「运行」"
        )
        self._placeholder.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)

        # PyQtGraph
        pg.setConfigOptions(antialias=True, background="#1E1E1E", foreground="#CCCCCC")
        self._glw = pg.GraphicsLayoutWidget()

        # 上图：IC 均值柱 + RankIC 折线
        self._plot_ic = self._glw.addPlot(
            row=0, col=0, title="IC 均值 / RankIC 均值（按持有期）"
        )
        self._plot_ic.showGrid(x=True, y=True, alpha=0.3)
        self._plot_ic.setLabel("left", "IC 均值")
        self._plot_ic.setLabel("bottom", "持有期（天）")
        self._plot_ic.addLegend(offset=(10, 10))

        self._zero_ic = pg.InfiniteLine(
            pos=0, angle=0,
            pen=pg.mkPen(color=self._COLOR_ZERO,
                         style=QtCore.Qt.PenStyle.DashLine, width=1),
        )
        self._plot_ic.addItem(self._zero_ic)

        # IC 柱（正/负各一个 BarGraphItem）
        self._bar_ic_pos = pg.BarGraphItem(
            x=[], height=[], width=self._BAR_WIDTH,
            brush=self._COLOR_POS, pen=None,
            name="IC（正）",
        )
        self._bar_ic_neg = pg.BarGraphItem(
            x=[], height=[], width=self._BAR_WIDTH,
            brush=self._COLOR_NEG, pen=None,
            name="IC（负）",
        )
        self._plot_ic.addItem(self._bar_ic_pos)
        self._plot_ic.addItem(self._bar_ic_neg)

        # RankIC 折线
        self._curve_ric = self._plot_ic.plot(
            [], [], name="RankIC 均值",
            pen=pg.mkPen(color=self._COLOR_RANK, width=2),
            symbol="o", symbolSize=5,
            symbolBrush=self._COLOR_RANK, symbolPen=None,
        )

        # 下图：ICIR 柱 + 最优 lag 标注
        self._plot_icir = self._glw.addPlot(
            row=1, col=0, title="ICIR（按持有期）"
        )
        self._plot_icir.showGrid(x=True, y=True, alpha=0.3)
        self._plot_icir.setLabel("left", "ICIR")
        self._plot_icir.setLabel("bottom", "持有期（天）")

        self._zero_icir = pg.InfiniteLine(
            pos=0, angle=0,
            pen=pg.mkPen(color=self._COLOR_ZERO,
                         style=QtCore.Qt.PenStyle.DashLine, width=1),
        )
        self._plot_icir.addItem(self._zero_icir)

        self._bar_icir_pos = pg.BarGraphItem(
            x=[], height=[], width=self._BAR_WIDTH,
            brush=self._COLOR_POS, pen=None,
        )
        self._bar_icir_neg = pg.BarGraphItem(
            x=[], height=[], width=self._BAR_WIDTH,
            brush=self._COLOR_NEG, pen=None,
        )
        self._plot_icir.addItem(self._bar_icir_pos)
        self._plot_icir.addItem(self._bar_icir_neg)

        # 最优持有期垂直虚线（两图各一条）
        self._best_line_ic = pg.InfiniteLine(
            pos=1, angle=90,
            pen=pg.mkPen(color=self._COLOR_BEST,
                         style=QtCore.Qt.PenStyle.DashLine, width=1.5),
            label="最优 lag={value:.0f}",
            labelOpts={"color": self._COLOR_BEST, "position": 0.9},
        )
        self._best_line_icir = pg.InfiniteLine(
            pos=1, angle=90,
            pen=pg.mkPen(color=self._COLOR_BEST,
                         style=QtCore.Qt.PenStyle.DashLine, width=1.5),
        )
        self._plot_ic.addItem(self._best_line_ic)
        self._plot_icir.addItem(self._best_line_icir)

        # x 轴联动
        self._plot_icir.setXLink(self._plot_ic)

        # 上下图高度比 3:2
        self._glw.ci.layout.setRowStretchFactor(0, 3)
        self._glw.ci.layout.setRowStretchFactor(1, 2)

        v.addWidget(self._placeholder)
        v.addWidget(self._glw)
        self._glw.hide()

        return container

    # ------------------------------------------------------------------ #
    #  公开接口
    # ------------------------------------------------------------------ #

    def update_decay(self, result: DecayResult) -> None:
        """
        将 DecayResult 渲染到图表。
        在 Qt 主线程调用（Signal/Slot 保证）。
        """
        if not result.is_valid():
            return

        lags      = np.array(result.lags, dtype=float)
        ic_vals   = np.array(result.ic_means, dtype=float)
        ric_vals  = np.array(result.rank_ic_means, dtype=float)
        icir_vals = np.array(result.icirs, dtype=float)
        best_lag  = result.best_lag

        # --- 上图 ---
        self._set_bar_data(self._bar_ic_pos, self._bar_ic_neg, lags, ic_vals)
        # RankIC 折线（去掉 NaN）
        valid_ric = ~np.isnan(ric_vals)
        self._curve_ric.setData(lags[valid_ric], ric_vals[valid_ric])

        # --- 下图 ---
        self._set_bar_data(self._bar_icir_pos, self._bar_icir_neg, lags, icir_vals)

        # --- 最优持有期标注 ---
        self._best_line_ic.setValue(best_lag)
        self._best_line_icir.setValue(best_lag)

        # --- 信息标签 ---
        best_ic = result.ic_means[best_lag - 1] if len(result.ic_means) >= best_lag else float("nan")
        self.lbl_info.setText(
            f"{result.vt_symbol}  {result.factor_name}  "
            f"最优持有期={best_lag}天  IC@best={best_ic:.4f}"
        )

        self._on_visibility_changed()
        self._placeholder.hide()
        self._glw.show()
        self._reset_zoom()

    def clear(self) -> None:
        """重置到空状态。"""
        empty = np.array([])
        for bar in (self._bar_ic_pos, self._bar_ic_neg,
                    self._bar_icir_pos, self._bar_icir_neg):
            bar.setOpts(x=empty, height=empty)
        self._curve_ric.setData([], [])
        self.lbl_info.setText("")
        self._glw.hide()
        self._placeholder.show()

    # ------------------------------------------------------------------ #
    #  工具栏回调
    # ------------------------------------------------------------------ #

    def _on_visibility_changed(self) -> None:
        show_ic   = self.chk_ic.isChecked()
        show_ric  = self.chk_ric.isChecked()
        show_icir = self.chk_icir.isChecked()

        for bar in (self._bar_ic_pos, self._bar_ic_neg):
            bar.setVisible(show_ic)
        self._curve_ric.setVisible(show_ric)
        self._plot_icir.setVisible(show_icir)
        self._best_line_ic.setVisible(show_ic or show_ric)
        self._best_line_icir.setVisible(show_icir)

    def _reset_zoom(self) -> None:
        self._plot_ic.autoRange()
        self._plot_icir.autoRange()

    # ------------------------------------------------------------------ #
    #  内部工具
    # ------------------------------------------------------------------ #

    @staticmethod
    def _set_bar_data(
        bar_pos: pg.BarGraphItem,
        bar_neg: pg.BarGraphItem,
        x: np.ndarray,
        y: np.ndarray,
    ) -> None:
        """将 y 按正负拆分，分别设置给两个 BarGraphItem。"""
        valid = ~np.isnan(y)
        xv, yv = x[valid], y[valid]

        pos_mask = yv >= 0
        neg_mask = yv < 0

        bar_pos.setOpts(
            x=xv[pos_mask],
            height=yv[pos_mask],
            width=DecayTab._BAR_WIDTH,
        )
        bar_neg.setOpts(
            x=xv[neg_mask],
            height=yv[neg_mask],
            width=DecayTab._BAR_WIDTH,
        )
