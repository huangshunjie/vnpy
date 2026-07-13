"""
strategy_lifecycle_ai/utils/lifecycle_utils.py  (Phase 1 Stub)

策略生命周期工具函数（Phase 1: 函数签名定义，Phase 2+ 实现）。
"""

from __future__ import annotations
from ..constant import StrategyPhase, PerformanceRating


def classify_performance_rating(sharpe: float) -> PerformanceRating:
    """根据 Sharpe 评级（Phase 1 stub）。"""
    if sharpe >= 2.0: return PerformanceRating.EXCELLENT
    if sharpe >= 1.0: return PerformanceRating.GOOD
    if sharpe >= 0.0: return PerformanceRating.NEUTRAL
    return PerformanceRating.WEAK


def compute_live_days(registered_at) -> int:
    """计算策略运行天数（Phase 1 stub）。"""
    from datetime import datetime
    try:
        return max(0, (datetime.now() - registered_at).days)
    except Exception:
        return 0


def phase_transition_allowed(
    current: StrategyPhase,
    target:  StrategyPhase,
) -> bool:
    """
    判断生命周期阶段切换是否合法（Phase 1 stub）。

    合法路径（单向）：
      REGISTERED → INCUBATION → LIVE → PEAK → DECAY → RETIRED → ARCHIVED
      任何阶段 → RECOVERING → LIVE
    """
    allowed: dict[StrategyPhase, set[StrategyPhase]] = {
        StrategyPhase.REGISTERED:  {StrategyPhase.INCUBATION},
        StrategyPhase.INCUBATION:  {StrategyPhase.LIVE, StrategyPhase.RETIRED},
        StrategyPhase.LIVE:        {StrategyPhase.PEAK, StrategyPhase.DECAY, StrategyPhase.RETIRED},
        StrategyPhase.PEAK:        {StrategyPhase.LIVE, StrategyPhase.DECAY, StrategyPhase.RETIRED},
        StrategyPhase.DECAY:       {StrategyPhase.RECOVERING, StrategyPhase.RETIRED},
        StrategyPhase.RECOVERING:  {StrategyPhase.LIVE, StrategyPhase.DECAY, StrategyPhase.RETIRED},
        StrategyPhase.RETIRED:     {StrategyPhase.ARCHIVED},
        StrategyPhase.ARCHIVED:    set(),
    }
    return target in allowed.get(current, set())


def generate_strategy_id(prefix: str = "S") -> str:
    """生成唯一策略 ID（Phase 1 stub）。"""
    from datetime import datetime
    ts = datetime.now().strftime("%Y%m%d%H%M%S%f")[:18]
    return f"{prefix}_{ts}"
