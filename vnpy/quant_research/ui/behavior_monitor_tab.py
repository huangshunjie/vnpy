"""
K-Line Behavior Lab - 条件监控 Monitor Tab
展示研究条件在时间序列上的满足/不满足状态波形。

功能：
  - 上方：完整K线图（蜡烛图 + MA均线 + 成交量 + 信号标记 + 十字线）
  - 下方：条件波形图（每个条件一行，0/1 方波，数字信号风格）
  - 三区同步：K线区、成交量区、波形区 X轴联动 + 十字竖线贯穿
  - 条件满足率统计表

复用 Strategy Condition Engine 的 KlineViewTab + ConditionWaveformView 组件，
实现与 Strategy Condition Engine 完全一致的显示效果。
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

import numpy as np

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
    QPushButton, QLabel, QComboBox, QTableWidget,
    QTableWidgetItem, QHeaderView, QFrame, QGroupBox,
    QGridLayout, QScrollArea, QProgressBar, QApplication,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor

try:
    import pyqtgraph as pg
    HAS_PYQTGRAPH = True
except ImportError:
    HAS_PYQTGRAPH = False

# 复用 Strategy Condition Engine 的 K线图组件
from vnpy.strategy_condition.ui.kline_view import (
    KlineViewTab, KlineChartWidget, CandlestickItem, VolumeItem, DateAxis,
)

# ── 颜色常量 ──
_BG = "#1e1e2e"
_PANEL = "#181825"
_PAN2 = "#11111b"
_BORD = "#45475a"
_FG = "#cdd6f4"
_MUT = "#6c7086"
_BLU = "#89b4fa"
_GRN = "#a6e3a1"
_YLW = "#f9e2af"
_RED = "#f38ba8"
_MAV = "#cba6f7"
_TEAL = "#94e2d5"
_WAVE_BG = "#181825"

_COMBO_SS = (f"QComboBox{{background:{_PAN2};color:{_FG};"
             f"border:1px solid {_BORD};border-radius:4px;padding:4px 10px;font-size:13px;}}"
             f"QComboBox::drop-down{{border:none;width:20px;}}"
             f"QComboBox QAbstractItemView{{background:{_PAN2};color:{_FG};"
             f"selection-background-color:{_BLU};}}")


def _lbl(text, color=_FG, size=13, bold=False):
    w = QLabel(text)
    w.setStyleSheet(f"color:{color};font-size:{size}px;"
                    f"font-weight:{'bold' if bold else 'normal'};"
                    f"background:transparent;border:none;")
    return w


def _hline():
    f = QFrame()
    f.setFrameShape(QFrame.Shape.HLine)
    f.setStyleSheet(f"border:none;border-top:1px solid {_BORD};")
    return f


def _btn(text, color=_BLU, w=0):
    b = QPushButton(text)
    b.setStyleSheet(f"QPushButton{{background:{color};color:#1e1e2e;border:none;"
                    f"border-radius:4px;padding:7px 16px;font-size:13px;font-weight:bold;}}"
                    f"QPushButton:hover{{opacity:0.85;}}"
                    f"QPushButton:disabled{{background:{_BORD};color:{_MUT};}}")
    if w:
        b.setFixedWidth(w)
    return b


class BehaviorWaveformView(QWidget):
    """
    条件波形图组件（行为研究版）：
    用数字信号方波展示各研究条件随时间的满足/不满足状态。
    每个条件一行子图，高电平(1)=满足，低电平(0)=不满足。

    与 Strategy Condition Engine 的 ConditionWaveformView 完全一致的视觉风格。
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._plots: List[pg.PlotItem] = []
        self._vlines: List[pg.InfiniteLine] = []
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
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

    def set_vline_pos(self, x: float) -> None:
        """设置所有波形竖线位置"""
        for vl in self._vlines:
            vl.setPos(x)
            vl.setVisible(True)

    def hide_vlines(self) -> None:
        """隐藏所有波形竖线"""
        for vl in self._vlines:
            vl.setVisible(False)

    def load_data(self, conditions: List[str], cond_results,
                  events: list = None) -> None:
        """
        加载条件评估数据并渲染波形。

        Args:
            conditions: 条件名称列表
            cond_results: DataFrame(bool)，列名=条件名，行=时间序列
            events: 事件列表（用于标记触发点）
        """
        self._plots.clear()
        self._vlines.clear()
        self._glw.clear()

        if cond_results is None or cond_results.empty:
            self._glw.addLabel("暂无条件评估数据", row=0, col=0,
                               color=_MUT, size="12pt")
            return

        n = len(cond_results)
        x = np.arange(n, dtype=float)

        # 条件颜色循环（与 Strategy Condition Engine 一致的风格）
        colors = [_GRN, _BLU, _MAV, _TEAL, _YLW, _RED, "#fab387", "#74c7ec"]
        fill_alphas = [
            (166, 227, 161, 50), (137, 180, 250, 50), (203, 166, 247, 50),
            (148, 226, 213, 50), (249, 226, 175, 50), (243, 139, 168, 50),
            (250, 179, 135, 50), (116, 199, 236, 50),
        ]

        # 计算左轴宽度（动态适应最长条件名）
        max_name_len = max((len(c) for c in conditions), default=6) if conditions else 6
        left_axis_width = max(120, min(250, max_name_len * 12 + 20))

        row = 0
        label_rows = set()

        # 标题行
        self._glw.addLabel("  研究条件", row=row, col=0,
                           color=_GRN, size="10pt")
        label_rows.add(row)
        row += 1

        for cond_idx, cond_name in enumerate(conditions):
            if cond_name not in cond_results.columns:
                continue

            y = cond_results[cond_name].astype(float).values
            color = colors[cond_idx % len(colors)]
            fill = fill_alphas[cond_idx % len(fill_alphas)]

            self._add_waveform_row(
                row, cond_name, x, y, color, fill,
                left_axis_width, events, cond_results
            )
            row += 1

        # 最后一行显示 X 轴
        if self._plots:
            last_plot = self._plots[-1]
            bottom_axis = last_plot.getAxis("bottom")
            bottom_axis.show()
            bottom_axis.setHeight(20)

        # 行拉伸因子：标题行固定，波形行等比
        ci_layout = self._glw.ci.layout
        ci_layout.setSpacing(0)
        for r in range(row):
            if r in label_rows:
                ci_layout.setRowFixedHeight(r, 16)
                ci_layout.setRowStretchFactor(r, 0)
            else:
                ci_layout.setRowStretchFactor(r, 1)

    def _add_waveform_row(self, row: int, name: str,
                          x: np.ndarray, y: np.ndarray,
                          color: str, fill_rgba: tuple,
                          left_axis_width: int,
                          events: list = None,
                          cond_results=None) -> None:
        """添加一行波形子图（与 Strategy Condition Engine 一致的样式）"""
        plot = self._glw.addPlot(row=row, col=0)
        plot.showGrid(x=False, y=False)
        plot.setYRange(-0.15, 1.25, padding=0)
        plot.setMouseEnabled(x=True, y=False)
        plot.hideButtons()
        plot.setContentsMargins(0, 0, 0, 0)
        plot.getViewBox().setDefaultPadding(0)

        # 左轴显示条件名
        left_axis = plot.getAxis("left")
        left_axis.setTicks([[(0.5, name)]])
        left_axis.setTextPen(color)
        left_axis.setWidth(left_axis_width)
        left_axis.setStyle(showValues=True)

        # X轴默认隐藏
        bottom_axis = plot.getAxis("bottom")
        bottom_axis.setTextPen(_MUT)
        bottom_axis.setHeight(0)
        bottom_axis.hide()

        # 画阶梯波形
        x_step, y_step = self._make_step_data(x, y)
        plot.plot(x_step, y_step,
                  pen=pg.mkPen(color, width=2.5),
                  fillLevel=0,
                  fillBrush=pg.mkBrush(*fill_rgba))

        # 画 0.5 参考线（虚线）
        plot.addLine(y=0.5, pen=pg.mkPen(_MUT, width=0.5,
                     style=Qt.PenStyle.DotLine))

        # 添加竖线（用于十字线同步）
        vline = pg.InfiniteLine(angle=90, pen=pg.mkPen(_MUT, width=1,
                                style=Qt.PenStyle.DashLine))
        vline.setVisible(False)
        plot.addItem(vline, ignoreBounds=True)
        self._vlines.append(vline)

        # X轴联动（波形子图之间互相联动）
        if self._plots:
            plot.setXLink(self._plots[0])

        self._plots.append(plot)

    @staticmethod
    def _make_step_data(x: np.ndarray, y: np.ndarray):
        """将 0/1 序列转为阶梯波形坐标"""
        n = len(y)
        x_out = np.empty(2 * n)
        y_out = np.empty(2 * n)
        x_out[0::2] = x - 0.4
        x_out[1::2] = x + 0.4
        y_out[0::2] = y
        y_out[1::2] = y
        return x_out, y_out


