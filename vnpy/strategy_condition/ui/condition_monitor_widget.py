"""
strategy_condition/ui/condition_monitor_widget.py
条件监控 Tab Widget：K线图（复用 KlineViewTab）+ 条件波形图（数字信号风格）

三区同步：
  - K线区、成交量区、波形区 X轴联动
  - 鼠标移动时贯穿三区的竖线
  - 滚轮缩放三区同步
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

import numpy as np
import pyqtgraph as pg

from vnpy.trader.ui import QtWidgets, QtCore, QtGui

from .kline_view import KlineViewTab
from ..monitor.condition_snapshot import ConditionDetail, ConditionSnapshot


# ── 颜色常量 ──────────────────────────────────────
_BG = "#1e1e2e"
_FG = "#cdd6f4"
_MUT = "#6c7086"
_BORD = "#45475a"
_GRN = "#a6e3a1"
_RED = "#f38ba8"
_WAVE_BG = "#181825"


class ConditionWaveformView(QtWidgets.QWidget):
    """
    条件波形图组件：用数字信号方波展示条件随时间的满足/不满足状态。

    每个条件一行子图，高电平(1)=满足，低电平(0)=不满足。
    买入条件用绿色，卖出条件用红色。
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._snapshots: List[ConditionSnapshot] = []
        self._buy_names: List[str] = []
        self._sell_names: List[str] = []
        self._dates: List[str] = []
        self._plots: List[pg.PlotItem] = []
        self._vlines: List[pg.InfiniteLine] = []  # 各子图中的竖线

        self._init_ui()

    def _init_ui(self):
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self._glw = pg.GraphicsLayoutWidget()
        self._glw.setBackground(_WAVE_BG)
        layout.addWidget(self._glw)

    def get_plots(self) -> List[pg.PlotItem]:
        """返回所有波形子图，用于外部 X 轴联动"""
        return self._plots

    def get_vlines(self) -> List[pg.InfiniteLine]:
        """返回所有竖线，用于外部同步十字线"""
        return self._vlines

    def load_data(self, snapshots: List[ConditionSnapshot],
                  dates: List[str] = None) -> None:
        """
        加载快照数据，生成波形图。
        """
        self._snapshots = snapshots
        self._plots.clear()
        self._vlines.clear()
        self._glw.clear()

        if not snapshots:
            self._show_empty_hint("暂无快照数据")
            return

        # 调试：检查第一个 snapshot 的内容
        print(f"[WaveView] load_data: {len(snapshots)} snapshots")
        print(f"[WaveView] snapshot[0].buy_details: {len(snapshots[0].buy_details)} items")
        print(f"[WaveView] snapshot[0].sell_details: {len(snapshots[0].sell_details)} items")
        if snapshots[0].buy_details:
            print(f"[WaveView] first buy_detail: {snapshots[0].buy_details[0]}")
        if snapshots[0].sell_details:
            print(f"[WaveView] first sell_detail: {snapshots[0].sell_details[0]}")

        # 提取条件名称
        self._buy_names = [d.condition_name for d in snapshots[0].buy_details]
        self._sell_names = [d.condition_name for d in snapshots[0].sell_details]
        self._dates = dates or [str(s.dt)[:10] for s in snapshots]

        print(f"[WaveView] buy_names: {self._buy_names}")
        print(f"[WaveView] sell_names: {self._sell_names}")

        total_conditions = len(self._buy_names) + len(self._sell_names)
        if total_conditions == 0:
            self._show_empty_hint("当前策略无买入/卖出条件，请先添加条件后再监控")
            return

        # 计算左轴宽度：基于最长条件名（每个中文字约 12px，英文约 7px）
        all_names = self._buy_names + self._sell_names
        max_name_len = max((len(n) for n in all_names), default=6)
        self._left_axis_width = max(120, min(250, max_name_len * 12 + 20))

        n = len(snapshots)
        # 使用 snapshot.bar_index 作为 x 坐标（和 K线图 x 轴对齐）
        self._x_indices = np.array([s.bar_index for s in snapshots], dtype=float)
        row = 0
        self._label_rows = set()  # 记录标签行的行号

        # ── 买入条件波形 ──────────────────────────────
        if self._buy_names:
            self._glw.addLabel(
                "  买入条件", row=row, col=0,
                color=_GRN, size="10pt")
            self._label_rows.add(row)
            row += 1

            for cond_idx, name in enumerate(self._buy_names):
                y = np.array([
                    1.0 if (cond_idx < len(s.buy_details) and s.buy_details[cond_idx].passed)
                    else 0.0
                    for s in snapshots
                ])
                pass_count = int(y.sum())
                print(f"[WaveView] BUY [{cond_idx}] '{name}': {pass_count}/{n} passed, x_range=[{self._x_indices[0]:.0f}, {self._x_indices[-1]:.0f}]")
                self._add_waveform_row(row, name, y, _GRN, (166, 227, 161, 50))
                row += 1

        # ── 卖出条件波形 ──────────────────────────────────
        if self._sell_names:
            self._glw.addLabel(
                "  卖出条件", row=row, col=0,
                color=_RED, size="10pt")
            self._label_rows.add(row)
            row += 1

            # 需要持仓上下文的指标（在纯技术评估中无法产生信号）
            _HOLD_CONTEXT_INDICATORS = {"MAX_HOLD_DAYS"}

            for cond_idx, name in enumerate(self._sell_names):
                # 获取 indicator 类型
                indicator = ""
                if snapshots[0].sell_details and cond_idx < len(snapshots[0].sell_details):
                    indicator = snapshots[0].sell_details[cond_idx].indicator

                # 确保名称不为空
                display_name = name if name else (indicator or f"卖出条件{cond_idx+1}")

                y = np.array([
                    1.0 if (cond_idx < len(s.sell_details) and s.sell_details[cond_idx].passed)
                    else 0.0
                    for s in snapshots
                ])
                pass_count = int(y.sum())
                print(f"[WaveView] SELL [{cond_idx}] '{display_name}' (ind={indicator}): {pass_count}/{n} passed, x_range=[{self._x_indices[0]:.0f}, {self._x_indices[-1]:.0f}]")

                # 持仓上下文条件：标注"(需持仓)"并用灰色显示
                if indicator in _HOLD_CONTEXT_INDICATORS:
                    display_name = f"{display_name}(需持仓)"
                    self._add_waveform_row(row, display_name, y, _MUT, (108, 112, 134, 30))
                else:
                    self._add_waveform_row(row, display_name, y, _RED, (243, 139, 168, 50))
                row += 1

        # 最后一行显示 X 轴日期
        if self._plots:
            last_plot = self._plots[-1]
            bottom_axis = last_plot.getAxis("bottom")
            bottom_axis.show()
            bottom_axis.setHeight(20)

        # 设置行拉伸因子：标题行固定高度，波形行等比例拉伸
        ci_layout = self._glw.ci.layout
        ci_layout.setSpacing(0)  # 行间距设为 0
        for r in range(row):
            if r in self._label_rows:
                ci_layout.setRowFixedHeight(r, 16)
                ci_layout.setRowStretchFactor(r, 0)
            else:
                ci_layout.setRowStretchFactor(r, 1)

    def _add_waveform_row(self, row: int, name: str,
                          y: np.ndarray,
                          color: str, fill_rgba: tuple) -> None:
        """添加一行波形子图"""
        plot = self._glw.addPlot(row=row, col=0)
        # 不设置 minimumHeight，让 stretch factor 完全控制高度分配
        plot.showGrid(x=False, y=False)
        plot.setYRange(-0.15, 1.25, padding=0)
        plot.setMouseEnabled(x=True, y=False)
        plot.hideButtons()
        # 压缩内部边距，使波形区更紧凑
        plot.setContentsMargins(0, 0, 0, 0)
        plot.getViewBox().setDefaultPadding(0)

        # 左轴显示条件名（完整显示，动态宽度）
        left_axis = plot.getAxis("left")
        left_axis.setTicks([[(0.5, name)]])
        left_axis.setTextPen(color)
        left_axis.setWidth(getattr(self, '_left_axis_width', 140))
        left_axis.setStyle(showValues=True)

        # X轴默认隐藏
        bottom_axis = plot.getAxis("bottom")
        bottom_axis.setTextPen(_MUT)
        bottom_axis.setHeight(0)
        bottom_axis.hide()

        # 画阶梯波形（使用 bar_index 作为 x，和 K线图对齐）
        x_step, y_step = self._make_step_data_aligned(self._x_indices, y)
        plot.plot(x_step, y_step,
                  pen=pg.mkPen(color, width=2.5),
                  fillLevel=0,
                  fillBrush=pg.mkBrush(*fill_rgba))

        # 画 0.5 参考线（虚线）
        plot.addLine(y=0.5, pen=pg.mkPen(_MUT, width=0.5,
                     style=QtCore.Qt.PenStyle.DotLine))

        # 添加竖线（用于十字线同步）
        vline = pg.InfiniteLine(angle=90, pen=pg.mkPen(_MUT, width=1,
                                style=QtCore.Qt.PenStyle.DashLine))
        vline.setVisible(False)
        plot.addItem(vline, ignoreBounds=True)
        self._vlines.append(vline)

        # X轴联动（波形子图之间先互相联动）
        if self._plots:
            plot.setXLink(self._plots[0])

        self._plots.append(plot)

    def set_vline_pos(self, x: float) -> None:
        """设置所有波形竖线位置（由外部十字线联动调用）"""
        for vl in self._vlines:
            vl.setPos(x)
            vl.setVisible(True)

    def hide_vlines(self) -> None:
        """隐藏所有波形竖线"""
        for vl in self._vlines:
            vl.setVisible(False)

    def _show_empty_hint(self, text: str) -> None:
        """当无数据时显示提示"""
        self._glw.clear()
        self._glw.addLabel(text, row=0, col=0,
                           color=_MUT, size="12pt")

    @staticmethod
    def _make_step_data_aligned(x_indices: np.ndarray, y: np.ndarray):
        """
        将 0/1 序列转为阶梯波形坐标，使用 bar_index 作为 x。
        每个 bar 占据 [bar_index-0.4, bar_index+0.4] 区间，值为 y[i]。
        这样波形 x 轴和 K 线图完全对齐。
        """
        n = len(y)
        x_out = np.empty(2 * n)
        y_out = np.empty(2 * n)
        # 向量化：避免 Python for 循环
        x_out[0::2] = x_indices - 0.4
        x_out[1::2] = x_indices + 0.4
        y_out[0::2] = y
        y_out[1::2] = y
        return x_out, y_out


