"""
portfolio_engine/model/allocation_model.py

AllocationResult — 权重分配结果数据结构。

Phase 1：仅定义字段，无计算逻辑。
Phase 2：由 AllocationEngine 填充。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from ..constant import WeightMethod


@dataclass
class AllocationResult:
    """一次权重分配计算的完整结果。"""
    method:        WeightMethod
    weights:       dict[str, float]        # slot_name -> weight (sum == 1.0)
    computed_at:   datetime = field(default_factory=datetime.now)
    n_slots:       int      = 0
    is_valid:      bool     = False        # False 直到 AllocationEngine 计算成功

    # Phase 2 附加字段（计算后填入）
    volatilities:  dict[str, float] = field(default_factory=dict)   # slot -> annualised σ
    risk_contribs: dict[str, float] = field(default_factory=dict)   # slot -> risk contribution

    def total_weight(self) -> float:
        return sum(self.weights.values())
