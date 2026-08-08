"""image.png
K-Line Behavior Lab - K线行为研究实验室
三栏布局：特征库 | 研究工作台+结果Tab | 参数设置
参照 Strategy Condition Engine 风格设计
"""
from __future__ import annotations
from typing import List, Optional, Dict
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
    QPushButton, QLabel, QLineEdit, QTextEdit,
    QComboBox, QSpinBox, QDoubleSpinBox, QGroupBox,
    QFormLayout, QTableWidget, QTableWidgetItem,
    QHeaderView, QAbstractItemView, QProgressBar,
    QApplication, QTreeWidget, QTreeWidgetItem,
    QTabWidget, QCheckBox, QRadioButton, QButtonGroup,
    QPlainTextEdit, QScrollArea, QFrame, QMessageBox,
    QMenu, QGridLayout, QDialog, QDialogButtonBox,
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QColor

from ..engine import ResearchEngine
from ..model.kline_event_model import EventSamplingRule
from ..behavior import (
    KLineFeatureCalculator,
    FeatureEngine,
    ConditionBuilder,
    SamplingEngine,
    EventSearcher,
    get_global_registry,
)
from ..model.kline_feature_model import KLineFeatureType
from .behavior_monitor_tab import BehaviorMonitorTab

_BG = "#1e1e2e"; _PANEL = "#181825"; _PAN2 = "#11111b"
_BORD = "#45475a"; _FG = "#cdd6f4"; _MUT = "#6c7086"
_BLU = "#89b4fa"; _GRN = "#a6e3a1"; _YLW = "#f9e2af"
_RED = "#f38ba8"; _MAV = "#cba6f7"; _PNK = "#f5c2e7"
_TEAL = "#94e2d5"

_FEATURE_COLORS = {
    KLineFeatureType.PATTERN: _PNK,
    KLineFeatureType.VOLUME: _MAV,
    KLineFeatureType.TREND: _GRN,
    KLineFeatureType.MOMENTUM: _YLW,
    KLineFeatureType.VOLATILITY: _TEAL,
    KLineFeatureType.CROSS_SECTIONAL: _BLU,
}

_SPIN_SS = (f"QDoubleSpinBox,QSpinBox{{background:{_PAN2};color:{_FG};"
            f"border:1px solid {_BORD};border-radius:4px;padding:3px 6px;font-size:13px;}}")
_EDIT_SS = (f"QLineEdit{{background:{_PAN2};color:{_FG};"
            f"border:1px solid {_BORD};border-radius:4px;padding:4px 8px;font-size:13px;}}")
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
                    f"QPushButton:hover{{background:{color};opacity:0.85;}}"
                    f"QPushButton:disabled{{background:{_BORD};color:{_MUT};}}")
    if w:
        b.setFixedWidth(w)
    return b


# ─── 公式变量名 → 中文释义字典 ───
_VAR_CN = {
    # K线基本价格
    "open": "开盘价", "high": "最高价", "low": "最低价", "close": "收盘价",
    "volume": "成交量", "amount": "成交额", "turnover_rate": "换手率",
    # 收益类
    "return_1": "1日涨跌幅", "return_3": "3日涨跌幅", "return_5": "5日涨跌幅",
    "return_10": "10日涨跌幅", "return_20": "20日涨跌幅",
    "gap_return": "跳空幅度", "intraday_return": "日内涨幅",
    "overnight_return": "隔夜涨幅", "log_return_1": "对数收益率",
    # K线形态结构
    "body_ratio": "实体占比(实体/振幅)", "body_pct": "实体幅度",
    "body_sign": "阴阳标记(1阳/-1阴)",
    "upper_shadow_ratio": "上影线占比", "lower_shadow_ratio": "下影线占比",
    "upper_shadow_pct": "上影线幅度", "lower_shadow_pct": "下影线幅度",
    "close_location": "收盘位置(0低~1高)", "range_pct": "振幅比例",
    # 布尔形态
    "is_green": "是否阳线", "is_red": "是否阴线",
    "is_big_green": "大阳线", "is_big_red": "大阴线",
    "is_doji": "十字星", "is_hammer": "锤子线",
    "is_shooting_star": "射击之星", "is_morning_star": "早晨之星",
    "three_red_soldiers": "三连阴", "three_green_soldiers": "三连阳",
    "engulfing_bullish": "看涨吞没", "engulfing_bearish": "看跌吞没",
    # 量价
    "volume_ratio": "量比(vs 20日均量)", "volume_ratio_5": "量比(vs 5日均量)",
    "amount_ratio": "额比(vs 20日均额)", "volume_spike": "放量突破",
    "volume_shrink": "缩量", "turnover_ratio": "换手率比",
    # 均线
    "ma5": "5日均线", "ma10": "10日均线", "ma20": "20日均线", "ma60": "60日均线",
    "ma_slope_5": "MA5斜率", "ma_slope_20": "MA20斜率",
    "price_to_ma5": "价格偏离MA5", "price_to_ma20": "价格偏离MA20",
    "price_position": "价格位置(60日高低间)",
    "price_ma5_pct": "价格vs MA5百分比", "price_ma20_pct": "价格vs MA20百分比",
    "ma_alignment": "均线多头排列", "ma_bull_arrange": "均线多头排列",
    "new_high_20": "20日新高", "new_low_20": "20日新低",
    "pullback_from_high": "离20日高点回撤", "bounce_from_low": "离20日低点反弹",
    # 波动率
    "atr_10": "10日ATR", "atr_20": "20日ATR",
    "volatility_10": "10日年化波动率", "volatility_20": "20日年化波动率",
    "volatility_percentile": "波动率百分位", "realized_volatility_5": "5日已实现波动率",
    # 动量
    "rsi_6": "RSI(6)", "rsi_14": "RSI(14)",
    "rsi_oversold": "RSI超卖(<30)", "rsi_overbought": "RSI超买(>70)",
    "macd": "MACD", "macd_signal": "MACD信号线", "macd_histogram": "MACD柱",
    "momentum_5": "5日动量", "momentum_10": "10日动量",
    "reversal_5": "5日反转", "reversal_score": "反转信号评分",
    "v_reversal": "V型反转",
    # 横截面
    "relative_strength": "相对强度(vs大盘)", "volume_rank": "成交量排名",
    "market_return_20": "大盘20日收益",
}

# 运算符中文说明
_OP_CN = {
    ">": "大于", ">=": "大于等于", "<": "小于", "<=": "小于等于",
    "==": "等于", "!=": "不等于",
}


