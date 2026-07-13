"""
execution_intelligence_ai/dispatcher.py  (Phase 5)

ExecutionIntelligenceEngine — 顶层引擎（最终版）。
Phase 5 流水线：冲击估算 → 拆单 → 路由 → 反馈闭环
"""
from __future__ import annotations
from datetime import datetime

from vnpy.event import EventEngine, Event
from vnpy.trader.engine import BaseEngine, MainEngine

from .constant import APP_NAME, RoutingMode
from .event import (
    EVENT_EXECUTION_START, EVENT_ORDER_SLICED, EVENT_IMPACT_ESTIMATED,
    EVENT_ROUTE_SELECTED, EVENT_EXECUTION_COMPLETED,
    EVENT_FEEDBACK_UPDATED, EVENT_EXECUTION_ABORTED,
)
from .engine.execution_engine import ExecutionEngine
from .engine.strategy_engine  import StrategyEngine
from .engine.slicing_engine   import SlicingEngine
from .engine.impact_engine    import ImpactEngine
from .engine.routing_engine   import RoutingEngine
from .engine.feedback_engine  import FeedbackEngine
from .datasource.market_loader    import MarketLoader
from .datasource.order_loader     import OrderLoader
from .datasource.execution_loader import ExecutionLoader
from .model.slicing_model  import SlicePlan, SlicingParams
from .model.impact_model   import ImpactState, ImpactParams
from .model.routing_model  import RoutingState, VenueProfile
from .model.feedback_model import FeedbackState, ExecutionReport, SliceFeedback
from .utils.execution_utils import generate_execution_id


