"""
portfolio_engine/model/portfolio_model.py

Portfolio / StrategySlot — 组合与策略槽位数据结构。

Portfolio  : 一个完整的组合定义（名称 + 若干策略槽位）
StrategySlot : 组合内单个策略的描述（代码 / 类型 / 目标权重）

Phase 1：仅定义字段，无业务逻辑。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

from ..constant import StrategyType, WeightMethod, RebalanceFreq


@dataclass
class StrategySlot:
    """组合内单个策略槽位。"""
    name:         str                        # 用户自定义名称，如 "CTA_MA"
    symbols:      list[str]                  # 对应合约代码列表，如 ["000001.SZSE"]
    strategy_type: StrategyType = StrategyType.CUSTOM
    target_weight: float = 0.0              # 目标权重（0~1），AllocationEngine 计算后填入
    enabled:      bool  = True


@dataclass
class Portfolio:
    """一个完整的投资组合定义。"""
    name:            str
    slots:           list[StrategySlot] = field(default_factory=list)
    weight_method:   WeightMethod       = WeightMethod.EQUAL
    rebalance_freq:  RebalanceFreq      = RebalanceFreq.MONTHLY
    start:           date | None        = None
    end:             date | None        = None
    benchmark_symbol: str               = ""   # 基准合约，如 "000300.SSE"
    description:     str               = ""

    def add_slot(self, slot: StrategySlot) -> None:
        """添加策略槽位（Phase 1：仅追加，不校验重复）。"""
        self.slots.append(slot)

    def remove_slot(self, name: str) -> None:
        """按名称移除策略槽位。"""
        self.slots = [s for s in self.slots if s.name != name]

    @property
    def n_slots(self) -> int:
        return len([s for s in self.slots if s.enabled])
