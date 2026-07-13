"""
market_reality_ai/engine/execution_simulator.py

Phase 2: Execution Reality Simulator — 完整实现。

核心公式:
  Realized Price = Market Price + Slippage + ½Spread + Delay Noise
  ──────────────────────────────────────────────────────────────────
  slippage     = vol_scaled_slippage(vol, size, adv, η, γ)
  fill_rate    = f(participation, spread, vol, regime)
  latency_ms   = lognormal(base, jitter, regime_mult)
  delay_noise  = price_drift(latency, vol, direction)
  rejection    = Bernoulli(vol_prem + size_prem + spread_prem + regime_prem)
"""
from __future__ import annotations
from datetime import datetime
from typing import Callable

from ..constant import SimulationStatus
from ..model.execution_model import (
    SlippageRecord, ExecutionRealityState, CalibrationParams)
from ..utils.execution_utils import (
    new_exec_id,
    vol_scaled_slippage, directional_slippage,
    fill_rate as _fill_rate, realised_fill,
    latency_ms as _latency_ms, delay_noise_bps,
    rejection_probability, is_rejected,
    effective_spread_bps, realized_price as _realized_price,
    calibrate_from_history, _default_params, execution_statistics,
)


class ExecutionSimulator:
    """
    执行现实模拟器 — Phase 2 完整实现。

    每次 simulate() 调用执行以下步骤:
      1. 检查 rejection (Bernoulli 拒绝试验)
      2. 计算 latency (log-normal + regime multiplier)
      3. 计算 delay_noise (price drift during latency)
      4. 计算 slippage (Almgren-Chriss vol-scaled sqrt-participation)
      5. 计算 effective_spread (Kyle 1985 adverse selection)
      6. 计算 fill_rate (participation + spread + vol + regime)
      7. 计算 realized_price = market + direction × total_cost
      8. 构建 SlippageRecord 并更新 ExecutionRealityState

    输入参数 (order_params):
      symbol        : str   — 合约代码
      direction     : int   — +1 buy / -1 sell
      order_size    : float — 订单规模 (shares / contracts)
      market_price  : float — 信号时刻参考价格
      adv           : float — 日均成交量 (default 10000)
      volatility    : float — 日化波动率 (default 0.02)
      spread_bps    : float — 报价买卖价差 bps (default 5.0)
      regime        : str   — normal / stressed / illiquid / crisis
      seed          : int   — 随机种子 (可选, 用于可复现测试)
    """

    def __init__(self, log_fn: Callable | None = None) -> None:
        self._log    = log_fn or (lambda m: None)
        self._status = SimulationStatus.IDLE
        self._params = CalibrationParams()
        self._state  = ExecutionRealityState()

    # ── lifecycle ─────────────────────────────────────────────────────
    def init(self) -> None:
        self._status = SimulationStatus.IDLE
        self._state  = ExecutionRealityState()
        self._log("[ExecutionSimulator] initialised")

    def start(self) -> None:
        self._status = SimulationStatus.RUNNING
        self._log("[ExecutionSimulator] started")

    def stop(self) -> None:
        self._status = SimulationStatus.IDLE
        self._log("[ExecutionSimulator] stopped")

    # ── main entry: simulate one order execution ───────────────────────
    def simulate(self, order_params: dict,
                  seed: int | None = None) -> SlippageRecord:
        """
        Execute one order through the reality simulator.

        Returns
        -------
        SlippageRecord
            Complete execution reality record with all deviations.
        """
        # ── extract params ──────────────────────────────────────────
        symbol      = order_params.get("symbol",       "UNKNOWN")
        direction   = int(order_params.get("direction", 1))
        size        = float(order_params.get("order_size",   1.0))
        mkt_price   = float(order_params.get("market_price", 100.0))
        adv         = float(order_params.get("adv",          10000.0))
        volatility  = float(order_params.get("volatility",   0.02))
        spread_q    = float(order_params.get("spread_bps",   5.0))
        regime      = order_params.get("regime", "normal")

        p = self._params   # calibrated model parameters

        # ── Step 1: rejection check ─────────────────────────────────
        participation = size / max(adv, 1.0)
        eff_spread    = effective_spread_bps(spread_q, volatility, regime)
        rej_prob      = rejection_probability(
            volatility, participation, eff_spread, regime)
        rejected      = is_rejected(rej_prob, seed)

        if rejected:
            rec = SlippageRecord(
                record_id      = new_exec_id(),
                symbol         = symbol,
                direction      = direction,
                order_size     = size,
                adv            = adv,
                order_price    = mkt_price,
                realized_price = mkt_price,   # no fill → no price impact
                slippage_bps   = 0.0,
                spread_bps     = eff_spread,
                delay_noise_bps= 0.0,
                impact_bps     = 0.0,
                total_cost_bps = 0.0,
                fill_rate      = 0.0,
                filled_size    = 0.0,
                rejected       = True,
                latency_ms     = 0.0,
                regime         = regime,
                volatility     = volatility,
            )
            self._append_record(rec)
            self._log(
                f"[ExecSim] REJECTED  {symbol}  dir={direction}  "
                f"size={size}  rej_prob={rej_prob:.3f}")
            return rec

        # ── Step 2: latency ─────────────────────────────────────────
        lat = _latency_ms(
            base_ms   = p.base_latency,
            jitter_ms = p.jitter_ms,
            queue_ms  = p.queue_ms,
            regime    = regime,
            seed      = seed,
        )

        # ── Step 3: delay noise ─────────────────────────────────────
        noise = delay_noise_bps(lat, volatility, direction, seed)

        # ── Step 4: slippage ─────────────────────────────────────────
        raw_slip = vol_scaled_slippage(
            volatility = volatility,
            size       = size,
            adv        = adv,
            spread_bps = eff_spread,
            base_bps   = p.base_bps,
            eta        = p.eta,
            gamma      = p.gamma,
        )
        # add directional noise (adverse selection skew)
        slip = directional_slippage(raw_slip, volatility, direction, seed)
        slip = max(0.0, slip)

        # ── Step 5: fill rate ────────────────────────────────────────
        fr    = _fill_rate(size, adv, eff_spread, volatility, regime)
        filled = realised_fill(size, fr, seed)

        # ── Step 6: total cost & realized price ──────────────────────
        total_cost = slip + eff_spread * 0.5 + abs(noise)
        real_px    = _realized_price(mkt_price, slip, eff_spread, noise, direction)

        # ── Step 7: build record ─────────────────────────────────────
        rec = SlippageRecord(
            record_id       = new_exec_id(),
            symbol          = symbol,
            direction       = direction,
            order_size      = size,
            adv             = adv,
            order_price     = mkt_price,
            realized_price  = real_px,
            slippage_bps    = round(slip,       4),
            spread_bps      = round(eff_spread, 4),
            delay_noise_bps = round(noise,      4),
            impact_bps      = 0.0,   # Phase 3
            total_cost_bps  = round(total_cost, 4),
            fill_rate       = fr,
            filled_size     = filled,
            rejected        = False,
            latency_ms      = lat,
            regime          = regime,
            volatility      = volatility,
        )
        self._append_record(rec)
        self._log(
            f"[ExecSim] FILLED  {symbol}  dir={direction}  "
            f"size={size:.2f}→{filled:.2f}({fr:.1%})  "
            f"slip={slip:.2f}bps  lat={lat:.1f}ms  "
            f"realized={real_px:.6f}")
        return rec

    # ── batch simulation ───────────────────────────────────────────────
    def simulate_batch(self, orders: list[dict],
                        seed_start: int | None = None) -> list[SlippageRecord]:
        """
        Simulate a batch of orders. Each order uses an independent
        random seed (seed_start + i) if seed_start is provided.
        """
        results = []
        for i, op in enumerate(orders):
            seed = (seed_start + i) if seed_start is not None else None
            results.append(self.simulate(op, seed=seed))
        return results

    # ── calibration ───────────────────────────────────────────────────
    def calibrate(self, historical_trades: list[dict],
                   adv: float = 10000.0) -> CalibrationParams:
        """
        Calibrate model parameters from historical execution data.
        Updates internal _params in place.
        """
        raw = calibrate_from_history(historical_trades, adv)
        self._params = CalibrationParams.from_dict(raw)
        self._log(
            f"[ExecSim] calibrated  n={self._params.n_samples}  "
            f"base={self._params.base_bps}bps  "
            f"eta={self._params.eta}  gamma={self._params.gamma}")
        return self._params

    def set_params(self, **kwargs) -> None:
        """Directly override individual model parameters."""
        for k, v in kwargs.items():
            if hasattr(self._params, k):
                setattr(self._params, k, v)

    # ── query ──────────────────────────────────────────────────────────
    def get_state(self) -> ExecutionRealityState:
        return self._state

    def get_statistics(self) -> dict:
        """Return aggregated statistics dict."""
        return self._state.to_dict()

    def get_records(self, limit: int = 500) -> list[SlippageRecord]:
        return self._state.records[-limit:]

    def get_params(self) -> CalibrationParams:
        return self._params

    @property
    def status(self) -> SimulationStatus:
        return self._status

    # ── internal ──────────────────────────────────────────────────────
    def _append_record(self, rec: SlippageRecord) -> None:
        self._state.records.append(rec)
        if len(self._state.records) > 10000:
            self._state.records = self._state.records[-10000:]
        self._state.update_from_records()
        self._state.status = SimulationStatus.RUNNING
