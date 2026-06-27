"""
FactorEngine

Multi-factor cross-sectional research engine.

Workflow:
  1. Register FactorTemplate instances
  2. calculate(results) -> DataFrame  (one row/symbol, one col/factor)
  3. cross_section_ic() / rank_ic()   -> IC / RankIC Series
  4. layer_analysis()                 -> quantile-bucket return table
  5. correlation_matrix()             -> factor collinearity matrix
  6. report()                         -> printable summary

The engine is decoupled from BatchBacktestingEngine: it receives
list[BacktestResult] and an optional bars_map dict.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from .factor_template import FactorTemplate
from ..utils.logger import get_logger

if TYPE_CHECKING:
    import pandas as pd
    from ..task import BacktestResult

logger = get_logger()


class FactorEngine:
    """Multi-factor cross-sectional research engine."""

    def __init__(self) -> None:
        self._factors: dict[str, FactorTemplate] = {}

    # ------------------------------------------------------------------ #
    #  Registration
    # ------------------------------------------------------------------ #

    def register(self, factor: FactorTemplate) -> None:
        """Register a factor. Overwrites if factor_name already exists."""
        if not factor.factor_name:
            raise ValueError(
                f"Factor {factor.__class__.__name__} has empty factor_name"
            )
        self._factors[factor.factor_name] = factor
        logger.debug("FactorEngine: registered %r", factor.factor_name)

    def register_factor(self, factor: FactorTemplate) -> None:
        """Alias for register()."""
        self.register(factor)

    def unregister(self, factor_name: str) -> None:
        """Remove a registered factor by name."""
        self._factors.pop(factor_name, None)

    @property
    def factor_names(self) -> list[str]:
        return list(self._factors.keys())

    def __len__(self) -> int:
        return len(self._factors)

    def __repr__(self) -> str:
        return f"FactorEngine(factors={self.factor_names})"

    # ------------------------------------------------------------------ #
    #  Calculation
    # ------------------------------------------------------------------ #

    def calculate(
        self,
        results: list["BacktestResult"],
        bars_map: dict | None = None,
        enrich: bool = True,
    ) -> "pd.DataFrame":
        """
        Compute all registered factors and return a merged DataFrame.

        Columns:
          metadata  : status, total_return, annual_return, sharpe_ratio,
                      max_ddpercent, total_trade_count
          factors   : one column per registered factor

        Index = vt_symbol.

        :param results:  list[BacktestResult] from BatchBacktestingEngine.
        :param bars_map: vt_symbol -> list[BarData], required by BarFactors.
        :param enrich:   Run StatisticsAnalyzer.enrich() first (adds calmar etc.)
        :raises RuntimeError: If no factors are registered.
        """
        import pandas as pd  # noqa: PLC0415

        if not self._factors:
            raise RuntimeError(
                "No factors registered. Call register() before calculate()."
            )

        if enrich:
            try:
                from ..statistics.analyzer import StatisticsAnalyzer  # noqa
                StatisticsAnalyzer().enrich(results)
            except Exception:
                pass

        kwargs: dict = {"bars_map": bars_map or {}}

        factor_series: dict[str, "pd.Series"] = {}
        for name, factor in self._factors.items():
            try:
                series = factor.calculate(results, **kwargs)
                factor_series[name] = series
                logger.debug("FactorEngine: %r  n=%d", name, series.notna().sum())
            except Exception as e:
                logger.warning("FactorEngine: factor %r failed: %s", name, e)
                factor_series[name] = pd.Series(dtype=float, name=name)

        factor_df = pd.DataFrame(factor_series)

        meta_rows = [
            {
                "vt_symbol":         r.vt_symbol,
                "status":            r.status.value,
                "total_return":      r.total_return,
                "annual_return":     r.annual_return,
                "sharpe_ratio":      r.sharpe_ratio,
                "max_ddpercent":     r.max_ddpercent,
                "total_trade_count": r.total_trade_count,
            }
            for r in results
        ]
        meta_df = pd.DataFrame(meta_rows).set_index("vt_symbol")
        # Drop factor cols that duplicate metadata col names to avoid
        # pandas 'columns overlap but no suffix specified' ValueError.
        # Metadata values (from BacktestResult directly) take precedence.
        overlap = [c for c in factor_df.columns if c in meta_df.columns]
        if overlap:
            factor_df = factor_df.drop(columns=overlap)
        result_df = meta_df.join(factor_df, how="left")

        logger.info(
            "FactorEngine.calculate(): %d symbols x %d factors",
            len(result_df), len(self._factors),
        )
        return result_df

    # ------------------------------------------------------------------ #
    #  IC / RankIC
    # ------------------------------------------------------------------ #

    def cross_section_ic(
        self,
        factor_df: "pd.DataFrame",
        return_col: str = "total_return",
        method: str = "spearman",
    ) -> "pd.Series":
        """
        Compute IC (Pearson) or RankIC (Spearman) vs a return column.

        :param factor_df:  DataFrame from calculate(), index=vt_symbol.
        :param return_col: Column containing forward returns.
        :param method:     'pearson' or 'spearman'.
        :return:           pd.Series(IC values, index=factor_names).
        """
        import pandas as pd  # noqa: PLC0415

        if return_col not in factor_df.columns:
            raise ValueError(
                f"return_col={return_col!r} not in factor_df. "
                f"Available: {list(factor_df.columns)}"
            )

        factor_cols = [c for c in self.factor_names if c in factor_df.columns]
        if not factor_cols:
            return pd.Series(dtype=float)

        returns = factor_df[return_col]
        ic_vals: dict[str, float] = {}

        for col in factor_cols:
            valid = pd.concat([factor_df[col], returns], axis=1).dropna()
            if len(valid) < 3:
                ic_vals[col] = float("nan")
                continue
            ic_vals[col] = valid.iloc[:, 0].corr(valid.iloc[:, 1], method=method)

        return pd.Series(ic_vals, name=f"IC_{method}")

    def rank_ic(
        self,
        factor_df: "pd.DataFrame",
        return_col: str = "total_return",
    ) -> "pd.Series":
        """Shorthand: Spearman rank IC."""
        return self.cross_section_ic(factor_df, return_col, method="spearman")

    # ------------------------------------------------------------------ #
    #  Layer (quantile) analysis
    # ------------------------------------------------------------------ #

    def layer_analysis(
        self,
        factor_df: "pd.DataFrame",
        return_col: str = "total_return",
        n_layers: int = 5,
        factor_col: str | None = None,
    ) -> "pd.DataFrame":
        """
        Divide symbols into N quantile layers by factor value;
        return average/median/std return per layer.

        Layer 1 = lowest factor values; Layer N = highest.

        :param factor_df:  DataFrame from calculate().
        :param return_col: Return column to aggregate within each layer.
        :param n_layers:   Number of quantile buckets (default 5 = quintiles).
        :param factor_col: Factor column to rank by. None -> first registered.
        :return:           DataFrame indexed by layer (1..N) with columns:
                           factor_col, count, mean_return, median_return, std_return, symbols.
        """
        import pandas as pd  # noqa: PLC0415

        if factor_col is None:
            candidates = [c for c in self.factor_names if c in factor_df.columns]
            if not candidates:
                raise ValueError("No factor columns found in factor_df")
            factor_col = candidates[0]

        for col in (factor_col, return_col):
            if col not in factor_df.columns:
                raise ValueError(f"{col!r} not in factor_df columns")

        df = factor_df[[factor_col, return_col]].dropna().copy()
        if len(df) < n_layers:
            raise ValueError(
                f"Not enough valid rows ({len(df)}) for {n_layers} layers"
            )

        df["_layer"] = pd.qcut(df[factor_col], q=n_layers,
                               labels=False, duplicates="drop")
        rows: list[dict] = []
        for lid in sorted(df["_layer"].dropna().unique()):
            grp = df[df["_layer"] == lid]
            rows.append({
                "layer":         int(lid) + 1,
                "factor_col":    factor_col,
                "count":         len(grp),
                "mean_return":   round(grp[return_col].mean(), 4),
                "median_return": round(grp[return_col].median(), 4),
                "std_return":    round(grp[return_col].std(), 4),
                "symbols":       list(grp.index),
            })

        return pd.DataFrame(rows).set_index("layer")

    # ------------------------------------------------------------------ #
    #  Correlation matrix
    # ------------------------------------------------------------------ #

    def correlation_matrix(
        self,
        factor_df: "pd.DataFrame",
        method: str = "spearman",
    ) -> "pd.DataFrame":
        """
        Pairwise correlation matrix between all registered factor columns.

        :param factor_df: DataFrame from calculate().
        :param method:    'pearson' or 'spearman'.
        :return:          Square correlation DataFrame.
        """
        import pandas as pd  # noqa: PLC0415

        factor_cols = [c for c in self.factor_names if c in factor_df.columns]
        if not factor_cols:
            return pd.DataFrame()
        return factor_df[factor_cols].corr(method=method)

    # ------------------------------------------------------------------ #
    #  Report
    # ------------------------------------------------------------------ #

    def report(
        self,
        factor_df: "pd.DataFrame",
        return_col: str = "total_return",
        n_layers: int = 5,
        show_corr: bool = True,
    ) -> None:
        """
        Print a comprehensive factor analysis report to stdout.

        Sections:
          1. Factor coverage
          2. IC / RankIC table
          3. Layer analysis for the highest-|RankIC| factor
          4. Factor correlation matrix (optional)
        """
        factor_cols = [c for c in self.factor_names if c in factor_df.columns]
        n_symbols = len(factor_df)

        print("=" * 65)
        print("Factor Analysis Report")
        print("=" * 65)
        print(f"  Symbols  : {n_symbols}")
        print(f"  Factors  : {len(factor_cols)}")
        print(f"  Return   : {return_col}")
        print()

        # Coverage
        print("  Factor Coverage:")
        print(f"  {'Factor':<32} {'N':>5}  {'Cov%':>7}")
        print("  " + "-" * 48)
        for col in factor_cols:
            cnt = int(factor_df[col].notna().sum())
            pct = cnt / max(n_symbols, 1) * 100
            print(f"  {col:<32} {cnt:>5}  {pct:>6.1f}%")
        print()

        # IC / RankIC
        try:
            pearson = self.cross_section_ic(factor_df, return_col, "pearson")
            spearman = self.cross_section_ic(factor_df, return_col, "spearman")
            print(f"  IC / RankIC  vs  {return_col}")
            print(f"  {'Factor':<32} {'Pearson IC':>12} {'Spearman IC':>12}")
            print("  " + "-" * 58)
            for col in factor_cols:
                p = pearson.get(col, float("nan"))
                s = spearman.get(col, float("nan"))
                print(f"  {col:<32} {p:>12.4f} {s:>12.4f}")
            print()
        except Exception as e:
            print(f"  IC analysis failed: {e}\n")

        # Layer analysis
        try:
            spearman = self.cross_section_ic(factor_df, return_col, "spearman")
            best = spearman.abs().idxmax()
            layer_df = self.layer_analysis(
                factor_df, return_col=return_col,
                n_layers=n_layers, factor_col=best,
            )
            print(f"  Layer Analysis  factor={best!r}  n={n_layers}")
            print(f"  {'Layer':>6} {'Count':>6} {'Mean%':>9} "
                  f"{'Median%':>9} {'Std%':>7}")
            print("  " + "-" * 45)
            for lid, row in layer_df.iterrows():
                print(
                    f"  {lid:>6} "
                    f"{int(row['count']):>6} "
                    f"{row['mean_return']:>9.2f} "
                    f"{row['median_return']:>9.2f} "
                    f"{row['std_return']:>7.2f}"
                )
            print()
        except Exception as e:
            print(f"  Layer analysis failed: {e}\n")

        # Correlation
        if show_corr and len(factor_cols) > 1:
            try:
                corr = self.correlation_matrix(factor_df, method="spearman")
                print("  Factor Correlation (Spearman):")
                corr_str = corr.round(3).to_string()
                for line in corr_str.split("\n"):
                    print(f"  {line}")
                print()
            except Exception as e:
                print(f"  Correlation failed: {e}\n")

        print("=" * 65)
