"""
temporal_intelligence_ai/engine.py

TemporalEngine — 时间智能系统主引擎（Phase 6 完整版）。

五大子引擎全部就位：
  1. Market Cycle Engine        — 市场周期识别  [Phase 2 ✔]
  2. Alpha Decay Engine         — Alpha 衰减    [Phase 3 ✔]
  3. Time Dependency Engine     — 时间依赖       [Phase 4 ✔]
  4. Regime Transition Engine   — 状态转移       [Phase 5 ✔]
  5. Temporal Validation Engine — 时间验证       [Phase 6 ✔]
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from vnpy.trader.engine import BaseEngine, MainEngine, EventEngine
from vnpy.event import Event
from vnpy.trader.constant import Interval, Exchange

from .constant import APP_NAME, DecayMode, TemporalSystemStatus
from .event import (
    EVENT_CYCLE_DETECTED,
    EVENT_ALPHA_DECAY_UPDATED,
    EVENT_TRANSITION_DETECTED,
    EVENT_TEMPORAL_ANALYSIS_COMPLETED,
    EVENT_VALIDATION_UPDATED,
)
from .engine.cycle_engine import CycleEngine
from .engine.decay_engine import DecayEngine
from .engine.dependency_engine import DependencyEngine
from .engine.transition_engine import TransitionEngine
from .engine.validation_engine import ValidationEngine
from .datasource.alpha_loader import AlphaRecord
from .model.validation_model import ValidationRecord


class TemporalEngine(BaseEngine):
    """时间智能系统主引擎（完整版）。"""

    engine_name: str = APP_NAME

    def __init__(self, main_engine: MainEngine, event_engine: EventEngine) -> None:
        super().__init__(main_engine, event_engine, APP_NAME)

        self._status:      TemporalSystemStatus = TemporalSystemStatus.IDLE
        self._start_time:  Optional[datetime]   = None
        self._current_bar: int = 0

        self._cycle_engine      = CycleEngine()
        self._decay_engine      = DecayEngine()
        self._dependency_engine = DependencyEngine()
        self._transition_engine = TransitionEngine()
        self._validation_engine = ValidationEngine()

    # ── lifecycle ────────────────────────────────────────────────────

    def init(self) -> None:
        self._status      = TemporalSystemStatus.IDLE
        self._current_bar = 0

    def start(self) -> None:
        self._status     = TemporalSystemStatus.RUNNING
        self._start_time = datetime.now()

    def stop(self) -> None:
        self._status = TemporalSystemStatus.STOPPED

    def close(self) -> None:
        self.stop()

    # ── cycle engine ─────────────────────────────────────────────────

    def configure_cycle(
        self,
        symbols:    List[tuple[str, Exchange]],
        interval:   Interval = Interval.DAILY,
        lookback:   int      = 120,
        vol_window: int      = 20,
        trend_fast: int      = 10,
        trend_slow: int      = 30,
        mom_window: int      = 20,
        dd_window:  int      = 60,
    ) -> None:
        self._cycle_engine.configure(
            symbols    = symbols,
            interval   = interval,
            lookback   = lookback,
            vol_window = vol_window,
            trend_fast = trend_fast,
            trend_slow = trend_slow,
            mom_window = mom_window,
            dd_window  = dd_window,
        )

    def analyze_cycle(self, as_of: Optional[datetime] = None) -> None:
        """触发周期分析，完成后自动注入上下文到 Decay / Transition。"""
        if self._status != TemporalSystemStatus.RUNNING:
            return
        self._status = TemporalSystemStatus.ANALYZING
        state = self._cycle_engine.analyze(as_of=as_of)
        self._status = TemporalSystemStatus.RUNNING
        if state is not None:
            self._decay_engine.set_context(
                regime      = state.regime,
                phase       = state.phase,
                current_vol = state.metrics.volatility,
                current_bar = self._current_bar,
            )
            self._transition_engine.set_context(
                regime        = state.regime,
                phase         = state.phase,
                current_vol   = state.metrics.volatility,
                current_trend = state.metrics.trend_strength,
            )
            self.dispatch_event(EVENT_CYCLE_DETECTED, state)

    # ── decay engine ─────────────────────────────────────────────────

    def configure_decay(
        self,
        mode:            DecayMode                  = DecayMode.EXPONENTIAL,
        baseline_vol:    float                      = 0.20,
        vol_sensitivity: float                      = 2.0,
        min_threshold:   float                      = 0.05,
        curve_horizon:   int                        = 60,
        weights:         tuple[float, float, float] = (0.40, 0.35, 0.25),
    ) -> None:
        self._decay_engine.configure(
            mode            = mode,
            baseline_vol    = baseline_vol,
            vol_sensitivity = vol_sensitivity,
            min_threshold   = min_threshold,
            curve_horizon   = curve_horizon,
            weights         = weights,
        )

    def register_alpha(self, record: AlphaRecord) -> None:
        self._decay_engine.register_alpha(record)

    def register_alphas(self, records: List[AlphaRecord]) -> None:
        self._decay_engine.register_alphas(records)

    def compute_decay(self, bar: Optional[int] = None) -> None:
        if self._status not in (
            TemporalSystemStatus.RUNNING, TemporalSystemStatus.ANALYZING
        ):
            return
        if bar is None:
            self._current_bar += 1
            bar = self._current_bar
        else:
            self._current_bar = bar
        states = self._decay_engine.compute(bar)
        for state in states:
            self.dispatch_event(EVENT_ALPHA_DECAY_UPDATED, state)

    # ── dependency engine ────────────────────────────────────────────

    def configure_dependency(
        self,
        max_lag:   int = 30,
        cross_lag: int = 20,
    ) -> None:
        self._dependency_engine.configure(
            max_lag   = max_lag,
            cross_lag = cross_lag,
        )

    def register_signal(self, signal_id: str, series: List[float]) -> None:
        self._dependency_engine.register_signal(signal_id, series)

    def register_signals(self, signals: Dict[str, List[float]]) -> None:
        self._dependency_engine.register_signals(signals)

    def analyze_dependency(self) -> None:
        if self._status not in (
            TemporalSystemStatus.RUNNING, TemporalSystemStatus.ANALYZING
        ):
            return
        prev = self._status
        self._status = TemporalSystemStatus.ANALYZING
        state = self._dependency_engine.analyze()
        self._status = prev
        if state is not None:
            self.dispatch_event(EVENT_TEMPORAL_ANALYSIS_COMPLETED, state)

    # ── transition engine ────────────────────────────────────────────

    def configure_transition(
        self,
        regime_fast:    int   = 10,
        regime_slow:    int   = 40,
        regime_thresh:  float = 2.0,
        vol_short:      int   = 10,
        vol_long:       int   = 40,
        vol_ratio:      float = 1.8,
        liq_short:      int   = 10,
        liq_long:       int   = 40,
        liq_thresh:     float = 1.5,
        confirm_thresh: float = 0.60,
    ) -> None:
        self._transition_engine.configure(
            regime_fast    = regime_fast,
            regime_slow    = regime_slow,
            regime_thresh  = regime_thresh,
            vol_short      = vol_short,
            vol_long       = vol_long,
            vol_ratio      = vol_ratio,
            liq_short      = liq_short,
            liq_long       = liq_long,
            liq_thresh     = liq_thresh,
            confirm_thresh = confirm_thresh,
        )

    def update_transition_series(
        self,
        prices:  Optional[List[float]] = None,
        returns: Optional[List[float]] = None,
        volumes: Optional[List[float]] = None,
    ) -> None:
        self._transition_engine.update_series(
            prices=prices, returns=returns, volumes=volumes)

    def detect_transition(self) -> None:
        if self._status not in (
            TemporalSystemStatus.RUNNING, TemporalSystemStatus.ANALYZING
        ):
            return
        prev = self._status
        self._status = TemporalSystemStatus.ANALYZING
        state = self._transition_engine.detect()
        self._status = prev
        if state is not None:
            self.dispatch_event(EVENT_TRANSITION_DETECTED, state)

    # ── validation engine ────────────────────────────────────────────

    def submit_prediction(self, record: ValidationRecord) -> None:
        """提交一条预测记录到验证引擎。"""
        self._validation_engine.submit_prediction(record)

    def submit_predictions(self, records: List[ValidationRecord]) -> None:
        """批量提交预测记录。"""
        self._validation_engine.submit_many(records)

    def realize_prediction(self, record_id: str, realized_value: float) -> None:
        """更新某条预测记录的实际值。"""
        self._validation_engine.realize(record_id, realized_value)

    def set_validation_decay_series(
        self,
        predicted: List[float],
        realized:  List[float],
    ) -> None:
        """注入衰减强度序列用于对齐验证。"""
        self._validation_engine.set_decay_series(predicted, realized)

    def set_validation_acf_series(
        self,
        predicted:        List[float],
        realized:         List[float],
        significant_lags: List[int],
    ) -> None:
        """注入 ACF 序列用于记忆有效性验证。"""
        self._validation_engine.set_acf_series(
            predicted, realized, significant_lags)

    def run_validation(self) -> None:
        """
        触发完整时间验证计算。
        结果通过 EVENT_VALIDATION_UPDATED 派发。
        """
        if self._status not in (
            TemporalSystemStatus.RUNNING, TemporalSystemStatus.ANALYZING
        ):
            return
        prev = self._status
        self._status = TemporalSystemStatus.ANALYZING
        state = self._validation_engine.validate()
        self._status = prev
        self.dispatch_event(EVENT_VALIDATION_UPDATED, state)

    # ── event dispatch ───────────────────────────────────────────────

    def dispatch_event(self, event_type: str, data: Any = None) -> None:
        event = Event(event_type, data)
        self.event_engine.put(event)

    # ── accessors ────────────────────────────────────────────────────

    def get_cycle_state(self):
        return self._cycle_engine.get_state()

    def get_cycle_history(self):
        return self._cycle_engine.get_history()

    def get_decay_states(self) -> Dict[str, Any]:
        return self._decay_engine.get_states()

    def get_decay_curves(self) -> Dict[str, Any]:
        return self._decay_engine.get_curves()

    def get_decay_history(self, alpha_id: str):
        return self._decay_engine.get_history(alpha_id)

    def get_decay_loader(self):
        return self._decay_engine.get_loader()

    def get_dependency_state(self):
        return self._dependency_engine.get_state()

    def get_dependency_history(self):
        return self._dependency_engine.get_history()

    def get_transition_state(self):
        return self._transition_engine.get_state()

    def get_transition_history(self):
        return self._transition_engine.get_history()

    def get_validation_state(self):
        return self._validation_engine.get_state()

    def get_validation_history(self):
        return self._validation_engine.get_history()

    def get_validation_records(self):
        return self._validation_engine.get_all_records()

    # ── status query ─────────────────────────────────────────────────

    def get_summary(self) -> dict[str, Any]:
        uptime = 0.0
        if self._start_time:
            uptime = (datetime.now() - self._start_time).total_seconds()
        return {
            "status": self._status.value,
            "phase":  6,
            "uptime": uptime,
            "engine": {
                "cycle_detected":      self._cycle_engine.get_state() is not None,
                "decay_computed":      bool(self._decay_engine.get_states()),
                "dependency_analyzed": self._dependency_engine.get_state() is not None,
                "transition_detected": self._transition_engine.get_state() is not None,
                "validation_run":      self._validation_engine.get_state() is not None,
            },
            "cycle":      self._cycle_engine.get_summary(),
            "decay":      self._decay_engine.get_summary(),
            "dependency": self._dependency_engine.get_summary(),
            "transition": self._transition_engine.get_summary(),
            "validation": self._validation_engine.get_summary(),
        }
