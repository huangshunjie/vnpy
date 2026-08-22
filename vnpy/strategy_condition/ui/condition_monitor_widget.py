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
                  dates: List[str] = None,
                  buy_indices: List[int] = None,
                  sell_indices: List[int] = None) -> None:
        """
        加载快照数据，生成波形图。

        Args:
            snapshots: 条件快照列表
            dates: 日期字符串列表
            buy_indices: 买入信号在 bars 中的索引列表（用于模拟持仓状态）
            sell_indices: 卖出信号在 bars 中的索引列表（用于模拟持仓状态）
        """
        self._snapshots = snapshots
        self._buy_indices = buy_indices or []
        self._sell_indices = sell_indices or []
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

            # ── 回测持仓段辅助波形（方案A）─────────────────────
            # 语义：0/1 波形，高电平代表"回测在这根 K 线处于持仓段"。
            # 用途：把"卖出条件"波形和此波形做视觉交集——
            #   - 卖出条件亮 且 持仓段亮 → 回测在此点会真实卖出
            #   - 卖出条件亮 且 持仓段暗 → 空仓/T+1/冷却期，回测不动作
            #   - 卖出条件暗 且 持仓段亮 → 持仓中但无卖出信号，继续持有
            hold_y = self._compute_backtest_position_waveform(snapshots)
            hold_hits = int(hold_y.sum())
            print(
                f"[WaveView] BACKTEST POSITION: {hold_hits}/{n} bars in position "
                f"(buy_idx={len(self._buy_indices)}, "
                f"sell_idx={len(self._sell_indices)})"
            )
            # 用琥珀色，和绿/红都区分开
            self._add_waveform_row(
                row, "回测持仓段",
                hold_y,
                "#f9a825",              # 琥珀色前景线
                (249, 168, 37, 55),     # 半透明琥珀色填充
            )
            row += 1

            for cond_idx, name in enumerate(self._sell_names):
                # 获取 indicator 类型
                indicator = ""
                if snapshots[0].sell_details and cond_idx < len(snapshots[0].sell_details):
                    detail0 = snapshots[0].sell_details[cond_idx]
                    indicator = detail0.indicator

                # 确保名称不为空
                display_name = name if name else (indicator or f"卖出条件{cond_idx+1}")

                # 所有卖出条件统一从 snapshot 的 sell_details 中读取评估结果
                # 监控引擎 _evaluate_bar() 已根据持仓上下文（entry_price, peak_price, hold_bars）
                # 正确评估了每个卖出条件（含 TRAILING_STOP, MAX_HOLD_DAYS 等），
                # 无持仓时全部为 False，有持仓时用 eval_exit() 精确计算。
                y = np.array([
                    1.0 if (cond_idx < len(s.sell_details) and s.sell_details[cond_idx].passed)
                    else 0.0
                    for s in snapshots
                ])
                # 对需要持仓上下文的指标添加标注
                if indicator == "MAX_HOLD_DAYS":
                    display_name = f"{display_name}(需持仓)"
                pass_count = int(y.sum())
                print(f"[WaveView] SELL [{cond_idx}] '{display_name}' (ind={indicator}): {pass_count}/{n} passed, x_range=[{self._x_indices[0]:.0f}, {self._x_indices[-1]:.0f}]")
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

    def _compute_backtest_position_waveform(
        self,
        snapshots: List[ConditionSnapshot],
    ) -> np.ndarray:
        """
        构造"回测持仓段"波形（方案 A 辅助波形）。

        高电平语义（=1）：
            这根 K 线的 bar_index 落在某段 [buy_idx, sell_idx] 之内
            —— 即回测在这一根上处于持仓状态。

        规则：
          - buy_idx 与 sell_idx 均来自 self._buy_indices / self._sell_indices，
            由上层将 buy_dates / sell_dates 匹配到 bar 索引得到。
          - 若某次买入之后没有对应的卖出（信号列表未成交出场），
            视作持仓一直延续到序列末尾。
          - buy_indices / sell_indices 会先分别排序再依次配对，防止
            上游传入顺序不一致导致区间反向。
        """
        n = len(snapshots)
        y = np.zeros(n, dtype=float)

        buy_ix = sorted(self._buy_indices)
        sell_ix = sorted(self._sell_indices)
        if not buy_ix:
            return y

        # 配对 buy → next sell（严格 sell > buy）
        used_sell = 0
        ranges: List[tuple] = []
        for b in buy_ix:
            s = None
            while used_sell < len(sell_ix):
                if sell_ix[used_sell] > b:
                    s = sell_ix[used_sell]
                    used_sell += 1
                    break
                # 不合法（sell 早于当前 buy），跳过
                used_sell += 1
            ranges.append((b, s))

        # 快速数组填充：对每根 snapshot，检查其 bar_index 是否落在任一区间内
        # 区间语义：[b, s]（含端点）—— buy 当日和卖出当日都算持仓（保持与回测口径一致）
        for i, snap in enumerate(snapshots):
            bar_idx = snap.bar_index
            for b, s in ranges:
                if bar_idx < b:
                    continue
                if s is None:
                    # 未卖出的持仓，延续到底
                    y[i] = 1.0
                    break
                if bar_idx <= s:
                    y[i] = 1.0
                    break

        return y

    def _compute_hold_days_waveform(
        self,
        snapshots: List[ConditionSnapshot],
        max_days: int,
    ) -> np.ndarray:
        """
        基于 buy/sell indices 模拟持仓状态，计算 MAX_HOLD_DAYS 波形。

        逻辑：
        - 买入信号后开始计数持仓天数
        - 卖出信号后持仓天数归零
        - 当持仓天数 >= max_days 时，波形为 1（条件满足）
        """
        n = len(snapshots)
        y = np.zeros(n)

        if not self._buy_indices and not self._sell_indices:
            return y

        # 构建事件时间线：用 bar_index -> event_type
        buy_set = set(self._buy_indices)
        sell_set = set(self._sell_indices)

        holding = False
        hold_start_idx = -1

        for i, snap in enumerate(snapshots):
            bar_idx = snap.bar_index

            if bar_idx in buy_set and not holding:
                holding = True
                hold_start_idx = i

            if holding:
                hold_days = i - hold_start_idx
                if hold_days >= max_days:
                    y[i] = 1.0

            if bar_idx in sell_set and holding:
                holding = False
                hold_start_idx = -1

        return y

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


