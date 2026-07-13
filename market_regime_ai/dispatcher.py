"""
market_regime_ai/dispatcher.py  (Phase 5)

MarketRegimeEngine — 顶层市场状态调度引擎（完整版）。

Phase 5 新增：
  - MarketDataLoader / FactorLoader / CapitalLoader 数据源接入
  - auto_detect()：从 DatabaseManager 自动加载并运行全链路
  - sync_to_capital_ai()：输出 regime_weight_modifier 事件
  - sync_to_quant_os()：输出 risk/capital 调整信号事件

❌ 不修改 Capital Allocation AI / Quant OS 内部逻辑
✔  通过 EventEngine 事件总线传播信号
"""

from __future__ import annotations
from datetime import datetime

from vnpy.event import EventEngine, Event
from vnpy.trader.engine import BaseEngine, MainEngine

from .constant import APP_NAME, MarketRegime
from .event import (
    EVENT_REGIME_DETECTED, EVENT_REGIME_CHANGED,
    EVENT_VOLATILITY_UPDATE, EVENT_TREND_UPDATE, EVENT_LIQUIDITY_UPDATE,
    EVENT_DECISION_SIGNAL,
    EVENT_REGIME_WEIGHT_MODIFIER, EVENT_RISK_SIGNAL_OUTPUT,
    EVENT_CAPITAL_SIGNAL_OUTPUT, EVENT_INTEGRATION_HEARTBEAT,
)
from .engine.regime_engine     import RegimeEngine
from .engine.volatility_engine import VolatilityEngine
from .engine.trend_engine      import TrendEngine
from .engine.liquidity_engine  import LiquidityEngine
from .engine.decision_engine   import DecisionEngine
from .datasource.market_loader  import MarketDataLoader
from .datasource.factor_loader  import FactorLoader
from .datasource.capital_loader import CapitalLoader
from .model.regime_model    import MarketRegimeState
from .model.volatility_model import VolatilityState
from .model.trend_model     import TrendState
from .model.liquidity_model import LiquidityState
from .model.decision_model  import DecisionSignal

_REGIME_MODIFIER: dict[MarketRegime, float] = {
    MarketRegime.BULL:     1.20,
    MarketRegime.BEAR:     0.70,
    MarketRegime.SIDEWAYS: 0.90,
    MarketRegime.HIGH_VOL: 0.60,
    MarketRegime.LOW_LIQ:  0.75,
    MarketRegime.UNKNOWN:  1.00,
}


