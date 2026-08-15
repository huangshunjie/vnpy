"""
strategy_condition/ui/widget.py
主窗口 — Phase 6 完整实现
三栏布局：条件库 | 策略树编辑器+Tab切换 | 参数设置
"""
from __future__ import annotations
import sys
import traceback
from typing import Optional

from vnpy.trader.ui import QtWidgets, QtCore, QtGui
from vnpy.trader.engine import MainEngine
from vnpy.trader.constant import Interval


# ── 全局异常钩子：防止未捕获异常导致静默崩溃 ──────────────────────────
def _global_exception_hook(exc_type, exc_value, exc_tb):
    """安装为 sys.excepthook，确保所有未处理异常弹出可见的错误对话框"""
    tb_str = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))
    print(f"[SCE] 未捕获异常:\n{tb_str}", flush=True)
    try:
        app = QtWidgets.QApplication.instance()
        if app:
            msg = QtWidgets.QMessageBox()
            msg.setIcon(QtWidgets.QMessageBox.Icon.Critical)
            msg.setWindowTitle("Strategy Condition Engine - 未捕获异常")
            msg.setText(f"{exc_type.__name__}: {exc_value}")
            msg.setDetailedText(tb_str)
            msg.exec()
    except Exception:
        pass


# 安装全局钩子（仅替换一次）
if not getattr(sys, '_sce_excepthook_installed', False):
    sys.excepthook = _global_exception_hook
    sys._sce_excepthook_installed = True

from ..constant import (NodeOp, ConditionCategory, ConditionIndicator,
                         SignalSource)
from ..core.condition_tree import ConditionNode
from ..core.strategy import Strategy, StrategyMeta, StrategyParams, empty_strategy
from ..templates.builtin import get_all_templates
from .condition_editor import ConditionTreeEditor, _COND_META
from .signal_view import SignalView
from .backtest_view import BacktestView
from .kline_view import KlineViewTab
# -- builtin stock pools --
_POOL_CSI300 = [
    "000001.SZSE","000002.SZSE","000063.SZSE","000100.SZSE","000333.SZSE",
    "000651.SZSE","000858.SZSE","002001.SZSE","002415.SZSE","002594.SZSE",
    "600000.SSE","600009.SSE","600016.SSE","600028.SSE","600030.SSE",
    "600031.SSE","600036.SSE","600048.SSE","600050.SSE","600104.SSE",
    "600196.SSE","600276.SSE","600309.SSE","600436.SSE","600519.SSE",
    "600547.SSE","600585.SSE","600690.SSE","600900.SSE","601006.SSE",
    "601012.SSE","601088.SSE","601166.SSE","601169.SSE","601186.SSE",
    "601211.SSE","601318.SSE","601328.SSE","601390.SSE","601601.SSE",
    "601628.SSE","601633.SSE","601668.SSE","601688.SSE","601728.SSE",
    "601766.SSE","601857.SSE","601888.SSE","601939.SSE","601985.SSE",
]
_POOL_CSI500 = [
    "000021.SZSE","000400.SZSE","000425.SZSE","000568.SZSE","000617.SZSE",
    "000661.SZSE","000725.SZSE","000776.SZSE","000895.SZSE","000938.SZSE",
    "001979.SZSE","002050.SZSE","002142.SZSE","002180.SZSE","002241.SZSE",
    "002271.SZSE","002304.SZSE","002352.SZSE","002371.SZSE","002460.SZSE",
    "600015.SSE","600018.SSE","600019.SSE","600025.SSE","600060.SSE",
    "600079.SSE","600109.SSE","600115.SSE","600118.SSE","600153.SSE",
    "600176.SSE","600188.SSE","600219.SSE","600233.SSE","600256.SSE",
    "600332.SSE","600346.SSE","600362.SSE","600372.SSE","600406.SSE",
]
_POOL_STAR = [
    "688001.SSE","688002.SSE","688003.SSE","688008.SSE","688009.SSE",
    "688011.SSE","688012.SSE","688016.SSE","688017.SSE","688018.SSE",
    "688019.SSE","688020.SSE","688021.SSE","688025.SSE","688026.SSE",
    "688041.SSE","688046.SSE","688047.SSE","688048.SSE","688050.SSE",
]



class _BarAdapter:
    """Wraps VeighNa BarData to expose .open/.high/.low/.close/.volume/.dt
    Also provides .open_price/.high_price/.low_price/.close_price/.datetime
    aliases for compatibility with KlineChartWidget."""
    __slots__ = ("_b",)
    def __init__(self, bar) -> None: self._b = bar
    @property
    def open(self)   -> float: return self._b.open_price
    @property
    def high(self)   -> float: return self._b.high_price
    @property
    def low(self)    -> float: return self._b.low_price
    @property
    def close(self)  -> float: return self._b.close_price
    @property
    def volume(self) -> float: return float(self._b.volume)
    @property
    def dt(self):              return self._b.datetime
    # Aliases for KlineChartWidget compatibility
    @property
    def open_price(self) -> float: return self._b.open_price
    @property
    def high_price(self) -> float: return self._b.high_price
    @property
    def low_price(self) -> float: return self._b.low_price
    @property
    def close_price(self) -> float: return self._b.close_price
    @property
    def datetime(self): return self._b.datetime

_BG   = "#1e1e2e"; _PANEL = "#181825"; _PAN2 = "#11111b"
_BORD = "#45475a"; _FG   = "#cdd6f4"; _MUT  = "#6c7086"
_BLU  = "#89b4fa"; _GRN  = "#a6e3a1"; _YLW  = "#f9e2af"
_RED  = "#f38ba8"; _MAV  = "#cba6f7"; _PNK  = "#f5c2e7"

_SPIN_SS = (f"QDoubleSpinBox,QSpinBox{{background:{_PAN2};color:{_FG};"
            f"border:1px solid {_BORD};border-radius:4px;"
            f"padding:3px 6px;font-size:13px;}}")
_EDIT_SS = (f"QLineEdit{{background:{_PAN2};color:{_FG};"
            f"border:1px solid {_BORD};border-radius:4px;"
            f"padding:4px 8px;font-size:13px;}}")
_COMBO_SS = (f"QComboBox{{background:{_PAN2};color:{_FG};"
             f"border:1px solid {_BORD};border-radius:4px;"
             f"padding:4px 10px;font-size:13px;}}"
             f"QComboBox::drop-down{{border:none;width:20px;}}"
             f"QComboBox QAbstractItemView{{background:{_PAN2};color:{_FG};"
             f"selection-background-color:{_BLU};}}")


def _lbl(text: str, color: str = _FG, size: int = 13,
         bold: bool = False) -> QtWidgets.QLabel:
    w = QtWidgets.QLabel(text)
    w.setStyleSheet(
        f"color:{color};font-size:{size}px;"
        f"font-weight:{'bold' if bold else 'normal'};"
        f"background:transparent;border:none;")
    return w


def _hline() -> QtWidgets.QFrame:
    f = QtWidgets.QFrame()
    f.setFrameShape(QtWidgets.QFrame.Shape.HLine)
    f.setStyleSheet(f"border:none;border-top:1px solid {_BORD};")
    return f


def _vline() -> QtWidgets.QFrame:
    f = QtWidgets.QFrame()
    f.setFrameShape(QtWidgets.QFrame.Shape.VLine)
    f.setStyleSheet(f"border:none;border-left:1px solid {_BORD};")
    return f


def _btn(text: str, color: str = _BLU, w: int = 0) -> QtWidgets.QPushButton:
    b = QtWidgets.QPushButton(text)
    ss = (f"QPushButton{{background:{color};color:#1e1e2e;border:none;"
          f"border-radius:4px;padding:7px 16px;font-size:13px;font-weight:bold;}}"
          f"QPushButton:hover{{background:{color};opacity:0.85;}}"
          f"QPushButton:disabled{{background:{_BORD};color:{_MUT};}}")
    b.setStyleSheet(ss)
    if w:
        b.setFixedWidth(w)
    return b


