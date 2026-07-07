"""
temporal_intelligence_ai/ui/cycle_tab.py

Market Cycle Tab — 市场周期可视化面板（Phase 2）。

布局：
  上方：当前周期状态卡片（阶段 / Regime / 置信度 / 持续时长）
  中部：指标仪表盘（波动率 / 趋势 / 动量 / 回撤 / 宽度 / 相关性）
  下方：周期历史时间线（最近 N 次识别结果）
"""
from __future__ import annotations

from typing import Optional, List

from vnpy.trader.ui import QtCore, QtWidgets, QtGui
from vnpy.trader.engine import MainEngine, EventEngine
from vnpy.event import Event

from ..event import APP_NAME, EVENT_CYCLE_DETECTED
from ..constant import CyclePhase, RegimeType

_BG     = "#1e1e2e"
_DARK   = "#181825"
_BORDER = "#45475a"
_FG     = "#cdd6f4"
_MUT    = "#6c7086"
_BLUE   = "#89b4fa"
_GRN    = "#a6e3a1"
_YLW    = "#f9e2af"
_RED    = "#f38ba8"
_MAV    = "#cba6f7"
_HEAD   = "#313244"
_CYN    = "#89dceb"
_ORG    = "#fab387"

_PHASE_COLORS: dict[str, str] = {
    CyclePhase.EXPANSION.value:   _GRN,
    CyclePhase.PEAK.value:        _YLW,
    CyclePhase.CONTRACTION.value: _RED,
    CyclePhase.TROUGH.value:      _BLUE,
    CyclePhase.TRANSITION.value:  _MAV,
    CyclePhase.UNKNOWN.value:     _MUT,
}

_PHASE_LABELS: dict[str, str] = {
    CyclePhase.EXPANSION.value:   "扩张期  Expansion",
    CyclePhase.PEAK.value:        "顶部    Peak",
    CyclePhase.CONTRACTION.value: "收缩期  Contraction",
    CyclePhase.TROUGH.value:      "底部    Trough",
    CyclePhase.TRANSITION.value:  "过渡期  Transition",
    CyclePhase.UNKNOWN.value:     "未知    Unknown",
}

_REGIME_COLORS: dict[str, str] = {
    RegimeType.BULL_QUIET.value:    _GRN,
    RegimeType.BULL_VOLATILE.value: _YLW,
    RegimeType.BEAR_QUIET.value:    _BLUE,
    RegimeType.BEAR_VOLATILE.value: _RED,
    RegimeType.SIDEWAYS.value:      _MAV,
    RegimeType.CRISIS.value:        _RED,
    RegimeType.UNKNOWN.value:       _MUT,
}


class _MetricCard(QtWidgets.QWidget):
    """单指标显示卡片：标题 + 数值 + 进度条。"""

    def __init__(self, title: str, color: str, parent=None) -> None:
        super().__init__(parent)
        self._color = color
        self.setStyleSheet(
            f"background:{_HEAD};border-radius:6px;border:1px solid {_BORDER};")
        self.setFixedHeight(82)

        vb = QtWidgets.QVBoxLayout(self)
        vb.setContentsMargins(10, 8, 10, 8)
        vb.setSpacing(4)

        self._title = QtWidgets.QLabel(title)
        self._title.setStyleSheet(
            f"color:{_MUT};font-size:10px;border:none;background:transparent;")

        self._value = QtWidgets.QLabel("--")
        self._value.setStyleSheet(
            f"color:{color};font-size:18px;font-weight:bold;"
            f"border:none;background:transparent;")

        self._bar = QtWidgets.QProgressBar()
        self._bar.setRange(0, 1000)
        self._bar.setValue(0)
        self._bar.setTextVisible(False)
        self._bar.setFixedHeight(4)
        self._bar.setStyleSheet(
            f"QProgressBar{{background:{_BORDER};border:none;border-radius:2px;}}"
            f"QProgressBar::chunk{{background:{color};border-radius:2px;}}")

        vb.addWidget(self._title)
        vb.addWidget(self._value)
        vb.addWidget(self._bar)

    def update_value(self, raw: float, display: str,
                     bar_pct: float = 0.5) -> None:
        """
        Args:
            raw:     原始浮点值（用于颜色判断）
            display: 显示字符串
            bar_pct: 进度条填充比例 [0, 1]
        """
        self._value.setText(display)
        self._bar.setValue(int(max(0.0, min(1.0, bar_pct)) * 1000))