class _PeriodMonitorPanel(QtWidgets.QWidget):
    """单一周期的 K线、成交量和条件波形联动面板。"""

    lifecycle_info_changed = QtCore.Signal(str, str)
    cursor_datetime_changed = QtCore.Signal(object)

    def __init__(self, period_title: str, parent=None):
        super().__init__(parent)
        self._period_title = period_title
        self._current_symbol: str = ""
        self._current_snapshots: List[ConditionSnapshot] = []
        self._current_bars: list = []
        self._synced: bool = False
        # 用于全屏联动：由 ConditionMonitorWidget 设置
        self._parent_monitor = None
        self._panel_type = 'unknown'  # 'daily' 或 'minute'
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
        # 传递面板引用给 KlineViewTab（供全屏窗口获取联动上下文）
        self._kline_tab._owner_panel = self
        splitter.addWidget(self._kline_tab)

        # 下方：条件波形图
        self._waveform_view = ConditionWaveformView()
        splitter.addWidget(self._waveform_view)

        # 高度比例 6:4
        splitter.setStretchFactor(0, 6)
        splitter.setStretchFactor(1, 4)
        splitter.setSizes([450, 300])

        self._splitter = splitter
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
            """同时更新 K线十字线 + 波形竖线 + Lifecycle面板"""
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
                # 更新右侧 Lifecycle 诊断面板
                self._update_lifecycle_for_bar(int(round(x)))
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

    def _update_lifecycle_for_bar(self, bar_index: int) -> None:
        """
        根据光标所在 bar_index，从 snapshot 提取诊断信息，
        通过 lifecycle_info_changed 信号发送给外部（底部状态栏）。
        """
        if not self._current_snapshots:
            return

        # 查找 bar_index 对应的 snapshot
        snapshot = None
        for s in self._current_snapshots:
            if s.bar_index == bar_index:
                snapshot = s
                break

        # 如果精确匹配不到，找最近的
        if snapshot is None:
            min_dist = float('inf')
            for s in self._current_snapshots:
                dist = abs(s.bar_index - bar_index)
                if dist < min_dist:
                    min_dist = dist
                    snapshot = s

        if snapshot is None:
            return

        # 构造两行诊断文本
        sig = getattr(snapshot, 'signal_type', None) or ""
        dt_str = str(snapshot.dt)[:16] if snapshot.dt else ""

        # 第一行：持仓状态 + 信号类型
        holding = getattr(snapshot, 'holding', False)
        hold_bars = getattr(snapshot, 'hold_bars', 0)
        if holding:
            status = f"持仓中(第{hold_bars}根)"
        else:
            status = "未持仓"
        line1 = (
            f"[{self._period_title}] [{dt_str}] "
            f"{status}  信号:{sig or '无'}")

        # 第二行：卖出条件触发摘要
        fired = []
        for d in snapshot.sell_details:
            if d.passed:
                name = d.condition_name or d.indicator or "?"
                fired.append(name)
        if fired:
            line2 = f"卖出触发: {', '.join(fired)}"
        else:
            line2 = "卖出条件均未触发"

        self.lifecycle_info_changed.emit(line1, line2)
        self.cursor_datetime_changed.emit(snapshot.dt)

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
        self._current_bars = list(bars or [])
        self._synced = False

        if bars:
            # 直接将传入的 bars 渲染到 K 线图（不走数据库加载）
            # 这样 K 线 X 轴 = 0..len(bars)-1，和波形 bar_index 完全对齐
            buy_indices = []
            sell_indices = []
            if buy_dates or sell_dates:
                # 将日期字符串转为 bar 索引
                # 建立多种格式的索引映射，支持日线和分钟线
                date_to_idx = {}
                for i, b in enumerate(bars):
                    dt = b.datetime
                    # 精确到分钟的key（分钟线用）
                    key_full = dt.strftime('%Y-%m-%d %H:%M')
                    date_to_idx[key_full] = i
                    # 精确到秒（某些datetime带秒）
                    key_sec = dt.strftime('%Y-%m-%d %H:%M:%S')
                    date_to_idx[key_sec] = i
                    # 日期key（日线用，分钟线下同一天多根K线只保留最后一根）
                    key_date = dt.strftime('%Y-%m-%d')
                    date_to_idx[key_date] = i

                for d in (buy_dates or []):
                    d = d.strip()
                    if d in date_to_idx:
                        buy_indices.append(date_to_idx[d])
                    elif d[:10] in date_to_idx:
                        # 日期部分匹配（fallback）
                        buy_indices.append(date_to_idx[d[:10]])
                for d in (sell_dates or []):
                    d = d.strip()
                    if d in date_to_idx:
                        sell_indices.append(date_to_idx[d])
                    elif d[:10] in date_to_idx:
                        sell_indices.append(date_to_idx[d[:10]])

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
                f"<span style='color:#cba6f7'>{self._period_title}</span>  "
                f"<span style='color:#6c7086'>({len(bars)} bars)</span>")

            dates = [str(s.dt)[:16] for s in (snapshots or [])]
            self._waveform_view.load_data(
                snapshots or [], dates,
                buy_indices=buy_indices,
                sell_indices=sell_indices,
            )
            # 同步波形数据到 KlineViewTab（供全屏窗口使用）
            self._kline_tab.set_waveform_data(
                snapshots or [], dates,
                buy_indices=buy_indices,
                sell_indices=sell_indices,
            )

        # 建立三区同步（只要 bars 已加载就建立——即使 snapshots 为空，
        # 波形和K线间的 X 轴联动仍然需要。snapshots 为空只是不显示 lifecycle 面板）
        if bars:
            try:
                self._setup_sync()
            except Exception as e:
                print(f"[Monitor] sync setup failed: {e}")

            # 数据加载后，自动显示最后一根 bar 的 Lifecycle 诊断
            if snapshots:
                last_bar_idx = snapshots[-1].bar_index
                self._update_lifecycle_for_bar(last_bar_idx)

    def show_empty(self, symbol: str, message: str) -> None:
        self._current_symbol = symbol
        self._current_snapshots = []
        self._current_bars = []
        self._kline_tab._chart.clear()
        self._kline_tab._title_lbl.setText(
            f"<b style='color:#89b4fa'>{symbol}</b>  "
            f"<span style='color:#f38ba8'>{message}</span>")
        self._waveform_view._show_empty_hint(message)

    def focus_datetime(self, dt, completed_daily: bool = False):
        """定位目标时刻；日线联动只使用目标日期前的完整日线。"""
        if dt is None or not self._current_bars:
            return None
        target_index = None
        for index, bar in enumerate(self._current_bars):
            bar_dt = getattr(bar, "dt", getattr(bar, "datetime", None))
            if bar_dt is None:
                continue
            if completed_daily and bar_dt.date() >= dt.date():
                continue
            if bar_dt <= dt:
                target_index = index
        if target_index is None:
            return None
        chart = self._kline_tab._chart
        chart._vline.setPos(target_index)
        chart._vline.setVisible(True)
        self._waveform_view.set_vline_pos(target_index)
        target_bar = self._current_bars[target_index]
        return getattr(target_bar, "dt", getattr(target_bar, "datetime", None))


