"""
execution_intelligence_ai/engine/routing_engine.py  (Phase 4)

RoutingEngine — 执行路由引擎。

四种路由策略：
  best_price   — 综合执行成本最低
  min_slippage — 历史滑点最低
  fastest      — 延迟最低
  balanced     — 多因子加权综合评分（默认）
"""
from __future__ import annotations
from datetime import datetime
from typing import Callable

from ..constant import RoutingMode
from ..model.routing_model import VenueProfile, VenueScore, RoutingState


DEFAULT_VENUES: list[VenueProfile] = [
    VenueProfile(venue_id="SSE_DIRECT",  name="上交所直连",  venue_type="exchange",
                 commission_bps=2.5, avg_slippage_bps=3.0, spread_bps=4.0,
                 avg_latency_ms=5.0,  fill_rate=0.98),
    VenueProfile(venue_id="SZSE_DIRECT", name="深交所直连",  venue_type="exchange",
                 commission_bps=2.5, avg_slippage_bps=3.2, spread_bps=4.0,
                 avg_latency_ms=5.5,  fill_rate=0.97),
    VenueProfile(venue_id="BROKER_A",    name="券商 A 通道", venue_type="broker",
                 commission_bps=3.0, avg_slippage_bps=5.0, spread_bps=6.0,
                 avg_latency_ms=15.0, fill_rate=0.94),
    VenueProfile(venue_id="BROKER_B",    name="券商 B 通道", venue_type="broker",
                 commission_bps=2.8, avg_slippage_bps=4.5, spread_bps=5.5,
                 avg_latency_ms=12.0, fill_rate=0.95),
    VenueProfile(venue_id="DARKPOOL_A",  name="暗池 A",      venue_type="darkpool",
                 commission_bps=1.5, avg_slippage_bps=1.0, spread_bps=0.0,
                 avg_latency_ms=50.0, fill_rate=0.60, darkpool_min_size=50000.0),
]