class _PhaseCard(QtWidgets.QWidget):
    """当前周期阶段大卡片。"""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setStyleSheet(
            f"background:{_HEAD};border-radius:8px;border:1px solid {_BORDER};")
        self.setFixedHeight(110)

        hb = QtWidgets.QHBoxLayout(self)
        hb.setContentsMargins(20, 12, 20, 12)
        hb.setSpacing(24)

        # 左：阶段图标 + 名称
        left = QtWidgets.QVBoxLayout()
        self._icon  = QtWidgets.QLabel("◈")
        self._icon.setStyleSheet(
            f"color:{_MUT};font-size:36px;border:none;background:transparent;")
        self._phase_lbl = QtWidgets.QLabel("--")
        self._phase_lbl.setStyleSheet(
            f"color:{_MUT};font-size:16px;font-weight:bold;"
            f"border:none;background:transparent;")
        left.addWidget(self._icon)
        left.addWidget(self._phase_lbl)
        hb.addLayout(left)

        hb.addStretch()

        # 右：数值列
        right = QtWidgets.QGridLayout()
        right.setSpacing(8)
        self._labels: dict[str, QtWidgets.QLabel] = {}
        pairs = [
            ("regime",     "Regime",     0, 0),
            ("confidence", "置信度",     0, 2),
            ("duration",   "持续 Bars",  1, 0),
            ("transitioning", "转换中",  1, 2),
        ]
        for key, text, row, col in pairs:
            k_lbl = QtWidgets.QLabel(text)
            k_lbl.setStyleSheet(
                f"color:{_MUT};font-size:10px;border:none;background:transparent;")
            v_lbl = QtWidgets.QLabel("--")
            v_lbl.setStyleSheet(
                f"color:{_FG};font-size:13px;font-weight:bold;"
                f"border:none;background:transparent;")
            right.addWidget(k_lbl, row, col)
            right.addWidget(v_lbl, row, col + 1)
            self._labels[key] = v_lbl

        hb.addLayout(right)

    def update_state(self, state) -> None:
        color = _PHASE_COLORS.get(state.phase.value, _MUT)
        label = _PHASE_LABELS.get(state.phase.value, state.phase.value)

        self._icon.setStyleSheet(
            f"color:{color};font-size:36px;border:none;background:transparent;")
        self._phase_lbl.setStyleSheet(
            f"color:{color};font-size:16px;font-weight:bold;"
            f"border:none;background:transparent;")
        self._phase_lbl.setText(label)

        reg_color = _REGIME_COLORS.get(state.regime.value, _MUT)
        self._labels["regime"].setStyleSheet(
            f"color:{reg_color};font-size:13px;font-weight:bold;"
            f"border:none;background:transparent;")
        self._labels["regime"].setText(state.regime.value)
        self._labels["confidence"].setText(f"{state.confidence:.1%}")
        self._labels["duration"].setText(str(state.phase_duration))
        self._labels["transitioning"].setText(
            "是" if state.is_transitioning else "否")


