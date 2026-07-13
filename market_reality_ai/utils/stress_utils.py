"""
market_reality_ai/utils/stress_utils.py

Phase 4: Stress Testing math core.

Scenario parameters + drawdown analysis + survival scoring.

Six standard scenarios:
  flash_crash          shock=-20%  liq*0.1  vol*5   dur=5bars
  liquidity_dry_up     shock=-5%   liq*0.05 vol*3   dur=20bars
  extreme_volatility   shock=+/-15% vol*6   regime=crisis
  regime_collapse      corr breakdown + impact*8
  correlation_breakdown diversification fails simultaneously
  fat_tail_event       6-sigma price move, permanent impact

Survival grade mapping:
  score >= 90 -> S   (survives all scenarios)
  score >= 75 -> A
  score >= 60 -> B
  score >= 40 -> C
  score <  40 -> F   (system dies)
"""
from __future__ import annotations
import math
import uuid
from datetime import datetime


def new_stress_id() -> str:
    return f"STR_{uuid.uuid4().hex[:8].upper()}"


def new_wf_id() -> str:
    return f"WF_{uuid.uuid4().hex[:8].upper()}"


# ── Standard scenario parameter presets ──────────────────────────────

SCENARIO_PRESETS: dict[str, dict] = {
    "flash_crash": {
        "shock_magnitude":  -0.20,
        "duration_bars":    5,
        "liquidity_factor": 0.10,
        "volatility_mult":  5.0,
        "correlation_adj":  0.30,
        "regime":           "crisis",
        "description":      "Sudden -20% price drop, liquidity evaporates",
    },
    "liquidity_dry_up": {
        "shock_magnitude":  -0.05,
        "duration_bars":    20,
        "liquidity_factor": 0.05,
        "volatility_mult":  3.0,
        "correlation_adj":  0.20,
        "regime":           "illiquid",
        "description":      "Sustained liquidity withdrawal, spreads widen 10x",
    },
    "extreme_volatility": {
        "shock_magnitude":  0.15,    # magnitude (direction random)
        "duration_bars":    10,
        "liquidity_factor": 0.30,
        "volatility_mult":  6.0,
        "correlation_adj":  0.15,
        "regime":           "crisis",
        "description":      "Vol spike to 6x normal, circuit-breaker territory",
    },
    "regime_collapse": {
        "shock_magnitude":  -0.35,
        "duration_bars":    30,
        "liquidity_factor": 0.15,
        "volatility_mult":  4.0,
        "correlation_adj":  0.80,   # all assets correlate to 1
        "regime":           "crisis",
        "description":      "Full regime shift, diversification fails",
    },
    "correlation_breakdown": {
        "shock_magnitude":  -0.12,
        "duration_bars":    15,
        "liquidity_factor": 0.40,
        "volatility_mult":  3.5,
        "correlation_adj":  0.90,
        "regime":           "stressed",
        "description":      "Cross-asset correlations spike to 0.9+",
    },
    "fat_tail_event": {
        "shock_magnitude":  -0.08,   # 6-sigma move
        "duration_bars":    3,
        "liquidity_factor": 0.20,
        "volatility_mult":  8.0,
        "correlation_adj":  0.50,
        "regime":           "crisis",
        "description":      "6-sigma tail event, permanent market impact",
    },
}


def get_scenario_params(scenario_type: str,
                         overrides: dict | None = None) -> dict:
    """Return scenario parameters, optionally overridden."""
    base = dict(SCENARIO_PRESETS.get(scenario_type, SCENARIO_PRESETS["flash_crash"]))
    if overrides:
        base.update(overrides)
    return base


# ── Portfolio shock simulation ────────────────────────────────────────

