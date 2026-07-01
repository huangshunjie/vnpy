"""
factor_research/engine/redundancy_engine.py

RedundancyEngine -- Factor correlation and redundancy analysis.

Responsibilities:
  - Build a Pearson / Spearman correlation matrix from a collection of
    IC time-series (one per factor), aligning on their common date index.
  - Identify "redundant" factor pairs whose |corr| exceeds a threshold.
  - Produce a per-factor summary (mean |corr| with all others) to rank
    factors by their uniqueness / redundancy degree.
  - No UI access, no database access.

Input:  list[IcStats]  -- each element carries ic_series for one factor.
Output: CorrelationResult dataclass (returned by compute())

Design notes:
  - Uses Pearson correlation by default; Spearman optional.
  - Aligns series on their INTERSECTION of dates (inner join) so that
    different-length histories do not distort the matrix.
  - Works for N >= 1 factor(s); N=1 returns a 1×1 identity matrix.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from ..model import IcStats


@dataclass
class RedundantPair:
    """One factor pair whose |correlation| >= threshold."""
    factor_a:    str
    factor_b:    str
    correlation: float
    is_redundant: bool = True   # True when |corr| >= threshold


@dataclass
class CorrelationResult:
    """Output of RedundancyEngine.compute()."""
    factor_names:     list[str]
    corr_matrix:      pd.DataFrame          # N×N, index=columns=factor_names
    redundant_pairs:  list[RedundantPair]
    uniqueness:       dict[str, float]      # factor -> mean |corr| with others
    threshold:        float = 0.70
    n_samples:        int   = 0             # number of aligned date points

    def is_valid(self) -> bool:
        return (self.corr_matrix is not None
                and not self.corr_matrix.empty
                and len(self.factor_names) >= 1)


class RedundancyEngine:
    """Factor correlation and redundancy analysis engine."""

    DEFAULT_THRESHOLD = 0.70   # |corr| >= this → flag as redundant

    # ------------------------------------------------------------------ #
    #  Main interface
    # ------------------------------------------------------------------ #

    @staticmethod
    def compute(
        ic_stats_list: list[IcStats],
        threshold: float = DEFAULT_THRESHOLD,
        method: str = "pearson",
    ) -> CorrelationResult:
        """
        Build correlation matrix and identify redundant factor pairs.

        Parameters
        ----------
        ic_stats_list : list[IcStats]
            Each element must have a valid ic_series. Duplicate factor_names
            are deduplicated (last one wins).
        threshold : float
            |correlation| >= threshold flags a pair as redundant.
        method : "pearson" or "spearman"
        """
        valid = [s for s in ic_stats_list
                 if s.ic_series is not None and not s.ic_series.dropna().empty]

        if not valid:
            return CorrelationResult(
                factor_names=[],
                corr_matrix=pd.DataFrame(),
                redundant_pairs=[],
                uniqueness={},
                threshold=threshold,
            )

        # deduplicate: keep last entry for each factor_name
        seen: dict[str, IcStats] = {}
        for s in valid:
            seen[s.factor_name] = s
        valid = list(seen.values())

        names = [s.factor_name for s in valid]

        if len(valid) == 1:
            corr_df = pd.DataFrame([[1.0]], index=names, columns=names)
            return CorrelationResult(
                factor_names=names,
                corr_matrix=corr_df,
                redundant_pairs=[],
                uniqueness={names[0]: 0.0},
                threshold=threshold,
                n_samples=len(valid[0].ic_series.dropna()),
            )

        # align on intersection of DatetimeIndex
        series_map: dict[str, pd.Series] = {}
        for s in valid:
            sr = s.ic_series.dropna()
            if not isinstance(sr.index, pd.DatetimeIndex):
                try:
                    sr.index = pd.to_datetime(sr.index)
                except Exception:
                    continue
            series_map[s.factor_name] = sr

        aligned = pd.DataFrame(series_map).dropna()
        n_samples = len(aligned)

        if aligned.empty or n_samples < 3:
            # not enough overlap — return identity
            corr_df = pd.DataFrame(np.eye(len(names)),
                                   index=names, columns=names)
            return CorrelationResult(
                factor_names=names,
                corr_matrix=corr_df,
                redundant_pairs=[],
                uniqueness={n: 0.0 for n in names},
                threshold=threshold,
                n_samples=n_samples,
            )

        if method == "spearman":
            corr_df = aligned.rank().corr(method="pearson")
        else:
            corr_df = aligned.corr(method="pearson")

        # identify redundant pairs (upper triangle only)
        pairs: list[RedundantPair] = []
        n = len(names)
        for i in range(n):
            for j in range(i + 1, n):
                c = float(corr_df.iloc[i, j])
                if math.isnan(c):
                    continue
                pairs.append(RedundantPair(
                    factor_a=names[i],
                    factor_b=names[j],
                    correlation=round(c, 6),
                    is_redundant=abs(c) >= threshold,
                ))

        # uniqueness: mean |corr| with all other factors (lower = more unique)
        uniqueness: dict[str, float] = {}
        for name in names:
            others = [abs(float(corr_df.loc[name, o]))
                      for o in names if o != name
                      and not math.isnan(float(corr_df.loc[name, o]))]
            uniqueness[name] = round(float(np.mean(others)), 6) if others else 0.0

        return CorrelationResult(
            factor_names=names,
            corr_matrix=corr_df,
            redundant_pairs=pairs,
            uniqueness=uniqueness,
            threshold=threshold,
            n_samples=n_samples,
        )

    # ------------------------------------------------------------------ #
    #  Helpers
    # ------------------------------------------------------------------ #

    @staticmethod
    def redundant_only(result: CorrelationResult) -> list[RedundantPair]:
        """Return only pairs flagged as redundant."""
        return [p for p in result.redundant_pairs if p.is_redundant]

    @staticmethod
    def uniqueness_rank(result: CorrelationResult) -> list[tuple[str, float]]:
        """Return factors sorted ascending by mean |corr| (most unique first)."""
        return sorted(result.uniqueness.items(), key=lambda x: x[1])