class _HistoryTimeline(QtWidgets.QWidget):
    """底部周期历史时间线（横向色块序列）。"""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setFixedHeight(60)
        self._phases: list[str] = []
        self.setStyleSheet(
            f"background:{_DARK};border-radius:4px;border:1px solid {_BORDER};")

    def set_phases(self, phases: list[str]) -> None:
        self._phases = phases[-120:]  # 最多显示最近 120 条
        self.update()

    def paintEvent(self, event) -> None:
        if not self._phases:
            return
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)

        w = self.width()
        h = self.height()
        n = len(self._phases)
        bar_w = max(2, w // n)
        bar_h = h - 16

        for i, phase in enumerate(self._phases):
            color = _PHASE_COLORS.get(phase, _MUT)
            x = i * bar_w
            painter.fillRect(
                x, 8, bar_w - 1, bar_h,
                QtGui.QColor(color))

        painter.setPen(QtGui.QColor(_MUT))
        painter.setFont(QtGui.QFont("monospace", 8))
        painter.drawText(4, h - 2, f"← 最近 {n} 次识别")
        painter.end()


class CycleTab(QtWidgets.QWidget):
    """
    市场周期 Tab 主面板。

    订阅 EVENT_CYCLE_DETECTED 事件，实时更新所有子组件。
    """

    def __init__(self, main_engine: MainEngine,
                 event_engine: EventEngine) -> None:
        super().__init__()
        self._main_engine  = main_engine
        self._event_engine = event_engine
        self._engine       = main_engine.get_engine(APP_NAME)

        self._init_ui()
        self._register_events()

    # ── UI ────────────────────────────────────────────────────────────

    def _init_ui(self) -> None:
        self.setStyleSheet(f"background:{_DARK};")

        root = QtWidgets.QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(10)

        # 顶部：阶段大卡片
        self._phase_card = _PhaseCard()
        root.addWidget(self._phase_card)

        # 中部：6 指标卡片网格
        self._metric_cards: dict[str, _MetricCard] = {}
        metric_defs = [
            ("volatility",     "波动率 (Ann.)",     _ORG),
            ("trend_strength", "趋势强度",           _GRN),
            ("momentum",       "动量",               _BLUE),
            ("drawdown",       "最大回撤",           _RED),
            ("breadth",        "市场宽度",           _YLW),
            ("correlation",    "跨资产相关性",       _MAV),
        ]
        grid = QtWidgets.QGridLayout()
        grid.setSpacing(8)
        for idx, (key, title, color) in enumerate(metric_defs):
            card = _MetricCard(title, color)
            self._metric_cards[key] = card
            grid.addWidget(card, idx // 3, idx % 3)
        root.addLayout(grid)

        # 底部工具栏
        toolbar = QtWidgets.QHBoxLayout()
        btn_analyze = QtWidgets.QPushButton("▶  立即分析")
        btn_analyze.setStyleSheet(
            f"QPushButton{{background:{_CYN};color:#1e1e2e;font-weight:bold;"
            f"border:none;border-radius:4px;padding:7px 16px;font-size:11px;}}"
            f"QPushButton:hover{{background:#74c7ec;}}")
        btn_analyze.clicked.connect(self._on_analyze)
        toolbar.addWidget(btn_analyze)

        self._ts_label = QtWidgets.QLabel("最后分析：--")
        self._ts_label.setStyleSheet(
            f"color:{_MUT};font-size:10px;border:none;background:transparent;")
        toolbar.addStretch()
        toolbar.addWidget(self._ts_label)
        root.addLayout(toolbar)

        # 历史时间线
        timeline_title = QtWidgets.QLabel("周期历史时间线")
        timeline_title.setStyleSheet(
            f"color:{_MUT};font-size:10px;border:none;background:transparent;")
        root.addWidget(timeline_title)

        self._timeline = _HistoryTimeline()
        root.addWidget(self._timeline)

        # 图例
        legend_row = QtWidgets.QHBoxLayout()
        legend_row.setSpacing(12)
        for phase, color in _PHASE_COLORS.items():
            if phase == CyclePhase.UNKNOWN.value:
                continue
            dot = QtWidgets.QLabel(f"■ {phase}")
            dot.setStyleSheet(
                f"color:{color};font-size:10px;border:none;background:transparent;")
            legend_row.addWidget(dot)
        legend_row.addStretch()
        root.addLayout(legend_row)

    # ── events ────────────────────────────────────────────────────────

    def _register_events(self) -> None:
        self._event_engine.register(
            EVENT_CYCLE_DETECTED, self._on_cycle_event)

    def _on_cycle_event(self, event: Event) -> None:
        state = event.data
        if state is None:
            return
        # Qt 跨线程安全：用 QMetaObject invokeMethod 或直接 queued signal
        # 这里使用 QTimer.singleShot(0) 确保在主线程更新 UI
        QtCore.QTimer.singleShot(0, lambda: self._update_display(state))

    def _update_display(self, state) -> None:
        self._phase_card.update_state(state)
        m = state.metrics

        def pct_bar(v: float, lo: float, hi: float) -> float:
            if hi == lo:
                return 0.5
            return max(0.0, min(1.0, (v - lo) / (hi - lo)))

        updates = [
            ("volatility",     m.volatility,     f"{m.volatility:.2%}",
             pct_bar(m.volatility, 0.0, 0.6)),
            ("trend_strength", m.trend_strength,  f"{m.trend_strength:+.3f}",
             pct_bar(m.trend_strength, -1.0, 1.0)),
            ("momentum",       m.momentum,        f"{m.momentum:+.2%}",
             pct_bar(m.momentum, -0.3, 0.3)),
            ("drawdown",       m.drawdown,        f"{m.drawdown:.2%}",
             pct_bar(abs(m.drawdown), 0.0, 0.5)),
            ("breadth",        m.breadth,         f"{m.breadth:.1%}",
             m.breadth),
            ("correlation",    m.correlation,     f"{m.correlation:+.3f}",
             pct_bar(m.correlation, -1.0, 1.0)),
        ]
        for key, raw, disp, bar in updates:
            self._metric_cards[key].update_value(raw, disp, bar)

        self._ts_label.setText(
            f"最后分析：{state.timestamp.strftime('%Y-%m-%d %H:%M:%S')}")

        history = self._engine.get_cycle_history() if self._engine else None
        if history:
            self._timeline.set_phases(history.phases())

    # ── slots ─────────────────────────────────────────────────────────

    def _on_analyze(self) -> None:
        if self._engine:
            self._engine.analyze_cycle()

    def closeEvent(self, event) -> None:
        self._event_engine.unregister(
            EVENT_CYCLE_DETECTED, self._on_cycle_event)
        super().closeEvent(event)
