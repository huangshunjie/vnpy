"""
market_reality_ai/utils/impact_utils.py

Phase 3: Market Impact math core.

Total Impact = Temporary + Permanent + Spread Cost
  Temporary : eta_T * vol * participation^alpha  (Almgren-Chriss)
  Permanent : eta_P * vol * participation        (Kyle lambda)
  Spread    : lambda_AS * vol * k                (Kyle 1985)
  Decay     : I0 * exp(-ln2 * t / half_life)
"""
from __future__ import annotations
import math
import uuid
from datetime import datetime


def new_impact_id() -> str:
    return f"IMP_{uuid.uuid4().hex[:8].upper()}"


_REGIME_MULT = {
    "normal": 1.0, "stressed": 2.0, "illiquid": 4.0, "crisis": 8.0}


def regime_multiplier(regime: str) -> float:
    return _REGIME_MULT.get(regime, 1.0)


def participation_rate(order_size: float, adv: float) -> float:
    return min(1.0, max(0.0, order_size / max(adv, 1.0)))


# ── Temporary impact (Almgren-Chriss) ────────────────────────────────

def temporary_impact_bps(
    volatility:   float,
    order_size:   float,
    adv:          float,
    eta_T:        float = 0.20,
    alpha:        float = 0.50,
    regime:       str   = "normal",
    market_depth: float = 1.0,
) -> float:
    """
    eta_T * vol_bps * participation^alpha / depth * regime_mult
    Returns basis points.
    """
    part   = participation_rate(order_size, adv)
    vol_bp = volatility * 10000.0
    depth  = max(market_depth, 0.01)
    rmult  = regime_multiplier(regime)
    return round(max(0.0,
        eta_T * vol_bp * (part ** alpha) / depth * rmult), 4)


# ── Permanent impact (Kyle lambda) ───────────────────────────────────

def permanent_impact_bps(
    volatility:   float,
    order_size:   float,
    adv:          float,
    eta_P:        float = 0.05,
    regime:       str   = "normal",
    market_depth: float = 1.0,
) -> float:
    """
    eta_P * vol_bps * participation / depth * regime_mult
    Returns basis points.
    """
    part   = participation_rate(order_size, adv)
    vol_bp = volatility * 10000.0
    depth  = max(market_depth, 0.01)
    rmult  = regime_multiplier(regime)
    return round(max(0.0,
        eta_P * vol_bp * part / depth * rmult), 4)


# ── Adverse selection spread cost (Kyle 1985) ─────────────────────────

def spread_cost_bps(
    quoted_spread_bps: float,
    volatility:        float,
    regime:            str   = "normal",
    lambda_as:         float = 1.0,
) -> float:
    """
    Effective half-spread cost = 0.5 * (quoted + adverse_selection).
    Adverse selection: lambda_as * regime_mult * 0.5 * vol_bps * 0.1
    Returns basis points.
    """
    lam_adj = lambda_as * regime_multiplier(regime) * 0.5
    adverse = lam_adj * volatility * 10000.0 * 0.1
    eff     = quoted_spread_bps + adverse
    return round(max(quoted_spread_bps * 0.5, eff * 0.5), 4)


# ── Total impact breakdown ────────────────────────────────────────────

def total_impact_bps(
    volatility:        float,
    order_size:        float,
    adv:               float,
    quoted_spread_bps: float = 5.0,
    eta_T:             float = 0.20,
    eta_P:             float = 0.05,
    alpha:             float = 0.50,
    regime:            str   = "normal",
    market_depth:      float = 1.0,
    lambda_as:         float = 1.0,
) -> dict:
    """Returns dict: temporary_bps, permanent_bps, spread_cost_bps,
    total_cost_bps, participation."""
    temp = temporary_impact_bps(
        volatility, order_size, adv, eta_T, alpha, regime, market_depth)
    perm = permanent_impact_bps(
        volatility, order_size, adv, eta_P, regime, market_depth)
    sprd = spread_cost_bps(
        quoted_spread_bps, volatility, regime, lambda_as)
    part = participation_rate(order_size, adv)
    return {
        "temporary_bps":   temp,
        "permanent_bps":   perm,
        "spread_cost_bps": sprd,
        "total_cost_bps":  round(temp + perm + sprd, 4),
        "participation":   round(part, 6),
    }


# ── Decay model ───────────────────────────────────────────────────────

