"""
factor_research/ui/ic_distribution_tab.py

IcDistributionTab — IC 分布 Tab。

布局（左图 + 右侧统计面板，水平分割）：
┌────────────────────────────┬──────────────────┐
│  PyQtGraph 直方图区           │  统计摘要面板        │
│  · 频率直方图（蓝色填充）        │  均值 / 标准差        │
│  · KDE 曲线（橙色实线）         │  偏度 / 峰度          │
│  · 正态分布拟合曲线（绿虚线）     │  JB 统计量 / p 值     │
│  · 零轴参考线                 │  正态性结论           │
└────────────────────────────┴──────────────────┘
工具栏：☑ KDE  ☑ 正态拟合  ☑ IC序列  ☑ RankIC序列

数据来源：
  dispatcher → EVENT_FACTOR_PLOT_READY {"tab":"ic_series", "payload": IcStats}
  widget._on_plot_ready 同时路由到 ic_dist_tab.update_dist(stats)
  统计量在 Tab 内部用 scipy 计算，不依赖额外引擎。
"""

from __future__ import annotations

import numpy as np
import pyqtgraph as pg

from vnpy.trader.ui import QtCore, QtWidgets

from ..model import IcDistStats, IcStats


_HIST_COLOR = "#5B9BD5"
_KDE_COLOR  = "#ED7D31"
_NORM_COLOR = "#70AD47"
_ZERO_COLOR = "#888888"
_GOOD_COLOR = "#4CAF50"
_BAD_COLOR  = "#F44336"


