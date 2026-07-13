"""
global_portfolio_intelligence/engine/global_engine.py  (Phase 5 — Final)

GlobalPortfolioEngine — 顶层引擎（全功能，五个 Phase 完整接入）。
"""
from __future__ import annotations
from datetime import datetime

from vnpy.event import EventEngine, Event
from vnpy.trader.engine import BaseEngine, MainEngine

from ..constant import APP_NAME, SystemStatus, OptimizationMode, AllocationMode
from ..event import (
    EVENT_GLOBAL_STATE_UPDATED, EVENT_OBJECTIVE_UPDATED,
    EVENT_ALLOCATION_UPDATED,  EVENT_REBALANCE_TRIGGERED,
    EVENT_SYSTEM_OPTIMIZED,
)
from .objective_engine  import ObjectiveEngine
from .optimizer_engine  import OptimizerEngine
from .flow_engine       import FlowEngine
from .rebalance_engine  import RebalanceEngine
from ..model.objective_model   import ObjectiveConfig, ObjectiveState
from ..model.allocation_model  import CrossModuleState, OptimizationResult
from ..model.performance_model import CapitalFlowState
from ..model.rebalance_model   import RebalanceState


class GlobalPortfolioEngine(BaseEngine):
    """全局组合智能系统 — 顶层引擎（Phase 5 Final）。"""

    engine_name = APP_NAME

    def __init__(self, main_engine: MainEngine, event_engine: EventEngine) -> None:
        super().__init__(main_engine, event_engine, APP_NAME)
        self._status:      SystemStatus    = SystemStatus.IDLE
        self._started_at:  datetime | None = None
        self._log_records: list[str]       = []

        self._objective_engine  = ObjectiveEngine(log_fn=self._log)
        self._optimizer_engine  = OptimizerEngine(log_fn=self._log)
        self._flow_engine       = FlowEngine(log_fn=self._log)
        self._rebalance_engine  = RebalanceEngine(log_fn=self._log)

        self._log(f"[{APP_NAME}] Engine created (Phase 5 Final)")

    # ── lifecycle ────────────────────────────────────────────────────
    def init(self) -> None:
        self._log(f"[{APP_NAME}] init()")
        for e in [self._objective_engine, self._optimizer_engine,
                  self._flow_engine, self._rebalance_engine]:
            e.init()
        self._status = SystemStatus.IDLE

    def start(self) -> None:
        self._started_at = datetime.now()
        self._status     = SystemStatus.RUNNING
        self._log(f"[{APP_NAME}] start()")
        for e in [self._objective_engine, self._optimizer_engine,
                  self._flow_engine, self._rebalance_engine]:
            e.start()
        self.dispatch_event(EVENT_GLOBAL_STATE_UPDATED,
                            {"status": self._status.value, "phase": 5})

    def stop(self) -> None:
        self._status = SystemStatus.STOPPED
        for e in [self._objective_engine, self._optimizer_engine,
                  self._flow_engine, self._rebalance_engine]:
            e.stop()
        self._log(f"[{APP_NAME}] stop()")

    def close(self) -> None: self.stop()

    # ── full pipeline (Phase 5) ──────────────────────────────────────
    def compute_global_state(self, inputs: dict | None = None) -> dict:
        """
        Phase 5 完整流水线：
          1. 统一目标函数计算
          2. 跨模块优化器状态
          3. 资金流状态
          4. 再平衡状态（若提供 rebalance_metrics 则自动检测）
        """
        self._status = SystemStatus.OPTIMIZING
        inp          = inputs or {}

        obj_state    = self._objective_engine.compute(inp)
        self.dispatch_event(EVENT_OBJECTIVE_UPDATED, obj_state.to_dict())

        cm_state     = self._optimizer_engine.get_state()
        flow_state   = self._flow_engine.get_state()

        # 若 inputs 含再平衡指标，自动触发检测
        rb_state = self._rebalance_engine.get_state()
        rb_metrics = inp.get("rebalance_metrics")
        if rb_metrics:
            rb_state = self._rebalance_engine.detect_and_rebalance(rb_metrics)
            if rb_state.trigger_count > 0:
                self.dispatch_event(EVENT_REBALANCE_TRIGGERED, rb_state.to_dict())

        state = {
            "status":       SystemStatus.RUNNING.value,
            "phase":        5,
            "uptime":       self._uptime(),
            "timestamp":    str(datetime.now())[:19],
            "objective":    obj_state.to_dict(),
            "cross_module": cm_state.to_dict(),
            "capital_flow": flow_state.to_dict(),
            "rebalance":    rb_state.to_dict(),
        }
        self._status = SystemStatus.RUNNING
        self.dispatch_event(EVENT_GLOBAL_STATE_UPDATED, state)
        return state

    # ── rebalance interface (Phase 5) ─────────────────────────────────
    def detect_rebalance(self, metrics: dict) -> RebalanceState:
        state = self._rebalance_engine.detect_and_rebalance(metrics)
        if state.trigger_count > 0:
            self.dispatch_event(EVENT_REBALANCE_TRIGGERED, state.to_dict())
        return state

    def manual_rebalance(self, reason: str = "manual") -> RebalanceState:
        state = self._rebalance_engine.manual_rebalance(reason)
        self.dispatch_event(EVENT_REBALANCE_TRIGGERED, state.to_dict())
        return state

    def scheduled_rebalance(self) -> RebalanceState:
        state = self._rebalance_engine.scheduled_rebalance()
        self.dispatch_event(EVENT_REBALANCE_TRIGGERED, state.to_dict())
        return state

    def set_rebalance_threshold(self, key: str, value: float) -> None:
        self._rebalance_engine.set_threshold(key, value)

    def get_rebalance_state(self) -> RebalanceState:
        return self._rebalance_engine.get_state()

    def get_rebalance_history(self, n: int = 20) -> list[RebalanceState]:
        return self._rebalance_engine.get_history(n)

    # ── capital flow interface (Phase 4) ─────────────────────────────
    def set_total_capital(self, total: float) -> None:
        self._flow_engine.set_total_capital(total)

    def register_strategy(self, entity_id: str,
                           performance_score: float = 50.0,
                           risk_budget: float = 0.15) -> None:
        self._flow_engine.register_strategy(entity_id, performance_score, risk_budget)

    def register_alpha(self, entity_id: str,
                        performance_score: float = 50.0) -> None:
        self._flow_engine.register_alpha(entity_id, performance_score)

    def allocate_capital(self, mode=None) -> CapitalFlowState:
        state = self._flow_engine.allocate(mode)
        self.dispatch_event(EVENT_ALLOCATION_UPDATED, state.to_dict())
        return state

    def rebalance_by_performance(self, updates: dict) -> CapitalFlowState:
        state = self._flow_engine.rebalance_by_performance(updates)
        self.dispatch_event(EVENT_ALLOCATION_UPDATED, state.to_dict())
        return state

    def rebalance_by_regime(self, weights: dict) -> CapitalFlowState:
        state = self._flow_engine.rebalance_by_regime(weights)
        self.dispatch_event(EVENT_ALLOCATION_UPDATED, state.to_dict())
        return state

    def get_capital_flow_state(self) -> CapitalFlowState:
        return self._flow_engine.get_state()

    def get_flow_records(self, n: int = 50) -> list:
        return self._flow_engine.get_flow_records(n)

    def set_allocation_mode(self, mode: AllocationMode) -> None:
        self._flow_engine.set_mode(mode)

    # ── optimizer interface (Phase 3) ────────────────────────────────
    def run_optimization(self, n_alpha=3, n_strategy=4, n_asset=5,
                         lr=0.05, n_iter=30, **kwargs) -> OptimizationResult:
        result = self._optimizer_engine.optimize(
            n_alpha=n_alpha, n_strategy=n_strategy, n_asset=n_asset,
            lr=lr, n_iter=n_iter, **kwargs)
        self.dispatch_event(EVENT_SYSTEM_OPTIMIZED, result.to_dict())
        return result

    def run_risk_parity(self, strategy_vols, asset_vols):
        return self._optimizer_engine.risk_parity_optimize(strategy_vols, asset_vols)

    def reoptimize_from_feedback(self, alpha_scores, strategy_scores,
                                  portfolio_scores, **kwargs):
        result = self._optimizer_engine.reoptimize_from_feedback(
            alpha_scores, strategy_scores, portfolio_scores, **kwargs)
        self.dispatch_event(EVENT_SYSTEM_OPTIMIZED, result.to_dict())
        return result

    def update_optimizer_scores(self, alpha_scores=None,
                                  strategy_scores=None, portfolio_scores=None):
        if alpha_scores     is not None:
            self._optimizer_engine.update_alpha_scores(alpha_scores)
        if strategy_scores  is not None:
            self._optimizer_engine.update_strategy_scores(strategy_scores)
        if portfolio_scores is not None:
            self._optimizer_engine.update_portfolio_scores(portfolio_scores)

    def get_cross_module_state(self) -> CrossModuleState:
        return self._optimizer_engine.get_state()

    def get_optimization_results(self, n: int = 20):
        return self._optimizer_engine.get_results(n)

    # ── objective interface (Phase 2) ────────────────────────────────
    def update_objective_inputs(self, inputs: dict) -> ObjectiveState:
        return self._objective_engine.compute(inputs)

    def set_objective_config(self, config: ObjectiveConfig) -> None:
        self._objective_engine.set_config(config)

    def get_objective_state(self) -> ObjectiveState:
        return self._objective_engine.get_state()

    def get_objective_history(self, n: int = 50):
        return self._objective_engine.get_history(n)

    def set_optimization_mode(self, mode: OptimizationMode) -> None:
        self._objective_engine.set_mode(mode)
        self._optimizer_engine.set_mode(mode)

    # ── summary ──────────────────────────────────────────────────────
    def get_summary(self) -> dict:
        return {
            "app":          APP_NAME,
            "phase":        5,
            "status":       self._status.value,
            "uptime":       self._uptime(),
            "objective":    self._objective_engine.summary(),
            "optimizer":    self._optimizer_engine.summary(),
            "capital_flow": self._flow_engine.summary(),
            "rebalance":    self._rebalance_engine.summary(),
        }

    def get_logs(self, limit: int = 200) -> list[str]:
        return self._log_records[-limit:]

    def get_status(self) -> SystemStatus:
        return self._status

    # ── events ───────────────────────────────────────────────────────
    def dispatch_event(self, event_type: str, data: dict | None = None) -> None:
        self.event_engine.put(Event(event_type, data or {}))

    # ── internal ─────────────────────────────────────────────────────
    def _uptime(self) -> float:
        if self._started_at is None:
            return 0.0
        return round((datetime.now() - self._started_at).total_seconds(), 1)

    def _log(self, msg: str) -> None:
        ts    = str(datetime.now())[:19]
        entry = f"{ts}  {msg}"
        self._log_records.append(entry)
        try:    self.write_log(msg)
        except: pass