class ExecutionIntelligenceEngine(BaseEngine):
    """Execution Intelligence 2.0 — 顶层引擎（Phase 5 最终版）。"""

    engine_name = APP_NAME

    def __init__(self, main_engine: MainEngine, event_engine: EventEngine) -> None:
        super().__init__(main_engine, event_engine, APP_NAME)
        self._started_at: datetime | None = None
        self._log_records: list[str] = []

        self._exec_engine     = ExecutionEngine(log_fn=self._log)
        self._strategy_engine = StrategyEngine(log_fn=self._log)
        self._slicing_engine  = SlicingEngine(log_fn=self._log)
        self._impact_engine   = ImpactEngine(log_fn=self._log)
        self._routing_engine  = RoutingEngine(log_fn=self._log)
        self._feedback_engine = FeedbackEngine(log_fn=self._log)

        self._market_loader    = MarketLoader(main_engine=main_engine)
        self._order_loader     = OrderLoader(main_engine=main_engine)
        self._execution_loader = ExecutionLoader(main_engine=main_engine)
        self._log(f"[{APP_NAME}] Engine created (Phase 5)")

    # ── lifecycle ────────────────────────────────────────────────────
    def init(self)  -> None:
        self._log(f"[{APP_NAME}] init()")
        for e in self._all_engines(): e.init()

    def start(self) -> None:
        self._started_at = datetime.now()
        self._log(f"[{APP_NAME}] start()")
        for e in self._all_engines(): e.start()
        self.dispatch_event(EVENT_EXECUTION_START, {"status": "started", "phase": 5})

    def stop(self) -> None:
        self._log(f"[{APP_NAME}] stop()")
        for e in self._all_engines(): e.stop()

    def close(self) -> None: self.stop()

    # ── main pipeline (Phase 5) ──────────────────────────────────────
    def process_order(
        self,
        order_data:    dict,
        params:        SlicingParams | None = None,
        impact_params: ImpactParams  | None = None,
        routing_mode:  RoutingMode   | None = None,
    ) -> tuple[SlicePlan, ImpactState, list[RoutingState]]:
        """
        Phase 5 流水线：冲击估算 → 拆单 → 路由 → 注册反馈。
        Returns (SlicePlan, ImpactState, list[RoutingState])
        """
        if "execution_id" not in order_data:
            order_data["execution_id"] = generate_execution_id()
        eid        = order_data["execution_id"]
        symbol     = order_data.get("symbol", "")
        total_vol  = float(order_data.get("total_volume", 0.0))
        volatility = float(order_data.get("volatility",  0.02))
        adv        = float(order_data.get("adv",         0.0)) or None
        spread_bps = float(order_data.get("spread_bps",  5.0))
        direction  = order_data.get("direction", "long")
        strategy   = (params.strategy.value if params else "twap")

        self._log(f"[{APP_NAME}] process_order: {eid} symbol={symbol} vol={total_vol}")
        self.dispatch_event(EVENT_EXECUTION_START, order_data)

        # Step 1: impact
        if impact_params is not None:
            self._impact_engine.set_params(impact_params)
        impact_state = self._impact_engine.estimate_impact(
            eid, symbol, total_vol, volatility, adv, spread_bps)
        self.dispatch_event(EVENT_IMPACT_ESTIMATED, {
            "execution_id": eid,
            "estimated_bp": impact_state.estimated_bp,
            "impact_level": impact_state.impact_level.value,
        })

        # Step 2: slicing
        if params is None: params = SlicingParams()
        params = self._adjust_for_impact(params, impact_state)
        plan = self._slicing_engine.slice_order(eid, order_data, params)
        self.dispatch_event(EVENT_ORDER_SLICED, {
            "execution_id": eid, "n_slices": plan.n_slices,
            "strategy": params.strategy.value, "total_volume": plan.total_volume,
        })

        # Step 3: routing
        routing_states = self._routing_engine.route_plan(
            eid, symbol,
            [s.slice_id for s in plan.slices],
            [s.volume   for s in plan.slices],
            routing_mode,
        )
        if routing_states:
            self.dispatch_event(EVENT_ROUTE_SELECTED, {
                "execution_id":   eid,
                "selected_venue": routing_states[0].selected_venue_id,
                "n_routes":       len(routing_states),
            })

        # Step 4: register feedback collection (Phase 5)
        self._feedback_engine.begin_execution(
            eid, symbol, direction, strategy, total_vol)

        self._log(f"[{APP_NAME}] pipeline done: {eid} slices={plan.n_slices} "
                  f"impact={impact_state.estimated_bp:.2f}bp "
                  f"venue={routing_states[0].selected_venue_id if routing_states else 'N/A'}")
        return plan, impact_state, routing_states

    # ── feedback interface (Phase 5) ─────────────────────────────────
    def record_slice_feedback(
        self,
        execution_id: str,
        slice_id: str,
        sequence: int,
        planned_volume: float,
        filled_volume: float,
        planned_price: float,
        filled_price: float,
        venue_id: str = "",
        latency_ms: float = 0.0,
    ) -> SliceFeedback:
        """记录单个切片成交结果。"""
        sf = self._feedback_engine.record_slice(
            execution_id, slice_id, sequence,
            planned_volume, filled_volume,
            planned_price, filled_price,
            venue_id, latency_ms)
        self.dispatch_event(EVENT_FEEDBACK_UPDATED, {
            "execution_id": execution_id,
            "slice_id":     slice_id,
            "fill_rate":    sf.fill_rate,
            "slippage_bps": sf.slippage_bps,
        })
        return sf

    def complete_execution(
        self,
        execution_id: str,
        realized_impact_bps: float = 0.0,
        market_vwap: float = 0.0,
    ) -> ExecutionReport:
        """汇总所有切片，生成执行质量报告 + 闭环建议。"""
        # 同步 ImpactEngine 实现值
        impact_state = self._impact_engine.record_realized(
            execution_id, realized_impact_bps)

        report = self._feedback_engine.complete_execution(
            execution_id, realized_impact_bps, market_vwap)

        self.dispatch_event(EVENT_EXECUTION_COMPLETED, {
            "execution_id":  execution_id,
            "fill_rate":     report.feedback.fill_rate,
            "slippage_bps":  report.feedback.slippage_bps,
            "total_cost_bps": report.feedback.total_cost_bps,
            "quality_score": report.feedback.quality_score,
        })
        self._log(f"[{APP_NAME}] completed: {execution_id} "
                  f"score={report.feedback.quality_score:.1f} "
                  f"fill={report.feedback.fill_rate:.1%}")
        return report

    def get_feedback_report(self, execution_id: str) -> ExecutionReport | None:
        return self._feedback_engine.get_report(execution_id)

    def get_all_reports(self) -> list[ExecutionReport]:
        return self._feedback_engine.get_all_reports()

    def get_aggregate_stats(self) -> dict:
        return self._feedback_engine.get_aggregate_stats()

    # ── routing interface (Phase 4) ──────────────────────────────────
    def route_slice(self, execution_id, slice_id, symbol, order_size, mode=None):
        return self._routing_engine.select_route(
            execution_id, slice_id, symbol, order_size, mode)

    def route_plan(self, execution_id, symbol, slice_ids, slice_volumes, mode=None):
        return self._routing_engine.route_plan(
            execution_id, symbol, slice_ids, slice_volumes, mode)

    def get_routing_states(self, execution_id):
        return self._routing_engine.get_routing_states(execution_id)

    def get_venue_ranking(self, mode=None):
        return self._routing_engine.get_venue_ranking(mode)

    def get_venues(self): return self._routing_engine.get_venues()

    def add_venue(self, venue: VenueProfile):
        self._routing_engine.add_venue(venue)

    def set_venue_available(self, venue_id, available):
        self._routing_engine.set_venue_available(venue_id, available)

    def set_routing_mode(self, mode: RoutingMode):
        self._routing_engine.set_default_mode(mode)

    def record_realized_routing(self, execution_id, slice_id,
                                 realized_cost_bps, realized_latency_ms):
        return self._routing_engine.record_realized(
            execution_id, slice_id, realized_cost_bps, realized_latency_ms)

    # ── impact interface (Phase 3) ───────────────────────────────────
    def estimate_impact(self, execution_id, symbol, order_size, volatility,
                        adv=None, spread_bps=None, model=None):
        return self._impact_engine.estimate_impact(
            execution_id, symbol, order_size, volatility, adv, spread_bps, model)

    def record_realized_impact(self, execution_id, realized_bp):
        state = self._impact_engine.record_realized(execution_id, realized_bp)
        if state:
            self.dispatch_event(EVENT_FEEDBACK_UPDATED, {
                "execution_id": execution_id,
                "realized_bp":  realized_bp,
                "adjusted_bp":  state.adjusted_bp,
            })
        return state

    def get_impact_state(self, execution_id):
        return self._impact_engine.get_state(execution_id)

    def get_impact_curve(self, adv, volatility, model=None, n_points=20):
        return self._impact_engine.get_impact_curve(adv, volatility, model, n_points)

    def get_multi_model_curves(self, adv, volatility, n_points=20):
        return self._impact_engine.get_multi_model_curves(adv, volatility, n_points)

    def calibrate_impact(self): return self._impact_engine.calibrate()

    def set_impact_params(self, params: ImpactParams):
        self._impact_engine.set_params(params)

    # ── slicing interface (Phase 2) ──────────────────────────────────
    def update_pov(self, execution_id, market_volume_this_bar):
        return self._slicing_engine.update_pov_slice(
            execution_id, market_volume_this_bar)

    def mark_slice_filled(self, execution_id, slice_id, filled_volume, filled_price):
        return self._slicing_engine.mark_slice_filled(
            execution_id, slice_id, filled_volume, filled_price)

    def get_slice_plan(self, execution_id):
        return self._slicing_engine.get_plan(execution_id)

    def get_all_plans(self):
        return self._slicing_engine.get_all_plans()

    # ── summary & logs ───────────────────────────────────────────────
    def get_summary(self) -> dict:
        uptime = 0.0
        if self._started_at:
            uptime = round((datetime.now() - self._started_at).total_seconds(), 1)
        plans = self.get_all_plans()
        return {
            "app":          APP_NAME,
            "phase":        5,
            "uptime":       uptime,
            "total_plans":  len(plans),
            "active_plans": sum(1 for p in plans if p.overall_fill_rate < 1.0),
            "done_plans":   sum(1 for p in plans if p.overall_fill_rate >= 1.0),
            "slicing":      self._slicing_engine.summary(),
            "impact":       self._impact_engine.summary(),
            "routing":      self._routing_engine.summary(),
            "feedback":     self._feedback_engine.summary(),
        }

    def get_logs(self, limit: int = 200) -> list[str]:
        return self._log_records[-limit:]

    # ── events ───────────────────────────────────────────────────────
    def dispatch_event(self, event_type: str, data: dict | None = None) -> None:
        self.event_engine.put(Event(event_type, data or {}))

    # ── internal ─────────────────────────────────────────────────────
    def _adjust_for_impact(self, params, impact):
        from .constant import ImpactLevel
        import math, dataclasses
        m = 1.0
        if   impact.impact_level == ImpactLevel.HIGH:   m = 1.5
        elif impact.impact_level == ImpactLevel.SEVERE: m = 2.0
        if m == 1.0: return params
        return dataclasses.replace(
            params,
            n_slices=max(1, math.ceil(params.n_slices * m)),
            interval_seconds=max(1, math.ceil(params.interval_seconds * m)))

    def _all_engines(self):
        return [self._exec_engine, self._strategy_engine,
                self._slicing_engine, self._impact_engine,
                self._routing_engine, self._feedback_engine]

    def _log(self, msg: str) -> None:
        ts    = str(datetime.now())[:19]
        entry = f"{ts}  {msg}"
        self._log_records.append(entry)
        try:    self.write_log(msg)
        except: pass
