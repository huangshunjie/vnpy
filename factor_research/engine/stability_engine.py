"""
factor_research/engine/stability_engine.py

StabilityEngine -- Factor stability analysis utilities.

Computes three stability views from an IcStats object:

  1. Monthly heatmap matrix
     rows = year, cols = month (1-12)
     values = mean IC for that year-month bucket
     Returns a DataFrame with year as index, month (1-12) as columns.

  2. Annual IC statistics
     Returns a DataFrame with one row per year containing:
     ic_mean, ic_std, icir, positive_rate, sample_size

  3. IC autocorrelation function (ACF)
     Returns a DataFrame with columns [lag, acf] for lag=1..max_lag.
     Uses numpy.correlate (no external stats library dependency).

All functions accept IcStats and return DataFrames.
Empty / invalid inputs return empty DataFrames.
No UI access, no database access.
"""

from __future__ import annotations

import math

import numpy as np
import pandas as pd

from ..model import IcStats


class StabilityEngine:
    """Factor stability analysis engine."""

    # ------------------------------------------------------------------ #
    #  Monthly IC heatmap
    # ------------------------------------------------------------------ #

    @staticmethod
    def monthly_ic_matrix(stats: IcStats) -> pd.DataFrame:
        """
        Build year × month IC mean matrix.

        Returns:
            DataFrame with year as index (int), month 1-12 as columns.
            Cell value = mean IC for that (year, month); NaN if no data.
        """
        ic = stats.ic_series if stats.ic_series is not None else None
        if ic is None or ic.dropna().empty:
            return pd.DataFrame()

        ic = ic.dropna()
        if not isinstance(ic.index, pd.DatetimeIndex):
            try:
                ic.index = pd.to_datetime(ic.index)
            except Exception:
                return pd.DataFrame()

        df = ic.to_frame(name="ic")
        df["year"]  = df.index.year
        df["month"] = df.index.month

        matrix = (
            df.groupby(["year", "month"])["ic"]
            .mean()
            .unstack("month")
            .reindex(columns=list(range(1, 13)))
        )
        matrix.index.name = "year"
        matrix.columns.name = "month"
        return matrix

    # ------------------------------------------------------------------ #
    #  Annual IC statistics
    # ------------------------------------------------------------------ #

    @staticmethod
    def annual_ic_stats(stats: IcStats) -> pd.DataFrame:
        """
        Compute per-year IC statistics.

        Returns:
            DataFrame columns: [year, ic_mean, ic_std, icir, positive_rate, sample_size]
        """
        ic = stats.ic_series if stats.ic_series is not None else None
        if ic is None or ic.dropna().empty:
            return pd.DataFrame()

        ic = ic.dropna()
        if not isinstance(ic.index, pd.DatetimeIndex):
            try:
                ic.index = pd.to_datetime(ic.index)
            except Exception:
                return pd.DataFrame()

        rows = []
        for year, group in ic.groupby(ic.index.year):
            g = group.dropna()
            if g.empty:
                continue
            mean = float(g.mean())
            std  = float(g.std()) if len(g) > 1 else float("nan")
            icir = mean / std if (not math.isnan(std) and std > 1e-12) else float("nan")
            pos  = float((g > 0).mean())
            rows.append({
                "年份":     int(year),
                "IC 均值":  round(mean, 6),
                "IC 标准差": round(std,  6) if not math.isnan(std) else None,
                "ICIR":    round(icir, 6) if not math.isnan(icir) else None,
                "IC 胜率":  round(pos,  4),
                "样本量":   len(g),
            })

        return pd.DataFrame(rows) if rows else pd.DataFrame()

    # ------------------------------------------------------------------ #
    #  IC autocorrelation
    # ------------------------------------------------------------------ #

    @staticmethod
    def ic_acf(stats: IcStats, max_lag: int = 20) -> pd.DataFrame:
        """
        Compute autocorrelation function of the IC series.

        Returns:
            DataFrame columns: [lag, acf]  lag=1..max_lag
        """
        ic = stats.ic_series if stats.ic_series is not None else None
        if ic is None or ic.dropna().empty:
            return pd.DataFrame()

        arr = ic.dropna().values.astype(float)
        n   = len(arr)
        if n < max_lag + 2:
            max_lag = max(1, n // 2)

        mean = arr.mean()
        demeaned = arr - mean
        var = float(np.dot(demeaned, demeaned))

        rows = []
        for k in range(1, max_lag + 1):
            cov = float(np.dot(demeaned[:-k], demeaned[k:]))
            acf_val = cov / var if var > 1e-15 else float("nan")
            rows.append({"滞后期": k, "ACF": round(acf_val, 6)})

        return pd.DataFrame(rows) if rows else pd.DataFrame()

    # ------------------------------------------------------------------ #
    #  Convenience: all three in one call
    # ------------------------------------------------------------------ #

    @staticmethod
    def compute_all(stats: IcStats, acf_max_lag: int = 20) -> dict:
        """Return dict with keys: heatmap, annual, acf."""
        return {
            "heatmap": StabilityEngine.monthly_ic_matrix(stats),
            "annual":  StabilityEngine.annual_ic_stats(stats),
            "acf":     StabilityEngine.ic_acf(stats, max_lag=acf_max_lag),
        }
