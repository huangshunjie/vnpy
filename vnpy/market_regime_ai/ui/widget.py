"""
market_regime_ai/ui/widget.py  (Phase 5)

MarketRegimeWidget — 主窗口（完整版）。

Phase 5 新增：
  - 订阅 EVENT_DECISION_SIGNAL / EVENT_REGIME_WEIGHT_MODIFIER
    / EVENT_RISK_SIGNAL_OUTPUT / EVENT_CAPITAL_SIGNAL_OUTPUT
  - 左侧侧边栏新增：资本调整 / 风险调整 / 行动建议 / Modifier
  - Phase 标签更新为 Phase 5
  - closeEvent 取消注册全部事件
"""

from __future__ import annotations

from vnpy.trader.ui import QtCore, QtWidgets
from vnpy.trader.engine import MainEngine
from vnpy.event import EventEngine

from ..constant import APP_NAME
from ..event import (
    EVENT_REGIME_DETECTED,
    EVENT_REGIME_CHANGED,
    EVENT_VOLATILITY_UPDATE,
    EVENT_TREND_UPDATE,
    EVENT_LIQUIDITY_UPDATE,
    EVENT_DECISION_SIGNAL,
    EVENT_REGIME_WEIGHT_MODIFIER,
    EVENT_RISK_SIGNAL_OUTPUT,
    EVENT_CAPITAL_SIGNAL_OUTPUT,
    EVENT_INTEGRATION_HEARTBEAT,
)
from .dashboard_tab  import DashboardTab
from .regime_tab     import RegimeTab
from .volatility_tab import VolatilityTab
from .trend_tab      import TrendTab
from .liquidity_tab  import LiquidityTab
from .log_tab        import LogTab

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
_CYN    = "#89dceb"

_REGIME_COLORS = {
    "BULL":     _GRN,  "BEAR":     _RED,
    "SIDEWAYS": _YLW,  "HIGH_VOL": _ORG,
    "LOW_LIQ":  _CYN,  "UNKNOWN":  _MUT,
}
_ACTION_COLORS = {
    "REBALANCE_NOW":    _RED,
    "REDUCE_EXPOSURE":  _ORG,
    "TIGHTEN_RISK":     _YLW,
    "INCREASE_EXPOSURE": _GRN,
    "MAINTAIN":         _MUT,
}


