"""
market_reality_ai/utils/failure_utils.py

Phase 5: Failure Mode Analysis math core.

Seven failure mode types:
  execution_breakdown  latency > 5000ms → orders rejected → capital frozen
  liquidity_crisis     spread > 200bps  → no fills → strategy dies
  risk_overflow        drawdown > limit → forced liquidation → spiral
  strategy_failure     signal degradation → adverse selection → losses
  model_breakdown      regime change → stale parameters → wrong signals
  cascade_failure      one failure triggers others → systemic collapse
  system_overload      CPU/mem/IO → engine stops → all orders missed

Severity levels (1–5):
  LOW=1 / MEDIUM=2 / HIGH=3 / CRITICAL=4 / FATAL=5

Cascade risk model:
  cascade_risk = G(active_failures) × severity_weight × connectivity
  G(n) = 1 - exp(-lambda * n)  (Poisson cascade spread)

Fatal combinations (any two together → system death):
  risk_overflow + execution_breakdown
  risk_overflow + liquidity_crisis
  cascade_failure + any CRITICAL/FATAL
  system_overload + execution_breakdown + risk_overflow
"""
from __future__ import annotations
import math
import uuid
from datetime import datetime


def new_failure_id() -> str:
    return f"FAIL_{uuid.uuid4().hex[:8].upper()}"


def new_event_id() -> str:
    return f"EVT_{uuid.uuid4().hex[:8].upper()}"


# ── Severity scoring ──────────────────────────────────────────────────

def severity_from_score(score: float) -> "FailureSeverity":
    """Map 0–100 severity score to FailureSeverity enum."""
    from ..constant import FailureSeverity
    if score >= 90: return FailureSeverity.FATAL
    if score >= 70: return FailureSeverity.CRITICAL
    if score >= 50: return FailureSeverity.HIGH
    if score >= 25: return FailureSeverity.MEDIUM
    return FailureSeverity.LOW


def severity_score(
    mode_type:      str,
    trigger_value:  float,
    threshold:      float,
    regime:         str = "normal",
) -> float:
    """
    Compute severity score 0–100 for a failure mode given trigger_value
    vs threshold. Regime amplifies severity.

    score = 100 * clip((trigger_value / threshold - 1) * 5, 0, 1)
    regime_mult: normal=1.0  stressed=1.5  illiquid=2.0  crisis=3.0
    """
    if threshold <= 0:
        return 0.0
    excess = max(0.0, trigger_value / threshold - 1.0)
    base   = min(1.0, excess * 5.0)
    rmult  = {"normal": 1.0, "stressed": 1.5,
               "illiquid": 2.0, "crisis": 3.0}.get(regime, 1.0)
    return round(min(100.0, base * 100.0 * rmult), 2)


def severity_weight(severity_value: int) -> float:
    """Numeric weight for cascade risk calculation: LOW=0.1 … FATAL=1.0"""
    return {1: 0.1, 2: 0.25, 3: 0.50, 4: 0.80, 5: 1.0}.get(
        severity_value, 0.1)


# ── Failure detection helpers ─────────────────────────────────────────

FAILURE_THRESHOLDS = {
    "execution_breakdown": {
        "latency_ms":       5000.0,
        "rejection_rate":   0.50,
        "fill_rate":        0.20,
    },
    "liquidity_crisis": {
        "spread_bps":       200.0,
        "market_depth":     0.05,
        "adv_fraction":     0.01,
    },
    "risk_overflow": {
        "drawdown":         0.20,
        "var_breach":       1.0,    # 1.0 = VaR limit hit
        "leverage":         5.0,
    },
    "strategy_failure": {
        "signal_quality":   0.20,   # < 20% accuracy
        "adverse_pct":      0.60,   # 60%+ of trades adverse
        "return_z_score":  -3.0,    # 3-sigma below expectation
    },
    "model_breakdown": {
        "prediction_error": 0.30,
        "regime_lag":       5,      # bars since regime detected
        "param_staleness":  30,     # days since last calibration
    },
    "cascade_failure": {
        "active_count":     3,      # 3+ active failures → cascade
        "cascade_risk":     0.70,
    },
    "system_overload": {
        "cpu_pct":          90.0,
        "mem_pct":          85.0,
        "queue_depth":      10000,
    },
}