def _build_formula_glossary(formula: str) -> List[str]:
    """
    解析公式中的所有变量和表达式，返回中文注释列表。
    支持：
    - 简单变量：close, body_ratio, volume_ratio 等
    - 带 .shift(N) 的表达式：close.shift(1) → 前1天的收盘价
    - 带 .rolling(N).xxx() 的表达式：volume.rolling(20).mean() → 成交量的20日均值
    - 带 .rank(pct=True) 的表达式
    - 复合变量引用：is_red.shift(2) → 前2天的是否阴线
    """
    import re
    lines = []
    seen = set()

    # 1. 匹配 var.shift(N) 模式
    for m in re.finditer(r'([a-zA-Z_][a-zA-Z0-9_]*)\.shift\((\d+)\)', formula):
        var, n = m.group(1), m.group(2)
        expr = f"{var}.shift({n})"
        if expr in seen:
            continue
        seen.add(expr)
        base_cn = _VAR_CN.get(var, var)
        lines.append(f"  {expr} = 前{n}天的{base_cn}")

    # 2. 匹配 var.rolling(N).mean/max/min/std() 模式
    for m in re.finditer(r'([a-zA-Z_][a-zA-Z0-9_]*)\.rolling\((\d+)\)\.(mean|max|min|std)\(\)', formula):
        var, n, func = m.group(1), m.group(2), m.group(3)
        expr = f"{var}.rolling({n}).{func}()"
        if expr in seen:
            continue
        seen.add(expr)
        base_cn = _VAR_CN.get(var, var)
        func_cn = {"mean": "均值", "max": "最大值", "min": "最小值", "std": "标准差"}.get(func, func)
        lines.append(f"  {expr} = {base_cn}的{n}日{func_cn}")

    # 3. 匹配 var.rolling(N).rank(pct=True) 模式
    for m in re.finditer(r'([a-zA-Z_][a-zA-Z0-9_]*)\.rolling\((\d+)\)\.rank\(pct=True\)', formula):
        var, n = m.group(1), m.group(2)
        expr = f"{var}.rolling({n}).rank(pct=True)"
        if expr in seen:
            continue
        seen.add(expr)
        base_cn = _VAR_CN.get(var, var)
        lines.append(f"  {expr} = {base_cn}在{n}日内的百分位排名")

    # 4. 匹配 max(var1, var2) / min(var1, var2) 函数调用
    for m in re.finditer(r'(max|min)\(([a-zA-Z_][a-zA-Z0-9_]*),\s*([a-zA-Z_][a-zA-Z0-9_]*)\)', formula):
        func, v1, v2 = m.group(1), m.group(2), m.group(3)
        expr = f"{func}({v1}, {v2})"
        if expr in seen:
            continue
        seen.add(expr)
        cn1 = _VAR_CN.get(v1, v1)
        cn2 = _VAR_CN.get(v2, v2)
        func_cn = "较大值" if func == "max" else "较小值"
        lines.append(f"  {func}({v1},{v2}) = {cn1}和{cn2}的{func_cn}")

    # 5. 匹配简单变量（不含.shift/.rolling等后缀的）
    _skip_words = {'astype', 'int', 'float', 'abs', 'max', 'min', 'np', 'pd',
                   'shift', 'rolling', 'mean', 'std', 'sqrt', 'rank', 'pct',
                   'True', 'False', 'talib', 'ATR', 'RSI', 'EMA', 'timeperiod',
                   'log', 'e', 'and', 'or', 'not'}
    simple_vars = set(re.findall(r'\b([a-zA-Z_][a-zA-Z0-9_]*)\b', formula))
    for var in sorted(simple_vars):
        if var in _skip_words or var in seen:
            continue
        cn = _VAR_CN.get(var)
        if cn:
            lines.append(f"  {var} = {cn}")
            seen.add(var)

    # 6. 对运算符加注释（如果有比较运算）
    ops_found = set(re.findall(r'>=|<=|!=|>|<|==', formula))
    if ops_found:
        op_notes = [f"{op}({_OP_CN.get(op, op)})" for op in sorted(ops_found, key=len, reverse=True)]
        lines.append(f"  运算符: {', '.join(op_notes)}")

    return lines


_POOL_CSI300 = [
    "000001.SZSE","000002.SZSE","000063.SZSE","000333.SZSE","000651.SZSE",
    "000858.SZSE","600000.SSE","600016.SSE","600028.SSE","600030.SSE",
    "600036.SSE","600048.SSE","600050.SSE","600104.SSE","600196.SSE",
    "600276.SSE","600309.SSE","600519.SSE","600585.SSE","600690.SSE",
    "600900.SSE","601012.SSE","601088.SSE","601166.SSE","601318.SSE",
    "601398.SSE","601601.SSE","601628.SSE","601668.SSE","601888.SSE",
]
_POOL_CSI500 = [
    "000021.SZSE","000400.SZSE","000568.SZSE","000661.SZSE","000725.SZSE",
    "000938.SZSE","002050.SZSE","002142.SZSE","002241.SZSE","002304.SZSE",
    "002460.SZSE","600015.SSE","600018.SSE","600019.SSE","600060.SSE",
    "600109.SSE","600115.SSE","600153.SSE","600176.SSE","600188.SSE",
]


