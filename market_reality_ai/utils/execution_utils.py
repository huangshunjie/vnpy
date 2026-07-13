"""
market_reality_ai/utils/execution_utils.py

Phase 2: 执行现实数学核心。

Realized Price = Market Price + Slippage + Impact + Delay Noise
──────────────────────────────────────────────────────────────
Slippage   : vol-scaled sqrt-participation (Almgren-Chriss)
Fill Rate  : participation + spread + volatility + regime
Latency    : log-normal distribution with regime multiplier
Delay Noise: price drift during latency period
Rejection  : volatility + size + spread + regime
"""
from __future__ import annotations
import math
import random
import uuid
from datetime import datetime


def new_exec_id() -> str:
    return f"EXEC_{uuid.uuid4().hex[:8].upper()}"


def now_str() -> str:
    return str(datetime.now())[:19]


# ── Core formula: Realized Price ─────────────────────────────────────

def realized_price(
    market_price:    float,
    slippage_bps:    float,
    spread_bps:      float,
    delay_noise_bps: float,
    direction:       int,    # +1 buy / -1 sell
) -> float:
    """
    Realized Price = Market Price × (1 + direction × total_cost_bps / 10000)
    total_cost_bps = slippage + ½ spread + delay_noise (signed)
    """
    total = slippage_bps + spread_bps * 0.5 + delay_noise_bps * direction
    return round(market_price * (1.0 + direction * total / 10000.0), 8)


# ── Slippage model (Almgren-Chriss) ──────────────────────────────────

def vol_scaled_slippage(
    volatility: float,
    size:       float,
    adv:        float,
    spread_bps: float = 5.0,
    base_bps:   float = 2.0,
    eta:        float = 0.10,
    gamma:      float = 0.03,
) -> float:
    """
    Slippage ≈ base + η·σ·√(participation) + γ·σ·participation + ½ spread

    η  : temporary impact coefficient (default 0.10)
    γ  : permanent impact coefficient (default 0.03)
    """
    if adv < 1e-9:
        return base_bps + spread_bps * 0.5
    part    = size / adv
    vol_bps = volatility * 10000.0
    temp    = eta   * vol_bps * math.sqrt(part)
    perm    = gamma * vol_bps * part
    return round(max(0.0, base_bps + temp + perm + spread_bps * 0.5), 4)


def directional_slippage(
    slippage_bps: float,
    volatility:   float,
    direction:    int,
    seed: int | None = None,
) -> float:
    """Add adverse-selection noise: buys tend to receive worse fills."""
    rng  = random.Random(seed) if seed is not None else random.Random()
    noise = rng.gauss(0.0, volatility * 5000.0)
    skew  = abs(noise) * 0.2 * direction
    return round(slippage_bps + skew, 4)


# ── Fill rate model ───────────────────────────────────────────────────

def fill_rate(
    size:       float,
    adv:        float,
    spread_bps: float = 5.0,
    volatility: float = 0.02,
    regime:     str   = "normal",
) -> float:
    """
    Fill rate ∈ [0.05, 1.0].
    base = 1 − clip(2 × participation, 0, 0.8)
    minus spread penalty, vol penalty, regime penalty.
    """
    part       = size / max(adv, 1.0)
    base       = 1.0 - min(2.0 * part, 0.8)
    spread_pen = max(0.0, (spread_bps - 10.0) / 200.0)
    vol_pen    = max(0.0, (volatility - 0.03) * 3.0)
    regime_adj = {"normal": 0.0, "stressed": -0.15,
                  "illiquid": -0.30, "crisis": -0.50}.get(regime, 0.0)
    return round(max(0.05, min(1.0, base - spread_pen - vol_pen + regime_adj)), 4)


def realised_fill(requested_size: float, fill_rate_val: float,
                   seed: int | None = None) -> float:
    """Stochastic realised fill with ±5% noise on fill rate."""
    rng  = random.Random(seed) if seed is not None else random.Random()
    rate = max(0.0, min(1.0, fill_rate_val + rng.gauss(0.0, 0.05)))
    return round(requested_size * rate, 6)