def check_execution_breakdown(
    latency_ms:      float = 0.0,
    rejection_rate:  float = 0.0,
    fill_rate:       float = 1.0,
    regime:          str   = "normal",
) -> dict:
    """Returns {detected: bool, score: float, trigger: str, value: float}"""
    th = FAILURE_THRESHOLDS["execution_breakdown"]
    candidates = [
        ("latency_ms",     latency_ms,       th["latency_ms"],     regime),
        ("rejection_rate", rejection_rate,    th["rejection_rate"], regime),
        ("fill_rate",      1.0 - fill_rate,  1.0 - th["fill_rate"], regime),
    ]
    best_score = 0.0; best_trigger = ""; best_val = 0.0
    for name, val, threshold, reg in candidates:
        sc = severity_score("execution_breakdown", val, threshold, reg)
        if sc > best_score:
            best_score = sc; best_trigger = name; best_val = val
    return {
        "detected": best_score > 0.0,
        "score":    best_score,
        "trigger":  best_trigger,
        "value":    best_val,
    }


def check_liquidity_crisis(
    spread_bps:   float = 5.0,
    market_depth: float = 1.0,
    regime:       str   = "normal",
) -> dict:
    th = FAILURE_THRESHOLDS["liquidity_crisis"]
    candidates = [
        ("spread_bps",   spread_bps,       th["spread_bps"],   regime),
        ("market_depth", 1.0 - market_depth, 1.0 - th["market_depth"], regime),
    ]
    best_score = 0.0; best_trigger = ""; best_val = 0.0
    for name, val, threshold, reg in candidates:
        sc = severity_score("liquidity_crisis", val, threshold, reg)
        if sc > best_score:
            best_score = sc; best_trigger = name; best_val = val
    return {"detected": best_score > 0.0, "score": best_score,
            "trigger": best_trigger, "value": best_val}


def check_risk_overflow(
    drawdown:  float = 0.0,
    leverage:  float = 1.0,
    regime:    str   = "normal",
) -> dict:
    th = FAILURE_THRESHOLDS["risk_overflow"]
    candidates = [
        ("drawdown", drawdown, th["drawdown"], regime),
        ("leverage", leverage, th["leverage"], regime),
    ]
    best_score = 0.0; best_trigger = ""; best_val = 0.0
    for name, val, threshold, reg in candidates:
        sc = severity_score("risk_overflow", val, threshold, reg)
        if sc > best_score:
            best_score = sc; best_trigger = name; best_val = val
    return {"detected": best_score > 0.0, "score": best_score,
            "trigger": best_trigger, "value": best_val}


# ── Cascade risk model ────────────────────────────────────────────────

def cascade_risk_score(
    active_failure_types: list[str],
    max_severity:         int,
    connectivity:         float = 0.5,
    lambda_param:         float = 0.8,
) -> float:
    """
    Cascade risk P(cascade) ∈ [0, 1].

    Model: G(n) = 1 - exp(-lambda * n) × severity_weight × connectivity
      n           = number of active distinct failure types
      lambda_param= cascade spread rate
      connectivity= system interdependency ∈ [0, 1]

    Higher connectivity = more tightly coupled = cascade spreads faster.
    """
    n = len(set(active_failure_types))
    if n == 0:
        return 0.0
    g_n      = 1.0 - math.exp(-lambda_param * n)
    sev_w    = severity_weight(max_severity)
    risk     = g_n * sev_w * connectivity
    return round(min(1.0, risk), 4)


def cascade_depth(
    active_failures:  list[str],
    cascade_risk:     float,
) -> int:
    """
    Estimated cascade depth (how many additional failures will be triggered).
    depth = floor(cascade_risk * len(active_failures) * 1.5)
    """
    if cascade_risk < 0.3 or not active_failures:
        return 0
    depth = int(cascade_risk * len(active_failures) * 1.5)
    return min(depth, 10)


