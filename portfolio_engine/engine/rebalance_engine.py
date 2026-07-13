"""
portfolio_engine/engine/rebalance_engine.py

RebalanceEngine — 调仓触发与记录引擎。
Phase 2：实现 should_rebalance / compute_delta / record。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta

from ..constant import RebalanceFreq


@dataclass
class RebalanceRecord:
    """单次调仓记录。"""
    triggered_at: datetime
    prev_weights: dict[str, float]
    new_weights:  dict[str, float]
    delta:        dict[str, float]
    reason:       str = "scheduled"


class RebalanceEngine:
    """调仓触发与记录引擎。"""

    def __init__(self) -> None:
        self._history: list[RebalanceRecord] = []

    # ------------------------------------------------------------------ #
    #  Phase 2 实现
    # ------------------------------------------------------------------ #

    def should_rebalance(
        self,
        freq: RebalanceFreq,
        last_rebalance: datetime | None,
        current_dt: datetime,
    ) -> bool:
        """
        判断当前时间点是否应触发调仓。

        规则：
          DAILY   — 每个交易日触发
          WEEKLY  — 距上次 >= 7 日触发
          MONTHLY — 距上次 >= 28 日，或跨月触发
          MANUAL  — 永不自动触发（只能手动）
        """
        if freq == RebalanceFreq.MANUAL:
            return False

        if last_rebalance is None:
            return True

        delta = current_dt - last_rebalance

        if freq == RebalanceFreq.DAILY:
            return delta.days >= 1

        if freq == RebalanceFreq.WEEKLY:
            return delta.days >= 7

        if freq == RebalanceFreq.MONTHLY:
            # 跨自然月 且 距上次 >= 20 天（防止月底→月初 3 天重复触发）
            crossed_month = not (
                current_dt.year  == last_rebalance.year
                and current_dt.month == last_rebalance.month
            )
            return crossed_month and delta.days >= 20

        return False

    def compute_delta(
        self,
        prev_weights: dict[str, float],
        new_weights:  dict[str, float],
    ) -> dict[str, float]:
        """
        计算权重变化量 delta = new - prev。
        新增槽位的 prev 视为 0；移除槽位的 new 视为 0。
        """
        all_keys = set(prev_weights) | set(new_weights)
        return {
            k: new_weights.get(k, 0.0) - prev_weights.get(k, 0.0)
            for k in all_keys
        }

    def record(
        self,
        triggered_at: datetime,
        prev_weights: dict[str, float],
        new_weights:  dict[str, float],
        reason: str = "scheduled",
    ) -> RebalanceRecord:
        """生成并保存一条调仓记录，返回记录对象。"""
        delta = self.compute_delta(prev_weights, new_weights)
        rec   = RebalanceRecord(
            triggered_at=triggered_at,
            prev_weights=dict(prev_weights),
            new_weights=dict(new_weights),
            delta=delta,
            reason=reason,
        )
        self._history.append(rec)
        return rec

    def get_history(self) -> list[RebalanceRecord]:
        return list(self._history)

    def clear_history(self) -> None:
        self._history.clear()