class BehaviorMonitorTab(QWidget):
    """
    K-Line Behavior Lab 条件监控 Tab。
    使用与 Strategy Condition Engine 完全一致的 K线图 + 波形图显示效果。
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._monitor_data: Dict[str, Dict] = {}
        self._current_symbol: str = ""
        self._condition_names: List[str] = []
        self._synced: bool = False
        self._init_ui()

    def _init_ui(self):
        self.setStyleSheet(f"background:{_BG};color:{_FG};")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # ── 顶部工具栏 ──
        toolbar = QWidget()
        toolbar.setFixedHeight(42)
        toolbar.setStyleSheet(
            f"background:{_PANEL};border-bottom:1px solid {_BORD};")
        tl = QHBoxLayout(toolbar)
        tl.setContentsMargins(14, 0, 14, 0)
        tl.setSpacing(10)
        tl.addWidget(_lbl("🔍 条件监控  Monitor", _YLW, 14, True))
        tl.addStretch()
        tl.addWidget(_lbl("标的:", _MUT, 12))
        self._symbol_combo = QComboBox()
        self._symbol_combo.setStyleSheet(_COMBO_SS)
        self._symbol_combo.setMinimumWidth(160)
        self._symbol_combo.currentTextChanged.connect(self._on_symbol_changed)
        tl.addWidget(self._symbol_combo)
        self._refresh_btn = _btn("刷新", _TEAL)
        self._refresh_btn.clicked.connect(self._on_refresh)
        tl.addWidget(self._refresh_btn)
        layout.addWidget(toolbar)

        # ── 主体：上下分栏（K线图 + 波形图） ──
        if HAS_PYQTGRAPH:
            splitter = QSplitter(Qt.Vertical)
            splitter.setHandleWidth(5)
            splitter.setStyleSheet(
                "QSplitter::handle { background: #45475a; }"
                "QSplitter::handle:hover { background: #89b4fa; }")

            # 上方：完整 K 线图（复用 Strategy Condition Engine 的 KlineChartWidget）
            self._kline_widget = self._build_kline_area()
            splitter.addWidget(self._kline_widget)

            # 下方：条件波形图（与 Strategy Condition Engine 一致的风格）
            self._waveform_view = BehaviorWaveformView()
            splitter.addWidget(self._waveform_view)

            # 高度比例 6:4
            splitter.setStretchFactor(0, 6)
            splitter.setStretchFactor(1, 4)
            splitter.setSizes([450, 300])
            self._splitter = splitter
            layout.addWidget(splitter, 1)
        else:
            layout.addWidget(_lbl("需要安装 pyqtgraph 才能显示条件监控波形图", _RED, 14))
            layout.addStretch()

        # ── 底部：图例栏 + 统计区 ──
        bottom_w = QWidget()
        bottom_layout = QVBoxLayout(bottom_w)
        bottom_layout.setContentsMargins(0, 0, 0, 0)
        bottom_layout.setSpacing(0)

        # 图例栏（与 Strategy Condition Engine 一致）
        legend = QWidget()
        legend.setFixedHeight(28)
        legend.setStyleSheet(
            f"background:{_PANEL};border-top:1px solid {_BORD};")
        ll = QHBoxLayout(legend)
        ll.setContentsMargins(14, 0, 14, 0)
        ll.setSpacing(18)
        ll.addWidget(_lbl("▲ 买入信号", _GRN, 13))
        ll.addWidget(_lbl("▼ 卖出信号", _RED, 13))
        ll.addWidget(_lbl("■ 阳线（涨）", "#ff5555", 13))
        ll.addWidget(_lbl("■ 阴线（跌）", "#00e676", 13))
        ll.addWidget(_lbl("— MA5", _YLW, 13))
        ll.addWidget(_lbl("— MA20", _BLU, 13))
        ll.addWidget(_lbl("— MA60", _MAV, 13))
        ll.addStretch()
        self._trig_count_lbl = _lbl("", _MUT, 13)
        ll.addWidget(self._trig_count_lbl)
        bottom_layout.addWidget(legend)

        # 统计区
        self._stats_widget = self._build_stats_area()
        bottom_layout.addWidget(self._stats_widget)
        layout.addWidget(bottom_w)

    def _build_kline_area(self) -> QWidget:
        """构建完整 K 线图区域（蜡烛图 + MA + 成交量 + 十字线）"""
        w = QWidget()
        v = QVBoxLayout(w)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(0)

        # 信息栏（悬停显示 OHLCV）
        self._info_bar = QLabel("  — 移动鼠标查看K线数据 —")
        self._info_bar.setMinimumHeight(24)
        self._info_bar.setStyleSheet(
            f"color:{_MUT};font-size:13px;background:{_PANEL};"
            f"padding:2px 10px;border-bottom:1px solid {_BORD};")
        v.addWidget(self._info_bar)

        # K线主图 + 成交量副图（QSplitter 可拖拽）
        chart_splitter = QSplitter(Qt.Vertical)
        chart_splitter.setHandleWidth(5)
        chart_splitter.setStyleSheet(
            "QSplitter::handle { background: #45475a; }"
            "QSplitter::handle:hover { background: #89b4fa; }")

        self._glw_main = pg.GraphicsLayoutWidget()
        self._glw_main.setBackground(_BG)
        self._main_plot = self._glw_main.addPlot(row=0, col=0)
        self._main_plot.showGrid(x=True, y=True, alpha=0.15)
        self._main_plot.getAxis("left").setTextPen(_MUT)
        self._main_plot.getAxis("bottom").setTextPen(_MUT)

        self._glw_vol = pg.GraphicsLayoutWidget()
        self._glw_vol.setBackground(_BG)
        self._vol_plot = self._glw_vol.addPlot(row=0, col=0)
        self._vol_plot.showGrid(x=True, y=True, alpha=0.10)
        self._vol_plot.getAxis("left").setTextPen(_MUT)
        self._vol_plot.getAxis("bottom").setTextPen(_MUT)
        self._vol_plot.setXLink(self._main_plot)

        chart_splitter.addWidget(self._glw_main)
        chart_splitter.addWidget(self._glw_vol)
        chart_splitter.setStretchFactor(0, 7)
        chart_splitter.setStretchFactor(1, 3)

        # 十字线
        self._vline = pg.InfiniteLine(angle=90, pen=pg.mkPen(_MUT, width=1,
                       style=Qt.PenStyle.DashLine))
        self._hline = pg.InfiniteLine(angle=0, pen=pg.mkPen(_MUT, width=1,
                       style=Qt.PenStyle.DashLine))
        self._main_plot.addItem(self._vline, ignoreBounds=True)
        self._main_plot.addItem(self._hline, ignoreBounds=True)

        # 鼠标移动信号
        self._proxy = pg.SignalProxy(
            self._main_plot.scene().sigMouseMoved,
            rateLimit=60, slot=self._on_mouse_moved)

        # Y轴自适应
        self._main_plot.sigXRangeChanged.connect(self._on_x_range_changed)

        v.addWidget(chart_splitter, 1)
        self._chart_splitter = chart_splitter
        return w

    def _build_stats_area(self) -> QWidget:
        """构建统计概览区域"""
        w = QWidget()
        w.setStyleSheet(f"background:{_PANEL};border-top:1px solid {_BORD};")
        w.setMaximumHeight(140)
        v = QVBoxLayout(w)
        v.setContentsMargins(10, 6, 10, 6)
        v.setSpacing(4)
        v.addWidget(_lbl("📈 条件满足率统计", _YLW, 12, True))

        self._stats_table = QTableWidget(0, 5)
        self._stats_table.setHorizontalHeaderLabels(
            ["条件名", "满足次数", "总K线数", "满足率", "最近满足"])
        self._stats_table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.Stretch)
        for i in range(1, 5):
            self._stats_table.horizontalHeader().setSectionResizeMode(
                i, QHeaderView.ResizeMode.ResizeToContents)
        self._stats_table.setStyleSheet(
            f"QTableWidget{{background:{_PAN2};color:{_FG};border:1px solid {_BORD};"
            f"gridline-color:{_BORD};font-size:12px;}}"
            f"QTableWidget::item:selected{{background:{_BLU};color:#1e1e2e;}}"
            f"QHeaderView::section{{background:{_PANEL};color:{_FG};"
            f"border:1px solid {_BORD};padding:3px;font-size:11px;}}")
        self._stats_table.verticalHeader().setVisible(False)
        v.addWidget(self._stats_table, 1)
        return w

    # ══════════════ 公开接口 ══════════════

    def set_monitor_data(self, data: Dict[str, Dict]):
        """
        设置监控数据（由主界面研究完成后调用）。

        Args:
            data: {symbol: {"df": DataFrame, "events": list, "conditions": list,
                            "condition_results": DataFrame(bool)}}
        """
        self._monitor_data = data
        self._symbol_combo.blockSignals(True)
        self._symbol_combo.clear()
        symbols = sorted(data.keys())
        self._symbol_combo.addItems(symbols)
        if symbols:
            self._symbol_combo.setCurrentText(symbols[0])
        self._symbol_combo.blockSignals(False)
        # 主动渲染当前选中标的（确保数据更新后立即刷新显示）
        if symbols:
            self._current_symbol = symbols[0]
            self._render_monitor(symbols[0])

    # ══════════════ 交互逻辑 ══════════════

    def set_refresh_callback(self, callback):
        """设置刷新回调函数，用于重新计算单个标的的数据"""
        self._refresh_callback = callback

    def _on_symbol_changed(self, symbol: str):
        """标的切换时重新渲染"""
        if not symbol:
            return
        self._current_symbol = symbol
        if symbol in self._monitor_data:
            self._render_monitor(symbol)

    def _on_refresh(self):
        """刷新当前标的 - 如果缓存中没有则通过回调重新计算"""
        symbol = self._symbol_combo.currentText().strip()
        if not symbol:
            return
        self._current_symbol = symbol

        # 如果有回调，先调用回调重新计算该标的的数据
        if hasattr(self, '_refresh_callback') and self._refresh_callback:
            self._refresh_callback(symbol)

        # 渲染（回调会更新 _monitor_data）
        if symbol in self._monitor_data:
            self._render_monitor(symbol)

    def _render_monitor(self, symbol: str):
        """渲染指定标的的监控数据"""
        if not HAS_PYQTGRAPH:
            return

        data = self._monitor_data.get(symbol)
        if not data:
            return

        df = data.get("df")
        conditions = data.get("conditions", [])
        cond_results = data.get("condition_results")
        events = data.get("events", [])

        if df is None or df.empty:
            return

        self._condition_names = conditions

        # ── 渲染 K 线图（完整蜡烛图） ──
        self._render_kline(df, events)

        # ── 渲染条件波形 ──
        self._waveform_view.load_data(conditions, cond_results, events)

        # ── 建立三区同步 ──
        self._setup_sync()

        # ── 更新统计表 ──
        self._render_stats(conditions, cond_results, df)

        # ── 更新信号计数 ──
        n_events = len(events) if events else 0
        self._trig_count_lbl.setText(
            f"触发 {n_events}" if n_events > 0 else "")

    def _render_kline(self, df, events):
        """渲染完整蜡烛图（与 Strategy Condition Engine 一致的效果）"""
        self._main_plot.clear()
        self._vol_plot.clear()

        # 从 DataFrame 提取 OHLCV
        n = len(df)
        if "open" not in df.columns:
            return

        opens = df["open"].values
        highs = df["high"].values
        lows = df["low"].values
        closes = df["close"].values
        volumes = df["volume"].values if "volume" in df.columns else np.zeros(n)

        self._bars_data = list(zip(opens, highs, lows, closes))
        self._volumes_data = list(volumes.astype(float))
        self._closes_data = list(closes.astype(float))

        # 日期处理
        if hasattr(df.index, 'strftime'):
            self._dates = [d.strftime("%Y-%m-%d") for d in df.index]
            self._datetimes = list(df.index)
        else:
            self._dates = [str(d)[:10] for d in df.index]
            self._datetimes = []

        # X 轴日期
        ax = DateAxis(self._dates, datetimes=self._datetimes, orientation="bottom")
        ax.setTextPen(_MUT)
        self._main_plot.setAxisItems({"bottom": ax})
        ax_v = DateAxis(self._dates, datetimes=self._datetimes, orientation="bottom")
        ax_v.setTextPen(_MUT)
        self._vol_plot.setAxisItems({"bottom": ax_v})

        # 蜡烛图
        candles = CandlestickItem(self._bars_data)
        self._main_plot.addItem(candles)

        # MA 均线
        closes_arr = np.array(closes, dtype=np.float64)
        ma_config = [(5, _YLW), (20, _BLU), (60, _MAV)]
        for period, color in ma_config:
            if n >= period:
                cumsum = np.cumsum(closes_arr)
                ma = np.empty(n, dtype=np.float64)
                ma[:period] = cumsum[:period] / np.arange(1, period + 1)
                ma[period:] = (cumsum[period:] - cumsum[:-period]) / period
                self._main_plot.plot(
                    np.arange(n), ma,
                    pen=pg.mkPen(color, width=1),
                    name=f'MA{period}')

        # 信号标记（事件触发点）
        if events:
            buy_indices = []
            dates_index = df.index
            for evt in events:
                evt_date = str(evt.get("date", ""))[:10]
                if hasattr(dates_index, 'strftime'):
                    for i, dt in enumerate(dates_index):
                        if dt.strftime("%Y-%m-%d") == evt_date:
                            buy_indices.append(i)
                            break
                else:
                    for i, dt in enumerate(dates_index):
                        if str(dt)[:10] == evt_date:
                            buy_indices.append(i)
                            break

            # 触发点高亮背景带
            for ti in buy_indices:
                if 0 <= ti < n:
                    band = pg.LinearRegionItem(
                        values=[ti - 0.45, ti + 0.45],
                        orientation='vertical',
                        brush=pg.mkBrush(166, 227, 161, 50),
                        pen=pg.mkPen(None),
                        movable=False,
                    )
                    self._main_plot.addItem(band)

            # 绿色 ▲ 三角标记
            if buy_indices:
                valid_ix = [i for i in buy_indices if 0 <= i < n]
                buy_y = [lows[i] * 0.97 for i in valid_ix]
                scatter_buy = pg.ScatterPlotItem(
                    x=valid_ix, y=buy_y, symbol="t1", size=16,
                    pen=pg.mkPen(_GRN, width=2),
                    brush=pg.mkBrush(_GRN))
                self._main_plot.addItem(scatter_buy)

        # 成交量图
        vol_item = VolumeItem(self._volumes_data, self._closes_data)
        self._vol_plot.addItem(vol_item)

        # 成交量Y轴：P95百分位截断
        vis_vols = self._volumes_data[max(0, n - 120):n]
        if vis_vols:
            vols_pos = [v for v in vis_vols if v > 0]
            if vols_pos:
                vols_arr = np.array(vols_pos)
                vol_p95 = float(np.percentile(vols_arr, 95))
                vol_max = float(vols_arr.max())
                vol_ceiling = max(vol_p95, vol_max * 0.6)
                self._vol_plot.setYRange(0, vol_ceiling * 1.05, padding=0)
        self._vol_plot.setMouseEnabled(x=True, y=False)
        self._vol_plot.enableAutoRange(axis='y', enable=False)

        # 重新添加十字线
        self._vline = pg.InfiniteLine(angle=90, pen=pg.mkPen(_MUT, width=1,
                       style=Qt.PenStyle.DashLine))
        self._hline = pg.InfiniteLine(angle=0, pen=pg.mkPen(_MUT, width=1,
                       style=Qt.PenStyle.DashLine))
        self._main_plot.addItem(self._vline, ignoreBounds=True)
        self._main_plot.addItem(self._hline, ignoreBounds=True)

        # 默认显示最后 120 根
        self._main_plot.setXRange(max(0, n - 120), n, padding=0.02)

        # Y轴根据可见区间设置
        vis_start = max(0, n - 120)
        vis_bars = self._bars_data[vis_start:n]
        if vis_bars:
            price_lo = min(b[2] for b in vis_bars)
            price_hi = max(b[1] for b in vis_bars)
            margin = (price_hi - price_lo) * 0.08 or price_hi * 0.05
            self._main_plot.setYRange(price_lo - margin, price_hi + margin, padding=0)
        self._main_plot.setMouseEnabled(x=True, y=True)
        self._main_plot.enableAutoRange(axis="y", enable=False)

    # ══════════════ 三区同步 ══════════════

    def _setup_sync(self) -> None:
        """建立 K线区、成交量区、波形区 X轴联动 + 十字竖线贯穿。"""
        waveform_plots = self._waveform_view.get_plots()
        for wp in waveform_plots:
            wp.setXLink(self._main_plot)

        # 替换鼠标移动代理，增加波形竖线同步
        try:
            self._proxy.disconnect()
        except Exception:
            pass

        def _on_mouse_synced(evt):
            pos = evt[0]
            if self._main_plot.sceneBoundingRect().contains(pos):
                mp = self._main_plot.vb.mapSceneToView(pos)
                x = mp.x()
                self._vline.setPos(x)
                self._hline.setPos(mp.y())
                self._waveform_view.set_vline_pos(x)
                self._on_mouse_moved(evt)
            else:
                self._waveform_view.hide_vlines()

        self._proxy = pg.SignalProxy(
            self._main_plot.scene().sigMouseMoved,
            rateLimit=60, slot=_on_mouse_synced)

        # 波形区鼠标移动反向同步到K线
        for wp in waveform_plots:
            scene = wp.scene()
            if scene:
                def _make_handler(wave_plot):
                    def _handler(evt):
                        pos = evt[0]
                        if wave_plot.sceneBoundingRect().contains(pos):
                            mp = wave_plot.vb.mapSceneToView(pos)
                            x = mp.x()
                            self._vline.setPos(x)
                            self._vline.setVisible(True)
                            self._waveform_view.set_vline_pos(x)
                    return _handler
                pg.SignalProxy(scene.sigMouseMoved, rateLimit=60,
                               slot=_make_handler(wp))

        self._synced = True

    # ══════════════ 鼠标悬停信息 ══════════════

    def _on_mouse_moved(self, evt) -> None:
        """鼠标移动时更新信息栏（OHLCV + 涨幅）"""
        pos = evt[0]
        if not self._main_plot.sceneBoundingRect().contains(pos):
            return
        mp = self._main_plot.vb.mapSceneToView(pos)
        x = int(round(mp.x()))
        self._vline.setPos(mp.x())
        self._hline.setPos(mp.y())
        if not hasattr(self, '_bars_data') or not (0 <= x < len(self._bars_data)):
            return
        o, h, l, c = self._bars_data[x]
        vol = self._volumes_data[x] if x < len(self._volumes_data) else 0
        chg = ((c - self._bars_data[x-1][3]) / self._bars_data[x-1][3] * 100
               if x > 0 else 0.0)
        cs = f"+{chg:.2f}%" if chg >= 0 else f"{chg:.2f}%"
        cc = "#ff5555" if chg >= 0 else "#00e676"

        dt_str = ""
        if hasattr(self, '_datetimes') and self._datetimes and x < len(self._datetimes):
            dt = self._datetimes[x]
            if hasattr(dt, 'strftime'):
                dt_str = dt.strftime("%Y-%m-%d")

        self._info_bar.setText(
            f"  {dt_str}　"
            f"开 <b style='color:{_FG}'>{o:.2f}</b>　"
            f"高 <b style='color:#ff5555'>{h:.2f}</b>　"
            f"低 <b style='color:#00e676'>{l:.2f}</b>　"
            f"收 <b style='color:{_FG}'>{c:.2f}</b>　"
            f"涨幅 <b style='color:{cc}'>{cs}</b>　"
            f"量 <span style='color:{_MUT}'>{vol/1e4:.0f}万</span>")
        self._info_bar.setTextFormat(Qt.TextFormat.RichText)

    def _on_x_range_changed(self, *_args) -> None:
        """X轴范围变化时动态更新Y轴范围"""
        if not hasattr(self, '_bars_data') or not self._bars_data:
            return
        n = len(self._bars_data)
        xmin, xmax = self._main_plot.viewRange()[0]
        i_start = max(0, int(xmin))
        i_end = min(n, int(xmax) + 1)
        if i_start >= i_end:
            return

        vis_bars = self._bars_data[i_start:i_end]
        if vis_bars:
            price_lo = min(b[2] for b in vis_bars)
            price_hi = max(b[1] for b in vis_bars)
            price_range = price_hi - price_lo
            if price_range <= 0:
                price_range = price_hi * 0.1 or 1.0
            padding = price_range * 0.05
            self._main_plot.setYRange(price_lo - padding, price_hi + padding, padding=0)

        # 成交量Y轴
        vis_vols = self._volumes_data[i_start:i_end]
        if vis_vols:
            vols_arr = np.array([v for v in vis_vols if v > 0])
            if len(vols_arr) > 0:
                vol_p95 = float(np.percentile(vols_arr, 95))
                vol_max = float(vols_arr.max())
                vol_ceiling = max(vol_p95, vol_max * 0.6)
                self._vol_plot.setYRange(0, vol_ceiling * 1.05, padding=0)

    # ══════════════ 统计表渲染 ══════════════

    def _render_stats(self, conditions: List[str], cond_results, df):
        """渲染条件满足率统计表"""
        self._stats_table.setRowCount(0)
        if cond_results is None or cond_results.empty:
            return

        n = len(cond_results)
        for cond_name in conditions:
            if cond_name not in cond_results.columns:
                continue
            col = cond_results[cond_name]
            pass_count = int(col.sum())
            rate = pass_count / n * 100 if n > 0 else 0

            # 最近满足日期
            last_pass = ""
            if pass_count > 0:
                last_idx = col[col].index[-1]
                if hasattr(last_idx, 'strftime'):
                    last_pass = last_idx.strftime("%Y-%m-%d")
                else:
                    last_pass = str(last_idx)[:10]

            row = self._stats_table.rowCount()
            self._stats_table.insertRow(row)
            self._stats_table.setItem(row, 0, QTableWidgetItem(cond_name))
            self._stats_table.setItem(row, 1, QTableWidgetItem(str(pass_count)))
            self._stats_table.setItem(row, 2, QTableWidgetItem(str(n)))
            self._stats_table.setItem(row, 3, QTableWidgetItem(f"{rate:.1f}%"))
            self._stats_table.setItem(row, 4, QTableWidgetItem(last_pass))
