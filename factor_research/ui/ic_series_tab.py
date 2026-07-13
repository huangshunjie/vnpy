"""
factor_research/ui/ic_series_tab.py

IcSeriesTab — IC 时序 Tab。

图表布局（上下两个 PyQtGraph 子图）：
  上图：滚动 IC（蓝）/ 滚动 RankIC（橙）折线 + 零轴参考线
  下图：累计 IC（绿）折线

工具栏（图表上方）：
  ☑ IC   ☑ RankIC   ☑ 累计IC   [重置缩放]

数据来源：
  dispatcher → EVENT_FACTOR_PLOT_READY {"tab":"ic_series", "payload": IcStats}
  由 FactorResearchWidget 调用 self.ic_series_tab.update_series(stats)

设计原则：
  - 只依赖 pyqtgraph；不引入 matplotlib
  - x 轴使用时间戳（秒级 unix time），自定义 AxisItem 显示日期
  - 两个子图 x 轴联动（X-link）
  - 无数据时显示占位标签
"""

from __future__ import annotations

import numpy as np
import pyqtgraph as pg

from vnpy.trader.ui import QtCore, QtWidgets

from ..model import IcStats


class _DateAxisItem(pg.AxisItem):
    """将 unix 时间戳（秒）格式化为 YYYY-MM-DD 显示。"""

    def tickStrings(self, values, scale, spacing):
        from datetime import datetime, timezone
        result = []
        for v in values:
            try:
                dt = datetime.fromtimestamp(v, tz=timezone.utc)
                result.append(dt.strftime("%Y-%m-%d"))
            except Exception:
                result.append("")
        return result


