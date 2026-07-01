"""
portfolio_engine/model/attribution_model.py

AttributionResult — 回撤归因数据结构。
Phase 3：补充 SlotContribution.cumulative_return + AttributionResult.computed_at。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class SlotContribution:
    """单个策略槽位对组合回撤的贡献。"""
    slot_name:         str
    contribution:      float = 0.0    # w_i × cumret_i（负数表示拖累回撤）
    weight:            float = 0.0    # 该槽位权重
    cumulative_return: float = field(default_factory=lambda: float("nan"))
                                      # 槽位在回撤区间内的累计收益（未乘权重）


@dataclass
class AttributionResult:
    """回撤归因结果快照。"""
    portfolio_name:    str
    computed_at:       datetime = field(default_factory=datetime.now)

    # 最大回撤区间
    drawdown_start:    datetime | None = None
    drawdown_end:      datetime | None = None
    total_drawdown:    float = field(default_factory=lambda: float("nan"))

    # 各槽位贡献（Phase 3 填充）
    slot_contributions: list[SlotContribution] = field(default_factory=list)

    # 市场系统性贡献（β × benchmark_cumret，Phase 3 填充）
    market_contribution: float = field(default_factory=lambda: float("nan"))

    is_valid: bool = False