def decay_half_life(
    adv:        float,
    volatility: float,
    regime:     str = "normal",
) -> float:
    """
    Half-life of temporary impact in seconds.
    base=300s, modulated by ADV, volatility, regime.
    """
    base   = 300.0
    adv_f  = (max(adv, 100.0) / 10000.0) ** (-0.3)
    vol_f  = (max(volatility, 0.005) / 0.02) ** (-0.2)
    r_adj  = {"normal": 1.0, "stressed": 2.0,
               "illiquid": 3.5, "crisis": 6.0}.get(regime, 1.0)
    return round(max(30.0, base * adv_f * vol_f * r_adj), 1)


def decayed_impact(
    initial_bps:       float,
    elapsed_seconds:   float,
    half_life_seconds: float,
) -> float:
    """I(t) = I0 * exp(-ln2 * t / T_half). Returns basis points."""
    if half_life_seconds <= 0:
        return 0.0
    return round(
        initial_bps
        * math.exp(-math.log(2) * elapsed_seconds / half_life_seconds), 4)


# ── Impact-adjusted price ────────────────────────────────────────────

def impact_adjusted_price(
    market_price: float,
    impact_bps:   float,
    direction:    int,
) -> float:
    """BUY: impact pushes price up. SELL: down."""
    return round(
        market_price * (1.0 + direction * impact_bps / 10000.0), 8)


# ── Liquidity score ───────────────────────────────────────────────────

def liquidity_score(
    spread_bps:   float,
    adv:          float,
    market_depth: float,
    volatility:   float,
) -> float:
    """Composite liquidity score in [0, 100]. 100 = perfectly liquid."""
    sp_score    = max(0.0, 100.0 - spread_bps * 0.5)
    adv_score   = min(100.0, adv / 100.0)
    depth_score = market_depth * 100.0
    vol_score   = max(0.0, 100.0 - volatility * 10000.0 * 0.5)
    return round(
        sp_score * 0.30 + adv_score * 0.30
        + depth_score * 0.25 + vol_score * 0.15, 2)


# ── Calibration ───────────────────────────────────────────────────────

def default_impact_params() -> dict:
    return {"eta_T": 0.20, "eta_P": 0.05, "alpha": 0.50,
            "lambda_as": 1.0, "calibrated": False}


def calibrate_impact_params(
    observations: list[dict], adv: float = 10000.0) -> dict:
    """
    OLS estimate of eta_T from observed (order_size, realized_cost_bps,
    volatility) triples. Each obs: {order_size, realized_cost_bps, volatility}
    """
    if not observations:
        return default_impact_params()
    numer = denom = 0.0
    for obs in observations:
        size  = obs.get("order_size",        1.0)
        cost  = obs.get("realized_cost_bps", 0.0)
        vol   = obs.get("volatility",        0.02)
        part  = participation_rate(size, adv)
        vol_bp= vol * 10000.0
        basis = vol_bp * (part ** 0.5)
        numer += cost * basis
        denom += basis * basis
    eta_fit = max(0.01, min(1.0, numer / max(denom, 1e-9)))
    return {
        "eta_T": round(eta_fit, 4), "eta_P": round(eta_fit * 0.25, 4),
        "alpha": 0.50, "lambda_as": 1.0,
        "n_samples": len(observations), "calibrated": True,
    }


# ── Statistics ────────────────────────────────────────────────────────

def impact_statistics(estimates: list[dict]) -> dict:
    """Aggregate impact stats from ImpactEstimate dicts."""
    if not estimates:
        return {"count": 0, "avg_total_cost_bps": 0.0,
                "p95_total_cost_bps": 0.0, "avg_temporary_bps": 0.0,
                "avg_permanent_bps": 0.0, "avg_spread_cost_bps": 0.0,
                "avg_participation": 0.0}
    n = len(estimates)
    totals = sorted(e.get("total_cost_bps", 0.0) for e in estimates)
    def _p(sl, p): return sl[min(int(len(sl)*p), len(sl)-1)]
    return {
        "count":               n,
        "avg_total_cost_bps":  round(sum(totals)/n, 4),
        "p95_total_cost_bps":  round(_p(totals, 0.95), 4),
        "avg_temporary_bps":   round(sum(e.get("temporary_bps",  0)
                                          for e in estimates)/n, 4),
        "avg_permanent_bps":   round(sum(e.get("permanent_bps",  0)
                                          for e in estimates)/n, 4),
        "avg_spread_cost_bps": round(sum(e.get("spread_cost_bps",0)
                                          for e in estimates)/n, 4),
        "avg_participation":   round(sum(e.get("participation",  0)
                                          for e in estimates)/n, 6),
    }