# 条件库分类配置
_COND_LIBRARY = [
    ("📈 趋势  Trend", [
        ConditionIndicator.MA_SLOPE,
        ConditionIndicator.WEEKLY_MA_SLOPE,
        ConditionIndicator.MA_ALIGNMENT,
        ConditionIndicator.NEW_HIGH_N,
        ConditionIndicator.TREND_STRENGTH,
        ConditionIndicator.PRICE_ABOVE_MA,
        ConditionIndicator.TREND_DAYS,
        ConditionIndicator.TREND_INTACT,
        ConditionIndicator.MA_BINDONG,
        ConditionIndicator.TREND_SCORE,
    ]),
    ("🔄 回调  Pullback", [
        ConditionIndicator.PULLBACK_FROM_HIGH,
        ConditionIndicator.PULLBACK_PCT,
        ConditionIndicator.PULLBACK_TO_MA,
        ConditionIndicator.PULLBACK_TO_MA5,
        ConditionIndicator.PULLBACK_TO_MA10,
        ConditionIndicator.PULLBACK_TO_MA20,
        ConditionIndicator.PULLBACK_TO_MA30,
        ConditionIndicator.FIRST_PULLBACK,
        ConditionIndicator.SHRINK_PULLBACK,
        ConditionIndicator.STRONG_PULLBACK_SCORE,
    ]),
    ("⚡ 动量  Momentum", [
        ConditionIndicator.MACD_GOLDEN,
        ConditionIndicator.MACD_DEATH,
        ConditionIndicator.RSI_RANGE,
        ConditionIndicator.RETURN_N_DAYS,
    ]),
    ("📊 成交量  Volume", [
        ConditionIndicator.VOLUME_PRICE_UP,
        ConditionIndicator.VOLUME_RATIO,
        ConditionIndicator.VOLUME_SHRINK,
        ConditionIndicator.VOLUME_UP_PHASE,
        ConditionIndicator.VOLUME_LAYER,
        ConditionIndicator.VOLUME_YIN_FILTER,
        ConditionIndicator.FUND_INTENSITY,
    ]),
    ("🕯 K线行为  Kline", [
        ConditionIndicator.CONTINUOUS_RISE,
        ConditionIndicator.LIMIT_UP_COUNT,
        ConditionIndicator.BIG_YANG_COUNT,
        ConditionIndicator.KLINE_STRENGTH,
        ConditionIndicator.KLINE_YIN,
        ConditionIndicator.KLINE_YANG,
        ConditionIndicator.KLINE_SHRINK_YIN,
        ConditionIndicator.KLINE_VOL_YIN,
        ConditionIndicator.KLINE_LONG_LOWER,
        ConditionIndicator.KLINE_DOJI,
        ConditionIndicator.KLINE_BIG_YANG,
        ConditionIndicator.KLINE_LIMIT_UP,
    ]),
    ("💪 强势股  Strength", [
        ConditionIndicator.STRENGTH_RETURN_N,
        ConditionIndicator.STRENGTH_LIMIT_UP_COUNT,
        ConditionIndicator.STRENGTH_BIG_YANG_COUNT,
        ConditionIndicator.STRENGTH_VOL_BREAK,
        ConditionIndicator.STRENGTH_SCORE,
    ]),
    ("📐 偏离  Deviation", [
        ConditionIndicator.DEV_MA5,
        ConditionIndicator.DEV_MA10,
        ConditionIndicator.DEV_MA20,
        ConditionIndicator.DEV_MA10_MA20,
        ConditionIndicator.DEV_OVERBOUGHT,
    ]),
    ("🌍 市场环境  Market", [
        ConditionIndicator.MARKET_INDEX_TREND,
        ConditionIndicator.MARKET_RISK,
    ]),
    ("🌊 波动  Volatility", [
        ConditionIndicator.ATR_RATIO,
        ConditionIndicator.BOLL_WIDTH,
    ]),
    ("⏰ 时间  Time", [
        ConditionIndicator.TIME_OF_DAY,
    ]),
    ("🚪 卖出  Exit", [
        ConditionIndicator.TRAILING_STOP,
        ConditionIndicator.STOP_LOSS,
        ConditionIndicator.TAKE_PROFIT,
        ConditionIndicator.MA_BREAK_DOWN,
        ConditionIndicator.MACD_DEATH_SELL,
        ConditionIndicator.MAX_HOLD_DAYS,
    ]),
    ("🎯 评分  Score", [
        ConditionIndicator.SCORE_NODE,
    ]),
]


