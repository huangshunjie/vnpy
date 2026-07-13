"""
market_reality_ai/engine/impact_simulator.py

Phase 3: Market Impact Simulator — 完整实现。

Impact = f(size, liquidity, volatility, market depth)
────────────────────────────────────────────────────────────────
Total Impact = Temporary + Permanent + Spread Cost
  Temporary : Almgren-Chriss concave model
  Permanent : Kyle lambda linear model
  Spread    : Kyle (1985) adverse selection
  Decay     : power-law half-life model
"""
from __future__ import annotations
from datetime import datetime

from ..constant import SimulationStatus, ImpactType
from ..model.impact_model import LiquidityState, ImpactEstimate, ImpactState
from ..utils.impact_utils import (
    new_impact_id,
    total_impact_bps, temporary_impact_bps, permanent_impact_bps,
    spread_cost_bps, decay_half_life, decayed_impact,
    impact_adjusted_price, liquidity_score,
    calibrate_impact_params, default_impact_params, impact_statistics,
    participation_rate,
)


class ImpactSimulator:
    """
    市场冲击模拟器 — Phase 3 完整实现。

    每次 estimate() 调用:
      1. 解析 order_params + liquidity_state
      2. 计算 temporary_bps  (Almgren-Chriss)
      3. 计算 permanent_bps  (Kyle lambda)
      4. 计算 spread_cost_bps (Kyle 1985 adverse selection)
      5. 计算 decay_half_life
      6. 构建 ImpactEstimate，更新 ImpactState

    输入参数 (order_params):
      symbol        : str
      direction     : int   +1 buy / -1 sell
      order_size    : float
      adv           : float average daily volume
      volatility    : float daily vol
      regime        : str   normal / stressed / illiquid / crisis
      market_depth  : float 0.0–1.0 LOB depth index

    liquidity_state (optional):
      LiquidityState instance or dict — overrides order_param fields
    """

    def __init__(self, log_fn=None) -> None:
        self._log    = log_fn or (lambda m: None)
        self._status = SimulationStatus.IDLE
        self._params = default_impact_params()
        self._state  = ImpactState()

    # ── lifecycle ─────────────────────────────────────────────────────
    def init(self) -> None:
        self._status = SimulationStatus.IDLE
        self._state  = ImpactState()
        self._log("[ImpactSimulator] initialised")

    def start(self) -> None:
        self._status = SimulationStatus.RUNNING
        self._log("[ImpactSimulator] started")

    def stop(self) -> None:
        self._status = SimulationStatus.IDLE
        self._log("[ImpactSimulator] stopped")

    # ── main entry: estimate impact for one order ──────────────────────
    def estimate(
        self,
        order_params:    dict,
        liquidity_state: LiquidityState | None = None,
    ) -> ImpactEstimate:
        """
        Estimate market impact for a single order.

        Returns ImpactEstimate with all components filled.
        """
        # ── extract order fields ────────────────────────────────────
        symbol     = order_params.get("symbol",       "UNKNOWN")
        direction  = int(order_params.get("direction", 1))
        size       = float(order_params.get("order_size",   1.0))
        adv        = float(order_params.get("adv",          10000.0))
        volatility = float(order_params.get("volatility",   0.02))
        regime     = order_params.get("regime", "normal")
        depth      = float(order_params.get("market_depth", 1.0))
        spread_q   = float(order_params.get("spread_bps",   5.0))

        # override with LiquidityState if provided
        if liquidity_state is not None:
            adv       = liquidity_state.adv or adv
            volatility= liquidity_state.volatility_1h or volatility
            regime    = liquidity_state.regime  or regime
            depth     = liquidity_state.market_depth
            spread_q  = liquidity_state.spread_bps or spread_q

        p = self._params

        # ── compute impact components ───────────────────────────────
        breakdown = total_impact_bps(
            volatility        = volatility,
            order_size        = size,
            adv               = adv,
            quoted_spread_bps = spread_q,
            eta_T             = p["eta_T"],
            eta_P             = p["eta_P"],
            alpha             = p["alpha"],
            regime            = regime,
            market_depth      = depth,
            lambda_as         = p["lambda_as"],
        )

        hl = decay_half_life(adv, volatility, regime)

        # ── determine dominant impact type ──────────────────────────
        if breakdown["temporary_bps"] >= breakdown["permanent_bps"]:
            imp_type = ImpactType.TEMPORARY
        else:
            imp_type = ImpactType.PERMANENT

        # ── build LiquidityState if not provided ────────────────────
        if liquidity_state is None:
            liq = LiquidityState(
                symbol        = symbol,
                spread_bps    = spread_q,
                adv           = adv,
                volatility_1h = volatility,
                market_depth  = depth,
                regime        = regime,
            )
        else:
            liq = liquidity_state

        # ── build ImpactEstimate ────────────────────────────────────
        est = ImpactEstimate(
            estimate_id      = new_impact_id(),
            symbol           = symbol,
            order_size       = size,
            direction        = direction,
            impact_type      = imp_type,
            temporary_bps    = breakdown["temporary_bps"],
            permanent_bps    = breakdown["permanent_bps"],
            spread_cost_bps  = breakdown["spread_cost_bps"],
            total_cost_bps   = breakdown["total_cost_bps"],
            participation    = breakdown["participation"],
            decay_half_life  = hl,
            liquidity_state  = liq,
        )

        self._append_estimate(est)
        self._log(
            f"[ImpactSim] {symbol}  size={size}  part={est.participation:.4f}  "
            f"temp={est.temporary_bps:.2f}bps  perm={est.permanent_bps:.2f}bps  "
            f"spread={est.spread_cost_bps:.2f}bps  total={est.total_cost_bps:.2f}bps  "
            f"regime={regime}  depth={depth:.2f}")
        return est

    # ── batch estimation ───────────────────────────────────────────────
    def estimate_batch(
        self,
        orders: list[dict],
        liquidity_states: list[LiquidityState] | None = None,
    ) -> list[ImpactEstimate]:
        results = []
        for i, op in enumerate(orders):
            liq = (liquidity_states[i]
                   if liquidity_states and i < len(liquidity_states)
                   else None)
            results.append(self.estimate(op, liq))
        return results

    # ── liquidity state helpers ────────────────────────────────────────
    def get_liquidity_state(
        self,
        symbol:       str,
        spread_bps:   float = 5.0,
        adv:          float = 10000.0,
        volatility:   float = 0.02,
        market_depth: float = 1.0,
        regime:       str   = "normal",
    ) -> LiquidityState:
        """Build a LiquidityState snapshot (read-only, no external calls)."""
        return LiquidityState(
            symbol        = symbol,
            spread_bps    = spread_q if (spread_q := spread_bps) else 5.0,
            adv           = adv,
            volatility_1h = volatility,
            market_depth  = market_depth,
            regime        = regime,
        )

    def compute_liquidity_score(
        self, liq: LiquidityState) -> float:
        return liquidity_score(
            liq.spread_bps, liq.adv, liq.market_depth, liq.volatility_1h)

    # ── decay query ────────────────────────────────────────────────────
    def get_decayed_impact(
        self,
        estimate: ImpactEstimate,
        elapsed_seconds: float,
    ) -> float:
        """Remaining temporary impact after elapsed_seconds."""
        return decayed_impact(
            estimate.temporary_bps,
            elapsed_seconds,
            estimate.decay_half_life,
        )

    # ── calibration ───────────────────────────────────────────────────
    def calibrate(
        self,
        observations: list[dict],
        adv: float = 10000.0,
    ) -> dict:
        """
        Calibrate eta_T from observed (order_size, realized_cost_bps,
        volatility) triples. Updates _params in place.
        """
        p = calibrate_impact_params(observations, adv)
        self._params = p
        self._log(
            f"[ImpactSim] calibrated  n={p.get('n_samples',0)}  "
            f"eta_T={p['eta_T']}  eta_P={p['eta_P']}")
        return p

    def set_params(self, **kwargs) -> None:
        for k, v in kwargs.items():
            if k in self._params:
                self._params[k] = v

    # ── query ──────────────────────────────────────────────────────────
    def get_state(self) -> ImpactState:
        return self._state

    def get_statistics(self) -> dict:
        return self._state.to_dict()

    def get_estimates(self, limit: int = 500) -> list[ImpactEstimate]:
        return self._state.estimates[-limit:]

    def get_params(self) -> dict:
        return dict(self._params)

    @property
    def status(self) -> SimulationStatus:
        return self._status

    # ── internal ──────────────────────────────────────────────────────
    def _append_estimate(self, est: ImpactEstimate) -> None:
        self._state.estimates.append(est)
        if len(self._state.estimates) > 10000:
            self._state.estimates = self._state.estimates[-10000:]
        self._state.update_from_estimates()
