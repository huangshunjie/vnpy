"""
factor_research/ui/longshort_tab.py

LongShortTab — Long-Short Tab。

布局（左图 + 右侧指标面板，水平分割）：
┌──────────────────────────────┬──────────────────────┐
│  上图：净值曲线（Q1多头/Q5空头/L-S）    │  绩效指标面板           │
│  下图：L-S 回撤曲线（红色填充）         │  多头/空头/L-S          │
│                             │  年化收益/最大回撤/Sharpe/Calmar │
└──────────────────────────────┴──────────────────────┘
工具栏：☑多头 ☑空头 ☑L-S ☑回撤曲线  [重置缩放]

数据来源：
  dispatcher → EVENT_FACTOR_PLOT_READY {"tab":"quantile", "payload": QuantileResult}
  widget._on_plot_ready 同时路由到 self.longshort_tab.update_ls(result)
  绩效统计在 Tab 内部用 numpy 计算，零额外引擎。

指标定义：
  净值   = (1 + period_ret_series).cumprod()
  MDD    = max((peak - trough) / peak)，取负值
  Sharpe = mean(r) / std(r) * sqrt(TRADING_DAYS / lag)
  Calmar = ann_return / |MDD|（MDD=0 时为 nan）
"""

from __future__ import annotations

import math

import numpy as np
import pyqtgraph as pg

from vnpy.trader.ui import QtCore, QtWidgets

from ..model import LongShortStats, PerfStats, QuantileResult


_LONG_COLOR  = "#5B9BD5"   # 多头蓝
_SHORT_COLOR = "#ED7D31"   # 空头橙
_LS_COLOR    = "#E53935"   # L-S 红
_DD_COLOR    = "#F44336"   # 回撤填充红（半透明）
_ZERO_COLOR  = "#888888"
_GOOD_COLOR  = "#4CAF50"
_BAD_COLOR   = "#F44336"
TRADING_DAYS = 252


class _DateAxisItem(pg.AxisItem):
    def tickStrings(self, values, scale, spacing):
        from datetime import datetime, timezone
        out = []
        for v in values:
            try:
                out.append(datetime.fromtimestamp(v, tz=timezone.utc).strftime("%Y-%m-%d"))
            except Exception:
                out.append("")
        return out