# ── Latency model (log-normal) ────────────────────────────────────────

def latency_ms(
    base_ms:   float = 5.0,
    jitter_ms: float = 3.0,
    queue_ms:  float = 0.0,
    regime:    str   = "normal",
    seed: int | None = None,
) -> float:
    """
    Latency = lognormal(base × regime_mult) + queue_ms × regime_mult
    Regime multipliers: normal×1 / stressed×2.5 / illiquid×4 / crisis×8
    """
    rng   = random.Random(seed) if seed is not None else random.Random()
    rmult = {"normal": 1.0, "stressed": 2.5,
             "illiquid": 4.0, "crisis": 8.0}.get(regime, 1.0)
    bm    = max(0.1, base_ms * rmult)
    mu    = math.log(bm)
    sigma = max(0.1, jitter_ms / bm)
    return round(max(0.1, rng.lognormvariate(mu, sigma) + queue_ms * rmult), 2)


def delay_noise_bps(
    latency_val: float,
    volatility:  float,
    direction:   int,
    seed: int | None = None,
) -> float:
    """
    Price drift during latency: N(0, σ·√Δt) where Δt = latency / 86_400_000.
    Returns signed bps (positive = adverse to trader).
    """
    rng   = random.Random(seed) if seed is not None else random.Random()
    dt    = latency_val / 86_400_000.0
    sigma_t = volatility * math.sqrt(max(dt, 1e-10))
    drift   = rng.gauss(0.0, sigma_t) * 10000.0
    return round(drift * 0.5, 4)


# ── Rejection model ───────────────────────────────────────────────────

def rejection_probability(
    volatility:    float,
    participation: float,
    spread_bps:    float,
    regime:        str = "normal",
) -> float:
    """
    Rejection prob in [0.0, 0.95].
    Base 2% + vol premium + size premium + spread premium + regime premium.
    """
    vol_prem    = min(max(0.0, (volatility    - 0.02) * 15.0), 0.50)
    size_prem   = min(max(0.0, (participation - 0.10) * 0.80), 0.30)
    spread_prem = max(0.0, (spread_bps - 20.0) / 300.0)
    regime_prem = {"normal": 0.0, "stressed": 0.10,
                   "illiquid": 0.20, "crisis": 0.40}.get(regime, 0.0)
    return round(min(0.95, 0.02 + vol_prem + size_prem + spread_prem + regime_prem), 4)


def is_rejected(prob: float, seed: int | None = None) -> bool:
    """Bernoulli trial for order rejection."""
    rng = random.Random(seed) if seed is not None else random.Random()
    return rng.random() < prob


# ── Effective spread ──────────────────────────────────────────────────

def effective_spread_bps(
    quoted_spread_bps: float,
    volatility:        float,
    regime:            str = "normal",
) -> float:
    """
    Effective spread = quoted spread + adverse-selection component.
    Kyle (1985): adverse selection ~ lambda * sigma, lambda higher in stress.
    """
    lam     = {"normal": 0.8, "stressed": 1.5,
               "illiquid": 2.0, "crisis": 3.0}.get(regime, 0.8)
    adverse = lam * volatility * 10000.0 * 0.1
    return round(max(quoted_spread_bps, quoted_spread_bps + adverse), 4)


# ── Calibration ───────────────────────────────────────────────────────

def _default_params() -> dict:
    return {
        "base_bps": 2.0, "eta": 0.10, "gamma": 0.03,
        "avg_fill": 0.95, "avg_latency": 5.0,
        "rej_rate": 0.02, "n_samples": 0, "calibrated": False,
    }