class RoutingEngine:
    """执行路由引擎 (Phase 4)。"""

    def __init__(self, log_fn: Callable | None = None) -> None:
        self._log    = log_fn or (lambda m: None)
        self._venues: dict[str, VenueProfile] = {
            v.venue_id: v for v in DEFAULT_VENUES}
        self._routing_states: dict[str, list[RoutingState]] = {}
        self._mode = RoutingMode.BALANCED

    def init(self)  -> None: self._log("[RoutingEngine] init()")
    def start(self) -> None: self._log(f"[RoutingEngine] start()  venues={len(self._venues)}")
    def stop(self)  -> None: self._log("[RoutingEngine] stop()")

    # ── venue management ─────────────────────────────────────────────
    def add_venue(self, v: VenueProfile) -> None:
        self._venues[v.venue_id] = v
    def remove_venue(self, venue_id: str) -> None:
        self._venues.pop(venue_id, None)
    def set_venue_available(self, venue_id: str, available: bool) -> None:
        if venue_id in self._venues:
            self._venues[venue_id].is_available = available
    def update_venue_stats(self, venue_id: str,
                           avg_slippage_bps=None,
                           avg_latency_ms=None,
                           fill_rate=None) -> None:
        v = self._venues.get(venue_id)
        if v is None: return
        if avg_slippage_bps is not None: v.avg_slippage_bps = avg_slippage_bps
        if avg_latency_ms   is not None: v.avg_latency_ms   = avg_latency_ms
        if fill_rate        is not None: v.fill_rate         = fill_rate
    def get_venues(self) -> list[VenueProfile]:
        return list(self._venues.values())
    def set_default_mode(self, mode: RoutingMode) -> None:
        self._mode = mode

    # ── core routing ─────────────────────────────────────────────────
    def select_route(self, execution_id: str, slice_id: str,
                     symbol: str, order_size: float,
                     mode: RoutingMode | None = None) -> RoutingState:
        """为一个切片子订单选择最优执行路径。"""
        routing_mode = mode if mode is not None else self._mode
        available = [
            v for v in self._venues.values()
            if v.is_available
            and (v.max_order_size <= 0 or order_size <= v.max_order_size)
            and order_size >= v.min_order_size
            and (v.venue_type != "darkpool" or order_size >= v.darkpool_min_size)
        ]
        if not available:
            available = list(self._venues.values())[:1]
            self._log("[RoutingEngine] WARN: no available venue, fallback")

        scores = self._score_venues(available, order_size, routing_mode)
        scores.sort(key=lambda s: s.score, reverse=True)
        best = scores[0]
        selected_venue = self._venues.get(best.venue_id)

        state = RoutingState(
            execution_id        = execution_id,
            slice_id            = slice_id,
            symbol              = symbol,
            routing_mode        = routing_mode,
            candidates          = scores,
            selected_venue_id   = best.venue_id,
            selected_venue_name = selected_venue.name if selected_venue else best.venue_id,
            expected_cost_bps   = best.cost_bps,
            expected_latency_ms = best.latency_ms,
            decided_at          = datetime.now(),
        )
        if execution_id not in self._routing_states:
            self._routing_states[execution_id] = []
        self._routing_states[execution_id].append(state)

        self._log(f"[RoutingEngine] {execution_id}/{slice_id} "
                  f"mode={routing_mode.value} -> {best.venue_id} "
                  f"cost={best.cost_bps:.2f}bp score={best.score:.4f}")
        return state

    def route_plan(self, execution_id: str, symbol: str,
                   slice_ids: list[str], slice_volumes: list[float],
                   mode: RoutingMode | None = None) -> list[RoutingState]:
        """为整个拆单计划批量路由。"""
        return [self.select_route(execution_id, sid, symbol, vol, mode)
                for sid, vol in zip(slice_ids, slice_volumes)]

    def record_realized(self, execution_id: str, slice_id: str,
                        realized_cost_bps: float,
                        realized_latency_ms: float) -> bool:
        for state in self._routing_states.get(execution_id, []):
            if state.slice_id == slice_id:
                state.realized_cost_bps   = realized_cost_bps
                state.realized_latency_ms = realized_latency_ms
                v = self._venues.get(state.selected_venue_id)
                if v:
                    a = 0.2
                    v.avg_slippage_bps = round((1-a)*v.avg_slippage_bps + a*realized_cost_bps,  4)
                    v.avg_latency_ms   = round((1-a)*v.avg_latency_ms   + a*realized_latency_ms, 4)
                return True
        return False

    def get_routing_states(self, execution_id: str) -> list[RoutingState]:
        return self._routing_states.get(execution_id, [])

    def get_venue_ranking(self, mode: RoutingMode | None = None) -> list[VenueScore]:
        m = mode if mode is not None else self._mode
        available = [v for v in self._venues.values() if v.is_available]
        scores = self._score_venues(available, 10000.0, m)
        scores.sort(key=lambda s: s.score, reverse=True)
        return scores

    def summary(self) -> dict:
        return {
            "phase":        4,
            "status":       "active",
            "venues":       len(self._venues),
            "available":    sum(1 for v in self._venues.values() if v.is_available),
            "total_routes": sum(len(v) for v in self._routing_states.values()),
            "default_mode": self._mode.value,
        }

    # ── scoring ───────────────────────────────────────────────────────
    def _score_venues(self, venues: list[VenueProfile],
                      order_size: float, mode: RoutingMode) -> list[VenueScore]:
        if not venues: return []
        if   mode == RoutingMode.BEST_PRICE:   return self._score_best_price(venues)
        elif mode == RoutingMode.MIN_SLIPPAGE: return self._score_min_slippage(venues)
        elif mode == RoutingMode.FASTEST:      return self._score_fastest(venues)
        else:                                  return self._score_balanced(venues)

    @staticmethod
    def _norm_asc(vals: list[float]) -> list[float]:
        mn,mx = min(vals),max(vals); rng=max(mx-mn,0.001)
        return [round(1.0-(v-mn)/rng,4) for v in vals]

    @staticmethod
    def _norm_desc(vals: list[float]) -> list[float]:
        mn,mx = min(vals),max(vals); rng=max(mx-mn,0.001)
        return [round((v-mn)/rng,4) for v in vals]

    def _score_best_price(self, venues):
        costs=[v.total_cost_bps() for v in venues]
        nc=self._norm_asc(costs)
        return [VenueScore(venue_id=v.venue_id, score=nc[i], cost_bps=costs[i],
                latency_ms=v.avg_latency_ms, fill_rate=v.fill_rate,
                reason=f"best_price cost={costs[i]:.2f}bp")
                for i,v in enumerate(venues)]

    def _score_min_slippage(self, venues):
        slips=[v.avg_slippage_bps for v in venues]
        ns=self._norm_asc(slips)
        return [VenueScore(venue_id=v.venue_id, score=ns[i], cost_bps=v.total_cost_bps(),
                latency_ms=v.avg_latency_ms, fill_rate=v.fill_rate,
                reason=f"min_slippage slip={slips[i]:.2f}bp")
                for i,v in enumerate(venues)]

    def _score_fastest(self, venues):
        lats=[v.avg_latency_ms for v in venues]
        nl=self._norm_asc(lats)
        return [VenueScore(venue_id=v.venue_id, score=nl[i], cost_bps=v.total_cost_bps(),
                latency_ms=lats[i], fill_rate=v.fill_rate,
                reason=f"fastest lat={lats[i]:.1f}ms")
                for i,v in enumerate(venues)]

    def _score_balanced(self, venues):
        costs=[v.total_cost_bps()   for v in venues]
        slips=[v.avg_slippage_bps   for v in venues]
        lats =[v.avg_latency_ms     for v in venues]
        fills=[v.fill_rate          for v in venues]
        nc=self._norm_asc(costs); ns=self._norm_asc(slips)
        nl=self._norm_asc(lats);  nf=self._norm_desc(fills)
        W_C,W_S,W_L,W_F = 0.40,0.25,0.15,0.20
        return [VenueScore(
            venue_id=v.venue_id,
            score=round(W_C*nc[i]+W_S*ns[i]+W_L*nl[i]+W_F*nf[i],4),
            cost_bps=costs[i], latency_ms=lats[i], fill_rate=fills[i],
            reason=f"balanced c={nc[i]:.2f} s={ns[i]:.2f} l={nl[i]:.2f} f={nf[i]:.2f}")
            for i,v in enumerate(venues)]