class MarketRegimeEngine(BaseEngine):
    """Market Regime Intelligence System — 顶层引擎（Phase 5 完整版）。"""

    engine_name = APP_NAME

    def __init__(self, main_engine: MainEngine, event_engine: EventEngine) -> None:
        super().__init__(main_engine, event_engine, APP_NAME)

        self._started_at:  datetime | None = None
        self._log_records: list[str]       = []

        self._vol_engine      = VolatilityEngine(log_fn=self._log)
        self._trend_engine    = TrendEngine(log_fn=self._log)
        self._liq_engine      = LiquidityEngine(log_fn=self._log)
        self._regime_engine   = RegimeEngine(log_fn=self._log)
        self._decision_engine = DecisionEngine(log_fn=self._log)

        self._market_loader  = MarketDataLoader(main_engine=main_engine)
        self._factor_loader  = FactorLoader(main_engine=main_engine)
        self._capital_loader = CapitalLoader(main_engine=main_engine)

        self._prices:  list[float] = []
        self._volumes: list[float] = []
        self._highs:   list[float] = []
        self._lows:    list[float] = []
        self._tracked_symbols: list[str] = []
        self._sync_count = 0

        self._log(f"[{APP_NAME}] Engine created (Phase 5)")

    # ------------------------------------------------------------------ #
    #  BaseEngine 接口
    # ------------------------------------------------------------------ #

    def init(self) -> None:
        self._log("[" + APP_NAME + "] init()")

    def start(self) -> None:
        self._started_at = datetime.now()
        self._log("[" + APP_NAME + "] start()")
        state = self._regime_engine.get_state()
        self.dispatch_event(EVENT_REGIME_DETECTED, state.to_dict())
        self.dispatch_event(EVENT_INTEGRATION_HEARTBEAT, {
            "status": "started",
            "capital_ai_available": self._capital_loader.is_available(),
            "quant_os_available":   self._factor_loader.is_available(),
            "db_available":         self._market_loader.is_available(),
        })

    def stop(self) -> None:
        self._log("[" + APP_NAME + "] stop()")

    def close(self) -> None:
        self.stop()

    # ------------------------------------------------------------------ #
    #  数据输入
    # ------------------------------------------------------------------ #

    def update_prices(self, prices, volumes=None, highs=None, lows=None):
        self._prices = list(prices)
        if volumes: self._volumes = list(volumes)
        if highs:   self._highs   = list(highs)
        if lows:    self._lows    = list(lows)

    def set_tracked_symbols(self, symbols: list) -> None:
        self._tracked_symbols = list(symbols)

    # ------------------------------------------------------------------ #
    #  Phase 5 主接口
    # ------------------------------------------------------------------ #

    def auto_detect(self, symbol="", exchange="", interval="d", limit=250):
        sym = symbol or (self._tracked_symbols[0] if self._tracked_symbols else "")
        if not sym:
            return None
        prices, volumes, highs, lows = self._market_loader.get_ohlcv(
            sym, exchange, interval, limit)
        if len(prices) < 10:
            return None
        corr  = self._factor_loader.get_correlation_factor()
        state = self.detect_regime(
            prices=prices, volumes=volumes or None,
            highs=highs or None, lows=lows or None, corr_score=corr)
        self.sync_to_capital_ai()
        self.sync_to_quant_os()
        return state

    # ------------------------------------------------------------------ #
    #  五引擎流水线
    # ------------------------------------------------------------------ #

    def detect_regime(self, prices=None, volumes=None, highs=None,
                      lows=None, corr_score=0.0):
        px   = prices  if prices  is not None else self._prices
        vols = volumes if volumes is not None else (self._volumes or None)
        hi   = highs   if highs   is not None else (self._highs   or None)
        lo   = lows    if lows    is not None else (self._lows     or None)

        vol_state   = self._vol_engine.analyze(px)
        trend_state = self._trend_engine.analyze(px)
        liq_state   = self._liq_engine.analyze(px, vols, hi, lo)

        self.dispatch_event(EVENT_VOLATILITY_UPDATE, vol_state.to_dict())
        self.dispatch_event(EVENT_TREND_UPDATE,      trend_state.to_dict())
        self.dispatch_event(EVENT_LIQUIDITY_UPDATE,  liq_state.to_dict())

        regime_state = self._regime_engine.detect(
            vol_state=vol_state, trend_state=trend_state,
            liq_state=liq_state, corr_score=corr_score)

        ev = EVENT_REGIME_CHANGED if regime_state.regime_changed else EVENT_REGIME_DETECTED
        self.dispatch_event(ev, regime_state.to_dict())

        decision = self._decision_engine.decide(
            regime_state=regime_state, vol_state=vol_state, liq_state=liq_state)
        self.dispatch_event(EVENT_DECISION_SIGNAL, decision.to_dict())
        return regime_state

    def make_decision(self, regime_state=None, vol_state=None, liq_state=None):
        rs = regime_state or self._regime_engine.get_state()
        vs = vol_state    or self._vol_engine.get_state()
        ls = liq_state    or self._liq_engine.get_state()
        signal = self._decision_engine.decide(rs, vs, ls)
        self.dispatch_event(EVENT_DECISION_SIGNAL, signal.to_dict())
        return signal

    # ------------------------------------------------------------------ #
    #  Phase 5 联动接口
    # ------------------------------------------------------------------ #

    def sync_to_capital_ai(self) -> dict:
        state    = self._regime_engine.get_state()
        decision = self._decision_engine.get_signal()
        base_mod = _REGIME_MODIFIER.get(state.regime, 1.0)
        conf     = state.confidence_score
        modifier = round(max(0.5, min(1.5, base_mod * conf + 1.0 * (1.0 - conf))), 6)
        self._capital_loader.set_regime_weight_modifier(modifier)
        payload = {
            "regime":                 state.regime.value,
            "confidence":             round(conf, 4),
            "regime_weight_modifier": modifier,
            "capital_adjustment":     round(decision.capital_adjustment, 4),
            "risk_adjustment":        round(decision.risk_adjustment,    4),
            "recommendation":         decision.recommendation.value,
            "action":                 decision.action,
        }
        self.dispatch_event(EVENT_REGIME_WEIGHT_MODIFIER, payload)
        self.dispatch_event(EVENT_CAPITAL_SIGNAL_OUTPUT,  payload)
        self._sync_count += 1
        return payload

    def sync_to_quant_os(self) -> dict:
        state    = self._regime_engine.get_state()
        decision = self._decision_engine.get_signal()
        payload = {
            "regime_state":       state.regime.value,
            "confidence":         round(state.confidence_score, 4),
            "recommendation":     decision.recommendation.value,
            "capital_adjustment": round(decision.capital_adjustment, 4),
            "risk_adjustment":    round(decision.risk_adjustment,    4),
            "position_limit":     round(decision.position_limit,     4),
            "rebalance_urgency":  round(decision.rebalance_urgency,  4),
            "action":             decision.action,
            "vol_regime":         self._vol_engine.get_state().regime.value,
            "trend_direction":    self._trend_engine.get_state().direction.value,
            "liquidity_level":    self._liq_engine.get_state().level.value,
        }
        self._factor_loader.set_regime_output(
            regime_state=state.regime.value,
            capital_adj=decision.capital_adjustment,
            risk_adj=decision.risk_adjustment,
            recommendation=decision.recommendation.value,
        )
        self.dispatch_event(EVENT_RISK_SIGNAL_OUTPUT, payload)
        return payload

    def get_integration_status(self) -> dict:
        return {
            "capital_ai_available": self._capital_loader.is_available(),
            "quant_os_available":   self._factor_loader.is_available(),
            "db_available":         self._market_loader.is_available(),
            "sync_count":           self._sync_count,
            "tracked_symbols":      list(self._tracked_symbols),
            "regime_modifier":      self._capital_loader.get_regime_weight_modifier(),
            "last_output":          self._factor_loader.get_last_output(),
            "capital_ratios":       self._capital_loader.get_capital_ratios(),
        }

    # ------------------------------------------------------------------ #
    #  查询接口
    # ------------------------------------------------------------------ #

    def get_regime_state(self)       -> MarketRegimeState: return self._regime_engine.get_state()
    def get_vol_state(self)          -> VolatilityState:   return self._vol_engine.get_state()
    def get_trend_state(self)        -> TrendState:        return self._trend_engine.get_state()
    def get_liq_state(self)          -> LiquidityState:    return self._liq_engine.get_state()
    def get_decision_signal(self)    -> DecisionSignal:    return self._decision_engine.get_signal()
    def get_capital_adjustment(self) -> float: return self._decision_engine.get_capital_adjustment()
    def get_risk_adjustment(self)    -> float: return self._decision_engine.get_risk_adjustment()
    def get_rebalance_urgency(self)  -> float: return self._decision_engine.get_rebalance_urgency()
    def get_current_regime(self)     -> MarketRegime: return self._regime_engine.get_state().regime

    def get_factor_states(self) -> dict:
        return {
            "volatility": self._vol_engine.get_state().to_dict(),
            "trend":      self._trend_engine.get_state().to_dict(),
            "liquidity":  self._liq_engine.get_state().to_dict(),
        }

    def get_regime_history(self, limit=20)   -> list: return self._regime_engine.get_history().get_records(limit=limit)
    def get_regime_sequence(self, limit=50)  -> list: return self._regime_engine.get_history().get_sequence(limit=limit)
    def get_decision_history(self, limit=20) -> list: return self._decision_engine.get_history(limit=limit)
    def get_regime_summary(self)   -> dict: return self._regime_engine.summary()
    def get_vol_summary(self)      -> dict: return self._vol_engine.summary()
    def get_trend_summary(self)    -> dict: return self._trend_engine.summary()
    def get_liq_summary(self)      -> dict: return self._liq_engine.summary()
    def get_decision_summary(self) -> dict: return self._decision_engine.summary()

    def update_regime_params(self,   **kw): self._regime_engine.update_params(**kw)
    def update_vol_params(self,      **kw): self._vol_engine.update_params(**kw)
    def update_trend_params(self,    **kw): self._trend_engine.update_params(**kw)
    def update_liq_params(self,      **kw): self._liq_engine.update_params(**kw)
    def update_decision_params(self, **kw): self._decision_engine.update_params(**kw)

    # ------------------------------------------------------------------ #
    #  事件 / 摘要 / 日志
    # ------------------------------------------------------------------ #

    def dispatch_event(self, event_type, data=None):
        self.event_engine.put(Event(event_type, data or {}))

    def get_summary(self) -> dict:
        uptime = 0.0
        if self._started_at:
            uptime = round((datetime.now() - self._started_at).total_seconds(), 1)
        rs = self._regime_engine.get_state()
        ds = self._decision_engine.get_signal()
        return {
            "app": APP_NAME, "phase": 5,
            "current_regime":     rs.regime.value,
            "confidence":         round(rs.confidence_score,   4),
            "recommendation":     ds.recommendation.value,
            "capital_adjustment": round(ds.capital_adjustment, 4),
            "risk_adjustment":    round(ds.risk_adjustment,    4),
            "rebalance_urgency":  round(ds.rebalance_urgency,  4),
            "action":             ds.action,
            "regime_modifier":    self._capital_loader.get_regime_weight_modifier(),
            "vol_regime":         self._vol_engine.get_state().regime.value,
            "trend_dir":          self._trend_engine.get_state().direction.value,
            "liq_level":          self._liq_engine.get_state().level.value,
            "sync_count":         self._sync_count,
            "uptime":             uptime,
        }

    def _log(self, msg: str) -> None:
        ts = str(datetime.now())[:19]
        self._log_records.append(ts + "  " + msg)
        try:
            self.write_log(msg)
        except Exception:
            pass

    def get_logs(self, limit=200) -> list:
        return self._log_records[-limit:]
