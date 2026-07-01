"""
execution_engine/ui/slippage_tab.py

SlippageTab — 滑点模型配置 + 历史分析 Tab（Phase 2 实现）。

左侧：滑点模型参数配置（实时修改后通知 dispatcher）
右侧：历史滑点分布统计（柱状图 + 统计表）
"""

from __future__ import annotations

from vnpy.trader.ui import QtCore, QtWidgets

from ..constant import SlippageModel, FillMode
from ..engine.slippage_engine import SlippageConfig
from ..engine.fill_engine import FillConfig

_BG  = "#1e1e2e"
_FG  = "#cdd6f4"
_MUT = "#6c7086"

_LABEL_STYLE = f"color: {_FG}; font-size: 12px;"
_INPUT_STYLE = (
    "QDoubleSpinBox, QSpinBox, QComboBox {"
    " background: #313244; color: #cdd6f4; border: 1px solid #45475a;"
    " border-radius: 3px; padding: 2px 6px; font-size: 12px; }"
)


class SlippageTab(QtWidgets.QWidget):
    """滑点模型配置 + 历史分析 Tab（Phase 2 实现）。"""

    # 配置变更信号：(SlippageConfig, FillConfig)
    config_changed = QtCore.Signal(object, object)

    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self._slippage_records: list[float] = []   # 历史滑点百分比列表
        self._init_ui()

    def _init_ui(self) -> None:
        root = QtWidgets.QHBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(12)

        # 左侧配置区
        root.addWidget(self._build_config_panel(), stretch=0)

        # 右侧统计区
        root.addWidget(self._build_stats_panel(), stretch=1)

    # ------------------------------------------------------------------ #
    #  左侧：配置面板
    # ------------------------------------------------------------------ #

    def _build_config_panel(self) -> QtWidgets.QWidget:
        panel = QtWidgets.QGroupBox("滑点 & 成交配置")
        panel.setFixedWidth(280)
        panel.setStyleSheet(
            "QGroupBox { color: #cdd6f4; font-size: 12px; font-weight: bold;"
            " border: 1px solid #45475a; border-radius: 4px; margin-top: 6px; }"
            "QGroupBox::title { subcontrol-origin: margin; padding: 0 4px; }"
        )
        form = QtWidgets.QFormLayout(panel)
        form.setContentsMargins(10, 16, 10, 10)
        form.setSpacing(8)
        form.setLabelAlignment(QtCore.Qt.AlignmentFlag.AlignRight)

        # ── 滑点模型选择 ──────────────────────────────────────────────────
        self._cmb_model = QtWidgets.QComboBox()
        self._cmb_model.addItems(["固定滑点(fixed)", "百分比(percentage)", "波动率(volatility)"])
        self._cmb_model.setStyleSheet(_INPUT_STYLE)
        self._cmb_model.currentIndexChanged.connect(self._on_model_changed)
        form.addRow("滑点模型：", self._cmb_model)

        # ── FIXED 参数 ───────────────────────────────────────────────────
        self._spn_tick_size = self._dbl_spin(0.0001, 10.0, 0.01, 4)
        self._spn_ticks     = QtWidgets.QSpinBox()
        self._spn_ticks.setRange(0, 20)
        self._spn_ticks.setValue(1)
        self._spn_ticks.setStyleSheet(_INPUT_STYLE)
        form.addRow("Tick大小：", self._spn_tick_size)
        form.addRow("Tick数量：", self._spn_ticks)

        # ── PERCENTAGE 参数 ──────────────────────────────────────────────
        self._spn_rate = self._dbl_spin(0.0, 0.05, 0.0002, 4)
        form.addRow("滑点比例：", self._spn_rate)

        # ── VOLATILITY 参数 ──────────────────────────────────────────────
        self._spn_vol_factor  = self._dbl_spin(0.0, 2.0, 0.1, 3)
        self._spn_daily_vol   = self._dbl_spin(0.0, 0.2, 0.015, 4)
        form.addRow("波动率系数：", self._spn_vol_factor)
        form.addRow("日波动率：",   self._spn_daily_vol)

        # ── 噪声 ─────────────────────────────────────────────────────────
        self._spn_noise = self._dbl_spin(0.0, 1.0, 0.2, 2)
        form.addRow("噪声比例：", self._spn_noise)

        # ── 分隔线 ───────────────────────────────────────────────────────
        sep = QtWidgets.QFrame()
        sep.setFrameShape(QtWidgets.QFrame.Shape.HLine)
        sep.setStyleSheet("color: #45475a;")
        form.addRow(sep)

        # ── 成交模式 ─────────────────────────────────────────────────────
        self._cmb_fill = QtWidgets.QComboBox()
        self._cmb_fill.addItems(["立即全成(immediate)", "随机部分(partial)"])
        self._cmb_fill.setStyleSheet(_INPUT_STYLE)
        form.addRow("成交模式：", self._cmb_fill)

        self._spn_min_ratio = self._dbl_spin(0.0, 1.0, 0.2, 2)
        self._spn_max_ratio = self._dbl_spin(0.0, 1.0, 0.8, 2)
        self._spn_attempts  = QtWidgets.QSpinBox()
        self._spn_attempts.setRange(1, 20)
        self._spn_attempts.setValue(3)
        self._spn_attempts.setStyleSheet(_INPUT_STYLE)
        form.addRow("最小成交比：", self._spn_min_ratio)
        form.addRow("最大成交比：", self._spn_max_ratio)
        form.addRow("最大尝试次：", self._spn_attempts)

        # ── 应用按钮 ─────────────────────────────────────────────────────
        btn = QtWidgets.QPushButton("应用配置")
        btn.setStyleSheet(
            "QPushButton { background: #89b4fa; color: #1e1e2e; border-radius: 4px;"
            " padding: 6px; font-size: 12px; font-weight: bold; }"
            "QPushButton:hover { background: #b4befe; }"
        )
        btn.clicked.connect(self._apply_config)
        form.addRow(btn)

        self._on_model_changed(0)
        return panel

    # ------------------------------------------------------------------ #
    #  右侧：历史滑点统计
    # ------------------------------------------------------------------ #

    def _build_stats_panel(self) -> QtWidgets.QWidget:
        panel = QtWidgets.QGroupBox("历史滑点分析")
        panel.setStyleSheet(
            "QGroupBox { color: #cdd6f4; font-size: 12px; font-weight: bold;"
            " border: 1px solid #45475a; border-radius: 4px; margin-top: 6px; }"
            "QGroupBox::title { subcontrol-origin: margin; padding: 0 4px; }"
        )
        v = QtWidgets.QVBoxLayout(panel)
        v.setContentsMargins(10, 16, 10, 10)
        v.setSpacing(8)

        # 统计卡片行
        v.addWidget(self._build_stat_cards())

        # 简易文本分布（Phase 3 换成图表）
        self._txt_dist = QtWidgets.QTextEdit()
        self._txt_dist.setReadOnly(True)
        self._txt_dist.setStyleSheet(
            "background: #181825; color: #cdd6f4;"
            " font-size: 11px; font-family: monospace;"
        )
        self._txt_dist.setPlaceholderText("执行订单后将在此显示滑点分布…")
        v.addWidget(self._txt_dist, stretch=1)
        return panel

    def _build_stat_cards(self) -> QtWidgets.QWidget:
        w = QtWidgets.QWidget()
        w.setStyleSheet("background: #181825; border-radius: 4px;")
        h = QtWidgets.QHBoxLayout(w)
        h.setContentsMargins(8, 4, 8, 4)
        h.setSpacing(20)
        cards = [
            ("总执行数",    "0",    _FG),
            ("平均滑点%",   "—",    "#f9e2af"),
            ("最大滑点%",   "—",    "#f38ba8"),
            ("最小滑点%",   "—",    "#a6e3a1"),
            ("滑点标准差%", "—",    _FG),
        ]
        self._card_lbls: dict[str, QtWidgets.QLabel] = {}
        for name, val, color in cards:
            col = QtWidgets.QVBoxLayout()
            col.setSpacing(1)
            ln = QtWidgets.QLabel(name)
            ln.setStyleSheet(f"color: {_MUT}; font-size: 10px;")
            ln.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
            lv = QtWidgets.QLabel(val)
            lv.setStyleSheet(f"color: {color}; font-size: 14px; font-weight: bold;")
            lv.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
            col.addWidget(ln)
            col.addWidget(lv)
            self._card_lbls[name] = lv
            h.addLayout(col)
        h.addStretch()
        return w

    # ------------------------------------------------------------------ #
    #  公开接口
    # ------------------------------------------------------------------ #

    def add_slippage(self, slippage_pct: float) -> None:
        """追加一笔滑点记录（每次执行完成后调用）。"""
        self._slippage_records.append(slippage_pct)
        self._refresh_stats()

    def refresh_from_records(self, slippage_pcts: list[float]) -> None:
        """全量刷新。"""
        self._slippage_records = list(slippage_pcts)
        self._refresh_stats()

    def get_slippage_config(self) -> SlippageConfig:
        """读取当前 UI 配置，返回 SlippageConfig。"""
        idx = self._cmb_model.currentIndex()
        model_map = {
            0: SlippageModel.FIXED,
            1: SlippageModel.PERCENTAGE,
            2: SlippageModel.VOLATILITY,
        }
        return SlippageConfig(
            model       = model_map.get(idx, SlippageModel.FIXED),
            tick_size   = self._spn_tick_size.value(),
            ticks       = self._spn_ticks.value(),
            rate        = self._spn_rate.value(),
            vol_factor  = self._spn_vol_factor.value(),
            daily_vol   = self._spn_daily_vol.value(),
            noise_ratio = self._spn_noise.value(),
        )

    def get_fill_config(self) -> FillConfig:
        """读取当前 UI 配置，返回 FillConfig。"""
        idx = self._cmb_fill.currentIndex()
        mode = FillMode.IMMEDIATE if idx == 0 else FillMode.PARTIAL
        return FillConfig(
            mode            = mode,
            min_fill_ratio  = self._spn_min_ratio.value(),
            max_fill_ratio  = self._spn_max_ratio.value(),
            fill_attempts   = self._spn_attempts.value(),
        )

    def clear(self) -> None:
        self._slippage_records.clear()
        self._refresh_stats()

    # ------------------------------------------------------------------ #
    #  内部槽
    # ------------------------------------------------------------------ #

    def _on_model_changed(self, idx: int) -> None:
        """切换模型时控制参数可见性。"""
        is_fixed = (idx == 0)
        is_pct   = (idx == 1)
        is_vol   = (idx == 2)
        self._spn_tick_size.setEnabled(is_fixed or is_vol)
        self._spn_ticks.setEnabled(is_fixed)
        self._spn_rate.setEnabled(is_pct)
        self._spn_vol_factor.setEnabled(is_vol)
        self._spn_daily_vol.setEnabled(is_vol)

    def _apply_config(self) -> None:
        self.config_changed.emit(
            self.get_slippage_config(),
            self.get_fill_config(),
        )

    def _refresh_stats(self) -> None:
        data = self._slippage_records
        n = len(data)
        self._card_lbls["总执行数"].setText(str(n))
        if n == 0:
            for k in ("平均滑点%", "最大滑点%", "最小滑点%", "滑点标准差%"):
                self._card_lbls[k].setText("—")
            self._txt_dist.clear()
            return

        avg = sum(data) / n
        mx  = max(data)
        mn  = min(data)
        var = sum((x - avg) ** 2 for x in data) / n
        std = var ** 0.5

        self._card_lbls["平均滑点%"].setText(f"{avg:.4%}")
        self._card_lbls["最大滑点%"].setText(f"{mx:.4%}")
        self._card_lbls["最小滑点%"].setText(f"{mn:.4%}")
        self._card_lbls["滑点标准差%"].setText(f"{std:.4%}")

        # 简易 ASCII 直方图（10 桶）
        lo, hi = mn, mx
        if hi <= lo:
            self._txt_dist.setPlainText(f"所有滑点相同：{avg:.4%}")
            return

        buckets = 10
        width   = (hi - lo) / buckets
        counts  = [0] * buckets
        for v in data:
            b = min(int((v - lo) / width), buckets - 1)
            counts[b] += 1

        max_c  = max(counts) or 1
        bar_w  = 24
        lines  = [f"滑点分布（共 {n} 笔）\n"]
        for i, c in enumerate(counts):
            lo_b = lo + i * width
            hi_b = lo_b + width
            bar  = "█" * int(bar_w * c / max_c)
            lines.append(f"{lo_b:+.4%}~{hi_b:+.4%} │{bar:<{bar_w}}│ {c}")
        self._txt_dist.setPlainText("\n".join(lines))

    # ------------------------------------------------------------------ #
    #  工具
    # ------------------------------------------------------------------ #

    @staticmethod
    def _dbl_spin(
        lo: float, hi: float, val: float, dec: int
    ) -> QtWidgets.QDoubleSpinBox:
        spn = QtWidgets.QDoubleSpinBox()
        spn.setRange(lo, hi)
        spn.setValue(val)
        spn.setDecimals(dec)
        spn.setSingleStep(10 ** (-dec))
        spn.setStyleSheet(_INPUT_STYLE)
        return spn
