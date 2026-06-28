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

    def ic_ir(
        self,
        ic_series: "pd.Series",
    ) -> float:
        """
        ICIR = mean(IC) / std(IC).

        Measures the stability of a factor's predictive power over time.
        Requires a time-series of IC values (one per period / cross-section).

        :param ic_series: pd.Series of IC values indexed by date/period.
        :return:          ICIR float; nan if fewer than 2 valid values.
        """
        import pandas as pd  # noqa: PLC0415
        valid = ic_series.dropna()
        if len(valid) < 2:
            return float("nan")
        std = float(valid.std())
        if std == 0:
            return float("nan")
        return round(float(valid.mean()) / std, 4)


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


# ------------------------------------------------------------------ #
#  CompositeScorer
# ------------------------------------------------------------------ #

class CompositeScorer:
    """
    把多个因子值加权求和，得出每只股票的综合评分。

    权重字典 key = factor_name，value = 权重（未归一化）。
    权重在计算前会归一化为 sum=1.0。

    用法::

        scorer = CompositeScorer({'sharpe_ratio': 0.4, 'calmar_ratio': 0.6})
        scores = scorer.score(factor_df)  # pd.Series, index=vt_symbol
    """

    def __init__(self, weights: dict[str, float] | None = None) -> None:
        self._weights: dict[str, float] = weights or {}

    def score(
        self,
        factor_df: 'pd.DataFrame',
    ) -> 'pd.Series':
        """
        加权求和（各因子先做 rank 归一化到 [0,1]，再加权求和）。

        rank 归一化：避免不同量纲因子值之间的数值差异。
        """
        import pandas as pd

        weights = self._weights
        cols = [c for c in weights if c in factor_df.columns]
        if not cols:
            return pd.Series(dtype=float, name='composite_score')

        total_w = sum(abs(weights[c]) for c in cols)
        if total_w == 0:
            return pd.Series(dtype=float, name='composite_score')

        ranked = factor_df[cols].rank(pct=True, ascending=True)
        scored = sum(
            ranked[c] * (weights[c] / total_w)
            for c in cols
        )
        scored.name = 'composite_score'
        return scored


# ------------------------------------------------------------------ #
#  ICCalculator
# ------------------------------------------------------------------ #

class ICCalculator:
    """
    IC / RankIC 计算器。

    IC（信息系数）衡量因子预测能力：因子值与未来收益的相关性。
    当前实现：用回测结果区间内的 total_return 作为近似未来收益。
    后续：接入真实的 forward_returns 数据替换实现。
    """

    @staticmethod
    def calc_ic(
        factor_values: dict[str, float],
        forward_returns: dict[str, float],
        method: str = 'pearson',
    ) -> float:
        """Pearson IC = corr(factor_values, forward_returns)"""
        import pandas as pd
        s1 = pd.Series(factor_values)
        s2 = pd.Series(forward_returns)
        aligned = pd.concat([s1, s2], axis=1).dropna()
        if len(aligned) < 3:
            return float('nan')
        return float(aligned.iloc[:, 0].corr(aligned.iloc[:, 1], method=method))

    @staticmethod
    def calc_rank_ic(
        factor_values: dict[str, float],
        forward_returns: dict[str, float],
    ) -> float:
        """RankIC = Spearman corr(rank(factor), rank(forward_returns))"""
        return ICCalculator.calc_ic(factor_values, forward_returns, method='spearman')


# ------------------------------------------------------------------ #
#  IndustryNeutralizer
# ------------------------------------------------------------------ #

class IndustryNeutralizer:
    """
    行业中性化处理器。

    对每只股票的因子值，减去同行业均值，得到行业内相对值。
    需要 BatchBacktestResult.industry 字段非空。
    industry 为空的股票：直接使用原始值，不参与中性化。
    """

    @staticmethod
    def neutralize(
        results: list,
        factor_values: dict[str, float],
    ) -> dict[str, float]:
        """
        行业中性化。

        :param results:       BatchBacktestResult 列表（需要 .vt_symbol / .industry）
        :param factor_values: {vt_symbol: factor_value}
        :return:              行业中性化后的 {vt_symbol: neutralized_value}
        """
        from collections import defaultdict

        industry_map: dict[str, str] = {
            r.vt_symbol: getattr(r, 'industry', '')
            for r in results
        }

        industry_vals: dict[str, list[float]] = defaultdict(list)
        for sym, val in factor_values.items():
            ind = industry_map.get(sym, '')
            if ind:
                industry_vals[ind].append(val)

        industry_mean: dict[str, float] = {
            ind: sum(vals) / len(vals)
            for ind, vals in industry_vals.items()
            if vals
        }

        neutralized: dict[str, float] = {}
        for sym, val in factor_values.items():
            ind = industry_map.get(sym, '')
            mean = industry_mean.get(ind)
            neutralized[sym] = val - mean if mean is not None else val
        return neutralized


# ------------------------------------------------------------------ #
#  FactorEngine.run()  —  写回 BatchBacktestResult 扩展字段
# ------------------------------------------------------------------ #

def _bbr_factor_df(
    self: FactorEngine,
    results: list,
) -> 'pd.DataFrame':
    """
    从 BatchBacktestResult 列表直接读强类型字段构建因子 DataFrame。

    BatchBacktestResult 没有 .statistics，status 已是 str，
    不能走旧的 calculate() 路径，直接读字段。
    """
    import pandas as pd
    import math

    factor_data: dict[str, dict[str, float]] = {
        name: {} for name in self.factor_names
    }

    for r in results:
        sym = r.vt_symbol
        if getattr(r, 'status', '') not in ('success', 'SUCCESS'):
            continue
        for name in self.factor_names:
            try:
                raw = getattr(r, name, None)
                if raw is None:
                    continue
                val = float(raw)
                if not math.isnan(val) and not math.isinf(val):
                    factor_data[name][sym] = val
            except (TypeError, ValueError, AttributeError):
                pass

    return pd.DataFrame(factor_data)


def _factor_engine_run(
    self: FactorEngine,
    results: list,
    weights: dict[str, float] | None = None,
    bars_map: dict | None = None,
    selector_top_n: int | None = None,
) -> list:
    """
    对 BatchBacktestResult 列表执行完整因子分析，
    把结果写回每个对象的扩展字段：
      factor_scores   : {factor_name: value}
      composite_score : 加权综合评分
      factor_rank     : 按 composite_score 从高到低排名（1=最好）
      selected        : factor_rank <= selector_top_n 时为 True
    """
    if not results or not self._factors:
        return results

    import pandas as pd

    factor_df = _bbr_factor_df(self, results)

    if weights is None:
        weights = {name: 1.0 for name in self.factor_names}

    scorer = CompositeScorer(weights)
    scores = scorer.score(factor_df)

    ranked = scores.rank(ascending=False, method='min').astype(int)

    for r in results:
        sym = r.vt_symbol
        r.factor_scores = {
            name: float(factor_df.at[sym, name])
            for name in self.factor_names
            if sym in factor_df.index
            and name in factor_df.columns
            and pd.notna(factor_df.at[sym, name])
        }
        r.composite_score = float(scores[sym]) if sym in scores else None
        r.factor_rank     = int(ranked[sym])   if sym in ranked else None
        r.selected        = (
            r.factor_rank is not None
            and selector_top_n is not None
            and r.factor_rank <= selector_top_n
        )

    return results


FactorEngine.run = _factor_engine_run