def calibrate_from_history(trades: list, adv: float = 10000.0) -> dict:
    """
    Estimate model parameters from historical trade records.
    Each record: {order_price, realized_price, size, latency_ms,
                  fill_rate, rejected, volatility}
    """
    if not trades:
        return _default_params()

    slippages, fills, lats, rej_n = [], [], [], 0
    for t in trades:
        op = t.get("order_price", 0.0)
        rp = t.get("realized_price", op)
        if op > 0:
            slippages.append(abs(rp - op) / op * 10000.0)
        fills.append(t.get("fill_rate",  1.0))
        lats.append(t.get("latency_ms", 5.0))
        if t.get("rejected", False):
            rej_n += 1

    n         = len(trades)
    avg_slip  = sum(slippages) / len(slippages) if slippages else 3.0
    avg_fill  = sum(fills)     / len(fills)
    avg_lat   = sum(lats)      / len(lats)
    avg_part  = sum(t.get("size", 1.0) / adv for t in trades) / n
    avg_vol   = sum(t.get("volatility", 0.02) for t in trades) / n
    vol_bps   = avg_vol * 10000.0
    sqrt_part = math.sqrt(max(avg_part, 1e-6))
    eta_fit   = max(0.01, min(0.5, (avg_slip - 2.0) / (vol_bps * sqrt_part + 1e-9)))

    return {
        "base_bps":    round(max(0.5, avg_slip * 0.3), 4),
        "eta":         round(eta_fit,       4),
        "gamma":       round(eta_fit * 0.3, 4),
        "avg_fill":    round(avg_fill,       4),
        "avg_latency": round(avg_lat,        2),
        "rej_rate":    round(rej_n / n,      4),
        "n_samples":   n,
        "calibrated":  True,
    }


# ── Statistics ────────────────────────────────────────────────────────

def execution_statistics(records: list) -> dict:
    """Aggregate p50/p95 slippage, fill rate, latency, rejection rate."""
    if not records:
        return {
            "count": 0, "avg_slippage_bps": 0.0,
            "p50_slippage_bps": 0.0, "p95_slippage_bps": 0.0,
            "avg_fill_rate": 0.0, "avg_latency_ms": 0.0,
            "rejection_rate": 0.0, "reality_gap_bps": 0.0,
        }

    slips = sorted(r.get("slippage_bps", 0.0) for r in records)
    fills = [r.get("fill_rate",  1.0) for r in records]
    lats  = [r.get("latency_ms", 0.0) for r in records]
    n     = len(records)

    def _p(sl, p):
        return round(sl[min(int(len(sl) * p), len(sl) - 1)], 4)

    rej_n = sum(1 for r in records if r.get("rejected", False))
    avg_s = sum(slips) / n
    avg_f = sum(fills) / n

    return {
        "count":            n,
        "avg_slippage_bps": round(avg_s,      4),
        "p50_slippage_bps": _p(slips, 0.50),
        "p95_slippage_bps": _p(slips, 0.95),
        "avg_fill_rate":    round(avg_f,       4),
        "avg_latency_ms":   round(sum(lats)/n, 2),
        "rejection_rate":   round(rej_n / n,   4),
        "reality_gap_bps":  round(avg_s * (2.0 - avg_f), 4),
    }


# ── Rejection model ───────────────────────────────────────────────────

def rejection_probability(
    volatility:    float,
    participation: float,
    spread_bps:    float,
    regime:        str = "normal",
) -> float:
    """
    Rejection prob in [0.0, 0.95].
    Base 2% + vol premium + size premium + spread premium + regime premium.
    """
    vol_prem    = min(max(0.0, (volatility    - 0.02) * 15.0), 0.50)
    size_prem   = min(max(0.0, (participation - 0.10) * 0.80), 0.30)
    spread_prem = max(0.0, (spread_bps - 20.0) / 300.0)
    regime_prem = {"normal": 0.0, "stressed": 0.10,
                   "illiquid": 0.20, "crisis": 0.40}.get(regime, 0.0)
    return round(min(0.95, 0.02 + vol_prem + size_prem + spread_prem + regime_prem), 4)


def is_rejected(prob: float, seed: int | None = None) -> bool:
    """Bernoulli trial for order rejection."""
    rng = random.Random(seed) if seed is not None else random.Random()
    return rng.random() < prob


# ── Effective spread ──────────────────────────────────────────────────

