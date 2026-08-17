"""image.png
market_behavior/ui/kline_view.py  —  K线图 Tab
"""
from __future__ import annotations
from typing import List, TYPE_CHECKING

import pyqtgraph as pg
from pyqtgraph import GraphicsObject

from vnpy.trader.ui import QtWidgets, QtCore, QtGui
from .measure_tool import MeasureTool
from vnpy.trader.constant import Interval

if TYPE_CHECKING:
    from vnpy.trader.object import BarData

_BG   = "#1e1e2e"
_PANEL= "#181825"
_PAN2 = "#11111b"
_BORD = "#45475a"
_FG   = "#cdd6f4"
_MUT  = "#6c7086"
_BLU  = "#89b4fa"
_GRN  = "#a6e3a1"
_YLW  = "#f9e2af"
_RED  = "#f38ba8"
_MAV  = "#cba6f7"

_C_UP = "#ff5555"
_C_DN = "#00e676"


def _lbl(text, color=_FG, size=14, bold=False):
    w = QtWidgets.QLabel(text)
    w.setStyleSheet(
        f"color:{color};font-size:{size}px;"
        f"font-weight:{'bold' if bold else 'normal'};"
        f"background:transparent;border:none;")
    return w


# ── 自定义图元 ───────────────────────────────────────────────────────

# Neutral gray for flat price (close == open) - between red and green
_C_FLAT = "#9399b2"

class CandlestickItem(GraphicsObject):
    """
    高性能 K 线图元：使用 QPainterPath 批量绘制，
    将同色 K 线聚合到一个 path 中（2-3 次 drawPath 替代 N×4 次独立调用）。
    10000 根 K 线绘制时间从 ~2s 降低到 ~0.1s。
    """
    def __init__(self, bars: list):
        super().__init__()
        self._bars = bars
        self._pic  = QtGui.QPicture()
        self._draw()

    def _draw(self) -> None:
        p = QtGui.QPainter(self._pic)
        w = 0.35

        # 按颜色分组收集路径（减少 QPainter 状态切换）
        up_wick_path   = QtGui.QPainterPath()  # 阳线影线
        up_body_path   = QtGui.QPainterPath()  # 阳线实体
        dn_wick_path   = QtGui.QPainterPath()  # 阴线影线
        dn_body_path   = QtGui.QPainterPath()  # 阴线实体
        flat_wick_path = QtGui.QPainterPath()  # 十字星影线
        flat_body_path = QtGui.QPainterPath()  # 十字星实体
        halt_path      = QtGui.QPainterPath()  # 停牌横线

        for i, (o, h, l, c) in enumerate(self._bars):
            if o == h == l == c:
                halt_path.moveTo(i - w, c)
                halt_path.lineTo(i + w, c)
                continue
            top = max(o, c)
            bot = min(o, c)
            body_h = max(top - bot, 0.001)
            if c > o:
                up_wick_path.moveTo(i, l)
                up_wick_path.lineTo(i, h)
                up_body_path.addRect(i - w, bot, w * 2, body_h)
            elif c < o:
                dn_wick_path.moveTo(i, l)
                dn_wick_path.lineTo(i, h)
                dn_body_path.addRect(i - w, bot, w * 2, body_h)
            else:
                flat_wick_path.moveTo(i, l)
                flat_wick_path.lineTo(i, h)
                flat_body_path.addRect(i - w, bot, w * 2, body_h)

        # 一次性绘制每种颜色（极少 QPainter 状态切换）
        up_color   = QtGui.QColor(_C_UP)
        dn_color   = QtGui.QColor(_C_DN)
        flat_color = QtGui.QColor(_C_FLAT)
        halt_color = QtGui.QColor(_BLU)

        # 阳线
        p.setPen(pg.mkPen(up_color, width=1))
        p.drawPath(up_wick_path)
        p.setBrush(pg.mkBrush(up_color))
        p.drawPath(up_body_path)

        # 阴线
        p.setPen(pg.mkPen(dn_color, width=1))
        p.drawPath(dn_wick_path)
        p.setBrush(pg.mkBrush(dn_color))
        p.drawPath(dn_body_path)

        # 十字星
        p.setPen(pg.mkPen(flat_color, width=1))
        p.drawPath(flat_wick_path)
        p.setBrush(pg.mkBrush(flat_color))
        p.drawPath(flat_body_path)

        # 停牌
        if not halt_path.isEmpty():
            p.setPen(pg.mkPen(halt_color, width=2))
            p.setBrush(QtCore.Qt.BrushStyle.NoBrush)
            p.drawPath(halt_path)

        p.end()

    def paint(self, p, *_): p.drawPicture(0, 0, self._pic)
    def boundingRect(self): return QtCore.QRectF(self._pic.boundingRect())


class VolumeItem(GraphicsObject):
    """高性能成交量图元：QPainterPath 批量绘制。"""
    def __init__(self, volumes: list, closes: list):
        super().__init__()
        self._vols   = volumes
        self._closes = closes
        self._pic    = QtGui.QPicture()
        self._draw()

    def _draw(self) -> None:
        p = QtGui.QPainter(self._pic)
        w = 0.35

        up_path   = QtGui.QPainterPath()
        dn_path   = QtGui.QPainterPath()
        flat_path = QtGui.QPainterPath()

        for i, vol in enumerate(self._vols):
            if vol <= 0:
                continue
            if i == 0:
                up = True
            else:
                if self._closes[i] > self._closes[i - 1]:
                    up = True
                elif self._closes[i] < self._closes[i - 1]:
                    up = False
                else:
                    up = None
            if up is True:
                up_path.addRect(i - w, 0, w * 2, vol)
            elif up is False:
                dn_path.addRect(i - w, 0, w * 2, vol)
            else:
                flat_path.addRect(i - w, 0, w * 2, vol)

        # 批量绘制
        p.setPen(pg.mkPen(QtGui.QColor(_C_UP), width=1))
        p.setBrush(pg.mkBrush(QtGui.QColor(_C_UP)))
        p.drawPath(up_path)

        p.setPen(pg.mkPen(QtGui.QColor(_C_DN), width=1))
        p.setBrush(pg.mkBrush(QtGui.QColor(_C_DN)))
        p.drawPath(dn_path)

        if not flat_path.isEmpty():
            p.setPen(pg.mkPen(QtGui.QColor(_C_FLAT), width=1))
            p.setBrush(pg.mkBrush(QtGui.QColor(_C_FLAT)))
            p.drawPath(flat_path)

        p.end()

    def paint(self, p, *_): p.drawPicture(0, 0, self._pic)
    def boundingRect(self): return QtCore.QRectF(self._pic.boundingRect())