class BehaviorResearchTab(QWidget):
    """K线行为研究实验室 - 三栏布局主界面"""

    def __init__(self, engine: ResearchEngine, parent=None):
        super().__init__(parent)
        self._engine = engine
        self._feature_calculator = KLineFeatureCalculator()
        self.feature_engine = FeatureEngine()
        self.condition_builder = ConditionBuilder()
        self.sampling_engine = SamplingEngine()
        self.feature_registry = get_global_registry()
        self._condition_nodes: List[Dict] = []
        self._logic_op = "AND"
        self._init_ui()

    def _init_ui(self):
        self.setStyleSheet(f"background:{_BG};color:{_FG};font-family:微软雅黑,Arial,sans-serif;")
        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        self._main_splitter = QSplitter(Qt.Horizontal)
        self._main_splitter.setHandleWidth(4)
        self._main_splitter.setStyleSheet("QSplitter::handle{background:#313244;}"
                               "QSplitter::handle:hover{background:#89b4fa;}")
        self._left_panel = self._build_left()
        self._mid_panel = self._build_mid()
        self._right_panel = self._build_right()
        self._main_splitter.addWidget(self._left_panel)
        self._main_splitter.addWidget(self._mid_panel)
        self._main_splitter.addWidget(self._right_panel)
        self._main_splitter.setStretchFactor(0, 2)
        self._main_splitter.setStretchFactor(1, 5)
        self._main_splitter.setStretchFactor(2, 3)
        self._main_splitter.setSizes([220, 700, 340])
        self._main_splitter.setCollapsible(0, True)
        self._main_splitter.setCollapsible(1, False)
        self._main_splitter.setCollapsible(2, True)
        root.addWidget(self._main_splitter)

    # ══════════════ 左栏：特征库 ══════════════
    def _build_left(self):
        w = QWidget()
        w.setStyleSheet(f"background:{_PANEL};")
        v = QVBoxLayout(w)
        v.setContentsMargins(12, 12, 12, 12)
        v.setSpacing(6)
        v.addWidget(_lbl("特征库  Feature Library", _YLW, 14, True))
        v.addWidget(_hline())
        self._lib_tree = QTreeWidget()
        self._lib_tree.setHeaderHidden(True)
        self._lib_tree.setStyleSheet(
            f"QTreeWidget{{background:{_PAN2};color:{_FG};border:1px solid {_BORD};"
            f"border-radius:4px;font-size:13px;}}"
            f"QTreeWidget::item{{padding:4px 2px;}}"
            f"QTreeWidget::item:hover{{background:#313244;}}"
            f"QTreeWidget::item:selected{{background:{_BLU};color:#1e1e2e;}}")
        self._populate_feature_tree()
        self._lib_tree.expandAll()
        self._lib_tree.itemDoubleClicked.connect(self._on_feature_double_click)
        v.addWidget(self._lib_tree, 1)
        v.addWidget(_lbl("双击添加到研究条件", _MUT, 11))
        return w

    def _populate_feature_tree(self):
        features_by_type = {}
        for name in self.feature_registry.get_feature_names():
            feat = self.feature_registry.get_feature(name)
            if feat:
                features_by_type.setdefault(feat.feature_type, []).append(feat)
        type_labels = {
            KLineFeatureType.PATTERN: "🕯 形态  Shape",
            KLineFeatureType.VOLUME: "📊 量价  Volume",
            KLineFeatureType.TREND: "📈 趋势  Trend",
            KLineFeatureType.MOMENTUM: "⚡ 动量  Momentum",
            KLineFeatureType.VOLATILITY: "🌊 波动  Volatility",
            KLineFeatureType.CROSS_SECTIONAL: "🎯 综合  Composite",
        }
        for ft, label in type_labels.items():
            features = features_by_type.get(ft, [])
            if not features:
                continue
            parent = QTreeWidgetItem([label])
            parent.setForeground(0, QColor(_YLW))
            color = _FEATURE_COLORS.get(ft, _FG)
            for feat in sorted(features, key=lambda x: x.name):
                child = QTreeWidgetItem([f"  {feat.display_name}"])
                child.setData(0, Qt.ItemDataRole.UserRole, feat)
                child.setForeground(0, QColor(color))
                child.setToolTip(0, f"{feat.name}\n{feat.description}")
                parent.addChild(child)
            self._lib_tree.addTopLevelItem(parent)

    # ══════════════ 中栏：研究工作台 ══════════════
    def _build_mid(self):
        w = QWidget()
        w.setStyleSheet(f"background:{_BG};")
        w.setMinimumWidth(400)
        v = QVBoxLayout(w)
        v.setContentsMargins(14, 12, 14, 12)
        v.setSpacing(8)
        title_row = QHBoxLayout()
        title_row.addWidget(_lbl("研究工作台  Research", _YLW, 14, True))
        title_row.addSpacing(20)
        # ── 面板显示/隐藏勾选框 ──
        _cb_ss = (f"QCheckBox{{color:{_FG};font-size:12px;background:transparent;}}"
                  f"QCheckBox::indicator{{width:14px;height:14px;border:1px solid {_BORD};"
                  f"border-radius:3px;background:{_PAN2};}}"
                  f"QCheckBox::indicator:checked{{background:{_BLU};border-color:{_BLU};}}")
        self._show_left_cb = QCheckBox("特征库")
        self._show_left_cb.setChecked(True)
        self._show_left_cb.setStyleSheet(_cb_ss)
        self._show_left_cb.toggled.connect(self._toggle_left_panel)
        title_row.addWidget(self._show_left_cb)
        title_row.addSpacing(12)
        self._show_right_cb = QCheckBox("参数面板")
        self._show_right_cb.setChecked(True)
        self._show_right_cb.setStyleSheet(_cb_ss)
        self._show_right_cb.toggled.connect(self._toggle_right_panel)
        title_row.addWidget(self._show_right_cb)
        title_row.addStretch()
        title_row.addWidget(_lbl("名称:", _MUT, 12))
        self._name_edit = QLineEdit("新研究")
        self._name_edit.setStyleSheet(_EDIT_SS)
        self._name_edit.setFixedWidth(180)
        title_row.addWidget(self._name_edit)
        v.addLayout(title_row)
        v.addWidget(_hline())

        self._tab = QTabWidget()
        self._tab.setStyleSheet(
            f"QTabWidget::pane{{background:{_BG};border:1px solid {_BORD};border-radius:4px;}}"
            f"QTabBar::tab{{background:{_PAN2};color:{_MUT};padding:8px 18px;font-size:13px;"
            f"border:1px solid {_BORD};border-bottom:none;border-radius:4px 4px 0 0;margin-right:2px;}}"
            f"QTabBar::tab:selected{{background:{_BLU};color:#1e1e2e;font-weight:bold;}}"
            f"QTabBar::tab:hover{{background:#313244;color:{_FG};}}")
        self._tab.addTab(self._build_condition_tab(), "📝 研究条件")
        self._tab.addTab(self._build_events_tab(), "📋 事件列表")
        self._tab.addTab(self._build_stats_tab(), "📊 收益统计")
        self._monitor_tab = BehaviorMonitorTab()
        self._monitor_tab.set_refresh_callback(self._refresh_single_symbol)
        self._tab.addTab(self._monitor_tab, "🔍 条件监控")
        v.addWidget(self._tab, 1)

        v.addWidget(_hline())
        btn_row = QHBoxLayout()
        self._btn_run = _btn("▶  开始研究", _GRN)
        self._btn_save = _btn("💾  保存", _YLW)
        self._btn_new = _btn("＋  新建", _MAV)
        self._btn_export = _btn("📊  导出", _BLU)
        self._btn_run.clicked.connect(self._on_run_research)
        self._btn_save.clicked.connect(self._on_save)
        self._btn_new.clicked.connect(self._on_new)
        self._btn_save.setEnabled(False)
        self._btn_export.setEnabled(False)
        for b in (self._btn_run, self._btn_save, self._btn_new, self._btn_export):
            btn_row.addWidget(b)
        btn_row.addStretch()
        self._status_lbl = _lbl("就绪", _MUT, 11)
        btn_row.addWidget(self._status_lbl)
        v.addLayout(btn_row)
        self._progress = QProgressBar()
        self._progress.setVisible(False)
        self._progress.setStyleSheet(
            f"QProgressBar{{background:{_PAN2};border:1px solid {_BORD};border-radius:3px;height:6px;}}"
            f"QProgressBar::chunk{{background:{_GRN};border-radius:3px;}}")
        v.addWidget(self._progress)
        return w

    def _build_condition_tab(self):
        w = QWidget()
        h_layout = QHBoxLayout(w)
        h_layout.setContentsMargins(0, 0, 0, 0)
        h_layout.setSpacing(0)

        # ─── 左侧：条件列表 ───
        left_panel = QWidget()
        left_panel.setMinimumWidth(300)
        v = QVBoxLayout(left_panel)
        v.setContentsMargins(8, 8, 4, 8)
        v.setSpacing(6)
        logic_row = QHBoxLayout()
        logic_row.addWidget(_lbl("顶层逻辑:", _MUT, 12))
        self._logic_and_btn = QPushButton("AND")
        self._logic_or_btn = QPushButton("OR")
        for btn, is_and in [(self._logic_and_btn, True), (self._logic_or_btn, False)]:
            btn.setCheckable(True)
            btn.setStyleSheet(
                f"QPushButton{{background:{_PAN2};color:{_FG};border:1px solid {_BORD};"
                f"border-radius:4px;padding:4px 12px;font-size:12px;}}"
                f"QPushButton:checked{{background:{_BLU};color:#1e1e2e;font-weight:bold;}}")
            btn.clicked.connect(lambda checked, a=is_and: self._set_logic(a))
        self._logic_and_btn.setChecked(True)
        logic_row.addWidget(self._logic_and_btn)
        logic_row.addWidget(self._logic_or_btn)
        logic_row.addStretch()
        clear_btn = QPushButton("🗑 清空")
        clear_btn.setStyleSheet(
            f"QPushButton{{background:transparent;color:{_RED};border:1px solid {_RED};"
            f"border-radius:4px;padding:4px 10px;font-size:11px;}}"
            f"QPushButton:hover{{background:{_RED};color:#1e1e2e;}}")
        clear_btn.clicked.connect(self._on_clear_conditions)
        logic_row.addWidget(clear_btn)
        v.addLayout(logic_row)

        self._cond_tree = QTreeWidget()
        self._cond_tree.setHeaderLabels(["条件", "比较", "阈值"])
        self._cond_tree.setColumnCount(3)
        self._cond_tree.header().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self._cond_tree.header().setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        self._cond_tree.header().setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        self._cond_tree.header().resizeSection(1, 60)
        self._cond_tree.header().resizeSection(2, 80)
        self._cond_tree.setStyleSheet(
            f"QTreeWidget{{background:{_PAN2};color:{_FG};border:1px solid {_BORD};"
            f"border-radius:4px;font-size:13px;}}"
            f"QTreeWidget::item{{padding:5px 4px;}}"
            f"QTreeWidget::item:hover{{background:#313244;}}"
            f"QTreeWidget::item:selected{{background:{_BLU};color:#1e1e2e;}}"
            f"QHeaderView::section{{background:{_PANEL};color:{_FG};border:1px solid {_BORD};padding:4px;font-size:12px;}}")
        self._cond_tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._cond_tree.customContextMenuRequested.connect(self._on_cond_context_menu)
        self._cond_tree.itemDoubleClicked.connect(self._on_cond_double_click)
        self._cond_tree.itemClicked.connect(self._on_cond_clicked)
        v.addWidget(self._cond_tree, 1)
        self._cond_summary = _lbl("尚未添加条件，请从左侧特征库双击添加", _MUT, 11)
        v.addWidget(self._cond_summary)

        tmpl_row = QHBoxLayout()
        tmpl_row.addWidget(_lbl("模板:", _MUT, 12))
        self._template_combo = QComboBox()
        self._template_combo.setStyleSheet(_COMBO_SS)
        self._template_combo.addItem("自定义", None)
        for t in self.condition_builder.get_condition_templates():
            self._template_combo.addItem(t["name"], t)
        tmpl_row.addWidget(self._template_combo, 1)
        tmpl_apply = QPushButton("应用")
        tmpl_apply.setStyleSheet(
            f"QPushButton{{background:{_PAN2};color:{_FG};border:1px solid {_BORD};"
            f"border-radius:4px;padding:4px 10px;font-size:11px;}}"
            f"QPushButton:hover{{border-color:{_BLU};color:{_BLU};}}")
        tmpl_apply.clicked.connect(self._on_apply_template)
        tmpl_row.addWidget(tmpl_apply)
        v.addLayout(tmpl_row)

        # ─── 右侧：参数设置面板 ───
        self._param_panel = QWidget()
        self._param_panel.setStyleSheet(f"background:{_PANEL};border-left:1px solid {_BORD};")
        self._param_panel.setMinimumWidth(260)
        self._param_panel.setMaximumWidth(360)
        param_scroll = QScrollArea()
        param_scroll.setWidgetResizable(True)
        param_scroll.setStyleSheet(f"QScrollArea{{background:{_PANEL};border:none;}}")
        self._param_inner = QWidget()
        self._param_inner.setStyleSheet(f"background:{_PANEL};")
        self._param_layout = QVBoxLayout(self._param_inner)
        self._param_layout.setContentsMargins(12, 12, 12, 12)
        self._param_layout.setSpacing(8)
        # 初始占位内容
        self._param_placeholder = _lbl("选择条件查看参数设置", _MUT, 12)
        self._param_placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._param_layout.addWidget(self._param_placeholder)
        self._param_layout.addStretch()
        param_scroll.setWidget(self._param_inner)
        param_outer = QVBoxLayout(self._param_panel)
        param_outer.setContentsMargins(0, 0, 0, 0)
        param_outer.addWidget(param_scroll)

        # 组装左右布局
        cond_splitter = QSplitter(Qt.Horizontal)
        cond_splitter.setHandleWidth(3)
        cond_splitter.setStyleSheet("QSplitter::handle{background:#313244;}"
                                    "QSplitter::handle:hover{background:#89b4fa;}")
        cond_splitter.addWidget(left_panel)
        cond_splitter.addWidget(self._param_panel)
        cond_splitter.setStretchFactor(0, 3)
        cond_splitter.setStretchFactor(1, 2)
        cond_splitter.setSizes([400, 280])
        cond_splitter.setCollapsible(0, False)
        cond_splitter.setCollapsible(1, False)
        h_layout.addWidget(cond_splitter)
        return w

    def _on_cond_clicked(self, item, col):
        """单击条件时，在右侧参数面板中展示该条件的参数设置"""
        parent = item.parent()
        if parent is None:
            # 点击根节点（AND/OR），清空面板
            self._show_param_placeholder()
            return
        idx = parent.indexOfChild(item)
        if idx < 0 or idx >= len(self._condition_nodes):
            self._show_param_placeholder()
            return
        node = self._condition_nodes[idx]
        self._show_condition_params(node, idx)

    def _show_param_placeholder(self):
        """显示占位提示"""
        self._clear_param_panel()
        self._param_placeholder = _lbl("选择条件查看参数设置", _MUT, 12)
        self._param_placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._param_layout.addWidget(self._param_placeholder)
        self._param_layout.addStretch()

    def _clear_param_panel(self):
        """清空参数面板内容"""
        while self._param_layout.count():
            child = self._param_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

    def _show_condition_params(self, node: Dict, node_idx: int):
        """展示选中条件的参数设置面板"""
        self._clear_param_panel()
        feat = node.get("feature")
        layout = self._param_layout

        # ─── 标题区域 ───
        layout.addWidget(_lbl("参数设置", _YLW, 13, True))
        layout.addWidget(_hline())

        # ─── 特征名称 & 类型标签 ───
        feat_color = _FEATURE_COLORS.get(feat.feature_type if feat else None, _FG)
        type_name = feat.feature_type.value if feat else "unknown"
        layout.addWidget(_lbl(f"🏷 {node['display']}", feat_color, 14, True))
        layout.addWidget(_lbl(f"  类型: {type_name}", _MUT, 11))
        layout.addWidget(_hline())

        # ─── 比较运算符 ───
        layout.addWidget(_lbl("比较运算符", _MUT, 12))
        op_combo = QComboBox()
        op_combo.setStyleSheet(_COMBO_SS)
        for op in [">", ">=", "<", "<=", "==", "!="]:
            op_combo.addItem(op)
        op_combo.setCurrentText(node["op"])
        op_combo.currentTextChanged.connect(
            lambda text, n=node: self._update_node_op(n, text))
        layout.addWidget(op_combo)

        # ─── 阈值 ───
        layout.addWidget(_lbl("阈值", _MUT, 12))
        threshold_sp = QDoubleSpinBox()
        threshold_sp.setRange(-9999.0, 9999.0)
        threshold_sp.setDecimals(4)
        threshold_sp.setSingleStep(0.01)
        threshold_sp.setValue(float(node["threshold"]))
        threshold_sp.setStyleSheet(_SPIN_SS)
        threshold_sp.valueChanged.connect(
            lambda val, n=node: self._update_node_threshold(n, val))
        layout.addWidget(threshold_sp)

        # ─── 权重 weight ───
        layout.addWidget(_hline())
        layout.addWidget(_lbl("权重 weight", _MUT, 12))
        weight_sp = QDoubleSpinBox()
        weight_sp.setRange(0.0, 10.0)
        weight_sp.setDecimals(2)
        weight_sp.setSingleStep(0.1)
        weight_sp.setValue(float(node.get("weight", 1.0)))
        weight_sp.setStyleSheet(_SPIN_SS)
        weight_sp.valueChanged.connect(
            lambda val, n=node: n.__setitem__("weight", val))
        layout.addWidget(weight_sp)

        # ─── 子参数编辑（复合特征） ───
        if feat and hasattr(feat, 'formula') and feat.formula:
            sub_params = self._parse_formula_params(feat.formula)
            if sub_params:
                layout.addWidget(_hline())
                layout.addWidget(_lbl("⚙ 触发条件参数", _TEAL, 12, True))
                # 初始化 sub_params 存储
                if "sub_params" not in node:
                    node["sub_params"] = {sp["name"]: sp["value"] for sp in sub_params}
                for sp in sub_params:
                    sp_name = sp["name"]
                    sp_op = sp["op"]
                    sp_val = node["sub_params"].get(sp_name, sp["value"])
                    # 获取子特征的显示名，优先用中文字典
                    sub_feat = self.feature_registry.get_feature(sp_name)
                    cn_name = _VAR_CN.get(sp_name, "")
                    if sub_feat and sub_feat.display_name != sp_name:
                        disp = sub_feat.display_name
                    elif cn_name:
                        disp = cn_name
                    else:
                        disp = sp_name
                    # 如果 display_name 是英文且有中文释义，附加中文
                    if disp == sp_name and cn_name:
                        disp = cn_name
                    row_w = QWidget()
                    row_w.setStyleSheet(f"background:transparent;")
                    row_l = QHBoxLayout(row_w)
                    row_l.setContentsMargins(0, 2, 0, 2)
                    row_l.setSpacing(6)
                    row_l.addWidget(_lbl(f"{disp}", _FG, 11))
                    op_cn = _OP_CN.get(sp_op, sp_op)
                    row_l.addWidget(_lbl(f"{sp_op}({op_cn})", _MUT, 10))
                    sp_spin = QDoubleSpinBox()
                    sp_spin.setRange(-999.0, 999.0)
                    sp_spin.setDecimals(3)
                    sp_spin.setSingleStep(0.01)
                    sp_spin.setValue(sp_val)
                    sp_spin.setStyleSheet(_SPIN_SS)
                    sp_spin.setFixedWidth(90)
                    sp_spin.valueChanged.connect(
                        lambda val, n=node, k=sp_name: n["sub_params"].__setitem__(k, val))
                    row_l.addWidget(sp_spin)
                    layout.addWidget(row_w)

        # ─── 特征描述卡片 ───
        if feat:
            layout.addWidget(_hline())
            desc_card = QWidget()
            desc_card.setStyleSheet(
                f"background:{_PAN2};border:1px solid {_BORD};border-radius:6px;")
            dc_layout = QVBoxLayout(desc_card)
            dc_layout.setContentsMargins(10, 8, 10, 8)
            dc_layout.setSpacing(4)
            dc_layout.addWidget(_lbl(f"📖 {feat.display_name}", feat_color, 13, True))
            dc_layout.addWidget(_lbl(feat.description or "暂无描述", _FG, 11))

            if hasattr(feat, 'formula') and feat.formula:
                dc_layout.addWidget(_hline())
                dc_layout.addWidget(_lbl("📐 计算公式", _TEAL, 11, True))
                formula_lbl = _lbl(f"  {feat.formula}", _FG, 11)
                formula_lbl.setWordWrap(True)
                dc_layout.addWidget(formula_lbl)
                # 生成完整的公式变量中文注释
                glossary_lines = _build_formula_glossary(feat.formula)
                if glossary_lines:
                    dc_layout.addWidget(_lbl("📖 变量说明", _YLW, 11, True))
                    glossary_lbl = _lbl("\n".join(glossary_lines), _MUT, 10)
                    glossary_lbl.setWordWrap(True)
                    dc_layout.addWidget(glossary_lbl)

            if hasattr(feat, 'dependencies') and feat.dependencies:
                dc_layout.addWidget(_hline())
                dc_layout.addWidget(_lbl("🔗 依赖特征", _MAV, 11, True))
                dc_layout.addWidget(_lbl(f"  {', '.join(feat.dependencies)}", _FG, 11))

            if hasattr(feat, 'lookback_period') and feat.lookback_period:
                dc_layout.addWidget(_lbl(f"⏱ 回看周期: {feat.lookback_period}天", _MUT, 11))

            if hasattr(feat, 'value_range_min') and feat.value_range_min is not None:
                vmin = feat.value_range_min
                vmax = getattr(feat, 'value_range_max', None)
                range_text = f"📊 值域: [{vmin}, {vmax}]" if vmax is not None else f"📊 最小值: {vmin}"
                dc_layout.addWidget(_lbl(range_text, _MUT, 11))

            layout.addWidget(desc_card)

        # ─── 应用参数按钮 ───
        layout.addWidget(_hline())
        apply_btn = _btn("✔  应用参数", _GRN)
        apply_btn.clicked.connect(self._refresh_cond_tree)
        layout.addWidget(apply_btn)

        layout.addStretch()

    def _parse_formula_params(self, formula: str) -> List[Dict]:
        """
        从公式中解析可调子参数。
        例如: '(lower_shadow_ratio > 0.4) & (upper_shadow_ratio < 0.2) & (body_ratio < 0.4)'
        返回: [{"name": "lower_shadow_ratio", "op": ">", "value": 0.4}, ...]
        """
        import re
        results = []
        # 匹配形如 (feature_name op number) 的模式，支持负数
        pattern = r'\(?\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*(>=|<=|!=|>|<|==)\s*(-?[0-9]*\.?[0-9]+)\s*\)?'
        for m in re.finditer(pattern, formula):
            name = m.group(1)
            op = m.group(2)
            try:
                val = float(m.group(3))
            except ValueError:
                continue
            # 过滤掉非特征名的关键字（如 astype, int 等）
            if name in ('astype', 'int', 'float', 'abs', 'max', 'min', 'np', 'pd'):
                continue
            results.append({"name": name, "op": op, "value": val})
        # 只有多于1个子参数时才展示（单参数公式用外层阈值就够了）
        if len(results) <= 1:
            return []
        return results

    def _update_node_op(self, node: Dict, op: str):
        """更新节点运算符"""
        node["op"] = op

    def _update_node_threshold(self, node: Dict, val: float):
        """更新节点阈值"""
        node["threshold"] = val

    def _build_events_tab(self):
        w = QWidget()
        v = QVBoxLayout(w)
        v.setContentsMargins(8, 8, 8, 8)
        summary = QHBoxLayout()
        self._events_count_lbl = _lbl("事件数: 0", _FG, 13)
        self._symbols_count_lbl = _lbl("标的数: 0", _FG, 13)
        summary.addWidget(self._events_count_lbl)
        summary.addWidget(self._symbols_count_lbl)
        summary.addStretch()
        v.addLayout(summary)
        self._results_table = QTableWidget(0, 7)
        self._results_table.setHorizontalHeaderLabels(
            ["事件ID", "标的", "日期", "1日收益", "5日收益", "10日收益", "MFE/MAE"])
        self._results_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self._results_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._results_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._results_table.setAlternatingRowColors(True)
        self._results_table.setStyleSheet(
            f"QTableWidget{{background:{_PAN2};color:{_FG};border:1px solid {_BORD};"
            f"gridline-color:{_BORD};font-size:12px;}}"
            f"QTableWidget::item:selected{{background:{_BLU};color:#1e1e2e;}}"
            f"QHeaderView::section{{background:{_PANEL};color:{_FG};border:1px solid {_BORD};padding:4px;font-size:11px;}}")
        v.addWidget(self._results_table, 1)
        return w

    def _build_stats_tab(self):
        w = QWidget()
        v = QVBoxLayout(w)
        v.setContentsMargins(12, 12, 12, 12)
        v.setSpacing(10)
        v.addWidget(_lbl("收益统计概览", _YLW, 14, True))
        v.addWidget(_hline())
        grid = QGridLayout()
        self._stat_labels = {}
        for idx, (label, key) in enumerate([
            ("5日平均收益", "mean_5d"), ("5日胜率", "win_5d"),
            ("5日夏普", "sharpe_5d"), ("10日平均收益", "mean_10d"),
            ("10日胜率", "win_10d"), ("最大回撤", "max_dd"),
        ]):
            card = QWidget()
            card.setStyleSheet(f"background:{_PAN2};border:1px solid {_BORD};border-radius:6px;")
            cl = QVBoxLayout(card)
            cl.setContentsMargins(12, 8, 12, 8)
            cl.addWidget(_lbl(label, _MUT, 11))
            val_lbl = _lbl("--", _FG, 18, True)
            self._stat_labels[key] = val_lbl
            cl.addWidget(val_lbl)
            grid.addWidget(card, idx // 3, idx % 3)
        v.addLayout(grid)
        v.addStretch()
        return w

    # ══════════════ 右栏：参数设置 ══════════════
    def _build_right(self):
        w = QWidget()
        w.setStyleSheet(f"background:{_PANEL};")
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet(f"QScrollArea{{background:{_PANEL};border:none;}}")
        inner = QWidget()
        inner.setStyleSheet(f"background:{_PANEL};")
        v = QVBoxLayout(inner)
        v.setContentsMargins(12, 12, 12, 12)
        v.setSpacing(6)
        v.addWidget(_lbl("参数设置  Parameters", _YLW, 14, True))
        v.addWidget(_hline())

        # 股票池
        v.addWidget(_lbl("股票池  Universe", _YLW, 12, True))
        preset_grid = QGridLayout()
        preset_grid.setSpacing(4)
        for idx, (label, pool) in enumerate([
            ("沪深300", _POOL_CSI300), ("中证500", _POOL_CSI500),
            ("全市场", []), ("自定义", None),
        ]):
            b = QPushButton(label)
            b.setStyleSheet(
                f"QPushButton{{background:{_PAN2};color:{_FG};border:1px solid {_BORD};"
                f"border-radius:4px;padding:5px 8px;font-size:11px;}}"
                f"QPushButton:hover{{border-color:{_BLU};color:{_BLU};}}")
            b.clicked.connect(lambda checked, p=pool: self._set_pool(p))
            preset_grid.addWidget(b, idx // 2, idx % 2)
        v.addLayout(preset_grid)
        v.addWidget(_lbl("手动输入（逗号或换行分隔）", _MUT, 11))
        self._pool_edit = QPlainTextEdit()
        self._pool_edit.setMaximumHeight(80)
        self._pool_edit.setPlaceholderText("000001.SZSE\n600519.SSE")
        self._pool_edit.setStyleSheet(
            f"QPlainTextEdit{{background:{_PAN2};color:{_FG};border:1px solid {_BORD};"
            f"border-radius:4px;font-size:11px;padding:4px;font-family:Consolas,monospace;}}")
        v.addWidget(self._pool_edit)
        self._pool_count_lbl = _lbl("0 只", _MUT, 11)
        v.addWidget(self._pool_count_lbl)
        self._pool_edit.textChanged.connect(self._on_pool_changed)
        v.addWidget(_hline())

        # 采样规则
        v.addWidget(_lbl("采样规则", _YLW, 12, True))
        self._sampling_group = QButtonGroup(self)
        for label, rule in [("全部事件", EventSamplingRule.ALL),
                            ("首次触发", EventSamplingRule.FIRST_TRIGGER),
                            ("冷却期", EventSamplingRule.COOLDOWN)]:
            rb = QRadioButton(label)
            rb.setStyleSheet(f"QRadioButton{{color:{_FG};font-size:12px;background:transparent;}}")
            rb.setProperty("rule", rule)
            self._sampling_group.addButton(rb)
            v.addWidget(rb)
            if rule == EventSamplingRule.COOLDOWN:
                rb.setChecked(True)
        v.addWidget(_lbl("冷却期（天）", _MUT, 11))
        self._cooldown_sp = QSpinBox()
        self._cooldown_sp.setRange(1, 60)
        self._cooldown_sp.setValue(5)
        self._cooldown_sp.setStyleSheet(_SPIN_SS)
        v.addWidget(self._cooldown_sp)
        v.addWidget(_hline())

        # 未来观察期
        v.addWidget(_lbl("未来观察期", _YLW, 12, True))
        self._period_cbs: Dict[int, QCheckBox] = {}
        period_row = QHBoxLayout()
        for p in [1, 3, 5, 10, 20]:
            cb = QCheckBox(f"{p}日")
            cb.setChecked(p in [1, 5, 10])
            cb.setStyleSheet(
                f"QCheckBox{{color:{_FG};font-size:11px;background:transparent;}}"
                f"QCheckBox::indicator{{width:14px;height:14px;border:1px solid {_BORD};"
                f"border-radius:3px;background:{_PAN2};}}"
                f"QCheckBox::indicator:checked{{background:{_BLU};border-color:{_BLU};}}")
            self._period_cbs[p] = cb
            period_row.addWidget(cb)
        v.addLayout(period_row)
        v.addWidget(_hline())

        # 时间范围
        v.addWidget(_lbl("回测时间范围", _YLW, 12, True))
        v.addWidget(_lbl("起始日期", _MUT, 11))
        self._date_start = QLineEdit("2020-01-01")
        self._date_start.setStyleSheet(_EDIT_SS)
        v.addWidget(self._date_start)
        v.addWidget(_lbl("截止日期", _MUT, 11))
        self._date_end = QLineEdit("今日")
        self._date_end.setStyleSheet(_EDIT_SS)
        v.addWidget(self._date_end)
        v.addStretch()

        scroll.setWidget(inner)
        outer = QVBoxLayout(w)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)
        return w

    # ══════════════ 面板显示/隐藏 ══════════════

    def _toggle_left_panel(self, checked: bool):
        """切换左侧特征库面板的显示/隐藏"""
        if checked:
            self._left_panel.show()
        else:
            self._left_panel.hide()

    def _toggle_right_panel(self, checked: bool):
        """切换右侧参数设置面板的显示/隐藏"""
        if checked:
            self._right_panel.show()
        else:
            self._right_panel.hide()

    # ══════════════ 交互逻辑 ══════════════

    def _get_pool_symbols(self) -> List[str]:
        text = self._pool_edit.toPlainText().strip()
        if not text:
            return []
        symbols = []
        for line in text.replace(",", "\n").replace("\uff0c", "\n").split("\n"):
            s = line.strip()
            if s:
                symbols.append(s)
        return symbols

    def _set_pool(self, pool):
        if pool is None:
            self._pool_edit.clear()
            return
        if not pool:
            try:
                from vnpy.trader.database import get_database
                from vnpy.trader.constant import Interval
                db = get_database()
                overview = db.get_bar_overview()
                syms = [f"{o.symbol}.{o.exchange.value}" for o in overview
                        if o.interval == Interval.DAILY][:100]
                self._pool_edit.setPlainText("\n".join(syms))
            except Exception:
                self._pool_edit.setPlainText("")
            return
        self._pool_edit.setPlainText("\n".join(pool))

    def _on_pool_changed(self):
        self._pool_count_lbl.setText(f"{len(self._get_pool_symbols())} 只")

    def _set_logic(self, is_and):
        self._logic_op = "AND" if is_and else "OR"
        self._logic_and_btn.setChecked(is_and)
        self._logic_or_btn.setChecked(not is_and)
        self._refresh_cond_tree()

    def _on_feature_double_click(self, item, col):
        feat = item.data(0, Qt.ItemDataRole.UserRole)
        if feat is None:
            return
        op, threshold = self._get_default_condition(feat)
        node = {
            "name": feat.name,
            "display": feat.display_name,
            "op": op,
            "threshold": threshold,
            "feature": feat,
            "weight": 1.0,
        }
        self._condition_nodes.append(node)
        self._refresh_cond_tree()

    def _get_default_condition(self, feat):
        """根据特征类型和属性返回合理的默认运算符和阈值"""
        name = feat.name
        ft = feat.feature_type

        # ─── 特定特征的精确默认值 ───
        _DEFAULTS = {
            # 收益类
            "return_1": (">", 0.03),
            "return_3": (">", 0.05),
            "return_5": (">", 0.08),
            "return_10": (">", 0.10),
            "gap_return": (">", 0.02),
            "intraday_return": (">", 0.03),
            "overnight_return": (">", 0.01),
            # K线结构
            "body_ratio": (">", 0.6),
            "upper_shadow_ratio": (">", 0.3),
            "lower_shadow_ratio": (">", 0.3),
            "close_location": (">", 0.7),
            "body_sign": (">", 0.0),
            # 波动率
            "range_pct": (">", 0.03),
            "atr_20": (">", 0.5),
            "volatility_20": (">", 0.2),
            # 量价
            "volume_ratio": (">", 1.5),
            "amount_ratio": (">", 1.5),
            "volume_5d_ratio": (">", 1.5),
            # 趋势
            "ma5": (">", 0.0),
            "ma10": (">", 0.0),
            "ma20": (">", 0.0),
            "ma60": (">", 0.0),
            "ma_slope_5": (">", 0.005),
            "ma_slope_20": (">", 0.002),
            "price_position": (">", 0.5),
            "price_ma5_pct": (">", 0.02),
            "price_ma20_pct": (">", 0.0),
            "ma_bull_arrange": ("==", 1.0),
            "new_high_20": ("==", 1.0),
            "new_low_20": ("==", 1.0),
            # 动量
            "rsi_14": (">", 50.0),
            "macd": (">", 0.0),
            "reversal_5": (">", 0.05),
            # 形态 (pattern) - 布尔型默认 > 0
            "is_big_green": (">", 0.0),
            "is_big_red": (">", 0.0),
            "is_hammer": (">", 0.0),
            "is_doji": (">", 0.0),
            "is_shooting_star": (">", 0.0),
            "is_morning_star": (">", 0.0),
            "three_red_soldiers": (">", 0.0),
            "three_black_crows": (">", 0.0),
            "engulfing_bull": (">", 0.0),
            "engulfing_bear": (">", 0.0),
        }

        if name in _DEFAULTS:
            return _DEFAULTS[name]

        # ─── 按类型推断默认值 ───
        if ft == KLineFeatureType.PATTERN:
            return (">", 0.0)  # 布尔型形态，> 0 表示出现
        elif ft == KLineFeatureType.VOLUME:
            return (">", 1.5)  # 量价类默认放量
        elif ft == KLineFeatureType.TREND:
            return (">", 0.0)  # 趋势类默认向上
        elif ft == KLineFeatureType.MOMENTUM:
            return (">", 0.0)  # 动量类默认正向
        elif ft == KLineFeatureType.VOLATILITY:
            return (">", 0.03)  # 波动率默认 3%
        elif ft == KLineFeatureType.RETURN:
            return (">", 0.03)  # 收益类默认 3%

        # 如果有 value_range_min/max 可以推断中间值
        vmin = getattr(feat, 'value_range_min', None)
        vmax = getattr(feat, 'value_range_max', None)
        if vmin is not None and vmax is not None:
            mid = (vmin + vmax) / 2
            return (">", round(mid, 4))

        return (">", 0.0)

    def _refresh_cond_tree(self):
        self._cond_tree.clear()
        if not self._condition_nodes:
            self._cond_summary.setText("尚未添加条件，请从左侧特征库双击添加")
            return
        root_item = QTreeWidgetItem([self._logic_op, "", ""])
        root_item.setForeground(0, QColor(_BLU))
        for node in self._condition_nodes:
            thr = node["threshold"]
            thr_str = f"{thr:.4f}" if isinstance(thr, float) else str(thr)
            child = QTreeWidgetItem([node["display"], node["op"], thr_str])
            feat = node.get("feature")
            color = _FEATURE_COLORS.get(feat.feature_type if feat else None, _FG)
            child.setForeground(0, QColor(color))
            child.setData(0, Qt.ItemDataRole.UserRole, node)
            root_item.addChild(child)
        self._cond_tree.addTopLevelItem(root_item)
        self._cond_tree.expandAll()
        parts = []
        for n in self._condition_nodes:
            parts.append(f"{n['name']} {n['op']} {n['threshold']}")
        joiner = f" {self._logic_op} "
        self._cond_summary.setText(f"表达式: {joiner.join(parts)}")

    def _on_cond_double_click(self, item, col):
        """双击条件时，直接在右侧参数面板中展示（与单击相同）"""
        self._on_cond_clicked(item, col)

    def _on_cond_context_menu(self, pos):
        item = self._cond_tree.itemAt(pos)
        if not item:
            return
        node = item.data(0, Qt.ItemDataRole.UserRole)
        if node is None:
            return
        menu = QMenu(self)
        menu.setStyleSheet(
            f"QMenu{{background:{_PAN2};color:{_FG};border:1px solid {_BORD};}}"
            f"QMenu::item:selected{{background:{_BLU};color:#1e1e2e;}}")
        del_action = menu.addAction("删除此条件")
        action = menu.exec(self._cond_tree.viewport().mapToGlobal(pos))
        if action == del_action and node in self._condition_nodes:
            self._condition_nodes.remove(node)
            self._refresh_cond_tree()

    def _on_clear_conditions(self):
        self._condition_nodes.clear()
        self._refresh_cond_tree()

    def _on_apply_template(self):
        data = self._template_combo.currentData()
        if data is None:
            return
        self._condition_nodes.clear()
        expr_str = data.get("expression", "")
        sep_parts = expr_str.replace(" AND ", "\n").replace(" OR ", "\n").split("\n")
        for part in sep_parts:
            part = part.strip()
            if not part:
                continue
            for op in [">=", "<=", "!=", ">", "<", "=="]:
                if op in part:
                    name, val = part.split(op, 1)
                    name = name.strip()
                    feat = self.feature_registry.get_feature(name)
                    display = feat.display_name if feat else name
                    try:
                        threshold = float(val.strip())
                    except ValueError:
                        threshold = 0.0
                    self._condition_nodes.append({
                        "name": name, "display": display,
                        "op": op, "threshold": threshold, "feature": feat,
                    })
                    break
        if " OR " in expr_str:
            self._set_logic(False)
        else:
            self._set_logic(True)
        self._refresh_cond_tree()

    def _on_new(self):
        self._condition_nodes.clear()
        self._refresh_cond_tree()
        self._name_edit.setText("新研究")
        self._results_table.setRowCount(0)
        self._events_count_lbl.setText("事件数: 0")
        self._symbols_count_lbl.setText("标的数: 0")
        for lbl in self._stat_labels.values():
            lbl.setText("--")
        self._status_lbl.setText("就绪")
        self._btn_save.setEnabled(False)
        self._btn_export.setEnabled(False)

    def _on_save(self):
        QMessageBox.information(self, "保存", "研究配置已保存")

    def _on_run_research(self):
        """Execute research"""
        if not self._condition_nodes:
            QMessageBox.warning(self, "提示", "请先添加研究条件")
            return
        symbols = self._get_pool_symbols()
        if not symbols:
            QMessageBox.warning(self, "提示", "请先设置股票池")
            return

        # Build condition expression
        cond_parts = []
        for n in self._condition_nodes:
            cond_parts.append(f"({n['name']} {n['op']} {n['threshold']})")
        joiner = " & " if self._logic_op == "AND" else " | "
        condition_expr = joiner.join(cond_parts)

        cooldown = self._cooldown_sp.value()
        periods = [p for p, cb in self._period_cbs.items() if cb.isChecked()]
        if not periods:
            periods = [1, 5, 10]

        self._status_lbl.setText("研究中...")
        self._progress.setVisible(True)
        self._progress.setRange(0, len(symbols))
        self._progress.setValue(0)
        QApplication.processEvents()

        try:
            from vnpy.trader.database import get_database
            from vnpy.trader.constant import Interval, Exchange
            import pandas as pd
            from datetime import datetime

            db = get_database()
            all_events = []
            processed = 0

            for sym_full in symbols:
                processed += 1
                self._progress.setValue(processed)
                if processed % 5 == 0:
                    QApplication.processEvents()

                parts_sym = sym_full.split(".")
                if len(parts_sym) != 2:
                    continue
                symbol, exchange_str = parts_sym
                try:
                    exchange = Exchange(exchange_str)
                except ValueError:
                    continue

                # 解析用户设置的回测时间范围
                try:
                    _start_str = self._date_start.text().strip()
                    _start_dt = datetime.strptime(_start_str, "%Y-%m-%d")
                except Exception:
                    _start_dt = datetime(2020, 1, 1)

                _end_str = self._date_end.text().strip()
                if _end_str in ("今日", "today", ""):
                    _end_dt = datetime.now()
                else:
                    try:
                        _end_dt = datetime.strptime(_end_str, "%Y-%m-%d")
                    except Exception:
                        _end_dt = datetime.now()

                bars = db.load_bar_data(
                    symbol=symbol, exchange=exchange,
                    interval=Interval.DAILY,
                    start=_start_dt, end=_end_dt)
                if not bars or len(bars) < 30:
                    continue

                df = pd.DataFrame([{
                    "open": b.open_price, "high": b.high_price,
                    "low": b.low_price, "close": b.close_price,
                    "volume": float(b.volume), "datetime": b.datetime,
                } for b in bars])
                df.set_index("datetime", inplace=True)

                feature_names = [n["name"] for n in self._condition_nodes]
                features_df = self._feature_calculator.calculate(df, feature_names, use_cache=False)
                research_name = self._name_edit.text() or "behavior_research"
                searcher = EventSearcher(research_id=research_name)
                event_records = searcher.search_events(
                    data=features_df,
                    condition_expression=condition_expr,
                    required_features=feature_names,
                    cooldown_days=cooldown,
                    forward_periods=periods,
                )
                for evt in event_records:
                    d = {
                        "symbol": sym_full,
                        "date": str(getattr(evt, 'datetime', '')),
                        "event_id": getattr(evt, 'event_id', ''),
                    }
                    # Extract forward returns by period
                    fwd = getattr(evt, 'forward_returns', [])
                    for fr in fwd:
                        period = getattr(fr, 'period', 0)
                        ret = getattr(fr, 'return_pct', 0.0)
                        d[f"return_{period}d"] = ret
                        d[f"mfe_{period}d"] = getattr(fr, 'mfe', 0.0)
                        d[f"mae_{period}d"] = getattr(fr, 'mae', 0.0)
                    all_events.append(d)

            self._display_results(all_events, periods)
            self._generate_monitor_data(symbols, condition_expr)
            self._status_lbl.setText(
                f"完成 | {len(all_events)} 事件 | {len(symbols)} 标的")
            self._btn_save.setEnabled(True)
            self._btn_export.setEnabled(True)

        except Exception as e:
            self._status_lbl.setText(f"错误: {str(e)[:50]}")
            QMessageBox.critical(self, "研究失败", str(e))
        finally:
            self._progress.setVisible(False)

    def _display_results(self, events, periods):
        """Display research results"""
        import numpy as np

        self._results_table.setRowCount(0)
        self._events_count_lbl.setText(f"事件数: {len(events)}")
        symbols_set = set(e.get("symbol", "") for e in events)
        self._symbols_count_lbl.setText(f"标的数: {len(symbols_set)}")
        self._results_table.setRowCount(len(events))

        returns_5d = []
        returns_10d = []

        for row, evt in enumerate(events):
            self._results_table.setItem(row, 0, QTableWidgetItem(str(row + 1)))
            self._results_table.setItem(row, 1, QTableWidgetItem(evt.get("symbol", "")))
            self._results_table.setItem(row, 2, QTableWidgetItem(str(evt.get("date", ""))))
            r1 = evt.get("return_1d", 0)
            r5 = evt.get("return_5d", 0)
            r10 = evt.get("return_10d", 0)
            self._results_table.setItem(row, 3, QTableWidgetItem(f"{r1:.2%}"))
            self._results_table.setItem(row, 4, QTableWidgetItem(f"{r5:.2%}"))
            self._results_table.setItem(row, 5, QTableWidgetItem(f"{r10:.2%}"))
            self._results_table.setItem(row, 6, QTableWidgetItem("--"))
            if r5 != 0:
                returns_5d.append(r5)
            if r10 != 0:
                returns_10d.append(r10)

        if returns_5d:
            arr = np.array(returns_5d)
            self._stat_labels["mean_5d"].setText(f"{arr.mean():.2%}")
            self._stat_labels["win_5d"].setText(f"{(arr > 0).mean():.1%}")
            std = arr.std()
            sharpe = arr.mean() / std * (252**0.5) if std > 0 else 0
            self._stat_labels["sharpe_5d"].setText(f"{sharpe:.2f}")
        if returns_10d:
            arr = np.array(returns_10d)
            self._stat_labels["mean_10d"].setText(f"{arr.mean():.2%}")
            self._stat_labels["win_10d"].setText(f"{(arr > 0).mean():.1%}")

        self._tab.setCurrentIndex(1)

    def _generate_monitor_data(self, symbols: List[str], condition_expr: str):
        """
        生成条件监控数据，传递给 Monitor Tab。
        为每个标的计算每根K线上各条件的满足/不满足状态。
        """
        import pandas as pd
        from datetime import datetime

        try:
            from vnpy.trader.database import get_database
            from vnpy.trader.constant import Interval, Exchange

            db = get_database()
            monitor_data = {}
            feature_names = [n["name"] for n in self._condition_nodes]
            condition_displays = [n["display"] for n in self._condition_nodes]

            # 最多处理前10个标的（避免内存过大）
            # 解析用户设置的回测时间范围
            try:
                _start_str = self._date_start.text().strip()
                _start_dt = datetime.strptime(_start_str, "%Y-%m-%d")
            except Exception:
                _start_dt = datetime(2020, 1, 1)

            _end_str = self._date_end.text().strip()
            if _end_str in ("今日", "today", ""):
                _end_dt = datetime.now()
            else:
                try:
                    _end_dt = datetime.strptime(_end_str, "%Y-%m-%d")
                except Exception:
                    _end_dt = datetime.now()

            for sym_full in symbols[:10]:
                parts_sym = sym_full.split(".")
                if len(parts_sym) != 2:
                    continue
                symbol, exchange_str = parts_sym
                try:
                    exchange = Exchange(exchange_str)
                except ValueError:
                    continue

                bars = db.load_bar_data(
                    symbol=symbol, exchange=exchange,
                    interval=Interval.DAILY,
                    start=_start_dt, end=_end_dt)
                if not bars or len(bars) < 30:
                    continue

                df = pd.DataFrame([{
                    "open": b.open_price, "high": b.high_price,
                    "low": b.low_price, "close": b.close_price,
                    "volume": float(b.volume), "datetime": b.datetime,
                } for b in bars])
                df.set_index("datetime", inplace=True)

                # 计算特征（必须禁用缓存，因为每个标的/日期范围数据不同）
                features_df = self._feature_calculator.calculate(df, feature_names, use_cache=False)

                # 为每个条件逐行计算 True/False
                cond_results = pd.DataFrame(index=features_df.index)
                for node in self._condition_nodes:
                    name = node["name"]
                    op = node["op"]
                    threshold = node["threshold"]
                    display = node["display"]

                    if name not in features_df.columns:
                        cond_results[display] = False
                        continue

                    col = features_df[name]
                    if op == ">":
                        cond_results[display] = col > threshold
                    elif op == ">=":
                        cond_results[display] = col >= threshold
                    elif op == "<":
                        cond_results[display] = col < threshold
                    elif op == "<=":
                        cond_results[display] = col <= threshold
                    elif op == "==":
                        cond_results[display] = col == threshold
                    elif op == "!=":
                        cond_results[display] = col != threshold
                    else:
                        cond_results[display] = False

                # 收集事件信息（条件全部满足的日期，应用冷却期）
                if self._logic_op == "AND":
                    all_met = cond_results.all(axis=1)
                else:
                    all_met = cond_results.any(axis=1)

                cooldown = self._cooldown_sp.value()
                events = []
                last_event_idx = -999
                met_indices = [i for i, v in enumerate(all_met) if v]
                for idx_pos in met_indices:
                    if idx_pos - last_event_idx >= cooldown:
                        dt_idx = cond_results.index[idx_pos]
                        events.append({"date": str(dt_idx)[:10]})
                        last_event_idx = idx_pos

                monitor_data[sym_full] = {
                    "df": df,
                    "events": events,
                    "conditions": condition_displays,
                    "condition_results": cond_results,
                }

            # 传递给 Monitor Tab
            if monitor_data:
                self._monitor_tab.set_monitor_data(monitor_data)

        except Exception as e:
            print(f"[BehaviorLab] 生成监控数据异常: {e}")

    def _refresh_single_symbol(self, symbol: str):
        """
        刷新回调：为单个标的重新计算条件监控数据并更新缓存。
        当用户在 Monitor Tab 切换标的后点刷新时被调用。
        """
        import pandas as pd
        from datetime import datetime

        if not self._condition_nodes:
            return

        try:
            from vnpy.trader.database import get_database
            from vnpy.trader.constant import Interval, Exchange

            parts_sym = symbol.split(".")
            if len(parts_sym) != 2:
                return
            sym, exchange_str = parts_sym
            try:
                exchange = Exchange(exchange_str)
            except ValueError:
                return

            # 解析用户设置的回测时间范围
            try:
                _start_str = self._date_start.text().strip()
                _start_dt = datetime.strptime(_start_str, "%Y-%m-%d")
            except Exception:
                _start_dt = datetime(2020, 1, 1)

            _end_str = self._date_end.text().strip()
            if _end_str in ("今日", "today", ""):
                _end_dt = datetime.now()
            else:
                try:
                    _end_dt = datetime.strptime(_end_str, "%Y-%m-%d")
                except Exception:
                    _end_dt = datetime.now()

            db = get_database()
            bars = db.load_bar_data(
                symbol=sym, exchange=exchange,
                interval=Interval.DAILY,
                start=_start_dt, end=_end_dt)
            if not bars or len(bars) < 30:
                return

            df = pd.DataFrame([{
                "open": b.open_price, "high": b.high_price,
                "low": b.low_price, "close": b.close_price,
                "volume": float(b.volume), "datetime": b.datetime,
            } for b in bars])
            df.set_index("datetime", inplace=True)

            feature_names = [n["name"] for n in self._condition_nodes]
            condition_displays = [n["display"] for n in self._condition_nodes]

            # 计算特征（禁用缓存，确保使用当前数据）
            features_df = self._feature_calculator.calculate(df, feature_names, use_cache=False)

            # 为每个条件逐行计算 True/False
            cond_results = pd.DataFrame(index=features_df.index)
            for node in self._condition_nodes:
                name = node["name"]
                op = node["op"]
                threshold = node["threshold"]
                display = node["display"]

                if name not in features_df.columns:
                    cond_results[display] = False
                    continue

                col = features_df[name]
                if op == ">":
                    cond_results[display] = col > threshold
                elif op == ">=":
                    cond_results[display] = col >= threshold
                elif op == "<":
                    cond_results[display] = col < threshold
                elif op == "<=":
                    cond_results[display] = col <= threshold
                elif op == "==":
                    cond_results[display] = col == threshold
                elif op == "!=":
                    cond_results[display] = col != threshold
                else:
                    cond_results[display] = False

            # 收集事件信息（应用冷却期）
            if self._logic_op == "AND":
                all_met = cond_results.all(axis=1)
            else:
                all_met = cond_results.any(axis=1)

            cooldown = self._cooldown_sp.value()
            events = []
            last_event_idx = -999
            met_indices = [i for i, v in enumerate(all_met) if v]
            for idx_pos in met_indices:
                if idx_pos - last_event_idx >= cooldown:
                    dt_idx = cond_results.index[idx_pos]
                    events.append({"date": str(dt_idx)[:10]})
                    last_event_idx = idx_pos

            # 更新 monitor_tab 的缓存数据
            self._monitor_tab._monitor_data[symbol] = {
                "df": df,
                "events": events,
                "conditions": condition_displays,
                "condition_results": cond_results,
            }

            # 如果 combo 中没有这个标的，追加进去
            combo = self._monitor_tab._symbol_combo
            if combo.findText(symbol) < 0:
                combo.addItem(symbol)

        except Exception as e:
            print(f"[BehaviorLab] 刷新单标的 {symbol} 异常: {e}")

