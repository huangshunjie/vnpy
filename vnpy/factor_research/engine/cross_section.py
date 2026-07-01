"""
factor_research/engine/cross_section.py

CrossSection -- Cross-sectional averaging utilities.

Merges per-symbol computation results into a single cross-sectional mean
result, which is then broadcast to UI tabs exactly like a single-symbol
result. Tabs require zero changes.

Design:
  - Pure functions only; no IO, no Qt, no EventEngine.
  - All merge_* functions accept a list of per-symbol results and return
    one averaged result. Empty / invalid inputs are silently skipped.
  - NaN-safe: uses nanmean so that one bad symbol does not poison the pool.
  - For time-series merging (IC series, quantile cumulative curves) we
    align on a common date index and take row-wise nanmean.

Label convention:
  vt_symbol in merged results is set to
      "截面均值（N 合约）"   when N > 1
      original symbol        when N == 1  (pass-through, no copy)
"""

from __future__ import annotations

import math
from typing import TYPE_CHECKING

import numpy as np
import pandas as pd

from ..model import DecayPoint, DecayResult, IcStats, QuantileResult

if TYPE_CHECKING:
    pass


def _label(n: int, symbols: list[str]) -> str:
    if n == 1:
        return symbols[0] if symbols else "unknown"
    return f"截面均值（{n} 合约）"


# ------------------------------------------------------------------ #
#  IC cross-section merge
# ------------------------------------------------------------------ #

def merge_ic(results: list[IcStats]) -> IcStats | None:
    """
    Average a list of per-symbol IcStats into one cross-sectional IcStats.

    Scalar fields (ic_mean, icir, etc.) → nanmean.
    Time-series fields (ic_series, rank_ic_series) → align on union index,
    row-wise nanmean.

    Returns None if the input list is empty or all results are invalid.
    """
    valid = [r for r in results if r.is_valid()]
    if not valid:
        return None
    if len(valid) == 1:
        valid[0].n_symbols = 1
        return valid[0]

    n = len(valid)
    symbols = [r.vt_symbol for r in valid]

    def _nm(vals: list[float]) -> float:
        arr = [v for v in vals if not math.isnan(v)]
        return float(np.mean(arr)) if arr else float("nan")

    merged = IcStats(
        vt_symbol=_label(n, symbols),
        factor_name=valid[0].factor_name,
        lag=valid[0].lag,
        n_symbols=n,
        ic_mean=_nm([r.ic_mean for r in valid]),
        ic_std=_nm([r.ic_std for r in valid]),
        icir=_nm([r.icir for r in valid]),
        ic_positive_rate=_nm([r.ic_positive_rate for r in valid]),
        rank_ic_mean=_nm([r.rank_ic_mean for r in valid]),
        rank_ic_std=_nm([r.rank_ic_std for r in valid]),
        rank_icir=_nm([r.rank_icir for r in valid]),
        rank_ic_positive_rate=_nm([r.rank_ic_positive_rate for r in valid]),
        sample_size=int(np.mean([r.sample_size for r in valid])),
        ic_series_len=int(np.mean([r.ic_series_len for r in valid])),
    )

    # Time-series: align on union date index, then nanmean row-wise
    ic_srs  = [r.ic_series      for r in valid if r.ic_series      is not None]
    ric_srs = [r.rank_ic_series for r in valid if r.rank_ic_series is not None]

    if ic_srs:
        merged.ic_series = _align_nanmean(ic_srs)
    if ric_srs:
        merged.rank_ic_series = _align_nanmean(ric_srs)

    return merged


# ------------------------------------------------------------------ #
#  Decay cross-section merge
# ------------------------------------------------------------------ #