class DateAxis(pg.AxisItem):
    def __init__(self, dates: list, datetimes: list = None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._dates = dates
        self._datetimes = datetimes or []
        # 判断是否为分钟线：存在相邻日期相同的情况
        self._is_intraday = False
        if len(dates) > 1:
            self._is_intraday = any(
                dates[i] == dates[i+1] for i in range(min(10, len(dates)-1)))

    def tickStrings(self, values, scale, spacing):
        out = []
        for v in values:
            i = int(v)
            if not (0 <= i < len(self._dates)):
                out.append("")
                continue
            if self._is_intraday and self._datetimes:
                dt = self._datetimes[i]
                # 每天第一根显示日期+时间，其余只显示时间
                if i == 0 or self._dates[i] != self._dates[i-1]:
                    out.append(dt.strftime("%m-%d\n%H:%M"))
                else:
                    out.append(dt.strftime("%H:%M"))
            else:
                out.append(self._dates[i])
        return out


# ── 主图表组件 ───────────────────────────────────────────────────────

class KlineChartWidget(QtWidgets.QWidget):
    """K线主图 + 成交量副图 + 买入/卖出信号标记 + 十字线悬停。"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._bars:         list = []
        self._dates:        list = []
        self._volumes:      list = []
        self._buy_triggers: set  = set()
        self._sell_triggers: set = set()
        self._ma_flags:     dict = {5: True, 20: True, 60: True}
        self._show_triggers: bool = True
        self._show_candles:  bool = True

        self._build_ui()

    def _build_ui(self) -> None:
        pg.setConfigOptions(antialias=False, background=_BG, foreground=_FG)
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self._info_bar = QtWidgets.QLabel("  — 移动鼠标查看K线数据 —")
        self._info_bar.setMinimumHeight(22)
        self._info_bar.setStyleSheet(
            f"color:{_MUT};font-size:12px;background:{_PANEL};"
            f"padding:2px 8px;border-bottom:1px solid {_BORD};")
        layout.addWidget(self._info_bar)

        # 使用 QSplitter 使 K线区和成交量区高度可拖拽调整
        splitter = QtWidgets.QSplitter(QtCore.Qt.Orientation.Vertical)
        splitter.setHandleWidth(5)
        splitter.setStyleSheet(
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

        splitter.addWidget(self._glw_main)
        splitter.addWidget(self._glw_vol)
        splitter.setStretchFactor(0, 7)
        splitter.setStretchFactor(1, 3)
        self._splitter = splitter
        layout.addWidget(splitter, 1)

        self._vline = pg.InfiniteLine(angle=90, pen=pg.mkPen(_MUT, width=1,
                       style=QtCore.Qt.PenStyle.DashLine))
        self._hline = pg.InfiniteLine(angle=0,  pen=pg.mkPen(_MUT, width=1,
                       style=QtCore.Qt.PenStyle.DashLine))
        self._main_plot.addItem(self._vline, ignoreBounds=True)
        self._main_plot.addItem(self._hline, ignoreBounds=True)

        self._proxy = pg.SignalProxy(
            self._main_plot.scene().sigMouseMoved,
            rateLimit=60, slot=self._on_mouse_moved)

        # Connect mouse click for measure tool



        # -- Dynamic Y-axis: auto-update when user scrolls/zooms X axis --
        self._main_plot.sigXRangeChanged.connect(self._on_x_range_changed)

    def set_volume_visible(self, visible: bool) -> None:
        """显示或隐藏成交量区域"""
        self._glw_vol.setVisible(visible)

    def set_ma_flags(self, flags: list, show_triggers: bool = True,
                     show_candles: bool = True) -> None:
        self._ma_flags      = flags
        self._show_triggers = show_triggers
        self._show_candles  = show_candles

    def load(self, bars: list, buy_indices: list = None,
             sell_indices: list = None) -> None:
        """
        加载 K 线数据和信号触发点。
        buy_indices:  买入信号触发的 bar 索引列表
        sell_indices: 卖出信号触发的 bar 索引列表
        """
        self._bars     = [(b.open_price, b.high_price, b.low_price, b.close_price)
                          for b in bars]
        self._dates    = [b.datetime.strftime("%Y-%m-%d") for b in bars]
        self._datetimes = [b.datetime for b in bars]
        self._volumes  = [float(b.volume) for b in bars]
        self._buy_triggers  = set(buy_indices or [])
        self._sell_triggers = set(sell_indices or [])
        self._redraw()

    def clear(self) -> None:
        self._bars = []; self._dates = []; self._volumes = []
        self._buy_triggers = set(); self._sell_triggers = set()
        self._main_plot.clear()
        self._vol_plot.clear()

    def _redraw(self) -> None:
        self._main_plot.clear()
        self._vol_plot.clear()
        if not self._bars:
            return

        import numpy as np
        n      = len(self._bars)
        closes = [b[3] for b in self._bars]

        # 更新 X 轴日期（传入 datetimes 支持分钟线智能显示）
        ax = DateAxis(self._dates, datetimes=self._datetimes, orientation="bottom")
        ax.setTextPen(_MUT)
        self._main_plot.setAxisItems({"bottom": ax})
        ax_v = DateAxis(self._dates, datetimes=self._datetimes, orientation="bottom")
        ax_v.setTextPen(_MUT)
        self._vol_plot.setAxisItems({"bottom": ax_v})

        # 日期分隔线（分钟线时，不同日期之间画竖线）
        if len(self._dates) > 1:
            has_same_date = any(self._dates[i] == self._dates[i+1]
                                for i in range(min(10, len(self._dates)-1)))
            if has_same_date:  # 说明是分钟线
                prev_date = self._dates[0]
                for i in range(1, n):
                    cur_date = self._dates[i]
                    if cur_date != prev_date:
                        vline = pg.InfiniteLine(
                            pos=i - 0.5, angle=90,
                            pen=pg.mkPen("#f9e2af", width=1,
                                         style=QtCore.Qt.PenStyle.DashLine))
                        self._main_plot.addItem(vline)
                    prev_date = cur_date

        # K线（可隐藏）
        if self._show_candles:
            candles = CandlestickItem(self._bars)
            self._main_plot.addItem(candles)

        # MA 均线（numpy cumsum O(n) 一次性计算，替代 O(n×period) 循环）
        closes_arr = np.array(closes, dtype=np.float64)
        for period, color, enabled in self._ma_flags:
            if enabled and n >= period:
                # cumsum 滑动窗口法 O(n)
                cumsum = np.cumsum(closes_arr)
                ma = np.empty(n, dtype=np.float64)
                ma[:period] = cumsum[:period] / np.arange(1, period + 1)
                ma[period:] = (cumsum[period:] - cumsum[:-period]) / period
                self._main_plot.plot(
                    np.arange(n), ma,
                    pen=pg.mkPen(color, width=1),
                    name=f'MA{period}')

        # 信号标记
        if self._show_triggers:
            all_triggers = self._buy_triggers | self._sell_triggers

            # 触发点高亮背景带（半透明竖向填充）
            tx_sorted = sorted(i for i in all_triggers if 0 <= i < n)
            for ti in tx_sorted:
                is_buy = ti in self._buy_triggers
                brush_color = (166, 227, 161, 50) if is_buy else (243, 139, 168, 50)
                band = pg.LinearRegionItem(
                    values=[ti - 0.45, ti + 0.45],
                    orientation='vertical',
                    brush=pg.mkBrush(*brush_color),
                    pen=pg.mkPen(None),
                    movable=False,
                )
                self._main_plot.addItem(band)

            # 买入信号：绿色 ▲ 向上三角在 K 线下方
            buy_ix = sorted(i for i in self._buy_triggers if 0 <= i < n)
            if buy_ix:
                buy_y = [self._bars[i][2] * 0.97 for i in buy_ix]  # low * 0.97
                scatter_buy = pg.ScatterPlotItem(
                    x=buy_ix, y=buy_y, symbol="t1", size=16,
                    pen=pg.mkPen(_GRN, width=2),
                    brush=pg.mkBrush(_GRN))
                self._main_plot.addItem(scatter_buy)

            # 卖出信号：红色 ▼ 向下三角在 K 线上方
            sell_ix = sorted(i for i in self._sell_triggers if 0 <= i < n)
            if sell_ix:
                sell_y = [self._bars[i][1] * 1.03 for i in sell_ix]  # high * 1.03
                scatter_sell = pg.ScatterPlotItem(
                    x=sell_ix, y=sell_y, symbol="t", size=16,
                    pen=pg.mkPen(_RED, width=2),
                    brush=pg.mkBrush(_RED))
                self._main_plot.addItem(scatter_sell)

        # 成交量
        vol_item = VolumeItem(self._volumes, closes)
        self._vol_plot.addItem(vol_item)

        # 成交量Y轴：P95百分位截断 + 5% padding
        vis_vols = self._volumes[max(0, n - 120):n]
        if vis_vols:
            vols_pos = [v for v in vis_vols if v > 0]
            if vols_pos:
                import numpy as np
                vols_arr = np.array(vols_pos)
                vol_p95 = float(np.percentile(vols_arr, 95))
                vol_max = float(vols_arr.max())
                vol_ceiling = max(vol_p95, vol_max * 0.6)
                vol_padding = vol_ceiling * 0.05
                self._vol_plot.setYRange(0, vol_ceiling + vol_padding, padding=0)
        self._vol_plot.setMouseEnabled(x=True, y=False)
        self._vol_plot.enableAutoRange(axis='y', enable=False)

        # 重新添加十字线
        self._vline = pg.InfiniteLine(angle=90, pen=pg.mkPen(_MUT, width=1,
                       style=QtCore.Qt.PenStyle.DashLine))
        self._hline = pg.InfiniteLine(angle=0,  pen=pg.mkPen(_MUT, width=1,
                       style=QtCore.Qt.PenStyle.DashLine))
        self._main_plot.addItem(self._vline, ignoreBounds=True)
        self._main_plot.addItem(self._hline, ignoreBounds=True)

        # 默认显示最后 120 根
        self._main_plot.setXRange(max(0, n - 120), n, padding=0.02)

        # 根据可见区间内的价格设置 Y 轴
        vis_start = max(0, n - 120)
        vis_bars  = self._bars[vis_start:n]
        if vis_bars:
            price_lo = min(b[2] for b in vis_bars)
            price_hi = max(b[1] for b in vis_bars)
            margin   = (price_hi - price_lo) * 0.08 or price_hi * 0.05
            self._main_plot.setYRange(price_lo - margin, price_hi + margin, padding=0)
        self._main_plot.setMouseEnabled(x=True, y=True)
        self._main_plot.enableAutoRange(axis="y", enable=False)

    def jump_to_trigger(self, direction: int) -> None:
        """direction: +1 下一个, -1 上一个"""
        all_triggers = self._buy_triggers | self._sell_triggers
        if not all_triggers:
            return
        n = len(self._bars)
        tx = sorted(i for i in all_triggers if 0 <= i < n)
        if not tx:
            return
        xmin, xmax = self._main_plot.viewRange()[0]
        center = (xmin + xmax) / 2
        half   = max((xmax - xmin) / 2, 30)
        if direction > 0:
            candidates = [t for t in tx if t > center + 1]
            target = candidates[0] if candidates else tx[0]
        else:
            candidates = [t for t in tx if t < center - 1]
            target = candidates[-1] if candidates else tx[-1]
        lo = target - half
        hi = target + half
        self._main_plot.setXRange(lo, hi, padding=0)
        vis = self._bars[max(0, int(lo)):min(n, int(hi)+1)]
        if vis:
            plo = min(b[2] for b in vis)
            phi = max(b[1] for b in vis)
            mg  = (phi - plo) * 0.08 or phi * 0.05
            self._main_plot.setYRange(plo - mg, phi + mg, padding=0)

    def set_auto_yaxis(self, enabled: bool) -> None:
        """开启/关闭Y轴自适应模式。"""
        self._auto_yaxis = enabled
        if enabled:
            # 立即触发一次Y轴更新
            self._on_x_range_changed()
        else:
            # 关闭时恢复Y轴自由拖拽（autoRange）
            self._main_plot.enableAutoRange(axis='y', enable=True)
            self._vol_plot.enableAutoRange(axis='y', enable=True)

    def _on_x_range_changed(self, *_args) -> None:
        """X轴范围变化时动态更新Y轴范围。"""
        if not getattr(self, "_auto_yaxis", True):
            return
        if not self._bars:
            return
        n = len(self._bars)
        xmin, xmax = self._main_plot.viewRange()[0]
        i_start = max(0, int(xmin))
        i_end = min(n, int(xmax) + 1)
        if i_start >= i_end:
            return

        # K线Y轴：可见区间的 low/high + 5% padding
        vis_bars = self._bars[i_start:i_end]
        if vis_bars:
            price_lo = min(b[2] for b in vis_bars)
            price_hi = max(b[1] for b in vis_bars)
            price_range = price_hi - price_lo
            if price_range <= 0:
                price_range = price_hi * 0.1 or 1.0
            padding = price_range * 0.05
            self._main_plot.setYRange(
                price_lo - padding, price_hi + padding, padding=0)

        # 成交量Y轴：可见区间的P95百分位 + 5% padding
        vis_vols = self._volumes[i_start:i_end]
        if vis_vols:
            import numpy as np
            vols_arr = np.array([v for v in vis_vols if v > 0])
            if len(vols_arr) > 0:
                vol_p95 = float(np.percentile(vols_arr, 95))
                vol_max = float(vols_arr.max())
                vol_ceiling = max(vol_p95, vol_max * 0.6)
                vol_padding = vol_ceiling * 0.05
                self._vol_plot.setYRange(0, vol_ceiling + vol_padding, padding=0)

    def _on_mouse_moved(self, evt) -> None:
        pos = evt[0]
        if not self._main_plot.sceneBoundingRect().contains(pos):
            return
        mp = self._main_plot.vb.mapSceneToView(pos)
        x  = int(round(mp.x()))
        self._vline.setPos(mp.x())
        self._hline.setPos(mp.y())
        if not (0 <= x < len(self._bars)):
            return
        o, h, l, c = self._bars[x]
        vol  = self._volumes[x] if x < len(self._volumes) else 0
        dt = self._datetimes[x] if x < len(self._datetimes) else None
        chg  = ((c - self._bars[x-1][3]) / self._bars[x-1][3] * 100
                if x > 0 else 0.0)
        cs   = f"+{chg:.2f}%" if chg >= 0 else f"{chg:.2f}%"
        cc   = _C_UP if chg >= 0 else _C_DN

        # 格式化日期时间：日线只显示日期，分钟线显示日期+时间
        if dt is not None:
            if dt.hour == 0 and dt.minute == 0:
                datetime_str = dt.strftime("%Y-%m-%d")
            else:
                datetime_str = dt.strftime("%Y-%m-%d %H:%M")
        else:
            datetime_str = ""

        # 信号标记
        mark = ""
        if x in self._buy_triggers and x in self._sell_triggers:
            mark = f"  <b style='color:{_GRN}'>▲ 买入</b> + <b style='color:{_RED}'>▼ 卖出</b>"
        elif x in self._buy_triggers:
            mark = f"  <b style='color:{_GRN}'>▲ 买入信号</b>"
        elif x in self._sell_triggers:
            mark = f"  <b style='color:{_RED}'>▼ 卖出信号</b>"

        self._info_bar.setText(
            f"  {datetime_str}　"
            f"开 <b style='color:{_FG}'>{o:.2f}</b>　"
            f"高 <b style='color:{_C_UP}'>{h:.2f}</b>　"
            f"低 <b style='color:{_C_DN}'>{l:.2f}</b>　"
            f"收 <b style='color:{_FG}'>{c:.2f}</b>　"
            f"涨幅 <b style='color:{cc}'>{cs}</b>　"
            f"量 <span style='color:{_MUT}'>{vol/1e4:.0f}万</span>"
            f"{mark}")
        self._info_bar.setTextFormat(QtCore.Qt.TextFormat.RichText)




# ── 后台数据加载线程 ─────────────────────────────────────────────────

class _BarLoaderThread(QtCore.QThread):
    """后台线程加载 K 线数据，避免阻塞 UI 主线程。"""
    finished = QtCore.Signal(list)  # 加载完成信号，携带 bars 列表

    def __init__(self, load_fn, symbol: str, parent=None):
        super().__init__(parent)
        self._load_fn = load_fn
        self._symbol = symbol

    def run(self):
        bars = self._load_fn(self._symbol)
        self.finished.emit(bars)


# ── K线图 Tab ────────────────────────────────────────────────────────

class KlineViewTab(QtWidgets.QWidget):
    """
    K线图 Tab。
    外部调用：show_symbol(symbol, buy_dates=[...], sell_dates=[...])
    """

    def __init__(self, engine=None, parent=None):
        super().__init__(parent)
        self.engine = engine
        self._current_symbol = ""
        self._current_buy_triggers: list = []
        self._current_sell_triggers: list = []
        self._waveform_snapshots: list = []
        self._waveform_dates: list = []
        # ── 缓存：避免相同请求重复查库/重绘 ──
        self._cache_key: tuple = ()  # (symbol, interval_idx, buy_dates_tuple, sell_dates_tuple)
        # ── 异步加载状态 ──
        self._loader_thread: _BarLoaderThread = None
        self._pending_buy_dates: list = []
        self._pending_sell_dates: list = []
        self._pending_trigger_dates: list = []
        self._build_ui()

    def _build_ui(self) -> None:
        self.setStyleSheet(f"background:{_BG};")
        root = QtWidgets.QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # 工具栏
        # ── 主工具栏（紧凑版：控件更小、间距更紧）──────────────────
        toolbar = QtWidgets.QWidget()
        toolbar.setFixedHeight(30)
        toolbar.setStyleSheet(
            f"background:{_PANEL};border-bottom:1px solid {_BORD};")
        tl = QtWidgets.QHBoxLayout(toolbar)
        tl.setContentsMargins(6, 0, 6, 0)
        tl.setSpacing(3)

        # 统一样式常量
        _MINI_H = 20
        _sep_style = f"background:{_BORD};max-width:1px;min-width:1px;"
        _btn_common = (f"QPushButton{{border:none;border-radius:2px;"
                       f"font-size:11px;font-weight:bold;padding:0 6px;}}")

        def _mk_sep():
            s = QtWidgets.QFrame()
            s.setFrameShape(QtWidgets.QFrame.Shape.VLine)
            s.setFixedWidth(1)
            s.setStyleSheet(_sep_style)
            return s

        # 代码输入 + 加载
        self._sym_edit = QtWidgets.QLineEdit()
        self._sym_edit.setFixedSize(70, _MINI_H)
        self._sym_edit.setPlaceholderText("代码")
        self._sym_edit.setStyleSheet(
            f"background:{_PAN2};color:{_FG};border:1px solid {_BORD};"
            f"border-radius:2px;padding:0 4px;font-size:11px;")
        self._sym_edit.returnPressed.connect(self._on_manual_load)
        tl.addWidget(self._sym_edit)

        load_btn = QtWidgets.QPushButton("加载")
        load_btn.setFixedSize(36, _MINI_H)
        load_btn.setStyleSheet(
            _btn_common + f"QPushButton{{background:{_BLU};color:#11111b;}}")
        load_btn.clicked.connect(self._on_manual_load)
        tl.addWidget(load_btn)

        tl.addWidget(_mk_sep())

        # K线周期选择（去掉"周期:"标签，节省空间）
        self._interval_cb = QtWidgets.QComboBox()
        self._interval_cb.setFixedSize(66, _MINI_H)
        self._interval_cb.setStyleSheet(
            "QComboBox{background:#11111b;color:#cdd6f4;"
            "border:1px solid #45475a;border-radius:2px;"
            "padding:0 4px;font-size:11px;}"
            "QComboBox::drop-down{border:none;width:14px;}"
            "QComboBox::down-arrow{width:8px;height:8px;}")
        self._interval_options = [
            (Interval.DAILY,    "日线"),
            (Interval.MINUTE,   "1分钟"),
            (Interval.MINUTE_5, "5分钟"),
            (Interval.MINUTE_15,"15分钟"),
            (Interval.MINUTE_30,"30分钟"),
            (Interval.HOUR,     "60分钟"),
        ]
        for _, name in self._interval_options:
            self._interval_cb.addItem(name)
        self._interval_cb.setCurrentIndex(0)
        tl.addWidget(self._interval_cb)

        tl.addWidget(_mk_sep())

        # ── MA 组：标准 checkbox（带对勾）+ 数字输入框 ──────────────
        tl.addWidget(_lbl('MA', _MUT, 11))
        _edit_style = ('background:#11111b;border:1px solid #45475a;'
                       'border-radius:2px;padding:0 2px;'
                       'font-size:11px;font-weight:bold;')
        # 复选框：使用默认对勾（原生 ✔），字体着色为均线颜色
        _chk_style = ('QCheckBox{{spacing:2px;background:transparent;}}'
                      'QCheckBox::indicator{{width:12px;height:12px;}}')
        self._ma_inputs = []
        self._ma_enabled = []
        _MA_DEFAULTS = [
            ('5',   '#f9e2af'),  # 黄色
            ('10',  '#94e2d5'),  # 青色
            ('20',  '#89b4fa'),  # 蓝色
            ('60',  '#cba6f7'),  # 紫色
            ('120', '#f5c2e7'),  # 粉色
            ('250', '#a6e3a1'),  # 绿色
        ]
        for default, color in _MA_DEFAULTS:
            chk = QtWidgets.QCheckBox()
            chk.setChecked(default in ('5', '20', '60'))
            chk.setStyleSheet(_chk_style.format(c=color))
            chk.setFixedHeight(_MINI_H)
            chk.stateChanged.connect(self._on_ma_toggle)
            edt = QtWidgets.QLineEdit(default)
            edt.setFixedSize(28, _MINI_H)
            edt.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
            edt.setStyleSheet(f'QLineEdit{{{_edit_style}color:{color};}}')
            edt.editingFinished.connect(self._on_ma_toggle)
            tl.addWidget(chk)
            tl.addWidget(edt)
            self._ma_inputs.append(edt)
            self._ma_enabled.append(chk)

        tl.addWidget(_mk_sep())

        # ── 显示选项：标准 checkbox + 彩色文字标签 ──────────────
        _opt_chk_style = ('QCheckBox{{color:{c};font-size:11px;'
                          'background:transparent;spacing:2px;}}'
                          'QCheckBox::indicator{{width:12px;height:12px;}}')

        def _mk_opt(text: str, color: str):
            c = QtWidgets.QCheckBox(text)
            c.setChecked(True)
            c.setStyleSheet(_opt_chk_style.format(c=color))
            c.setFixedHeight(_MINI_H)
            return c

        self._candle_chk = _mk_opt('K线', _C_UP)
        self._candle_chk.stateChanged.connect(self._on_ma_toggle)
        tl.addWidget(self._candle_chk)

        self._vol_chk = _mk_opt('量', _YLW)
        self._vol_chk.stateChanged.connect(self._on_vol_toggle)
        tl.addWidget(self._vol_chk)

        self._trig_chk = _mk_opt('信号', '#c084fc')
        self._trig_chk.stateChanged.connect(self._on_ma_toggle)
        tl.addWidget(self._trig_chk)

        self._yaxis_chk = _mk_opt('Y轴', '#94e2d5')
        self._yaxis_chk.stateChanged.connect(self._on_yaxis_toggle)
        tl.addWidget(self._yaxis_chk)

        tl.addWidget(_mk_sep())

        # 测量工具 + 全屏（图标按钮）
        self._measure_btn = QtWidgets.QPushButton('📏')
        self._measure_btn.setCheckable(True)
        self._measure_btn.setFixedSize(24, _MINI_H)
        self._measure_btn.setToolTip('测量工具')
        self._measure_btn.setStyleSheet(
            'QPushButton{background:#313244;color:#cdd6f4;'
            'border:1px solid #45475a;border-radius:2px;font-size:11px;}'
            'QPushButton:hover{background:#45475a;}'
            'QPushButton:checked{background:#a6e3a1;color:#11111b;'
            'border-color:#a6e3a1;}')
        self._measure_btn.clicked.connect(self._on_measure_toggle)
        tl.addWidget(self._measure_btn)

        self._fullscreen_btn = QtWidgets.QPushButton('⛶')
        self._fullscreen_btn.setFixedSize(24, _MINI_H)
        self._fullscreen_btn.setToolTip('全屏')
        self._fullscreen_btn.setStyleSheet(
            _btn_common + "QPushButton{background:#fab387;color:#11111b;"
                          "font-size:13px;padding:0;}")
        self._fullscreen_btn.clicked.connect(self._on_fullscreen)
        tl.addWidget(self._fullscreen_btn)

        tl.addStretch()
        self._title_lbl = _lbl("未选择股票", _MUT, 10)
        tl.addWidget(self._title_lbl)

        root.addWidget(toolbar)

        # 图表主体
        self._chart = KlineChartWidget()
        root.addWidget(self._chart, 1)

        # ── 底部栏：仅保留触发计数 + 跳转按钮（默认隐藏）─────────
        # 说明：▲/▼、涨/跌、MA 颜色 都已在工具栏和图表中体现，无需再单列。
        legend = QtWidgets.QWidget()
        legend.setFixedHeight(22)
        legend.setStyleSheet(
            f"background:{_PANEL};border-top:1px solid {_BORD};")
        ll = QtWidgets.QHBoxLayout(legend)
        ll.setContentsMargins(8, 0, 8, 0)
        ll.setSpacing(6)
        ll.addStretch()
        self._trig_count_lbl = _lbl("", _MUT, 10)
        ll.addWidget(self._trig_count_lbl)

        # 触发点跳转按钮
        self._prev_btn = QtWidgets.QPushButton('◀')
        self._prev_btn.setFixedSize(22, 18)
        self._prev_btn.setStyleSheet(
            'background:#cba6f7;color:#11111b;border:none;'
            'border-radius:2px;font-size:10px;font-weight:bold;')
        self._prev_btn.clicked.connect(lambda: self._chart.jump_to_trigger(-1))
        ll.addWidget(self._prev_btn)
        self._next_btn = QtWidgets.QPushButton('▶')
        self._next_btn.setFixedSize(22, 18)
        self._next_btn.setStyleSheet(
            'background:#89b4fa;color:#11111b;border:none;'
            'border-radius:2px;font-size:10px;font-weight:bold;')
        self._next_btn.clicked.connect(lambda: self._chart.jump_to_trigger(+1))
        ll.addWidget(self._next_btn)
        self._prev_btn.setVisible(False)
        self._next_btn.setVisible(False)
        # 底部栏默认隐藏，仅在有触发信号时显示（见 _update_trig_count_visibility）
        self._legend_bar = legend
        legend.setVisible(False)
        root.addWidget(legend)

    # ── 公开接口 ─────────────────────────────────────────────────────

    def show_symbol(self, symbol: str, trigger_dates: list = None,
                    buy_dates: list = None, sell_dates: list = None) -> None:
        """
        显示 K 线图并标记信号（异步加载，不阻塞 UI）。
        数据库查询在后台线程执行，完成后回到主线程渲染。
        """
        # ── 缓存命中检测 ──
        new_key = (
            symbol,
            self._interval_cb.currentIndex(),
            tuple(buy_dates or []),
            tuple(sell_dates or []),
            tuple(trigger_dates or []),
        )
        if new_key == self._cache_key and self._chart._bars:
            return
        self._cache_key = new_key

        self._current_symbol = symbol
        self._last_buy_dates = list(buy_dates or [])
        self._last_sell_dates = list(sell_dates or [])
        self._sym_edit.setText(symbol)

        # 保存待渲染的信号日期（等数据加载完再处理）
        self._pending_buy_dates = list(buy_dates or [])
        self._pending_sell_dates = list(sell_dates or [])
        self._pending_trigger_dates = list(trigger_dates or [])

        # 显示加载中状态
        self._title_lbl.setText(f'{symbol}  ⏳ 加载中...')
        self._title_lbl.setStyleSheet(
            'color:#f9e2af;font-size:14px;background:transparent;border:none;')

        # 如果已有线程在跑，停止旧的
        if self._loader_thread is not None and self._loader_thread.isRunning():
            self._loader_thread.finished.disconnect()
            self._loader_thread.quit()
            self._loader_thread.wait(500)

        # 启动后台线程加载数据
        self._loader_thread = _BarLoaderThread(self._load_bars, symbol, self)
        self._loader_thread.finished.connect(self._on_bars_loaded)
        self._loader_thread.start()

    def _on_bars_loaded(self, bars: list) -> None:
        """后台线程加载完毕回调（在主线程执行）。"""
        symbol = self._current_symbol

        # 保存原始 BarData 列表，供 Monitor Tab 复用
        self._last_raw_bars = list(bars) if bars else []
        if not bars:
            self._title_lbl.setText(f'{symbol}  -- no data')
            self._title_lbl.setStyleSheet(
                'color:#f38ba8;font-size:14px;background:transparent;border:none;')
            self._chart.clear()
            self._trig_count_lbl.setText('')
            self._prev_btn.setVisible(False)
            self._next_btn.setVisible(False)
            return

        # 日期→索引映射
        date_to_idx = {}
        date_to_idx_10 = {}
        for i, b in enumerate(bars):
            dt = b.datetime
            if dt.hour == 0 and dt.minute == 0:
                key = dt.strftime('%Y-%m-%d')
                date_to_idx[key] = i
            else:
                key = dt.strftime('%Y-%m-%d %H:%M')
                date_to_idx[key] = i
                key_10 = dt.strftime('%Y-%m-%d')
                date_to_idx_10[key_10] = i

        def normalize_date(d: str) -> str:
            d = d.strip()
            if len(d) >= 16 and ':' in d:
                return d[:16]
            elif len(d) >= 10:
                return d[:10]
            return d

        buy_dates  = [normalize_date(d) for d in self._pending_buy_dates]
        sell_dates = [normalize_date(d) for d in self._pending_sell_dates]

        if not buy_dates and not sell_dates and self._pending_trigger_dates:
            buy_dates = [normalize_date(d) for d in self._pending_trigger_dates]

        buy_indices_set = set()
        for d in buy_dates:
            if d in date_to_idx:
                buy_indices_set.add(date_to_idx[d])
            elif d in date_to_idx_10:
                buy_indices_set.add(date_to_idx_10[d])

        sell_indices_set = set()
        for d in sell_dates:
            if d in date_to_idx:
                sell_indices_set.add(date_to_idx[d])
            elif d in date_to_idx_10:
                sell_indices_set.add(date_to_idx_10[d])

        buy_indices  = sorted(buy_indices_set)
        sell_indices = sorted(sell_indices_set)

        self._current_buy_triggers  = buy_indices
        self._current_sell_triggers = sell_indices

        total_cnt = len(buy_indices) + len(sell_indices)
        self._title_lbl.setText(f'{symbol}  ({len(bars)} bars)')
        self._title_lbl.setStyleSheet(
            'color:#a6e3a1;font-size:14px;background:transparent;border:none;')

        parts = []
        if buy_indices:
            parts.append(f"买入 {len(buy_indices)}")
        if sell_indices:
            parts.append(f"卖出 {len(sell_indices)}")
        self._trig_count_lbl.setText(" | ".join(parts) if parts else "")

        # 有触发信号时才显示底部栏
        has_triggers = total_cnt > 0
        self._legend_bar.setVisible(has_triggers)
        self._prev_btn.setVisible(has_triggers)
        self._next_btn.setVisible(has_triggers)
        
        self._chart.set_ma_flags(self._get_ma_config(), self._trig_chk.isChecked())
        self._chart.load(bars, buy_indices, sell_indices)

    def clear(self) -> None:
        self._current_symbol = ''
        self._current_buy_triggers = []
        self._current_sell_triggers = []
        self._chart.clear()
        self._title_lbl.setStyleSheet(
            f'color:#6c7086;font-size:14px;background:transparent;border:none;')
        self._trig_count_lbl.setText('')
        self._prev_btn.setVisible(False)
        self._next_btn.setVisible(False)

    def _on_manual_load(self) -> None:
        sym = self._sym_edit.text().strip()
        if sym:
            self.show_symbol(sym)

    def _on_measure_toggle(self, checked: bool) -> None:
        """Toggle measure mode using MeasureTool."""
        if not hasattr(self._chart, '_measure_tool'):
            self._chart._measure_tool = MeasureTool(self._chart._main_plot, self._chart._bars, self._chart._dates)
        self._chart._measure_tool.set_active(checked)

    def _get_ma_config(self) -> list:
        colors = ['#f9e2af', '#94e2d5', '#89b4fa', '#cba6f7', '#f5c2e7', '#a6e3a1']
        result = []
        for i, edt in enumerate(self._ma_inputs):
            try:
                period = int(edt.text().strip())
            except ValueError:
                period = 0
            color = colors[i] if i < len(colors) else '#cdd6f4'
            enabled = self._ma_enabled[i].isChecked() and period > 0
            result.append((period, color, enabled))
        return result

    def _on_yaxis_toggle(self, state: int) -> None:
        """切换Y轴自适应模式。"""
        enabled = bool(state)
        self._chart.set_auto_yaxis(enabled)

    def _on_vol_toggle(self, *_) -> None:
        self._chart.set_volume_visible(self._vol_chk.isChecked())

    def _on_ma_toggle(self, *_) -> None:
        self._chart.set_ma_flags(
            self._get_ma_config(),
            self._trig_chk.isChecked(),
            self._candle_chk.isChecked(),
        )
        self._chart._redraw()

    def set_waveform_data(self, snapshots: list, dates: list = None,
                          buy_indices: list = None,
                          sell_indices: list = None) -> None:
        """设置波形数据（由 ConditionMonitorWidget 调用）"""
        self._waveform_snapshots = snapshots
        self._waveform_dates = dates or []
        self._waveform_buy_indices = buy_indices or []
        self._waveform_sell_indices = sell_indices or []

    def _on_fullscreen(self) -> None:
        """弹出独立全屏 K 线图窗口（含波形区）。"""
        if not self._chart._bars:
            return
        win = _KlineFullscreenWindow(
            bars=self._chart._bars,
            dates=self._chart._dates,
            volumes=self._chart._volumes,
            buy_triggers=self._chart._buy_triggers,
            sell_triggers=self._chart._sell_triggers,
            ma_flags=self._get_ma_config(),
            show_triggers=self._trig_chk.isChecked(),
            show_candles=self._candle_chk.isChecked(),
            title=self._current_symbol,
            datetimes=getattr(self._chart, '_datetimes', None),
            waveform_snapshots=self._waveform_snapshots,
            waveform_dates=self._waveform_dates,
            waveform_buy_indices=getattr(self, '_waveform_buy_indices', []),
            waveform_sell_indices=getattr(self, '_waveform_sell_indices', []),
            parent=self,
        )
        win.showMaximized()

    def _load_bars(self, symbol: str) -> list:
        """
        symbol 可以是 "601857.SSE" 或 "601857" 两种格式。
        先拆分后缀确定交易所，再用纯代码查库。
        """
        try:
            import datetime
            from vnpy.trader.database import get_database
            from vnpy.trader.constant import Exchange, Interval

            # Get selected interval from UI
            idx = self._interval_cb.currentIndex()
            interval, _ = self._interval_options[idx]

            if "." in symbol:
                sym_code, suffix = symbol.rsplit(".", 1)
                suffix = suffix.upper()
            else:
                sym_code = symbol.strip()
                suffix   = ""

            if suffix in ("SSE", "SH"):
                exch = Exchange.SSE
            elif suffix in ("SZSE", "SZ"):
                exch = Exchange.SZSE
            elif suffix == "BSE":
                exch = Exchange.BSE
            elif sym_code.startswith(("000","001","002","003","300","301")):
                exch = Exchange.SZSE
            elif sym_code.startswith(("600","601","603","605","688")):
                exch = Exchange.SSE
            elif sym_code.startswith(("430","83","87")):
                exch = Exchange.BSE
            else:
                exch = Exchange.SSE

            db   = get_database()
            bars = db.load_bar_data(
                symbol=sym_code,
                exchange=exch,
                interval=interval,
                start=datetime.datetime(2000, 1, 1),
                end=datetime.datetime(2099, 12, 31),
            )
            return sorted(bars, key=lambda b: b.datetime) if bars else []
        except Exception as e:
            import traceback
            traceback.print_exc()
            print(f"[KlineViewTab] load_bars error: {e}")
            return []


# ── 全屏 K 线图窗口 ──────────────────────────────────────────────────

class _KlineFullscreenWindow(QtWidgets.QWidget):
    """独立弹出的全屏 K 线图窗口，按 Esc 或点击关闭按钮退出。"""

    def __init__(self, bars: list, dates: list, volumes: list,
                 buy_triggers: set, sell_triggers: set,
                 ma_flags: list, show_triggers: bool,
                 show_candles: bool = True,
                 title: str = "", datetimes: list = None,
                 waveform_snapshots: list = None,
                 waveform_dates: list = None,
                 waveform_buy_indices: list = None,
                 waveform_sell_indices: list = None,
                 parent=None):
        super().__init__(parent, QtCore.Qt.WindowType.Window)
        self.setWindowTitle(f"K线图 全屏 — {title}")
        self.setStyleSheet(f"background:{_BG};")
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_DeleteOnClose)
        self._waveform_snapshots = waveform_snapshots or []
        self._waveform_dates = waveform_dates or []
        self._waveform_buy_indices = waveform_buy_indices or []
        self._waveform_sell_indices = waveform_sell_indices or []

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # 顶部工具条
        top_bar = QtWidgets.QWidget()
        top_bar.setFixedHeight(36)
        top_bar.setStyleSheet(
            f"background:{_PANEL};border-bottom:1px solid {_BORD};")
        tl = QtWidgets.QHBoxLayout(top_bar)
        tl.setContentsMargins(14, 0, 14, 0)
        tl.setSpacing(8)
        tl.addWidget(_lbl(f"📈 {title}", _GRN, 15, True))
        tl.addWidget(_lbl(f"{len(bars)} bars", _MUT, 13))

        sep = QtWidgets.QFrame()
        sep.setFrameShape(QtWidgets.QFrame.Shape.VLine)
        sep.setStyleSheet(f"color:{_BORD};")
        tl.addWidget(sep)

        # MA 均线设置（6根）
        tl.addWidget(_lbl('MA:', _MUT, 13))
        # 注意：_edit_style 不设置 color，避免覆盖后面按均线颜色设置的字体色
        _edit_style = ('background:#11111b;border:1px solid #45475a;'
                       'border-radius:3px;padding:1px 4px;font-size:12px;font-weight:bold;')
        _chk_style = 'font-size:13px;background:transparent;'
        _MA_DEFAULTS = [
            ('5',   '#f9e2af'),
            ('10',  '#94e2d5'),
            ('20',  '#89b4fa'),
            ('60',  '#cba6f7'),
            ('120', '#f5c2e7'),
            ('250', '#a6e3a1'),
        ]
        self._ma_inputs = []
        self._ma_enabled = []
        for idx_ma, (default, color) in enumerate(_MA_DEFAULTS):
            # 默认启用的和传入 ma_flags 对应
            initially_on = ma_flags[idx_ma][2] if idx_ma < len(ma_flags) else False
            init_period = str(ma_flags[idx_ma][0]) if idx_ma < len(ma_flags) else default
            chk = QtWidgets.QCheckBox()
            chk.setChecked(initially_on)
            chk.setStyleSheet(f'QCheckBox{{color:{color};{_chk_style}}}')
            edt = QtWidgets.QLineEdit(init_period)
            edt.setFixedWidth(34)
            edt.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
            edt.setStyleSheet(f'QLineEdit{{{_edit_style}color:{color};}}')
            tl.addWidget(chk)
            tl.addWidget(edt)
            self._ma_inputs.append(edt)
            self._ma_enabled.append(chk)

        sep2 = QtWidgets.QFrame()
        sep2.setFrameShape(QtWidgets.QFrame.Shape.VLine)
        sep2.setStyleSheet(f"color:{_BORD};")
        tl.addWidget(sep2)

        self._candle_chk = QtWidgets.QCheckBox('K线')
        self._candle_chk.setChecked(show_candles)
        self._candle_chk.setStyleSheet(f'color:{_C_UP};font-size:13px;background:transparent;')
        tl.addWidget(self._candle_chk)

        self._trig_chk = QtWidgets.QCheckBox('信号')
        self._trig_chk.setChecked(show_triggers)
        self._trig_chk.setStyleSheet('color:#c084fc;font-size:13px;background:transparent;')
        tl.addWidget(self._trig_chk)

        tl.addStretch()
        tl.addWidget(_lbl("按 Esc 退出全屏", _MUT, 12))

        
        # 测量工具按钮
        self._fs_measure_btn = QtWidgets.QPushButton("📏 测量")
        self._fs_measure_btn.setCheckable(True)
        self._fs_measure_btn.setFixedHeight(28)
        self._fs_measure_btn.setStyleSheet(
            "QPushButton{background:#313244;color:#cdd6f4;border:1px solid #45475a;"
            "border-radius:4px;padding:2px 10px;font-size:13px;}"
            "QPushButton:hover{background:#45475a;}"
            "QPushButton:checked{background:#FFA500;color:#1e1e2e;border-color:#FFA500;}")
        self._fs_measure_btn.clicked.connect(self._on_fs_measure_toggle)
        tl.addWidget(self._fs_measure_btn)

        close_btn = QtWidgets.QPushButton("✕ 关闭")
        close_btn.setFixedHeight(26)
        close_btn.setStyleSheet(
            'background:#f38ba8;color:#11111b;border:none;'
            'border-radius:4px;font-size:13px;font-weight:bold;padding:0 14px;')
        close_btn.clicked.connect(self.close)
        tl.addWidget(close_btn)
        layout.addWidget(top_bar)

        # 图表（复用已有渲染逻辑）
        self._chart = _FullscreenChart(
            bars, dates, volumes, buy_triggers, sell_triggers,
            ma_flags, show_triggers, show_candles,
            datetimes=datetimes)

        # 如果有波形数据，使用 splitter 显示 K线 + 波形
        if self._waveform_snapshots:
            splitter = QtWidgets.QSplitter(QtCore.Qt.Orientation.Vertical)
            splitter.setHandleWidth(5)
            splitter.setStyleSheet(
                "QSplitter::handle { background: #45475a; }"
                "QSplitter::handle:hover { background: #89b4fa; }")
            splitter.addWidget(self._chart)
            # 创建波形视图
            from .condition_monitor_widget import ConditionWaveformView
            self._waveform_view = ConditionWaveformView()
            self._waveform_view.load_data(
                self._waveform_snapshots, self._waveform_dates,
                buy_indices=self._waveform_buy_indices,
                sell_indices=self._waveform_sell_indices)
            splitter.addWidget(self._waveform_view)
            splitter.setStretchFactor(0, 6)
            splitter.setStretchFactor(1, 4)
            layout.addWidget(splitter, 1)
            # X 轴联动 + 竖线同步
            wf_plots = self._waveform_view.get_plots()
            main_plot = self._chart._main_plot
            for wp in wf_plots:
                wp.setXLink(main_plot)
            # 建立十字线同步
            self._setup_vline_sync()
        else:
            layout.addWidget(self._chart, 1)

        # 连接 MA 控件信号
        for chk in self._ma_enabled:
            chk.stateChanged.connect(self._on_ma_toggle)
        for edt in self._ma_inputs:
            edt.editingFinished.connect(self._on_ma_toggle)
        self._candle_chk.stateChanged.connect(self._on_ma_toggle)
        self._trig_chk.stateChanged.connect(self._on_ma_toggle)

    def _setup_vline_sync(self) -> None:
        """建立 K线区 ↔ 波形区的竖线同步。"""
        chart = self._chart
        main_plot = chart._main_plot
        waveform_view = self._waveform_view

        # 替换 chart 原有的鼠标监听，增加波形竖线同步
        try:
            chart._proxy.disconnect()
        except Exception:
            pass

        def _on_mouse_moved_synced(evt):
            pos = evt[0]
            if main_plot.sceneBoundingRect().contains(pos):
                mp = main_plot.vb.mapSceneToView(pos)
                x = mp.x()
                chart._vline.setPos(x)
                chart._hline.setPos(mp.y())
                waveform_view.set_vline_pos(x)
                # 更新信息栏
                chart._on_mouse_moved(evt)
            else:
                waveform_view.hide_vlines()

        chart._proxy = pg.SignalProxy(
            main_plot.scene().sigMouseMoved,
            rateLimit=60, slot=_on_mouse_moved_synced)

        # 波形区鼠标移动 → 同步竖线到 K 线区
        wf_plots = waveform_view.get_plots()
        for wp in wf_plots:
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
                            waveform_view.set_vline_pos(x)
                    return _handler
                pg.SignalProxy(
                    scene.sigMouseMoved,
                    rateLimit=60,
                    slot=_make_wave_handler(wp))

    def _on_ma_toggle(self, *_) -> None:
        colors = ['#f9e2af', '#94e2d5', '#89b4fa', '#cba6f7', '#f5c2e7', '#a6e3a1']
        ma_flags = []
        for i, edt in enumerate(self._ma_inputs):
            try:
                period = int(edt.text().strip())
            except ValueError:
                period = 0
            color = colors[i] if i < len(colors) else '#cdd6f4'
            enabled = self._ma_enabled[i].isChecked() and period > 0
            ma_flags.append((period, color, enabled))
        self._chart._ma_flags = ma_flags
        self._chart._show_candles = self._candle_chk.isChecked()
        self._chart._show_triggers = self._trig_chk.isChecked()
        self._chart._redraw()

    def _on_fs_measure_toggle(self, checked: bool) -> None:
        """Toggle measure mode in fullscreen chart."""
        self._chart._on_measure_toggle(checked)

    def keyPressEvent(self, event) -> None:
        if event.key() == QtCore.Qt.Key.Key_Escape:
            self.close()
        else:
            super().keyPressEvent(event)


class _FullscreenChart(QtWidgets.QWidget):
    """全屏模式下的 K 线图渲染（直接接收已解析的数据，无需再加载）。"""

    def __init__(self, bars: list, dates: list, volumes: list,
                 buy_triggers: set, sell_triggers: set,
                 ma_flags: list, show_triggers: bool,
                 show_candles: bool = True,
                 datetimes: list = None, parent=None):
        super().__init__(parent)
        self._bars = bars
        self._dates = dates
        self._volumes = volumes
        self._datetimes = datetimes or []
        self._buy_triggers = buy_triggers
        self._sell_triggers = sell_triggers
        self._ma_flags = ma_flags
        self._show_triggers = show_triggers
        self._show_candles = show_candles

        self._build_ui()
        self._redraw()

    def _build_ui(self) -> None:
        pg.setConfigOptions(antialias=False, background=_BG, foreground=_FG)
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self._info_bar = QtWidgets.QLabel("  — 移动鼠标查看K线数据 —")
        self._info_bar.setMinimumHeight(26)
        self._info_bar.setStyleSheet(
            f"color:{_MUT};font-size:14px;background:{_PANEL};"
            f"padding:2px 10px;border-bottom:1px solid {_BORD};")
        layout.addWidget(self._info_bar)

        # 使用 QSplitter 使 K线区和成交量区高度可拖拽调整
        splitter = QtWidgets.QSplitter(QtCore.Qt.Orientation.Vertical)
        splitter.setHandleWidth(5)
        splitter.setStyleSheet(
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

        splitter.addWidget(self._glw_main)
        splitter.addWidget(self._glw_vol)
        splitter.setStretchFactor(0, 7)
        splitter.setStretchFactor(1, 3)
        self._glw_vol.setVisible(False)
        layout.addWidget(splitter, 1)

        self._vline = pg.InfiniteLine(angle=90, pen=pg.mkPen(_MUT, width=1,
                       style=QtCore.Qt.PenStyle.DashLine))
        self._hline = pg.InfiniteLine(angle=0, pen=pg.mkPen(_MUT, width=1,
                       style=QtCore.Qt.PenStyle.DashLine))
        self._main_plot.addItem(self._vline, ignoreBounds=True)
        self._main_plot.addItem(self._hline, ignoreBounds=True)

        self._proxy = pg.SignalProxy(
            self._main_plot.scene().sigMouseMoved,
            rateLimit=60, slot=self._on_mouse_moved)

        # Connect mouse click for measure tool



    def _redraw(self) -> None:
        self._main_plot.clear()
        self._vol_plot.clear()
        if not self._bars:
            return

        import numpy as np
        n = len(self._bars)
        closes = [b[3] for b in self._bars]

        ax = DateAxis(self._dates, datetimes=self._datetimes, orientation="bottom")
        ax.setTextPen(_MUT)
        self._main_plot.setAxisItems({"bottom": ax})
        ax_v = DateAxis(self._dates, datetimes=self._datetimes, orientation="bottom")
        ax_v.setTextPen(_MUT)
        self._vol_plot.setAxisItems({"bottom": ax_v})

        # 日期分隔线（分钟线时，不同日期之间画竖线）
        if len(self._dates) > 1:
            has_same_date = any(self._dates[i] == self._dates[i+1]
                                for i in range(min(10, len(self._dates)-1)))
            if has_same_date:
                prev_date = self._dates[0]
                for i in range(1, n):
                    cur_date = self._dates[i]
                    if cur_date != prev_date:
                        vline = pg.InfiniteLine(
                            pos=i - 0.5, angle=90,
                            pen=pg.mkPen("#f9e2af", width=1,
                                         style=QtCore.Qt.PenStyle.DashLine))
                        self._main_plot.addItem(vline)
                    prev_date = cur_date

        if self._show_candles:
            candles = CandlestickItem(self._bars)
            self._main_plot.addItem(candles)

        closes_arr = np.array(closes, dtype=np.float64)
        for period, color, enabled in self._ma_flags:
            if enabled and n >= period:
                cumsum = np.cumsum(closes_arr)
                ma = np.empty(n, dtype=np.float64)
                ma[:period] = cumsum[:period] / np.arange(1, period + 1)
                ma[period:] = (cumsum[period:] - cumsum[:-period]) / period
                self._main_plot.plot(np.arange(n), ma,
                    pen=pg.mkPen(color, width=1))

        if self._show_triggers:
            all_triggers = self._buy_triggers | self._sell_triggers
            for ti in sorted(i for i in all_triggers if 0 <= i < n):
                is_buy = ti in self._buy_triggers
                brush_color = (166, 227, 161, 50) if is_buy else (243, 139, 168, 50)
                band = pg.LinearRegionItem(
                    values=[ti - 0.45, ti + 0.45],
                    orientation='vertical',
                    brush=pg.mkBrush(*brush_color),
                    pen=pg.mkPen(None), movable=False)
                self._main_plot.addItem(band)

            buy_ix = sorted(i for i in self._buy_triggers if 0 <= i < n)
            if buy_ix:
                buy_y = [self._bars[i][2] * 0.97 for i in buy_ix]
                self._main_plot.addItem(pg.ScatterPlotItem(
                    x=buy_ix, y=buy_y, symbol="t1", size=18,
                    pen=pg.mkPen(_GRN, width=2), brush=pg.mkBrush(_GRN)))

            sell_ix = sorted(i for i in self._sell_triggers if 0 <= i < n)
            if sell_ix:
                sell_y = [self._bars[i][1] * 1.03 for i in sell_ix]
                self._main_plot.addItem(pg.ScatterPlotItem(
                    x=sell_ix, y=sell_y, symbol="t", size=18,
                    pen=pg.mkPen(_RED, width=2), brush=pg.mkBrush(_RED)))

        vol_item = VolumeItem(self._volumes, closes)
        self._vol_plot.addItem(vol_item)

        self._vline = pg.InfiniteLine(angle=90, pen=pg.mkPen(_MUT, width=1,
                       style=QtCore.Qt.PenStyle.DashLine))
        self._hline = pg.InfiniteLine(angle=0, pen=pg.mkPen(_MUT, width=1,
                       style=QtCore.Qt.PenStyle.DashLine))
        self._main_plot.addItem(self._vline, ignoreBounds=True)
        self._main_plot.addItem(self._hline, ignoreBounds=True)

        self._main_plot.setXRange(max(0, n - 180), n, padding=0.02)
        vis_start = max(0, n - 180)
        vis_bars = self._bars[vis_start:n]
        if vis_bars:
            price_lo = min(b[2] for b in vis_bars)
            price_hi = max(b[1] for b in vis_bars)
            margin = (price_hi - price_lo) * 0.08 or price_hi * 0.05
            self._main_plot.setYRange(price_lo - margin, price_hi + margin, padding=0)
        self._main_plot.setMouseEnabled(x=True, y=True)

    def _on_mouse_moved(self, evt) -> None:
        pos = evt[0]
        if not self._main_plot.sceneBoundingRect().contains(pos):
            return
        mp = self._main_plot.vb.mapSceneToView(pos)
        x = int(round(mp.x()))
        self._vline.setPos(mp.x())
        self._hline.setPos(mp.y())
        if not (0 <= x < len(self._bars)):
            return
        o, h, l, c = self._bars[x]
        vol = self._volumes[x] if x < len(self._volumes) else 0
        chg = ((c - self._bars[x-1][3]) / self._bars[x-1][3] * 100
               if x > 0 else 0.0)
        cs = f"+{chg:.2f}%" if chg >= 0 else f"{chg:.2f}%"
        cc = _C_UP if chg >= 0 else _C_DN

        # 显示日期+时间（分钟线显示HH:MM）
        if x < len(self._datetimes) and self._datetimes:
            dt = self._datetimes[x]
            if dt.hour == 0 and dt.minute == 0:
                datetime_str = dt.strftime("%Y-%m-%d")
            else:
                datetime_str = dt.strftime("%Y-%m-%d %H:%M")
        else:
            datetime_str = self._dates[x] if x < len(self._dates) else ""

        mark = ""
        if x in self._buy_triggers and x in self._sell_triggers:
            mark = f"  <b style='color:{_GRN}'>▲ 买入</b> + <b style='color:{_RED}'>▼ 卖出</b>"
        elif x in self._buy_triggers:
            mark = f"  <b style='color:{_GRN}'>▲ 买入信号</b>"
        elif x in self._sell_triggers:
            mark = f"  <b style='color:{_RED}'>▼ 卖出信号</b>"

        self._info_bar.setText(
            f"  {datetime_str}　"
            f"开 <b style='color:{_FG}'>{o:.2f}</b>　"
            f"高 <b style='color:{_C_UP}'>{h:.2f}</b>　"
            f"低 <b style='color:{_C_DN}'>{l:.2f}</b>　"
            f"收 <b style='color:{_FG}'>{c:.2f}</b>　"
            f"涨幅 <b style='color:{cc}'>{cs}</b>　"
            f"量 <span style='color:{_MUT}'>{vol/1e4:.0f}万</span>"
            f"{mark}")
        self._info_bar.setTextFormat(QtCore.Qt.TextFormat.RichText)
    # ── Measure tool methods ──────────────────────────────────────────
    def _on_measure_toggle(self, checked: bool) -> None:
        """Toggle measure mode using MeasureTool."""
        if not hasattr(self, '_measure_tool') or self._measure_tool is None:
            self._measure_tool = MeasureTool(self._main_plot, self._bars, self._dates)
        self._measure_tool.set_active(checked)