class MarketRegimeWidget(QtWidgets.QMainWindow):
    """Market Regime Intelligence System — 主窗口（Phase 5 完整版）。"""

    widget_name = f"{APP_NAME}Widget"

    def __init__(self, main_engine: MainEngine, event_engine: EventEngine) -> None:
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
        self.setWindowTitle("Market Regime Intelligence System  市场状态智能系统")
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
            f"background: {_PANEL}; border-radius: 8px; border: 1px solid {_BORDER};")
        v = QtWidgets.QVBoxLayout(w)
        v.setContentsMargins(12, 12, 12, 12)
        v.setSpacing(8)

        title = QtWidgets.QLabel("Market Regime AI")
        title.setStyleSheet(
            f"color: {_MAV}; font-size: 12px; font-weight: bold; border: none;")
        title.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        v.addWidget(title)
        v.addWidget(self._sep())

        # ── 状态类卡片 ───────────────────────────────────────────
        self._regime_card = self._make_card("当前状态",   "UNKNOWN",  _MUT)
        self._vol_card    = self._make_card("波动率状态", "---",      _MUT)
        self._trend_card  = self._make_card("趋势方向",   "---",      _MUT)
        self._liq_card    = self._make_card("流动性",     "---",      _MUT)
        self._conf_card   = self._make_card("置信度",     "---",      _MUT)
        self._rec_card    = self._make_card("策略建议",   "NEUTRAL",  _MUT)

        for card in [self._regime_card, self._vol_card, self._trend_card,
                     self._liq_card, self._conf_card, self._rec_card]:
            v.addWidget(card)

        v.addWidget(self._sep())

        # ── Phase 5 决策信号卡片 ─────────────────────────────────
        self._cap_card    = self._make_card("资本调整",   "1.000x",   _MUT)
        self._risk_card   = self._make_card("风险调整",   "1.000x",   _MUT)
        self._action_card = self._make_card("行动建议",   "MAINTAIN", _MUT)
        self._mod_card    = self._make_card("Regime Mod", "1.000",    _MUT)

        for card in [self._cap_card, self._risk_card,
                     self._action_card, self._mod_card]:
            v.addWidget(card)

        v.addStretch()

        self._phase_lbl = QtWidgets.QLabel("Phase 5  System Integration")
        self._phase_lbl.setStyleSheet(f"color: {_MUT}; font-size: 9px; border: none;")
        self._phase_lbl.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        v.addWidget(self._phase_lbl)
        return w

    def _make_card(self, title: str, value: str, color: str) -> QtWidgets.QWidget:
        card = QtWidgets.QWidget()
        card.setStyleSheet(
            f"background: #11111b; border-radius: 6px; border: 1px solid {_BORDER};")
        cv = QtWidgets.QVBoxLayout(card)
        cv.setContentsMargins(8, 5, 8, 5)
        cv.setSpacing(1)
        tl = QtWidgets.QLabel(title)
        tl.setStyleSheet(f"color: {_MUT}; font-size: 9px; border: none;")
        vl = QtWidgets.QLabel(value)
        vl.setStyleSheet(
            f"color: {color}; font-size: 13px; font-weight: bold; border: none;")
        vl.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        cv.addWidget(tl)
        cv.addWidget(vl)
        card._value_label = vl
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

        self.dashboard_tab  = DashboardTab(self.engine)
        self.regime_tab     = RegimeTab(self.engine)
        self.volatility_tab = VolatilityTab(self.engine)
        self.trend_tab      = TrendTab(self.engine)
        self.liquidity_tab  = LiquidityTab(self.engine)
        self.log_tab        = LogTab(self.engine)

        self.tab_widget.addTab(self.dashboard_tab,  "Dashboard")
        self.tab_widget.addTab(self.regime_tab,     "Regime Detection")
        self.tab_widget.addTab(self.volatility_tab, "Volatility")
        self.tab_widget.addTab(self.trend_tab,      "Trend")
        self.tab_widget.addTab(self.liquidity_tab,  "Liquidity")
        self.tab_widget.addTab(self.log_tab,        "Logs")

        return self.tab_widget

    # ------------------------------------------------------------------ #
    #  事件注册 / 取消注册
    # ------------------------------------------------------------------ #

    def _register_events(self) -> None:
        self._handlers = {
            EVENT_REGIME_DETECTED:        self._on_regime_event,
            EVENT_REGIME_CHANGED:         self._on_regime_event,
            EVENT_VOLATILITY_UPDATE:      self._on_volatility_update,
            EVENT_TREND_UPDATE:           self._on_trend_update,
            EVENT_LIQUIDITY_UPDATE:       self._on_liquidity_update,
            EVENT_DECISION_SIGNAL:        self._on_decision_signal,
            EVENT_REGIME_WEIGHT_MODIFIER: self._on_modifier_event,
            EVENT_RISK_SIGNAL_OUTPUT:     self._on_risk_signal,
            EVENT_CAPITAL_SIGNAL_OUTPUT:  self._on_capital_signal,
            EVENT_INTEGRATION_HEARTBEAT:  self._on_heartbeat,
        }
        for event_type, handler in self._handlers.items():
            self.event_engine.register(event_type, handler)

    def _unregister_events(self) -> None:
        for event_type, handler in self._handlers.items():
            try:
                self.event_engine.unregister(event_type, handler)
            except Exception:
                pass

    # ------------------------------------------------------------------ #
    #  事件回调
    # ------------------------------------------------------------------ #

    def _on_regime_event(self, event) -> None:
        data   = event.data or {}
        regime = data.get("regime", "unknown").upper()
        color  = _REGIME_COLORS.get(regime, _MUT)
        self._set_card(self._regime_card, regime, color)
        conf = data.get("confidence_score", 0.0)
        if conf:
            self._set_card(self._conf_card, f"{float(conf):.1%}", _MUT)
        rec = data.get("recommendation", "")
        if rec:
            self._set_card(self._rec_card, rec.upper(), _MUT)
        try:
            self.regime_tab.update_from_event(data)
            self.dashboard_tab.update_from_event(data)
        except Exception:
            pass

    def _on_volatility_update(self, event) -> None:
        data = event.data or {}
        self._set_card(self._vol_card, data.get("regime", "---").upper(), _MUT)
        try:
            self.volatility_tab.update_from_event(data)
        except Exception:
            pass

    def _on_trend_update(self, event) -> None:
        data = event.data or {}
        self._set_card(self._trend_card, data.get("direction", "---").upper(), _MUT)
        try:
            self.trend_tab.update_from_event(data)
        except Exception:
            pass

    def _on_liquidity_update(self, event) -> None:
        data = event.data or {}
        self._set_card(self._liq_card, data.get("level", "---").upper(), _MUT)
        try:
            self.liquidity_tab.update_from_event(data)
        except Exception:
            pass

    def _on_decision_signal(self, event) -> None:
        data   = event.data or {}
        cap    = float(data.get("capital_adjustment", 1.0))
        risk   = float(data.get("risk_adjustment",    1.0))
        action = data.get("action", "MAINTAIN")
        cap_c  = _GRN if cap  > 1.0 else (_RED if cap  < 0.8 else _MUT)
        risk_c = _GRN if risk > 1.0 else (_RED if risk < 0.7 else _MUT)
        ac     = _ACTION_COLORS.get(action, _MUT)
        self._set_card(self._cap_card,    f"{cap:.3f}x",  cap_c)
        self._set_card(self._risk_card,   f"{risk:.3f}x", risk_c)
        self._set_card(self._action_card, action,          ac)
        try:
            self.dashboard_tab.update_decision_from_event(data)
        except Exception:
            pass

    def _on_modifier_event(self, event) -> None:
        data = event.data or {}
        mod  = float(data.get("regime_weight_modifier", 1.0))
        mod_c = _GRN if mod > 1.05 else (_RED if mod < 0.80 else _MUT)
        self._set_card(self._mod_card, f"{mod:.3f}", mod_c)

    def _on_risk_signal(self, event) -> None:
        pass   # 供 Phase 5+ 扩展

    def _on_capital_signal(self, event) -> None:
        pass   # 供 Phase 5+ 扩展

    def _on_heartbeat(self, event) -> None:
        data = event.data or {}
        status = data.get("status", "")
        try:
            self.log_tab.append_log(
                f"[Integration] heartbeat: {status}"
                f"  capital_ai={data.get('capital_ai_available')}"
                f"  quant_os={data.get('quant_os_available')}"
                f"  db={data.get('db_available')}"
            )
        except Exception:
            pass

    # ------------------------------------------------------------------ #
    #  工具方法
    # ------------------------------------------------------------------ #

    def _set_card(self, card: QtWidgets.QWidget, text: str, color: str) -> None:
        try:
            card._value_label.setText(text)
            card._value_label.setStyleSheet(
                f"color: {color}; font-size: 13px; font-weight: bold; border: none;")
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
