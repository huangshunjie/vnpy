"""image.png
market_behavior/ui/kline_view.py  —  K线图 Tab
"""
from __future__ import annotations
from typing import List, TYPE_CHECKING

import pyqtgraph as pg
from pyqtgraph import GraphicsObject

from vnpy.trader.ui import QtWidgets, QtCore, QtGui
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
    def __init__(self, bars: list):
        super().__init__()
        self._bars = bars
        self._pic  = QtGui.QPicture()
        self._draw()

    def _draw(self) -> None:
        p = QtGui.QPainter(self._pic)
        w = 0.35
        for i, (o, h, l, c) in enumerate(self._bars):
            # 开高低收完全相等 → 蓝色横线（停牌/无波动）
            if o == h == l == c:
                color = QtGui.QColor(_BLU)
                p.setPen(pg.mkPen(color, width=2))
                p.drawLine(QtCore.QPointF(i - w, c), QtCore.QPointF(i + w, c))
                continue
            if c > o:
                color = QtGui.QColor(_C_UP)    # 阳线（涨）
            elif c < o:
                color = QtGui.QColor(_C_DN)    # 阴线（跌）
            else:
                color = QtGui.QColor(_C_FLAT)  # 平盘/十字星（有上下影线）
            p.setPen(pg.mkPen(color, width=1))
            p.setBrush(pg.mkBrush(color))
            p.drawLine(QtCore.QPointF(i, l), QtCore.QPointF(i, h))
            top = max(o, c); bot = min(o, c)
            p.drawRect(QtCore.QRectF(i - w, bot, w * 2, max(top - bot, 0.001)))
        p.end()

    def paint(self, p, *_): p.drawPicture(0, 0, self._pic)
    def boundingRect(self): return QtCore.QRectF(self._pic.boundingRect())


class VolumeItem(GraphicsObject):
    def __init__(self, volumes: list, closes: list):
        super().__init__()
        self._vols   = volumes
        self._closes = closes
        self._pic    = QtGui.QPicture()
        self._draw()

    def _draw(self) -> None:
        p = QtGui.QPainter(self._pic)
        w = 0.35
        for i, vol in enumerate(self._vols):
            if i == 0:
                up = True
            else:
                if self._closes[i] > self._closes[i - 1]:
                    up = True
                elif self._closes[i] < self._closes[i - 1]:
                    up = False
                else:
                    up = None  # flat
            if up is True:
                color = QtGui.QColor(_C_UP)
            elif up is False:
                color = QtGui.QColor(_C_DN)
            else:
                color = QtGui.QColor(_C_FLAT)
            p.setPen(pg.mkPen(color, width=1))
            p.setBrush(pg.mkBrush(color))
            p.drawRect(QtCore.QRectF(i - w, 0, w * 2, vol))
        p.end()

    def paint(self, p, *_): p.drawPicture(0, 0, self._pic)
    def boundingRect(self): return QtCore.QRectF(self._pic.boundingRect())


