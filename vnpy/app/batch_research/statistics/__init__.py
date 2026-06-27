"""statistics sub-package: backtest result analysis."""

from .analyzer import StatisticsAnalyzer, ORDERED_COLUMNS
from .metrics import (
    calculate_avg_return,
    calculate_avg_sharpe,
    calculate_avg_max_drawdown,
    calculate_win_rate,
    calculate_profit_loss_ratio,
    calculate_calmar_ratio,
    calculate_sharpe_ratio,
    calculate_max_drawdown,
    enrich_statistics,
    build_aggregate_summary,
)

__all__ = [
    "StatisticsAnalyzer",
    "ORDERED_COLUMNS",
    "calculate_avg_return",
    "calculate_avg_sharpe",
    "calculate_avg_max_drawdown",
    "calculate_win_rate",
    "calculate_profit_loss_ratio",
    "calculate_calmar_ratio",
    "calculate_sharpe_ratio",
    "calculate_max_drawdown",
    "enrich_statistics",
    "build_aggregate_summary",
]