def effective_spread_bps(
    quoted_spread_bps: float,
    volatility:        float,
    regime:            str = "normal",
) -> float:
    """
    Effective spread = quoted spread + adverse-selection component.
    Kyle (1985): adverse selection ~ lambda * sigma, lambda higher in stress.
    """
    lam     = {"normal": 0.8, "stressed": 1.5,
               "illiquid": 2.0, "crisis": 3.0}.get(regime, 0.8)
    adverse = lam * volatility * 10000.0 * 0.1
    return round(max(quoted_spread_bps, quoted_spread_bps + adverse), 4)


# ── Calibration ───────────────────────────────────────────────────────

def _default_params() -> dict:
    return {
        "base_bps": 2.0, "eta": 0.10, "gamma": 0.03,
        "avg_fill": 0.95, "avg_latency": 5.0,
        "rej_rate": 0.02, "n_samples": 0, "calibrated": False,
    }


def calibrate_from_history(trades: list, adv: float = 10000.0) -> dict:
    """
    Estimate model parameters from historical trade records.
    Each record: {order_price, realized_price, size, latency_ms,
                  fill_rate, rejected, volatility}
    """
    if not trades:
        return _default_params()

    slippages, fills, lats, rej_n = [], [], [], 0
    for t in trades:
        op = t.get("order_price", 0.0)
        rp = t.get("realized_price", op)
        if op > 0:
            slippages.append(abs(rp - op) / op * 10000.0)
        fills.append(t.get("fill_rate",  1.0))
        lats.append(t.get("latency_ms", 5.0))
        if t.get("rejected", False):
            rej_n += 1

    n         = len(trades)
    avg_slip  = sum(slippages) / len(slippages) if slippages else 3.0
    avg_fill  = sum(fills)     / len(fills)
    avg_lat   = sum(lats)      / len(lats)
    avg_part  = sum(t.get("size", 1.0) / adv for t in trades) / n
    avg_vol   = sum(t.get("volatility", 0.02) for t in trades) / n
    vol_bps   = avg_vol * 10000.0
    sqrt_part = math.sqrt(max(avg_part, 1e-6))
    eta_fit   = max(0.01, min(0.5, (avg_slip - 2.0) / (vol_bps * sqrt_part + 1e-9)))

    return {
        "base_bps":    round(max(0.5, avg_slip * 0.3), 4),
        "eta":         round(eta_fit,       4),
        "gamma":       round(eta_fit * 0.3, 4),
        "avg_fill":    round(avg_fill,       4),
        "avg_latency": round(avg_lat,        2),
        "rej_rate":    round(rej_n / n,      4),
        "n_samples":   n,
        "calibrated":  True,
    }


# ── Statistics ────────────────────────────────────────────────────────

def execution_statistics(records: list) -> dict:
    """Aggregate p50/p95 slippage, fill rate, latency, rejection rate."""
    if not records:
        return {
            "count": 0, "avg_slippage_bps": 0.0,
            "p50_slippage_bps": 0.0, "p95_slippage_bps": 0.0,
            "avg_fill_rate": 0.0, "avg_latency_ms": 0.0,
            "rejection_rate": 0.0, "reality_gap_bps": 0.0,
        }

    slips = sorted(r.get("slippage_bps", 0.0) for r in records)
    fills = [r.get("fill_rate",  1.0) for r in records]
    lats  = [r.get("latency_ms", 0.0) for r in records]
    n     = len(records)

    def _p(sl, p):
        return round(sl[min(int(len(sl) * p), len(sl) - 1)], 4)

    rej_n = sum(1 for r in records if r.get("rejected", False))
    avg_s = sum(slips) / n
    avg_f = sum(fills) / n

    return {
        "count":            n,
        "avg_slippage_bps": round(avg_s,      4),
        "p50_slippage_bps": _p(slips, 0.50),
        "p95_slippage_bps": _p(slips, 0.95),
        "avg_fill_rate":    round(avg_f,       4),
        "avg_latency_ms":   round(sum(lats)/n, 2),
        "rejection_rate":   round(rej_n / n,   4),
        "reality_gap_bps":  round(avg_s * (2.0 - avg_f), 4),
    }
