"""
portfolio_engine/model/factor_signal_model.py

FactorSignal — 因子信号数据结构（Phase 4）。

设计：
  - 桥接 FactorResearch 的 IcStats / FactorScore 与 PortfolioEngine 的权重分配
  - 不直接依赖 factor_research 包（通过 factor_bridge 转换）
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class FactorSignal:
    """
    单个因子的截面信号快照（一期）。

    由 FactorBridge 从 FactorResearch 结果提取，供 AllocationEngine 消费。
    """
    factor_name:   str                        # 因子名称
    generated_at:  datetime = field(default_factory=datetime.now)

    # IC 统计（来自 IcStats）
    ic_mean:       float = float("nan")       # 滚动 IC 均值
    rank_ic_mean:  float = float("nan")       # 滚动 RankIC 均值
    icir:          float = float("nan")       # ICIR
    rank_icir:     float = float("nan")       # RankICIR

    # 截面信号：symbol -> ic_value（截面 IC / RankIC）
    cross_section_ic:    dict[str, float] = field(default_factory=dict)

    # 截面评分：symbol -> score(0~100)（来自 FactorScore）
    cross_section_score: dict[str, float] = field(default_factory=dict)

    # 建议权重（由 FactorBridge 计算）
    suggested_weights:   dict[str, float] = field(default_factory=dict)

    # 信号强度：0~1（由 ICIR 标准化派生，供 dispatcher 决定是否采纳信号）
    signal_strength:     float = float("nan")

    is_valid:      bool = False


@dataclass
class FactorWeightOverride:
    """
    因子权重覆盖记录。

    当 WeightMethod == FACTOR_DRIVEN 时，记录本次因子信号对应的权重决策。
    """
    triggered_at:  datetime = field(default_factory=datetime.now)
    factor_name:   str = ""
    weights:       dict[str, float] = field(default_factory=dict)
    signal_strength: float = float("nan")
    ic_mean:       float = float("nan")
    method:        str = ""   # "rank" / "score" / "blend"
