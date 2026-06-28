"""statistics sub-package: backtest result analysis."""

from .analyzer import StatisticsAnalyzer, ORDERED_COLUMNS
from .metrics import (
    enrich_statistics,
    build_aggregate_summary,
    calc_annual_volatility,
    calc_win_rate,
    BasicMetrics,
    ReturnMetrics,
    RiskMetrics,
    TradeMetrics,
    CapitalMetrics,
)

__all__ = [
    "StatisticsAnalyzer",
    "ORDERED_COLUMNS",
    "enrich_statistics",
    "build_aggregate_summary",
    "calc_annual_volatility",
    "calc_win_rate",
    "BasicMetrics",
    "ReturnMetrics",
    "RiskMetrics",
    "TradeMetrics",
    "CapitalMetrics",
]