class ConditionMonitorWidget(QtWidgets.QWidget):
    """日线、分钟和双周期条件监控容器。"""

    lifecycle_info_changed = QtCore.Signal(str, str)
    minute_interval_changed = QtCore.Signal()
    # 日线点击信号（datetime, {buy:[...], sell:[...]}）—— 用于全屏联动
    daily_bar_clicked = QtCore.Signal(object, dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()

    def _init_ui(self) -> None:
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        toolbar = QtWidgets.QWidget()
        toolbar.setFixedHeight(38)
        toolbar.setStyleSheet(
            f"background:{_BG};border-bottom:1px solid {_BORD};")
        row = QtWidgets.QHBoxLayout(toolbar)
        row.setContentsMargins(10, 4, 10, 4)
        row.addWidget(QtWidgets.QLabel("显示模式"))
        self._mode_cb = QtWidgets.QComboBox()
        self._mode_cb.addItems(["日线", "分钟", "双周期"])
        self._mode_cb.setCurrentText("双周期")
        self._mode_cb.currentTextChanged.connect(self._apply_mode)
        row.addWidget(self._mode_cb)
        row.addSpacing(12)
        row.addWidget(QtWidgets.QLabel("分钟周期"))
        self._minute_cb = QtWidgets.QComboBox()
        for value, label in (
            ("1m", "1分钟"), ("5m", "5分钟"), ("15m", "15分钟"),
            ("30m", "30分钟"), ("1h", "60分钟")):
            self._minute_cb.addItem(label, value)
        self._minute_cb.setCurrentIndex(1)
        self._minute_cb.currentIndexChanged.connect(
            lambda _idx: self.minute_interval_changed.emit())
        row.addWidget(self._minute_cb)
        row.addStretch()
        self._status_lbl = QtWidgets.QLabel("等待加载双周期数据")
        self._status_lbl.setStyleSheet(f"color:{_MUT};")
        row.addWidget(self._status_lbl)
        layout.addWidget(toolbar)

        self._daily_panel = _PeriodMonitorPanel("日线过滤 / 日线风控")
        self._minute_panel = _PeriodMonitorPanel("分钟触发 / 分钟退出")
        self._daily_panel.lifecycle_info_changed.connect(
            self.lifecycle_info_changed.emit)
        self._minute_panel.lifecycle_info_changed.connect(
            self.lifecycle_info_changed.emit)
        self._minute_panel.cursor_datetime_changed.connect(
            self._sync_daily_cursor)

        # 设置面板引用和类型（用于全屏联动）
        self._daily_panel._parent_monitor = self
        self._daily_panel._panel_type = 'daily'
        self._minute_panel._parent_monitor = self
        self._minute_panel._panel_type = 'minute'

        self._period_splitter = QtWidgets.QSplitter(
            QtCore.Qt.Orientation.Vertical)
        self._period_splitter.setHandleWidth(6)
        self._period_splitter.addWidget(self._daily_panel)
        self._period_splitter.addWidget(self._minute_panel)
        self._period_splitter.setStretchFactor(0, 1)
        self._period_splitter.setStretchFactor(1, 1)
        layout.addWidget(self._period_splitter, 1)
        self._apply_mode("双周期")

        # 连接日线K线点击事件（实现日线→分钟联动）
        self._connect_daily_click_handler()

        # 分钟周期下拉变化时，调用方可主动通知重新加载数据
        # （由 StrategyConditionWidget._feed_monitor 监听此信号）
        self.minute_interval_changed.connect(
            self._on_minute_interval_changed)

    def _on_minute_interval_changed(self) -> None:
        """
        分钟周期下拉框变化时清空当前分钟面板的缓存标记，
        并提示调用方重新加载数据（信号会冒泡到 widget 端）。
        """
        # 重置分钟面板的 cache 状态，让 _feed_monitor 重新加载
        if hasattr(self, '_minute_panel'):
            self._minute_panel._last_minute_interval_key = (
                self.minute_interval_key())

    def _connect_daily_click_handler(self):
        """连接日线K线点击处理器"""
        try:
            if hasattr(self._daily_panel, '_kline_tab'):
                kline_tab = self._daily_panel._kline_tab
                if hasattr(kline_tab, '_chart'):
                    kline_tab._chart.bar_clicked.connect(
                        self._on_daily_bar_clicked)
        except Exception as e:
            print(f"[联动] 连接日线点击失败: {e}")

    def _on_daily_bar_clicked(self, clicked_dt):
        """处理日线K线点击事件"""
        try:
            clicked_date = clicked_dt.date()
            print(f"[联动] 日线K线被点击: {clicked_date}")

            # 查找该日期的买卖信号
            signals = self._get_signals_for_date(clicked_date)
            print(f"[联动] 找到信号: 买入={len(signals['buy'])}, 卖出={len(signals['sell'])}")

            # 更新分钟面板
            self._update_minute_view_for_date(clicked_date, signals)

            # 发射信号（供全屏窗口监听）
            self.daily_bar_clicked.emit(clicked_dt, signals)

        except Exception as e:
            print(f"[联动] 处理日线点击失败: {e}")
            import traceback
            traceback.print_exc()

    def _get_signals_for_date(self, target_date):
        """获取指定日期的所有信号时间（优先使用真实 snapshot.signal_type）

        优先从分钟面板的 snapshots 读取每根 bar 的 signal_type，
        定位目标日期内真正触发买入/卖出的分钟 K 线 datetime。
        若无 snapshots 或无 signal_type，降级为"首根买入/末根卖出"方案。
        """
        result = {'buy': [], 'sell': []}

        if not hasattr(self, '_minute_panel'):
            return result

        minute_panel = self._minute_panel

        # ── 方案A：从真实 snapshot.signal_type 读取（优先）──────────────
        minute_snapshots = getattr(minute_panel, '_current_snapshots', [])
        if minute_snapshots:
            for snap in minute_snapshots:
                snap_dt = getattr(snap, 'dt', None)
                if snap_dt is None:
                    continue
                if snap_dt.date() != target_date:
                    continue
                signal_type = getattr(snap, 'signal_type', None)
                if signal_type == 'buy':
                    result['buy'].append(snap_dt)
                elif signal_type == 'sell':
                    result['sell'].append(snap_dt)
            # 若找到真实信号，直接返回
            if result['buy'] or result['sell']:
                return result

        # ── 方案B：降级方案（无 snapshots 或无 signal_type）─────────────
        minute_bars = getattr(minute_panel, '_current_bars', [])
        if not minute_bars:
            return result

        # 收集当前日线面板持有的买卖日期
        daily_panel = self._daily_panel
        buy_dates = getattr(daily_panel, '_last_buy_dates', None)
        sell_dates = getattr(daily_panel, '_last_sell_dates', None)

        # 如果日线面板未缓存，尝试从 KlineViewTab 获取
        if buy_dates is None:
            buy_dates = getattr(daily_panel._kline_tab, '_last_buy_dates', [])
        if sell_dates is None:
            sell_dates = getattr(daily_panel._kline_tab, '_last_sell_dates', [])

        # 目标日期字符串
        date_str = target_date.strftime('%Y-%m-%d')

        # 判断目标日期是否为买入/卖出信号日
        is_buy_day = any(str(d)[:10] == date_str for d in (buy_dates or []))
        is_sell_day = any(str(d)[:10] == date_str for d in (sell_dates or []))

        # 若该日是信号日，则将该日所有分钟bar的datetime作为信号候选
        if is_buy_day or is_sell_day:
            day_minute_dts = [
                b.datetime for b in minute_bars
                if b.datetime.date() == target_date
            ]
            if day_minute_dts:
                # 买入信号标记在当天第一根分钟K线（开盘）
                # 卖出信号标记在当天最后一根分钟K线（收盘）
                if is_buy_day:
                    result['buy'].append(day_minute_dts[0])
                if is_sell_day:
                    result['sell'].append(day_minute_dts[-1])

        return result

    def _update_minute_view_for_date(self, target_date, signals):
        """更新分钟K线视图，聚焦到指定日期"""
        try:
            if not hasattr(self, '_minute_panel'):
                return

            minute_panel = self._minute_panel
            if not hasattr(minute_panel, '_kline_tab'):
                return

            kline_tab = minute_panel._kline_tab

            # 调用 focus_on_date 方法
            if hasattr(kline_tab, 'focus_on_date'):
                kline_tab.focus_on_date(target_date, signals)
            else:
                print(f"[联动] KlineViewTab 缺少 focus_on_date 方法")

        except Exception as e:
            print(f"[联动] 更新分钟视图失败: {e}")
            import traceback
            traceback.print_exc()

    def _sync_daily_cursor(self, minute_dt) -> None:
        daily_dt = self._daily_panel.focus_datetime(
            minute_dt, completed_daily=True)
        if daily_dt is None:
            self._status_lbl.setText(
                f"分钟 {str(minute_dt)[:16]} / 无可用的上一完整日线")
            return
        self._status_lbl.setText(
            f"分钟 {str(minute_dt)[:16]} / 引用日线 {str(daily_dt)[:10]}")

    def minute_interval_key(self) -> str:
        return str(self._minute_cb.currentData() or "5m")

    def minute_interval_text(self) -> str:
        return self._minute_cb.currentText()

    def _apply_mode(self, mode: str) -> None:
        self._daily_panel.setVisible(mode in ("日线", "双周期"))
        self._minute_panel.setVisible(mode in ("分钟", "双周期"))
        self._minute_cb.setEnabled(mode != "日线")

    def load_layered_data(
        self, symbol: str,
        daily_snapshots: List[ConditionSnapshot], daily_bars: list,
        minute_snapshots: List[ConditionSnapshot] = None,
        minute_bars: list = None,
        buy_dates: list = None, sell_dates: list = None,
    ) -> None:
        """
        双周期数据加载（双周期 Monitor Tab 入口）。

        Args:
            symbol: 股票代码
            daily_snapshots: 日线 ConditionSnapshot 列表
            daily_bars: 日线 K 线数据
            minute_snapshots: 分钟 ConditionSnapshot 列表（可为空——降级场景）
            minute_bars: 分钟 K 线数据（来自 _load_bars_by_date_range）
            buy_dates: 回测/选股产生的买入日期列表
            sell_dates: 回测/选股产生的卖出日期列表

        兼容旧调用 + 新场景：
            旧版 widget 只传日线 → 自动构造"日内首根买入/末根卖出"的简易 snapshots
            新版 widget 传日+分双层数据 → 完整驱动双周期面板
        """
        buy_dates = list(buy_dates or [])
        sell_dates = list(sell_dates or [])
        minute_bars = list(minute_bars or [])
        minute_snapshots = list(minute_snapshots or [])

        if daily_bars:
            self._daily_panel.load_snapshots(
                symbol, daily_snapshots, daily_bars, buy_dates, sell_dates)
        else:
            self._daily_panel.show_empty(symbol, "缺少日线数据")

        if minute_bars:
            # ── 降级场景：调用方未生成 minute_snapshots ──
            # 用 bars + daily 买卖日期构造最小可用 snapshots，
            # 保证 _PeriodMonitorPanel.load_snapshots 不会因空 snapshots 短路退出。
            if not minute_snapshots:
                minute_snapshots = self._build_minute_snapshots_fallback(
                    symbol, minute_bars, buy_dates, sell_dates)
            self._minute_panel.load_snapshots(
                symbol, minute_snapshots, minute_bars,
                buy_dates, sell_dates)
        else:
            self._minute_panel.show_empty(
                symbol, f"缺少{self.minute_interval_text()}数据")

        # 缓存买卖日期到日线面板（供联动信号查询使用）
        self._daily_panel._last_buy_dates = list(buy_dates)
        self._daily_panel._last_sell_dates = list(sell_dates)
        self._status_lbl.setText(
            f"日线 {len(daily_bars)} 根 / "
            f"{self.minute_interval_text()} {len(minute_bars)} 根")
        print(
            f"[Monitor] load_layered_data {symbol}: "
            f"daily={len(daily_bars)} bars/{len(daily_snapshots)} snaps, "
            f"minute={len(minute_bars)} bars/{len(minute_snapshots)} snaps",
            flush=True,
        )

    def _build_minute_snapshots_fallback(
        self, symbol: str, minute_bars: list,
        buy_dates: list, sell_dates: list,
    ) -> list:
        """
        当调用方未生成 minute snapshots 时，根据 buy_dates/sell_dates 与
        minute_bars 的日内位置构造最小可用的 ConditionSnapshot 列表。

        规则（与 _get_signals_for_date 降级方案 B 一致）：
          - 每根 minute bar 对应一个 snapshot（signal_type 默认 None）
          - 匹配 buy_date 当日首根分钟 bar：signal_type = 'buy'
          - 匹配 sell_date 当日末根分钟 bar：signal_type = 'sell'
        """
        from ..monitor.condition_snapshot import ConditionSnapshot
        if not minute_bars:
            return []

        buy_date_set = set(str(d)[:10] for d in (buy_dates or []))
        sell_date_set = set(str(d)[:10] for d in (sell_dates or []))

        # 按日期分组：每组首根标记 buy，末根标记 sell
        by_date: dict = {}
        for i, bar in enumerate(minute_bars):
            try:
                dt = bar.datetime
                d_key = dt.strftime("%Y-%m-%d")
            except Exception:
                continue
            by_date.setdefault(d_key, []).append(i)

        snapshots = []
        for i, bar in enumerate(minute_bars):
            try:
                dt = bar.datetime
                d_key = dt.strftime("%Y-%m-%d")
            except Exception:
                dt = None
                d_key = ""

            sig = None
            indices = by_date.get(d_key, [])
            if indices:
                if d_key in buy_date_set and i == indices[0]:
                    sig = "buy"
                elif d_key in sell_date_set and i == indices[-1]:
                    sig = "sell"

            try:
                snap = ConditionSnapshot(
                    dt=dt or bar.dt,
                    symbol=symbol,
                    price=float(getattr(bar, "close_price", 0.0)),
                    bar_index=i,
                    signal_type=sig,
                )
            except Exception:
                continue
            snapshots.append(snap)
        return snapshots

    def load_snapshots(self, symbol: str,
                       snapshots: List[ConditionSnapshot], bars: list = None,
                       buy_dates: list = None,
                       sell_dates: list = None) -> None:
        """兼容旧调用：单周期数据在日线面板显示。"""
        self._daily_panel.load_snapshots(
            symbol, snapshots, bars, buy_dates, sell_dates)
        self._daily_panel._last_buy_dates = list(buy_dates or [])
        self._daily_panel._last_sell_dates = list(sell_dates or [])
        self._mode_cb.setCurrentText("日线")
        self._status_lbl.setText(f"单周期 {len(bars or [])} 根")