class DateAxis(pg.AxisItem):
    def __init__(self, dates: list, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._dates = dates

    def tickStrings(self, values, scale, spacing):
        out = []
        for v in values:
            i = int(v)
            out.append(self._dates[i] if 0 <= i < len(self._dates) else "")
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
        self._info_bar.setMinimumHeight(24)
        self._info_bar.setStyleSheet(
            f"color:{_MUT};font-size:13px;background:{_PANEL};"
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

        # 更新 X 轴日期
        ax = DateAxis(self._dates, orientation="bottom")
        ax.setTextPen(_MUT)
        self._main_plot.setAxisItems({"bottom": ax})
        ax_v = DateAxis(self._dates, orientation="bottom")
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

        # MA 均线（动态周期，来自工具栏输入框）
        for period, color, enabled in self._ma_flags:
            if enabled and n >= period:
                ma = [float(np.mean(closes[max(0, i-period+1):i+1]))
                      for i in range(n)]
                self._main_plot.plot(
                    list(range(n)), ma,
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
        self._build_ui()

    def _build_ui(self) -> None:
        self.setStyleSheet(f"background:{_BG};")
        root = QtWidgets.QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # 工具栏
        toolbar = QtWidgets.QWidget()
        toolbar.setFixedHeight(46)
        toolbar.setStyleSheet(
            f"background:{_PANEL};border-bottom:1px solid {_BORD};")
        tl = QtWidgets.QHBoxLayout(toolbar)
        tl.setContentsMargins(14, 0, 14, 0)
        tl.setSpacing(10)

        tl.addWidget(_lbl("K线图  Chart", _MAV, 14, True))

        tl.addWidget(_lbl("股票代码：", _MUT))
        self._sym_edit = QtWidgets.QLineEdit()
        self._sym_edit.setFixedWidth(110)
        self._sym_edit.setPlaceholderText("如 000938")
        self._sym_edit.setStyleSheet(
            f"background:{_PAN2};color:{_FG};border:1px solid {_BORD};"
            f"border-radius:4px;padding:3px 8px;font-size:14px;")
        self._sym_edit.returnPressed.connect(self._on_manual_load)
        tl.addWidget(self._sym_edit)

        load_btn = QtWidgets.QPushButton("加载")
        load_btn.setFixedSize(64, 28)
        load_btn.setStyleSheet(
            f"background:{_BLU};color:#11111b;border:none;"
            f"border-radius:4px;font-size:14px;font-weight:bold;")
        load_btn.clicked.connect(self._on_manual_load)
        tl.addWidget(load_btn)

        sep = QtWidgets.QFrame()
        sep.setFrameShape(QtWidgets.QFrame.Shape.VLine)
        sep.setStyleSheet(f"color:{_BORD};")
        tl.addWidget(sep)

        # K线周期选择
        tl.addWidget(_lbl('周期:', _MUT))
        self._interval_cb = QtWidgets.QComboBox()
        self._interval_cb.setFixedWidth(70)
        self._interval_cb.setStyleSheet('''
            QComboBox {
                background:#11111b;
                color:#cdd6f4;
                border:1px solid #45475a;
                border-radius:3px;
                padding:2px 4px;
                font-size:12px;
                min-height:22px;
            }
            QComboBox::drop-down {
                border:none;
            }
            QComboBox::down-arrow {
                width:8px;
                height:8px;
            }
        ''')
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

        sep = QtWidgets.QFrame()
        sep.setFrameShape(QtWidgets.QFrame.Shape.VLine)
        sep.setStyleSheet(f"color:{_BORD};")
        tl.addWidget(sep)

        tl.addWidget(_lbl('MA:', _MUT))
        _edit_style = ('background:#11111b;color:#cdd6f4;border:1px solid #45475a;'
                       'border-radius:3px;padding:1px 4px;font-size:13px;')
        _chk_style  = 'font-size:14px;background:transparent;'
        self._ma_inputs  = []
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
            chk.setStyleSheet(f'color:{color};{_chk_style}')
            chk.stateChanged.connect(self._on_ma_toggle)
            edt = QtWidgets.QLineEdit(default)
            edt.setFixedWidth(34)
            edt.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
            edt.setStyleSheet(f'color:{color};{_edit_style}')
            edt.editingFinished.connect(self._on_ma_toggle)
            tl.addWidget(chk)
            tl.addWidget(edt)
            self._ma_inputs.append(edt)
            self._ma_enabled.append(chk)

        sep2 = QtWidgets.QFrame()
        sep2.setFrameShape(QtWidgets.QFrame.Shape.VLine)
        sep2.setStyleSheet('color:#45475a;')
        tl.addWidget(sep2)

        self._candle_chk = QtWidgets.QCheckBox('K线')
        self._candle_chk.setChecked(True)
        self._candle_chk.setStyleSheet(f'color:{_C_UP};font-size:14px;background:transparent;')
        self._candle_chk.stateChanged.connect(self._on_ma_toggle)
        tl.addWidget(self._candle_chk)

        self._vol_chk = QtWidgets.QCheckBox('成交量')
        self._vol_chk.setChecked(True)
        self._vol_chk.setStyleSheet(f'color:{_YLW};font-size:14px;background:transparent;')
        self._vol_chk.stateChanged.connect(self._on_vol_toggle)
        tl.addWidget(self._vol_chk)

        self._trig_chk = QtWidgets.QCheckBox('触发信号')
        self._trig_chk.setChecked(True)
        self._trig_chk.setStyleSheet('color:#c084fc;font-size:14px;background:transparent;')
        self._trig_chk.stateChanged.connect(self._on_ma_toggle)
        tl.addWidget(self._trig_chk)

        sep3 = QtWidgets.QFrame()
        sep3.setFrameShape(QtWidgets.QFrame.Shape.VLine)
        sep3.setStyleSheet('color:#45475a;')
        tl.addWidget(sep3)

        self._fullscreen_btn = QtWidgets.QPushButton('⛶ 全屏')
        self._fullscreen_btn.setFixedHeight(28)
        self._fullscreen_btn.setStyleSheet(
            'background:#fab387;color:#11111b;border:none;'
            'border-radius:4px;font-size:13px;font-weight:bold;padding:0 12px;')
        self._fullscreen_btn.clicked.connect(self._on_fullscreen)
        tl.addWidget(self._fullscreen_btn)

        tl.addStretch()
        self._title_lbl = _lbl("未选择股票", _MUT, 14)
        tl.addWidget(self._title_lbl)

        root.addWidget(toolbar)

        # 图表主体
        self._chart = KlineChartWidget()
        root.addWidget(self._chart, 1)

        # 底部图例栏
        legend = QtWidgets.QWidget()
        legend.setFixedHeight(28)
        legend.setStyleSheet(
            f"background:{_PANEL};border-top:1px solid {_BORD};")
        ll = QtWidgets.QHBoxLayout(legend)
        ll.setContentsMargins(14, 0, 14, 0)
        ll.setSpacing(18)
        ll.addWidget(_lbl("▲ 买入信号", _GRN, 13))
        ll.addWidget(_lbl("▼ 卖出信号", _RED, 13))
        ll.addWidget(_lbl("■ 阳线（涨）", _C_UP, 13))
        ll.addWidget(_lbl("■ 阴线（跌）", _C_DN, 13))
        ll.addWidget(_lbl("— MA5",  _YLW, 13))
        ll.addWidget(_lbl("— MA20", _BLU, 13))
        ll.addWidget(_lbl("— MA60", _MAV, 13))
        ll.addStretch()
        self._trig_count_lbl = _lbl("", _MUT, 13)
        ll.addWidget(self._trig_count_lbl)

        # 触发点跳转按钮
        self._prev_btn = QtWidgets.QPushButton('< 上一个')
        self._prev_btn.setFixedHeight(22)
        self._prev_btn.setStyleSheet(
            'background:#cba6f7;color:#11111b;border:none;'
            'border-radius:4px;font-size:13px;font-weight:bold;padding:0 10px;')
        self._prev_btn.clicked.connect(lambda: self._chart.jump_to_trigger(-1))
        ll.addWidget(self._prev_btn)
        self._next_btn = QtWidgets.QPushButton('下一个 >')
        self._next_btn.setFixedHeight(22)
        self._next_btn.setStyleSheet(
            'background:#89b4fa;color:#11111b;border:none;'
            'border-radius:4px;font-size:13px;font-weight:bold;padding:0 10px;')
        self._next_btn.clicked.connect(lambda: self._chart.jump_to_trigger(+1))
        ll.addWidget(self._next_btn)
        self._prev_btn.setVisible(False)
        self._next_btn.setVisible(False)
        root.addWidget(legend)

    # ── 公开接口 ─────────────────────────────────────────────────────

    def show_symbol(self, symbol: str, trigger_dates: list = None,
                    buy_dates: list = None, sell_dates: list = None) -> None:
        """
        显示 K 线图并标记信号。
        buy_dates:  买入信号日期列表 ['2026-03-25', ...]
        sell_dates: 卖出信号日期列表 ['2026-05-10', ...]
        trigger_dates: 兼容旧接口，所有触发日期（当 buy/sell_dates 未提供时作为买入处理）
        """
        self._current_symbol = symbol
        self._sym_edit.setText(symbol)
        bars = self._load_bars(symbol)
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
        # 对于日线，key = 'YYYY-MM-DD'；对于分钟线，key = 'YYYY-MM-DD HH:MM'
        date_to_idx = {}
        date_to_idx_10 = {}  # 仅保存前10字符也做一份索引用于兼容
        for i, b in enumerate(bars):
            dt = b.datetime
            if dt.hour == 0 and dt.minute == 0:
                key = dt.strftime('%Y-%m-%d')
                date_to_idx[key] = i
            else:
                key = dt.strftime('%Y-%m-%d %H:%M')
                date_to_idx[key] = i
                # 同时保存YYYY-MM-DD用于兼容旧格式
                key_10 = dt.strftime('%Y-%m-%d')
                date_to_idx_10[key_10] = i

        # 解析买入/卖出日期，标准化日期格式
        def normalize_date(d: str) -> str:
            """标准化日期字符串：去除空白，截取到对应长度"""
            d = d.strip()
            if len(d) >= 16 and ':' in d:
                # 已经是YYYY-MM-DD HH:MM格式，保持原样
                return d[:16]
            elif len(d) >= 10:
                # 只有YYYY-MM-DD
                return d[:10]
            return d

        buy_dates  = [normalize_date(d) for d in (buy_dates or [])]
        sell_dates = [normalize_date(d) for d in (sell_dates or [])]

        # 兼容旧接口：如果 buy_dates/sell_dates 都为空但 trigger_dates 有值，
        # 则全部当作买入信号
        if not buy_dates and not sell_dates and trigger_dates:
            buy_dates = [normalize_date(d) for d in trigger_dates]

        # 尝试匹配，如果精确匹配失败则回退到10字符匹配
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

        # 统计信息
        parts = []
        if buy_indices:
            parts.append(f"买入 {len(buy_indices)}")
        if sell_indices:
            parts.append(f"卖出 {len(sell_indices)}")
        self._trig_count_lbl.setText(" | ".join(parts) if parts else "")

        self._prev_btn.setVisible(total_cnt > 0)
        self._next_btn.setVisible(total_cnt > 0)
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
        _edit_style = ('background:#11111b;color:#cdd6f4;border:1px solid #45475a;'
                       'border-radius:3px;padding:1px 4px;font-size:12px;')
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
            chk.setStyleSheet(f'color:{color};{_chk_style}')
            edt = QtWidgets.QLineEdit(init_period)
            edt.setFixedWidth(34)
            edt.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
            edt.setStyleSheet(f'color:{color};{_edit_style}')
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

    def _redraw(self) -> None:
        self._main_plot.clear()
        self._vol_plot.clear()
        if not self._bars:
            return

        import numpy as np
        n = len(self._bars)
        closes = [b[3] for b in self._bars]

        ax = DateAxis(self._dates, orientation="bottom")
        ax.setTextPen(_MUT)
        self._main_plot.setAxisItems({"bottom": ax})
        ax_v = DateAxis(self._dates, orientation="bottom")
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

        for period, color, enabled in self._ma_flags:
            if enabled and n >= period:
                ma = [float(np.mean(closes[max(0, i-period+1):i+1]))
                      for i in range(n)]
                self._main_plot.plot(list(range(n)), ma,
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
