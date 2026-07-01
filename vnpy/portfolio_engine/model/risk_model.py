"""
portfolio_engine/model/risk_model.py

RiskExposure — 风险暴露数据结构。
Phase 3：补充 alpha / tracking_error / information_ratio /
          correlation_matrix / slot_volatilities / rolling_vol_series 字段。
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import datetime

import pandas as pd


@dataclass
class RiskExposure:
    """组合风险暴露快照。"""
    portfolio_name:     str
    computed_at:        datetime = field(default_factory=datetime.now)

    # ── Beta / Alpha ────────────────────────────────────────────────────
    portfolio_beta:     float = field(default_factory=lambda: float("nan"))
    portfolio_alpha:    float = field(default_factory=lambda: float("nan"))

    # ── 跟踪误差 / 信息比率 ─────────────────────────────────────────────
    tracking_error:     float = field(default_factory=lambda: float("nan"))
    information_ratio:  float = field(default_factory=lambda: float("nan"))

    # ── 行业暴露：sector_name -> weight ─────────────────────────────────
    sector_weights:     dict[str, float] = field(default_factory=dict)

    # ── 因子暴露：factor_name -> exposure_score ──────────────────────────
    factor_exposures:   dict[str, float] = field(default_factory=dict)

    # ── 相关矩阵（Phase 3）─────────────────────────────────────────────
    correlation_matrix: "pd.DataFrame | None" = None

    # ── 各槽位最新滚动波动率（21 日）─────────────────────────────────────
    slot_volatilities:  dict[str, float] = field(default_factory=dict)

    # ── 组合滚动波动率序列（index=datetime）──────────────────────────────
    rolling_vol_series: "pd.Series | None" = None

    # ── 最大回撤区间 ────────────────────────────────────────────────────
    max_drawdown:       float = field(default_factory=lambda: float("nan"))
    drawdown_start:     datetime | None = None
    drawdown_end:       datetime | None = None

    is_valid:           bool = False