def apply_price_shock(
    portfolio_value: float,
    shock_magnitude: float,
    correlation_adj: float = 0.0,
    n_positions:     int   = 10,
) -> float:
    """
    Apply price shock to portfolio.

    With correlation_adj > 0, diversification benefit is reduced:
      effective_shock = shock * (1 - diversification_benefit)
      diversification_benefit = (1 - correlation_adj) / sqrt(n_positions)

    Returns shocked portfolio value.
    """
    # diversification_benefit: low correlation softens shock
    # high correlation (close to 1.0) -> benefit near 0 -> full shock
    diversification_benefit = max(0.0, (1.0 - correlation_adj) / math.sqrt(max(n_positions, 1)))
    # effective_shock = shock * (1 - benefit): high corr makes shock worse (larger magnitude)
    effective_shock = shock_magnitude * (1.0 - diversification_benefit)
    effective_shock = max(-0.99, min(effective_shock, 0.99))
    return round(portfolio_value * (1.0 + effective_shock), 4)


def simulate_drawdown_path(
    initial_value:   float,
    shock_magnitude: float,
    duration_bars:   int,
    volatility_mult: float,
    liquidity_factor:float,
    correlation_adj: float = 0.0,
    n_positions:     int   = 10,
    seed:            int   = 42,
) -> list[float]:
    """
    Simulate portfolio value path under stress scenario.

    The path models:
    - Immediate shock at bar 0
    - Continued pressure from elevated vol and reduced liquidity
    - Partial recovery starting at bar duration_bars//2
    - Final level determined by permanent impact fraction

    Returns list of portfolio values (length = duration_bars + 1).
    """
    import random
    rng    = random.Random(seed)
    path   = [initial_value]
    value  = initial_value

    # immediate shock
    shocked = apply_price_shock(
        value, shock_magnitude, correlation_adj, n_positions)
    path.append(shocked)
    value = shocked

    # continued stress bars
    daily_vol = 0.02 * volatility_mult
    liq_drag  = max(0.0, (1.0 - liquidity_factor) * 0.005)

    for bar in range(1, duration_bars):
        # stressed random walk
        noise  = rng.gauss(0.0, daily_vol)
        # mean-reversion toward shock level (partial recovery)
        recovery = (initial_value * (1.0 + shock_magnitude * 0.5) - value) * 0.05
        # liquidity drag: wide spreads eat into value each bar
        value  = value * (1.0 + noise) + recovery - abs(value) * liq_drag
        value  = max(0.01, value)
        path.append(round(value, 4))

    return path


def max_drawdown_from_path(path: list[float]) -> float:
    """Maximum drawdown from a price/value path."""
    if not path or len(path) < 2:
        return 0.0
    peak = path[0]
    mdd  = 0.0
    for v in path:
        if v > peak:
            peak = v
        dd = (peak - v) / peak if peak > 1e-9 else 0.0
        if dd > mdd:
            mdd = dd
    return round(mdd, 6)


def survival_rate_from_path(
    path:            list[float],
    initial_value:   float,
    survival_threshold: float = 0.50,
) -> float:
    """
    Fraction of the path where portfolio value >= survival_threshold * initial.
    survival_threshold=0.5 means the portfolio must retain at least 50%
    of initial value to be considered 'surviving'.
    """
    if not path or initial_value <= 0:
        return 0.0
    floor  = survival_threshold * initial_value
    alive  = sum(1 for v in path if v >= floor)
    return round(alive / len(path), 4)


# ── Execution degradation under stress ───────────────────────────────

def execution_degradation(
    liquidity_factor: float,
    volatility_mult:  float,
    regime:           str = "normal",
) -> float:
    """
    Execution quality loss ∈ [0.0, 1.0] under stress scenario.

    0.0 = perfect execution (no degradation)
    1.0 = complete execution breakdown

    Model:
      base = 1 - liquidity_factor   (illiquid → high degradation)
      vol_component = (vol_mult - 1) / 10  (clipped)
      regime_component
    """
    base      = 1.0 - max(0.0, min(1.0, liquidity_factor))
    vol_comp  = min((volatility_mult - 1.0) / 10.0, 0.30)
    regime_comp = {"normal": 0.0, "stressed": 0.05,
                   "illiquid": 0.15, "crisis": 0.25}.get(regime, 0.0)
    return round(min(1.0, base + vol_comp + regime_comp), 4)