class IcSeriesTab(QtWidgets.QWidget):
    """IC 时序 Tab（PyQtGraph 折线图）。"""

    # 颜色常量
    _COLOR_IC      = "#5B9BD5"   # 蓝
    _COLOR_RANK_IC = "#ED7D31"   # 橙
    _COLOR_CUM_IC  = "#70AD47"   # 绿
    _COLOR_ZERO    = "#888888"   # 零轴

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

        self.chk_ic      = QtWidgets.QCheckBox("IC")
        self.chk_rank_ic = QtWidgets.QCheckBox("RankIC")
        self.chk_cum_ic  = QtWidgets.QCheckBox("累计 IC")
        self.chk_ic.setChecked(True)
        self.chk_rank_ic.setChecked(True)
        self.chk_cum_ic.setChecked(True)

        self.chk_ic.toggled.connect(self._on_visibility_changed)
        self.chk_rank_ic.toggled.connect(self._on_visibility_changed)
        self.chk_cum_ic.toggled.connect(self._on_visibility_changed)

        btn_reset = QtWidgets.QPushButton("重置缩放")
        btn_reset.setFixedWidth(80)
        btn_reset.clicked.connect(self._reset_zoom)

        # 合约 + 因子信息标签
        self.lbl_info = QtWidgets.QLabel("")
        self.lbl_info.setAlignment(QtCore.Qt.AlignmentFlag.AlignRight)

        layout.addWidget(self.chk_ic)
        layout.addWidget(self.chk_rank_ic)
        layout.addWidget(self.chk_cum_ic)
        layout.addWidget(btn_reset)
        layout.addStretch()
        layout.addWidget(self.lbl_info)
        return bar

    def _build_chart(self) -> QtWidgets.QWidget:
        """构建 PyQtGraph 图表容器（上图 + 下图）。"""
        container = QtWidgets.QWidget(self)
        v = QtWidgets.QVBoxLayout(container)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(0)

        # 占位提示
        self._placeholder = QtWidgets.QLabel(
            "暂无数据\n请在左侧配置区填写参数后点击「运行」"
        )
        self._placeholder.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)

        # PyQtGraph GraphicsLayoutWidget
        pg.setConfigOptions(antialias=True, background="#1E1E1E", foreground="#CCCCCC")
        self._glw = pg.GraphicsLayoutWidget()

        # 上图：IC / RankIC
        self._plot_ic = self._glw.addPlot(
            row=0, col=0,
            axisItems={"bottom": _DateAxisItem(orientation="bottom")},
            title="滚动 IC / RankIC",
        )
        self._plot_ic.showGrid(x=True, y=True, alpha=0.3)
        self._plot_ic.setLabel("left", "IC 值")
        self._plot_ic.addLegend(offset=(10, 10))

        # 零轴
        self._zero_line_ic = pg.InfiniteLine(
            pos=0, angle=0,
            pen=pg.mkPen(color=self._COLOR_ZERO, style=QtCore.Qt.PenStyle.DashLine, width=1),
        )
        self._plot_ic.addItem(self._zero_line_ic)

        # IC 曲线
        self._curve_ic = self._plot_ic.plot(
            [], [], name="IC",
            pen=pg.mkPen(color=self._COLOR_IC, width=1.5),
        )
        self._curve_rank_ic = self._plot_ic.plot(
            [], [], name="RankIC",
            pen=pg.mkPen(color=self._COLOR_RANK_IC, width=1.5),
        )

        # 下图：累计 IC
        self._plot_cum = self._glw.addPlot(
            row=1, col=0,
            axisItems={"bottom": _DateAxisItem(orientation="bottom")},
            title="累计 IC",
        )
        self._plot_cum.showGrid(x=True, y=True, alpha=0.3)
        self._plot_cum.setLabel("left", "累计值")
        self._plot_cum.addLegend(offset=(10, 10))

        self._zero_line_cum = pg.InfiniteLine(
            pos=0, angle=0,
            pen=pg.mkPen(color=self._COLOR_ZERO, style=QtCore.Qt.PenStyle.DashLine, width=1),
        )
        self._plot_cum.addItem(self._zero_line_cum)

        self._curve_cum_ic = self._plot_cum.plot(
            [], [], name="累计 IC",
            pen=pg.mkPen(color=self._COLOR_CUM_IC, width=1.5),
        )

        # x 轴联动
        self._plot_cum.setXLink(self._plot_ic)

        # 上下图高度比 2:1
        self._glw.ci.layout.setRowStretchFactor(0, 2)
        self._glw.ci.layout.setRowStretchFactor(1, 1)

        v.addWidget(self._placeholder)
        v.addWidget(self._glw)
        self._glw.hide()

        return container

    # ------------------------------------------------------------------ #
    #  公开接口
    # ------------------------------------------------------------------ #

    def update_series(self, stats: IcStats) -> None:
        """
        将 IcStats 中的序列数据渲染到图表。
        在 Qt 主线程调用（Signal/Slot 保证）。
        """
        if stats.ic_series is None and stats.rank_ic_series is None:
            return

        self.lbl_info.setText(
            f"{stats.vt_symbol}  {stats.factor_name}  lag={stats.lag}"
        )

        # 转换为 numpy 数组，处理 NaN
        x_ic, y_ic           = self._series_to_xy(stats.ic_series)
        x_ric, y_ric         = self._series_to_xy(stats.rank_ic_series)
        x_cum, y_cum         = self._cumsum_xy(stats.ic_series)

        self._curve_ic.setData(x_ic, y_ic)
        self._curve_rank_ic.setData(x_ric, y_ric)
        self._curve_cum_ic.setData(x_cum, y_cum)

        self._on_visibility_changed()

        self._placeholder.hide()
        self._glw.show()
        self._reset_zoom()

    def clear(self) -> None:
        """重置到空状态。"""
        self._curve_ic.setData([], [])
        self._curve_rank_ic.setData([], [])
        self._curve_cum_ic.setData([], [])
        self.lbl_info.setText("")
        self._glw.hide()
        self._placeholder.show()

    # ------------------------------------------------------------------ #
    #  工具栏回调
    # ------------------------------------------------------------------ #

    def _on_visibility_changed(self) -> None:
        self._curve_ic.setVisible(self.chk_ic.isChecked())
        self._curve_rank_ic.setVisible(self.chk_rank_ic.isChecked())
        self._curve_cum_ic.setVisible(self.chk_cum_ic.isChecked())
        # 下图整体随"累计IC"复选框显隐
        self._plot_cum.setVisible(self.chk_cum_ic.isChecked())

    def _reset_zoom(self) -> None:
        self._plot_ic.autoRange()
        self._plot_cum.autoRange()

    # ------------------------------------------------------------------ #
    #  数据转换
    # ------------------------------------------------------------------ #

    @staticmethod
    def _series_to_xy(
        series: "pd.Series | None",
    ) -> tuple[np.ndarray, np.ndarray]:
        """
        把 pandas Series（index=datetime）转为 (x_unix_sec, y_float) 两个 numpy 数组。
        NaN 值保留（pyqtgraph 会断开折线）。
        """
        if series is None or series.empty:
            return np.array([]), np.array([])

        clean = series.dropna()
        if clean.empty:
            return np.array([]), np.array([])

        x = np.array([ts.timestamp() for ts in clean.index], dtype=np.float64)
        y = clean.values.astype(np.float64)
        return x, y

    @staticmethod
    def _cumsum_xy(
        series: "pd.Series | None",
    ) -> tuple[np.ndarray, np.ndarray]:
        """计算累计 IC 序列的 (x, y)。"""
        if series is None or series.empty:
            return np.array([]), np.array([])

        clean = series.dropna()
        if clean.empty:
            return np.array([]), np.array([])

        x = np.array([ts.timestamp() for ts in clean.index], dtype=np.float64)
        y = np.cumsum(clean.values.astype(np.float64))
        return x, y
