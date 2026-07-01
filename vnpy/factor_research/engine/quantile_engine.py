"""
factor_research/engine/quantile_engine.py

QuantileEngine -- Quantile Return Engine.

Long-Short implementation:
  Single asset: each bar belongs to exactly one quantile bucket,
  so pivot rows have only one non-NaN per row -- subtracting two
  columns would always yield NaN.

  Correct approach: build a L-S return series directly from aligned:
    bar in Q_last  -> +fwd_ret  (long contribution)
    bar in Q_first -> -fwd_ret  (short contribution)
  Concatenate into one time-series, then cumprod for NAV.
"""

from __future__ import annotations

import math

import numpy as np
import pandas as pd

from ..model import QuantileResult


class QuantileEngine:
    """Quantile return calculation engine."""

    TRADING_DAYS = 252

    def __init__(self) -> None:
        pass

    def compute(
        self,
        df: pd.DataFrame,
        vt_symbol: str,
        factor_name: str = "momentum_20",
        momentum_window: int = 20,
        lag: int = 5,
        n_quantiles: int = 5,
        rank_window: int = 252,
    ) -> QuantileResult:
        """Compute quantile returns for a single-asset OHLCV DataFrame."""

        def _empty() -> QuantileResult:
            return QuantileResult(
                vt_symbol=vt_symbol, factor_name=factor_name,
                lag=lag, n_quantiles=n_quantiles,
            )

        if df is None or df.empty or "close" not in df.columns:
            return _empty()

        close = df["close"].copy()
        factor  = close.pct_change(momentum_window)
        fwd_ret = close.pct_change(lag).shift(-lag)

        combined = pd.concat(
            [factor.rename("factor"), fwd_ret.rename("fwd")], axis=1
        ).dropna()

        if len(combined) < n_quantiles * 10:
            return _empty()

        # Rolling percentile rank -> quantile label
        effective_window = min(rank_window, len(combined))
        pct_ranks = (
            combined["factor"]
            .rolling(effective_window, min_periods=n_quantiles * 2)
            .rank(pct=True)
        )

        bins = np.linspace(0.0, 1.0, n_quantiles + 1)
        bins[0] -= 1e-9
        q_labels = [f"Q{i}" for i in range(1, n_quantiles + 1)]

        q_series = pd.cut(pct_ranks.dropna(), bins=bins, labels=q_labels)

        aligned = pd.concat(
            [q_series.rename("q"), combined["fwd"]], axis=1
        ).dropna()

        n = len(aligned)
        if n < n_quantiles * 5:
            return _empty()

        ann_factor = self.TRADING_DAYS / lag

        # Per-quantile stats (each bucket has its own irregular time index)
        quantile_ret_dict: dict[str, pd.Series] = {}
        cum_ret_dict:      dict[str, pd.Series] = {}
        ann_ret_dict:      dict[str, float]     = {}

        for ql in q_labels:
            mask = aligned["q"] == ql
            col  = aligned.loc[mask, "fwd"].sort_index()
            if col.empty:
                quantile_ret_dict[ql] = pd.Series(dtype=float)
                cum_ret_dict[ql]      = pd.Series(dtype=float)
                ann_ret_dict[ql]      = float("nan")
                continue

            cum       = (1 + col).cumprod() - 1
            total_ret = float((1 + col).prod() - 1)
            periods   = len(col)
            ann = (
                (1 + total_ret) ** (ann_factor / periods) - 1
                if periods > 0 else float("nan")
            )
            quantile_ret_dict[ql] = col
            cum_ret_dict[ql]      = cum
            ann_ret_dict[ql]      = ann

        # Long-Short return series
        # Each bar is in exactly one bucket, so we cannot subtract two
        # columns of a pivot directly (every row has only one non-NaN).
        # Instead, assign +fwd to Q_last bars and -fwd to Q_first bars,
        # producing a single continuous return series.
        q_first, q_last = q_labels[0], q_labels[-1]
        ls_series: pd.Series | None = None
        ls_ann = float("nan")

        long_mask  = aligned["q"] == q_last
        short_mask = aligned["q"] == q_first

        ls_parts = pd.concat([
            aligned.loc[long_mask,  "fwd"],
            -aligned.loc[short_mask, "fwd"],
        ]).sort_index()
        ls_ret = ls_parts.dropna()

        if not ls_ret.empty:
            ls_series  = (1 + ls_ret).cumprod() - 1
            total_ls   = float((1 + ls_ret).prod() - 1)
            periods_ls = len(ls_ret)
            if periods_ls > 0:
                ls_ann = (1 + total_ls) ** (ann_factor / periods_ls) - 1

        mono_score = self._monotonicity_score(q_labels, ann_ret_dict)

        return QuantileResult(
            vt_symbol=vt_symbol,
            factor_name=factor_name,
            lag=lag,
            n_quantiles=n_quantiles,
            quantile_labels=q_labels,
            quantile_returns=quantile_ret_dict,
            cumulative_returns=cum_ret_dict,
            long_short_series=ls_series,
            annualized_returns=ann_ret_dict,
            monotonicity_score=mono_score,
            long_short_annualized=ls_ann,
            sample_size=n,
        )

    @staticmethod
    def _monotonicity_score(
        q_labels: list[str],
        ann_ret_dict: dict[str, float],
    ) -> float:
        from scipy.stats import spearmanr
        rets  = [ann_ret_dict.get(ql, float("nan")) for ql in q_labels]
        valid = [(i + 1, r) for i, r in enumerate(rets) if not math.isnan(r)]
        if len(valid) < 3:
            return float("nan")
        corr, _ = spearmanr([v[0] for v in valid], [v[1] for v in valid])
        return float(corr)