def fill_rate_under_stress(
    normal_fill_rate: float,
    liquidity_factor: float,
    volatility_mult:  float,
) -> float:
    """
    Fill rate degradation under stress.
    normal_fill_rate is the baseline (e.g. 0.95).
    """
    liq_pen = (1.0 - liquidity_factor) * 0.6
    vol_pen = min((volatility_mult - 1.0) / 20.0, 0.20)
    return round(max(0.02, normal_fill_rate - liq_pen - vol_pen), 4)


def slippage_under_stress(
    normal_slippage_bps: float,
    liquidity_factor:    float,
    volatility_mult:     float,
) -> float:
    """Slippage (bps) amplification under stress."""
    liq_amp = 1.0 / max(liquidity_factor, 0.01)
    vol_amp = volatility_mult
    return round(normal_slippage_bps * liq_amp * vol_amp * 0.5, 2)


# ── Survival scoring ─────────────────────────────────────────────────

def scenario_survival_score(
    max_drawdown:     float,
    survival_rate:    float,
    exec_degradation: float,
) -> float:
    """
    Score a single scenario result: 0–100.

    Components:
      drawdown_score   = 100 * max(0, 1 - max_drawdown / 0.5)  (50% dd → 0)
      survival_score   = 100 * survival_rate
      exec_score       = 100 * (1 - exec_degradation)
    Weights: 50% drawdown, 30% survival, 20% execution.
    """
    dd_score   = max(0.0, 100.0 * (1.0 - max_drawdown / 0.50))
    surv_score = 100.0 * survival_rate
    exec_score = 100.0 * (1.0 - exec_degradation)
    return round(
        dd_score * 0.50 + surv_score * 0.30 + exec_score * 0.20, 2)


def system_survival_score(scenario_scores: list[float]) -> float:
    """
    Aggregate system survival score from all scenario scores.

    Uses a pessimistic (min-weighted) aggregation:
      system_score = 0.6 * mean + 0.4 * min
    This ensures one catastrophic failure pulls the score down hard.
    """
    if not scenario_scores:
        return 0.0
    mean_s = sum(scenario_scores) / len(scenario_scores)
    min_s  = min(scenario_scores)
    return round(0.6 * mean_s + 0.4 * min_s, 2)


def survival_grade(score: float) -> str:
    """Map 0–100 score to S/A/B/C/F grade."""
    if score >= 90: return "S"
    if score >= 75: return "A"
    if score >= 60: return "B"
    if score >= 40: return "C"
    return "F"


def worst_grade(grades: list[str]) -> str:
    """Return the worst grade from a list."""
    order = {"S": 5, "A": 4, "B": 3, "C": 2, "F": 1}
    if not grades:
        return "F"
    return min(grades, key=lambda g: order.get(g, 0))


# ── Walk-Forward reality gap ──────────────────────────────────────────

def reality_gap_bps(
    backtest_return:  float,
    realized_return:  float,
) -> float:
    """
    Reality gap = backtest_return - realized_return (in bps).
    Positive = backtest was optimistic (system overestimates performance).
    Negative = system outperformed backtest (rare).
    """
    return round((backtest_return - realized_return) * 10000.0, 4)


def reality_gap_score(avg_gap_bps: float) -> float:
    """
    Convert average reality gap to a 0–100 score.
    0 gap -> 100 (perfect), 100bps gap -> 0 (system is unrealistic).
    """
    return round(max(0.0, 100.0 - abs(avg_gap_bps)), 2)


def regime_label_from_vol(volatility: float) -> str:
    """Classify regime from volatility."""
    if volatility < 0.015:  return "low_vol"
    if volatility < 0.030:  return "normal"
    if volatility < 0.060:  return "stressed"
    return "crisis"