# ── Fatal combination detection ───────────────────────────────────────

_FATAL_PAIRS: list[frozenset] = [
    frozenset({"risk_overflow",     "execution_breakdown"}),
    frozenset({"risk_overflow",     "liquidity_crisis"}),
    frozenset({"cascade_failure",   "risk_overflow"}),
    frozenset({"cascade_failure",   "execution_breakdown"}),
    frozenset({"system_overload",   "execution_breakdown"}),
    frozenset({"liquidity_crisis",  "execution_breakdown"}),
]

_FATAL_TRIPLES: list[frozenset] = [
    frozenset({"system_overload", "execution_breakdown", "risk_overflow"}),
    frozenset({"risk_overflow", "liquidity_crisis", "strategy_failure"}),
]


def is_fatal_combination(failure_types: list[str]) -> bool:
    """
    True if the active set of failure types contains a known fatal combination.
    Any two-member pair OR three-member triple from the fatal lists → True.
    """
    active = set(failure_types)
    for pair in _FATAL_PAIRS:
        if pair.issubset(active):
            return True
    for triple in _FATAL_TRIPLES:
        if triple.issubset(active):
            return True
    return False


def fatal_combination_names(failure_types: list[str]) -> list[str]:
    """Return descriptions of all triggered fatal combinations."""
    active  = set(failure_types)
    results = []
    for pair in _FATAL_PAIRS:
        if pair.issubset(active):
            results.append("+".join(sorted(pair)))
    for triple in _FATAL_TRIPLES:
        if triple.issubset(active):
            results.append("+".join(sorted(triple)))
    return results


# ── Failure scoring ───────────────────────────────────────────────────

def system_failure_score(
    active_failures:    list[dict],
    cascade_risk_val:   float,
    is_fatal:           bool,
) -> float:
    """
    System failure score 0–100. Higher = more dangerous.

    0 = no failures
    50 = multiple HIGH failures
    80+ = CRITICAL combination
    100 = fatal combination detected

    Formula:
      base = 20 * n_active + 30 * max_severity_weight
      cascade_boost = cascade_risk * 30
      fatal_boost = 100 if is_fatal else 0
    """
    if not active_failures:
        return 0.0
    n         = len(active_failures)
    max_sev   = max(f.get("severity", 1) for f in active_failures)
    base      = min(50.0, n * 10.0) + severity_weight(max_sev) * 30.0
    c_boost   = cascade_risk_val * 30.0
    f_boost   = 100.0 if is_fatal else 0.0
    return round(min(100.0, base + c_boost + f_boost), 2)


# ── Report helpers ────────────────────────────────────────────────────

def format_failure_summary(active_failures: list[dict]) -> str:
    """Human-readable summary of active failures."""
    if not active_failures:
        return "No active failure modes detected."
    lines = [f"Active failures ({len(active_failures)}):"]
    for f in active_failures:
        sev  = f.get("severity", 1)
        typ  = f.get("mode_type", "unknown")
        trig = f.get("trigger",  "unknown")
        lines.append(f"  [{sev}] {typ}: trigger={trig}")
    return "\n".join(lines)


def failure_report(
    active_failures:  list[dict],
    cascade_risk_val: float,
    cascade_depth_val:int,
    is_fatal:         bool,
    system_score:     float,
) -> dict:
    """Generate structured failure analysis report."""
    from ..constant import FailureSeverity
    max_sev = max(
        (f.get("severity", 1) for f in active_failures), default=1)
    return {
        "failure_count":   len(active_failures),
        "active_types":    [f.get("mode_type", "") for f in active_failures],
        "max_severity":    max_sev,
        "max_severity_name": FailureSeverity(max_sev).name,
        "cascade_risk":    cascade_risk_val,
        "cascade_depth":   cascade_depth_val,
        "cascade_active":  cascade_depth_val > 0,
        "is_fatal":        is_fatal,
        "fatal_combos":    fatal_combination_names(
            [f.get("mode_type","") for f in active_failures]),
        "system_score":    system_score,
        "summary":         format_failure_summary(active_failures),
        "phase":           5,
    }