class ConditionMonitorWidget(QtWidgets.QWidget):
    """
    条件监控主 Widget：上方 K 线图（复用 KlineViewTab）+ 下方条件波形图。
    三区同步：X轴联动 + 十字竖线贯穿 + 滚轮同步缩放。
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._current_symbol: str = ""
        self._current_snapshots: List[ConditionSnapshot] = []
        self._synced: bool = False

        self._init_ui()

    def _init_ui(self):
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # 上下分栏：K线图 + 波形图
        splitter = QtWidgets.QSplitter(QtCore.Qt.Orientation.Vertical)
        splitter.setHandleWidth(5)
        splitter.setStyleSheet(
            "QSplitter::handle { background: #45475a; }"
            "QSplitter::handle:hover { background: #89b4fa; }")

        # 上方：完整 K 线图（复用 KlineViewTab，和 Chart tab 完全一致）
        self._kline_tab = KlineViewTab()
        splitter.addWidget(self._kline_tab)

        # 下方：条件波形图
        self._waveform_view = ConditionWaveformView()
        splitter.addWidget(self._waveform_view)

        # 高度比例 6:4
        splitter.setStretchFactor(0, 6)
        splitter.setStretchFactor(1, 4)

        layout.addWidget(splitter, stretch=1)

    # ── 三区同步 ──────────────────────────────────────────────────

    def _setup_sync(self) -> None:
        """
        建立 X 轴联动和十字线同步。
        必须在 K 线和波形都加载完数据后调用。
        """
        chart = self._kline_tab._chart
        main_plot = chart._main_plot

        # 1. 波形子图 X 轴联动到 K 线主图
        waveform_plots = self._waveform_view.get_plots()
        for wp in waveform_plots:
            wp.setXLink(main_plot)

        # 2. 监听 K 线主图的鼠标移动，同步竖线到波形区
        # 替换原来的 SignalProxy，增加波形竖线同步
        try:
            chart._proxy.disconnect()
        except Exception:
            pass

        def _on_mouse_moved_synced(evt):
            """同时更新 K线十字线 + 波形竖线"""
            pos = evt[0]
            if main_plot.sceneBoundingRect().contains(pos):
                mp = main_plot.vb.mapSceneToView(pos)
                x = mp.x()
                # 更新 K 线自身的十字线
                chart._vline.setPos(x)
                chart._hline.setPos(mp.y())
                # 更新波形区竖线
                self._waveform_view.set_vline_pos(x)
                # 更新 K 线信息栏
                chart._on_mouse_moved(evt)
            else:
                self._waveform_view.hide_vlines()

        chart._proxy = pg.SignalProxy(
            main_plot.scene().sigMouseMoved,
            rateLimit=60, slot=_on_mouse_moved_synced)

        # 3. 也监听波形区的鼠标移动，反向同步竖线到 K 线区
        for wp in waveform_plots:
            scene = wp.scene()
            if scene:
                def _make_wave_handler(wave_plot):
                    def _handler(evt):
                        pos = evt[0]
                        if wave_plot.sceneBoundingRect().contains(pos):
                            mp = wave_plot.vb.mapSceneToView(pos)
                            x = mp.x()
                            chart._vline.setPos(x)
                            chart._vline.setVisible(True)
                            self._waveform_view.set_vline_pos(x)
                    return _handler

                pg.SignalProxy(
                    scene.sigMouseMoved,
                    rateLimit=60,
                    slot=_make_wave_handler(wp))

        self._synced = True

    # ── 公开接口 ──────────────────────────────────────────────────

    def load_snapshots(self, symbol: str, snapshots: List[ConditionSnapshot],
                       bars: list = None,
                       buy_dates: list = None,
                       sell_dates: list = None) -> None:
        """
        加载监控数据。

        Args:
            symbol: 股票代码
            snapshots: 条件快照列表
            bars: K线数据（BarData列表），用于绘制K线图
            buy_dates: 回测/选股产生的买入信号日期列表（与 Chart tab 一致）
            sell_dates: 回测/选股产生的卖出信号日期列表（与 Chart tab 一致）
        """
        self._current_symbol = symbol
        self._current_snapshots = snapshots
        self._synced = False

        if bars:
            # 直接将传入的 bars 渲染到 K 线图（不走数据库加载）
            # 这样 K 线 X 轴 = 0..len(bars)-1，和波形 bar_index 完全对齐
            buy_indices = []
            sell_indices = []
            if buy_dates or sell_dates:
                # 将日期字符串转为 bar 索引
                date_to_idx = {}
                for i, b in enumerate(bars):
                    dt = b.datetime
                    if dt.hour == 0 and dt.minute == 0:
                        key = dt.strftime('%Y-%m-%d')
                    else:
                        key = dt.strftime('%Y-%m-%d %H:%M')
                    date_to_idx[key] = i
                    # 也存短格式
                    date_to_idx[dt.strftime('%Y-%m-%d')] = i

                for d in (buy_dates or []):
                    d = d.strip()[:10]
                    if d in date_to_idx:
                        buy_indices.append(date_to_idx[d])
                for d in (sell_dates or []):
                    d = d.strip()[:10]
                    if d in date_to_idx:
                        sell_indices.append(date_to_idx[d])

            # 先配置 MA 均线（使用 KlineViewTab 的工具栏配置）
            try:
                ma_config = self._kline_tab._get_ma_config()
            except Exception:
                # 如果工具栏还没初始化，用默认配置
                ma_config = [
                    (5, '#f9e2af', True),
                    (20, '#89b4fa', True),
                    (60, '#a6e3a1', True),
                ]
            self._kline_tab._chart.set_ma_flags(ma_config, show_triggers=True)
            self._kline_tab._chart.load(bars,
                                        buy_indices=buy_indices,
                                        sell_indices=sell_indices)
            # 更新标题
            self._kline_tab._title_lbl.setText(
                f"<b style='color:#89b4fa'>{symbol}</b>  "
                f"<span style='color:#6c7086'>({len(bars)} bars)</span>")

            dates = [str(s.dt)[:10] for s in snapshots]
            self._waveform_view.load_data(snapshots, dates)
            # 同步波形数据到 KlineViewTab（供全屏窗口使用）
            self._kline_tab.set_waveform_data(snapshots, dates)

        # 建立三区同步
        if bars and snapshots:
            try:
                self._setup_sync()
            except Exception as e:
                print(f"[Monitor] sync setup failed: {e}")
