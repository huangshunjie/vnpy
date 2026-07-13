"""
portfolio_engine/model/performance_model.py

PerformanceStats — 组合绩效统计数据结构。

Phase 1：仅定义字段。
Phase 2：由 PerformanceEngine 填充。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

import pandas as pd


@dataclass
class PerformanceStats:
    """组合绩效统计快照。"""
    portfolio_name: str
    computed_at:    datetime = field(default_factory=datetime.now)

    # 净值序列（index=datetime, value=nav），Phase 2 填充
    nav_series:     "pd.Series | None" = None

    # 标量统计（Phase 2 填充）
    total_return:   float = float("nan")   # 区间总收益率
    annual_return:  float = float("nan")   # 年化收益率
    sharpe_ratio:   float = float("nan")   # 年化 Sharpe（无风险利率=0）
    max_drawdown:   float = float("nan")   # 最大回撤（负数，如 -0.15）
    calmar_ratio:   float = float("nan")   # annual_return / |max_drawdown|
    volatility:     float = float("nan")   # 年化波动率
    win_rate:       float = float("nan")   # 日胜率

    # 基准对比（Phase 3 填充）
    benchmark_return: float = float("nan")
    alpha:            float = float("nan")
    beta:             float = float("nan")

    is_valid: bool = False
