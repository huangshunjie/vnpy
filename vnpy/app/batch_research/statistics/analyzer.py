"""
StatisticsAnalyzer

Aggregates BacktestResult lists into structured summary tables.

Two levels of analysis:
  1. Per-symbol enrichment: adds calmar_ratio, profit_factor to each result's
     statistics dict (via metrics.enrich_statistics).
  2. Cross-symbol summary: builds aggregate metrics over the full batch
     (win rate, avg Sharpe, avg drawdown, etc.).

Usage::

    analyzer = StatisticsAnalyzer()
    enriched = analyzer.enrich(results)          # mutates result.statistics in-place
    summary  = analyzer.summarize(results)       # returns aggregate dict
    df       = analyzer.to_dataframe(results)    # returns pandas DataFrame
    top10    = analyzer.top_n(results, n=10, by="sharpe_ratio")
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from .metrics import (
    build_aggregate_summary,
    enrich_statistics,
)

if TYPE_CHECKING:
    import pandas as pd
    from ..task import BacktestResult


# Column order for DataFrame / CSV export (official keys first, then derived)
ORDERED_COLUMNS: list[str] = [
    # identity
    "vt_symbol",
    "strategy_name",
    "status",
    # time
    "start_date",
    "end_date",
    "total_days",
    "profit_days",
    "loss_days",
    # capital
    "capital",
    "end_balance",
    # return
    "total_return",
    "annual_return",
    "daily_return",
    "return_std",
    # drawdown
    "max_drawdown",
    "max_ddpercent",
    "max_drawdown_duration",
    # ratios
    "sharpe_ratio",
    "ewm_sharpe",
    "return_drawdown_ratio",
    "rgr_ratio",
    "calmar_ratio",       # derived
    "profit_factor",      # derived
    # trades
    "total_trade_count",
    "daily_trade_count",
    "total_net_pnl",
    "daily_net_pnl",
    # costs
    "total_commission",
    "daily_commission",
    "total_slippage",
    "daily_slippage",
    "total_turnover",
    "daily_turnover",
    # meta
    "task_id",
    "elapsed_seconds",
    "error_msg",
]


class StatisticsAnalyzer:
    """
    Batch backtest statistics analyzer.

    Enriches per-symbol results and computes cross-symbol aggregate metrics.
    Does NOT depend on pandas — to_dataframe() lazily imports it only when called.
    """

    # ------------------------------------------------------------------ #
    #  Per-symbol enrichment
    # ------------------------------------------------------------------ #

    def enrich(self, results: list["BacktestResult"]) -> list["BacktestResult"]:
        """
        Add derived metrics (calmar_ratio, profit_factor) to each successful
        result's statistics dict in-place.

        :param results: List of BacktestResult objects.
        :return:        Same list (mutated in-place) for chaining.
        """
        for r in results:
            if r.statistics:
                enrich_statistics(r.statistics)
        return results

    # ------------------------------------------------------------------ #
    #  Cross-symbol summary
    # ------------------------------------------------------------------ #

    def summarize(self, results: list["BacktestResult"]) -> dict:
        """
        Build a single aggregate summary dict over all results.

        Keys are prefixed 'agg_' and include:
          agg_total_symbols, agg_success_symbols, agg_failed_symbols,
          agg_skipped_symbols, agg_avg_total_return, agg_avg_annual_return,
          agg_avg_sharpe, agg_avg_max_ddpercent, agg_avg_calmar,
          agg_win_rate, agg_profit_loss_ratio,
          agg_total_trades, agg_avg_trades

        :param results: List of BacktestResult objects.
        :return:        Aggregate metrics dict.
        """
        return build_aggregate_summary(results)

    # ------------------------------------------------------------------ #
    #  Filtering and ranking helpers
    # ------------------------------------------------------------------ #

    def top_n(
        self,
        results: list["BacktestResult"],
        n: int = 10,
        by: str = "sharpe_ratio",
        ascending: bool = False,
    ) -> list["BacktestResult"]:
        """
        Return the top-N results sorted by a statistics field.

        :param results:   List of BacktestResult objects.
        :param n:         Number of results to return.
        :param by:        Statistics key to sort by (default 'sharpe_ratio').
        :param ascending: Sort direction (default descending = best first).
        :return:          Sorted sub-list of up to N results.
        """
        valid = [r for r in results if r.statistics]
        sorted_results = sorted(
            valid,
            key=lambda r: float(r.statistics.get(by, 0)),
            reverse=not ascending,
        )
        return sorted_results[:n]

    def filter_by_min_trades(
        self,
        results: list["BacktestResult"],
        min_trades: int = 10,
    ) -> list["BacktestResult"]:
        """
        Discard results with fewer than min_trades total trades.
        Useful for filtering out strategies that barely traded.
        """
        return [r for r in results if r.total_trade_count >= min_trades]

    def filter_by_min_sharpe(
        self,
        results: list["BacktestResult"],
        min_sharpe: float = 0.0,
    ) -> list["BacktestResult"]:
        """Return results with sharpe_ratio >= min_sharpe."""
        return [r for r in results if r.sharpe_ratio >= min_sharpe]

    def filter_by_max_drawdown(
        self,
        results: list["BacktestResult"],
        max_ddpercent: float = -20.0,
    ) -> list["BacktestResult"]:
        """
        Return results where max_ddpercent >= max_ddpercent threshold.
        E.g. max_ddpercent=-20.0 keeps symbols with drawdown no worse than -20%.
        """
        return [r for r in results if r.max_ddpercent >= max_ddpercent]

    # ------------------------------------------------------------------ #
    #  DataFrame output
    # ------------------------------------------------------------------ #

    def to_dataframe(
        self,
        results: list["BacktestResult"],
        enrich: bool = True,
        sort_by: str = "sharpe_ratio",
        ascending: bool = False,
    ) -> "pd.DataFrame":
        """
        Convert results to a pandas DataFrame.

        :param results:   List of BacktestResult objects.
        :param enrich:    Run enrich() before building DataFrame (default True).
        :param sort_by:   Column to sort by (default 'sharpe_ratio').
        :param ascending: Sort direction.
        :return:          pandas DataFrame with ORDERED_COLUMNS column order.
        """
        import pandas as pd  # noqa: PLC0415

        if not results:
            return pd.DataFrame(columns=ORDERED_COLUMNS)

        if enrich:
            self.enrich(results)

        rows = [r.to_flat_dict() for r in results]
        df = pd.DataFrame(rows)

        # Reorder columns: ORDERED_COLUMNS first, then any extras
        existing_ordered = [c for c in ORDERED_COLUMNS if c in df.columns]
        extras = [c for c in df.columns if c not in ORDERED_COLUMNS]
        df = df[existing_ordered + extras]

        if sort_by in df.columns:
            df = df.sort_values(sort_by, ascending=ascending).reset_index(drop=True)

        return df

    def print_summary(
        self,
        results: list["BacktestResult"],
        top_n: int = 10,
    ) -> None:
        """
        Print a human-readable summary to stdout.

        Shows: aggregate metrics table + top-N symbols by Sharpe ratio.
        """
        agg = self.summarize(results)

        print("=" * 60)
        print(f"Batch Backtest Summary")
        print("=" * 60)
        print(f"  Total symbols   : {agg['agg_total_symbols']}")
        print(f"  Success         : {agg['agg_success_symbols']}")
        print(f"  Skipped         : {agg['agg_skipped_symbols']}")
        print(f"  Failed          : {agg['agg_failed_symbols']}")
        print(f"  Win rate        : {agg['agg_win_rate']:.1f}%")
        print(f"  Avg return      : {agg['agg_avg_total_return']:.2f}%")
        print(f"  Avg annual ret  : {agg['agg_avg_annual_return']:.2f}%")
        print(f"  Avg Sharpe      : {agg['agg_avg_sharpe']:.2f}")
        print(f"  Avg max DD      : {agg['agg_avg_max_ddpercent']:.2f}%")
        print(f"  Avg Calmar      : {agg['agg_avg_calmar']:.2f}")
        print(f"  P/L ratio       : {agg['agg_profit_loss_ratio']:.2f}")
        print(f"  Total trades    : {agg['agg_total_trades']}")
        print(f"  Avg trades/sym  : {agg['agg_avg_trades']:.1f}")
        print()

        top = self.top_n(results, n=top_n, by="sharpe_ratio")
        if top:
            print(f"Top-{min(top_n, len(top))} by Sharpe ratio:")
            print(f"  {'Symbol':<16} {'Return%':>8} {'Annual%':>8} "
                  f"{'Sharpe':>8} {'MaxDD%':>8} {'Trades':>7}")
            print("  " + "-" * 62)
            for r in top:
                print(
                    f"  {r.vt_symbol:<16} "
                    f"{r.total_return:>8.2f} "
                    f"{r.annual_return:>8.2f} "
                    f"{r.sharpe_ratio:>8.2f} "
                    f"{r.max_ddpercent:>8.2f} "
                    f"{r.total_trade_count:>7d}"
                )
        print("=" * 60)