class StrategyConditionWidget(QtWidgets.QWidget):
    """
    量化策略条件引擎主窗口。
    三栏布局：条件库 | 策略树编辑器(买/卖Tab) | 参数设置
    """

    def __init__(self, main_engine: MainEngine, event_engine) -> None:
        super().__init__()
        self._main_engine  = main_engine
        self._event_engine = event_engine
        self._engine       = main_engine.get_engine("StrategyCondition")
        self._strategy: Optional[Strategy] = None
        self._last_bars_dict: dict = {}  # 保存最近一次加载的K线数据

        # ── 性能缓存 ────────────────────────────────────────────────────
        # 第一层：K 线数据缓存 {(symbol, interval, n_bars): [bar, ...]}
        self._bars_cache: dict = {}
        self._bars_cache_key: tuple = ()  # 当前缓存的 key

        # 第二层：快照缓存 {(symbol, strategy_hash): (snapshots, buy_dates, sell_dates)}
        self._snapshot_cache: dict = {}
        self._snapshot_cache_key: tuple = ()

        # 第三层：Monitor 异步计算线程
        self._monitor_worker: Optional[QtCore.QThread] = None

        # dirty 标记：策略变更时置 True，下次切换到 Monitor 时重新计算
        self._monitor_dirty: bool = True

        self._init_ui()
        self._load_builtin_templates()

    # ── 初始化 ────────────────────────────────────────────────────────

    def _init_ui(self) -> None:
        self.setWindowTitle("Strategy Condition Engine  量化策略条件引擎")
        self.setStyleSheet(
            f"background:{_BG};color:{_FG};"
            f"font-family:微软雅黑,Arial,sans-serif;")
        self.resize(1500, 920)

        root = QtWidgets.QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        splitter = QtWidgets.QSplitter(QtCore.Qt.Orientation.Horizontal)
        splitter.setHandleWidth(4)
        splitter.setStyleSheet(
            "QSplitter::handle{background:#313244;}"
            "QSplitter::handle:hover{background:#89b4fa;}"
        )
        self._left_panel = self._build_left()
        self._right_panel = self._build_right()
        splitter.addWidget(self._left_panel)
        splitter.addWidget(self._build_mid())
        splitter.addWidget(self._right_panel)
        splitter.setStretchFactor(0, 2)
        splitter.setStretchFactor(1, 5)
        splitter.setStretchFactor(2, 3)
        splitter.setSizes([240, 760, 380])
        # 允许折叠左栏和右栏（拖到边缘可完全隐藏）
        splitter.setCollapsible(0, True)
        splitter.setCollapsible(1, False)
        splitter.setCollapsible(2, True)
        self._splitter = splitter
        root.addWidget(splitter)

        # ── 快捷键：切换条件库/参数面板 ──────────────────────────────
        from vnpy.trader.ui import QtGui as _qg
        sc_left = QtGui.QShortcut(QtGui.QKeySequence("Ctrl+L"), self)
        sc_left.activated.connect(self._toggle_left_panel)
        sc_right = QtGui.QShortcut(QtGui.QKeySequence("Ctrl+R"), self)
        sc_right.activated.connect(self._toggle_right_panel)

    # ── 左栏：条件库 ──────────────────────────────────────────────────

    def _build_left(self) -> QtWidgets.QWidget:
        w = QtWidgets.QWidget()
        w.setStyleSheet(f"background:{_PANEL};")
        v = QtWidgets.QVBoxLayout(w)
        v.setContentsMargins(14, 14, 14, 14)
        v.setSpacing(8)
        v.addWidget(_lbl("条件库  Condition Library", _YLW, 15, True))
        v.addWidget(_hline())

        self._lib_tree = QtWidgets.QTreeWidget()
        self._lib_tree.setHeaderHidden(True)
        self._lib_tree.setStyleSheet(
            f"QTreeWidget{{background:{_PAN2};color:{_FG};"
            f"border:1px solid {_BORD};border-radius:4px;font-size:13px;}}"
            f"QTreeWidget::item{{padding:4px 2px;}}"
            f"QTreeWidget::item:hover{{background:#313244;}}"
            f"QTreeWidget::item:selected{{background:{_BLU};color:#1e1e2e;}}"
            f"QScrollBar:vertical{{background:{_PAN2};width:8px;border:none;}}"
            f"QScrollBar::handle:vertical{{background:{_BORD};border-radius:4px;}}"
        )
        _CAT_COLORS = {
            ConditionCategory.TREND: _GRN,
            ConditionCategory.PULLBACK: _BLU,
            ConditionCategory.MOMENTUM: _YLW,
            ConditionCategory.VOLUME: _MAV,
            ConditionCategory.KLINE: _PNK,
            ConditionCategory.VOLATILITY: "#94e2d5",
            ConditionCategory.TIME: "#f9e2af",
            ConditionCategory.EXIT: _RED,
        }
        for cat_name, indicators in _COND_LIBRARY:
            parent_item = QtWidgets.QTreeWidgetItem([cat_name])
            parent_item.setForeground(0, QtGui.QColor(_YLW))
            parent_item.setFont(0, self._bold_font())
            for ind in indicators:
                if ind not in _COND_META:
                    continue
                display, _, _ = _COND_META[ind]
                child = QtWidgets.QTreeWidgetItem([f"  {display}"])
                child.setData(0, QtCore.Qt.ItemDataRole.UserRole, ind)
                # 按 indicator category 着色
                meta_cond = _COND_META[ind]
                # 找 category from indicator name range
                if "EXIT" in ind.value or ind.value in (
                    "STOP_LOSS","TAKE_PROFIT","TRAILING_STOP",
                    "MAX_HOLD_DAYS","MA_BREAK_DOWN","MACD_DEATH_SELL"):
                    child.setForeground(0, QtGui.QColor(_RED))
                elif ind.value in ("MA_SLOPE","WEEKLY_MA_SLOPE",
                                   "MA_ALIGNMENT","NEW_HIGH_N"):
                    child.setForeground(0, QtGui.QColor(_GRN))
                elif ind.value in ("MACD_GOLDEN","MACD_DEATH",
                                   "RSI_RANGE","RETURN_N_DAYS"):
                    child.setForeground(0, QtGui.QColor(_YLW))
                elif ind.value in ("VOLUME_RATIO","VOLUME_PRICE_UP","VOLUME_SHRINK"):
                    child.setForeground(0, QtGui.QColor(_MAV))
                elif ind.value in ("PULLBACK_PCT","PULLBACK_FROM_HIGH","PULLBACK_TO_MA"):
                    child.setForeground(0, QtGui.QColor(_BLU))
                elif ind.value == "TIME_OF_DAY":
                    child.setForeground(0, QtGui.QColor("#f9e2af"))
                else:
                    child.setForeground(0, QtGui.QColor(_FG))
                parent_item.addChild(child)
            self._lib_tree.addTopLevelItem(parent_item)

        self._lib_tree.expandAll()
        self._lib_tree.itemDoubleClicked.connect(self._on_lib_double_click)
        v.addWidget(self._lib_tree)
        v.addWidget(_lbl("双击添加到当前策略树", _MUT, 11))
        return w

    # ── 中栏：策略树编辑器 + 结果 Tab ─────────────────────────────────

    def _build_mid(self) -> QtWidgets.QWidget:
        w = QtWidgets.QWidget()
        w.setStyleSheet(f"background:{_BG};")
        w.setMinimumWidth(400)  # 允许中间栏缩小，让右栏可以向左扩展
        v = QtWidgets.QVBoxLayout(w)
        v.setContentsMargins(16, 14, 16, 14)
        v.setSpacing(8)

        # 标题行：策略选择 + 面板显示控制 + 操作按钮
        title_row = QtWidgets.QHBoxLayout()
        title_row.addWidget(_lbl("策略  Strategy", _YLW, 15, True))
        
        # 面板显示控制复选框
        title_row.addSpacing(20)
        self._show_left_cb = QtWidgets.QCheckBox("条件库")
        self._show_left_cb.setChecked(True)
        self._show_left_cb.setStyleSheet(
            f"QCheckBox{{color:{_FG};font-size:12px;background:transparent;}}"
            f"QCheckBox::indicator{{width:14px;height:14px;"
            f"border:1px solid {_BORD};border-radius:3px;background:{_PAN2};}}"
            f"QCheckBox::indicator:checked{{background:{_BLU};"
            f"border-color:{_BLU};}}"
        )
        self._show_left_cb.stateChanged.connect(self._on_left_cb_changed)
        title_row.addWidget(self._show_left_cb)
        
        title_row.addSpacing(12)
        self._show_right_cb = QtWidgets.QCheckBox("参数面板")
        self._show_right_cb.setChecked(True)
        self._show_right_cb.setStyleSheet(
            f"QCheckBox{{color:{_FG};font-size:12px;background:transparent;}}"
            f"QCheckBox::indicator{{width:14px;height:14px;"
            f"border:1px solid {_BORD};border-radius:3px;background:{_PAN2};}}"
            f"QCheckBox::indicator:checked{{background:{_BLU};"
            f"border-color:{_BLU};}}"
        )
        self._show_right_cb.stateChanged.connect(self._on_right_cb_changed)
        title_row.addWidget(self._show_right_cb)
        
        title_row.addStretch()
        self._strategy_cb = QtWidgets.QComboBox()
        self._strategy_cb.setStyleSheet(_COMBO_SS)
        self._strategy_cb.setMinimumWidth(200)
        self._strategy_cb.currentIndexChanged.connect(self._on_strategy_changed)
        title_row.addWidget(self._strategy_cb)
        v.addLayout(title_row)
        v.addWidget(_hline())

        # 买入/卖出 Tab 切换
        self._tab = QtWidgets.QTabWidget()
        self._tab.setStyleSheet(
            f"QTabWidget::pane{{background:{_BG};border:1px solid {_BORD};"
            f"border-radius:4px;}}"
            f"QTabBar::tab{{background:{_PAN2};color:{_MUT};"
            f"padding:8px 20px;font-size:13px;border:1px solid {_BORD};"
            f"border-bottom:none;border-radius:4px 4px 0 0;margin-right:2px;}}"
            f"QTabBar::tab:selected{{background:{_BLU};color:#1e1e2e;"
            f"font-weight:bold;}}"
            f"QTabBar::tab:hover{{background:#313244;color:{_FG};}}"
        )

        # 买入条件 Tab
        self._buy_editor = ConditionTreeEditor(root_display_label="买入条件")
        self._buy_editor.tree_changed.connect(self._on_tree_changed)
        self._tab.addTab(self._buy_editor, "📈  买入条件  BUY")

        # 卖出条件 Tab
        self._sell_editor = ConditionTreeEditor(root_display_label="卖出条件")
        self._sell_editor.tree_changed.connect(self._on_tree_changed)
        self._tab.addTab(self._sell_editor, "🚪  卖出条件  SELL")

        # 信号结果 Tab
        self._signal_view = SignalView()
        self._signal_view.signal_selected.connect(self._on_signal_selected)
        self._tab.addTab(self._signal_view, "📋  选股结果  Signals")

        # 回测结果 Tab
        self._bt_view = BacktestView()
        self._tab.addTab(self._bt_view, "📊  回测结果  Backtest")

        # K线图 Tab
        self._kline_tab = KlineViewTab()
        self._tab.addTab(self._kline_tab, "📈  K线图  Chart")

        # 条件监控 Tab（延迟导入，避免阻塞 app 加载）
        try:
            from .condition_monitor_widget import ConditionMonitorWidget
            self._monitor_tab = ConditionMonitorWidget()
            self._monitor_tab.lifecycle_info_changed.connect(
                self._on_lifecycle_info)
            self._tab.addTab(self._monitor_tab, "🔍  条件监控  Monitor")
        except Exception as e:
            print(f"[SCE] Monitor Tab 加载失败: {e}")
            self._monitor_tab = None

        # 切换到 Monitor Tab 时，自动用 K线图当前 symbol 刷新
        self._tab.currentChanged.connect(self._on_tab_changed)

        v.addWidget(self._tab, 1)

        # 底部按钮行
        v.addWidget(_hline())
        btn_row = QtWidgets.QHBoxLayout()
        self._btn_scan   = _btn("▶  运行选股", _GRN)
        self._btn_bt     = _btn("📊  回测验证", _BLU)
        self._btn_save   = _btn("💾  保存策略", _YLW)
        self._btn_new    = _btn("＋  新建策略", _MAV)
        self._btn_rename = _btn("✏  重命名", "#94e2d5")
        self._btn_del    = _btn("🗑  删除策略", _RED)
        self._btn_scan.clicked.connect(self._on_scan)
        self._btn_bt.clicked.connect(self._on_backtest)
        self._btn_save.clicked.connect(self._on_save)
        self._btn_new.clicked.connect(self._on_new_strategy)
        self._btn_rename.clicked.connect(self._on_rename_strategy)
        self._btn_del.clicked.connect(self._on_delete_strategy)
        for b in (self._btn_scan, self._btn_bt, self._btn_save,
                  self._btn_new, self._btn_rename, self._btn_del):
            btn_row.addWidget(b)

        # 诊断信息标签（两行小字，显示在删除策略右侧）
        self._lifecycle_lbl = QtWidgets.QLabel("")
        self._lifecycle_lbl.setStyleSheet(
            f"color:{_MUT};font-size:11px;background:transparent;"
            f"border:none;padding:0 12px;")
        self._lifecycle_lbl.setWordWrap(False)
        btn_row.addWidget(self._lifecycle_lbl, 1)
        v.addLayout(btn_row)
        return w

    # ── 右栏：股票池 + 参数设置 ───────────────────────────────────────

    def _build_right(self) -> QtWidgets.QWidget:
        w = QtWidgets.QWidget()
        w.setStyleSheet(f"background:{_PANEL};")

        scroll = QtWidgets.QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet(
            f"QScrollArea{{background:{_PANEL};border:none;}}"
            f"QScrollBar:vertical{{background:{_PAN2};width:8px;border:none;}}"
            f"QScrollBar::handle:vertical{{background:{_BORD};border-radius:4px;}}"
        )
        inner = QtWidgets.QWidget()
        inner.setStyleSheet(f"background:{_PANEL};")
        v = QtWidgets.QVBoxLayout(inner)
        v.setContentsMargins(14, 14, 14, 14)
        v.setSpacing(8)

        # ── 标题和策略名称 ────────────────────────────────────────────
        v.addWidget(_lbl("参数设置  Parameters", _YLW, 15, True))
        v.addWidget(_hline())
        v.addWidget(_lbl("策略名称", _MUT, 12))
        self._name_edit = QtWidgets.QLineEdit("新策略")
        self._name_edit.setStyleSheet(_EDIT_SS)
        v.addWidget(self._name_edit)
        v.addWidget(_hline())

        # ── 两列布局容器 ──────────────────────────────────
        two_col = QtWidgets.QHBoxLayout()
        two_col.setSpacing(12)

        # ══════════════════════════════════
        # 左列：股票池 + K线设置 + 时间范围
        # ══════════════════════════════════════════════════════════════
        left_col = QtWidgets.QVBoxLayout()
        left_col.setSpacing(6)

        # ── 股票池（完整版）──
        pool_hdr = QtWidgets.QHBoxLayout()
        pool_hdr.addWidget(_lbl("股票池  Universe", _YLW, 13, True))
        pool_hdr.addStretch()
        left_col.addLayout(pool_hdr)
        self._current_pool_name = ""
        self._pool_last_update = ""

        # ━━ 市场/板块 ━━
        left_col.addWidget(_lbl("市场/板块", _MUT, 11))
        _sbtn = (f"QPushButton{{background:{_PAN2};color:{_FG};border:1px solid {_BORD};"
                 f"border-radius:4px;padding:4px 6px;font-size:10px;}}"
                 f"QPushButton:hover{{border-color:{_BLU};color:{_BLU};}}")
        exch_row = QtWidgets.QHBoxLayout()
        exch_row.setSpacing(3)
        for label, key in [("全市场","ALL"),("沪市","SSE"),("深市","SZSE"),("北交所","BSE")]:
            b = QtWidgets.QPushButton(label)
            b.setStyleSheet(_sbtn)
            b.clicked.connect(lambda checked, k=key, n=label: self._set_exchange_pool(k, n))
            exch_row.addWidget(b)
        left_col.addLayout(exch_row)
        board_row = QtWidgets.QHBoxLayout()
        board_row.setSpacing(3)
        for label in ["沪主板","科创板","深主板","创业板"]:
            b = QtWidgets.QPushButton(label)
            b.setStyleSheet(_sbtn)
            b.clicked.connect(lambda checked, n=label: self._set_board_pool(n))
            board_row.addWidget(b)
        left_col.addLayout(board_row)

        # ━━ 指数成分 ━━
        left_col.addWidget(_lbl("指数成分", _MUT, 11))
        idx_grid = QtWidgets.QGridLayout()
        idx_grid.setSpacing(4)
        for idx, (label, pool_key) in enumerate([("上证50","IDX:000016"),("沪深300","IDX:000300"),("中证500","IDX:000905"),("中证1000","IDX:000852"),("创业板指","IDX:399006")]):
            b = QtWidgets.QPushButton(label)
            b.setStyleSheet(_sbtn)
            b.clicked.connect(lambda checked, p=pool_key, n=label: self._set_index_pool(p, n))
            idx_grid.addWidget(b, idx // 3, idx % 3)
        left_col.addLayout(idx_grid)

        # 更多指数下拉框
        more_row = QtWidgets.QHBoxLayout()
        more_row.setSpacing(6)
        more_row.addWidget(_lbl("更多:", _MUT, 11))
        self._sce_index_combo = QtWidgets.QComboBox()
        self._sce_index_combo.setStyleSheet(_COMBO_SS)
        self._sce_index_combo.setFixedHeight(26)
        self._sce_index_combo.addItem("-- 选择指数 --", "")
        try:
            from vnpy.trader.index_constituents import SUPPORTED_INDICES as _ALL_IDX
            _added = {"000016","000300","000905","000852","399006"}
            for cat in ["规模指数","板块指数","风格策略","行业主题"]:
                hdr = False
                for code, info in _ALL_IDX.items():
                    if info.get("category") != cat or code in _added:
                        continue
                    if not hdr:
                        self._sce_index_combo.addItem(f"━━ {cat} ━━", "")
                        hdr = True
                    self._sce_index_combo.addItem(f"  {info['name']} ({code})", f"IDX:{code}")
        except Exception:
            pass
        self._sce_index_combo.currentIndexChanged.connect(self._on_sce_index_changed)
        more_row.addWidget(self._sce_index_combo, 1)
        left_col.addLayout(more_row)

        # ━━ 行业筛选 ━━
        left_col.addWidget(_lbl("行业筛选", _MUT, 11))
        ind_row = QtWidgets.QHBoxLayout()
        ind_row.setSpacing(6)
        self._sce_industry_combo = QtWidgets.QComboBox()
        self._sce_industry_combo.setStyleSheet(_COMBO_SS)
        self._sce_industry_combo.setFixedHeight(26)
        self._sce_industry_combo.addItem("-- 选择行业 --", "")
        try:
            from vnpy.trader.stock_pool import get_all_industries
            for ind in get_all_industries():
                self._sce_industry_combo.addItem(ind, ind)
        except Exception:
            for ind in ["银行","医药生物","电子","计算机","食品饮料","家用电器","汽车","化工"]:
                self._sce_industry_combo.addItem(ind, ind)
        self._sce_industry_combo.currentIndexChanged.connect(self._on_sce_industry_changed)
        ind_row.addWidget(self._sce_industry_combo, 1)
        left_col.addLayout(ind_row)

        # 手动输入框
        left_col.addWidget(_lbl("手动输入（逗号或换行分隔）", _MUT, 11))
        self._pool_edit = QtWidgets.QPlainTextEdit()
        self._pool_edit.setMinimumHeight(70)
        self._pool_edit.setMaximumHeight(100)
        self._pool_edit.setPlaceholderText(
            "例：\n000001.SZSE\n600519.SSE")
        self._pool_edit.setStyleSheet(
            f"QPlainTextEdit{{background:{_PAN2};color:{_FG};"
            f"border:1px solid {_BORD};border-radius:4px;"
            f"font-size:11px;padding:4px;"
            f"font-family:Consolas,Courier New,monospace;}}"
        )
        self._pool_edit.textChanged.connect(self._on_pool_changed)
        left_col.addWidget(self._pool_edit)

        # 数据源说明
        self._pool_count_lbl = _lbl(
            "数据源：VeighNa 数据库", _MUT, 10)
        self._pool_count_lbl.setWordWrap(True)
        left_col.addWidget(self._pool_count_lbl)

        left_col.addSpacing(4)
        left_col.addWidget(_hline())

        # ── K线设置 ──
        left_col.addWidget(_lbl("K线数量", _MUT, 12))
        self._nbars_sp = QtWidgets.QSpinBox()
        self._nbars_sp.setRange(0, 10000); self._nbars_sp.setValue(300)
        self._nbars_sp.setSingleStep(50); self._nbars_sp.setStyleSheet(_SPIN_SS)
        left_col.addWidget(self._nbars_sp)
        # 显示预估起始日期
        self._nbars_start_lbl = _lbl("", _MUT, 10)
        self._nbars_start_lbl.setStyleSheet("color: #888888;")
        left_col.addWidget(self._nbars_start_lbl)

        left_col.addWidget(_lbl("K线周期", _MUT, 12))
        self._interval_cb = QtWidgets.QComboBox()
        self._interval_cb.setStyleSheet(_COMBO_SS)
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
        left_col.addWidget(self._interval_cb)
        
        # 更新预估起始日期
        def update_estimate_start():
            self._update_estimated_start_date()
        self._nbars_sp.valueChanged.connect(update_estimate_start)
        self._interval_cb.currentIndexChanged.connect(update_estimate_start)

        left_col.addSpacing(4)
        left_col.addWidget(_hline())

        # ── 时间范围 ──
        left_col.addWidget(_lbl("回测时间范围", _YLW, 12, True))
        left_col.addWidget(_lbl("起始日期", _MUT, 11))
        self._date_start = QtWidgets.QLineEdit("2020-01-01")
        self._date_start.setStyleSheet(_EDIT_SS)
        left_col.addWidget(self._date_start)
        left_col.addWidget(_lbl("截止日期", _MUT, 11))
        self._date_end = QtWidgets.QLineEdit("今日")
        self._date_end.setStyleSheet(_EDIT_SS)
        left_col.addWidget(self._date_end)

        left_col.addStretch()

        # ══════════════════════════════════
        # 右列：卖出参数 + 交易成本
        # ══════════════════════════════════════════════════════════════
        right_col = QtWidgets.QVBoxLayout()
        right_col.setSpacing(6)

        # ── 卖出参数 ──
        right_col.addWidget(_lbl("卖出参数", _YLW, 12, True))

        right_col.addWidget(_lbl("最大持仓天数", _MUT, 11))
        self._hold_sp = QtWidgets.QSpinBox()
        self._hold_sp.setRange(1, 99999); self._hold_sp.setValue(120)
        self._hold_sp.setStyleSheet(_SPIN_SS)
        right_col.addWidget(self._hold_sp)

        right_col.addWidget(_lbl("冷却期（交易日）", _MUT, 11))
        self._cooldown_sp = QtWidgets.QSpinBox()
        self._cooldown_sp.setRange(0, 30); self._cooldown_sp.setValue(3)
        self._cooldown_sp.setStyleSheet(_SPIN_SS)
        right_col.addWidget(self._cooldown_sp)

        right_col.addWidget(_lbl("止损触发 (%)", _MUT, 11))
        self._sl_sp = QtWidgets.QDoubleSpinBox()
        self._sl_sp.setRange(0.0, 50.0); self._sl_sp.setValue(8.0)
        self._sl_sp.setSingleStep(0.5); self._sl_sp.setStyleSheet(_SPIN_SS)
        right_col.addWidget(self._sl_sp)

        right_col.addWidget(_lbl("止盈触发 (%)", _MUT, 11))
        self._tp_sp = QtWidgets.QDoubleSpinBox()
        self._tp_sp.setRange(0.0, 200.0); self._tp_sp.setValue(15.0)
        self._tp_sp.setSingleStep(1.0); self._tp_sp.setStyleSheet(_SPIN_SS)
        right_col.addWidget(self._tp_sp)

        right_col.addWidget(_lbl("追踪止盈回撤 (%)", _MUT, 11))
        self._trail_sp = QtWidgets.QDoubleSpinBox()
        self._trail_sp.setRange(0.0, 50.0); self._trail_sp.setValue(10.0)
        self._trail_sp.setSingleStep(1.0); self._trail_sp.setStyleSheet(_SPIN_SS)
        right_col.addWidget(self._trail_sp)

        right_col.addSpacing(4)
        right_col.addWidget(_hline())

        # ── 交易成本 ──
        right_col.addWidget(_lbl("交易成本", _YLW, 12, True))

        right_col.addWidget(_lbl("手续费率 (万)", _MUT, 11))
        self._comm_sp = QtWidgets.QDoubleSpinBox()
        self._comm_sp.setRange(0.0, 20.0); self._comm_sp.setValue(3.0)
        self._comm_sp.setSingleStep(0.5); self._comm_sp.setDecimals(1)
        self._comm_sp.setStyleSheet(_SPIN_SS)
        right_col.addWidget(self._comm_sp)

        right_col.addWidget(_lbl("印花税率 (千)", _MUT, 11))
        self._stamp_sp = QtWidgets.QDoubleSpinBox()
        self._stamp_sp.setRange(0.0, 20.0); self._stamp_sp.setValue(1.0)
        self._stamp_sp.setSingleStep(0.5); self._stamp_sp.setDecimals(1)
        self._stamp_sp.setStyleSheet(_SPIN_SS)
        right_col.addWidget(self._stamp_sp)

        right_col.addStretch()

        # 组装两列
        two_col.addLayout(left_col, 1)
        two_col.addLayout(right_col, 1)
        v.addLayout(two_col, 1)

        # ── 策略描述 ─────────────────────────────────────────────────
        v.addWidget(_hline())
        v.addWidget(_lbl("策略描述", _MUT, 12))
        self._desc_edit = QtWidgets.QTextEdit()
        self._desc_edit.setMaximumHeight(70)
        self._desc_edit.setStyleSheet(
            f"QTextEdit{{background:{_PAN2};color:{_FG};"
            f"border:1px solid {_BORD};border-radius:4px;"
            f"font-size:12px;padding:4px;}}")
        v.addWidget(self._desc_edit)

        v.addStretch()

        # 应用参数按鈕
        self._btn_apply = QtWidgets.QPushButton("✓  应用参数")
        self._btn_apply.setStyleSheet(
            f"QPushButton{{background:{_GRN};color:#1e1e2e;border:none;"
            f"border-radius:4px;padding:8px 0;font-size:13px;font-weight:bold;}}"
            f"QPushButton:hover{{background:{_GRN};opacity:0.85;}}"
        )
        self._btn_apply.clicked.connect(self._on_apply_params)
        v.addWidget(self._btn_apply)

        scroll.setWidget(inner)

        outer = QtWidgets.QVBoxLayout(w)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)
        return w

    # ── 本地策略持久化 (无引擎模式) ─────────────────────────────

    @staticmethod
    def _strategy_save_dir():
        from pathlib import Path
        d = Path.home() / ".vnpy" / "strategy_condition"
        d.mkdir(parents=True, exist_ok=True)
        return d

    def _load_saved_strategies_from_disk(self) -> None:
        """开启时扫描 ~/.vnpy/strategy_condition/*.json 并装入下拉框。"""
        from ..core.strategy import Strategy
        save_dir = self._strategy_save_dir()
        loaded = 0
        self._strategy_cb.blockSignals(True)
        for fp in sorted(save_dir.glob("*.json")):
            try:
                s = Strategy.from_json(fp.read_text(encoding="utf-8"))
                label = f"[已保存] {s.meta.name}"
                # 避免重复添加
                existing = [self._strategy_cb.itemText(i)
                            for i in range(self._strategy_cb.count())]
                if label not in existing:
                    self._strategy_cb.addItem(label, s)
                    loaded += 1
            except Exception as e:
                print(f"[SCE] 加载策略失败 {fp.name}: {e}")
        self._strategy_cb.blockSignals(False)
        if loaded:
            print(f"[SCE] 从本地加载 {loaded} 个已保存策略")

    # ── 初始化策略模板 ────────────────────────────────────────────────

    def _load_builtin_templates(self) -> None:
        templates = get_all_templates()
        self._strategy_cb.blockSignals(True)
        self._strategy_cb.addItem("[ 新建空策略 ]", None)
        for t in templates:
            self._strategy_cb.addItem(t.name, t)
        self._strategy_cb.blockSignals(False)
        # 默认加载第一个内置模板
        if templates:
            self._load_strategy(templates[0])

        # 从引擎加载已保存的策略
        loaded_from_engine = 0
        if self._engine:
            for name in self._engine.get_strategies():
                s = self._engine.get_strategy(name)
                if s:
                    self._strategy_cb.addItem(f"[已保存] {name}", s)
                    loaded_from_engine += 1

        # 如果引擎未加载到任何策略（或引擎不存在），从磁盘扫描
        if loaded_from_engine == 0:
            self._load_saved_strategies_from_disk()

    def _load_strategy(self, strategy: Strategy) -> None:
        # Deep-copy so each strategy holds independent tree objects
        import copy
        self._strategy = copy.deepcopy(strategy)
        self._buy_editor.load_tree(self._strategy.buy_tree)
        self._sell_editor.load_tree(self._strategy.sell_tree)
        self._name_edit.setText(self._strategy.name)
        self._hold_sp.setValue(self._strategy.params.max_hold_days)
        self._cooldown_sp.setValue(self._strategy.params.cooldown_days)
        self._sl_sp.setValue(self._strategy.params.stop_loss_pct)
        self._tp_sp.setValue(self._strategy.params.take_profit_pct)
        self._trail_sp.setValue(self._strategy.params.trail_drawdown)
        self._desc_edit.setPlainText(self._strategy.meta.description)

    def _collect_params(self) -> StrategyParams:
        return StrategyParams(
            max_hold_days=   self._hold_sp.value(),
            cooldown_days=   self._cooldown_sp.value(),
            stop_loss_pct=   self._sl_sp.value(),
            take_profit_pct= self._tp_sp.value(),
            trail_drawdown=  self._trail_sp.value(),
            commission_rate= self._comm_sp.value() / 10000,
            stamp_duty_rate= self._stamp_sp.value() / 1000,
            slippage_rate=   0.0002,
        )

    # ── 事件处理 ──────────────────────────────────────────────────────

    def _on_apply_params(self) -> None:
        """
        Write right-panel sell parameters into strategy.params,
        then sync matching nodes in the sell tree so both stay consistent.
        """
        if not self._strategy:
            return
        sp = self._collect_params()
        self._strategy.params = sp

        from ..constant import ConditionIndicator as CI
        for cond in self._strategy.sell_tree.all_conditions():
            ind = cond.indicator
            if ind == CI.STOP_LOSS:
                cond.params["pct"] = sp.stop_loss_pct
            elif ind == CI.TAKE_PROFIT:
                cond.params["pct"] = sp.take_profit_pct
            elif ind == CI.TRAILING_STOP:
                cond.params["take_profit"]    = sp.take_profit_pct
                cond.params["trail_drawdown"] = sp.trail_drawdown
            elif ind == CI.MAX_HOLD_DAYS:
                cond.params["days"] = sp.max_hold_days

        self._sell_editor.load_tree(self._strategy.sell_tree)
        self._show_msg(
            f"参数已应用：\n"
            f"  止损 {sp.stop_loss_pct}%  "
            f"止盈 {sp.take_profit_pct}%  "
            f"追踪回撤 {sp.trail_drawdown}%\n"
            f"  最大持仓 {sp.max_hold_days} 天"
        )

    # ── 缓存辅助 ──────────────────────────────────────────────────────

    def _strategy_hash(self) -> str:
        """策略的指纹哈希（买卖树结构 + params），用于快照缓存 key"""
        import hashlib, json
        if not self._strategy:
            return ""
        # 用 JSON 序列化策略的核心数据作为指纹
        try:
            payload = self._strategy.to_json()
        except Exception:
            payload = repr(self._strategy.params) + repr(self._strategy.buy_tree)
        return hashlib.md5(payload.encode()).hexdigest()[:12]

    def _invalidate_caches(self, bars: bool = True, snapshots: bool = True) -> None:
        """清除缓存。bars=True 清 K 线缓存，snapshots=True 清快照缓存"""
        if bars:
            self._bars_cache.clear()
            self._bars_cache_key = ()
        if snapshots:
            self._snapshot_cache.clear()
            self._snapshot_cache_key = ()
        self._monitor_dirty = True

    def _feed_monitor(self, symbol: str,
                      buy_dates: list = None,
                      sell_dates: list = None) -> None:
        """
        为指定股票生成条件监控快照并加载到 Monitor Tab。
        内置两层缓存：
          1. 如果 (symbol, strategy_hash, buy_dates, sell_dates) 命中缓存，
             直接从缓存加载渲染，0 延迟。
          2. 否则执行完整计算，结果存入缓存。
        """
        if self._monitor_tab is None:
            return
        if not self._strategy:
            return

        # ── 缓存 key ──
        buy_dates = buy_dates or []
        sell_dates = sell_dates or []
        cache_key = (
            symbol,
            self._strategy_hash(),
            tuple(buy_dates),
            tuple(sell_dates),
        )

        # ── 缓存命中：直接渲染 ──
        cached = self._snapshot_cache.get(cache_key)
        if cached is not None:
            snapshots, bars = cached
            print(
                f"[SCE] Monitor 缓存命中 {symbol} "
                f"({len(snapshots)} snapshots, {len(bars)} bars)",
                flush=True,
            )
            self._monitor_tab.load_snapshots(
                symbol, snapshots,
                bars=bars,
                buy_dates=buy_dates,
                sell_dates=sell_dates,
            )
            self._monitor_dirty = False
            return

        # ── 缓存未命中：计算快照 ──
        print(f"[SCE] _feed_monitor: computing for {symbol}", flush=True)
        try:
            n_bars = self._nbars_sp.value()

            # 优先复用 Chart Tab 已加载的原始 bars
            chart_raw_bars = getattr(self._kline_tab, '_last_raw_bars', None)
            if chart_raw_bars and len(chart_raw_bars) > 0:
                bars = [_BarAdapter(b) for b in chart_raw_bars]
            else:
                bars_dict = self._load_bars([symbol], n_bars)
                bars = bars_dict.get(symbol, [])

            if not bars:
                print(f"[SCE] _feed_monitor: no bars for {symbol}")
                return

            from ..monitor.condition_monitor_engine import ConditionMonitorEngine
            from ..engine.condition_engine import ConditionEngine
            ce = ConditionEngine()
            monitor_eng = ConditionMonitorEngine(ce)

            if len(bars) >= 200:
                monitor_warmup = 60
            elif len(bars) >= 100:
                monitor_warmup = 30
            else:
                monitor_warmup = min(10, max(1, len(bars) // 4))

            snapshots = monitor_eng.generate_snapshots(
                symbol=symbol,
                bars=bars,
                strategy=self._strategy,
                warmup=monitor_warmup,
                buy_dates=buy_dates,
                sell_dates=sell_dates,
            )
            print(
                f"[SCE] _feed_monitor: {len(snapshots)} snapshots "
                f"(warmup={monitor_warmup})",
                flush=True,
            )

            # 回测结果的卖出日期是权威来源
            effective_sell_dates = sell_dates

            # ── 存入缓存 ──
            self._snapshot_cache[cache_key] = (snapshots, bars)
            self._snapshot_cache_key = cache_key

            self._monitor_tab.load_snapshots(
                symbol, snapshots,
                bars=bars,
                buy_dates=buy_dates,
                sell_dates=effective_sell_dates,
            )
            self._monitor_dirty = False
            print(f"[SCE] _feed_monitor: done, cached", flush=True)
        except Exception as e:
            import traceback
            print(f"[SCE] Monitor 快照生成失败: {e}")
            traceback.print_exc()

    def _on_tab_changed(self, idx: int) -> None:
        """切换到 Monitor Tab 时，使用缓存快速展示"""
        if self._monitor_tab is None:
            return
        monitor_idx = self._tab.indexOf(self._monitor_tab)
        if idx != monitor_idx:
            return
        symbol = getattr(self._kline_tab, "_current_symbol", "")
        if not symbol:
            return
        buy_dates  = getattr(self._kline_tab, "_last_buy_dates",  [])
        sell_dates = getattr(self._kline_tab, "_last_sell_dates", [])
        # _feed_monitor 内部会先查缓存，命中则 0 延迟
        self._feed_monitor(symbol, buy_dates=buy_dates, sell_dates=sell_dates)

    def _on_signal_selected(self, rec) -> None:
        """
        信号结果行被点击时，自动切换到 K线图 Tab 并进行渲染。
        买入信号：绿色 ▲ 标记入场日期 (rec.dt)
        卖出信号：红色 ▼ 标记出场日期 (rec.exit_dt)
        """
        symbol = getattr(rec, "symbol", None)
        if not symbol:
            return
        # 收集该股票在当前批次里的所有信号
        buy_dates: list = []
        sell_dates: list = []
        batch = getattr(self._signal_view, "_batch", None)
        if batch is not None:
            for s in getattr(batch, "signals", []):
                if s.symbol == symbol:
                    # 入场日期 → 买入标记，智能格式化：
                    # - 日线 (hour=0, min=0): 只保留 "YYYY-MM-DD"
                    # - 分钟线: 保留 "YYYY-MM-DD HH:MM"
                    dt = s.dt
                    if hasattr(dt, 'hour') and dt.hour == 0 and dt.minute == 0:
                        entry_dt = str(dt)[:10]  # YYYY-MM-DD
                    else:
                        entry_dt = str(dt)[:16]  # YYYY-MM-DD HH:MM
                    if entry_dt and entry_dt != "None":
                        buy_dates.append(entry_dt)
                    # 出场日期 → 卖出标记，同样处理
                    exit_dt = getattr(s, "exit_dt", None)
                    if exit_dt is not None:
                        if hasattr(exit_dt, 'hour') and exit_dt.hour == 0 and exit_dt.minute == 0:
                            exit_str = str(exit_dt)[:10]
                        else:
                            exit_str = str(exit_dt)[:16]
                        if exit_str and exit_str != "None":
                            sell_dates.append(exit_str)
        # 如果批次为空，用当前记录本身
        if not buy_dates and not sell_dates:
            dt = getattr(rec, "dt", None)
            if dt:
                if hasattr(dt, 'hour') and dt.hour == 0 and dt.minute == 0:
                    dt_str = str(dt)[:10]
                else:
                    dt_str = str(dt)[:16]
                if dt_str and dt_str != "None":
                    buy_dates = [dt_str]
            exit_dt = getattr(rec, "exit_dt", None)
            if exit_dt is not None:
                if hasattr(exit_dt, 'hour') and exit_dt.hour == 0 and exit_dt.minute == 0:
                    exit_str = str(exit_dt)[:10]
                else:
                    exit_str = str(exit_dt)[:16]
                if exit_str and exit_str != "None":
                    sell_dates = [exit_str]
        # 切换到 K线图 Tab
        kline_idx = self._tab.indexOf(self._kline_tab)
        if kline_idx >= 0:
            self._tab.setCurrentIndex(kline_idx)
        
        # 同步K线图周期选择和当前主界面保持一致
        current_idx = self._interval_cb.currentIndex()
        self._kline_tab._interval_cb.setCurrentIndex(current_idx)
        
        self._kline_tab.show_symbol(symbol, buy_dates=buy_dates, sell_dates=sell_dates)

        # ── 同步 Monitor Tab（传递相同的回测信号）──
        self._feed_monitor(symbol, buy_dates=buy_dates, sell_dates=sell_dates)

    def _on_strategy_changed(self, idx: int) -> None:
        s = self._strategy_cb.itemData(idx)
        if s is None:
            self._on_new_strategy()
        else:
            self._load_strategy(s)

    def _on_new_strategy(self) -> None:
        name = self._name_edit.text().strip() or "新策略"
        s = empty_strategy(name)
        self._load_strategy(s)

    def _on_rename_strategy(self) -> None:
        """重命名当前选中的已保存策略"""
        cb  = self._strategy_cb
        idx = cb.currentIndex()
        txt = cb.currentText()

        if not txt.startswith("[已保存]"):
            self._show_msg(
                "只能重命名 [已保存] 的策略，内置模板不可重命名。"
            )
            return

        old_name = txt[len("[已保存] "):]
        new_name, ok = QtWidgets.QInputDialog.getText(
            self, "重命名策略",
            "请输入新的策略名称：",
            QtWidgets.QLineEdit.EchoMode.Normal,
            old_name,
        )
        if not ok:
            return
        new_name = new_name.strip()
        if not new_name:
            self._show_msg("策略名称不能为空")
            return
        if new_name == old_name:
            return

        # 检查是否重名
        for i in range(cb.count()):
            if cb.itemText(i) == f"[已保存] {new_name}":
                self._show_msg(f"已存在同名策略「{new_name}」，请换一个名称。")
                return

        # 磁盘上重命名文件
        save_dir = self._strategy_save_dir()
        old_safe = "".join(
            c if c.isalnum() or c in "-_ " else "_" for c in old_name
        )
        new_safe = "".join(
            c if c.isalnum() or c in "-_ " else "_" for c in new_name
        )
        old_fp = save_dir / f"{old_safe}.json"
        new_fp = save_dir / f"{new_safe}.json"

        # 更新策略对象
        strategy = cb.itemData(idx)
        if strategy:
            strategy.meta.name = new_name
            strategy.touch()
            # 写入新文件
            new_fp.write_text(strategy.to_json(), encoding="utf-8")
            # 删除旧文件（如果不同名）
            if old_fp.exists() and old_fp != new_fp:
                old_fp.unlink()

        # 引擎模式下也同步
        if self._engine:
            try:
                self._engine.delete_strategy(old_name)
                self._engine.save_strategy(strategy)
            except Exception:
                pass

        # 更新 ComboBox 显示
        cb.blockSignals(True)
        cb.setItemText(idx, f"[已保存] {new_name}")
        cb.setItemData(idx, strategy)
        cb.blockSignals(False)

        # 更新右侧名称输入框
        self._name_edit.setText(new_name)
        if self._strategy:
            self._strategy.meta.name = new_name

        self._show_msg(f"策略已重命名：「{old_name}」→「{new_name}」")

    def _on_delete_strategy(self) -> None:
        cb  = self._strategy_cb
        idx = cb.currentIndex()
        txt = cb.currentText()

        if not txt.startswith("[已保存]"):
            self._show_msg(
                "只能删除 [已保存] 的策略，内置模板不可删除。"
            )
            return

        name = txt[len("[已保存] "):]
        ret  = QtWidgets.QMessageBox.question(
            self,
            "删除策略",
            f"确认删除策略「{name}」？\n此操作不可撤销。",
            QtWidgets.QMessageBox.StandardButton.Yes |
            QtWidgets.QMessageBox.StandardButton.No,
            QtWidgets.QMessageBox.StandardButton.No,
        )
        if ret != QtWidgets.QMessageBox.StandardButton.Yes:
            return

        if self._engine:
            try:
                self._engine.delete_strategy(name)
            except Exception:
                pass
        else:
            save_dir = self._strategy_save_dir()
            safe = "".join(
                c if c.isalnum() or c in "-_ " else "_" for c in name
            )
            fp = save_dir / f"{safe}.json"
            if fp.exists():
                fp.unlink()

        cb.blockSignals(True)
        cb.removeItem(idx)
        cb.blockSignals(False)

        new_idx = min(1, cb.count() - 1)
        cb.setCurrentIndex(new_idx)
        self._on_strategy_changed(new_idx)
        self._strategy = None
        self._show_msg(f"策略「{name}」已删除")

    def _on_lib_double_click(self, item, _col) -> None:
        """
        双击条件库条目 → 添加到当前策略树。

        崩溃根因与修复：
          itemDoubleClicked 信号是在 Qt 的 mouseDoubleClickEvent 事件处理
          链“内部同步”发射的。而 editor.add_condition() 内部会调用
          load_tree() → QTreeWidget.clear()，销毁并重建策略树的
          QTreeWidgetItem C++ 对象。若在双击事件链中同步执行，会 clear()
          掉正在被 Qt 内部引用的 item，导致 C++ 层野指针 segfault——这种
          崩溃无法被 Python 的 try/except 捕获，表现为程序直接闪退。

          解决办法与 dropEvent 一致：先同步取出 indicator 与目标 editor
          （item 属于“条件库树”，不会被重建，引用安全），再用
          QTimer.singleShot(0, ...) 把真正的添加动作延迟到下一个事件循环，
          此时 Qt 已完成双击事件处理，可以安全地 clear()/rebuild。
        """
        try:
            ind = item.data(0, QtCore.Qt.ItemDataRole.UserRole)
            if ind is None:
                return
            # 判断当前 Tab：买入 or 卖出
            tab_idx = self._tab.currentIndex()
            editor  = self._sell_editor if tab_idx == 1 else self._buy_editor
            # 延迟到下一个事件循环执行，避开双击事件链中的 C++ 野指针陷阱
            QtCore.QTimer.singleShot(
                0, lambda e=editor, i=ind: self._do_add_condition(e, i))
        except Exception as e:
            self._show_add_cond_error(e)

    def _do_add_condition(self, editor, ind) -> None:
        """在下一个事件循环中真正执行添加条件（异常捕获 + 弹窗）"""
        try:
            editor.add_condition(ind)
        except Exception as e:
            self._show_add_cond_error(e)

    def _show_add_cond_error(self, e: Exception) -> None:
        """添加条件异常弹窗（崩溃前的诊断信息）"""
        tb_str = "".join(
            traceback.format_exception(type(e), e, e.__traceback__))
        print(f"[SCE] 添加条件异常:\n{tb_str}", flush=True)
        try:
            msg = QtWidgets.QMessageBox(self)
            msg.setIcon(QtWidgets.QMessageBox.Icon.Critical)
            msg.setWindowTitle("添加条件异常")
            msg.setText(f"双击添加条件时发生异常：\n{type(e).__name__}: {e}")
            msg.setDetailedText(tb_str)
            msg.exec()
        except Exception:
            pass

    def _on_tree_changed(self) -> None:
        if self._strategy:
            self._strategy.buy_tree  = self._buy_editor.get_tree()
            self._strategy.sell_tree = self._sell_editor.get_tree()
            # ── 方向A同步：卖出条件节点参数 → 右侧面板 SpinBox ──
            self._sync_sell_node_params_to_panel()

    def _sync_sell_node_params_to_panel(self) -> None:
        """
        遍历卖出树中的条件节点，将关联参数同步到右侧面板的 SpinBox。
        仅对 EXIT 类条件做同步（止损/止盈/追踪/最大持仓），避免误覆盖。
        使用 blockSignals 防止循环触发。
        """
        if not self._strategy:
            return
        from ..constant import ConditionIndicator as CI
        for cond in self._strategy.sell_tree.all_conditions():
            ind = cond.indicator
            if ind == CI.STOP_LOSS:
                val = cond.params.get("pct")
                if val is not None:
                    self._sl_sp.blockSignals(True)
                    self._sl_sp.setValue(float(val))
                    self._sl_sp.blockSignals(False)
            elif ind == CI.TAKE_PROFIT:
                val = cond.params.get("pct")
                if val is not None:
                    self._tp_sp.blockSignals(True)
                    self._tp_sp.setValue(float(val))
                    self._tp_sp.blockSignals(False)
            elif ind == CI.TRAILING_STOP:
                tp_val = cond.params.get("take_profit")
                dd_val = cond.params.get("trail_drawdown")
                if tp_val is not None:
                    self._tp_sp.blockSignals(True)
                    self._tp_sp.setValue(float(tp_val))
                    self._tp_sp.blockSignals(False)
                if dd_val is not None:
                    self._trail_sp.blockSignals(True)
                    self._trail_sp.setValue(float(dd_val))
                    self._trail_sp.blockSignals(False)
            elif ind == CI.MAX_HOLD_DAYS:
                val = cond.params.get("days")
                if val is not None:
                    self._hold_sp.blockSignals(True)
                    self._hold_sp.setValue(int(val))
                    self._hold_sp.blockSignals(False)
        # 同步更新 strategy.params 以保证三方一致
        self._strategy.params.max_hold_days = self._hold_sp.value()
        self._strategy.params.stop_loss_pct = self._sl_sp.value()
        self._strategy.params.take_profit_pct = self._tp_sp.value()
        self._strategy.params.trail_drawdown = self._trail_sp.value()

    def _on_scan(self) -> None:
        if not self._strategy:
            self._show_msg("请先选择或创建策略")
            return
        symbols = self._get_pool_symbols()
        if not symbols:
            self._show_msg(
                "股票池为空！请在右侧[股票池]区域设置股票。\n"
                "可点击预设按钮（沪深300/中证500/科创板），\n"
                "或手动输入股票代码（每行一个，格式：000001.SZSE）。"
            )
            return
        self._strategy.params = self._collect_params()
        n_bars = self._nbars_sp.value()
        self._btn_scan.setEnabled(False)
        self._btn_scan.setText("扫描中...")
        try:
            bars_dict = self._load_bars(symbols, n_bars)
            loaded = [s for s, b in bars_dict.items() if b]
            if not loaded:
                self._show_msg(
                    f"未能加载到任何K线数据（共{len(symbols)}只股票）。\n"
                    "请先通过【数据管理器】下载历史K线数据。\n"
                    "股票代码格式应为 000001.SZSE / 600519.SSE"
                )
                return
            from ..engine.scan_engine import ScanEngine
            from ..engine.condition_engine import ConditionEngine
            ce = self._engine.condition_engine if self._engine else ConditionEngine()
            se = ScanEngine(ce)
            batch = se.scan(
                loaded, self._strategy, n_bars=n_bars,
                _bars_dict=bars_dict
            )
            self._signal_view.load_batch(batch)
            self._tab.setCurrentIndex(2)
            self._pool_count_lbl.setText(
                f"上次扫描：{len(loaded)}/{len(symbols)}只加载成功，"
                f"命中{batch.count}只"
            )
        except Exception as e:
            self._show_msg(f"选股失败: {e}")
        finally:
            self._btn_scan.setEnabled(True)
            self._btn_scan.setText("▶  运行选股")

    def _on_backtest(self) -> None:
        if not self._strategy:
            self._show_msg("请先选择或创建策略")
            return
        symbols = self._get_pool_symbols()
        if not symbols:
            self._show_msg("股票池为空！请先在右侧设置股票池。")
            return
        self._strategy.params = self._collect_params()
        n_bars = self._nbars_sp.value()
        self._btn_bt.setEnabled(False)
        self._btn_bt.setText("回测中...")
        try:
            bars_dict = self._load_bars(symbols, n_bars)
            loaded = [s for s, b in bars_dict.items() if b]
            if not loaded:
                self._show_msg(
                    f"未能加载到任何K线数据（共{len(symbols)}只股票）。\n"
                    "请先通过【数据管理器】下载历史K线数据。"
                )
                return
            from ..engine.scan_engine import ScanEngine
            from ..engine.condition_engine import ConditionEngine
            ce = self._engine.condition_engine if self._engine else ConditionEngine()
            se = ScanEngine(ce)
            warmup = max(60, self._strategy.params.min_bars)
            # 判断是否为分钟级K线（非日线即为日内，需启用T+1规则）
            bt_idx = self._interval_cb.currentIndex()
            bt_interval, _ = self._interval_options[bt_idx]
            is_intraday = (bt_interval != Interval.DAILY)
            batch  = se.backtest(loaded, self._strategy, bars_dict,
                                 warmup=warmup, is_intraday=is_intraday)
            self._bt_view.load_batch(batch)
            self._signal_view.load_batch(batch)
            self._tab.setCurrentIndex(3)
            self._pool_count_lbl.setText(
                f"上次回测：{len(loaded)}/{len(symbols)}只，"
                f"{batch.count}笔交易"
            )
        except Exception as e:
            self._show_msg(f"回测失败: {e}")
        finally:
            self._btn_bt.setEnabled(True)
            self._btn_bt.setText("📊  回测验证")

    def _on_save(self) -> None:
        if not self._strategy:
            self._show_msg("请先创建策略")
            return

        current_name = (
            self._name_edit.text().strip()
            or self._strategy.meta.name
        )

        name, ok = QtWidgets.QInputDialog.getText(
            self, "保存策略",
            "策略名称：",
            QtWidgets.QLineEdit.EchoMode.Normal,
            current_name,
        )
        if not ok:
            return
        name = name.strip()
        if not name:
            self._show_msg("策略名称不能为空")
            return

        self._name_edit.setText(name)
        self._strategy.meta.name = name
        self._strategy.meta.description = self._desc_edit.toPlainText()
        self._strategy.params = self._collect_params()
        self._strategy.touch()

        if self._engine:
            self._engine.save_strategy(self._strategy)
            cb     = self._strategy_cb
            target = f"[已保存] {name}"
            found  = False
            for i in range(cb.count()):
                if cb.itemText(i) == target:
                    cb.setItemData(i, self._strategy)
                    found = True
                    break
            if not found:
                cb.addItem(target, self._strategy)
            self._show_msg(f"策略 [{name}] 已保存")
        else:
            save_dir = self._strategy_save_dir()
            safe = "".join(
                c if c.isalnum() or c in "-_ " else "_" for c in name
            )
            fp = save_dir / f"{safe}.json"
            fp.write_text(self._strategy.to_json(), encoding="utf-8")
            self._show_msg(
                f"策略 [{name}] 已保存到\n{fp}"
            )

    # ── 诊断信息槽 ──────────────────────────────────────────────────────

    def _on_lifecycle_info(self, line1: str, line2: str) -> None:
        """接收 Monitor 波形区鼠标移动时的诊断信息，显示在底部按钮栏"""
        self._lifecycle_lbl.setText(f"{line1}\n{line2}")

    # ── 股票池辅助（完整版）────────────────────────────────────────────

    def _set_pool(self, symbols: list) -> None:
        if not symbols:
            self._pool_edit.clear()
        else:
            self._pool_edit.setPlainText("\n".join(symbols))

    def _on_pool_changed(self) -> None:
        n = len(self._get_pool_symbols())
        name = getattr(self, '_current_pool_name', '')
        if name:
            self._pool_count_lbl.setText(f"{name} - {n} 只")
        elif n > 0:
            self._pool_count_lbl.setText(f"数据源：VeighNa 数据库 - {n} 只")
        else:
            self._pool_count_lbl.setText("数据源：VeighNa 数据库")

    def _set_exchange_pool(self, exchange_key: str, name: str = "") -> None:
        """按交易所筛选股票（优化：友好的加载提示）"""
        try:
            from vnpy.trader.stock_pool import get_symbols_by_exchange, is_cache_loading
            
            symbols = get_symbols_by_exchange(exchange_key)
            if symbols:
                self._current_pool_name = name or exchange_key
                self._pool_edit.setPlainText("\n".join(symbols))
                # 显示股票池数量和更新时间
                from vnpy.trader import stock_pool
                update_time = stock_pool.get_pool_update_time()
                time_str = f" (更新: {update_time})" if update_time else ""
                self._pool_count_lbl.setText(f"{name or exchange_key} - {len(symbols)}只{time_str}")
            else:
                # 区分：后台加载中 vs 真的没有数据
                if is_cache_loading():
                    self._show_msg(
                        f"正在后台加载 {name or exchange_key} 的股票数据...\n\n"
                        "⏳ 首次加载需要几秒钟，请稍后再次点击按钮"
                    )
                else:
                    self._show_msg(
                        f"{name or exchange_key} 没有找到任何股票数据\n\n"
                        "请先通过【数据管理器】下载历史K线数据。"
                    )
        except Exception as e:
            self._show_msg(f"交易所筛选失败: {e}")

    def _set_board_pool(self, board_name: str) -> None:
        """按板块筛选股票"""
        try:
            from vnpy.trader.stock_pool import get_symbols_by_board
            symbols = get_symbols_by_board(board_name)
            if symbols:
                self._current_pool_name = board_name
                self._pool_edit.setPlainText("\n".join(symbols))
        except Exception as e:
            self._show_msg(f"板块筛选失败: {e}")

    def _set_index_pool(self, pool_key: str, name: str = "") -> None:
        """按指数成分筛选股票"""
        self._current_pool_name = name
        if pool_key.startswith("IDX:"):
            index_code = pool_key[4:]
            try:
                from vnpy.trader.index_constituents import get_index_symbols
                symbols = get_index_symbols(index_code)
                if symbols:
                    self._pool_edit.setPlainText("\n".join(symbols))
                    from vnpy.trader import stock_pool
                    update_time = stock_pool.get_pool_update_time()
                    time_str = f" (更新: {update_time})" if update_time else ""
                    self._pool_count_lbl.setText(f"{name} - {len(symbols)}只{time_str}")
                    return
            except Exception:
                pass
            # fallback: 使用内置池
            if index_code == "000300":
                self._set_pool(_POOL_CSI300)
            elif index_code == "000905":
                self._set_pool(_POOL_CSI500)
            else:
                self._show_msg(f"尚无 {name or index_code} 的成分股缓存数据。\n请在数据管理App中先更新。")

    def _on_sce_index_changed(self, index: int) -> None:
        """从更多指数下拉框选择"""
        data = self._sce_index_combo.currentData()
        if not data:
            return
        text = self._sce_index_combo.currentText().strip()
        self._set_index_pool(data, text)
        self._sce_index_combo.blockSignals(True)
        self._sce_index_combo.setCurrentIndex(0)
        self._sce_index_combo.blockSignals(False)

    def _on_sce_industry_changed(self, index: int) -> None:
        """从行业下拉框选择"""
        industry = self._sce_industry_combo.currentData()
        if not industry:
            return
        try:
            from vnpy.trader.stock_pool import get_symbols_by_industry
            symbols = get_symbols_by_industry(industry)
            if symbols:
                self._current_pool_name = industry
                self._pool_edit.setPlainText("\n".join(symbols))
        except Exception as e:
            self._show_msg(f"行业筛选失败: {e}")
        self._sce_industry_combo.blockSignals(True)
        self._sce_industry_combo.setCurrentIndex(0)
        self._sce_industry_combo.blockSignals(False)

    def _get_pool_symbols(self) -> list:
        raw = self._pool_edit.toPlainText()
        tokens = []
        for tok in raw.replace(",", " ").replace("\n", " ").split():
            tok = tok.strip()
            if not tok:
                continue
            if "." in tok:
                tokens.append(tok.upper())
            elif tok.isdigit() and len(tok) == 6:
                if tok.startswith("6") or tok.startswith("5"):
                    tokens.append(tok + ".SSE")
                else:
                    tokens.append(tok + ".SZSE")
            else:
                tokens.append(tok)
        seen = set()
        result = []
        for t in tokens:
            if t not in seen:
                seen.add(t)
                result.append(t)
        return result

    def _load_bars(self, symbols: list, n_bars: int) -> dict:
        """
        Load K-line bars for each symbol.
        Priority: MarketBehavior CandleBuffer > VeighNa database.
        Returns {vt_symbol: [bar, ...]} where each bar has
        .open .high .low .close .volume .dt attributes expected by
        ConditionEngine.
        """
        bars_dict: dict = {}

        # Get selected interval from UI
        idx = self._interval_cb.currentIndex()
        interval, _ = self._interval_options[idx]

        # 1. Try MarketBehavior CandleBuffer first
        buf = None
        if self._engine:
            buf = getattr(self._engine.scan_engine, "_buf", None)
        if buf is not None and hasattr(buf, "get"):
            for sym in symbols:
                try:
                    bars_dict[sym] = buf.get(sym, n_bars) or []
                except Exception:
                    bars_dict[sym] = []
            if any(bars_dict.values()):
                return bars_dict

        # 2. Fall back to VeighNa database
        from vnpy.trader.database import get_database
        from vnpy.trader.constant import Exchange, Interval
        from datetime import datetime, timedelta
        db = get_database()

        # 使用 UI 上的回测时间范围
        end_date_str = self._date_end.text().strip()
        start_date_str = self._date_start.text().strip()

        if end_date_str in ("今日", "today", ""):
            end_dt = datetime.now()
        else:
            try:
                end_dt = datetime.strptime(end_date_str, "%Y-%m-%d")
                # 设到当天23:59:59确保包含当天所有数据
                end_dt = end_dt.replace(hour=23, minute=59, second=59)
            except ValueError:
                end_dt = datetime.now()

        if start_date_str:
            try:
                start_dt = datetime.strptime(start_date_str, "%Y-%m-%d")
            except ValueError:
                start_dt = datetime(1990, 1, 1)
        else:
            start_dt = datetime(1990, 1, 1)

        _loaded_count = 0
        for sym in symbols:
            _loaded_count += 1
            if _loaded_count % 10 == 0:
                QtWidgets.QApplication.processEvents()
            try:
                parts    = sym.split(".")
                code     = parts[0]
                exch_str = parts[1] if len(parts) > 1 else ""
                try:
                    # UI uses SSE/SZSE, database enum uses the same values
                    exchange = Exchange(exch_str)
                except Exception:
                    exchange = Exchange.SSE if code.startswith("6") else Exchange.SZSE
                raw = db.load_bar_data(
                    symbol=code, exchange=exchange,
                    interval=interval,
                    start=start_dt, end=end_dt,
                )
                # BarData uses open_price/high_price/low_price/close_price;
                # ConditionEngine reads .open/.high/.low/.close/.volume/.dt
                if n_bars > 0 and raw:
                    bars_dict[sym] = [_BarAdapter(b) for b in raw[-n_bars:]]
                else:
                    bars_dict[sym] = [_BarAdapter(b) for b in raw] if raw else []
            except Exception:
                bars_dict[sym] = []

        return bars_dict

    def _update_estimated_start_date(self) -> None:
        """根据当前K线数量和周期计算预估起始日期并显示"""
        from vnpy.trader.constant import Interval
        from datetime import datetime, timedelta
        
        n_bars = self._nbars_sp.value()
        if n_bars <= 0:
            self._nbars_start_lbl.setText("预估起始日期：全部历史数据")
            return
        
        idx = self._interval_cb.currentIndex()
        interval, _ = self._interval_options[idx]
        end_dt = datetime.now()
        
        if interval == Interval.DAILY:
            days_needed = int(n_bars * 1.8)
        elif interval in (Interval.MINUTE, Interval.MINUTE_5,
                          Interval.MINUTE_15, Interval.MINUTE_30,
                          Interval.HOUR):
            bars_per_day = {
                Interval.MINUTE:    240,
                Interval.MINUTE_5:   48,
                Interval.MINUTE_15:  16,
                Interval.MINUTE_30:   8,
                Interval.HOUR:        4,
            }
            bpd = bars_per_day.get(interval, 240)
            days_needed = int(n_bars / bpd * 1.8) + 1
        else:
            days_needed = int(n_bars * 1.8)
        
        start_dt = end_dt - timedelta(days=days_needed)
        date_str = start_dt.strftime("%Y-%m-%d")
        self._nbars_start_lbl.setText(f"预估起始日期：{date_str}")

    def _show_msg(self, msg: str) -> None:
        QtWidgets.QMessageBox.information(self, "提示", msg)

    # ── 面板显示/隐藏切换 ────────────────────────────────────────────

    def _on_left_cb_changed(self, state: int) -> None:
        """左侧复选框状态改变（与快捷键联动）"""
        if state == QtCore.Qt.CheckState.Checked.value:
            if not self._left_panel.isVisible():
                self._left_panel.show()
                sizes = self._splitter.sizes()
                if sizes[0] == 0:
                    sizes[0] = 240
                    self._splitter.setSizes(sizes)
        else:
            if self._left_panel.isVisible():
                self._left_panel.hide()

    def _on_right_cb_changed(self, state: int) -> None:
        """右侧复选框状态改变（与快捷键联动）"""
        if state == QtCore.Qt.CheckState.Checked.value:
            if not self._right_panel.isVisible():
                self._right_panel.show()
                sizes = self._splitter.sizes()
                if sizes[2] == 0:
                    sizes[2] = 380
                    self._splitter.setSizes(sizes)
        else:
            if self._right_panel.isVisible():
                self._right_panel.hide()

    def _toggle_left_panel(self) -> None:
        """切换左侧条件库面板的显示/隐藏（快捷键 Ctrl+L）"""
        if self._left_panel.isVisible():
            self._left_panel.hide()
            self._show_left_cb.setChecked(False)
        else:
            self._left_panel.show()
            self._show_left_cb.setChecked(True)
            # 恢复合理宽度
            sizes = self._splitter.sizes()
            if sizes[0] == 0:
                sizes[0] = 240
                self._splitter.setSizes(sizes)

    def _toggle_right_panel(self) -> None:
        """切换右侧参数面板的显示/隐藏（快捷键 Ctrl+R）"""
        if self._right_panel.isVisible():
            self._right_panel.hide()
            self._show_right_cb.setChecked(False)
        else:
            self._right_panel.show()
            self._show_right_cb.setChecked(True)
            # 恢复合理宽度
            sizes = self._splitter.sizes()
            if sizes[2] == 0:
                sizes[2] = 380
                self._splitter.setSizes(sizes)

    @staticmethod
    def _bold_font() -> QtGui.QFont:
        f = QtGui.QFont(); f.setBold(True); return f