class IcDistributionTab(QtWidgets.QWidget):
    """IC 分布 Tab（PyQtGraph 直方图 + KDE + 正态拟合）。"""

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

        splitter = QtWidgets.QSplitter(QtCore.Qt.Orientation.Horizontal)
        splitter.addWidget(self._build_chart())
        splitter.addWidget(self._build_stats_panel())
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 1)
        root.addWidget(splitter, stretch=1)

    def _build_toolbar(self) -> QtWidgets.QWidget:
        bar = QtWidgets.QWidget(self)
        layout = QtWidgets.QHBoxLayout(bar)
        layout.setContentsMargins(4, 0, 4, 0)
        layout.setSpacing(12)

        self.chk_kde  = QtWidgets.QCheckBox("KDE")
        self.chk_norm = QtWidgets.QCheckBox("正态拟合")
        self.chk_ic   = QtWidgets.QCheckBox("IC 序列")
        self.chk_ric  = QtWidgets.QCheckBox("RankIC 序列")
        self.chk_kde.setChecked(True)
        self.chk_norm.setChecked(True)
        self.chk_ic.setChecked(True)
        self.chk_ric.setChecked(False)

        for chk in (self.chk_kde, self.chk_norm, self.chk_ic, self.chk_ric):
            chk.toggled.connect(self._on_visibility_changed)
            layout.addWidget(chk)

        btn_reset = QtWidgets.QPushButton("重置缩放")
        btn_reset.setFixedWidth(80)
        btn_reset.clicked.connect(self._reset_zoom)
        layout.addWidget(btn_reset)
        layout.addStretch()
        return bar

    def _build_chart(self) -> QtWidgets.QWidget:
        container = QtWidgets.QWidget(self)
        v = QtWidgets.QVBoxLayout(container)
        v.setContentsMargins(0, 0, 0, 0)

        self._placeholder = QtWidgets.QLabel(
            "暂无数据\n请在左侧配置区填写参数后点击「运行」"
        )
        self._placeholder.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)

        pg.setConfigOptions(antialias=True, background="#1E1E1E", foreground="#CCCCCC")
        self._glw = pg.GraphicsLayoutWidget()

        self._plot = self._glw.addPlot(row=0, col=0, title="IC / RankIC 分布")
        self._plot.showGrid(x=True, y=True, alpha=0.3)
        self._plot.setLabel("left",   "频率密度")
        self._plot.setLabel("bottom", "IC 值")
        self._plot.addLegend(offset=(10, 10))

        self._zero_line = pg.InfiniteLine(
            pos=0, angle=90,
            pen=pg.mkPen(color=_ZERO_COLOR, style=QtCore.Qt.PenStyle.DashLine, width=1),
        )
        self._plot.addItem(self._zero_line)

        self._hist_ic = pg.BarGraphItem(
            x=[], height=[], width=0.01,
            brush=pg.mkBrush(_HIST_COLOR + "99"),
            pen=pg.mkPen(_HIST_COLOR, width=0.5),
            name="IC 频率",
        )
        self._hist_ric = pg.BarGraphItem(
            x=[], height=[], width=0.01,
            brush=pg.mkBrush(_NORM_COLOR + "88"),
            pen=pg.mkPen(_NORM_COLOR, width=0.5),
            name="RankIC 频率",
        )
        self._plot.addItem(self._hist_ic)
        self._plot.addItem(self._hist_ric)

        self._kde_ic = self._plot.plot(
            [], [], name="KDE(IC)",
            pen=pg.mkPen(color=_KDE_COLOR, width=2),
        )
        self._norm_ic = self._plot.plot(
            [], [], name="正态拟合(IC)",
            pen=pg.mkPen(color=_NORM_COLOR, width=2,
                         style=QtCore.Qt.PenStyle.DashLine),
        )

        v.addWidget(self._placeholder)
        v.addWidget(self._glw)
        self._glw.hide()
        return container

    def _build_stats_panel(self) -> QtWidgets.QGroupBox:
        group = QtWidgets.QGroupBox("统计摘要")
        form = QtWidgets.QFormLayout(group)
        form.setLabelAlignment(QtCore.Qt.AlignmentFlag.AlignRight)
        form.setSpacing(6)
        form.setContentsMargins(8, 8, 8, 8)

        def _lbl(text: str = "—") -> QtWidgets.QLabel:
            lbl = QtWidgets.QLabel(text)
            lbl.setTextInteractionFlags(
                QtCore.Qt.TextInteractionFlag.TextSelectableByMouse
            )
            return lbl

        self.lbl_symbol  = _lbl()
        self.lbl_factor  = _lbl()
        self.lbl_count   = _lbl()
        self.lbl_mean    = _lbl()
        self.lbl_std     = _lbl()
        self.lbl_skew    = _lbl()
        self.lbl_kurt    = _lbl()
        self.lbl_jb_stat = _lbl()
        self.lbl_jb_p    = _lbl()
        self.lbl_normal  = _lbl()

        form.addRow("合约代码",  self.lbl_symbol)
        form.addRow("因子名称",  self.lbl_factor)
        form.addRow("样本量",    self.lbl_count)
        form.addRow(self._sep())
        form.addRow("均值",      self.lbl_mean)
        form.addRow("标准差",    self.lbl_std)
        form.addRow("偏度",      self.lbl_skew)
        form.addRow("超额峰度",  self.lbl_kurt)
        form.addRow(self._sep())
        form.addRow("JB 统计量", self.lbl_jb_stat)
        form.addRow("JB p 值",   self.lbl_jb_p)
        form.addRow("正态性",    self.lbl_normal)

        spacer = QtWidgets.QWidget()
        spacer.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Preferred,
            QtWidgets.QSizePolicy.Policy.Expanding,
        )
        form.addRow(spacer)
        return group

    @staticmethod
    def _sep() -> QtWidgets.QFrame:
        line = QtWidgets.QFrame()
        line.setFrameShape(QtWidgets.QFrame.Shape.HLine)
        line.setFrameShadow(QtWidgets.QFrame.Shadow.Sunken)
        return line

    # ------------------------------------------------------------------ #
    #  公开接口
    # ------------------------------------------------------------------ #

    def update_dist(self, stats: IcStats) -> None:
        """
        从 IcStats 提取 ic_series，计算分布统计量并渲染图表。
        Qt 主线程调用（Signal/Slot 保证）。
        """
        if stats.ic_series is None:
            return
        ic_clean = stats.ic_series.dropna()
        if len(ic_clean) < 10:
            return

        dist_stats = self._compute_stats(
            ic_clean.values,
            vt_symbol=stats.vt_symbol,
            factor_name=stats.factor_name,
        )
        self._update_panel(dist_stats)

        self._update_hist(ic_clean.values, self._hist_ic, n_bins=30)
        kde_x, kde_y   = self._compute_kde(ic_clean.values)
        self._kde_ic.setData(kde_x, kde_y)
        norm_x, norm_y = self._compute_normal(ic_clean.values)
        self._norm_ic.setData(norm_x, norm_y)

        if stats.rank_ic_series is not None:
            ric_clean = stats.rank_ic_series.dropna()
            if len(ric_clean) >= 10:
                self._update_hist(ric_clean.values, self._hist_ric, n_bins=30)
            else:
                self._hist_ric.setOpts(x=[], height=[], width=0.01)
        else:
            self._hist_ric.setOpts(x=[], height=[], width=0.01)

        self._on_visibility_changed()
        self._placeholder.hide()
        self._glw.show()
        self._reset_zoom()

    def clear(self) -> None:
        """重置到空状态。"""
        self._hist_ic.setOpts(x=[], height=[], width=0.01)
        self._hist_ric.setOpts(x=[], height=[], width=0.01)
        self._kde_ic.setData([], [])
        self._norm_ic.setData([], [])
        for lbl in (self.lbl_symbol, self.lbl_factor, self.lbl_count,
                    self.lbl_mean, self.lbl_std, self.lbl_skew,
                    self.lbl_kurt, self.lbl_jb_stat, self.lbl_jb_p):
            lbl.setText("—")
        self.lbl_normal.setText("—")
        self.lbl_normal.setStyleSheet("")
        self._glw.hide()
        self._placeholder.show()

    # ------------------------------------------------------------------ #
    #  工具栏回调
    # ------------------------------------------------------------------ #

    def _on_visibility_changed(self) -> None:
        self._kde_ic.setVisible(self.chk_kde.isChecked())
        self._norm_ic.setVisible(self.chk_norm.isChecked())
        self._hist_ic.setVisible(self.chk_ic.isChecked())
        self._hist_ric.setVisible(self.chk_ric.isChecked())

    def _reset_zoom(self) -> None:
        self._plot.autoRange()

    # ------------------------------------------------------------------ #
    #  统计量计算（纯函数，可独立测试）
    # ------------------------------------------------------------------ #

    @staticmethod
    def _compute_stats(
        values: "np.ndarray",
        vt_symbol: str,
        factor_name: str,
    ) -> IcDistStats:
        from scipy.stats import skew, kurtosis, jarque_bera
        n      = len(values)
        mu     = float(np.mean(values))
        sig    = float(np.std(values, ddof=1))
        sk     = float(skew(values))
        ku     = float(kurtosis(values))   # Fisher，超额，正态=0
        jb, jp = jarque_bera(values)
        return IcDistStats(
            vt_symbol=vt_symbol, factor_name=factor_name,
            count=n, mean=mu, std=sig,
            skewness=sk, kurtosis=ku,
            jb_stat=float(jb), jb_pvalue=float(jp),
            is_normal=(float(jp) > 0.05),
        )

    @staticmethod
    def _compute_kde(values: "np.ndarray", n_pts: int = 300) -> tuple:
        from scipy.stats import gaussian_kde
        if len(values) < 5:
            return np.array([]), np.array([])
        kde = gaussian_kde(values, bw_method="scott")
        x_min, x_max = float(values.min()), float(values.max())
        margin = (x_max - x_min) * 0.1 or 0.1
        x = np.linspace(x_min - margin, x_max + margin, n_pts)
        return x, kde(x)

    @staticmethod
    def _compute_normal(values: "np.ndarray", n_pts: int = 300) -> tuple:
        from scipy.stats import norm
        mu, sig = float(np.mean(values)), float(np.std(values, ddof=1))
        if sig < 1e-12:
            return np.array([]), np.array([])
        x_min, x_max = float(values.min()), float(values.max())
        margin = (x_max - x_min) * 0.15 or 0.15
        x = np.linspace(x_min - margin, x_max + margin, n_pts)
        return x, norm.pdf(x, mu, sig)

    @staticmethod
    def _update_hist(
        values: "np.ndarray",
        bar_item: pg.BarGraphItem,
        n_bins: int = 30,
    ) -> None:
        counts, edges = np.histogram(values, bins=n_bins, density=True)
        centers = (edges[:-1] + edges[1:]) / 2
        width   = float(edges[1] - edges[0])
        bar_item.setOpts(x=centers, height=counts, width=width * 0.9)

    # ------------------------------------------------------------------ #
    #  统计面板渲染
    # ------------------------------------------------------------------ #

    def _update_panel(self, s: IcDistStats) -> None:
        self.lbl_symbol.setText(s.vt_symbol)
        self.lbl_factor.setText(s.factor_name)
        self.lbl_count.setText(str(s.count))
        self.lbl_mean.setText(f"{s.mean:.6f}")
        self.lbl_std.setText(f"{s.std:.6f}")

        skew_flag = "（右偏）" if s.skewness > 0.1 else "（左偏）" if s.skewness < -0.1 else "（对称）"
        self.lbl_skew.setText(f"{s.skewness:.4f}  {skew_flag}")

        kurt_flag = "（厚尾）" if s.kurtosis > 0.5 else "（薄尾）" if s.kurtosis < -0.5 else "（正常）"
        self.lbl_kurt.setText(f"{s.kurtosis:.4f}  {kurt_flag}")

        self.lbl_jb_stat.setText(f"{s.jb_stat:.4f}")
        self.lbl_jb_p.setText(f"{s.jb_pvalue:.4f}")

        if s.is_normal:
            self.lbl_normal.setText("通过（p > 0.05）")
            self.lbl_normal.setStyleSheet(f"color: {_GOOD_COLOR}; font-weight: bold;")
        else:
            self.lbl_normal.setText("拒绝（p ≤ 0.05）")
            self.lbl_normal.setStyleSheet(f"color: {_BAD_COLOR}; font-weight: bold;")
