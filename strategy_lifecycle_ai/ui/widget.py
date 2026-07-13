"""
strategy_lifecycle_ai/ui/widget.py  (Phase 1)

StrategyLifecycleWidget — 主窗口（Phase 1 骨架）。

布局：
  左侧：策略状态概览面板
  右侧：TabWidget（6 个 Tab）
"""

from __future__ import annotations

from vnpy.trader.ui import QtCore, QtWidgets
from vnpy.trader.engine import MainEngine
from vnpy.event import EventEngine

from ..constant import APP_NAME
from ..event import (
    EVENT_STRATEGY_REGISTERED,
    EVENT_STRATEGY_UPDATED,
    EVENT_STRATEGY_DECAY_DETECTED,
    EVENT_STRATEGY_EVOLVED,
    EVENT_STRATEGY_RETIRED,
    EVENT_LIFECYCLE_HEARTBEAT,
)
from .registry_tab    import RegistryTab
from .performance_tab import PerformanceTab
from .decay_tab       import DecayTab
from .evolution_tab   import EvolutionTab
from .retirement_tab  import RetirementTab
from .log_tab         import LogTab

_BG     = "#1e1e2e"
_PANEL  = "#181825"
_BORDER = "#45475a"
_FG     = "#cdd6f4"
_MUT    = "#6c7086"
_GRN    = "#a6e3a1"
_RED    = "#f38ba8"
_YLW    = "#f9e2af"
_MAV    = "#cba6f7"
_ORG    = "#fab387"
_BLU    = "#89b4fa"

_PHASE_COLORS = {
    "REGISTERED": _MUT,
    "INCUBATION": _BLU,
    "LIVE":       _GRN,
    "PEAK":       _YLW,
    "DECAY":      _ORG,
    "RECOVERING": "#89dceb",
    "RETIRED":    _RED,
    "ARCHIVED":   _MUT,
}