def merge_decay(results: list[DecayResult]) -> DecayResult | None:
    """
    Average per-symbol DecayResults. Each lag point is nanmean'd across
    all symbols that have that lag.

    Returns None if the input list is empty or all are invalid.
    """
    valid = [r for r in results if r.is_valid()]
    if not valid:
        return None
    if len(valid) == 1:
        valid[0].n_symbols = 1
        return valid[0]

    n = len(valid)
    symbols = [r.vt_symbol for r in valid]

    # Determine common lag set (intersection guarantees all have data)
    all_lag_sets = [set(r.lags) for r in valid]
    common_lags  = sorted(all_lag_sets[0].intersection(*all_lag_sets[1:]))

    if not common_lags:
        # Fall back to union with NaN fill
        common_lags = sorted({lag for r in valid for lag in r.lags})

    # Build per-lag lookup for each result
    def _idx(result: DecayResult) -> dict[int, DecayPoint]:
        return {p.lag: p for p in result.points}

    indexes = [_idx(r) for r in valid]

    def _nm_pts(lpts: list[DecayPoint | None], attr: str) -> float:
        vals = [getattr(p, attr) for p in lpts if p is not None]
        clean = [v for v in vals if not math.isnan(v)]
        return float(np.mean(clean)) if clean else float("nan")

    merged_points: list[DecayPoint] = []
    for lag in common_lags:
        pts = [idx.get(lag) for idx in indexes]
        merged_points.append(DecayPoint(
            lag=lag,
            ic_mean=_nm_pts(pts, "ic_mean"),
            rank_ic_mean=_nm_pts(pts, "rank_ic_mean"),
            icir=_nm_pts(pts, "icir"),
            rank_icir=_nm_pts(pts, "rank_icir"),
            sample_size=int(np.mean([p.sample_size for p in pts if p is not None])),
        ))

    return DecayResult(
        vt_symbol=_label(n, symbols),
        factor_name=valid[0].factor_name,
        max_lag=valid[0].max_lag,
        n_symbols=n,
        points=merged_points,
    )


# ------------------------------------------------------------------ #
#  Quantile cross-section merge
# ------------------------------------------------------------------ #

def merge_quantile(results: list[QuantileResult]) -> QuantileResult | None:
    """
    Average per-symbol QuantileResults.

    - annualized_returns, monotonicity_score, long_short_annualized → nanmean
    - cumulative_returns / quantile_returns / long_short_series →
      align on union date index, row-wise nanmean
    - sample_size → sum (total observations)
    """
    valid = [r for r in results if r.is_valid()]
    if not valid:
        return None
    if len(valid) == 1:
        valid[0].n_symbols = 1
        return valid[0]

    n = len(valid)
    symbols = [r.vt_symbol for r in valid]

    def _nm(vals: list[float]) -> float:
        clean = [v for v in vals if not math.isnan(v)]
        return float(np.mean(clean)) if clean else float("nan")

    q_labels = valid[0].quantile_labels

    # Scalar stats
    ann_ret: dict[str, float] = {}
    for ql in q_labels:
        ann_ret[ql] = _nm([r.annualized_returns.get(ql, float("nan")) for r in valid])

    mono  = _nm([r.monotonicity_score      for r in valid])
    ls_ann = _nm([r.long_short_annualized  for r in valid])

    # Time-series merging
    cum_ret: dict[str, pd.Series] = {}
    q_ret:   dict[str, pd.Series] = {}
    for ql in q_labels:
        cum_srs = [r.cumulative_returns.get(ql) for r in valid
                   if r.cumulative_returns.get(ql) is not None
                   and not r.cumulative_returns[ql].empty]
        if cum_srs:
            cum_ret[ql] = _align_nanmean(cum_srs)

        ret_srs = [r.quantile_returns.get(ql) for r in valid
                   if r.quantile_returns.get(ql) is not None
                   and not r.quantile_returns[ql].empty]
        if ret_srs:
            q_ret[ql] = _align_nanmean(ret_srs)

    ls_list = [r.long_short_series for r in valid
               if r.long_short_series is not None and not r.long_short_series.empty]
    ls_series = _align_nanmean(ls_list) if ls_list else None

    return QuantileResult(
        vt_symbol=_label(n, symbols),
        factor_name=valid[0].factor_name,
        lag=valid[0].lag,
        n_quantiles=valid[0].n_quantiles,
        n_symbols=n,
        quantile_labels=q_labels,
        quantile_returns=q_ret,
        cumulative_returns=cum_ret,
        long_short_series=ls_series,
        annualized_returns=ann_ret,
        monotonicity_score=mono,
        long_short_annualized=ls_ann,
        sample_size=sum(r.sample_size for r in valid),
    )


# ------------------------------------------------------------------ #
#  Internal helper
# ------------------------------------------------------------------ #

def _align_nanmean(series_list: list[pd.Series]) -> pd.Series:
    """
    Align multiple Series on their union DatetimeIndex,
    then compute row-wise nanmean. Returns a Series with the union index.
    """
    if not series_list:
        return pd.Series(dtype=float)
    if len(series_list) == 1:
        return series_list[0].copy()

    df = pd.concat(series_list, axis=1)
    result = df.mean(axis=1, skipna=True)
    return result