class LongShortTab(QtWidgets.QWidget):
    """Long-Short 绩效 Tab。"""

    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self._lag: int = 5
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
        splitter.addWidget(self._build_perf_panel())
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 1)
        root.addWidget(splitter, stretch=1)

    def _build_toolbar(self) -> QtWidgets.QWidget:
        bar = QtWidgets.QWidget(self)
        layout = QtWidgets.QHBoxLayout(bar)
        layout.setContentsMargins(4, 0, 4, 0)
        layout.setSpacing(12)

        self.chk_long  = QtWidgets.QCheckBox("多头（Q5）")
        self.chk_short = QtWidgets.QCheckBox("空头（Q1）")
        self.chk_ls    = QtWidgets.QCheckBox("Long-Short")
        self.chk_dd    = QtWidgets.QCheckBox("回撤曲线")
        self.chk_long.setChecked(True)
        self.chk_short.setChecked(True)
        self.chk_ls.setChecked(True)
        self.chk_dd.setChecked(True)

        self.chk_long.setStyleSheet(f"color: {_LONG_COLOR}; font-weight: bold;")
        self.chk_short.setStyleSheet(f"color: {_SHORT_COLOR}; font-weight: bold;")
        self.chk_ls.setStyleSheet(f"color: {_LS_COLOR}; font-weight: bold;")

        for chk in (self.chk_long, self.chk_short, self.chk_ls, self.chk_dd):
            chk.toggled.connect(self._on_visibility_changed)
            layout.addWidget(chk)

        btn_reset = QtWidgets.QPushButton("重置缩放")
        btn_reset.setFixedWidth(80)
        btn_reset.clicked.connect(self._reset_zoom)
        layout.addWidget(btn_reset)

        self.lbl_info = QtWidgets.QLabel("")
        self.lbl_info.setAlignment(QtCore.Qt.AlignmentFlag.AlignRight)
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

        # 上图：净值曲线
        self._plot_nav = self._glw.addPlot(
            row=0, col=0,
            axisItems={"bottom": _DateAxisItem(orientation="bottom")},
            title="净值曲线",
        )
        self._plot_nav.showGrid(x=True, y=True, alpha=0.3)
        self._plot_nav.setLabel("left", "净值")
        self._plot_nav.addLegend(offset=(10, 10))

        self._zero_nav = pg.InfiniteLine(
            pos=1, angle=0,
            pen=pg.mkPen(color=_ZERO_COLOR,
                         style=QtCore.Qt.PenStyle.DashLine, width=1),
        )
        self._plot_nav.addItem(self._zero_nav)

        self._curve_long  = self._plot_nav.plot(
            [], [], name="多头（Q5）",
            pen=pg.mkPen(color=_LONG_COLOR, width=2),
        )
        self._curve_short = self._plot_nav.plot(
            [], [], name="空头（Q1）",
            pen=pg.mkPen(color=_SHORT_COLOR, width=2),
        )
        self._curve_ls = self._plot_nav.plot(
            [], [], name="Long-Short",
            pen=pg.mkPen(color=_LS_COLOR, width=2.5),
        )

        # 下图：L-S 回撤曲线（FillBetweenItem 填充到0轴）
        self._plot_dd = self._glw.addPlot(
            row=1, col=0,
            axisItems={"bottom": _DateAxisItem(orientation="bottom")},
            title="Long-Short 回撤",
        )
        self._plot_dd.showGrid(x=True, y=True, alpha=0.3)
        self._plot_dd.setLabel("left", "回撤")

        self._zero_dd = pg.InfiniteLine(
            pos=0, angle=0,
            pen=pg.mkPen(color=_ZERO_COLOR,
                         style=QtCore.Qt.PenStyle.DashLine, width=1),
        )
        self._plot_dd.addItem(self._zero_dd)

        self._curve_dd = self._plot_dd.plot(
            [], [],
            pen=pg.mkPen(color=_DD_COLOR, width=1.5),
            fillLevel=0,
            brush=pg.mkBrush(_DD_COLOR + "55"),
        )

        # x 轴联动
        self._plot_dd.setXLink(self._plot_nav)

        self._glw.ci.layout.setRowStretchFactor(0, 3)
        self._glw.ci.layout.setRowStretchFactor(1, 1)

        v.addWidget(self._placeholder)
        v.addWidget(self._glw)
        self._glw.hide()
        return container

    def _build_perf_panel(self) -> QtWidgets.QGroupBox:
        group = QtWidgets.QGroupBox("绩效指标")
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

        def _sep() -> QtWidgets.QFrame:
            line = QtWidgets.QFrame()
            line.setFrameShape(QtWidgets.QFrame.Shape.HLine)
            line.setFrameShadow(QtWidgets.QFrame.Shadow.Sunken)
            return line

        # 多头
        self.lbl_long_ann    = _lbl()
        self.lbl_long_mdd    = _lbl()
        self.lbl_long_sharpe = _lbl()
        self.lbl_long_calmar = _lbl()
        # 空头
        self.lbl_short_ann    = _lbl()
        self.lbl_short_mdd    = _lbl()
        self.lbl_short_sharpe = _lbl()
        self.lbl_short_calmar = _lbl()
        # L-S
        self.lbl_ls_ann    = _lbl()
        self.lbl_ls_mdd    = _lbl()
        self.lbl_ls_sharpe = _lbl()
        self.lbl_ls_calmar = _lbl()

        form.addRow(_sep())
        _hdr_long = QtWidgets.QLabel("▶ 多头（Q5）")
        _hdr_long.setStyleSheet(f"color: {_LONG_COLOR}; font-weight: bold;")
        form.addRow(_hdr_long)
        form.addRow("年化收益",  self.lbl_long_ann)
        form.addRow("最大回撤",  self.lbl_long_mdd)
        form.addRow("Sharpe",    self.lbl_long_sharpe)
        form.addRow("Calmar",    self.lbl_long_calmar)

        form.addRow(_sep())
        _hdr_short = QtWidgets.QLabel("▶ 空头（Q1）")
        _hdr_short.setStyleSheet(f"color: {_SHORT_COLOR}; font-weight: bold;")
        form.addRow(_hdr_short)
        form.addRow("年化收益",  self.lbl_short_ann)
        form.addRow("最大回撤",  self.lbl_short_mdd)
        form.addRow("Sharpe",    self.lbl_short_sharpe)
        form.addRow("Calmar",    self.lbl_short_calmar)

        form.addRow(_sep())
        _hdr_ls = QtWidgets.QLabel("▶ Long-Short")
        _hdr_ls.setStyleSheet(f"color: {_LS_COLOR}; font-weight: bold;")
        form.addRow(_hdr_ls)
        form.addRow("年化收益",  self.lbl_ls_ann)
        form.addRow("最大回撤",  self.lbl_ls_mdd)
        form.addRow("Sharpe",    self.lbl_ls_sharpe)
        form.addRow("Calmar",    self.lbl_ls_calmar)

        spacer = QtWidgets.QWidget()
        spacer.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Preferred,
            QtWidgets.QSizePolicy.Policy.Expanding,
        )
        form.addRow(spacer)
        return group

    # ------------------------------------------------------------------ #
    #  公开接口
    # ------------------------------------------------------------------ #

    def update_ls(self, result: QuantileResult) -> None:
        """
        从 QuantileResult 提取多头/空头/L-S 序列，
        计算绩效统计并渲染图表。Qt 主线程调用。
        """
        if not result.is_valid():
            return

        self._lag = result.lag
        q_labels = result.quantile_labels
        if len(q_labels) < 2:
            return

        q_first = q_labels[0]   # 空头：因子最低档
        q_last  = q_labels[-1]  # 多头：因子最高档

        # 取收益率序列（period returns，非累计）
        long_ret  = result.quantile_returns.get(q_last)
        short_ret = result.quantile_returns.get(q_first)
        ls_cum    = result.long_short_series

        # ── 净值曲线 ──
        if long_ret is not None and not long_ret.empty:
            long_nav = (1 + long_ret).cumprod()
            x, y = self._series_to_xy(long_nav)
            self._curve_long.setData(x, y)
        else:
            self._curve_long.setData([], [])

        if short_ret is not None and not short_ret.empty:
            short_nav = (1 + short_ret).cumprod()
            x, y = self._series_to_xy(short_nav)
            self._curve_short.setData(x, y)
        else:
            self._curve_short.setData([], [])

        if ls_cum is not None and not ls_cum.empty:
            # L-S 用净值序列（1 + cum_ret）
            ls_nav = 1 + ls_cum
            x, y = self._series_to_xy(ls_nav)
            self._curve_ls.setData(x, y)
            # 回撤曲线
            dd_x, dd_y = self._drawdown_xy(ls_nav)
            self._curve_dd.setData(dd_x, dd_y)
        else:
            self._curve_ls.setData([], [])
            self._curve_dd.setData([], [])

        # ── 绩效指标 ──
        ls_stats = LongShortStats(
            vt_symbol=result.vt_symbol,
            factor_name=result.factor_name,
            lag=result.lag,
            long_stats=self._compute_perf(
                q_last, long_ret, result.lag) if long_ret is not None else None,
            short_stats=self._compute_perf(
                q_first, short_ret, result.lag) if short_ret is not None else None,
            ls_stats=self._compute_perf_from_cum(
                "L-S", ls_cum, result.lag) if ls_cum is not None else None,
        )
        self._update_panel(ls_stats)

        # 信息标签
        ls_ann = result.long_short_annualized
        self.lbl_info.setText(
            f"{result.vt_symbol}  {result.factor_name}  lag={result.lag}  "
            f"L-S年化={ls_ann:.2%}"
        )

        self._on_visibility_changed()
        self._placeholder.hide()
        self._glw.show()
        self._reset_zoom()

    def clear(self) -> None:
        """重置到空状态。"""
        for curve in (self._curve_long, self._curve_short,
                      self._curve_ls, self._curve_dd):
            curve.setData([], [])
        for lbl in (
            self.lbl_long_ann, self.lbl_long_mdd,
            self.lbl_long_sharpe, self.lbl_long_calmar,
            self.lbl_short_ann, self.lbl_short_mdd,
            self.lbl_short_sharpe, self.lbl_short_calmar,
            self.lbl_ls_ann, self.lbl_ls_mdd,
            self.lbl_ls_sharpe, self.lbl_ls_calmar,
        ):
            lbl.setText("—")
            lbl.setStyleSheet("")
        self.lbl_info.setText("")
        self._glw.hide()
        self._placeholder.show()

    # ------------------------------------------------------------------ #
    #  工具栏回调
    # ------------------------------------------------------------------ #

    def _on_visibility_changed(self) -> None:
        self._curve_long.setVisible(self.chk_long.isChecked())
        self._curve_short.setVisible(self.chk_short.isChecked())
        self._curve_ls.setVisible(self.chk_ls.isChecked())
        self._plot_dd.setVisible(self.chk_dd.isChecked())

    def _reset_zoom(self) -> None:
        self._plot_nav.autoRange()
        self._plot_dd.autoRange()

    # ------------------------------------------------------------------ #
    #  绩效计算（纯函数，可独立测试）
    # ------------------------------------------------------------------ #

    def _compute_perf(
        self,
        label: str,
        ret_series: "pd.Series",
        lag: int,
    ) -> PerfStats:
        """从期间收益率序列计算绩效指标。"""
        import pandas as pd
        if ret_series is None or ret_series.empty:
            return PerfStats(label=label)
        r = ret_series.dropna().values
        return self._calc_stats(label, r, lag)

    def _compute_perf_from_cum(
        self,
        label: str,
        cum_series: "pd.Series",
        lag: int,
    ) -> PerfStats:
        """从累计收益序列还原期间收益率，再计算绩效指标。"""
        if cum_series is None or cum_series.empty:
            return PerfStats(label=label)
        nav = (1 + cum_series.dropna()).values
        if len(nav) < 2:
            return PerfStats(label=label)
        r = np.diff(nav) / nav[:-1]
        return self._calc_stats(label, r, lag)

    @classmethod
    def _calc_stats(
        cls,
        label: str,
        r: "np.ndarray",
        lag: int,
    ) -> PerfStats:
        """核心绩效计算：年化收益/MDD/Sharpe/Calmar。"""
        if len(r) < 2:
            return PerfStats(label=label)

        # 年化收益
        total = float((1 + r).prod()) - 1
        n_periods = len(r)
        ann_factor = TRADING_DAYS / lag
        ann = (1 + total) ** (ann_factor / n_periods) - 1

        # 净值序列
        nav = np.cumprod(1 + r)

        # 最大回撤
        mdd = cls._max_drawdown(nav)

        # Sharpe
        mean_r = float(np.mean(r))
        std_r  = float(np.std(r, ddof=1))
        sharpe = (mean_r / std_r * math.sqrt(ann_factor)
                  if std_r > 1e-12 else float("nan"))

        # Calmar
        calmar = (ann / abs(mdd)
                  if mdd < -1e-6 else float("nan"))

        return PerfStats(
            label=label,
            ann_return=float(ann),
            max_drawdown=float(mdd),
            sharpe=float(sharpe),
            calmar=float(calmar),
        )

    @staticmethod
    def _max_drawdown(nav: "np.ndarray") -> float:
        """计算最大回撤（返回负值，如 -0.15）。"""
        if len(nav) < 2:
            return 0.0
        peak = np.maximum.accumulate(nav)
        dd   = (nav - peak) / peak
        return float(np.min(dd))

    @staticmethod
    def _series_to_xy(series: "pd.Series") -> tuple:
        clean = series.dropna()
        if clean.empty:
            return np.array([]), np.array([])
        x = np.array([ts.timestamp() for ts in clean.index], dtype=np.float64)
        y = clean.values.astype(np.float64)
        return x, y

    @classmethod
    def _drawdown_xy(cls, nav_series: "pd.Series") -> tuple:
        """计算净值序列的回撤时序，返回 (x_unix, y_drawdown)。"""
        clean = nav_series.dropna()
        if clean.empty:
            return np.array([]), np.array([])
        nav = clean.values.astype(np.float64)
        peak = np.maximum.accumulate(nav)
        dd   = (nav - peak) / peak
        x = np.array([ts.timestamp() for ts in clean.index], dtype=np.float64)
        return x, dd

    # ------------------------------------------------------------------ #
    #  绩效面板渲染
    # ------------------------------------------------------------------ #

    def _update_panel(self, ls_stats: LongShortStats) -> None:
        def _fill(
            ann_lbl, mdd_lbl, sharpe_lbl, calmar_lbl,
            perf: PerfStats | None,
        ) -> None:
            if perf is None:
                for lbl in (ann_lbl, mdd_lbl, sharpe_lbl, calmar_lbl):
                    lbl.setText("—")
                    lbl.setStyleSheet("")
                return

            # 年化收益（正绿负红）
            ann = perf.ann_return
            ann_lbl.setText(f"{ann:.2%}" if not math.isnan(ann) else "—")
            if not math.isnan(ann):
                ann_lbl.setStyleSheet(
                    f"color: {_GOOD_COLOR};" if ann > 0
                    else f"color: {_BAD_COLOR};"
                )

            mdd = perf.max_drawdown
            mdd_lbl.setText(f"{mdd:.2%}" if not math.isnan(mdd) else "—")
            if not math.isnan(mdd):
                mdd_lbl.setStyleSheet(
                    f"color: {_BAD_COLOR};" if mdd < -0.1 else ""
                )

            sp = perf.sharpe
            sharpe_lbl.setText(f"{sp:.4f}" if not math.isnan(sp) else "—")
            if not math.isnan(sp):
                sharpe_lbl.setStyleSheet(
                    f"color: {_GOOD_COLOR};" if abs(sp) >= 1.0 else ""
                )

            cal = perf.calmar
            calmar_lbl.setText(f"{cal:.4f}" if not math.isnan(cal) else "—")

        _fill(self.lbl_long_ann, self.lbl_long_mdd,
              self.lbl_long_sharpe, self.lbl_long_calmar,
              ls_stats.long_stats)
        _fill(self.lbl_short_ann, self.lbl_short_mdd,
              self.lbl_short_sharpe, self.lbl_short_calmar,
              ls_stats.short_stats)
        _fill(self.lbl_ls_ann, self.lbl_ls_mdd,
              self.lbl_ls_sharpe, self.lbl_ls_calmar,
              ls_stats.ls_stats)