class StrategyLifecycleWidget(QtWidgets.QMainWindow):
    """Strategy Lifecycle Intelligence System — 主窗口（Phase 1）。"""

    widget_name = f"{APP_NAME}Widget"

    def __init__(
        self,
        main_engine:  MainEngine,
        event_engine: EventEngine,
    ) -> None:
        super().__init__()
        self.main_engine  = main_engine
        self.event_engine = event_engine
        self.engine = main_engine.get_engine(APP_NAME)

        self._init_ui()
        self._register_events()

        if self.engine:
            self.engine.init()
            self.engine.start()

    # ------------------------------------------------------------------ #
    #  UI 构建
    # ------------------------------------------------------------------ #

    def _init_ui(self) -> None:
        self.setWindowTitle(
            "Strategy Lifecycle Intelligence System  策略生命周期智能系统")
        self.setMinimumSize(1320, 820)
        self.setStyleSheet(f"QMainWindow {{ background: {_BG}; }}")

        central = QtWidgets.QWidget()
        self.setCentralWidget(central)
        root = QtWidgets.QHBoxLayout(central)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(8)
        root.addWidget(self._build_side_panel(), stretch=0)
        root.addWidget(self._build_tab_widget(), stretch=1)

    def _build_side_panel(self) -> QtWidgets.QWidget:
        w = QtWidgets.QWidget()
        w.setFixedWidth(210)
        w.setStyleSheet(
            f"background: {_PANEL}; border-radius: 8px;"
            f" border: 1px solid {_BORDER};")
        v = QtWidgets.QVBoxLayout(w)
        v.setContentsMargins(12, 12, 12, 12)
        v.setSpacing(8)

        title = QtWidgets.QLabel("Strategy Lifecycle AI")
        title.setStyleSheet(
            f"color: {_MAV}; font-size: 12px; font-weight: bold; border: none;")
        title.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        v.addWidget(title)
        v.addWidget(self._sep())

        # 统计卡片
        self._total_card     = self._card("策略总数",     "0",        _FG)
        self._live_card      = self._card("运行中",        "0",        _GRN)
        self._decay_card     = self._card("衰减中",        "0",        _ORG)
        self._retired_card   = self._card("已退役",        "0",        _RED)
        self._peak_card      = self._card("峰值阶段",      "0",        _YLW)
        self._incub_card     = self._card("孵化期",        "0",        _BLU)

        for card in [self._total_card, self._live_card, self._decay_card,
                     self._retired_card, self._peak_card, self._incub_card]:
            v.addWidget(card)

        v.addWidget(self._sep())

        # 系统状态卡片
        self._qos_card       = self._card("Quant OS",      "---",      _MUT)
        self._portfolio_card = self._card("Portfolio",     "---",      _MUT)
        self._capital_card   = self._card("Capital AI",    "---",      _MUT)

        for card in [self._qos_card, self._portfolio_card, self._capital_card]:
            v.addWidget(card)

        v.addStretch()

        phase_lbl = QtWidgets.QLabel("Phase 1  Skeleton")
        phase_lbl.setStyleSheet(
            f"color: {_MUT}; font-size: 9px; border: none;")
        phase_lbl.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        v.addWidget(phase_lbl)
        return w

    def _card(self, title: str, value: str, color: str) -> QtWidgets.QWidget:
        card = QtWidgets.QWidget()
        card.setStyleSheet(
            f"background: #11111b; border-radius: 6px;"
            f" border: 1px solid {_BORDER};")
        cv = QtWidgets.QVBoxLayout(card)
        cv.setContentsMargins(8, 5, 8, 5)
        cv.setSpacing(1)
        tl = QtWidgets.QLabel(title)
        tl.setStyleSheet(f"color: {_MUT}; font-size: 9px; border: none;")
        vl = QtWidgets.QLabel(value)
        vl.setStyleSheet(
            f"color: {color}; font-size: 14px;"
            f" font-weight: bold; border: none;")
        vl.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        cv.addWidget(tl)
        cv.addWidget(vl)
        card._vl = vl
        return card

    def _sep(self) -> QtWidgets.QFrame:
        s = QtWidgets.QFrame()
        s.setFrameShape(QtWidgets.QFrame.Shape.HLine)
        s.setStyleSheet(f"border: none; border-top: 1px solid {_BORDER};")
        return s

    def _build_tab_widget(self) -> QtWidgets.QTabWidget:
        self.tab_widget = QtWidgets.QTabWidget()
        self.tab_widget.setStyleSheet(f"""
            QTabWidget::pane {{
                background: {_PANEL};
                border: 1px solid {_BORDER};
                border-radius: 4px;
            }}
            QTabBar::tab {{
                background: #11111b;
                color: {_MUT};
                padding: 6px 16px;
                border: 1px solid {_BORDER};
                border-bottom: none;
                border-radius: 4px 4px 0 0;
                font-size: 12px;
            }}
            QTabBar::tab:selected {{
                background: {_PANEL};
                color: {_MAV};
                border-bottom: 2px solid {_MAV};
            }}
            QTabBar::tab:hover {{ color: {_FG}; }}
        """)

        self.registry_tab    = RegistryTab(self.engine)
        self.performance_tab = PerformanceTab(self.engine)
        self.decay_tab       = DecayTab(self.engine)
        self.evolution_tab   = EvolutionTab(self.engine)
        self.retirement_tab  = RetirementTab(self.engine)
        self.log_tab         = LogTab(self.engine)

        self.tab_widget.addTab(self.registry_tab,    "Registry")
        self.tab_widget.addTab(self.performance_tab, "Performance")
        self.tab_widget.addTab(self.decay_tab,       "Decay")
        self.tab_widget.addTab(self.evolution_tab,   "Evolution")
        self.tab_widget.addTab(self.retirement_tab,  "Retirement")
        self.tab_widget.addTab(self.log_tab,         "Logs")

        return self.tab_widget

    # ------------------------------------------------------------------ #
    #  事件注册
    # ------------------------------------------------------------------ #

    def _register_events(self) -> None:
        self._handlers = {
            EVENT_STRATEGY_REGISTERED:     self._on_strategy_event,
            EVENT_STRATEGY_UPDATED:        self._on_strategy_event,
            EVENT_STRATEGY_DECAY_DETECTED: self._on_decay_event,
            EVENT_STRATEGY_EVOLVED:        self._on_evolution_event,
            EVENT_STRATEGY_RETIRED:        self._on_retirement_event,
            EVENT_LIFECYCLE_HEARTBEAT:     self._on_heartbeat,
        }
        for et, handler in self._handlers.items():
            self.event_engine.register(et, handler)

    def _unregister_events(self) -> None:
        for et, handler in self._handlers.items():
            try:
                self.event_engine.unregister(et, handler)
            except Exception:
                pass

    # ------------------------------------------------------------------ #
    #  事件回调
    # ------------------------------------------------------------------ #

    def _on_strategy_event(self, event) -> None:
        self._refresh_counts()
        try:
            self.registry_tab.update_from_event(event.data or {})
        except Exception:
            pass

    def _on_decay_event(self, event) -> None:
        self._refresh_counts()
        try:
            self.decay_tab.update_from_event(event.data or {})
        except Exception:
            pass

    def _on_evolution_event(self, event) -> None:
        try:
            self.evolution_tab.update_from_event(event.data or {})
        except Exception:
            pass

    def _on_retirement_event(self, event) -> None:
        self._refresh_counts()
        try:
            self.retirement_tab.update_from_event(event.data or {})
        except Exception:
            pass

    def _on_heartbeat(self, event) -> None:
        data = event.data or {}
        self._refresh_counts()
        try:
            self.log_tab.append_log(
                "[Lifecycle] heartbeat"
                f"  strategies={data.get('strategy_count', 0)}"
                f"  phase={data.get('phase', 1)}"
            )
        except Exception:
            pass
        # 更新系统可用性卡片
        try:
            summ = self.engine.get_summary() if self.engine else {}
            self._set_card(self._qos_card,
                "OK" if summ.get("quant_os") else "N/A",
                _GRN if summ.get("quant_os") else _MUT)
            self._set_card(self._portfolio_card,
                "OK" if summ.get("portfolio_engine") else "N/A",
                _GRN if summ.get("portfolio_engine") else _MUT)
            self._set_card(self._capital_card,
                "OK" if summ.get("capital_ai") else "N/A",
                _GRN if summ.get("capital_ai") else _MUT)
        except Exception:
            pass

    # ------------------------------------------------------------------ #
    #  计数刷新
    # ------------------------------------------------------------------ #

    def _refresh_counts(self) -> None:
        if self.engine is None:
            return
        try:
            from ..constant import StrategyPhase
            strategies = self.engine.get_all_strategies()
            total   = len(strategies)
            live    = sum(1 for s in strategies if s.phase == StrategyPhase.LIVE)
            decay   = sum(1 for s in strategies if s.phase == StrategyPhase.DECAY)
            retired = sum(1 for s in strategies if s.phase == StrategyPhase.RETIRED)
            peak    = sum(1 for s in strategies if s.phase == StrategyPhase.PEAK)
            incub   = sum(1 for s in strategies if s.phase == StrategyPhase.INCUBATION)

            self._set_card(self._total_card,   str(total),   _FG)
            self._set_card(self._live_card,    str(live),    _GRN)
            self._set_card(self._decay_card,   str(decay),   _ORG  if decay  else _MUT)
            self._set_card(self._retired_card, str(retired), _RED  if retired else _MUT)
            self._set_card(self._peak_card,    str(peak),    _YLW  if peak   else _MUT)
            self._set_card(self._incub_card,   str(incub),   _BLU  if incub  else _MUT)
        except Exception:
            pass

    def _set_card(self, card: QtWidgets.QWidget, text: str, color: str) -> None:
        try:
            card._vl.setText(text)
            card._vl.setStyleSheet(
                f"color: {color}; font-size: 14px;"
                f" font-weight: bold; border: none;")
        except Exception:
            pass

    # ------------------------------------------------------------------ #
    #  生命周期
    # ------------------------------------------------------------------ #

    def closeEvent(self, event) -> None:
        if self.engine:
            self.engine.stop()
        self._unregister_events()
        event.accept()
