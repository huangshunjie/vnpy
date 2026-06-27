"""
Metrics

Pure-function library for computing backtest performance indicators.

All functions operate on either a list of BacktestResult objects
(cross-symbol aggregation) or the flat statistics dict produced by
BacktestingEngine.calculate_statistics() (per-symbol enrichment).

Functions are intentionally stateless and side-effect free so they
can be called from any context (analyzer, Jupyter, tests).
"""

from __future__ import annotations

import math
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..task import BacktestResult


# ------------------------------------------------------------------ #
#  Cross-symbol aggregate metrics (operate on list[BacktestResult])
# ------------------------------------------------------------------ #

def calculate_avg_return(results: list["BacktestResult"]) -> float:
    """Average total return (%) across successful results."""
    vals = [r.total_return for r in results if r.statistics]
    return sum(vals) / len(vals) if vals else 0.0


def calculate_avg_sharpe(results: list["BacktestResult"]) -> float:
    """Average Sharpe ratio across successful results."""
    vals = [r.sharpe_ratio for r in results if r.statistics]
    return sum(vals) / len(vals) if vals else 0.0


def calculate_avg_max_drawdown(results: list["BacktestResult"]) -> float:
    """Average max drawdown (%) across successful results (negative number)."""
    vals = [r.max_ddpercent for r in results if r.statistics]
    return sum(vals) / len(vals) if vals else 0.0


def calculate_win_rate(results: list["BacktestResult"]) -> float:
    """
    Symbol-level win rate: fraction of symbols with total_return > 0.

    :return: Value in [0.0, 100.0].
    """
    valid = [r for r in results if r.statistics]
    if not valid:
        return 0.0
    winners = sum(1 for r in valid if r.total_return > 0)
    return winners / len(valid) * 100.0


def calculate_profit_loss_ratio(results: list["BacktestResult"]) -> float:
    """
    Symbol-level profit/loss ratio:
        avg_return_of_winners / abs(avg_return_of_losers)

    Returns 0.0 if there are no losers.
    """
    valid = [r for r in results if r.statistics]
    winners = [r.total_return for r in valid if r.total_return > 0]
    losers  = [r.total_return for r in valid if r.total_return < 0]
    if not losers:
        return 0.0
    avg_win  = sum(winners) / len(winners) if winners else 0.0
    avg_loss = abs(sum(losers) / len(losers))
    return avg_win / avg_loss if avg_loss else 0.0


def calculate_calmar_ratio(results: list["BacktestResult"]) -> float:
    """
    Average Calmar ratio: annual_return / abs(max_ddpercent).
    Computed per symbol then averaged.

    Returns 0.0 if no valid results exist.
    """
    vals: list[float] = []
    for r in results:
        if not r.statistics:
            continue
        mdd = abs(r.max_ddpercent)
        ann = r.annual_return
        if mdd > 0:
            vals.append(ann / mdd)
    return sum(vals) / len(vals) if vals else 0.0


def calculate_sharpe_ratio(results: list["BacktestResult"]) -> float:
    """Alias for calculate_avg_sharpe (cross-symbol average)."""
    return calculate_avg_sharpe(results)


def calculate_max_drawdown(results: list["BacktestResult"]) -> float:
    """Alias for calculate_avg_max_drawdown."""
    return calculate_avg_max_drawdown(results)


# ------------------------------------------------------------------ #
#  Per-result enrichment (operates on a single statistics dict)
# ------------------------------------------------------------------ #

def enrich_statistics(stats: dict) -> dict:
    """
    Add derived metrics to a statistics dict produced by
    BacktestingEngine.calculate_statistics().

    Added keys:
      calmar_ratio   — annual_return / abs(max_ddpercent)
      profit_factor  — total_net_pnl / abs(total_commission + total_slippage)
                       (0.0 when costs are zero)

    Returns the same dict with new keys inserted in place.
    """
    annual_return = float(stats.get("annual_return", 0))
    max_ddpercent = float(stats.get("max_ddpercent", 0))
    total_net_pnl = float(stats.get("total_net_pnl", 0))
    total_commission = float(stats.get("total_commission", 0))
    total_slippage = float(stats.get("total_slippage", 0))

    # Calmar
    if max_ddpercent and not math.isnan(max_ddpercent):
        calmar = annual_return / abs(max_ddpercent)
    else:
        calmar = 0.0
    stats["calmar_ratio"] = round(calmar, 4) if not math.isnan(calmar) else 0.0

    # Profit factor (gross profit / gross cost)
    costs = abs(total_commission) + abs(total_slippage)
    if costs > 0:
        profit_factor = total_net_pnl / costs
    else:
        profit_factor = 0.0
    stats["profit_factor"] = (
        round(profit_factor, 4)
        if not math.isnan(profit_factor) and not math.isinf(profit_factor)
        else 0.0
    )

    return stats


# ------------------------------------------------------------------ #
#  Aggregate summary dict (for reporting)
# ------------------------------------------------------------------ #

def build_aggregate_summary(results: list["BacktestResult"]) -> dict:
    """
    Build a single-row summary dict for the entire batch run.

    Keys match BacktestResult.to_flat_dict() naming conventions
    where applicable, prefixed with 'agg_' to avoid collisions.
    """
    valid = [r for r in results if r.statistics]
    total = len(results)

    return {
        "agg_total_symbols":     total,
        "agg_success_symbols":   len(valid),
        "agg_failed_symbols":    sum(1 for r in results if not r.statistics and r.error_msg),
        "agg_skipped_symbols":   sum(1 for r in results if not r.statistics and not r.error_msg),
        "agg_avg_total_return":  round(calculate_avg_return(results), 4),
        "agg_avg_annual_return": round(
            sum(r.annual_return for r in valid) / len(valid) if valid else 0.0, 4
        ),
        "agg_avg_sharpe":        round(calculate_avg_sharpe(results), 4),
        "agg_avg_max_ddpercent": round(calculate_avg_max_drawdown(results), 4),
        "agg_avg_calmar":        round(calculate_calmar_ratio(results), 4),
        "agg_win_rate":          round(calculate_win_rate(results), 2),
        "agg_profit_loss_ratio": round(calculate_profit_loss_ratio(results), 4),
        "agg_total_trades":      sum(r.total_trade_count for r in valid),
        "agg_avg_trades":        round(
            sum(r.total_trade_count for r in valid) / len(valid) if valid else 0.0, 1
        ),
    }
